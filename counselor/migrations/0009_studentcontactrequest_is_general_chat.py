from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counselor', '0008_counselordigestdelivery_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentcontactrequest',
            name='is_general_chat',
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE counselor_studentcontactrequest "
                "SET is_general_chat = 1 "
                "WHERE initiated_by_system = 1"
            ),
            reverse_sql=(
                "UPDATE counselor_studentcontactrequest "
                "SET is_general_chat = 0 "
                "WHERE initiated_by_system = 1"
            ),
        ),
    ]
