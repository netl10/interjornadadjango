"""
URLs para o app interjornada.
"""
from django.urls import path
from . import views

app_name = 'interjornada'

urlpatterns = [
    # Regras de interjornada
    path('rules/', views.InterjornadaRuleListCreateView.as_view(), name='rule-list-create'),
    path('rules/<int:pk>/', views.InterjornadaRuleDetailView.as_view(), name='rule-detail'),
    
    # Ciclos de interjornada
    path('cycles/', views.InterjornadaCycleListView.as_view(), name='cycle-list'),
    
    # Violações
    path('violations/', views.InterjornadaViolationListView.as_view(), name='violation-list'),
    path('violations/<int:violation_id>/resolve/', views.resolve_violation, name='violation-resolve'),
    path('violations/summary/', views.get_violations_summary, name='violations-summary'),
    
    # Estatísticas
    path('statistics/', views.InterjornadaStatisticsListView.as_view(), name='statistics-list'),
    
    # Ações por funcionário
    path('employees/<int:device_id>/create-cycle/', views.create_cycle, name='create-cycle'),
    path('employees/<int:device_id>/process-event/', views.process_access_event, name='process-event'),
    path('employees/<int:device_id>/status/', views.get_employee_status, name='employee-status'),
    path('employees/<int:device_id>/complete-cycle/', views.complete_cycle, name='complete-cycle'),
    
    # Monitoramento
    path('monitoring/start/', views.start_monitoring, name='start-monitoring'),
    path('monitoring/stop/', views.stop_monitoring, name='stop-monitoring'),
    path('monitoring/status/', views.get_monitoring_status, name='monitoring-status'),
    
    # Status geral
    path('active-cycles/', views.get_active_cycles, name='active-cycles'),
]
