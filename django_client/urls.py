"""
URL configuration for django_client project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('transfer_app.urls')),
]
