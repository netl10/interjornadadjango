"""
URLs para sessões de funcionários.
"""
from django.urls import path
from . import views

app_name = 'sessions'

urlpatterns = [
    path('dashboard/', views.dashboard_sessoes, name='dashboard_sessoes'),
    path('api/sessoes-ativas/', views.api_sessoes_ativas, name='api_sessoes_ativas'),
]
