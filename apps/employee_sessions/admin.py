"""
Admin para sessões de funcionários.
"""
from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import EmployeeSession
from apps.core.utils import TimezoneUtils
from apps.core.models import SystemConfiguration


class EmployeeSessionForm(forms.ModelForm):
    """Formulário personalizado para sessões de funcionários com valores padrão."""
    
    class Meta:
        model = EmployeeSession
        fields = '__all__'
        widgets = {
            'work_duration_minutes': forms.NumberInput(attrs={
                'placeholder': 'Deixe em branco para usar configuração padrão'
            }),
            'rest_duration_minutes': forms.NumberInput(attrs={
                'placeholder': 'Deixe em branco para usar configuração padrão'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tornar campos de duração opcionais no formulário
        self.fields['work_duration_minutes'].required = False
        self.fields['rest_duration_minutes'].required = False
        
        # Obter configuração padrão
        try:
            config = SystemConfiguration.objects.first()
            if config:
                self.fields['work_duration_minutes'].help_text = f"Valor padrão: {config.liberado_minutes} minutos ({config.get_liberado_hours():.1f} horas)"
                self.fields['rest_duration_minutes'].help_text = f"Valor padrão: {config.bloqueado_minutes} minutos ({config.get_bloqueado_hours():.1f} horas)"
        except:
            self.fields['work_duration_minutes'].help_text = "Valor padrão: 480 minutos (8.0 horas)"
            self.fields['rest_duration_minutes'].help_text = "Valor padrão: 672 minutos (11.2 horas)"
    
    def clean(self):
        """Validação geral do formulário."""
        cleaned_data = super().clean()
        
        # Se campos de duração estiverem vazios, usar valores padrão
        if not cleaned_data.get('work_duration_minutes'):
            try:
                config = SystemConfiguration.objects.first()
                if config:
                    cleaned_data['work_duration_minutes'] = config.liberado_minutes
                else:
                    cleaned_data['work_duration_minutes'] = 480  # Valor padrão hardcoded
            except:
                cleaned_data['work_duration_minutes'] = 480  # Valor padrão hardcoded
        
        if not cleaned_data.get('rest_duration_minutes'):
            try:
                config = SystemConfiguration.objects.first()
                if config:
                    cleaned_data['rest_duration_minutes'] = config.bloqueado_minutes
                else:
                    cleaned_data['rest_duration_minutes'] = 672  # Valor padrão hardcoded
            except:
                cleaned_data['rest_duration_minutes'] = 672  # Valor padrão hardcoded
        
        # Se o estado for 'blocked', calcular block_start e return_time automaticamente
        if cleaned_data.get('state') == 'blocked':
            from django.utils import timezone
            
            # Se block_start não estiver definido, usar o momento atual
            if not cleaned_data.get('block_start'):
                cleaned_data['block_start'] = timezone.now()
            
            # Calcular return_time baseado em block_start + rest_duration_minutes
            if cleaned_data.get('block_start') and cleaned_data.get('rest_duration_minutes'):
                from datetime import timedelta
                cleaned_data['return_time'] = cleaned_data['block_start'] + timedelta(minutes=cleaned_data['rest_duration_minutes'])
        
        return cleaned_data


@admin.register(EmployeeSession)
class EmployeeSessionAdmin(admin.ModelAdmin):
    form = EmployeeSessionForm
    list_display = [
        'id', 'employee_name', 'state_display', 'first_access_display',
        'work_duration_display', 'rest_duration_display', 'created_at_display'
    ]
    list_filter = ['state', 'created_at', 'first_access']
    search_fields = ['employee__name', 'employee__device_id']
    readonly_fields = ['created_at', 'updated_at', 'default_config_info']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('employee', 'state', 'first_access', 'last_access')
        }),
        ('Configurações de Duração', {
            'fields': ('work_duration_minutes', 'rest_duration_minutes', 'default_config_info'),
            'description': 'Deixe os campos de duração em branco para usar os valores padrão do sistema.'
        }),
        ('Informações de Bloqueio', {
            'fields': ('block_start', 'return_time'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def default_config_info(self, obj):
        """Exibe informações sobre a configuração padrão do sistema."""
        try:
            config = SystemConfiguration.objects.first()
            if config:
                return format_html(
                    '<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #007bff;">'
                    '<strong>📋 Configuração Padrão do Sistema:</strong><br>'
                    '• <strong>Duração de Trabalho:</strong> {} minutos ({} horas)<br>'
                    '• <strong>Duração de Interjornada:</strong> {} minutos ({} horas)<br>'
                    '<small style="color: #6c757d;">Deixe os campos acima em branco para usar estes valores.</small>'
                    '</div>',
                    config.liberado_minutes, config.get_liberado_hours(),
                    config.bloqueado_minutes, config.get_bloqueado_hours()
                )
            else:
                return format_html(
                    '<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107;">'
                    '<strong>⚠️ Configuração não encontrada</strong><br>'
                    'Valores padrão: 480 min (8h) trabalho, 672 min (11.2h) interjornada'
                    '</div>'
                )
        except:
            return format_html(
                '<div style="background-color: #f8d7da; padding: 10px; border-radius: 5px; border-left: 4px solid #dc3545;">'
                '<strong>❌ Erro ao carregar configuração</strong><br>'
                'Valores padrão: 480 min (8h) trabalho, 672 min (11.2h) interjornada'
                '</div>'
            )
    
    default_config_info.short_description = 'Configuração Padrão'
    
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