from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.forms import StudentRegistrationForm
from intake.forms import IntakeResponseForm
from intake.models import IntakeResponse, Result
from recommendations.models import Recommendation

from .helpers import create_result_for_student, create_student


class RegistrationFormTests(TestCase):
    def test_registration_form_validates_required_student_fields(self):
        form = StudentRegistrationForm(
            data={
                'username': 'newstudent',
                'email': 'newstudent@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'program': 'Computer Science',
                'year_level': '2',
            }
        )

        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, 'newstudent')
        self.assertEqual(user.studentprofile.program, 'Computer Science')

    def test_registration_form_requires_profile_fields(self):
        form = StudentRegistrationForm(
            data={
                'username': 'missingprofile',
                'email': 'missingprofile@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('program', form.errors)
        self.assertIn('year_level', form.errors)


class IntakeFormTests(TestCase):
    def test_intake_form_help_texts_are_plain_and_example_based(self):
        form = IntakeResponseForm()

        self.assertIn('1 = very unorganized and inconsistent', form.fields['study_habit_score'].help_text)
        self.assertIn('2 = mostly unorganized', form.fields['study_habit_score'].help_text)
        self.assertIn('3 = weak', form.fields['study_habit_score'].help_text)
        self.assertIn('4 = a little weak', form.fields['study_habit_score'].help_text)
        self.assertIn('5 = average', form.fields['study_habit_score'].help_text)
        self.assertIn('6 = somewhat organized', form.fields['study_habit_score'].help_text)
        self.assertIn('7 = organized', form.fields['study_habit_score'].help_text)
        self.assertIn('8 = very organized', form.fields['study_habit_score'].help_text)
        self.assertIn('9 = extremely organized', form.fields['study_habit_score'].help_text)
        self.assertIn('10 = perfectly consistent', form.fields['study_habit_score'].help_text)

        self.assertIn('1 = almost no deadlines', form.fields['deadline_pressure'].help_text)
        self.assertIn('2 = very few deadlines', form.fields['deadline_pressure'].help_text)
        self.assertIn('3 = a light deadline load', form.fields['deadline_pressure'].help_text)
        self.assertIn('4 = a few deadlines', form.fields['deadline_pressure'].help_text)
        self.assertIn('5 = a moderate deadline load', form.fields['deadline_pressure'].help_text)
        self.assertIn('6 = several deadlines', form.fields['deadline_pressure'].help_text)
        self.assertIn('7 = a busy deadline load', form.fields['deadline_pressure'].help_text)
        self.assertIn('8 = a lot of deadline pressure', form.fields['deadline_pressure'].help_text)
        self.assertIn('9 = very heavy pressure', form.fields['deadline_pressure'].help_text)
        self.assertIn('10 = constant deadline pressure', form.fields['deadline_pressure'].help_text)

        self.assertIn('1 = a very light schedule', form.fields['class_load'].help_text)
        self.assertIn('2 = a light schedule', form.fields['class_load'].help_text)
        self.assertIn('3 = slightly light', form.fields['class_load'].help_text)
        self.assertIn('4 = a little light', form.fields['class_load'].help_text)
        self.assertIn('5 = a moderate schedule', form.fields['class_load'].help_text)
        self.assertIn('6 = somewhat full', form.fields['class_load'].help_text)
        self.assertIn('7 = full', form.fields['class_load'].help_text)
        self.assertIn('8 = very full', form.fields['class_load'].help_text)
        self.assertIn('9 = overloaded', form.fields['class_load'].help_text)
        self.assertIn('10 = extremely overloaded', form.fields['class_load'].help_text)

        self.assertIn('1 = very low mood and energy', form.fields['mood_energy'].help_text)
        self.assertIn('2 = low mood and energy', form.fields['mood_energy'].help_text)
        self.assertIn('3 = below average', form.fields['mood_energy'].help_text)
        self.assertIn('4 = somewhat low', form.fields['mood_energy'].help_text)
        self.assertIn('5 = average', form.fields['mood_energy'].help_text)
        self.assertIn('6 = somewhat good', form.fields['mood_energy'].help_text)
        self.assertIn('7 = good', form.fields['mood_energy'].help_text)
        self.assertIn('8 = very good', form.fields['mood_energy'].help_text)
        self.assertIn('9 = excellent', form.fields['mood_energy'].help_text)
        self.assertIn('10 = great mood and energy all around', form.fields['mood_energy'].help_text)

        self.assertIn('1 = your sleep times change a lot', form.fields['sleep_consistency'].help_text)
        self.assertIn('2 = very irregular', form.fields['sleep_consistency'].help_text)
        self.assertIn('3 = irregular', form.fields['sleep_consistency'].help_text)
        self.assertIn('4 = somewhat irregular', form.fields['sleep_consistency'].help_text)
        self.assertIn('5 = average', form.fields['sleep_consistency'].help_text)
        self.assertIn('6 = somewhat regular', form.fields['sleep_consistency'].help_text)
        self.assertIn('7 = regular', form.fields['sleep_consistency'].help_text)
        self.assertIn('8 = very regular', form.fields['sleep_consistency'].help_text)
        self.assertIn('9 = almost always the same', form.fields['sleep_consistency'].help_text)
        self.assertIn('10 = extremely consistent sleep times', form.fields['sleep_consistency'].help_text)

    def test_intake_form_includes_expanded_fields(self):
        form = IntakeResponseForm()

        self.assertEqual(
            list(form.fields.keys()),
            [
                'workload_hours',
                'sleep_hours',
                'sleep_quality',
                'study_habit_score',
                'social_media_hours',
                'deadline_pressure',
                'class_load',
                'mood_energy',
                'exercise_minutes',
                'sleep_consistency',
                'mbiss_exhaustion_1',
                'mbiss_exhaustion_2',
                'mbiss_exhaustion_3',
                'mbiss_exhaustion_4',
                'mbiss_exhaustion_5',
                'mbiss_cynicism_1',
                'mbiss_cynicism_2',
                'mbiss_cynicism_3',
                'mbiss_cynicism_4',
                'mbiss_academic_efficacy_1',
                'mbiss_academic_efficacy_2',
                'mbiss_academic_efficacy_3',
                'mbiss_academic_efficacy_4',
                'mbiss_academic_efficacy_5',
                'mbiss_academic_efficacy_6',
                'supporting_file',
            ],
        )

    def test_intake_form_sleep_quality_choices_are_constrained(self):
        form = IntakeResponseForm()

        choice_values = [value for value, _ in form.fields['sleep_quality'].widget.choices]
        self.assertEqual(choice_values, ['Good', 'Fair', 'Poor'])

    def test_intake_form_accepts_allowed_supporting_file(self):
        form = IntakeResponseForm(files={
            'supporting_file': SimpleUploadedFile(
                'support-notes.pdf', b'%PDF-1.4 test', content_type='application/pdf'
            ),
        })

        self.assertNotIn('supporting_file', form.errors)

    def test_intake_form_accepts_jpg_and_png_supporting_files(self):
        for filename, content_type in [('photo.jpg', 'image/jpeg'), ('photo.png', 'image/png')]:
            form = IntakeResponseForm(files={
                'supporting_file': SimpleUploadedFile(filename, b'image', content_type=content_type),
            })

            self.assertNotIn('supporting_file', form.errors)

    def test_intake_form_rejects_disallowed_supporting_file(self):
        form = IntakeResponseForm(files={
            'supporting_file': SimpleUploadedFile(
                'unsafe.exe', b'MZ', content_type='application/x-msdownload'
            ),
        })

        self.assertIn('supporting_file', form.errors)


class ModelTests(TestCase):
    def test_string_representations_are_clear(self):
        student = create_student('stringstudent')
        intake, result = create_result_for_student(student, stress_level='Moderate')
        recommendation = Recommendation.objects.filter(result=result).first()

        self.assertEqual(str(intake), 'Intake for stringstudent')
        self.assertEqual(str(result), 'Moderate result')
        self.assertEqual(str(recommendation), recommendation.factor_name)

    def test_result_is_linked_to_intake_and_recommendations(self):
        student = create_student('linkedstudent')
        intake, result = create_result_for_student(student, stress_level='High', factor_names=['workload', 'sleep'])

        self.assertEqual(IntakeResponse.objects.get(pk=intake.pk).result.pk, result.pk)
        self.assertEqual(result.recommendations.count(), 2)

    def test_expanded_intake_fields_have_expected_defaults(self):
        student = create_student('defaultfieldstudent')
        intake, _ = create_result_for_student(student, stress_level='Moderate')

        self.assertGreaterEqual(intake.deadline_pressure, 1)
        self.assertGreaterEqual(intake.class_load, 1)
        self.assertGreaterEqual(intake.mood_energy, 1)
        self.assertGreaterEqual(intake.exercise_minutes, 0)
        self.assertGreaterEqual(intake.sleep_consistency, 1)
