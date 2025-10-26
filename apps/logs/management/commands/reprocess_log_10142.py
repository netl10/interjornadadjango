"""
Comando para reprocessar o log 10142.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.logs.services import LogMonitorService


class Command(BaseCommand):
    help = 'Reprocessa o log 10142'

    def handle(self, *args, **options):
        # Buscar o log específico
        log = AccessLog.objects.filter(device_log_id=10142).first()
        
        if not log:
            self.stdout.write(self.style.ERROR('Log 10142 não encontrado'))
            return
        
        self.stdout.write(f'Reprocessando log {log.device_log_id}...')
        
        # Resetar status de processamento
        log.session_processed = False
        log.processing_status = 'pending'
        log.processed_data = {}
        log.processing_error = None
        log.save()
        
        # Reprocessar usando o LogMonitorService
        monitor = LogMonitorService()
        monitor.process_access_log(log)
        
        # Verificar resultado
        log.refresh_from_db()
        self.stdout.write(f'Status após reprocessamento: {log.processing_status}')
        self.stdout.write(f'Sessão processada: {log.session_processed}')
        self.stdout.write(f'Dados processados: {log.processed_data}')
        
        if log.processing_error:
            self.stdout.write(self.style.ERROR(f'Erro: {log.processing_error}'))
        else:
            self.stdout.write(self.style.SUCCESS('Log reprocessado com sucesso!'))
