from django.urls import path

from .views import (
    CustomLoginView,
    CustomLogoutView,
    mark_notification_read,
    mark_all_notifications_read,
    notification_settings,
    notifications,
    push_subscription,
    push_unsubscription,
    register,
    register_teacher,
)

urlpatterns = [
    path('register/', register, name='register'),
    path('register/teacher/', register_teacher, name='register_teacher'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('notifications/', notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/settings/', notification_settings, name='notification_settings'),
    path('notifications/push-subscription/', push_subscription, name='push_subscription'),
    path('notifications/push-unsubscription/', push_unsubscription, name='push_unsubscription'),
]
