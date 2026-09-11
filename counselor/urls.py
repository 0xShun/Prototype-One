from django.urls import path

from .views import (
    archive_result,
    archive_view,
    contact_request,
    contact_request_detail,
    claim_contact_request,
    close_contact_request,
    dashboard,
    delete_archived_result,
    restore_result,
    student_detail,
    student_reply,
)

urlpatterns = [
    path('contact/', contact_request, name='contact_request'),
    path('contact/<int:request_id>/', contact_request_detail, name='contact_request_detail'),
    path('contact/<int:request_id>/claim/', claim_contact_request, name='claim_contact_request'),
    path('contact/<int:request_id>/close/', close_contact_request, name='close_contact_request'),
    path('contact/<int:request_id>/reply/', student_reply, name='student_reply'),
    path('dashboard/', dashboard, name='dashboard'),
    path('student/<int:user_id>/', student_detail, name='student_detail'),
    path('result/<int:result_id>/archive/', archive_result, name='archive_result'),
    path('archive/', archive_view, name='archive'),
    path('archive/<int:result_id>/restore/', restore_result, name='restore_result'),
    path('archive/<int:result_id>/delete/', delete_archived_result, name='delete_archived_result'),
]
