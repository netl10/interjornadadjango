"""
Admin para sessões de funcionários.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import EmployeeSession


@admin.register(EmployeeSession)
class EmployeeSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'employee_name', 'state_display', 'first_access_display',
        'work_duration_display', 'rest_duration_display', 'created_at_display'
    ]
    list_filter = ['state', 'created_at', 'first_access']
    search_fields = ['employee__name', 'employee__device_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def employee_name(self, obj):
        return obj.employee.name
    employee_name.short_description = 'Funcionário'
    
    def state_display(self, obj):
        colors = {
            'active': '#28a745',
            'blocked': '#dc3545',
            'pending_rest': '#ffc107',
            'completed': '#6c757d'
        }
        color = colors.get(obj.state, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_state_display()
        )
    state_display.short_description = 'Estado'
    
    def first_access_display(self, obj):
        return obj.first_access.strftime('%d/%m/%Y %H:%M:%S')
    first_access_display.short_description = 'Primeiro Acesso'
    
    def work_duration_display(self, obj):
        hours = obj.work_duration_minutes // 60
        minutes = obj.work_duration_minutes % 60
        return f"{hours}h {minutes}min"
    work_duration_display.short_description = 'Duração Trabalho'
    
    def rest_duration_display(self, obj):
        hours = obj.rest_duration_minutes // 60
        minutes = obj.rest_duration_minutes % 60
        return f"{hours}h {minutes}min"
    rest_duration_display.short_description = 'Duração Interjornada'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M:%S')
    created_at_display.short_description = 'Criado em'