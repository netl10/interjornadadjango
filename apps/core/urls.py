"""
URLs para configurações do sistema.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.core_admin, name='core_admin'),
    path('configuracao/', views.configuracao_sistema, name='configuracao_sistema'),
    path('configuracao/help/', views.configuracao_help, name='configuracao_help'),
    path('api/test-connection/', views.test_device_connection, name='test_device_connection'),
    path('sincronizar-blacklist/', views.sincronizar_blacklist, name='sincronizar_blacklist'),
    path('api/sync-blacklist/', views.processar_sincronizacao_blacklist, name='processar_sincronizacao_blacklist'),
]