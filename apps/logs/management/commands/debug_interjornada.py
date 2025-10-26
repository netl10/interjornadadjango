"""
Comando para debugar o InterjornadaService.
"""
from django.core.management.base import BaseCommand
from apps.employees.models import Employee
from apps.interjornada.services import InterjornadaService
from datetime import datetime


class Command(BaseCommand):
    help = 'Debuga o InterjornadaService'

    def handle(self, *args, **options):
        # Buscar o funcionário
        employee = Employee.objects.filter(device_id=1000905, is_active=True).first()
        
        if not employee:
            self.stdout.write(self.style.ERROR('Funcionário não encontrado'))
            return
        
        self.stdout.write(f'Funcionário: {employee.name} (ID: {employee.device_id})')
        
        # Testar processamento de evento de entrada
        interjornada_service = InterjornadaService()
        
        self.stdout.write('\n=== TESTANDO PROCESSAMENTO DE ENTRADA ===')
        try:
            result = interjornada_service.process_access_event(
                employee=employee,
                event_type=1,  # Entrada
                timestamp=datetime.now(),
                portal_id=1
            )
            self.stdout.write(f'Resultado: {result}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {e}'))
        
        # Testar _process_entry_event_new diretamente
        self.stdout.write('\n=== TESTANDO _process_entry_event_new DIRETAMENTE ===')
        try:
            result = interjornada_service._process_entry_event_new(employee, datetime.now())
            self.stdout.write(f'Resultado direto: {result}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {e}'))
