from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counselor', '0011_studentcontactrequest_dashboard_reviewed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmessage',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
