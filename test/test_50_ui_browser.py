import os

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from playwright.sync_api import sync_playwright

from .helpers import create_counselor, create_result_for_student, create_student


class BrowserFlowTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.video_dir = os.path.join(os.getcwd(), 'test', 'videos')
        os.makedirs(cls.video_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.context = self.browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            record_video_dir=self.__class__.video_dir,
            record_video_size={"width": 390, "height": 844},
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(8000)

    def tearDown(self):
        self.page.close()
        # close context to flush and save the recorded video
        try:
            self.context.close()
        except Exception:
            pass

    def open_mobile_menu(self):
        self.assertTrue(self.page.locator('#nav-toggle').is_visible())
        self.page.locator('#nav-toggle').click()
        self.assertTrue(self.page.get_by_role('navigation').first.is_visible())

    def test_public_banner_pages_render_on_mobile(self):
        self.page.goto(f'{self.live_server_url}/')
        self.assertIn('Understand your stress before it becomes overwhelming.', self.page.locator('body').inner_text())
        self.assertTrue(self.page.locator('#nav-toggle').is_visible())
        self.open_mobile_menu()
        self.assertTrue(self.page.get_by_role('link', name='About').first.is_visible())
        self.assertTrue(self.page.get_by_role('link', name='How To').first.is_visible())

        self.page.get_by_role('link', name='About').first.click()
        self.assertIn('A simple platform for student stress check-ins.', self.page.locator('body').inner_text())
        self.assertIn('References', self.page.locator('body').inner_text())
        self.assertIn('Study habits, skills, and attitudes: The third pillar supporting collegiate academic performance', self.page.locator('body').inner_text())

        self.open_mobile_menu()
        self.page.get_by_role('link', name='How To').first.click()
        self.assertIn('Quick guides for students and counselors.', self.page.locator('body').inner_text())

    def test_student_browser_flow_from_register_to_logout(self):
        username = 'browserstudent'
        self.page.goto(f'{self.live_server_url}/accounts/register/')
        self.page.locator('input[name="username"]').fill(username)
        self.page.locator('input[name="email"]').fill(f'{username}@example.com')
        self.page.locator('input[name="password1"]').fill('StrongPass123!')
        self.page.locator('input[name="password2"]').fill('StrongPass123!')
        self.page.locator('input[name="program"]').fill('Psychology')
        self.page.locator('input[name="year_level"]').fill('3')
        self.page.get_by_role('button', name='Register').click()
        self.page.wait_for_url(f'{self.live_server_url}/')

        self.page.goto(f'{self.live_server_url}/intake/new/')
        reminder_text = self.page.locator('.soft-reminder').first.inner_text()
        self.assertIn('We recommend checking in once a week', reminder_text)
        self.assertIn('These questions are based on established research', self.page.locator('body').inner_text())
        self.assertNotIn('Research behind these questions', self.page.locator('body').inner_text())

        self.page.locator('input[name="workload_hours"]').fill('11')
        self.page.locator('input[name="study_habit_score"]').fill('3')
        self.page.locator('input[name="mood_energy"]').fill('3')
        self.page.get_by_role('button', name='Next').click()

        self.page.locator('input[name="deadline_pressure"]').fill('9')
        self.page.locator('input[name="class_load"]').fill('8')
        self.page.get_by_role('button', name='Next').click()

        self.page.locator('input[name="sleep_hours"]').fill('4')
        self.page.locator('select[name="sleep_quality"]').select_option('Poor')
        self.page.locator('input[name="exercise_minutes"]').fill('10')
        self.page.locator('input[name="sleep_consistency"]').fill('3')
        self.page.get_by_role('button', name='Next').click()

        self.page.locator('input[name="social_media_hours"]').fill('5')
        self.page.get_by_role('button', name='Next').click()

        self.page.locator('input[name="mbiss_exhaustion_1"]').fill('6')
        self.page.locator('input[name="mbiss_exhaustion_2"]').fill('6')
        self.page.locator('input[name="mbiss_exhaustion_3"]').fill('5')
        self.page.locator('input[name="mbiss_exhaustion_4"]').fill('6')
        self.page.locator('input[name="mbiss_exhaustion_5"]').fill('5')
        self.page.locator('input[name="mbiss_cynicism_1"]').fill('5')
        self.page.locator('input[name="mbiss_cynicism_2"]').fill('5')
        self.page.locator('input[name="mbiss_cynicism_3"]').fill('4')
        self.page.locator('input[name="mbiss_cynicism_4"]').fill('5')
        self.page.locator('input[name="mbiss_academic_efficacy_1"]').fill('3')
        self.page.locator('input[name="mbiss_academic_efficacy_2"]').fill('3')
        self.page.locator('input[name="mbiss_academic_efficacy_3"]').fill('4')
        self.page.locator('input[name="mbiss_academic_efficacy_4"]').fill('3')
        self.page.locator('input[name="mbiss_academic_efficacy_5"]').fill('4')
        self.page.locator('input[name="mbiss_academic_efficacy_6"]').fill('3')
        self.page.get_by_role('button', name='Submit').click()
        self.page.wait_for_url(f'{self.live_server_url}/intake/result/')
        self.assertIn('Your latest result', self.page.locator('body').inner_text())

        self.page.goto(f'{self.live_server_url}/intake/history/')
        self.assertIn('Your progress', self.page.locator('body').inner_text())
        self.assertIn('High', self.page.locator('body').inner_text())

        self.open_mobile_menu()
        self.page.get_by_role('button', name='Logout').click()
        self.page.wait_for_url(f'{self.live_server_url}/')
        self.assertIn('Create an account', self.page.locator('body').inner_text())

        self.page.goto(f'{self.live_server_url}/intake/new/')
        self.page.wait_for_url(f'{self.live_server_url}/accounts/login/?next=/intake/new/')

    def test_counselor_browser_flow_dashboard_and_detail(self):
        counselor = create_counselor('browsercounselor')
        student = create_student('browserrisk', program='CS', year_level='2')
        create_result_for_student(student, stress_level='High', days_ago=1)

        self.page.goto(f'{self.live_server_url}/accounts/login/')
        self.page.locator('input[name="username"]').fill(counselor.username)
        self.page.locator('input[name="password"]').fill('StrongPass123!')
        self.page.get_by_role('button', name='Log in').click()
        self.page.wait_for_url(f'{self.live_server_url}/')

        self.page.goto(f'{self.live_server_url}/counselor/dashboard/')
        self.assertIn('Student support', self.page.locator('body').inner_text())
        self.assertIn('browserrisk', self.page.locator('body').inner_text())

        self.page.get_by_role('link', name='View full history').first.click()
        self.assertIn('Results history', self.page.locator('body').inner_text())
        self.assertIn('CHECK-IN DETAILS', self.page.locator('body').inner_text())

    def test_counselor_chat_looks_like_a_messenger_thread(self):
        counselor = create_counselor('browserchatcounselor')
        student = create_student('browserchatstudent', program='Psychology', year_level='2')

        self.page.goto(f'{self.live_server_url}/accounts/login/')
        self.page.locator('input[name="username"]').fill(student.username)
        self.page.locator('input[name="password"]').fill('StrongPass123!')
        self.page.get_by_role('button', name='Log in').click()
        self.page.wait_for_url(f'{self.live_server_url}/')

        self.page.goto(f'{self.live_server_url}/counselor/contact/')
        self.page.locator('textarea[name="message"]').fill('I need help figuring out my schedule.')
        self.page.get_by_role('button', name='Send message').click()

        self.assertGreater(self.page.locator('.chat-row--outgoing').count(), 0)

        messages = self.page.locator('#chat-messages')
        outgoing_bubble = self.page.locator('.chat-row--outgoing .chat-bubble').first
        messages_box = messages.bounding_box()
        outgoing_box = outgoing_bubble.bounding_box()
        self.assertIsNotNone(messages_box)
        self.assertIsNotNone(outgoing_box)
        self.assertGreater(outgoing_box['x'], messages_box['x'] + (messages_box['width'] * 0.35))

        thread = student.contact_requests.first()
        self.context.clear_cookies()

        self.page.goto(f'{self.live_server_url}/accounts/login/')
        self.page.locator('input[name="username"]').fill(counselor.username)
        self.page.locator('input[name="password"]').fill('StrongPass123!')
        self.page.get_by_role('button', name='Log in').click()
        self.page.wait_for_url(f'{self.live_server_url}/')

        self.page.goto(f'{self.live_server_url}/counselor/contact/{thread.id}/')
        self.page.get_by_role('button', name='Claim request').click()
        self.page.wait_for_url(f'{self.live_server_url}/counselor/contact/{thread.id}/')
        incoming_bubble = self.page.locator('.chat-row--incoming .chat-bubble').first
        incoming_box = incoming_bubble.bounding_box()
        messages_box = self.page.locator('#chat-messages').bounding_box()
        self.assertIsNotNone(incoming_box)
        self.assertIsNotNone(messages_box)
        self.assertLess(incoming_box['x'], messages_box['x'] + (messages_box['width'] * 0.45))

        self.page.locator('textarea[name="body"]').fill('I can help you plan a schedule that works better.')
        self.page.get_by_role('button', name='Send reply').click()
        self.page.wait_for_url(f'{self.live_server_url}/counselor/contact/{thread.id}/')

        outgoing_reply = self.page.locator('.chat-row--outgoing .chat-bubble').last
        reply_box = outgoing_reply.bounding_box()
        messages_box = self.page.locator('#chat-messages').bounding_box()
        self.assertIsNotNone(reply_box)
        self.assertIsNotNone(messages_box)
        self.assertGreater(reply_box['x'], messages_box['x'] + (messages_box['width'] * 0.35))
