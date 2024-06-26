# vision-monitor-website/asgi.py
"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import monitor.routing
from whitenoise import WhiteNoise
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()
whitenoise_app = WhiteNoise(django_asgi_app, root=settings.STATIC_ROOT)

async def whitenoise_asgi_wrapper(scope, receive, send):
    if scope["type"] == "http":
        await whitenoise_app(scope, receive, send)
    else:
        await django_asgi_app(scope, receive, send)

application = ProtocolTypeRouter({
    "http": whitenoise_asgi_wrapper,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            monitor.routing.websocket_urlpatterns
        )
    ),
})
