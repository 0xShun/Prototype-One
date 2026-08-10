from django.contrib.auth.models import User
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    program = models.CharField(max_length=100, blank=True)
    year_level = models.CharField(max_length=20, blank=True)
    is_counselor = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
