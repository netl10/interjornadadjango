"""
Comando Django para verificar logs específicos no banco.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog


class Command(BaseCommand):
    help = 'Verifica logs específicos no banco Django'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO LOGS ESPECÍFICOS NO BANCO DJANGO")
        self.stdout.write("=" * 60)
        
        target_ids = [10029, 10028, 10027, 10025, 10021]
        
        self.stdout.write("📋 Verificando logs no banco Django:")
        self.stdout.write("")
        
        for log_id in target_ids:
            log = AccessLog.objects.filter(device_log_id=log_id).first()
            if log:
                self.stdout.write(f"✅ ID {log_id}: {log.user_name}")
                self.stdout.write(f"   Evento: {log.event_description}")
                self.stdout.write(f"   Portal: {log.device_name}")
                self.stdout.write(f"   Data/Hora: {log.device_timestamp}")
                self.stdout.write("")
            else:
                self.stdout.write(f"❌ ID {log_id}: NÃO ENCONTRADO")
                self.stdout.write("")
        
        # Verificar últimos logs no banco
        self.stdout.write("📊 Últimos 5 logs no banco Django:")
        self.stdout.write("")
        
        last_logs = AccessLog.objects.order_by('-device_log_id')[:5]
        for i, log in enumerate(last_logs, 1):
            self.stdout.write(f"{i}. ID {log.device_log_id}: {log.user_name}")
            self.stdout.write(f"   Evento: {log.event_description}")
            self.stdout.write(f"   Data/Hora: {log.device_timestamp}")
            self.stdout.write("")
