#!/usr/bin/env python
"""
Comando para reativar o monitoramento automático.
"""
import time
from django.core.management.base import BaseCommand
from apps.logs.services import log_monitor_service


class Command(BaseCommand):
    help = 'Reativa o monitoramento automático'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Reativando monitoramento...')
        
        # Parar monitoramento se estiver rodando
        if log_monitor_service.get_status().get('running', False):
            self.stdout.write('   Parando monitoramento atual...')
            log_monitor_service.stop_monitoring()
        time.sleep(0.5)
        
        # Iniciar monitoramento
        self.stdout.write('   Iniciando novo monitoramento...')
        log_monitor_service.start_monitoring()
        
        # Verificar status
        status = log_monitor_service.get_status()
        self.stdout.write(f'📊 Status: Rodando = {status.get("running", False)}')
        self.stdout.write(f'📊 Último ID: {status.get("last_processed_id", 0)}')
        
        if status.get('running', False):
            self.stdout.write(self.style.SUCCESS('✅ Monitoramento reativado com sucesso!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Falha ao reativar monitoramento!'))
