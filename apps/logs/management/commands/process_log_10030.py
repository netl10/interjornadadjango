"""
Comando Django para processar o log ID 10030 manualmente.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Processa o log ID 10030 manualmente'

    def handle(self, *args, **options):
        self.stdout.write("🔧 PROCESSANDO LOG ID 10030 MANUALMENTE")
        self.stdout.write("=" * 50)
        
        # Verificar se já existe no banco
        existing_log = AccessLog.objects.filter(device_log_id=10030).first()
        if existing_log:
            self.stdout.write("ℹ️ Log ID 10030 já existe no banco:")
            self.stdout.write(f"   Usuário: {existing_log.user_name}")
            self.stdout.write(f"   Evento: {existing_log.event_description}")
            self.stdout.write(f"   Timestamp: {existing_log.device_timestamp}")
            return
        
        # Buscar log na catraca
        try:
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write("❌ Não foi possível conectar à catraca")
                return
            
            self.stdout.write("✅ Conectado à catraca")
            
            # Buscar log específico
            logs = client.get_access_logs_from_id(10030)
            if not logs:
                self.stdout.write("❌ Log ID 10030 não encontrado na catraca")
                return
            
            log_data = logs[0]
            self.stdout.write("📋 Log encontrado na catraca:")
            self.stdout.write(f"   ID: {log_data['id']}")
            self.stdout.write(f"   User ID: {log_data.get('user_id', 'N/A')}")
            self.stdout.write(f"   Event: {log_data.get('event', 'N/A')}")
            self.stdout.write(f"   Time: {log_data.get('time', 'N/A')}")
            
            # Processar log
            from apps.logs.services import log_monitor_service
            success = log_monitor_service.process_single_log(log_data)
            
            if success:
                self.stdout.write("✅ Log processado com sucesso!")
                
                # Verificar se foi salvo
                saved_log = AccessLog.objects.filter(device_log_id=10030).first()
                if saved_log:
                    self.stdout.write("📊 Log salvo no banco:")
                    self.stdout.write(f"   Usuário: {saved_log.user_name}")
                    self.stdout.write(f"   Evento: {saved_log.event_description}")
                    self.stdout.write(f"   Timestamp: {saved_log.device_timestamp}")
                else:
                    self.stdout.write("❌ Log não foi salvo no banco")
            else:
                self.stdout.write("❌ Falha ao processar log")
                
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
