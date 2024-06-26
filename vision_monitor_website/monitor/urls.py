from django.contrib import admin
from django.urls import path
from django.views.static import serve
from django.conf import settings
from . import views
import os

def serve_favicon(request):
    favicon_path = os.path.join(settings.STATIC_ROOT, 'favicon.ico')
    return serve(request, os.path.basename(favicon_path), os.path.dirname(favicon_path))

urlpatterns = [
    path('', views.home, name='home'),
    path('monitor/', views.monitor, name='monitor'),
    path('test_websocket/', views.test_websocket, name='test_websocket'),
    path('favicon.ico', serve_favicon),
]