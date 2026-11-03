from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0009_alter_intakeresponse_sleep_hours_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_1',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_2',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_3',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_4',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_5',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_6',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_cynicism_1',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_cynicism_2',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_cynicism_3',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_cynicism_4',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_1',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_2',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_3',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_4',
        ),
        migrations.RemoveField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_5',
        ),
    ]
