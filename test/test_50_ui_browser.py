import os

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from playwright.sync_api import sync_playwright
from unittest.mock import patch

from .helpers import create_counselor, create_result_for_student, create_student


class BrowserFlowTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        launch_options = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
            launch_options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
        cls.browser = cls.playwright.chromium.launch(**launch_options)
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
        self.page.get_by_role('link', name='More').first.click()
        self.page.wait_for_url(f'{self.live_server_url}/more/')

    def login_as(self, username):
        self.context.clear_cookies()
        self.page.goto(f'{self.live_server_url}/accounts/login/')
        self.page.locator('input[name="username"]').fill(username)
        self.page.locator('input[name="password"]').fill('StrongPass123!')
        self.page.get_by_role('button', name='Log in').click()
        self.page.wait_for_url(f'{self.live_server_url}/')

    def test_mobile_urgent_sources_and_filters_open_exact_conversations(self):
        from counselor.models import StudentContactRequest

        counselor = create_counselor('browserurgentcounselor')
        request_student = create_student('browserurgentrequest')
        chat_student = create_student('browserurgentchat')
        checkin_student = create_student('browserhighcheckin')

        self.login_as(request_student.username)
        self.page.goto(f'{self.live_server_url}/counselor/urgent-help/')
        self.page.locator('textarea[name="message"]').fill('Urgent request from form')
        self.page.get_by_role('button', name='Send urgent request').click()
        request = StudentContactRequest.objects.get(student=request_student)

        self.login_as(chat_student.username)
        self.page.goto(f'{self.live_server_url}/counselor/messages/counselor/{counselor.id}/')
        self.page.get_by_role('button', name='Urgent help needed').click()
        chat = StudentContactRequest.objects.get(student=chat_student, assigned_counselor=counselor)

        self.login_as(checkin_student.username)
        self.page.goto(f'{self.live_server_url}/intake/new/')
        with patch('intake.views.random.choice', return_value=counselor):
            for start, end in ((1, 5), (6, 10), (11, 16), (17, 20)):
                for index in range(start, end + 1):
                    self.page.locator(f'input[name="q{index}"]').nth(4).check()
                self.page.get_by_role('button', name='Submit' if end == 20 else 'Next').click()
            self.page.wait_for_url(f'{self.live_server_url}/intake/result/')
        checkin = StudentContactRequest.objects.get(student=checkin_student, assigned_counselor=counselor)

        self.login_as(counselor.username)
        self.page.goto(f'{self.live_server_url}/counselor/dashboard/')
        self.page.get_by_label('Section').select_option('urgent')
        self.page.get_by_label('Support level').select_option('High')
        urgent_section = self.page.locator('[data-section="urgent"]')
        for student in (request_student, chat_student, checkin_student):
            self.assertTrue(urgent_section.locator('tr').filter(has_text=student.username).is_visible())
        self.assertFalse(self.page.locator('[data-section="attention"]').is_visible())
        self.page.get_by_label('Support level').select_option('Moderate')
        self.assertFalse(urgent_section.is_visible())
        self.assertTrue(self.page.locator('.filter-empty').is_visible())
        self.page.get_by_role('button', name='Reset').click()
        self.assertTrue(urgent_section.is_visible())

        for student, thread in ((request_student, request), (chat_student, chat), (checkin_student, checkin)):
            self.page.goto(f'{self.live_server_url}/counselor/dashboard/')
            self.page.get_by_label('Section').select_option('urgent')
            self.page.get_by_label('Support level').select_option('High')
            row = self.page.locator('[data-section="urgent"] tbody tr').filter(has_text=student.username)
            row.locator('button').click()
            self.page.wait_for_url(f'{self.live_server_url}/counselor/contact/{thread.id}/')
            self.assertIn(student.username, self.page.locator('.chat-room__header').inner_text())

    def test_mobile_conversation_bubbles_switch_sides_for_both_roles(self):
        counselor = create_counselor('bubblescounselor')
        student = create_student('bubblesstudent')
        self.login_as(student.username)
        self.page.goto(f'{self.live_server_url}/counselor/messages/counselor/{counselor.id}/')
        self.page.locator('textarea[name="message"]').fill('Student message for alignment')
        self.page.get_by_role('button', name='Send message').click()

        self.login_as(counselor.username)
        self.page.goto(f'{self.live_server_url}/counselor/messages/student/{student.id}/')
        self.page.locator('textarea[name="body"]').fill('Counselor message for alignment')
        self.page.get_by_role('button', name='Send message').click()
        for role, name in (('counselor', counselor.username), ('student', student.username)):
            self.login_as(name)
            url = (f'/counselor/messages/student/{student.id}/' if role == 'counselor'
                   else f'/counselor/messages/counselor/{counselor.id}/')
            self.page.goto(self.live_server_url + url)
            self.page.wait_for_timeout(300)
            student_row = self.page.locator('.chat-row').filter(has_text='Student message for alignment')
            counselor_row = self.page.locator('.chat-row').filter(has_text='Counselor message for alignment')
            self.assertIn('chat-row--outgoing' if role == 'student' else 'chat-row--incoming', student_row.get_attribute('class'))
            self.assertIn('chat-row--outgoing' if role == 'counselor' else 'chat-row--incoming', counselor_row.get_attribute('class'))
            student_box = student_row.locator('.chat-bubble').bounding_box()
            counselor_box = counselor_row.locator('.chat-bubble').bounding_box()
            if role == 'student':
                self.assertGreater(student_box['x'], counselor_box['x'])
            else:
                self.assertGreater(counselor_box['x'], student_box['x'])

    def test_public_home_page_renders_on_mobile(self):
        self.page.goto(f'{self.live_server_url}/')
        page_text = ' '.join(self.page.locator('body').inner_text().split())
        self.assertIn('Check in with yourself.', page_text)
        self.assertFalse(self.page.locator('.bottom-nav').count())
        self.assertFalse(self.page.locator('#nav-toggle').count())
        self.assertFalse(self.page.get_by_role('link', name='About').count())
        self.assertFalse(self.page.get_by_role('link', name='How To').count())
        self.assertIn('About the platform', self.page.locator('body').inner_text())
        self.assertIn('How to use it', self.page.locator('body').inner_text())

    def test_student_browser_flow_from_register_to_logout(self):
        username = 'browserstudent'
        self.page.goto(f'{self.live_server_url}/accounts/register/')
        self.page.locator('input[name="username"]').fill(username)
        self.page.locator('input[name="email"]').fill(f'{username}@example.com')
        self.page.locator('input[name="password1"]').fill('StrongPass123!')
        self.page.locator('input[name="password2"]').fill('StrongPass123!')
        self.assertFalse(self.page.locator('#strand-field').is_visible())
        self.page.locator('select[name="year_level"]').select_option('11')
        self.assertTrue(self.page.locator('#strand-field').is_visible())
        self.page.locator('select[name="program"]').select_option('STEM')
        self.page.locator('select[name="year_level"]').select_option('10')
        self.assertFalse(self.page.locator('#strand-field').is_visible())
        self.page.locator('select[name="year_level"]').select_option('11')
        self.page.locator('select[name="program"]').select_option('STEM')
        self.page.get_by_role('button', name='Register').click()
        self.page.wait_for_url(f'{self.live_server_url}/')

        self.page.goto(f'{self.live_server_url}/intake/new/')
        reminder_text = self.page.locator('.soft-reminder').first.inner_text()
        self.assertIn('We recommend checking in once a week', reminder_text)
        self.assertNotIn('Use this scale for every question', self.page.locator('body').inner_text())
        self.assertNotIn('Research behind these questions', self.page.locator('body').inner_text())

        for index in range(1, 6):
            self.page.locator(f'input[name="q{index}"]').nth(4).check()
        self.page.get_by_role('button', name='Next').click()

        for index in range(6, 11):
            self.page.locator(f'input[name="q{index}"]').nth(4).check()
        self.page.get_by_role('button', name='Next').click()

        for index in range(11, 17):
            self.page.locator(f'input[name="q{index}"]').nth(4).check()
        self.page.get_by_role('button', name='Next').click()

        for index in range(17, 21):
            self.page.locator(f'input[name="q{index}"]').nth(4).check()
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

        self.assertFalse(self.page.get_by_role('link', name='View full history').count())

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
