from django.contrib import admin

from .models import IntakeResponse, Result


@admin.register(IntakeResponse)
class IntakeResponseAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'workload_hours',
        'sleep_hours',
        'sleep_quality',
        'deadline_pressure',
        'class_load',
        'mood_energy',
        'exercise_minutes',
        'sleep_consistency',
        'date_submitted',
    )


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('intake_response', 'stress_level', 'created_at')
