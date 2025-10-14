"""
URLs para configurações do sistema.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('configuracao/', views.configuracao_sistema, name='configuracao_sistema'),
    path('configuracao/help/', views.configuracao_help, name='configuracao_help'),
    path('api/test-connection/', views.test_device_connection, name='test_device_connection'),
]