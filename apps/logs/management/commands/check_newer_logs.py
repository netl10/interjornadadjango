"""
Comando Django para verificar se há logs mais recentes na catraca.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Verifica se há logs mais recentes na catraca'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO LOGS MAIS RECENTES NA CATRACA")
        self.stdout.write("=" * 60)
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            self.stdout.write("✅ Conectado à catraca")
            
            # Buscar logs recentes sem filtro de ID
            logs = client.get_recent_access_logs(limit=20)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado")
                return
            
            self.stdout.write(f"📊 Total de logs encontrados: {len(logs)}")
            
            # Encontrar o maior ID
            max_id = max(log['id'] for log in logs)
            self.stdout.write(f"📈 Maior ID encontrado: {max_id}")
            
            # Mostrar logs com ID >= 10036
            recent_logs = [log for log in logs if log['id'] >= 10036]
            
            if recent_logs:
                self.stdout.write(f"\n📋 Logs com ID >= 10036:")
                for log in recent_logs:
                    timestamp = log.get('time', 0)
                    if timestamp:
                        from datetime import datetime, timezone
                        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        self.stdout.write(f"   ID {log['id']}: User {log['user_id']} - {dt} - Event {log['event']}")
                    else:
                        self.stdout.write(f"   ID {log['id']}: User {log['user_id']} - Event {log['event']}")
            else:
                self.stdout.write("\n❌ Nenhum log com ID >= 10036 encontrado")
            
            # Mostrar todos os IDs encontrados
            ids = [log['id'] for log in logs]
            ids.sort(reverse=True)
            
            self.stdout.write(f"\n📋 Todos os IDs encontrados (primeiros 10):")
            for i, log_id in enumerate(ids[:10]):
                self.stdout.write(f"   {i+1:2d}. ID {log_id}")
                
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
