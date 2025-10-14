"""
URLs para sessões de funcionários.
"""
from django.urls import path
from . import views

app_name = 'sessions'

urlpatterns = [
    path('dashboard/', views.dashboard_sessoes, name='dashboard_sessoes'),
    path('dashboard-clean/', views.dashboard_sessoes_clean, name='dashboard_sessoes_clean'),
    path('interjornada-ativa/', views.interjornada_ativa, name='interjornada_ativa'),
    path('api/sessoes-ativas/', views.api_sessoes_ativas, name='api_sessoes_ativas'),
    path('api/interjornada-ativa/', views.api_interjornada_ativa, name='api_interjornada_ativa'),
]
