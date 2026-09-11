from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from pathlib import Path


MAX_SUPPORTING_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_SUPPORTING_FILE_TYPES = {
    '.pdf': {'application/pdf'},
    '.doc': {'application/msword'},
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    '.txt': {'text/plain'},
    '.jpg': {'image/jpeg'},
    '.png': {'image/png'},
}


def validate_supporting_file(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()
    allowed_mime_types = ALLOWED_SUPPORTING_FILE_TYPES.get(extension)
    if not allowed_mime_types:
        raise ValidationError('Upload a PDF, DOC, DOCX, TXT, JPG, or PNG file.')
    if uploaded_file.size > MAX_SUPPORTING_FILE_SIZE:
        raise ValidationError('Supporting files must be 50 MB or smaller.')
    content_type = getattr(uploaded_file, 'content_type', None)
    if content_type is None:
        content_type = getattr(getattr(uploaded_file, 'file', None), 'content_type', None)
    if content_type not in allowed_mime_types:
        raise ValidationError('The file type does not match its extension.')


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
    mbiss_exhaustion_1 = models.PositiveSmallIntegerField(default=4)
    mbiss_exhaustion_2 = models.PositiveSmallIntegerField(default=4)
    mbiss_exhaustion_3 = models.PositiveSmallIntegerField(default=4)
    mbiss_exhaustion_4 = models.PositiveSmallIntegerField(default=4)
    mbiss_exhaustion_5 = models.PositiveSmallIntegerField(default=4)
    mbiss_cynicism_1 = models.PositiveSmallIntegerField(default=4)
    mbiss_cynicism_2 = models.PositiveSmallIntegerField(default=4)
    mbiss_cynicism_3 = models.PositiveSmallIntegerField(default=4)
    mbiss_cynicism_4 = models.PositiveSmallIntegerField(default=4)
    mbiss_academic_efficacy_1 = models.PositiveSmallIntegerField(default=4)
    mbiss_academic_efficacy_2 = models.PositiveSmallIntegerField(default=4)
    mbiss_academic_efficacy_3 = models.PositiveSmallIntegerField(default=4)
    mbiss_academic_efficacy_4 = models.PositiveSmallIntegerField(default=4)
    mbiss_academic_efficacy_5 = models.PositiveSmallIntegerField(default=4)
    mbiss_academic_efficacy_6 = models.PositiveSmallIntegerField(default=4)
    supporting_file = models.FileField(
        upload_to='student_uploads/%Y/%m/%d/',
        blank=True,
        validators=[validate_supporting_file],
    )
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Intake for {self.student.username}"

    @property
    def mbiss_exhaustion_score(self):
        return sum(getattr(self, f'mbiss_exhaustion_{i}') for i in range(1, 6))

    @property
    def mbiss_cynicism_score(self):
        return sum(getattr(self, f'mbiss_cynicism_{i}') for i in range(1, 5))

    @property
    def mbiss_academic_efficacy_score(self):
        return sum(getattr(self, f'mbiss_academic_efficacy_{i}') for i in range(1, 7))

    @property
    def mbiss_total_score(self):
        return self.mbiss_exhaustion_score + self.mbiss_cynicism_score + self.mbiss_academic_efficacy_score


class Result(models.Model):
    intake_response = models.OneToOneField(IntakeResponse, on_delete=models.CASCADE, related_name='result')
    stress_level = models.CharField(max_length=20)
    factors = models.TextField(default='[]')
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_results',
    )

    def __str__(self):
        return f"{self.stress_level} result"
