"""
Comando para debugar por que as sessões estão sendo deletadas.
"""
from django.core.management.base import BaseCommand
from apps.employees.models import Employee
from apps.employee_sessions.models import EmployeeSession
from apps.employee_sessions.services import session_service
from apps.interjornada.services import InterjornadaService
from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Debuga por que as sessões estão sendo deletadas'

    def handle(self, *args, **options):
        # Buscar o funcionário
        employee = Employee.objects.filter(device_id=1000905, is_active=True).first()
        
        if not employee:
            self.stdout.write(self.style.ERROR('Funcionário não encontrado'))
            return
        
        self.stdout.write(f'Funcionário: {employee.name} (ID: {employee.device_id})')
        
        # Verificar configurações do sistema
        from apps.core.models import SystemConfiguration
        config = SystemConfiguration.objects.get(id=1)
        self.stdout.write(f'\n=== CONFIGURAÇÕES ===')
        self.stdout.write(f'Tempo de acesso livre: {config.liberado_minutes} minutos')
        self.stdout.write(f'Tempo de interjornada: {config.bloqueado_minutes} minutos')
        
        # Verificar se há sessões ativas
        active_sessions = EmployeeSession.objects.filter(employee=employee)
        self.stdout.write(f'\n=== SESSÕES ATUAIS ===')
        self.stdout.write(f'Total de sessões: {active_sessions.count()}')
        
        for session in active_sessions:
            self.stdout.write(f'Sessão {session.id}: {session.state}')
            self.stdout.write(f'  - Primeiro acesso: {session.first_access}')
            self.stdout.write(f'  - Último acesso: {session.last_access}')
            self.stdout.write(f'  - Início do bloqueio: {session.block_start}')
            self.stdout.write(f'  - Horário de retorno: {session.return_time}')
            self.stdout.write(f'  - Duração trabalho: {session.work_duration_minutes} min')
            self.stdout.write(f'  - Duração interjornada: {session.rest_duration_minutes} min')
            
            # Calcular tempos
            now = timezone.now()
            if session.first_access:
                tempo_decorrido = now - session.first_access
                self.stdout.write(f'  - Tempo decorrido: {tempo_decorrido.total_seconds()/60:.1f} min')
            
            if session.return_time:
                tempo_restante = session.return_time - now
                self.stdout.write(f'  - Tempo restante interjornada: {tempo_restante.total_seconds()/60:.1f} min')
        
        # Testar criação de nova sessão
        self.stdout.write(f'\n=== TESTANDO CRIAÇÃO DE SESSÃO ===')
        try:
            new_session = session_service.create_user_session(employee, timezone.now())
            self.stdout.write(f'Nova sessão criada: {new_session.id} - {new_session.state}')
            
            # Aguardar um pouco e verificar se ainda existe
            import time
            time.sleep(2)
            
            new_session.refresh_from_db()
            if EmployeeSession.objects.filter(id=new_session.id).exists():
                self.stdout.write(f'Sessão ainda existe após 2 segundos')
            else:
                self.stdout.write(self.style.ERROR(f'Sessão foi deletada automaticamente!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao criar sessão: {e}'))
        
        # Verificar se há algum processo em background deletando sessões
        self.stdout.write(f'\n=== VERIFICANDO PROCESSOS EM BACKGROUND ===')
        from apps.logs.services import log_monitor_service
        monitor_status = log_monitor_service.get_status()
        self.stdout.write(f'Monitor rodando: {monitor_status.get("running", False)}')
        
        # Verificar se o enforce_session_timeouts está sendo executado
        try:
            log_monitor_service.enforce_session_timeouts()
            self.stdout.write('enforce_session_timeouts executado')
        except Exception as e:
            self.stdout.write(f'Erro ao executar enforce_session_timeouts: {e}')
