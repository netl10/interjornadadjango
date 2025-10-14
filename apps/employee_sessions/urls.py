"""
URLs para sessões de funcionários.
"""
from django.urls import path
from . import views

app_name = 'sessions'

urlpatterns = [
    path('dashboard/', views.dashboard_sessoes, name='dashboard_sessoes'),
    path('dashboard-clean/', views.dashboard_sessoes_clean, name='dashboard_sessoes_clean'),
    path('interjornada/', views.sessoes_interjornada, name='sessoes_interjornada'),
    path('api/sessoes-ativas/', views.api_sessoes_ativas, name='api_sessoes_ativas'),
]
