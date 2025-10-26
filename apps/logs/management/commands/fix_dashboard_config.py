"""
Comando para corrigir as configurações do dashboard.
"""
from django.core.management.base import BaseCommand
from apps.core.models import SystemConfiguration
from apps.employees.models import Employee
from apps.employee_sessions.services import session_service
from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Corrige as configurações do dashboard'

    def handle(self, *args, **options):
        # Ajustar configurações do sistema
        config, created = SystemConfiguration.objects.get_or_create(
            id=1,
            defaults={
                'liberado_minutes': 480,  # 8 horas
                'bloqueado_minutes': 672,    # 11.2 horas
                'device_ip': '192.168.1.251',
                'giro_validation_timeout': 30,
                'timezone_offset': -3,
            }
        )
        
        if not created:
            # Atualizar configurações existentes
            config.liberado_minutes = 480  # 8 horas
            config.bloqueado_minutes = 672  # 11.2 horas
            config.save()
        
        self.stdout.write(f'Configurações atualizadas:')
        self.stdout.write(f'  - Tempo de acesso livre: {config.liberado_minutes} minutos ({config.liberado_minutes/60:.1f} horas)')
        self.stdout.write(f'  - Tempo de interjornada: {config.bloqueado_minutes} minutos ({config.bloqueado_minutes/60:.1f} horas)')
        
        # Criar uma sessão de teste para o funcionário
        employee = Employee.objects.filter(device_id=1000905, is_active=True).first()
        if employee:
            # Verificar se já tem sessão ativa
            existing_session = session_service.get_user_session(employee)
            if existing_session:
                self.stdout.write(f'Funcionário já tem sessão ativa: {existing_session.id} - {existing_session.state}')
            else:
                # Criar nova sessão
                new_session = session_service.create_user_session(employee, timezone.now())
                self.stdout.write(f'Nova sessão criada: {new_session.id} - {new_session.state}')
                self.stdout.write(f'  - Primeiro acesso: {new_session.first_access}')
                self.stdout.write(f'  - Duração trabalho: {new_session.work_duration_minutes} minutos')
                self.stdout.write(f'  - Duração interjornada: {new_session.rest_duration_minutes} minutos')
        else:
            self.stdout.write(self.style.ERROR('Funcionário não encontrado'))
        
        # Verificar sessões ativas
        from apps.employee_sessions.models import EmployeeSession
        active_sessions = EmployeeSession.objects.filter(
            state__in=['active', 'blocked', 'pending_rest']
        )
        self.stdout.write(f'\nTotal de sessões ativas: {active_sessions.count()}')
        
        for session in active_sessions:
            self.stdout.write(f'  - Sessão {session.id}: {session.employee.name} - {session.state}')
        
        self.stdout.write(self.style.SUCCESS('\nDashboard deve funcionar agora!'))
        self.stdout.write('Acesse: http://localhost:8000/admin/sessions/dashboard/')
