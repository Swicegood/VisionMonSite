from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('monitor/', views.monitor, name='monitor'),
    path('test_websocket/', views.test_websocket, name='test_websocket'),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico')))
]