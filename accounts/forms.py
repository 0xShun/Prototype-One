from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import StudentProfile


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    program = forms.CharField(max_length=100, required=True, label='Strand')
    year_level = forms.CharField(max_length=20, required=True)
    age = forms.IntegerField(min_value=10, max_value=100, required=False)
    section = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'program', 'year_level', 'age', 'section')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                program=self.cleaned_data['program'],
                year_level=self.cleaned_data['year_level'],
                age=self.cleaned_data.get('age'),
                section=self.cleaned_data.get('section', ''),
            )
        return user


class TeacherRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    phone_number = forms.CharField(max_length=30, required=True, label='Contact number')
    program = forms.CharField(max_length=100, required=True, label='Department or office')

    class Meta:
        model = User
        fields = (
            'username', 'first_name', 'last_name', 'email', 'password1', 'password2',
            'phone_number', 'program',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                program=self.cleaned_data['program'],
                phone_number=self.cleaned_data['phone_number'],
                is_teacher=True,
                is_teacher_approved=False,
            )
        return user
