from django.urls import path

from .views import create_intake, history_view, result_view, save_draft, supporting_file_download

urlpatterns = [
    path('new/', create_intake, name='create'),
    path('drafts/', save_draft, name='drafts'),
    path('result/', result_view, name='result'),
    path('history/', history_view, name='history'),
    path('file/<int:intake_id>/', supporting_file_download, name='supporting_file_download'),
]
