from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class PublicPageTests(TestCase):
    def test_home_page_reads_like_a_banner_landing_page(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Understand your stress before it becomes overwhelming.')
        self.assertContains(response, 'Create an account')
        self.assertContains(response, 'Sign in')
        self.assertContains(response, 'About')
        self.assertContains(response, 'How To')

    def test_base_template_includes_pwa_support(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'name="theme-color"')
        self.assertContains(response, 'serviceWorker')

    def test_service_worker_supports_offline_fallback(self):
        service_worker_path = Path(settings.BASE_DIR) / 'static' / 'sw.js'
        service_worker_content = service_worker_path.read_text(encoding='utf-8')

        self.assertIn('offline.html', service_worker_content)
        self.assertIn('fetch', service_worker_content)

    def test_service_worker_route_is_available_at_root_scope(self):
        response = self.client.get(reverse('service_worker'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertContains(response, 'offline.html')

    def test_service_worker_prefers_network_for_document_requests(self):
        response = self.client.get(reverse('service_worker'))

        self.assertContains(response, 'request.destination === \'document\'')
        self.assertContains(response, 'text/html')

    def test_base_template_includes_install_prompt(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Install App')

    def test_base_template_includes_mobile_bottom_nav(self):
        response = self.client.get(reverse('home'))

    def test_base_template_supports_offline_form_draft_storage(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'draft')

    def test_base_template_includes_app_shell_loading_state(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'app-shell-loading')

    def test_base_template_includes_refresh_prompt(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Refresh')

    def test_base_template_includes_app_shell_header(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'app-shell-header')

    def test_about_page_explains_the_platform(self):
        response = self.client.get(reverse('about'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A simple platform for student stress check-ins.')
        self.assertContains(response, 'For students')
        self.assertContains(response, 'For counselors')
        self.assertContains(response, 'References')
        self.assertContains(response, 'Study habits, skills, and attitudes: The third pillar supporting collegiate academic performance')

    def test_how_to_page_explains_the_user_flow(self):
        response = self.client.get(reverse('how_to'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick guides for students and counselors.')
        self.assertContains(response, 'Create an account or sign in')
        self.assertContains(response, 'Complete a check-in')
        self.assertContains(response, 'Review results and history')
