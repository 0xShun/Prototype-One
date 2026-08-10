from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
                'program': 'Psychology',
                'year_level': '3',
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

    def test_registration_creates_user_profile_record(self):
        self.client.post(
            reverse('register'),
            {
                'username': 'profilestudent',
                'email': 'profilestudent@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'program': 'Biology',
                'year_level': '1',
            },
        )

        user = get_user_model().objects.get(username='profilestudent')
        self.assertEqual(user.studentprofile.program, 'Biology')
        self.assertEqual(user.studentprofile.year_level, '1')
