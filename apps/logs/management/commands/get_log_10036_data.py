"""
Comando Django para buscar os dados exatos do log 10036 da catraca.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Busca os dados exatos do log 10036 da catraca'

    def handle(self, *args, **options):
        self.stdout.write("🔍 BUSCANDO DADOS EXATOS DO LOG 10036")
        self.stdout.write("=" * 50)
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            self.stdout.write("✅ Conectado à catraca")
            
            # Buscar logs recentes
            logs = client.get_recent_access_logs(limit=10)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado")
                return
            
            # Encontrar log 10036
            log_10036 = None
            for log in logs:
                if log['id'] == 10036:
                    log_10036 = log
                    break
            
            if log_10036:
                self.stdout.write("✅ Log 10036 encontrado na catraca:")
                self.stdout.write(f"   ID: {log_10036['id']}")
                self.stdout.write(f"   User ID: {log_10036['user_id']}")
                self.stdout.write(f"   Event: {log_10036['event']}")
                self.stdout.write(f"   Time: {log_10036['time']}")
                self.stdout.write(f"   Portal ID: {log_10036.get('portal_id', 'N/A')}")
                
                # Converter timestamp
                timestamp = datetime.fromtimestamp(log_10036['time'], tz=timezone.utc)
                self.stdout.write(f"   Data/Hora convertida: {timestamp}")
                
                # Mostrar dados brutos
                self.stdout.write(f"\n📊 Dados brutos completos:")
                for key, value in log_10036.items():
                    self.stdout.write(f"   {key}: {value}")
                    
            else:
                self.stdout.write("❌ Log 10036 não encontrado na catraca")
                
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
