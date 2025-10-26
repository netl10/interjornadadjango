#!/usr/bin/env python
"""
Comando para verificar status do sistema de análise em tempo real.
"""
from django.core.management.base import BaseCommand
from apps.logs.services import log_monitor_service
from apps.employees.models import EmployeeSession
from apps.logs.models import AccessLog


class Command(BaseCommand):
    help = 'Verifica status do sistema de análise em tempo real'

    def handle(self, *args, **options):
        self.stdout.write('📊 VERIFICANDO STATUS DO SISTEMA...')
        
        # Verificar status do monitoramento
        status = log_monitor_service.get_status()
        self.stdout.write(f'📊 STATUS DO MONITORAMENTO:')
        self.stdout.write(f'   Rodando: {status.get("running", False)}')
        self.stdout.write(f'   Último ID processado: {status.get("last_processed_id", 0)}')
        self.stdout.write(f'   Logs pendentes: {status.get("pending_logs", "?")}')
        last_processed_at = status.get('last_session_processed_at')
        if last_processed_at:
            self.stdout.write(f'   Último processamento: {last_processed_at}')
        
        # Verificar sessões atuais
        sessoes = EmployeeSession.objects.all()
        self.stdout.write(f'\n📊 SESSÕES ATUAIS: {sessoes.count()}')
        for sessao in sessoes:
            self.stdout.write(f'   - {sessao.employee.name} (Estado: {sessao.get_state_display()})')
        
        # Verificar logs recentes
        logs_recentes = AccessLog.objects.filter(
            event_description='7',
            user_id__gt=0
        ).order_by('-device_log_id')[:5]
        
        self.stdout.write(f'\n📊 LOGS RECENTES (Portal 1/2): {logs_recentes.count()}')
        for log in logs_recentes:
            self.stdout.write(f'   ID {log.device_log_id}: {log.user_name} - Portal {log.portal_id} - {log.device_timestamp}')
        
        self.stdout.write(self.style.SUCCESS('✅ Verificação concluída!'))
