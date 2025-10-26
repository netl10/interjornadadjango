"""
Modelos para gerenciamento de logs de acesso.
"""
from django.db import models
from django.contrib.auth.models import User
from apps.core.utils import TimezoneUtils


class AccessLog(models.Model):
    """Modelo para logs de acesso dos dispositivos."""
    
    # Tipos de evento (baseado na documentação oficial Control iD)
    EVENT_TYPES = [
        (1, 'Entrada'),
        (2, 'Saída'),
        (3, 'Não Identificado'),
        (4, 'Erro de Leitura'),
        (5, 'Timeout'),
        (6, 'Acesso Negado'),
        (7, 'Acesso Autorizado'),
        (8, 'Acesso Bloqueado'),
        (13, 'Desistência'),
    ]
    
    # Status de processamento
    PROCESSING_STATUS = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('processed', 'Processado'),
        ('error', 'Erro'),
        ('ignored', 'Ignorado'),
    ]
    
    # ID do log no dispositivo
    device_log_id = models.BigIntegerField(unique=True, verbose_name="ID do Log no Dispositivo")
    
    # Flag para identificar logs manuais
    is_manual = models.BooleanField(default=False, verbose_name="Log Manual")
    
    # Informações do usuário
    user_id = models.IntegerField(verbose_name="ID do Usuário")
    user_name = models.CharField(max_length=255, verbose_name="Nome do Usuário")
    
    # Informações do evento
    event_type = models.IntegerField(choices=EVENT_TYPES, verbose_name="Tipo de Evento")
    event_description = models.CharField(max_length=500, verbose_name="Descrição do Evento")
    
    # Informações do dispositivo
    device_id = models.IntegerField(null=True, blank=True, verbose_name="ID do Dispositivo")
    device_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Nome do Dispositivo")
    portal_id = models.IntegerField(null=True, blank=True, verbose_name="ID do Portal")
    
    # Timestamps (sempre em UTC)
    device_timestamp = models.DateTimeField(verbose_name="Timestamp do Dispositivo")
    received_timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp de Recebimento")
    processed_timestamp = models.DateTimeField(null=True, blank=True, verbose_name="Timestamp de Processamento")
    
    # Status de processamento
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS, 
        default='pending', 
        verbose_name="Status de Processamento"
    )
    processing_error = models.TextField(null=True, blank=True, verbose_name="Erro de Processamento")
    
    # Controle de processamento para sessões/interjornada
    session_processed = models.BooleanField(default=False, verbose_name="Processado para Sessão")
    session_processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Processado para Sessão em")
    session_processing_error = models.TextField(null=True, blank=True, verbose_name="Erro no Processamento de Sessão")
    
    # Dados adicionais
    raw_data = models.JSONField(default=dict, blank=True, verbose_name="Dados Brutos")
    processed_data = models.JSONField(default=dict, blank=True, verbose_name="Dados Processados")
    
    # Metadados
    created_at = models.DateTimeField(verbose_name="Criado em")
    updated_at = models.DateTimeField(verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Log de Acesso"
        verbose_name_plural = "Logs de Acesso"
        ordering = ['-device_timestamp']
        indexes = [
            models.Index(fields=['device_log_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['event_type']),
            models.Index(fields=['device_timestamp']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['device_id']),
            models.Index(fields=['session_processed']),
        ]
    
    def __str__(self):
        return f"Log {self.device_log_id} - {self.user_name} - {self.get_event_type_display()}"
    
    @property
    def display_device_timestamp(self):
        """Timestamp do dispositivo formatado para exibição."""
        return TimezoneUtils.format_datetime(self.device_timestamp)
    
    @property
    def display_received_timestamp(self):
        """Timestamp de recebimento formatado para exibição."""
        return TimezoneUtils.format_datetime(self.received_timestamp)
    
    @property
    def display_processed_timestamp(self):
        """Timestamp de processamento formatado para exibição."""
        if self.processed_timestamp:
            return TimezoneUtils.format_datetime(self.processed_timestamp)
        return None
    
    @property
    def is_processed(self):
        """Verifica se o log foi processado."""
        return self.processing_status == 'processed'
    
    @property
    def is_pending(self):
        """Verifica se o log está pendente."""
        return self.processing_status == 'pending'
    
    @property
    def has_error(self):
        """Verifica se o log tem erro."""
        return self.processing_status == 'error'
    
    def mark_as_processed(self, processed_data=None):
        """Marca o log como processado."""
        self.processing_status = 'processed'
        self.processed_timestamp = TimezoneUtils.get_utc_now()
        if processed_data:
            self.processed_data = processed_data
        self.save(update_fields=['processing_status', 'processed_timestamp', 'processed_data'])
    
    def mark_as_error(self, error_message):
        """Marca o log como erro."""
        self.processing_status = 'error'
        self.processing_error = error_message
        self.save(update_fields=['processing_status', 'processing_error'])
    
    def mark_as_ignored(self, reason=None):
        """Marca o log como ignorado."""
        self.processing_status = 'ignored'
        if reason:
            self.processing_error = reason
        self.save(update_fields=['processing_status', 'processing_error'])

    def mark_session_processed(self, session_data=None):
        """Marca o log como processado para lógica de sessões/interjornada."""
        self.session_processed = True
        self.session_processed_at = TimezoneUtils.get_utc_now()
        self.session_processing_error = None
        # Também atualizar o processing_status para 'processed'
        self.processing_status = 'processed'
        self.processed_timestamp = TimezoneUtils.get_utc_now()
        
        if session_data:
            processed_data = self.processed_data or {}
            processed_data.update({'session': session_data})
            self.processed_data = processed_data
            self.save(update_fields=['session_processed', 'session_processed_at', 'session_processing_error', 'processed_data', 'processing_status', 'processed_timestamp'])
        else:
            self.save(update_fields=['session_processed', 'session_processed_at', 'session_processing_error', 'processing_status', 'processed_timestamp'])

    def mark_session_error(self, error_message, session_data=None):
        """Marca o log como processado, porém com erro na lógica de sessão."""
        self.session_processed = True
        self.session_processed_at = TimezoneUtils.get_utc_now()
        self.session_processing_error = error_message
        # Também atualizar o processing_status para 'error'
        self.processing_status = 'error'
        self.processing_error = error_message
        self.processed_timestamp = TimezoneUtils.get_utc_now()
        
        update_fields = ['session_processed', 'session_processed_at', 'session_processing_error', 'processing_status', 'processing_error', 'processed_timestamp']
        if session_data:
            processed_data = self.processed_data or {}
            processed_data.update({'session': session_data})
            self.processed_data = processed_data
            update_fields.append('processed_data')
        self.save(update_fields=update_fields)


class SystemLog(models.Model):
    """Modelo para logs do sistema."""
    
    # Níveis de log
    LOG_LEVELS = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Informação'),
        ('WARNING', 'Aviso'),
        ('ERROR', 'Erro'),
        ('CRITICAL', 'Crítico'),
    ]
    
    # Categorias de log
    LOG_CATEGORIES = [
        ('system', 'Sistema'),
        ('device', 'Dispositivo'),
        ('employee', 'Funcionário'),
        ('interjornada', 'Interjornada'),
        ('authentication', 'Autenticação'),
        ('database', 'Banco de Dados'),
        ('api', 'API'),
        ('websocket', 'WebSocket'),
        ('monitoring', 'Monitoramento'),
    ]
    
    level = models.CharField(max_length=10, choices=LOG_LEVELS, verbose_name="Nível")
    category = models.CharField(max_length=20, choices=LOG_CATEGORIES, verbose_name="Categoria")
    message = models.TextField(verbose_name="Mensagem")
    
    # Informações do usuário (opcional)
    user_id = models.IntegerField(null=True, blank=True, verbose_name="ID do Usuário")
    user_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Nome do Usuário")
    
    # Informações do dispositivo (opcional)
    device_id = models.IntegerField(null=True, blank=True, verbose_name="ID do Dispositivo")
    device_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Nome do Dispositivo")
    
    # Dados adicionais
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes")
    
    # Metadados
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")
    
    class Meta:
        verbose_name = "Log do Sistema"
        verbose_name_plural = "Logs do Sistema"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['category']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user_id']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        return f"{self.level} - {self.category} - {self.timestamp}"
    
    @property
    def display_timestamp(self):
        """Timestamp formatado para exibição."""
        return TimezoneUtils.format_datetime(self.timestamp)
    
    @classmethod
    def log_info(cls, message, category='system', user_id=None, user_name=None, 
                 device_id=None, device_name=None, details=None):
        """Cria log de informação."""
        return cls.objects.create(
            level='INFO',
            category=category,
            message=message,
            user_id=user_id,
            user_name=user_name,
            device_id=device_id,
            device_name=device_name,
            details=details or {}
        )
    
    @classmethod
    def log_warning(cls, message, category='system', user_id=None, user_name=None, 
                   device_id=None, device_name=None, details=None):
        """Cria log de aviso."""
        return cls.objects.create(
            level='WARNING',
            category=category,
            message=message,
            user_id=user_id,
            user_name=user_name,
            device_id=device_id,
            device_name=device_name,
            details=details or {}
        )
    
    @classmethod
    def log_error(cls, message, category='system', user_id=None, user_name=None, 
                 device_id=None, device_name=None, details=None):
        """Cria log de erro."""
        return cls.objects.create(
            level='ERROR',
            category=category,
            message=message,
            user_id=user_id,
            user_name=user_name,
            device_id=device_id,
            device_name=device_name,
            details=details or {}
        )
    
    @classmethod
    def log_critical(cls, message, category='system', user_id=None, user_name=None, 
                    device_id=None, device_name=None, details=None):
        """Cria log crítico."""
        return cls.objects.create(
            level='CRITICAL',
            category=category,
            message=message,
            user_id=user_id,
            user_name=user_name,
            device_id=device_id,
            device_name=device_name,
            details=details or {}
        )


class LogProcessingQueue(models.Model):
    """Modelo para fila de processamento de logs."""
    
    # Status da fila
    QUEUE_STATUS = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou'),
        ('retry', 'Tentar Novamente'),
    ]
    
    access_log = models.ForeignKey(AccessLog, on_delete=models.CASCADE, related_name='queue_entries', verbose_name="Log de Acesso")
    status = models.CharField(max_length=20, choices=QUEUE_STATUS, default='pending', verbose_name="Status")
    priority = models.IntegerField(default=0, verbose_name="Prioridade")
    
    # Informações de processamento
    attempts = models.IntegerField(default=0, verbose_name="Tentativas")
    max_attempts = models.IntegerField(default=3, verbose_name="Máximo de Tentativas")
    last_attempt = models.DateTimeField(null=True, blank=True, verbose_name="Última Tentativa")
    next_retry = models.DateTimeField(null=True, blank=True, verbose_name="Próxima Tentativa")
    
    # Erros
    error_message = models.TextField(null=True, blank=True, verbose_name="Mensagem de Erro")
    error_details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes do Erro")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Entrada da Fila de Processamento"
        verbose_name_plural = "Fila de Processamento de Logs"
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['next_retry']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Fila {self.access_log.device_log_id} - {self.get_status_display()}"
    
    @property
    def can_retry(self):
        """Verifica se pode tentar novamente."""
        return self.attempts < self.max_attempts and self.status in ['failed', 'retry']
    
    @property
    def is_ready_for_processing(self):
        """Verifica se está pronto para processamento."""
        if self.status != 'pending':
            return False
        
        if self.next_retry and self.next_retry > TimezoneUtils.get_utc_now():
            return False
        
        return True
    
    def mark_as_processing(self):
        """Marca como processando."""
        self.status = 'processing'
        self.attempts += 1
        self.last_attempt = TimezoneUtils.get_utc_now()
        self.save(update_fields=['status', 'attempts', 'last_attempt'])
    
    def mark_as_completed(self):
        """Marca como concluído."""
        self.status = 'completed'
        self.save(update_fields=['status'])
    
    def mark_as_failed(self, error_message, error_details=None):
        """Marca como falhou."""
        self.status = 'failed'
        self.error_message = error_message
        if error_details:
            self.error_details = error_details
        
        # Calcular próxima tentativa se ainda pode tentar
        if self.can_retry:
            from datetime import timedelta
            retry_delay = 2 ** self.attempts  # Backoff exponencial
            self.next_retry = TimezoneUtils.get_utc_now() + timedelta(minutes=retry_delay)
            self.status = 'retry'
        
        self.save(update_fields=['status', 'error_message', 'error_details', 'next_retry'])
