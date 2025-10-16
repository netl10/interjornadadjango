"""
Modelos para sessões de funcionários.
"""
from django.db import models
from apps.employees.models import Employee
from apps.core.utils import TimezoneUtils


class EmployeeSession(models.Model):
    """Modelo para sessões de funcionários."""
    
    # Estados possíveis
    STATE_CHOICES = [
        ('active', 'Ativo'),
        ('pending_rest', 'Aguardando Interjornada'),
        ('blocked', 'Bloqueado'),
        ('completed', 'Concluído'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sessions', verbose_name="Funcionário")
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='active', verbose_name="Estado")
    
    # Timestamps (sempre em UTC)
    first_access = models.DateTimeField(verbose_name="Primeiro Acesso")
    last_access = models.DateTimeField(null=True, blank=True, verbose_name="Último Acesso")
    block_start = models.DateTimeField(null=True, blank=True, verbose_name="Início do Bloqueio")
    return_time = models.DateTimeField(null=True, blank=True, verbose_name="Horário de Retorno")
    
    # Informações do ciclo
    work_duration_minutes = models.IntegerField(verbose_name="Duração de Trabalho (min)")
    rest_duration_minutes = models.IntegerField(verbose_name="Duração de Interjornada (min)")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Sessão de Funcionário"
        verbose_name_plural = "Sessões de Funcionários"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'state']),
            models.Index(fields=['state']),
            models.Index(fields=['first_access']),
            models.Index(fields=['return_time']),
        ]
    
    def __str__(self):
        return f"Sessão {self.employee.name} - {self.get_state_display()}"
    
    @property
    def is_active(self):
        """Verifica se a sessão está ativa."""
        return self.state in ['active', 'pending_rest']
    
    @property
    def is_blocked(self):
        """Verifica se a sessão está bloqueada."""
        return self.state == 'blocked'
    
    @property
    def time_remaining_until_return(self):
        """Calcula tempo restante até o retorno."""
        if not self.return_time:
            return None
        return TimezoneUtils.get_time_remaining(self.return_time)
    
    @property
    def display_first_access(self):
        """Primeiro acesso formatado para exibição."""
        return TimezoneUtils.format_datetime(self.first_access)
    
    @property
    def display_last_access(self):
        """Último acesso formatado para exibição."""
        if self.last_access:
            return TimezoneUtils.format_datetime(self.last_access)
        return None
    
    @property
    def display_block_start(self):
        """Início do bloqueio formatado para exibição."""
        if self.block_start:
            return TimezoneUtils.format_datetime(self.block_start)
        return None
    
    @property
    def display_return_time(self):
        """Horário de retorno formatado para exibição."""
        if self.return_time:
            return TimezoneUtils.format_datetime(self.return_time)
        return None
    
    def can_access(self):
        """
        Verifica se o funcionário pode acessar.
        
        Returns:
            dict: {'can_access': bool, 'reason': str, 'return_time': datetime}
        """
        if self.state == 'active':
            return {
                'can_access': True,
                'reason': 'Funcionário em período de trabalho',
                'return_time': None
            }
        
        elif self.state == 'pending_rest':
            return {
                'can_access': False,
                'reason': 'Funcionário deve iniciar interjornada',
                'return_time': None
            }
        
        elif self.state == 'blocked':
            time_remaining = self.time_remaining_until_return
            if time_remaining and time_remaining['is_expired']:
                return {
                    'can_access': True,
                    'reason': 'Período de interjornada expirado',
                    'return_time': None
                }
            else:
                return {
                    'can_access': False,
                    'reason': 'Funcionário em período de interjornada',
                    'return_time': self.return_time
                }
        
        else:
            return {
                'can_access': False,
                'reason': 'Sessão não ativa',
                'return_time': None
            }
    
    def start_work_session(self):
        """Inicia uma nova sessão de trabalho."""
        now = TimezoneUtils.get_utc_now()
        self.state = 'active'
        self.first_access = now
        self.last_access = now
        self.block_start = None
        self.return_time = None
        self.save()
    
    def start_rest_period(self):
        """Inicia período de interjornada."""
        now = TimezoneUtils.get_utc_now()
        self.state = 'blocked'
        self.block_start = now
        self.return_time = TimezoneUtils.add_minutes(now, self.rest_duration_minutes)
        self.save()
    
    def end_session(self):
        """Finaliza a sessão."""
        self.state = 'completed'
        self.save()