import json
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from intake.models import IntakeDraft, IntakeResponse, Result
from counselor.models import ContactMessage, StudentContactRequest
from accounts.models import UserNotification
from intake.views import _generate_survey_result

from .helpers import create_result_for_student, create_student


class IntakeFlowTests(TestCase):
    def setUp(self):
        self.student = create_student('intakestudent')

    def test_student_can_submit_intake_and_create_result_pipeline(self):
        self.client.login(username='intakestudent', password='StrongPass123!')
        response = self.client.post(
            reverse('intake:create'),
            {f'q{i}': 5 for i in range(1, 21)},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntakeResponse.objects.filter(student=self.student).count(), 1)
        result = Result.objects.get(intake_response__student=self.student)
        self.assertIn(result.stress_level, {'Low', 'Moderate', 'High'})
        self.assertGreater(result.recommendations.count(), 0)
        self.assertEqual(result.stress_level, 'High')
        if result.stress_level == 'High':
            urgent_request = StudentContactRequest.objects.get(student=self.student)
            self.assertEqual(urgent_request.priority, StudentContactRequest.Priority.URGENT)
            self.assertTrue(urgent_request.initiated_by_system)
            self.assertEqual(urgent_request.messages.first().sender, ContactMessage.Sender.SYSTEM)
            self.assertTrue(UserNotification.objects.filter(recipient=self.student, kind=UserNotification.Kind.URGENT_HELP).exists())

    def test_result_band_is_based_on_survey_blocks(self):
        intake, _ = create_result_for_student(self.student, stress_level='High')
        for i in range(1, 21):
            setattr(intake, f'q{i}', 1)
        intake.save()

        low_result = _generate_survey_result(intake)

        self.assertEqual(low_result[0], 'Low')

        for i in range(1, 21):
            setattr(intake, f'q{i}', 5)
        intake.save()

        high_result = _generate_survey_result(intake)

        self.assertEqual(high_result[0], 'High')

    def test_result_page_shows_latest_result_only(self):
        create_result_for_student(self.student, stress_level='Low', days_ago=4)
        create_result_for_student(self.student, stress_level='High', days_ago=1)
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:result'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="result-badge">High</span>', html=True)

    def test_result_page_shows_model_signal_separately_from_survey_result(self):
        create_result_for_student(self.student, stress_level='Moderate')
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:result'))

        self.assertContains(response, 'Check-in area scores')
        self.assertContains(response, 'Initial model support signal')
        self.assertContains(response, 'does not replace your check-in result')

    def test_result_page_shows_initial_model_signal(self):
        intake, _ = create_result_for_student(self.student, stress_level='High')
        for i in range(1, 21):
            setattr(intake, f'q{i}', 5)
        intake.save()
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:result'))

        self.assertContains(response, 'Initial model support signal')
        self.assertContains(response, 'generated response patterns')

    def test_history_lists_results_oldest_to_newest(self):
        create_result_for_student(self.student, stress_level='Low', days_ago=5)
        create_result_for_student(self.student, stress_level='Moderate', days_ago=3)
        create_result_for_student(self.student, stress_level='High', days_ago=1)
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:history'))

        self.assertEqual(response.status_code, 200)
        results = response.context['results']
        self.assertEqual([result.stress_level for result in results], ['Low', 'Moderate', 'High'])

    def test_history_shows_empty_state_for_new_student(self):
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No check-ins yet. Start your first check-in to begin tracking your progress.')

    def test_intake_page_shows_general_soft_prompt_before_any_submission(self):
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'We recommend checking in once a week.')
        self.assertContains(response, 'You can retake this anytime. Weekly check-ins are a good rhythm for tracking changes.')
        self.assertNotContains(response, 'Research behind these questions')

    def test_intake_page_uses_recent_checkin_prompt_after_submission(self):
        create_result_for_student(self.student, stress_level='Moderate', days_ago=3)
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'We recommend checking in once a week.')
        self.assertContains(response, 'You last checked in 3 days ago')

    def test_intake_page_no_longer_shows_research_references(self):
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Research behind these questions')
        self.assertNotContains(response, 'doi.org/10.1111/j.1745-6924.2008.00089.x')

    def test_history_page_shows_general_checkin_standard(self):
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'We recommend checking in once a week.')

    def test_draft_endpoint_persists_payload_for_logged_in_student(self):
        self.client.login(username='intakestudent', password='StrongPass123!')
        payload = {
            'q1': '4',
            'q2': '3',
        }

        response = self.client.post(
            reverse('intake:drafts'),
            data=json.dumps({'payload': payload}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        draft = IntakeDraft.objects.get(student=self.student)
        self.assertEqual(draft.payload['q1'], '4')
        self.assertEqual(draft.payload['q2'], '3')

    def test_intake_form_restores_saved_draft_on_load(self):
        IntakeDraft.objects.create(student=self.student, payload={
            'q1': '4',
            'q2': '5',
        })
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="4"')
        self.assertContains(response, 'value="5"')

    def test_intake_page_uses_redesigned_sections_and_guidance(self):
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Academic burnout')
        self.assertContains(response, 'Academic stress and workload')
        self.assertContains(response, 'Social media usage')
        self.assertContains(response, 'Sleep patterns and habits')
        self.assertContains(response, '1 = Never / Strongly Disagree')

    def test_student_can_download_own_supporting_file(self):
        intake, _ = create_result_for_student(self.student, stress_level='Moderate')
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            intake.supporting_file.save('support-notes.pdf', ContentFile(b'%PDF-1.4 test'))
            self.client.login(username='intakestudent', password='StrongPass123!')

            response = self.client.get(reverse('intake:supporting_file_download', args=[intake.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_student_cannot_download_another_students_supporting_file(self):
        other_student = create_student('otherstudent')
        intake, _ = create_result_for_student(other_student, stress_level='Moderate')
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            intake.supporting_file.save('support-notes.pdf', ContentFile(b'%PDF-1.4 test'))
            self.client.login(username='intakestudent', password='StrongPass123!')

            response = self.client.get(reverse('intake:supporting_file_download', args=[intake.id]))

        self.assertEqual(response.status_code, 403)
