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
    path('api/sessoes-publicas/', views.api_sessoes_publicas, name='api_sessoes_publicas'),
    path('api/sessoes-ativas/', views.api_sessoes_ativas, name='api_sessoes_ativas'),
    path('api/session-counts/', views.api_session_counts, name='api_session_counts'),
]
