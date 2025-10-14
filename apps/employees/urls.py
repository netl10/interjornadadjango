"""
URLs para o app employees.
"""
from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    # Funcionários
    path('', views.EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('<int:device_id>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    
    # Grupos
    path('groups/', views.EmployeeGroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', views.EmployeeGroupDetailView.as_view(), name='group-detail'),
    
    # Ações específicas
    path('check-access/', views.check_employee_access, name='check-access'),
]
