from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import StudentProfile, UserNotification
from accounts.notifications import notify_user
from counselor.models import CounselorDigestDelivery
from intake.models import Result


class Command(BaseCommand):
    help = 'Send each counselor one weekly in-app digest of students with elevated check-in results.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        week_start = today - timedelta(days=7)
        week_end = today
        week_start_dt = timezone.make_aware(datetime.combine(week_start, time.min))
        week_end_dt = timezone.make_aware(datetime.combine(week_end, time.min))

        student_ids = StudentProfile.objects.filter(
            is_counselor=False,
            is_teacher=False,
        ).values_list('user_id', flat=True)
        elevated_students = []
        for student in get_user_model().objects.filter(id__in=student_ids).iterator():
            latest = Result.objects.filter(
                intake_response__student=student,
                archived_at__isnull=True,
            ).order_by('-created_at').first()
            if (
                latest
                and latest.stress_level == 'Moderate'
                and week_start_dt <= latest.created_at < week_end_dt
            ):
                elevated_students.append(student)

        counselors = get_user_model().objects.filter(studentprofile__is_counselor=True)
        sent_count = 0
        for counselor in counselors:
            if not elevated_students:
                continue
            try:
                with transaction.atomic():
                    CounselorDigestDelivery.objects.create(counselor=counselor, week_start=week_start)
            except IntegrityError:
                continue
            notify_user(
                counselor,
                kind=UserNotification.Kind.WEEKLY_DIGEST,
                title='Weekly elevated support update',
                body=f'{len(elevated_students)} students had an elevated check-in result last week. Sign in to StudentSense to review the dashboard.',
                target_url='/counselor/dashboard/',
            )
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Weekly elevated digest complete. {len(elevated_students)} students, {sent_count} counselor notifications.'
        ))
