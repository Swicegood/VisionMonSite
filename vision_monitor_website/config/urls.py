from django.urls import path
from . import views
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
       path('admin/', admin.site.urls),
    path('', include('monitor.urls')),
    path('get_latest_image/<int:camera_index>/', views.get_latest_image, name='get_latest_image'),
]