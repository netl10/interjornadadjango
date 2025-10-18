"""
ASGI config for interjornada_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')

# Importar as rotas do WebSocket
from apps.dashboard.routing import websocket_urlpatterns as dashboard_websocket_urlpatterns
from apps.logs.routing import websocket_urlpatterns as logs_websocket_urlpatterns

# Combinar todas as rotas WebSocket
all_websocket_urlpatterns = dashboard_websocket_urlpatterns + logs_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            all_websocket_urlpatterns
        )
    ),
})
