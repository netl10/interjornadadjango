"""
Admin personalizado para configurações do sistema.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect
from .models import SystemConfiguration


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'device_info', 'timezone_info', 'interjornada_info', 
        'monitoring_info', 'is_active_display', 'updated_at_display'
    ]
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['device_ip', 'device_username', 'exemption_group_name']
    readonly_fields = ['created_at', 'updated_at', 'config_summary']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('🌐 Configurações de Conexão - Dispositivo Principal', {
            'fields': (
                'device_ip', 'device_port', 'device_username', 'device_password'
            ),
            'classes': ('wide',)
        }),
        ('🌐 Configurações de Conexão - Dispositivo Secundário', {
            'fields': (
                'secondary_device_ip', 'secondary_device_port', 
                'secondary_device_username', 'secondary_device_password'
            ),
            'classes': ('wide', 'collapse')
        }),
        ('⏰ Configurações de Timezone e Tempo', {
            'fields': (
                'timezone_offset', 'giro_validation_timeout', 'monitor_interval'
            ),
            'classes': ('wide',)
        }),
        ('🚪 Configurações de Interjornada', {
            'fields': (
                'liberado_minutes', 'bloqueado_minutes', 'exemption_group_name'
            ),
            'classes': ('wide',)
        }),
        ('🔄 Configurações de Reinício Automático', {
            'fields': (
                'restart_time_1', 'restart_time_2', 'restart_time_3', 'restart_time_4'
            ),
            'classes': ('wide', 'collapse')
        }),
        ('🔒 Configurações de Segurança e Logs', {
            'fields': (
                'ssl_verify', 'max_logs_per_request'
            ),
            'classes': ('wide', 'collapse')
        }),
        ('📊 Resumo da Configuração', {
            'fields': ('config_summary',),
            'classes': ('wide', 'collapse')
        }),
        ('📝 Metadados', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('wide', 'collapse')
        }),
    )
    
    def device_info(self, obj):
        """Exibe informações do dispositivo."""
        if obj.device_ip:
            return format_html(
                '<strong>📱 {}:{}</strong><br>'
                '<small>Usuário: {}</small>',
                obj.device_ip, obj.device_port, obj.device_username
            )
        return '-'
    device_info.short_description = 'Dispositivo Principal'
    
    def timezone_info(self, obj):
        """Exibe informações do timezone."""
        timezone_str = obj.get_timezone_info()
        return format_html(
            '<strong>🌍 {}</strong><br>'
            '<small>Offset: {}</small>',
            timezone_str, obj.timezone_offset
        )
    timezone_info.short_description = 'Timezone'
    
    def interjornada_info(self, obj):
        """Exibe informações de interjornada."""
        liberado_hours = obj.get_liberado_hours()
        bloqueado_hours = obj.get_bloqueado_hours()
        return format_html(
            '<strong>🚪 Interjornada</strong><br>'
            '<small>Liberado: {}h | Bloqueado: {}h</small><br>'
            '<small>Grupo: {}</small>',
            round(liberado_hours, 1), round(bloqueado_hours, 1), obj.exemption_group_name
        )
    interjornada_info.short_description = 'Interjornada'
    
    def monitoring_info(self, obj):
        """Exibe informações de monitoramento."""
        return format_html(
            '<strong>📊 Monitoramento</strong><br>'
            '<small>Intervalo: {}s | Timeout: {}s</small><br>'
            '<small>Max Logs: {}</small>',
            obj.monitor_interval, obj.giro_validation_timeout, obj.max_logs_per_request
        )
    monitoring_info.short_description = 'Monitoramento'
    
    def is_active_display(self, obj):
        """Exibe status ativo com cores."""
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✅ Ativo</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">❌ Inativo</span>'
            )
    is_active_display.short_description = 'Status'
    
    def updated_at_display(self, obj):
        """Exibe data de atualização."""
        return obj.updated_at.strftime('%d/%m/%Y %H:%M')
    updated_at_display.short_description = 'Atualizado'
    
    def config_summary(self, obj):
        """Exibe resumo da configuração."""
        restart_times = obj.get_restart_times()
        restart_str = ', '.join(restart_times) if restart_times else 'Nenhum'
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff;">'
            '<h4 style="margin-top: 0; color: #007bff;">📋 Resumo da Configuração</h4>'
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">'
            '<div>'
            '<strong>🌐 Conexão:</strong><br>'
            '• IP: {}:{}<br>'
            '• Usuário: {}<br>'
            '• SSL: {}<br>'
            '</div>'
            '<div>'
            '<strong>⏰ Tempo:</strong><br>'
            '• Timezone: {}<br>'
            '• Monitor: {}s<br>'
            '• Timeout: {}s<br>'
            '</div>'
            '<div>'
            '<strong>🚪 Interjornada:</strong><br>'
            '• Liberado: {}h ({}min)<br>'
            '• Bloqueado: {}h ({}min)<br>'
            '• Grupo: {}<br>'
            '</div>'
            '<div>'
            '<strong>🔄 Reinícios:</strong><br>'
            '• Horários: {}<br>'
            '• Max Logs: {}<br>'
            '</div>'
            '</div>'
            '</div>',
            obj.device_ip, obj.device_port, obj.device_username,
            'Sim' if obj.ssl_verify else 'Não',
            obj.get_timezone_info(), obj.monitor_interval, obj.giro_validation_timeout,
            round(obj.get_liberado_hours(), 1), obj.liberado_minutes,
            round(obj.get_bloqueado_hours(), 1), obj.bloqueado_minutes,
            obj.exemption_group_name,
            restart_str, obj.max_logs_per_request
        )
    config_summary.short_description = 'Resumo'
    
    def has_add_permission(self, request):
        """Permite adicionar apenas se não houver configuração ativa."""
        active_count = SystemConfiguration.objects.filter(is_active=True).count()
        return active_count == 0
    
    def has_delete_permission(self, request, obj=None):
        """Permite apenas superusuários deletar configurações."""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Salva o modelo e garante que apenas uma configuração esteja ativa."""
        if obj.is_active:
            # Desativar outras configurações
            SystemConfiguration.objects.filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)
    
    def changelist_view(self, request, extra_context=None):
        """Adiciona informações extras na listagem."""
        extra_context = extra_context or {}
        active_config = SystemConfiguration.objects.filter(is_active=True).first()
        if active_config:
            extra_context['active_config'] = active_config
        
        return super().changelist_view(request, extra_context=extra_context)


# Criar um modelo fictício para o Config. Blacklist
from django.db import models

class BlacklistConfig(models.Model):
    """Modelo fictício para Config. Blacklist."""
    name = models.CharField(max_length=100, default="Config. Blacklist")
    
    class Meta:
        verbose_name = "Config. Blacklist"
        verbose_name_plural = "Config. Blacklist"
        managed = False  # Não criar tabela no banco
    
    def __str__(self):
        return self.name


@admin.register(BlacklistConfig)
class BlacklistConfigAdmin(admin.ModelAdmin):
    """Admin personalizado para Config. Blacklist."""
    
    def changelist_view(self, request, extra_context=None):
        """Redireciona para a página de sincronização do blacklist."""
        return HttpResponseRedirect(reverse('core:sincronizar_blacklist'))
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        return True
