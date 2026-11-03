from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    program = models.CharField(max_length=100, blank=True)
    year_level = models.CharField(max_length=20, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    section = models.CharField(max_length=50, blank=True)
    is_counselor = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_teacher_approved = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~(Q(is_counselor=True) & Q(is_teacher=True)),
                name='profile_not_counselor_and_teacher',
            ),
        ]

    def __str__(self):
        return self.user.username


class UserNotification(models.Model):
    class Kind(models.TextChoices):
        REFERRAL = 'Referral', 'Referral'
        URGENT_HELP = 'Urgent help', 'Urgent help'
        APPOINTMENT = 'Appointment', 'Appointment'
        CONTACT_REQUEST = 'Contact request', 'Contact request'
        WEEKLY_DIGEST = 'Weekly digest', 'Weekly digest'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_sense_notifications')
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=160)
    body = models.TextField()
    target_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])


class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(unique=True, max_length=1000)
    p256dh = models.TextField()
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
