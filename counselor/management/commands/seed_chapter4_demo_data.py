import json
import secrets
from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import StudentProfile
from counselor.models import (
    AppointmentBooking,
    CounselorAvailability,
    ContactMessage,
    StudentContactRequest,
    TeacherReferral,
)
from intake.models import IntakeResponse, Result
from recommendations.models import Recommendation


User = get_user_model()
CHECKIN_LEVELS = (
    'Low',
    'Moderate',
    'Moderate',
    'High',
    'Moderate',
    'Low',
    'Moderate',
    'High',
    'Moderate',
    'Low',
    'Moderate',
    'High',
)


class Command(BaseCommand):
    help = 'Add clearly labeled synthetic Chapter 4 demo records to the local SQLite database.'

    def handle(self, *args, **options):
        self._require_local_database()
        from intake.views import _generate_survey_result, _recommendations_for_survey

        password = secrets.token_urlsafe(18)
        created_checkins = 0
        created_accounts = []

        with transaction.atomic():
            counselor, created = self._get_demo_user('counselor', 1, password)
            if created:
                created_accounts.append(counselor.username)
            students = []
            for number in range(1, 11):
                student, created = self._get_demo_user('student', number, password)
                students.append(student)
                if created:
                    created_accounts.append(student.username)
            teachers = []
            for number in range(1, 4):
                teacher, created = self._get_demo_user('teacher', number, password)
                teachers.append(teacher)
                if created:
                    created_accounts.append(teacher.username)

            today = timezone.localdate()
            this_monday = today - timedelta(days=today.weekday())
            first_monday = this_monday - timedelta(weeks=17)

            for student_index, student in enumerate(students):
                for week_index in range(18):
                    week_start = first_monday + timedelta(weeks=week_index)
                    for day_offset in (0, 3):
                        checkin_date = week_start + timedelta(days=day_offset)
                        if checkin_date > today:
                            continue
                        created_checkins += self._create_checkin(
                            student,
                            student_index,
                            week_index * 2 + (day_offset == 3),
                            checkin_date,
                            _generate_survey_result,
                            _recommendations_for_survey,
                        )

            self._create_conversations(students, counselor)
            self._create_referrals(students, teachers)
            self._create_appointments(students, counselor, first_monday)

        self.stdout.write(self.style.SUCCESS(
            f'Synthetic demo data is ready: 10 students, 3 teachers, 1 counselor; '
            f'{created_checkins} new check-ins added. Existing records were not deleted.'
        ))
        if created_accounts:
            self.stdout.write('Created demo accounts: ' + ', '.join(created_accounts))
            self.stdout.write(f'Temporary local demo password for those accounts: {password}')
        else:
            self.stdout.write('All demo accounts already exist; their passwords were not changed.')

    def _require_local_database(self):
        expected_path = (Path(settings.BASE_DIR) / 'db.sqlite3').resolve()
        configured_name = connection.settings_dict['NAME']
        configured_path = Path(configured_name).resolve() if configured_name != ':memory:' else None
        if not settings.DEBUG or connection.vendor != 'sqlite' or configured_path != expected_path:
            raise CommandError(
                'This command only runs with DEBUG enabled and the repository-local db.sqlite3 database.'
            )

    def _get_demo_user(self, role, number, password):
        if role == 'counselor':
            username = 'chapter4_demo_counselor'
            profile_values = {'is_counselor': True}
            email = 'chapter4-demo-counselor@example.invalid'
            first_name = 'Demo Counselor'
            last_name = 'Sample'
        else:
            username = f'chapter4_demo_{role}_{number:02d}'
            profile_values = {
                'is_teacher': role == 'teacher',
                'is_teacher_approved': role == 'teacher',
                'program': 'Demonstration',
                'year_level': 'Demo',
                'section': 'DEMO',
            }
            email = f'{username}@example.invalid'
            first_name = f'Demo {role.title()} {number:02d}'
            last_name = 'Sample'

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        if not created and user.email != email:
            raise CommandError(f'Refusing to change an existing non-demo account: {username}')
        if not created and (user.first_name != first_name or user.last_name != last_name):
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=['first_name', 'last_name'])

        profile, profile_created = StudentProfile.objects.get_or_create(
            user=user,
            defaults=profile_values,
        )
        if not profile_created and any(
            getattr(profile, field) != value
            for field, value in profile_values.items()
        ):
            raise CommandError(f'Refusing to change an existing non-demo profile: {username}')

        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user, created

    def _create_checkin(
        self,
        student,
        student_index,
        checkin_index,
        checkin_date,
        generate_result,
        recommendations_for_survey,
    ):
        if IntakeResponse.objects.filter(
            student=student,
            date_submitted__date=checkin_date,
        ).exists():
            return 0

        level = CHECKIN_LEVELS[(checkin_index + student_index) % len(CHECKIN_LEVELS)]
        if level == 'Low':
            response_values = [1 + ((student_index + checkin_index) % 2)] * 20
            context = (5, 8, 'Good', 8, 1, 2, 3, 8, 45, 8)
        elif level == 'Moderate':
            response_values = [3] * 10 + [1] * 10
            context = (8, 6, 'Fair', 5, 3, 6, 6, 5, 20, 5)
        else:
            response_values = [5] * 5 + [4] * 5 + [1] * 10
            context = (12, 4, 'Poor', 3, 5, 9, 8, 3, 10, 3)

        hour = 9 if checkin_index % 2 == 0 else 16
        submitted_at = timezone.make_aware(
            datetime.combine(checkin_date, time(hour=hour)),
        )
        intake = IntakeResponse.objects.create(
            student=student,
            **{f'q{index}': value for index, value in enumerate(response_values, start=1)},
            workload_hours=context[0],
            sleep_hours=context[1],
            sleep_quality=context[2],
            study_habit_score=context[3],
            social_media_hours=context[4],
            deadline_pressure=context[5],
            class_load=context[6],
            mood_energy=context[7],
            exercise_minutes=context[8],
            sleep_consistency=context[9],
            presenting_concern='Synthetic demonstration response for interface testing.',
        )
        IntakeResponse.objects.filter(pk=intake.pk).update(date_submitted=submitted_at)

        stress_level, factors, summary, _ = generate_result(intake)
        result = Result.objects.create(
            intake_response=intake,
            stress_level=stress_level,
            factors=json.dumps(factors),
            summary=summary,
        )
        Result.objects.filter(pk=result.pk).update(created_at=submitted_at)

        for factor, tip_text in recommendations_for_survey(factors):
            recommendation = Recommendation.objects.create(
                result=result,
                factor_name=factor,
                tip_text=tip_text,
            )
            Recommendation.objects.filter(pk=recommendation.pk).update(created_at=submitted_at)
        return 1

    def _create_conversations(self, students, counselor):
        for index, student in enumerate(students[:4]):
            priority = (
                StudentContactRequest.Priority.URGENT
                if index < 2
                else StudentContactRequest.Priority.ROUTINE
            )
            thread, _ = StudentContactRequest.objects.get_or_create(
                student=student,
                assigned_counselor=counselor,
                is_general_chat=True,
                defaults={
                    'priority': priority,
                    'initiated_by_system': True,
                    'message': 'Synthetic demonstration conversation for interface testing.',
                    'status': StudentContactRequest.Status.IN_PROGRESS,
                },
            )
            ContactMessage.objects.get_or_create(
                thread=thread,
                sender=ContactMessage.Sender.STUDENT,
                body='This is a simulated message for the Chapter 4 app demonstration.',
            )
            ContactMessage.objects.get_or_create(
                thread=thread,
                sender=ContactMessage.Sender.COUNSELOR,
                body='This is a simulated counselor reply for interface testing.',
            )

        support_request, _ = StudentContactRequest.objects.get_or_create(
            student=students[4],
            assigned_counselor=None,
            is_general_chat=False,
            message='Synthetic demonstration support request for interface testing.',
            defaults={
                'priority': StudentContactRequest.Priority.URGENT,
                'status': StudentContactRequest.Status.OPEN,
            },
        )
        ContactMessage.objects.get_or_create(
            thread=support_request,
            sender=ContactMessage.Sender.STUDENT,
            body='Synthetic demonstration support request for interface testing.',
        )

    def _create_referrals(self, students, teachers):
        reason = 'Synthetic demonstration referral for interface testing.'
        for index, student in enumerate(students[:3]):
            TeacherReferral.objects.get_or_create(
                student=student,
                teacher=teachers[index],
                reason=reason,
                defaults={'status': TeacherReferral.Status.NEW},
            )

    def _create_appointments(self, students, counselor, effective_from):
        schedules = (
            (CounselorAvailability.Weekday.MONDAY, time(hour=9), time(hour=10)),
            (CounselorAvailability.Weekday.WEDNESDAY, time(hour=13), time(hour=14)),
        )
        availability_rules = []
        for weekday, start_time, end_time in schedules:
            rule, _ = CounselorAvailability.objects.get_or_create(
                counselor=counselor,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                effective_from=effective_from,
                defaults={'is_active': True},
            )
            availability_rules.append(rule)

        today = timezone.localdate()
        days_until_monday = (0 - today.weekday()) % 7 or 7
        appointment_date = today + timedelta(days=days_until_monday)
        starts_at = timezone.make_aware(
            datetime.combine(appointment_date, schedules[0][1]),
        )
        ends_at = timezone.make_aware(
            datetime.combine(appointment_date, schedules[0][2]),
        )
        AppointmentBooking.objects.get_or_create(
            counselor=counselor,
            starts_at=starts_at,
            ends_at=ends_at,
            status=AppointmentBooking.Status.BOOKED,
            defaults={
                'student': students[0],
                'availability': availability_rules[0],
            },
        )
