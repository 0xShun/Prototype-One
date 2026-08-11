from django.db import migrations


def create_demo_counselor(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    StudentProfile = apps.get_model('accounts', 'StudentProfile')

    username = 'counselor_demo'
    password = 'StrongPass123!'

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': 'counselor_demo@example.com',
        },
    )

    if created:
        user.set_password(password)
        user.save(update_fields=['password'])

    profile, profile_created = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'is_counselor': True,
            'program': '',
            'year_level': '',
        },
    )

    if not profile_created and not profile.is_counselor:
        profile.is_counselor = True
        profile.save(update_fields=['is_counselor'])


def delete_demo_counselor(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    User.objects.filter(username='counselor_demo').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_demo_counselor, delete_demo_counselor),
    ]