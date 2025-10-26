"""
WebSocket routing para o app logs.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/logs/$', consumers.RealtimeLogsConsumer.as_asgi()),
]

