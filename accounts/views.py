import json

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import StudentRegistrationForm, TeacherRegistrationForm
from .models import PushSubscription, UserNotification


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'


class CustomLogoutView(LogoutView):
    next_page = '/'
    http_method_names = ['get', 'post', 'head', 'options']

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


def register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Your account was created successfully.')
            return redirect('home')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def register_teacher(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, 'Your teacher account is awaiting administrator approval. You can sign in after it is approved.')
            return redirect('login')
    else:
        form = TeacherRegistrationForm()
    return render(request, 'accounts/register_teacher.html', {'form': form})


def notifications(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user_notifications = UserNotification.objects.filter(recipient=request.user)
    return render(request, 'accounts/notifications.html', {'user_notifications': user_notifications})


@require_POST
def mark_notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return redirect('login')
    notification = UserNotification.objects.filter(recipient=request.user, id=notification_id).first()
    if notification:
        notification.mark_read()
        if notification.target_url:
            return redirect(notification.target_url)
    return redirect('notifications')


@require_POST
def mark_all_notifications_read(request):
    if not request.user.is_authenticated:
        return redirect('login')
    UserNotification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return redirect('notifications')


@require_POST
def push_subscription(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        endpoint = payload['endpoint']
        keys = payload['keys']
        p256dh = keys['p256dh']
        auth = keys['auth']
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'error': 'Invalid subscription payload'}, status=400)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
    )
    return JsonResponse({'saved': True})


@require_POST
def push_unsubscription(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        endpoint = payload['endpoint']
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'error': 'Invalid subscription payload'}, status=400)
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({'saved': True})


def notification_settings(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'accounts/notification_settings.html', {
        'vapid_public_key': settings.WEBPUSH_VAPID_PUBLIC_KEY,
    })
