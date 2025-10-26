"""
Admin personalizado para logs de acesso.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import AccessLog, SystemLog, LogProcessingQueue
from apps.core.utils import TimezoneUtils


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = [
        'device_log_id', 'user_name', 'event_type_display', 
        'portal_display', 'device_timestamp_display', 'processing_status_display'
    ]
    
    def changelist_view(self, request, extra_context=None):
        """Adiciona link para histórico na página de listagem."""
        extra_context = extra_context or {}
        extra_context['historico_url'] = '/admin/logs/historico/'
        return super().changelist_view(request, extra_context=extra_context)
    list_filter = [
        'event_type', 'processing_status', 'device_id', 'portal_id',
        'device_timestamp', 'created_at'
    ]
    search_fields = ['user_name', 'user_id', 'device_log_id', 'event_description']
    readonly_fields = [
        'device_log_id', 'user_id', 'user_name', 'event_type', 'event_description',
        'device_id', 'device_name', 'portal_id', 'device_timestamp', 
        'received_timestamp', 'processed_timestamp', 'raw_data_display',
        'created_at', 'updated_at'
    ]
    ordering = ['-device_timestamp']
    list_per_page = 50
    
    fieldsets = (
        ('Informações do Log', {
            'fields': ('device_log_id', 'user_id', 'user_name')
        }),
        ('Evento', {
            'fields': ('event_type', 'event_description')
        }),
        ('Dispositivo', {
            'fields': ('device_id', 'device_name', 'portal_id')
        }),
        ('Timestamps', {
            'fields': ('device_timestamp', 'received_timestamp', 'processed_timestamp')
        }),
        ('Status', {
            'fields': ('processing_status', 'processing_error')
        }),
        ('Dados', {
            'fields': ('raw_data_display', 'processed_data'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def event_type_display(self, obj):
        """Exibe o tipo de evento com cores."""
        colors = {
            1: '#28a745',  # Verde - Entrada
            2: '#dc3545',  # Vermelho - Saída
            3: '#6c757d',  # Cinza - Não Identificado
            4: '#6c757d',  # Cinza - Erro de Leitura
            5: '#fd7e14',  # Laranja - Timeout
            6: '#dc3545',  # Vermelho - Acesso Negado
            7: '#007bff',  # Azul - Acesso Autorizado
            8: '#6f42c1',  # Roxo - Acesso Bloqueado
            13: '#ffc107', # Amarelo - Desistência
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_event_type_display()
        )
    event_type_display.short_description = 'Evento'
    
    def portal_display(self, obj):
        """Exibe o portal com ícone."""
        if obj.portal_id == 1:
            return format_html('🚪 Portal 1 (Entrada)')
        elif obj.portal_id == 2:
            return format_html('🚪 Portal 2 (Saída)')
        else:
            return format_html('🚪 Portal {}', obj.portal_id)
    portal_display.short_description = 'Portal'
    
    def device_timestamp_display(self, obj):
        """Exibe timestamp formatado."""
        return TimezoneUtils.format_datetime(obj.device_timestamp)
    device_timestamp_display.short_description = 'Data/Hora'
    
    def processing_status_display(self, obj):
        """Exibe status com cores."""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'processed': '#28a745',
            'error': '#dc3545',
            'ignored': '#6c757d',
        }
        color = colors.get(obj.processing_status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_processing_status_display()
        )
    processing_status_display.short_description = 'Status'
    
    def raw_data_display(self, obj):
        """Exibe dados brutos formatados."""
        if obj.raw_data:
            import json
            formatted = json.dumps(obj.raw_data, indent=2, ensure_ascii=False)
            return format_html('<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
        return '-'
    raw_data_display.short_description = 'Dados Brutos'
    
    def has_add_permission(self, request):
        """Desabilita adição manual de logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Desabilita edição de logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permite apenas superusuários deletar logs."""
        return request.user.is_superuser


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp_display', 'level_display', 'category_display', 
        'message_short', 'user_name', 'device_name'
    ]
    list_filter = [
        'level', 'category', 'timestamp', 'user_id', 'device_id'
    ]
    search_fields = ['message', 'user_name', 'device_name']
    readonly_fields = [
        'level', 'category', 'message', 'user_id', 'user_name',
        'device_id', 'device_name', 'details_display', 'timestamp'
    ]
    ordering = ['-timestamp']
    list_per_page = 50
    
    fieldsets = (
        ('Log', {
            'fields': ('level', 'category', 'message')
        }),
        ('Contexto', {
            'fields': ('user_id', 'user_name', 'device_id', 'device_name')
        }),
        ('Detalhes', {
            'fields': ('details_display',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def timestamp_display(self, obj):
        """Exibe timestamp formatado."""
        return obj.display_timestamp
    timestamp_display.short_description = 'Data/Hora'
    
    def level_display(self, obj):
        """Exibe nível com cores."""
        colors = {
            'DEBUG': '#6c757d',
            'INFO': '#17a2b8',
            'WARNING': '#ffc107',
            'ERROR': '#dc3545',
            'CRITICAL': '#721c24',
        }
        color = colors.get(obj.level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.level
        )
    level_display.short_description = 'Nível'
    
    def category_display(self, obj):
        """Exibe categoria com ícone."""
        icons = {
            'system': '⚙️',
            'device': '📱',
            'employee': '👤',
            'interjornada': '🔄',
            'authentication': '🔐',
            'database': '🗄️',
            'api': '🌐',
            'websocket': '🔌',
            'monitoring': '📊',
        }
        icon = icons.get(obj.category, '📝')
        return format_html('{} {}', icon, obj.get_category_display())
    category_display.short_description = 'Categoria'
    
    def message_short(self, obj):
        """Exibe mensagem truncada."""
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message
    message_short.short_description = 'Mensagem'
    
    def details_display(self, obj):
        """Exibe detalhes formatados."""
        if obj.details:
            import json
            formatted = json.dumps(obj.details, indent=2, ensure_ascii=False)
            return format_html('<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
        return '-'
    details_display.short_description = 'Detalhes'
    
    def has_add_permission(self, request):
        """Desabilita adição manual de logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Desabilita edição de logs."""
        return False


@admin.register(LogProcessingQueue)
class LogProcessingQueueAdmin(admin.ModelAdmin):
    list_display = [
        'access_log', 'status_display', 'priority', 'attempts', 
        'last_attempt_display', 'next_retry_display'
    ]
    list_filter = [
        'status', 'priority', 'created_at', 'last_attempt'
    ]
    search_fields = ['access_log__user_name', 'access_log__device_log_id']
    readonly_fields = [
        'access_log', 'status', 'priority', 'attempts', 'max_attempts',
        'last_attempt', 'next_retry', 'error_message', 'error_details_display',
        'created_at', 'updated_at'
    ]
    ordering = ['-priority', 'created_at']
    list_per_page = 50
    
    def status_display(self, obj):
        """Exibe status com cores."""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'retry': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def last_attempt_display(self, obj):
        """Exibe última tentativa."""
        if obj.last_attempt:
            return TimezoneUtils.format_datetime(obj.last_attempt)
        return '-'
    last_attempt_display.short_description = 'Última Tentativa'
    
    def next_retry_display(self, obj):
        """Exibe próxima tentativa."""
        if obj.next_retry:
            return TimezoneUtils.format_datetime(obj.next_retry)
        return '-'
    next_retry_display.short_description = 'Próxima Tentativa'
    
    def error_details_display(self, obj):
        """Exibe detalhes do erro formatados."""
        if obj.error_details:
            import json
            formatted = json.dumps(obj.error_details, indent=2, ensure_ascii=False)
            return format_html('<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
        return '-'
    error_details_display.short_description = 'Detalhes do Erro'
    
    def has_add_permission(self, request):
        """Desabilita adição manual."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Desabilita edição."""
        return False
