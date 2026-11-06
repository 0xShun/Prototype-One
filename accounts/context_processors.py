from django.db import connection
from counselor.models import ContactMessage
from .models import UserNotification


def notification_count(request):
    if not request.user.is_authenticated:
        return {
            'unread_notification_count': 0,
            'unread_message_count': 0,
        }
    notification_table = UserNotification._meta.db_table
    message_table = ContactMessage._meta.db_table
    thread_table = ContactMessage._meta.get_field('thread').remote_field.model._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT
                (SELECT COUNT(*) FROM {notification_table}
                 WHERE recipient_id = %s AND read_at IS NULL),
                (SELECT COUNT(*) FROM {message_table} AS message
                 INNER JOIN {thread_table} AS thread ON thread.id = message.thread_id
                 WHERE message.read_at IS NULL AND (
                    (message.sender = %s AND thread.student_id = %s)
                    OR (message.sender = %s AND thread.assigned_counselor_id = %s)
                 ))
            ''',
            [
                request.user.id,
                ContactMessage.Sender.COUNSELOR,
                request.user.id,
                ContactMessage.Sender.STUDENT,
                request.user.id,
            ],
        )
        unread_notification_count, unread_message_count = cursor.fetchone()
    return {
        'unread_notification_count': unread_notification_count,
        'unread_message_count': unread_message_count,
    }
