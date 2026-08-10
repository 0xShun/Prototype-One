from django.urls import path

from .views import contact_request, contact_request_detail, dashboard, student_detail

urlpatterns = [
    path('contact/', contact_request, name='contact_request'),
    path('contact/<int:request_id>/', contact_request_detail, name='contact_request_detail'),
    path('dashboard/', dashboard, name='dashboard'),
    path('student/<int:user_id>/', student_detail, name='student_detail'),
]
