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
from .views import about, home, more, offline_page, service_worker_js

urlpatterns = [
    path('', home, name='home'),
    path('more/', more, name='more'),
    path('about/', about, name='about'),
    path('sw.js', service_worker_js, name='service_worker'),
    path('offline/', offline_page, name='offline'),
    path('accounts/', include('accounts.urls')),
    path('intake/', include(('intake.urls', 'intake'), namespace='intake')),
    path('recommendations/', include('recommendations.urls')),
    path('counselor/', include(('counselor.urls', 'counselor'), namespace='counselor')),
    path('admin/', admin.site.urls),
]
