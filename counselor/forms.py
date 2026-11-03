from django import forms
from django.contrib.auth import get_user_model

from .models import (
    CounselorAvailability,
    CounselorNote,
    CounselorUnavailableTime,
    ContactMessage,
    StudentContactRequest,
    TeacherReferral,
)


class StudentContactReplyForm(forms.Form):
    message = forms.CharField(
        label='Reply to this request',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Add more information or reply to the support conversation.',
        }),
    )


class CounselorNoteForm(forms.ModelForm):
    class Meta:
        model = CounselorNote
        fields = ['note']
        labels = {
            'note': 'Private note for this student',
        }
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write a private follow-up note for this student.'}),
        }


class StudentContactRequestForm(forms.ModelForm):
    class Meta:
        model = StudentContactRequest
        fields = ['message']
        labels = {
            'message': 'Message to student support',
        }
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Share what you need help with or what you would like the counselor to know.'}),
        }


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['body']
        labels = {
            'body': 'Message',
        }
        widgets = {
            'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a message...'}),
        }


class TeacherReferralForm(forms.ModelForm):
    class Meta:
        model = TeacherReferral
        fields = ['student', 'reason']
        labels = {'student': 'Student', 'reason': 'Reason for referral'}
        widgets = {'reason': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = get_user_model().objects.filter(
            studentprofile__is_counselor=False,
            studentprofile__is_teacher=False,
        ).order_by('last_name', 'first_name', 'username')
        self.fields['student'].label_from_instance = lambda user: (
            f'{user.get_full_name() or user.username} (Year {user.studentprofile.year_level}, {user.studentprofile.program})'
        )


class CounselorAvailabilityForm(forms.ModelForm):
    class Meta:
        model = CounselorAvailability
        fields = ['weekday', 'start_time', 'end_time', 'effective_from', 'effective_until']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'effective_from': forms.DateInput(attrs={'type': 'date'}),
            'effective_until': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, counselor=None, **kwargs):
        self.counselor = counselor
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if not self.counselor or not all(cleaned.get(key) for key in ('weekday', 'start_time', 'end_time', 'effective_from')):
            return cleaned
        until = cleaned.get('effective_until')
        overlaps = CounselorAvailability.objects.filter(counselor=self.counselor, weekday=cleaned['weekday'], is_active=True)
        if self.instance.pk:
            overlaps = overlaps.exclude(pk=self.instance.pk)
        for rule in overlaps:
            date_ranges_overlap = (until is None or rule.effective_from <= until) and (rule.effective_until is None or rule.effective_until >= cleaned['effective_from'])
            time_ranges_overlap = cleaned['start_time'] < rule.end_time and cleaned['end_time'] > rule.start_time
            if date_ranges_overlap and time_ranges_overlap:
                self.add_error(None, 'This recurring time overlaps another availability slot on that weekday.')
                break
        return cleaned


class CounselorUnavailableTimeForm(forms.ModelForm):
    class Meta:
        model = CounselorUnavailableTime
        fields = ['starts_at', 'ends_at', 'reason']
        widgets = {
            'starts_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }