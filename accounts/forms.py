from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import StudentProfile


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    program = forms.CharField(max_length=100, required=True)
    year_level = forms.CharField(max_length=20, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'program', 'year_level')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                program=self.cleaned_data['program'],
                year_level=self.cleaned_data['year_level'],
            )
        return user
