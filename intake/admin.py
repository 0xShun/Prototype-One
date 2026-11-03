from django.contrib import admin

from .models import IntakeResponse, Result


@admin.register(IntakeResponse)
class IntakeResponseAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'academic_burnout_score',
        'academic_stress_score',
        'social_media_score',
        'sleep_patterns_score',
        'date_submitted',
    )


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('intake_response', 'stress_level', 'created_at')
