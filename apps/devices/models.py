"""
Modelos para gerenciamento de dispositivos.
"""
from django.db import models
from django.contrib.auth.models import User
from apps.core.utils import TimezoneUtils


class Device(models.Model):
    """Modelo para dispositivos do sistema."""
    
    # Tipos de dispositivo
    DEVICE_TYPES = [
        ('primary', 'Primário'),
        ('secondary', 'Secundário'),
    ]
    
    # Status do dispositivo
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('inactive', 'Inativo'),
        ('maintenance', 'Manutenção'),
        ('error', 'Erro'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nome do Dispositivo")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, verbose_name="Tipo")
    ip_address = models.GenericIPAddressField(verbose_name="Endereço IP")
    port = models.IntegerField(verbose_name="Porta")
    username = models.CharField(max_length=100, verbose_name="Usuário")
    password = models.CharField(max_length=255, verbose_name="Senha")
    use_https = models.BooleanField(default=False, verbose_name="Usar HTTPS")
    
    # Status e configurações
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive', verbose_name="Status")
    is_enabled = models.BooleanField(default=True, verbose_name="Habilitado")
    
    # Configurações de conexão
    connection_timeout = models.IntegerField(default=15, verbose_name="Timeout de Conexão (s)")
    request_timeout = models.IntegerField(default=10, verbose_name="Timeout de Requisição (s)")
    max_reconnection_attempts = models.IntegerField(default=10, verbose_name="Máximo de Tentativas de Reconexão")
    
    # Informações de monitoramento
    last_connection = models.DateTimeField(null=True, blank=True, verbose_name="Última Conexão")
    last_error = models.DateTimeField(null=True, blank=True, verbose_name="Último Erro")
    error_count = models.IntegerField(default=0, verbose_name="Contador de Erros")
    success_count = models.IntegerField(default=0, verbose_name="Contador de Sucessos")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    
    class Meta:
        verbose_name = "Dispositivo"
        verbose_name_plural = "Dispositivos"
        ordering = ['device_type', 'name']
        unique_together = ['ip_address', 'port']
        indexes = [
            models.Index(fields=['device_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_enabled']),
            models.Index(fields=['ip_address', 'port']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port})"
    
    @property
    def base_url(self):
        """URL base do dispositivo."""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.ip_address}:{self.port}"
    
    @property
    def is_connected(self):
        """Verifica se o dispositivo está conectado."""
        return self.status == 'active' and self.last_connection is not None
    
    @property
    def connection_success_rate(self):
        """Taxa de sucesso de conexão."""
        total_attempts = self.success_count + self.error_count
        if total_attempts == 0:
            return 0
        return (self.success_count / total_attempts) * 100
    
    def update_connection_status(self, success=True, error_message=None):
        """Atualiza status de conexão do dispositivo."""
        now = TimezoneUtils.get_utc_now()
        
        if success:
            self.status = 'active'
            self.last_connection = now
            self.success_count += 1
            self.error_count = 0  # Reset error count on success
        else:
            self.status = 'error'
            self.last_error = now
            self.error_count += 1
            
            # Se muitos erros, marcar como inativo
            if self.error_count >= self.max_reconnection_attempts:
                self.is_enabled = False
        
        self.save(update_fields=['status', 'last_connection', 'last_error', 'error_count', 'success_count', 'is_enabled'])


class DeviceLog(models.Model):
    """Modelo para logs de dispositivos."""
    
    # Tipos de log
    LOG_TYPES = [
        ('connection', 'Conexão'),
        ('authentication', 'Autenticação'),
        ('data_fetch', 'Busca de Dados'),
        ('error', 'Erro'),
        ('maintenance', 'Manutenção'),
    ]
    
    # Níveis de log
    LOG_LEVELS = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Informação'),
        ('WARNING', 'Aviso'),
        ('ERROR', 'Erro'),
        ('CRITICAL', 'Crítico'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='logs', verbose_name="Dispositivo")
    log_type = models.CharField(max_length=20, choices=LOG_TYPES, verbose_name="Tipo de Log")
    level = models.CharField(max_length=10, choices=LOG_LEVELS, verbose_name="Nível")
    message = models.TextField(verbose_name="Mensagem")
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes")
    
    # Metadados
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")
    
    class Meta:
        verbose_name = "Log de Dispositivo"
        verbose_name_plural = "Logs de Dispositivos"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['log_type']),
            models.Index(fields=['level']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.get_log_type_display()} - {self.timestamp}"


class DeviceSession(models.Model):
    """Modelo para sessões de dispositivos."""
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sessions', verbose_name="Dispositivo")
    session_token = models.CharField(max_length=255, null=True, blank=True, verbose_name="Token de Sessão")
    is_active = models.BooleanField(default=False, verbose_name="Ativa")
    
    # Timestamps
    started_at = models.DateTimeField(verbose_name="Iniciada em")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Finalizada em")
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name="Última Atividade")
    
    # Estatísticas
    requests_count = models.IntegerField(default=0, verbose_name="Número de Requisições")
    errors_count = models.IntegerField(default=0, verbose_name="Número de Erros")
    
    class Meta:
        verbose_name = "Sessão de Dispositivo"
        verbose_name_plural = "Sessões de Dispositivos"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['device', 'is_active']),
            models.Index(fields=['started_at']),
            models.Index(fields=['session_token']),
        ]
    
    def __str__(self):
        return f"Sessão {self.device.name} - {self.started_at}"
    
    @property
    def duration(self):
        """Duração da sessão."""
        if self.ended_at:
            return self.ended_at - self.started_at
        elif self.is_active:
            return TimezoneUtils.get_utc_now() - self.started_at
        return None
    
    @property
    def success_rate(self):
        """Taxa de sucesso da sessão."""
        total_requests = self.requests_count + self.errors_count
        if total_requests == 0:
            return 0
        return (self.requests_count / total_requests) * 100
    
    def end_session(self):
        """Finaliza a sessão."""
        self.is_active = False
        self.ended_at = TimezoneUtils.get_utc_now()
        self.save(update_fields=['is_active', 'ended_at'])
    
    def update_activity(self, success=True):
        """Atualiza atividade da sessão."""
        self.last_activity = TimezoneUtils.get_utc_now()
        
        if success:
            self.requests_count += 1
        else:
            self.errors_count += 1
        
        self.save(update_fields=['last_activity', 'requests_count', 'errors_count'])


class DeviceConfiguration(models.Model):
    """Modelo para configurações de dispositivos."""
    
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='configuration', verbose_name="Dispositivo")
    
    # Configurações de monitoramento
    monitor_interval = models.IntegerField(default=3, verbose_name="Intervalo de Monitoramento (s)")
    log_retention_days = models.IntegerField(default=30, verbose_name="Retenção de Logs (dias)")
    
    # Configurações de API
    api_endpoints = models.JSONField(default=dict, verbose_name="Endpoints da API")
    authentication_method = models.CharField(max_length=50, default='token', verbose_name="Método de Autenticação")
    
    # Configurações de dados
    data_format = models.CharField(max_length=50, default='json', verbose_name="Formato de Dados")
    encoding = models.CharField(max_length=20, default='utf-8', verbose_name="Codificação")
    
    # Configurações de cache
    cache_enabled = models.BooleanField(default=True, verbose_name="Cache Habilitado")
    cache_duration = models.IntegerField(default=60, verbose_name="Duração do Cache (s)")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Configuração de Dispositivo"
        verbose_name_plural = "Configurações de Dispositivos"
    
    def __str__(self):
        return f"Configuração - {self.device.name}"
