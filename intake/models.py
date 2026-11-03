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
    q1 = models.PositiveSmallIntegerField(default=3)
    q2 = models.PositiveSmallIntegerField(default=3)
    q3 = models.PositiveSmallIntegerField(default=3)
    q4 = models.PositiveSmallIntegerField(default=3)
    q5 = models.PositiveSmallIntegerField(default=3)
    q6 = models.PositiveSmallIntegerField(default=3)
    q7 = models.PositiveSmallIntegerField(default=3)
    q8 = models.PositiveSmallIntegerField(default=3)
    q9 = models.PositiveSmallIntegerField(default=3)
    q10 = models.PositiveSmallIntegerField(default=3)
    q11 = models.PositiveSmallIntegerField(default=3)
    q12 = models.PositiveSmallIntegerField(default=3)
    q13 = models.PositiveSmallIntegerField(default=3)
    q14 = models.PositiveSmallIntegerField(default=3)
    q15 = models.PositiveSmallIntegerField(default=3)
    q16 = models.PositiveSmallIntegerField(default=3)
    q17 = models.PositiveSmallIntegerField(default=3)
    q18 = models.PositiveSmallIntegerField(default=3)
    q19 = models.PositiveSmallIntegerField(default=3)
    q20 = models.PositiveSmallIntegerField(default=3)
    workload_hours = models.PositiveIntegerField(default=0)
    sleep_hours = models.PositiveIntegerField(default=0)
    sleep_quality = models.CharField(max_length=50, default='')
    study_habit_score = models.PositiveIntegerField(default=3)
    social_media_hours = models.PositiveIntegerField(default=0)
    deadline_pressure = models.PositiveIntegerField(default=5)
    class_load = models.PositiveIntegerField(default=5)
    mood_energy = models.PositiveIntegerField(default=5)
    exercise_minutes = models.PositiveIntegerField(default=30)
    sleep_consistency = models.PositiveIntegerField(default=5)
    supporting_file = models.FileField(
        upload_to='student_uploads/%Y/%m/%d/',
        blank=True,
        validators=[validate_supporting_file],
    )
    presenting_concern = models.TextField(blank=True)
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Intake for {self.student.username}"

    def survey_block_score(self, start, end):
        return sum(getattr(self, f'q{i}') for i in range(start, end + 1))

    @property
    def academic_burnout_score(self):
        return self.survey_block_score(1, 5)

    @property
    def academic_stress_score(self):
        return self.survey_block_score(6, 10)

    @property
    def social_media_score(self):
        return self.survey_block_score(11, 16)

    @property
    def sleep_patterns_score(self):
        return self.survey_block_score(17, 20)

    @property
    def survey_total_score(self):
        return self.survey_block_score(1, 20)

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
