"""
URLs para logs de acesso.
"""
from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    path('historico/', views.historico_acessos, name='historico_acessos'),
    path('realtime/', views.realtime_monitor, name='realtime_monitor'),
    path('api/stats/', views.api_logs_stats, name='api_logs_stats'),
    path('api/monitor-status/', views.api_monitor_status, name='api_monitor_status'),
    path('api/realtime-logs/', views.api_realtime_logs, name='api_realtime_logs'),
    path('api/logs-publicos/', views.api_logs_publicos, name='api_logs_publicos'),
]