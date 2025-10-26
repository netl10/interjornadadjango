"""
Comando para verificar o processamento do log 10142.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.employees.models import Employee
from apps.employee_sessions.models import EmployeeSession


class Command(BaseCommand):
    help = 'Verifica o processamento do log 10142'

    def handle(self, *args, **options):
        # Buscar o log específico
        log = AccessLog.objects.filter(device_log_id=10142).first()
        
        if not log:
            self.stdout.write(self.style.ERROR('Log 10142 não encontrado'))
            return
        
        self.stdout.write(f'=== LOG 10142 ===')
        self.stdout.write(f'ID: {log.device_log_id}')
        self.stdout.write(f'Usuário: {log.user_name} (ID: {log.user_id})')
        self.stdout.write(f'Evento: {log.event_description}')
        self.stdout.write(f'Portal: {log.portal_id}')
        self.stdout.write(f'Timestamp: {log.device_timestamp}')
        self.stdout.write(f'Status: {log.processing_status}')
        self.stdout.write(f'Sessão processada: {log.session_processed}')
        self.stdout.write(f'Dados processados: {log.processed_data}')
        self.stdout.write(f'Erro: {log.processing_error}')
        
        # Verificar se o funcionário existe
        employee = Employee.objects.filter(device_id=log.user_id, is_active=True).first()
        if employee:
            self.stdout.write(f'\n=== FUNCIONÁRIO ===')
            self.stdout.write(f'Nome: {employee.name}')
            self.stdout.write(f'ID: {employee.device_id}')
            self.stdout.write(f'Ativo: {employee.is_active}')
            
            # Verificar sessões do funcionário
            sessions = EmployeeSession.objects.filter(employee=employee)
            self.stdout.write(f'\n=== SESSÕES ===')
            self.stdout.write(f'Total de sessões: {sessions.count()}')
            
            for session in sessions:
                self.stdout.write(f'Sessão {session.id}: {session.state} - {session.first_access}')
        else:
            self.stdout.write(self.style.ERROR(f'Funcionário com ID {log.user_id} não encontrado ou inativo'))
        
        # Verificar mapeamento de evento
        from apps.logs.services import LogMonitorService
        monitor = LogMonitorService()
        event_type = monitor.map_to_interjornada_event(log.event_description, log.portal_id)
        self.stdout.write(f'\n=== MAPEAMENTO ===')
        self.stdout.write(f'Evento mapeado: {event_type}')
        
        if event_type:
            self.stdout.write(f'Deve processar: SIM')
        else:
            self.stdout.write(f'Deve processar: NÃO (evento não mapeado)')
