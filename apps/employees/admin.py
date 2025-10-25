"""
Admin para o app employees.
"""
from django.contrib import admin
from .models import Employee, EmployeeGroup


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'name', 'employee_code', 'is_active', 'is_exempt', 'created_at']
    list_filter = ['is_active', 'is_exempt', 'created_at']
    search_fields = ['name', 'employee_code', 'device_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('device_id', 'name', 'employee_code', 'is_active')
        }),
        ('Configurações de Interjornada', {
            'fields': ('is_exempt', 'work_duration_minutes', 'rest_duration_minutes')
        }),
        ('Configurações de Aviso', {
            'fields': ('alert_type',),
            'description': 'Tipo de aviso que será reproduzido quando o funcionário fizer acesso (apenas quando não estiver em interjornada)'
        }),
        ('Grupos', {
            'fields': ('groups', 'exemption_groups'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmployeeGroup)
class EmployeeGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_exemption_group', 'employee_count', 'created_at']
    list_filter = ['is_exemption_group', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'employee_count']
    
    fieldsets = (
        ('Informações do Grupo', {
            'fields': ('name', 'description', 'is_exemption_group')
        }),
        ('Configurações de Interjornada', {
            'fields': ('work_duration_minutes', 'rest_duration_minutes')
        }),
        ('Estatísticas', {
            'fields': ('employee_count',),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
