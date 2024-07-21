from django.contrib import admin
from django.urls import path
from django.views.static import serve
from django.conf import settings
import os

from . import views
from .image_handling import get_latest_image, get_composite_image
from .notifications import test_notification

def serve_favicon(request):
    favicon_path = os.path.join(settings.STATIC_ROOT, 'favicon.ico')
    return serve(request, os.path.basename(favicon_path), os.path.dirname(favicon_path))

urlpatterns = [
    path('', views.home, name='home'),
    path('monitor/', views.monitor, name='monitor'),
    path('test_websocket/', views.test_websocket, name='test_websocket'),
    path('test-notification/', views.test_notification_view, name='test_notification'),
    path('favicon.ico', serve_favicon),
    path('get_latest_image/<int:camera_index>/', get_latest_image, name='get_latest_image'),
    path('get_composite_image/<str:camera_name>/', get_composite_image, name='get_composite_image'),
    path('update_state/', views.update_state, name='update_state'),
]