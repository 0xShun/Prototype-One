from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, time, timedelta
from io import StringIO

from django.core.management import call_command
from counselor.models import CounselorNote
from counselor.models import (
    AppointmentBooking,
    CounselorAvailability,
    ContactMessage,
    CounselorDigestDelivery,
    CounselorUnavailableTime,
    StudentContactRequest,
    TeacherReferral,
)
from accounts.models import StudentProfile, UserNotification
from intake.models import Result

from .helpers import create_counselor, create_result_for_student, create_student


class CounselorAccessTests(TestCase):
    def setUp(self):
        self.counselor = create_counselor('counselorflow')
        self.high_student = create_student('highstudent', program='CS', year_level='2')
        self.moderate_student = create_student('modstudent', program='Psychology', year_level='1')
        self.low_student = create_student('lowstudent', program='Biology', year_level='3')

        create_result_for_student(self.high_student, stress_level='High', days_ago=1)
        create_result_for_student(self.moderate_student, stress_level='Moderate', days_ago=2)
        create_result_for_student(self.low_student, stress_level='Low', days_ago=3)

    def test_counselor_can_access_dashboard_and_view_only_risk_students(self):
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.get(reverse('counselor:dashboard'))

        self.assertEqual(response.status_code, 200)
        students = response.context['students']
        self.assertEqual(len(students), 2)
        self.assertEqual([row['latest_result'].stress_level for row in students], ['High', 'Moderate'])

    def test_non_counselor_is_blocked_from_dashboard(self):
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.get(reverse('counselor:dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_counselor_can_view_student_detail_history(self):
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.get(reverse('counselor:student_detail', args=[self.high_student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'], self.high_student)
        self.assertContains(response, 'Results history')
        self.assertContains(response, 'Recommendations')

    def test_student_can_submit_contact_request(self):
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'I would like help planning how to manage workload this week.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.high_student.contact_requests.count(), 1)
        thread = self.high_student.contact_requests.first()
        self.assertEqual(thread.messages.count(), 1)
        self.assertEqual(thread.messages.first().sender, ContactMessage.Sender.STUDENT)

    def test_counselor_dashboard_does_not_show_unassigned_requests_section(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'Please follow up with me.'},
        )

        self.client.login(username='counselorflow', password='StrongPass123!')
        response = self.client.get(reverse('counselor:dashboard'))

        self.assertContains(response, 'Urgent requests')
        self.assertNotContains(response, 'Unassigned requests')

    def test_counselor_can_update_contact_request_status_and_reply(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'Need help figuring out my schedule.'},
        )
        contact_request = self.high_student.contact_requests.first()

        self.client.login(username='counselorflow', password='StrongPass123!')
        claim_response = self.client.post(
            reverse('counselor:claim_contact_request', args=[contact_request.id]),
        )
        self.assertEqual(claim_response.status_code, 302)
        response = self.client.post(
            reverse('counselor:contact_request_detail', args=[contact_request.id]),
            {
                'body': 'I reviewed your request and will follow up tomorrow.',
            },
        )

        self.assertEqual(response.status_code, 302)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.status, 'In progress')
        self.assertEqual(contact_request.replied_by, self.counselor)
        self.assertIsNotNone(contact_request.replied_at)
        self.assertEqual(contact_request.messages.count(), 2)
        self.assertEqual(contact_request.messages.last().sender, ContactMessage.Sender.COUNSELOR)

    def test_only_assigned_counselor_can_view_and_reply_to_request(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(reverse('counselor:contact_request'), {'message': 'Please help me.'})
        contact_request = self.high_student.contact_requests.first()
        other_counselor = create_counselor('otherreplycounselor')

        self.client.login(username='counselorflow', password='StrongPass123!')
        self.client.post(reverse('counselor:claim_contact_request', args=[contact_request.id]))

        self.client.login(username=other_counselor.username, password='StrongPass123!')
        detail_response = self.client.get(reverse('counselor:contact_request_detail', args=[contact_request.id]))
        reply_response = self.client.post(
            reverse('counselor:contact_request_detail', args=[contact_request.id]),
            {'body': 'I should not be able to send this.'},
        )

        self.assertEqual(detail_response.status_code, 403)
        self.assertEqual(reply_response.status_code, 403)

    def test_assigned_counselor_can_close_and_student_can_reopen_request(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(reverse('counselor:contact_request'), {'message': 'I need support.'})
        contact_request = self.high_student.contact_requests.first()

        self.client.login(username='counselorflow', password='StrongPass123!')
        self.client.post(reverse('counselor:claim_contact_request', args=[contact_request.id]))
        self.client.post(
            reverse('counselor:contact_request_detail', args=[contact_request.id]),
            {'body': 'I am following up with you.'},
        )
        close_response = self.client.post(reverse('counselor:close_contact_request', args=[contact_request.id]))
        self.assertEqual(close_response.status_code, 302)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.status, 'Closed')
        assigned_counselor_id = contact_request.assigned_counselor_id

        self.client.login(username='highstudent', password='StrongPass123!')
        reply_response = self.client.post(
            reverse('counselor:student_reply', args=[contact_request.id]),
            {'message': 'I have more information to share.'},
        )

        self.assertEqual(reply_response.status_code, 302)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.status, 'Open')
        self.assertEqual(contact_request.assigned_counselor_id, assigned_counselor_id)
        self.assertEqual(contact_request.messages.count(), 3)

    def test_second_counselor_cannot_claim_assigned_request(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(reverse('counselor:contact_request'), {'message': 'Please assign me.'})
        contact_request = self.high_student.contact_requests.first()
        other_counselor = create_counselor('secondclaimcounselor')

        self.client.login(username='counselorflow', password='StrongPass123!')
        first_claim = self.client.post(reverse('counselor:claim_contact_request', args=[contact_request.id]))
        self.client.login(username=other_counselor.username, password='StrongPass123!')
        second_claim = self.client.post(reverse('counselor:claim_contact_request', args=[contact_request.id]))

        self.assertEqual(first_claim.status_code, 302)
        self.assertEqual(second_claim.status_code, 404)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.assigned_counselor, self.counselor)

    def test_student_can_see_counselor_reply_and_status(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'Need help figuring out my schedule.'},
        )
        contact_request = self.high_student.contact_requests.first()

        contact_request.status = 'Closed'
        contact_request.replied_by = self.counselor
        contact_request.save()
        ContactMessage.objects.create(
            thread=contact_request,
            sender=ContactMessage.Sender.COUNSELOR,
            body='Thanks for reaching out. Please check your email for next steps.',
        )

        response = self.client.get(reverse('counselor:contact_request'))

        self.assertContains(response, 'chat-room__messages')
        self.assertContains(response, 'Thanks for reaching out. Please check your email for next steps.')

    def test_counselor_can_add_notes_to_student_detail(self):
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.post(
            reverse('counselor:student_detail', args=[self.high_student.id]),
            {'note': 'Student should be contacted this week about workload and sleep.'},
        )

        self.assertEqual(response.status_code, 302)
        note = CounselorNote.objects.get(student=self.high_student)
        self.assertEqual(note.counselor, self.counselor)
        self.assertIn('workload and sleep', note.note)

    def test_counselor_notes_appear_on_student_detail(self):
        CounselorNote.objects.create(
            student=self.high_student,
            counselor=self.counselor,
            note='Schedule follow-up after midterms.',
        )
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.get(reverse('counselor:student_detail', args=[self.high_student.id]))

        self.assertContains(response, 'Schedule follow-up after midterms.')

    def test_student_cannot_access_another_student_detail(self):
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.get(reverse('counselor:student_detail', args=[self.moderate_student.id]))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_excludes_counselors(self):
        second_counselor = create_counselor('secondcounselor')
        create_result_for_student(second_counselor, stress_level='High', days_ago=1)
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.get(reverse('counselor:dashboard'))
        students = response.context['students']

        self.assertNotIn(second_counselor, [row['user'] for row in students])

    def test_students_are_blocked_from_posting_counselor_notes(self):
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.post(
            reverse('counselor:student_detail', args=[self.moderate_student.id]),
            {'note': 'This should not be allowed.'},
        )

        self.assertEqual(response.status_code, 403)

    def test_counselor_can_archive_student_result(self):
        result = self.high_student.intakes.first().result
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.post(reverse('counselor:archive_result', args=[result.id]))

        self.assertEqual(response.status_code, 302)
        result.refresh_from_db()
        self.assertEqual(result.archived_by, self.counselor)
        self.assertIsNotNone(result.archived_at)

    def test_archive_page_lists_only_results_archived_by_current_counselor(self):
        result = self.high_student.intakes.first().result
        result.archived_at = timezone.now()
        result.archived_by = self.counselor
        result.save(update_fields=['archived_at', 'archived_by'])
        other_counselor = create_counselor('archiveother')
        other_result = self.moderate_student.intakes.first().result
        other_result.archived_at = timezone.now()
        other_result.archived_by = other_counselor
        other_result.save(update_fields=['archived_at', 'archived_by'])
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.get(reverse('counselor:archive'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Archived by counselorflow')
        self.assertNotContains(response, 'Archived by archiveother')

    def test_archived_result_can_be_restored_by_archiving_counselor(self):
        result = self.high_student.intakes.first().result
        result.archived_at = timezone.now()
        result.archived_by = self.counselor
        result.save(update_fields=['archived_at', 'archived_by'])
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.post(reverse('counselor:restore_result', args=[result.id]))

        self.assertEqual(response.status_code, 302)
        result.refresh_from_db()
        self.assertIsNone(result.archived_at)
        self.assertIsNone(result.archived_by)

    def test_archived_result_cannot_be_deleted_by_another_counselor(self):
        result = self.high_student.intakes.first().result
        result.archived_at = timezone.now()
        result.archived_by = self.counselor
        result.save(update_fields=['archived_at', 'archived_by'])
        other_counselor = create_counselor('deleteother')
        self.client.login(username=other_counselor.username, password='StrongPass123!')

        response = self.client.post(reverse('counselor:delete_archived_result', args=[result.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Result.objects.filter(id=result.id).exists())

    def test_archived_result_can_be_permanently_deleted_by_archiving_counselor(self):
        result = self.high_student.intakes.first().result
        result.archived_at = timezone.now()
        result.archived_by = self.counselor
        result.save(update_fields=['archived_at', 'archived_by'])
        result_id = result.id
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.post(reverse('counselor:delete_archived_result', args=[result_id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Result.objects.filter(id=result_id).exists())

    def test_counselor_cannot_archive_counselor_result(self):
        counselor_result = create_result_for_student(self.counselor, stress_level='High')[1]
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.post(reverse('counselor:archive_result', args=[counselor_result.id]))

        self.assertEqual(response.status_code, 404)

    def test_counselor_cannot_submit_student_contact_request(self):
        self.client.login(username='counselorflow', password='StrongPass123!')

        response = self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'This should not be allowed.'},
        )

        self.assertEqual(response.status_code, 403)

    def test_counselor_can_access_contact_request_detail(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'Need help with workload.'},
        )
        contact_request = self.high_student.contact_requests.first()

        self.client.login(username='counselorflow', password='StrongPass123!')
        response = self.client.get(reverse('counselor:contact_request_detail', args=[contact_request.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Need help with workload.')
        self.assertContains(response, 'Open')

    def test_user_without_student_profile_can_access_contact_request_page(self):
        User = get_user_model()
        user = User.objects.create_user(username='profileless', password='StrongPass123!')
        self.client.login(username='profileless', password='StrongPass123!')

        response = self.client.get(reverse('counselor:contact_request'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'chat-room__messages--empty')

    def make_approved_teacher(self, username='schoolteacher'):
        teacher = get_user_model().objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='StrongPass123!',
            first_name='School',
            last_name='Teacher',
        )
        StudentProfile.objects.create(
            user=teacher,
            program='Guidance Office',
            phone_number='+639171234567',
            is_teacher=True,
            is_teacher_approved=True,
        )
        return teacher

    def test_teacher_referral_notifies_student_without_exposing_reason(self):
        teacher = self.make_approved_teacher()
        referral_reason = 'Student shared a private concern about family pressure.'
        self.client.login(username=teacher.username, password='StrongPass123!')

        response = self.client.post(reverse('counselor:teacher_referral'), {
            'student': self.high_student.id,
            'reason': referral_reason,
        })

        self.assertEqual(response.status_code, 302)
        referral = TeacherReferral.objects.get(student=self.high_student, teacher=teacher)
        student_notification = UserNotification.objects.get(recipient=self.high_student)
        counselor_notification = UserNotification.objects.get(recipient=self.counselor)
        self.assertEqual(referral.reason, referral_reason)
        self.assertNotIn(referral_reason, student_notification.body)
        self.assertIn('referred', student_notification.body)
        self.assertNotIn(referral_reason, counselor_notification.body)

    def test_teacher_cannot_open_counselor_referral_queue(self):
        teacher = self.make_approved_teacher()
        self.client.login(username=teacher.username, password='StrongPass123!')

        response = self.client.get(reverse('counselor:dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_student_directory_lists_only_approved_teacher_contact(self):
        teacher = self.make_approved_teacher()
        pending = get_user_model().objects.create_user(username='pendingteacher', password='StrongPass123!')
        StudentProfile.objects.create(user=pending, is_teacher=True, phone_number='+639170000000')
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.get(reverse('counselor:teacher_directory'))

        self.assertContains(response, teacher.studentprofile.phone_number)
        self.assertNotContains(response, pending.studentprofile.phone_number)
        self.assertNotContains(response, f'tel:{teacher.studentprofile.phone_number}')

    def test_approved_teacher_can_open_counselor_directory(self):
        teacher = self.make_approved_teacher()
        self.client.login(username=teacher.username, password='StrongPass123!')

        response = self.client.get(reverse('counselor:teacher_directory'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Counselor contacts')
        self.assertContains(response, self.counselor.username)

    def test_urgent_request_creates_priority_and_notifies_all_counselors(self):
        second_counselor = create_counselor('urgentcounselor')
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.post(reverse('counselor:urgent_help'), {'message': 'I need urgent help today.'})

        self.assertEqual(response.status_code, 302)
        urgent_request = self.high_student.contact_requests.get()
        self.assertEqual(urgent_request.priority, StudentContactRequest.Priority.URGENT)
        self.assertTrue(UserNotification.objects.filter(recipient=self.counselor, kind=UserNotification.Kind.URGENT_HELP).exists())
        self.assertTrue(UserNotification.objects.filter(recipient=second_counselor, kind=UserNotification.Kind.URGENT_HELP).exists())
        self.assertTrue(UserNotification.objects.filter(recipient=self.high_student, kind=UserNotification.Kind.URGENT_HELP).exists())

    def test_student_books_whole_slot_and_cancellation_releases_it(self):
        appointment_date = timezone.localdate() + timedelta(days=2)
        rule = CounselorAvailability.objects.create(
            counselor=self.counselor,
            weekday=appointment_date.weekday(),
            start_time=time(13, 0),
            end_time=time(14, 0),
            effective_from=timezone.localdate(),
        )
        slot_start = timezone.make_aware(datetime.combine(appointment_date, time(13, 0)))
        self.client.login(username='highstudent', password='StrongPass123!')

        calendar_response = self.client.get(
            reverse('counselor:appointment_calendar'),
            {'counselor_id': self.counselor.id},
        )
        self.assertContains(calendar_response, '1:00 PM to 2:00 PM')
        booking_response = self.client.post(reverse('counselor:book_appointment'), {
            'availability_id': rule.id,
            'starts_at': slot_start.isoformat(),
        })
        self.assertEqual(booking_response.status_code, 302)
        booking = AppointmentBooking.objects.get(student=self.high_student)
        self.assertEqual(booking.ends_at - booking.starts_at, timedelta(hours=1))
        conversation = StudentContactRequest.objects.get(
            student=self.high_student,
            assigned_counselor=self.counselor,
        )
        appointment_message = conversation.messages.get(
            sender=ContactMessage.Sender.SYSTEM,
            body__contains='booked an appointment for',
        )
        self.assertIn('highstudent', appointment_message.body)
        self.assertIn('booked an appointment for', appointment_message.body)
        self.assertIn('01:00 PM to 02:00 PM', appointment_message.body)

        self.client.login(username='modstudent', password='StrongPass123!')
        taken_response = self.client.post(reverse('counselor:book_appointment'), {
            'availability_id': rule.id,
            'starts_at': slot_start.isoformat(),
        })
        self.assertEqual(taken_response.status_code, 302)
        self.assertFalse(AppointmentBooking.objects.filter(student=self.moderate_student).exists())

        self.client.login(username='highstudent', password='StrongPass123!')
        cancel_response = self.client.post(reverse('counselor:cancel_appointment', args=[booking.id]))
        self.assertEqual(cancel_response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, AppointmentBooking.Status.CANCELLED)

        self.client.login(username='modstudent', password='StrongPass123!')
        retry_response = self.client.post(reverse('counselor:book_appointment'), {
            'availability_id': rule.id,
            'starts_at': slot_start.isoformat(),
        })
        self.assertEqual(retry_response.status_code, 302)
        self.assertTrue(AppointmentBooking.objects.filter(student=self.moderate_student, status=AppointmentBooking.Status.BOOKED).exists())

    def test_same_day_appointment_is_not_bookable(self):
        appointment_date = timezone.localdate()
        rule = CounselorAvailability.objects.create(
            counselor=self.counselor,
            weekday=appointment_date.weekday(),
            start_time=time(16, 0),
            end_time=time(17, 0),
            effective_from=appointment_date,
        )
        slot_start = timezone.make_aware(datetime.combine(appointment_date, time(16, 0)))
        self.client.login(username='highstudent', password='StrongPass123!')

        response = self.client.post(reverse('counselor:book_appointment'), {
            'availability_id': rule.id,
            'starts_at': slot_start.isoformat(),
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AppointmentBooking.objects.filter(student=self.high_student).exists())

    def test_weekly_elevated_digest_sends_once_per_counselor_and_week(self):
        output = StringIO()
        call_command('send_weekly_elevated_digest', stdout=output)
        call_command('send_weekly_elevated_digest', stdout=output)

        self.assertEqual(CounselorDigestDelivery.objects.filter(counselor=self.counselor).count(), 1)
        digest = UserNotification.objects.filter(
            recipient=self.counselor,
            kind=UserNotification.Kind.WEEKLY_DIGEST,
        )
        self.assertEqual(digest.count(), 1)
        self.assertIn('elevated check-in result last week', digest.first().body)
