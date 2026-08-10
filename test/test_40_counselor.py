from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from counselor.models import CounselorNote
from counselor.models import ContactMessage

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

    def test_counselor_dashboard_shows_open_contact_requests(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'Please follow up with me.'},
        )

        self.client.login(username='counselorflow', password='StrongPass123!')
        response = self.client.get(reverse('counselor:dashboard'))

        self.assertContains(response, 'Open student contact requests')
        self.assertContains(response, 'Please follow up with me.')

    def test_counselor_can_update_contact_request_status_and_reply(self):
        self.client.login(username='highstudent', password='StrongPass123!')
        self.client.post(
            reverse('counselor:contact_request'),
            {'message': 'Need help figuring out my schedule.'},
        )
        contact_request = self.high_student.contact_requests.first()

        self.client.login(username='counselorflow', password='StrongPass123!')
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
