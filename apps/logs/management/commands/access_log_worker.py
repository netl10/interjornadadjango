"""
Comando para gerenciar o AccessLogWorker.
"""
from django.core.management.base import BaseCommand
from apps.logs.workers import access_log_worker


class Command(BaseCommand):
    help = 'Gerencia o AccessLogWorker para sincronização de logs da catraca'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['start', 'stop', 'status', 'restart'],
            help='Ação a ser executada'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'start':
            self.start_worker()
        elif action == 'stop':
            self.stop_worker()
        elif action == 'status':
            self.show_status()
        elif action == 'restart':
            self.restart_worker()

    def start_worker(self):
        """Inicia o worker."""
        self.stdout.write('🚀 Iniciando AccessLogWorker...')
        
        if access_log_worker.start_worker():
            self.stdout.write(self.style.SUCCESS('✅ AccessLogWorker iniciado com sucesso!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Falha ao iniciar AccessLogWorker!'))

    def stop_worker(self):
        """Para o worker."""
        self.stdout.write('🛑 Parando AccessLogWorker...')
        access_log_worker.stop_worker()
        self.stdout.write(self.style.SUCCESS('✅ AccessLogWorker parado!'))

    def show_status(self):
        """Mostra status do worker."""
        self.stdout.write('📊 STATUS DO ACCESSLOGWORKER:')
        
        status = access_log_worker.get_status()
        self.stdout.write(f'   Rodando: {status["running"]}')
        self.stdout.write(f'   Último ID sincronizado: {status["last_synced_id"]}')
        self.stdout.write(f'   Erros consecutivos: {status["consecutive_errors"]}')
        self.stdout.write(f'   Intervalo de sync: {status["sync_interval"]}s')
        self.stdout.write(f'   Tamanho do lote: {status["batch_size"]}')
        self.stdout.write(f'   Conectado à catraca: {status["connected"]}')

    def restart_worker(self):
        """Reinicia o worker."""
        self.stdout.write('🔄 Reiniciando AccessLogWorker...')
        
        # Parar se estiver rodando
        if access_log_worker.running:
            access_log_worker.stop_worker()
            self.stdout.write('   Worker parado')
        
        # Iniciar novamente
        if access_log_worker.start_worker():
            self.stdout.write(self.style.SUCCESS('✅ AccessLogWorker reiniciado com sucesso!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Falha ao reiniciar AccessLogWorker!'))
