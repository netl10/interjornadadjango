"""
URLs para o app dashboard.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_view, name='dashboard'),
    
    # APIs do dashboard
    path('api/data/', views.get_dashboard_data, name='dashboard-data'),
    path('api/employee/<int:device_id>/', views.get_employee_details, name='employee-details'),
    path('api/system-status/', views.get_system_status, name='system-status'),
    path('api/notifications/', views.get_notifications, name='notifications'),
    
    # Simulação para testes
    path('api/simulate-access-denied/', views.simulate_access_denied, name='simulate-access-denied'),
]
