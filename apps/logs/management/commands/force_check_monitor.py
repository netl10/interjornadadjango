"""
Comando Django para forçar verificação do monitor.
"""
from django.core.management.base import BaseCommand
from apps.logs.services import log_monitor_service


class Command(BaseCommand):
    help = 'Força verificação do monitor de logs'

    def handle(self, *args, **options):
        self.stdout.write("🔍 FORÇANDO VERIFICAÇÃO DO MONITOR")
        self.stdout.write("=" * 40)
        
        try:
            # Status do monitor
            self.stdout.write(f"📊 Monitor ativo: {log_monitor_service.is_running()}")
            self.stdout.write(f"📊 Último ID processado: {log_monitor_service.last_processed_id}")
            self.stdout.write(f"📊 Próximo esperado: {log_monitor_service.last_processed_id + 1}")
            
            # Forçar verificação
            self.stdout.write("\n🔍 Forçando verificação...")
            logs = log_monitor_service.get_logs_in_sequence()
            
            self.stdout.write(f"📊 Logs encontrados: {len(logs)}")
            
            if logs:
                for log in logs:
                    log_id = log.get('id', 'N/A')
                    user_id = log.get('user_id', 'N/A')
                    event = log.get('event', 'N/A')
                    self.stdout.write(f"  - ID {log_id}: user_id {user_id}, event {event}")
            else:
                self.stdout.write("  - Nenhum log novo encontrado")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
