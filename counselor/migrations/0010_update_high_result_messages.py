from django.db import migrations


OLD_HIGH_RESULT_MESSAGE = (
    'StudentSense flagged this check-in for prompt counselor review based on its provisional survey support band. '
    'This is a screening prompt, not a diagnosis or emergency assessment.'
)
NEW_HIGH_RESULT_MESSAGE = "This student's check-in result is high and needs urgent assistance."


def update_high_result_messages(apps, schema_editor):
    ContactMessage = apps.get_model('counselor', 'ContactMessage')
    ContactMessage.objects.filter(
        sender='StudentSense',
        body=OLD_HIGH_RESULT_MESSAGE,
    ).update(body=NEW_HIGH_RESULT_MESSAGE)


def restore_high_result_messages(apps, schema_editor):
    ContactMessage = apps.get_model('counselor', 'ContactMessage')
    ContactMessage.objects.filter(
        sender='StudentSense',
        body=NEW_HIGH_RESULT_MESSAGE,
    ).update(body=OLD_HIGH_RESULT_MESSAGE)


class Migration(migrations.Migration):

    dependencies = [
        ('counselor', '0009_studentcontactrequest_is_general_chat'),
    ]

    operations = [
        migrations.RunPython(update_high_result_messages, restore_high_result_messages),
    ]
