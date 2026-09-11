import json
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from intake.models import IntakeDraft, IntakeResponse, Result
from intake.views import _generate_mbiss_result

from .helpers import create_result_for_student, create_student


class IntakeFlowTests(TestCase):
    def setUp(self):
        self.student = create_student('intakestudent')

    def test_student_can_submit_intake_and_create_result_pipeline(self):
        self.client.login(username='intakestudent', password='StrongPass123!')
        response = self.client.post(
            reverse('intake:create'),
            {
                'workload_hours': 12,
                'sleep_hours': 4,
                'sleep_quality': 'Poor',
                'study_habit_score': 2,
                'social_media_hours': 5,
                'deadline_pressure': 9,
                'class_load': 8,
                'mood_energy': 3,
                'exercise_minutes': 10,
                'sleep_consistency': 3,
                'mbiss_exhaustion_1': 6,
                'mbiss_exhaustion_2': 6,
                'mbiss_exhaustion_3': 5,
                'mbiss_exhaustion_4': 6,
                'mbiss_exhaustion_5': 5,
                'mbiss_cynicism_1': 5,
                'mbiss_cynicism_2': 5,
                'mbiss_cynicism_3': 4,
                'mbiss_cynicism_4': 5,
                'mbiss_academic_efficacy_1': 3,
                'mbiss_academic_efficacy_2': 3,
                'mbiss_academic_efficacy_3': 4,
                'mbiss_academic_efficacy_4': 3,
                'mbiss_academic_efficacy_5': 4,
                'mbiss_academic_efficacy_6': 3,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(IntakeResponse.objects.filter(student=self.student).count(), 1)
        result = Result.objects.get(intake_response__student=self.student)
        self.assertIn(result.stress_level, {'Low', 'Moderate', 'High'})
        self.assertGreater(result.recommendations.count(), 0)

    def test_result_band_is_based_on_mbiss_subscales(self):
        intake, _ = create_result_for_student(self.student, stress_level='High')
        for field in [
            'mbiss_exhaustion_1', 'mbiss_exhaustion_2', 'mbiss_exhaustion_3',
            'mbiss_exhaustion_4', 'mbiss_exhaustion_5', 'mbiss_cynicism_1',
            'mbiss_cynicism_2', 'mbiss_cynicism_3', 'mbiss_cynicism_4',
        ]:
            setattr(intake, field, 1)
        for field in [
            'mbiss_academic_efficacy_1', 'mbiss_academic_efficacy_2',
            'mbiss_academic_efficacy_3', 'mbiss_academic_efficacy_4',
            'mbiss_academic_efficacy_5', 'mbiss_academic_efficacy_6',
        ]:
            setattr(intake, field, 7)
        intake.save()

        low_result = _generate_mbiss_result(intake)

        self.assertEqual(low_result[0], 'Low')

        intake.mbiss_exhaustion_1 = 7
        intake.mbiss_exhaustion_2 = 7
        intake.mbiss_exhaustion_3 = 7
        intake.mbiss_exhaustion_4 = 7
        intake.mbiss_exhaustion_5 = 7
        intake.mbiss_cynicism_1 = 7
        intake.mbiss_cynicism_2 = 7
        intake.mbiss_cynicism_3 = 7
        intake.mbiss_cynicism_4 = 7
        intake.mbiss_academic_efficacy_1 = 1
        intake.mbiss_academic_efficacy_2 = 1
        intake.mbiss_academic_efficacy_3 = 1
        intake.mbiss_academic_efficacy_4 = 1
        intake.mbiss_academic_efficacy_5 = 1
        intake.mbiss_academic_efficacy_6 = 1
        intake.save()

        high_result = _generate_mbiss_result(intake)

        self.assertEqual(high_result[0], 'High')

    def test_result_page_shows_latest_result_only(self):
        create_result_for_student(self.student, stress_level='Low', days_ago=4)
        create_result_for_student(self.student, stress_level='High', days_ago=1)
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:result'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'High')
        self.assertNotContains(response, 'Low', status_code=200)

    def test_result_page_separates_pending_prediction_from_mbiss_result(self):
        create_result_for_student(self.student, stress_level='Moderate')
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:result'))

        self.assertContains(response, 'Burnout question scores')
        self.assertContains(response, 'Predictive support signal')
        self.assertContains(response, 'enough approved data and a trained model')
        self.assertNotContains(response, 'Low:')

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
            'workload_hours': '12',
            'sleep_hours': '6',
            'sleep_quality': 'Fair',
            'study_habit_score': '5',
        }

        response = self.client.post(
            reverse('intake:drafts'),
            data=json.dumps({'payload': payload}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        draft = IntakeDraft.objects.get(student=self.student)
        self.assertEqual(draft.payload['workload_hours'], '12')
        self.assertEqual(draft.payload['sleep_quality'], 'Fair')

    def test_intake_form_restores_saved_draft_on_load(self):
        IntakeDraft.objects.create(student=self.student, payload={
            'workload_hours': '8',
            'sleep_hours': '7',
            'sleep_quality': 'Good',
            'study_habit_score': '6',
        })
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="8"')
        self.assertContains(response, 'Good')

    def test_intake_page_uses_redesigned_sections_and_guidance(self):
        self.client.login(username='intakestudent', password='StrongPass123!')

        response = self.client.get(reverse('intake:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'How you\'re managing right now')
        self.assertContains(response, 'School demands')
        self.assertContains(response, 'Recovery and rest')
        self.assertContains(response, 'Focus and energy')
        self.assertContains(response, 'Choose the option that feels most accurate for the past week')

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
