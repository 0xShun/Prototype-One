from django import forms

from .models import ContactMessage, CounselorNote, StudentContactRequest


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