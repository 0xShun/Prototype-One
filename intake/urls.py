from django.urls import path

from .views import create_intake, result_view, history_view, save_draft

urlpatterns = [
    path('new/', create_intake, name='create'),
    path('drafts/', save_draft, name='drafts'),
    path('result/', result_view, name='result'),
    path('history/', history_view, name='history'),
]
