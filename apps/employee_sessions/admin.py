"""
Admin para sessões de funcionários.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import EmployeeSession
from apps.core.utils import TimezoneUtils


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
        return TimezoneUtils.format_datetime(obj.first_access)
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
        return TimezoneUtils.format_datetime(obj.created_at)
    created_at_display.short_description = 'Criado em'
    
    def return_time_display(self, obj):
        if obj.return_time:
            return TimezoneUtils.format_datetime(obj.return_time)
        return '-'
    return_time_display.short_description = 'Horário de Retorno'
    
    def block_start_display(self, obj):
        if obj.block_start:
            return TimezoneUtils.format_datetime(obj.block_start)
        return '-'
    block_start_display.short_description = 'Início do Bloqueio'