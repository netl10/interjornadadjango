"""
Modelos para lógica de interjornada.
"""
from django.db import models
from django.contrib.auth.models import User
from apps.core.utils import TimezoneUtils


class InterjornadaRule(models.Model):
    """Modelo para regras de interjornada."""
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome da Regra")
    description = models.TextField(blank=True, verbose_name="Descrição")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    
    # Configurações de tempo
    work_duration_minutes = models.IntegerField(verbose_name="Duração de Trabalho (min)")
    rest_duration_minutes = models.IntegerField(verbose_name="Duração de Interjornada (min)")
    
    # Configurações de aplicação
    apply_to_all = models.BooleanField(default=False, verbose_name="Aplicar a Todos")
    employee_groups = models.JSONField(default=list, blank=True, verbose_name="Grupos de Funcionários")
    exempt_employee_groups = models.JSONField(default=list, blank=True, verbose_name="Grupos Isentos")
    
    # Configurações de horário
    start_time = models.TimeField(null=True, blank=True, verbose_name="Horário de Início")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Horário de Fim")
    days_of_week = models.JSONField(default=list, blank=True, verbose_name="Dias da Semana")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    
    class Meta:
        verbose_name = "Regra de Interjornada"
        verbose_name_plural = "Regras de Interjornada"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def work_duration_formatted(self):
        """Duração de trabalho formatada."""
        hours = self.work_duration_minutes // 60
        minutes = self.work_duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}min"
        return f"{minutes}min"
    
    @property
    def rest_duration_formatted(self):
        """Duração de interjornada formatada."""
        hours = self.rest_duration_minutes // 60
        minutes = self.rest_duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}min"
        return f"{minutes}min"


class InterjornadaCycle(models.Model):
    """Modelo para ciclos de interjornada."""
    
    # Estados do ciclo
    CYCLE_STATES = [
        ('work', 'Trabalho'),
        ('rest', 'Interjornada'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado'),
    ]
    
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='cycles', verbose_name="Funcionário")
    rule = models.ForeignKey(InterjornadaRule, on_delete=models.CASCADE, related_name='cycles', verbose_name="Regra")
    
    # Estado atual
    current_state = models.CharField(max_length=20, choices=CYCLE_STATES, default='work', verbose_name="Estado Atual")
    
    # Timestamps do ciclo
    cycle_start = models.DateTimeField(verbose_name="Início do Ciclo")
    work_start = models.DateTimeField(verbose_name="Início do Trabalho")
    work_end = models.DateTimeField(null=True, blank=True, verbose_name="Fim do Trabalho")
    rest_start = models.DateTimeField(null=True, blank=True, verbose_name="Início da Interjornada")
    rest_end = models.DateTimeField(null=True, blank=True, verbose_name="Fim da Interjornada")
    
    # Durações efetivas
    actual_work_duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Duração Real de Trabalho (min)")
    actual_rest_duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Duração Real de Interjornada (min)")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Ciclo de Interjornada"
        verbose_name_plural = "Ciclos de Interjornada"
        ordering = ['-cycle_start']
        indexes = [
            models.Index(fields=['employee', 'current_state']),
            models.Index(fields=['current_state']),
            models.Index(fields=['cycle_start']),
        ]
    
    def __str__(self):
        return f"Ciclo {self.employee.name} - {self.get_current_state_display()}"
    
    @property
    def is_active(self):
        """Verifica se o ciclo está ativo."""
        return self.current_state in ['work', 'rest']
    
    @property
    def is_work_period(self):
        """Verifica se está no período de trabalho."""
        return self.current_state == 'work'
    
    @property
    def is_rest_period(self):
        """Verifica se está no período de interjornada."""
        return self.current_state == 'rest'
    
    @property
    def work_time_remaining(self):
        """Calcula tempo restante de trabalho."""
        if not self.is_work_period:
            return None
        
        now = TimezoneUtils.get_utc_now()
        work_end_time = TimezoneUtils.add_minutes(self.work_start, self.rule.work_duration_minutes)
        
        return TimezoneUtils.get_time_remaining(work_end_time)
    
    @property
    def rest_time_remaining(self):
        """Calcula tempo restante de interjornada."""
        if not self.is_rest_period or not self.rest_start:
            return None
        
        now = TimezoneUtils.get_utc_now()
        rest_end_time = TimezoneUtils.add_minutes(self.rest_start, self.rule.rest_duration_minutes)
        
        return TimezoneUtils.get_time_remaining(rest_end_time)
    
    @property
    def can_start_work(self):
        """Verifica se pode iniciar trabalho."""
        if self.current_state == 'work':
            return False
        
        if self.current_state == 'rest':
            time_remaining = self.rest_time_remaining
            return time_remaining and time_remaining['is_expired']
        
        return True
    
    @property
    def should_start_rest(self):
        """Verifica se deve iniciar interjornada."""
        if self.current_state != 'work':
            return False
        
        time_remaining = self.work_time_remaining
        return time_remaining and time_remaining['is_expired']
    
    def start_work_period(self):
        """Inicia período de trabalho."""
        now = TimezoneUtils.get_utc_now()
        
        self.current_state = 'work'
        self.work_start = now
        
        if not self.cycle_start:
            self.cycle_start = now
        
        self.save(update_fields=['current_state', 'work_start', 'cycle_start'])
    
    def start_rest_period(self):
        """Inicia período de interjornada."""
        now = TimezoneUtils.get_utc_now()
        
        # Calcular duração real de trabalho
        if self.work_start:
            work_duration = now - self.work_start
            self.actual_work_duration_minutes = int(work_duration.total_seconds() / 60)
            self.work_end = now
        
        self.current_state = 'rest'
        self.rest_start = now
        self.save(update_fields=['current_state', 'rest_start', 'work_end', 'actual_work_duration_minutes'])
    
    def complete_cycle(self):
        """Completa o ciclo."""
        now = TimezoneUtils.get_utc_now()
        
        # Calcular duração real de interjornada
        if self.rest_start:
            rest_duration = now - self.rest_start
            self.actual_rest_duration_minutes = int(rest_duration.total_seconds() / 60)
            self.rest_end = now
        
        self.current_state = 'completed'
        self.save(update_fields=['current_state', 'rest_end', 'actual_rest_duration_minutes'])
    
    def cancel_cycle(self):
        """Cancela o ciclo."""
        self.current_state = 'cancelled'
        self.save(update_fields=['current_state'])


class InterjornadaViolation(models.Model):
    """Modelo para violações de interjornada."""
    
    # Tipos de violação
    VIOLATION_TYPES = [
        ('early_access', 'Acesso Antecipado'),
        ('late_access', 'Acesso Tardio'),
        ('exceeded_work_time', 'Tempo de Trabalho Excedido'),
        ('insufficient_rest', 'Interjornada Insuficiente'),
        ('unauthorized_access', 'Acesso Não Autorizado'),
    ]
    
    # Severidades
    SEVERITY_LEVELS = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    cycle = models.ForeignKey(InterjornadaCycle, on_delete=models.CASCADE, related_name='violations', verbose_name="Ciclo")
    violation_type = models.CharField(max_length=30, choices=VIOLATION_TYPES, verbose_name="Tipo de Violação")
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium', verbose_name="Severidade")
    
    # Descrição da violação
    description = models.TextField(verbose_name="Descrição")
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes")
    
    # Timestamps
    violation_time = models.DateTimeField(verbose_name="Horário da Violação")
    detected_time = models.DateTimeField(auto_now_add=True, verbose_name="Horário de Detecção")
    
    # Ações tomadas
    action_taken = models.TextField(null=True, blank=True, verbose_name="Ação Tomada")
    resolved = models.BooleanField(default=False, verbose_name="Resolvida")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Resolvida em")
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Resolvida por")
    
    class Meta:
        verbose_name = "Violação de Interjornada"
        verbose_name_plural = "Violações de Interjornada"
        ordering = ['-violation_time']
        indexes = [
            models.Index(fields=['violation_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['violation_time']),
            models.Index(fields=['resolved']),
        ]
    
    def __str__(self):
        return f"Violation {self.cycle.employee.name} - {self.get_violation_type_display()}"
    
    @property
    def display_violation_time(self):
        """Horário da violação formatado."""
        return TimezoneUtils.format_datetime(self.violation_time)
    
    @property
    def display_detected_time(self):
        """Horário de detecção formatado."""
        return TimezoneUtils.format_datetime(self.detected_time)
    
    def resolve(self, user, action_taken):
        """Resolve a violação."""
        self.resolved = True
        self.resolved_at = TimezoneUtils.get_utc_now()
        self.resolved_by = user
        self.action_taken = action_taken
        self.save(update_fields=['resolved', 'resolved_at', 'resolved_by', 'action_taken'])


class InterjornadaStatistics(models.Model):
    """Modelo para estatísticas de interjornada."""
    
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='interjornada_stats', verbose_name="Funcionário")
    date = models.DateField(verbose_name="Data")
    
    # Estatísticas do dia
    total_cycles = models.IntegerField(default=0, verbose_name="Total de Ciclos")
    completed_cycles = models.IntegerField(default=0, verbose_name="Ciclos Concluídos")
    cancelled_cycles = models.IntegerField(default=0, verbose_name="Ciclos Cancelados")
    
    # Tempos
    total_work_time_minutes = models.IntegerField(default=0, verbose_name="Tempo Total de Trabalho (min)")
    total_rest_time_minutes = models.IntegerField(default=0, verbose_name="Tempo Total de Interjornada (min)")
    average_work_time_minutes = models.FloatField(default=0, verbose_name="Tempo Médio de Trabalho (min)")
    average_rest_time_minutes = models.FloatField(default=0, verbose_name="Tempo Médio de Interjornada (min)")
    
    # Violações
    total_violations = models.IntegerField(default=0, verbose_name="Total de Violações")
    resolved_violations = models.IntegerField(default=0, verbose_name="Violações Resolvidas")
    critical_violations = models.IntegerField(default=0, verbose_name="Violações Críticas")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Estatística de Interjornada"
        verbose_name_plural = "Estatísticas de Interjornada"
        ordering = ['-date']
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Stats {self.employee.name} - {self.date}"
    
    @property
    def completion_rate(self):
        """Taxa de conclusão de ciclos."""
        if self.total_cycles == 0:
            return 0
        return (self.completed_cycles / self.total_cycles) * 100
    
    @property
    def violation_rate(self):
        """Taxa de violações."""
        if self.total_cycles == 0:
            return 0
        return (self.total_violations / self.total_cycles) * 100
    
    @property
    def work_time_formatted(self):
        """Tempo de trabalho formatado."""
        hours = self.total_work_time_minutes // 60
        minutes = self.total_work_time_minutes % 60
        return f"{hours}h {minutes}min"
    
    @property
    def rest_time_formatted(self):
        """Tempo de interjornada formatado."""
        hours = self.total_rest_time_minutes // 60
        minutes = self.total_rest_time_minutes % 60
        return f"{hours}h {minutes}min"
