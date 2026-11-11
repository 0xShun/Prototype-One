from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import PushSubscription, UserNotification

from .helpers import create_student


class AccountFlowTests(TestCase):
    def test_user_can_register_log_in_and_log_out(self):
        register_response = self.client.post(
            reverse('register'),
            {
                'username': 'accountstudent',
                'email': 'accountstudent@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'program': 'STEM',
                'year_level': '11',
            },
        )

        self.assertEqual(register_response.status_code, 302)
        self.assertEqual(register_response.url, reverse('home'))
        self.assertTrue(self.client.session.get('_auth_user_id'))

        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

        login_response = self.client.post(
            reverse('login'),
            {'username': 'accountstudent', 'password': 'StrongPass123!'},
        )

        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.url, reverse('home'))

    def test_logout_redirects_to_home_and_blocks_protected_pages(self):
        create_student('logoutguard')
        self.client.login(username='logoutguard', password='StrongPass123!')

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

        protected_response = self.client.get(reverse('intake:create'))
        self.assertEqual(protected_response.status_code, 302)
        self.assertIn('/accounts/login/', protected_response.url)

    def test_logout_accepts_direct_get_requests(self):
        create_student('getlogout')
        self.client.login(username='getlogout', password='StrongPass123!')

        response = self.client.get(reverse('logout'))

        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_creates_user_profile_record(self):
        self.client.post(
            reverse('register'),
            {
                'username': 'profilestudent',
                'email': 'profilestudent@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'program': 'ABM',
                'year_level': '12',
            },
        )

        user = get_user_model().objects.get(username='profilestudent')
        self.assertEqual(user.studentprofile.program, 'ABM')
        self.assertEqual(user.studentprofile.year_level, '12')

    def test_junior_student_registers_without_strand(self):
        response = self.client.post(reverse('register'), {
            'username': 'juniorstudent',
            'email': 'juniorstudent@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'year_level': '7',
        })
        self.assertEqual(response.status_code, 302)
        profile = get_user_model().objects.get(username='juniorstudent').studentprofile
        self.assertEqual((profile.year_level, profile.program), ('7', ''))

    def test_teacher_signup_requires_admin_approval_before_teacher_tools(self):
        response = self.client.post(reverse('register_teacher'), {
            'username': 'newteacher',
            'first_name': 'Taylor',
            'last_name': 'Teacher',
            'email': 'newteacher@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'program': 'Guidance Office',
            'phone_number': '+639171234567',
        })

        self.assertEqual(response.status_code, 302)
        teacher = get_user_model().objects.get(username='newteacher')
        self.assertTrue(teacher.studentprofile.is_teacher)
        self.assertFalse(teacher.studentprofile.is_teacher_approved)
        self.assertEqual(teacher.studentprofile.phone_number, '+639171234567')

        self.client.login(username='newteacher', password='StrongPass123!')
        home_response = self.client.get(reverse('home'))
        referral_response = self.client.get(reverse('counselor:teacher_referral'))
        self.assertContains(home_response, 'awaiting approval')
        self.assertEqual(referral_response.status_code, 403)

    def test_notification_inbox_is_private_and_can_mark_notifications_read(self):
        student = create_student('notifyowner')
        other_student = create_student('notifyother')
        own_notice = UserNotification.objects.create(
            recipient=student,
            kind=UserNotification.Kind.REFERRAL,
            title='Teacher referral',
            body='A teacher referred you.',
        )
        other_notice = UserNotification.objects.create(
            recipient=other_student,
            kind=UserNotification.Kind.REFERRAL,
            title='Private other notice',
            body='Not for this account.',
        )
        self.client.login(username=student.username, password='StrongPass123!')

        inbox = self.client.get(reverse('notifications'))
        forbidden_mark = self.client.post(reverse('mark_notification_read', args=[other_notice.id]))
        read_response = self.client.post(reverse('mark_notification_read', args=[own_notice.id]))

        self.assertContains(inbox, 'A teacher referred you.')
        self.assertNotContains(inbox, 'Not for this account.')
        self.assertRedirects(forbidden_mark, reverse('notifications'))
        self.assertRedirects(read_response, reverse('notifications'))
        own_notice.refresh_from_db()
        self.assertIsNotNone(own_notice.read_at)

    def test_push_subscription_is_stored_for_signed_in_user(self):
        student = create_student('pushsubscriber')
        self.client.login(username=student.username, password='StrongPass123!')

        response = self.client.post(
            reverse('push_subscription'),
            data='{"endpoint":"https://push.example/sub/1","keys":{"p256dh":"public-key","auth":"auth-key"}}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(user=student, endpoint='https://push.example/sub/1').exists())
