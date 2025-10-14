"""
URLs para o app devices.
"""
from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    # Dispositivos
    path('', views.DeviceListCreateView.as_view(), name='device-list-create'),
    path('<int:pk>/', views.DeviceDetailView.as_view(), name='device-detail'),
    
    # Logs de dispositivos
    path('logs/', views.DeviceLogListView.as_view(), name='device-log-list'),
    
    # Sessões de dispositivos
    path('sessions/', views.DeviceSessionListView.as_view(), name='device-session-list'),
    
    # Conexão e desconexão
    path('<int:device_id>/connect/', views.connect_device, name='device-connect'),
    path('<int:device_id>/disconnect/', views.disconnect_device, name='device-disconnect'),
    
    # Dados do dispositivo
    path('<int:device_id>/logs/', views.get_device_logs, name='device-logs'),
    path('<int:device_id>/status/', views.get_device_status, name='device-status'),
    path('<int:device_id>/users/', views.get_device_users, name='device-users'),
    path('<int:device_id>/groups/', views.get_device_groups, name='device-groups'),
    
    # Monitoramento
    path('monitoring/start/', views.start_monitoring, name='start-monitoring'),
    path('monitoring/stop/', views.stop_monitoring, name='stop-monitoring'),
    path('monitoring/status/', views.get_monitoring_status, name='monitoring-status'),
    
    # Status geral
    path('status/all/', views.get_all_devices_status, name='all-devices-status'),
]
