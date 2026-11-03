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
    def test_intake_form_uses_one_to_five_likert_choices(self):
        form = IntakeResponseForm()

        expected_choices = [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')]
        for index in range(1, 21):
            self.assertEqual(list(form.fields[f'q{index}'].widget.choices), expected_choices)

    def test_intake_form_includes_expanded_fields(self):
        form = IntakeResponseForm()

        self.assertEqual(
            list(form.fields.keys()),
            [
                *[f'q{i}' for i in range(1, 21)],
                'supporting_file',
                'presenting_concern',
            ],
        )

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
