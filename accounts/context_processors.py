from .models import UserNotification


def notification_count(request):
    if not request.user.is_authenticated:
        return {'unread_notification_count': 0}
    return {
        'unread_notification_count': UserNotification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count(),
    }