import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import StudentProfile
from intake.models import IntakeResponse, Result
from recommendations.models import Recommendation


User = get_user_model()


def create_student(
    username='student',
    password='StrongPass123!',
    email=None,
    program='Psychology',
    year_level='3',
):
    user = User.objects.create_user(
        username=username,
        email=email or f'{username}@example.com',
        password=password,
    )
    StudentProfile.objects.create(user=user, program=program, year_level=year_level)
    return user


def create_counselor(username='counselor', password='StrongPass123!'):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password=password,
    )
    StudentProfile.objects.create(user=user, is_counselor=True)
    return user


def create_result_for_student(
    student,
    stress_level='High',
    summary=None,
    factor_names=None,
    days_ago=0,
    workload_hours=None,
    sleep_hours=None,
    sleep_quality=None,
    study_habit_score=3,
    social_media_hours=4,
    deadline_pressure=None,
    class_load=None,
    mood_energy=None,
    exercise_minutes=None,
    sleep_consistency=None,
):
    payload_map = {
        'High': {
            'workload_hours': 12,
            'sleep_hours': 4,
            'sleep_quality': 'Poor',
            'deadline_pressure': 9,
            'class_load': 8,
            'mood_energy': 3,
            'exercise_minutes': 10,
            'sleep_consistency': 3,
            'factor_names': ['workload', 'sleep', 'deadlines', 'mood and energy'],
            'summary': 'Your workload, deadlines, and recovery signals point to a heavy stretch right now.',
        },
        'Moderate': {
            'workload_hours': 8,
            'sleep_hours': 6,
            'sleep_quality': 'Fair',
            'deadline_pressure': 6,
            'class_load': 6,
            'mood_energy': 5,
            'exercise_minutes': 20,
            'sleep_consistency': 5,
            'factor_names': ['sleep', 'deadlines', 'class load', 'mood and energy'],
            'summary': 'A few parts of your routine are starting to add strain, but there is room to adjust.',
        },
        'Low': {
            'workload_hours': 5,
            'sleep_hours': 8,
            'sleep_quality': 'Good',
            'deadline_pressure': 3,
            'class_load': 3,
            'mood_energy': 7,
            'exercise_minutes': 45,
            'sleep_consistency': 8,
            'factor_names': ['routine'],
            'summary': 'Your current pattern looks manageable and sustainable.',
        },
    }
    defaults = payload_map[stress_level]
    factor_names = factor_names or defaults['factor_names']
    summary = summary or defaults['summary']
    intake = IntakeResponse.objects.create(
        student=student,
        workload_hours=workload_hours if workload_hours is not None else defaults['workload_hours'],
        sleep_hours=sleep_hours if sleep_hours is not None else defaults['sleep_hours'],
        sleep_quality=sleep_quality if sleep_quality is not None else defaults['sleep_quality'],
        study_habit_score=study_habit_score,
        social_media_hours=social_media_hours,
        deadline_pressure=deadline_pressure if deadline_pressure is not None else defaults['deadline_pressure'],
        class_load=class_load if class_load is not None else defaults['class_load'],
        mood_energy=mood_energy if mood_energy is not None else defaults['mood_energy'],
        exercise_minutes=exercise_minutes if exercise_minutes is not None else defaults['exercise_minutes'],
        sleep_consistency=sleep_consistency if sleep_consistency is not None else defaults['sleep_consistency'],
    )

    if days_ago:
        timestamp = timezone.now() - timedelta(days=days_ago)
        IntakeResponse.objects.filter(pk=intake.pk).update(date_submitted=timestamp)

    result = Result.objects.create(
        intake_response=intake,
        stress_level=stress_level,
        factors=json.dumps(factor_names),
        summary=summary,
    )

    if days_ago:
        timestamp = timezone.now() - timedelta(days=days_ago)
        Result.objects.filter(pk=result.pk).update(created_at=timestamp)

    for factor in factor_names:
        recommendation = Recommendation.objects.create(
            result=result,
            factor_name=factor,
            tip_text='A small adjustment today can make the next week feel more manageable.',
        )
        if days_ago:
            Recommendation.objects.filter(pk=recommendation.pk).update(created_at=timestamp)

    return intake, result
