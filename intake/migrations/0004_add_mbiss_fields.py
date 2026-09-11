from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0003_intakedraft'),
    ]

    operations = [
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_1',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_2',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_3',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_4',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_exhaustion_5',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_cynicism_1',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_cynicism_2',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_cynicism_3',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_cynicism_4',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_1',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_2',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_3',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_4',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_5',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='intakeresponse',
            name='mbiss_academic_efficacy_6',
            field=models.PositiveSmallIntegerField(default=4),
        ),
    ]
