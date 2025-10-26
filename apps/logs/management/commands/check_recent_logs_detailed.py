"""
Comando Django para verificar logs recentes detalhadamente.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Verifica logs recentes detalhadamente'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO LOGS RECENTES DETALHADAMENTE")
        self.stdout.write("=" * 60)
        
        try:
            client = DeviceClient()
            
            # Buscar logs recentes
            logs = client.get_recent_access_logs(limit=50)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado")
                return
            
            self.stdout.write(f"📊 Total de logs encontrados: {len(logs)}")
            
            # Encontrar logs com ID >= 10030
            recent_logs = [log for log in logs if log['id'] >= 10030]
            
            self.stdout.write(f"📊 Logs com ID >= 10030: {len(recent_logs)}")
            
            if recent_logs:
                self.stdout.write("\n📋 Logs recentes (ID >= 10030):")
                for log in recent_logs:
                    timestamp = datetime.fromtimestamp(log['time'], tz=timezone.utc)
                    self.stdout.write(f"   ID {log['id']}: User {log['user_id']} - {timestamp} - Event {log['event']}")
            else:
                self.stdout.write("\n❌ Nenhum log com ID >= 10030 encontrado")
            
            # Mostrar todos os IDs encontrados
            ids = [log['id'] for log in logs]
            ids.sort(reverse=True)
            
            self.stdout.write(f"\n📋 Todos os IDs encontrados (primeiros 20):")
            for i, log_id in enumerate(ids[:20]):
                self.stdout.write(f"   {i+1:2d}. ID {log_id}")
            
            # Verificar se há lacunas
            if len(ids) > 1:
                self.stdout.write(f"\n🔍 Verificando lacunas...")
                for i in range(len(ids)-1):
                    current_id = ids[i]
                    next_id = ids[i+1]
                    if current_id - next_id > 1:
                        self.stdout.write(f"   ⚠️  Lacuna entre ID {current_id} e {next_id}")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
