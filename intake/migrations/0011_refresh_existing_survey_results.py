import json

from django.db import migrations


GUIDANCE = {
    'academic burnout': 'Try a short breathing exercise, plan brief rest breaks, and talk with student support if exhaustion continues.',
    'academic stress and workload': 'Break schoolwork into smaller steps, prioritize deadlines, and ask a teacher or counselor for help with workload pressure.',
    'social media usage': 'Set a small notification-free study window and protect your sleep from late-night scrolling.',
    'sleep patterns and habits': 'Try a consistent wind-down routine and keep phones and computers away from your bed before sleep.',
}


def survey_band(score, item_count):
    minimum = item_count
    maximum = item_count * 5
    third = (maximum - minimum) / 3
    if score <= minimum + third:
        return 'Low'
    if score <= minimum + (third * 2):
        return 'Moderate'
    return 'High'


def refresh_results(apps, schema_editor):
    Result = apps.get_model('intake', 'Result')
    Recommendation = apps.get_model('recommendations', 'Recommendation')

    for result in Result.objects.select_related('intake_response').all():
        intake = result.intake_response
        scores = {
            'academic burnout': sum(getattr(intake, f'q{i}') for i in range(1, 6)),
            'academic stress and workload': sum(getattr(intake, f'q{i}') for i in range(6, 11)),
            'social media usage': sum(getattr(intake, f'q{i}') for i in range(11, 17)),
            'sleep patterns and habits': sum(getattr(intake, f'q{i}') for i in range(17, 21)),
        }
        counts = {
            'academic burnout': 5,
            'academic stress and workload': 5,
            'social media usage': 6,
            'sleep patterns and habits': 4,
        }
        bands = {
            name: survey_band(score, counts[name])
            for name, score in scores.items()
        }
        high_concern = [name for name, band in bands.items() if band == 'High']
        moderate_concern = [name for name, band in bands.items() if band == 'Moderate']
        if len(high_concern) >= 2 or (
            bands['academic burnout'] == 'High'
            and bands['academic stress and workload'] in {'Moderate', 'High'}
        ):
            stress_level = 'High'
        elif high_concern or len(moderate_concern) >= 2:
            stress_level = 'Moderate'
        else:
            stress_level = 'Low'

        factors = [name for name, band in bands.items() if band in {'Moderate', 'High'}]
        if stress_level == 'High':
            summary = 'Your responses show elevated concern across multiple areas of academic wellbeing.'
        elif stress_level == 'Moderate':
            summary = 'Your responses show some areas of academic wellbeing worth noticing.'
        else:
            summary = 'Your responses do not show elevated concern across the four measured areas.'

        result.stress_level = stress_level
        result.factors = json.dumps(factors)
        result.summary = summary
        result.save(update_fields=['stress_level', 'factors', 'summary'])

        Recommendation.objects.filter(result=result).delete()
        Recommendation.objects.bulk_create([
            Recommendation(
                result=result,
                factor_name=factor,
                tip_text=GUIDANCE[factor],
            )
            for factor in factors
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0010_remove_legacy_survey_fields'),
        ('recommendations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(refresh_results, migrations.RunPython.noop),
    ]
