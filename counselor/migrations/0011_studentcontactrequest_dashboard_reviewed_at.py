from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counselor', '0010_update_high_result_messages'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentcontactrequest',
            name='dashboard_reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
