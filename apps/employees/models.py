"""
Modelos para gerenciamento de funcionários.
"""
from django.db import models
from django.contrib.auth.models import User
from apps.core.utils import TimezoneUtils


class Employee(models.Model):
    """Modelo para funcionários do sistema."""
    
    # ID do dispositivo (IDFace)
    device_id = models.IntegerField(unique=True, verbose_name="ID do Dispositivo")
    
    # Informações pessoais
    name = models.CharField(max_length=255, verbose_name="Nome")
    employee_code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Código do Funcionário")
    
    # Informações de acesso
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_exempt = models.BooleanField(default=False, verbose_name="Isento de Interjornada")
    
    # Grupos e permissões
    groups = models.JSONField(default=list, blank=True, verbose_name="Grupos")
    exemption_groups = models.JSONField(default=list, blank=True, verbose_name="Grupos de Isenção")
    
    # Relacionamento com grupo atual
    group = models.ForeignKey('EmployeeGroup', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Grupo Atual")
    original_group = models.ForeignKey('EmployeeGroup', on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='original_employees', verbose_name="Grupo Original")
    
    # Configurações específicas
    work_duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Duração de Trabalho (min)")
    rest_duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Duração de Interjornada (min)")
    
    # Tipo de aviso para acesso
    ALERT_TYPE_CHOICES = [
        ('', 'Padrão'),
        ('rh', 'RH'),
        ('supervisor', 'Supervisor'),
        ('coordenador', 'Coordenador'),
        ('ti', 'TI'),
    ]
    
    alert_type = models.CharField(
        max_length=20, 
        choices=ALERT_TYPE_CHOICES, 
        default='', 
        blank=True,
        verbose_name="Tipo de Aviso"
    )
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    
    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ['name']
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['employee_code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_exempt']),
        ]
    
    def __str__(self):
        return f"{self.name} (ID: {self.device_id})"
    
    @property
    def display_name(self):
        """Nome para exibição."""
        if self.employee_code:
            return f"{self.name} ({self.employee_code})"
        return self.name
    
    @property
    def effective_work_duration(self):
        """Duração efetiva de trabalho (individual ou padrão do sistema)."""
        from django.conf import settings
        return self.work_duration_minutes or settings.WORK_DURATION_MINUTES
    
    @property
    def effective_rest_duration(self):
        """Duração efetiva de interjornada (individual ou padrão do sistema)."""
        from django.conf import settings
        return self.rest_duration_minutes or settings.REST_DURATION_MINUTES
    
    def is_in_exemption_group(self, group_name=None):
        """
        Verifica se o funcionário está em grupo de isenção.
        
        Args:
            group_name: Nome do grupo (opcional, usa configuração padrão se não informado)
            
        Returns:
            bool: True se está em grupo de isenção
        """
        if self.is_exempt:
            return True
        
        if not group_name:
            from django.conf import settings
            group_name = settings.EXEMPTION_GROUP_NAME
        
        return group_name in self.exemption_groups
    
    def add_to_group(self, group_name):
        """Adiciona funcionário a um grupo."""
        if group_name not in self.groups:
            self.groups.append(group_name)
            self.save(update_fields=['groups'])
    
    def remove_from_group(self, group_name):
        """Remove funcionário de um grupo."""
        if group_name in self.groups:
            self.groups.remove(group_name)
            self.save(update_fields=['groups'])
    
    def add_to_exemption_group(self, group_name):
        """Adiciona funcionário a grupo de isenção."""
        if group_name not in self.exemption_groups:
            self.exemption_groups.append(group_name)
            self.save(update_fields=['exemption_groups'])
    
    def remove_from_exemption_group(self, group_name):
        """Remove funcionário de grupo de isenção."""
        if group_name in self.exemption_groups:
            self.exemption_groups.remove(group_name)
            self.save(update_fields=['exemption_groups'])


class EmployeeGroup(models.Model):
    """Modelo para grupos de funcionários."""
    
    # ID do grupo no dispositivo (IDFace)
    device_group_id = models.IntegerField(unique=True, null=True, blank=True, verbose_name="ID do Grupo no Dispositivo")
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome do Grupo")
    description = models.TextField(blank=True, verbose_name="Descrição")
    is_exemption_group = models.BooleanField(default=False, verbose_name="Grupo de Isenção")
    is_blacklist = models.BooleanField(default=False, verbose_name="Grupo de Blacklist")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Configurações específicas do grupo
    work_duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Duração de Trabalho (min)")
    rest_duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Duração de Interjornada (min)")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Grupo de Funcionários"
        verbose_name_plural = "Grupos de Funcionários"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def employee_count(self):
        """Número de funcionários no grupo."""
        return Employee.objects.filter(groups__contains=[self.name]).count()
    
    @property
    def effective_work_duration(self):
        """Duração efetiva de trabalho do grupo."""
        from django.conf import settings
        return self.work_duration_minutes or settings.WORK_DURATION_MINUTES
    
    @property
    def effective_rest_duration(self):
        """Duração efetiva de interjornada do grupo."""
        from django.conf import settings
        return self.rest_duration_minutes or settings.REST_DURATION_MINUTES
