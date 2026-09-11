"""
URL configuration for studentsense project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from .views import home, offline_page, service_worker_js

urlpatterns = [
    path('', home, name='home'),
    path('sw.js', service_worker_js, name='service_worker'),
    path('offline/', offline_page, name='offline'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('how-to/', TemplateView.as_view(template_name='how_to.html'), name='how_to'),
    path('accounts/', include('accounts.urls')),
    path('intake/', include(('intake.urls', 'intake'), namespace='intake')),
    path('recommendations/', include('recommendations.urls')),
    path('counselor/', include(('counselor.urls', 'counselor'), namespace='counselor')),
    path('admin/', admin.site.urls),
]
