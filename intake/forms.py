from django import forms

from .models import IntakeResponse


LIKERT_CHOICES = [
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
]

SURVEY_BLOCKS = [
    (
        'Academic burnout (CBI-Student Version)',
        'How often have these experiences applied to your school life recently?',
        [f'q{i}' for i in range(1, 6)],
    ),
    (
        'Academic stress and workload (PAS Subset)',
        'How often have academic demands felt this difficult recently?',
        [f'q{i}' for i in range(6, 11)],
    ),
    (
        'Social media usage (SMAS-6)',
        'How often have these social media experiences affected you recently?',
        [f'q{i}' for i in range(11, 17)],
    ),
    (
        'Sleep patterns and habits (Modified Behavioral Sleep Index)',
        'How often have these sleep patterns or habits occurred recently?',
        [f'q{i}' for i in range(17, 21)],
    ),
]

QUESTION_LABELS = {
    'q1': 'How often do you feel physically tired from your schoolwork?',
    'q2': 'How often do you feel emotionally drained by your studies?',
    'q3': 'How often do you think, "I can\'t take school anymore"?',
    'q4': 'How often do you feel weak or worn out at the end of a school day?',
    'q5': 'How often do you dread going to your classes?',
    'q6': 'How often do you feel overwhelmed by the amount of homework given?',
    'q7': 'How often do you feel you lack enough time to prepare for exams?',
    'q8': 'How often do you struggle to keep up with your weekly study workload?',
    'q9': 'How often do you feel extreme pressure regarding your grades?',
    'q10': 'How often does your class schedule make you feel overwhelmed?',
    'q11': 'I spend more time on social media than I intend to.',
    'q12': 'I feel anxious or restless when I cannot check my notifications.',
    'q13': 'I have tried to cut down my social media use but failed.',
    'q14': 'I neglect my hobbies or school activities to spend time on social media.',
    'q15': 'I lose sleep because I am scrolling on social media late at night.',
    'q16': 'My school performance or study habits have suffered because of social media.',
    'q17': 'How often do you get less than 6 hours of sleep on a school night?',
    'q18': 'How often do you have trouble falling asleep within 30 minutes of going to bed?',
    'q19': 'How often do you wake up in the middle of the night and struggle to fall back asleep?',
    'q20': 'How often do you use your phone or computer while lying in bed immediately before sleeping?',
}


class IntakeResponseForm(forms.ModelForm):
    class Meta:
        model = IntakeResponse
        fields = [
            *[f'q{i}' for i in range(1, 21)],
            'supporting_file',
            'presenting_concern',
        ]
        labels = {
            'supporting_file': 'Optional supporting file',
            'presenting_concern': 'What is on your mind right now? (optional)',
            **QUESTION_LABELS,
        }
        widgets = {
            **{
                f'q{i}': forms.RadioSelect(choices=LIKERT_CHOICES)
                for i in range(1, 21)
            },
            'supporting_file': forms.ClearableFileInput(attrs={
                'accept': '.pdf,.doc,.docx,.txt,.jpg,.png',
            }),
            'presenting_concern': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share anything you would like your counselor to know about how you are feeling.',
            }),
        }

    @property
    def survey_blocks(self):
        return [
            (title, description, [self[name] for name in field_names])
            for title, description, field_names in SURVEY_BLOCKS
        ]
