"""
Comando Django para verificar o log 10037 na catraca e no banco.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.devices.device_client import DeviceClient
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Verifica o log 10037 na catraca e no banco'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO LOG 10037")
        self.stdout.write("=" * 40)
        
        try:
            # Verificar no banco Django
            log_db = AccessLog.objects.filter(device_log_id=10037).first()
            if log_db:
                self.stdout.write("✅ Log 10037 ENCONTRADO no banco Django:")
                self.stdout.write(f"   Usuário: {log_db.user_name}")
                self.stdout.write(f"   Data/Hora: {log_db.device_timestamp}")
                self.stdout.write(f"   Evento: {log_db.event_description}")
                self.stdout.write(f"   Portal: {log_db.portal_id}")
            else:
                self.stdout.write("❌ Log 10037 NÃO ENCONTRADO no banco Django")
            
            # Verificar na catraca
            self.stdout.write("\n🔍 Verificando na catraca...")
            client = DeviceClient()
            
            # Buscar logs próximos ao 10037
            logs = client.get_recent_access_logs(limit=10, min_id=10035)
            
            log_10037_catraca = None
            for log in logs:
                if log['id'] == 10037:
                    log_10037_catraca = log
                    break
            
            if log_10037_catraca:
                self.stdout.write("✅ Log 10037 ENCONTRADO na catraca:")
                self.stdout.write(f"   ID: {log_10037_catraca['id']}")
                self.stdout.write(f"   User ID: {log_10037_catraca.get('user_id', 'N/A')}")
                self.stdout.write(f"   Event: {log_10037_catraca.get('event', 'N/A')}")
                self.stdout.write(f"   Time: {log_10037_catraca.get('time', 'N/A')}")
                self.stdout.write(f"   Portal: {log_10037_catraca.get('portal_id', 'N/A')}")
                
                # Converter timestamp
                if 'time' in log_10037_catraca:
                    timestamp = datetime.fromtimestamp(log_10037_catraca['time'], tz=timezone.utc)
                    self.stdout.write(f"   Data/Hora: {timestamp}")
            else:
                self.stdout.write("❌ Log 10037 NÃO ENCONTRADO na catraca")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
