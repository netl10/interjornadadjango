"""
Modelos para configurações do sistema.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class SystemConfiguration(models.Model):
    """Modelo para configurações do sistema de interjornada."""
    
    # Configurações de conexão com dispositivos
    device_ip = models.GenericIPAddressField(
        default='192.168.1.251',
        verbose_name="IP do Dispositivo Principal"
    )
    device_port = models.PositiveIntegerField(
        default=443,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name="Porta do Dispositivo Principal"
    )
    device_username = models.CharField(
        max_length=100,
        default='admin',
        verbose_name="Usuário do Dispositivo"
    )
    device_password = models.CharField(
        max_length=100,
        default='admin',
        verbose_name="Senha do Dispositivo"
    )
    
    # Configurações de dispositivo secundário
    secondary_device_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP do Dispositivo Secundário"
    )
    secondary_device_port = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name="Porta do Dispositivo Secundário"
    )
    secondary_device_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Usuário do Dispositivo Secundário"
    )
    secondary_device_password = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Senha do Dispositivo Secundário"
    )
    
    # Configurações de timezone
    timezone_offset = models.IntegerField(
        default=-3,
        validators=[MinValueValidator(-12), MaxValueValidator(14)],
        verbose_name="Offset de Timezone (UTC)",
        help_text="Ex: -3 para Brasil (UTC-3), 0 para UTC"
    )
    
    # Configurações de tempo
    giro_validation_timeout = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        verbose_name="Timeout de Validação de Giro (segundos)"
    )
    monitor_interval = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        verbose_name="Intervalo de Monitoramento (segundos)"
    )
    
    # Configurações de interjornada
    liberado_minutes = models.PositiveIntegerField(
        default=480,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        verbose_name="Tempo de Acesso Livre (minutos)",
        help_text="Tempo em minutos que o usuário pode acessar livremente"
    )
    bloqueado_minutes = models.PositiveIntegerField(
        default=672,
        validators=[MinValueValidator(1), MaxValueValidator(10080)],
        verbose_name="Tempo de Interjornada (minutos)",
        help_text="Tempo em minutos de bloqueio após o acesso"
    )
    
    # Configurações de grupos
    exemption_group_name = models.CharField(
        max_length=100,
        default='whitelist',
        verbose_name="Nome do Grupo de Exceção",
        help_text="Usuários neste grupo não seguem regras de interjornada"
    )
    
    # Configurações de reinício automático
    restart_time_1 = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Horário de Reinício 1",
        help_text="Formato: HH:MM (deixe vazio para desabilitar)"
    )
    restart_time_2 = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Horário de Reinício 2"
    )
    restart_time_3 = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Horário de Reinício 3"
    )
    restart_time_4 = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Horário de Reinício 4"
    )
    
    # Configurações de SSL
    ssl_verify = models.BooleanField(
        default=False,
        verbose_name="Verificar SSL",
        help_text="Verificar certificados SSL (desabilitar para desenvolvimento)"
    )
    
    # Configurações de logs
    max_logs_per_request = models.PositiveIntegerField(
        default=1000,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        verbose_name="Máximo de Logs por Requisição",
        help_text="Limite para não sobrecarregar a catraca"
    )
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    is_active = models.BooleanField(default=True, verbose_name="Configuração Ativa")
    
    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Configuração do Sistema - {self.device_ip}:{self.device_port}"
    
    def save(self, *args, **kwargs):
        # Garantir que apenas uma configuração esteja ativa
        if self.is_active:
            SystemConfiguration.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """Retorna a configuração ativa do sistema."""
        config = cls.objects.filter(is_active=True).first()
        if not config:
            # Criar configuração padrão se não existir
            config = cls.objects.create()
        return config
    
    def get_timezone_info(self):
        """Retorna informações do timezone."""
        offset = self.timezone_offset
        if offset == 0:
            return "UTC"
        elif offset > 0:
            return f"UTC+{offset}"
        else:
            return f"UTC{offset}"
    
    def get_liberado_hours(self):
        """Retorna tempo liberado em horas."""
        return self.liberado_minutes / 60
    
    def get_bloqueado_hours(self):
        """Retorna tempo bloqueado em horas."""
        return self.bloqueado_minutes / 60
    
    def get_restart_times(self):
        """Retorna lista de horários de reinício ativos."""
        times = []
        for i in range(1, 5):
            time_field = getattr(self, f'restart_time_{i}')
            if time_field:
                times.append(time_field.strftime('%H:%M'))
        return times
