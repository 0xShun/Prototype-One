import json
import logging

from django.conf import settings

from .models import PushSubscription, UserNotification


logger = logging.getLogger(__name__)


def notify_user(user, *, kind, title, body, target_url=''):
    notification = UserNotification.objects.create(
        recipient=user,
        kind=kind,
        title=title,
        body=body,
        target_url=target_url,
    )
    send_push_notification(notification)
    return notification


def notify_users(users, *, kind, title, body, target_url=''):
    return [
        notify_user(user, kind=kind, title=title, body=body, target_url=target_url)
        for user in users.distinct()
    ]


def send_push_notification(notification):
    if not settings.WEBPUSH_VAPID_PUBLIC_KEY or not settings.WEBPUSH_VAPID_PRIVATE_KEY:
        return

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning('pywebpush is unavailable, keeping notification in the in-app inbox')
        return

    subscriptions = PushSubscription.objects.filter(user=notification.recipient)
    payload = json.dumps({
        'title': notification.title,
        'body': notification.body,
        'url': notification.target_url or '/',
    })
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims={'sub': settings.WEBPUSH_VAPID_SUBJECT},
                timeout=4,
                ttl=3600,
            )
        except WebPushException as exc:
            response = getattr(exc, 'response', None)
            if response is not None and response.status_code in (404, 410):
                subscription.delete()
            else:
                logger.warning('Browser push delivery failed for user %s', notification.recipient_id)
        except Exception:
            logger.exception('Unexpected browser push failure for user %s', notification.recipient_id)
