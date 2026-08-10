from django.contrib.auth.models import User
from django.db import models


class IntakeDraft(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='intake_draft')
    payload = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Draft for {self.student.username}"


class IntakeResponse(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intakes')
    workload_hours = models.PositiveIntegerField()
    sleep_hours = models.PositiveIntegerField()
    sleep_quality = models.CharField(max_length=50)
    study_habit_score = models.PositiveIntegerField()
    social_media_hours = models.PositiveIntegerField()
    deadline_pressure = models.PositiveIntegerField(default=5)
    class_load = models.PositiveIntegerField(default=5)
    mood_energy = models.PositiveIntegerField(default=5)
    exercise_minutes = models.PositiveIntegerField(default=30)
    sleep_consistency = models.PositiveIntegerField(default=5)
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Intake for {self.student.username}"


class Result(models.Model):
    intake_response = models.OneToOneField(IntakeResponse, on_delete=models.CASCADE, related_name='result')
    stress_level = models.CharField(max_length=20)
    factors = models.TextField(default='[]')
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stress_level} result"
