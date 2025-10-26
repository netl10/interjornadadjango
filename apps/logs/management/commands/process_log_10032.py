"""
Comando Django para processar manualmente o log 10032.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Processa manualmente o log 10032'

    def handle(self, *args, **options):
        self.stdout.write("🔧 PROCESSANDO LOG 10032 MANUALMENTE")
        self.stdout.write("=" * 50)
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            logs = client.get_recent_access_logs(limit=10)
            
            # Encontrar log 10032
            log_10032 = None
            for log in logs:
                if log['id'] == 10032:
                    log_10032 = log
                    break
            
            if not log_10032:
                self.stdout.write("❌ Log 10032 não encontrado na catraca")
                return
            
            self.stdout.write("✅ Log 10032 encontrado na catraca:")
            self.stdout.write(f"   User ID: {log_10032['user_id']}")
            self.stdout.write(f"   Event: {log_10032['event']}")
            self.stdout.write(f"   Time: {log_10032['time']}")
            self.stdout.write(f"   Portal ID: {log_10032.get('portal_id', 1)}")
            
            # Verificar se já existe no Django
            if AccessLog.objects.filter(device_log_id=10032).exists():
                self.stdout.write("⚠️  Log 10032 já existe no Django")
                return
            
            # Processar log
            user_id = log_10032['user_id']
            if user_id == 0:
                self.stdout.write("⚠️  Log 10032 é de sistema (user_id=0), pulando")
                return
            
            # Mapear evento
            event_map = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 1, 8: 3}
            event_type = event_map.get(log_10032['event'], 1)
            
            # Obter nome do usuário
            try:
                from apps.employees.models import Employee
                employee = Employee.objects.filter(device_user_id=user_id).first()
                user_name = employee.name if employee else f"Usuário {user_id}"
            except:
                user_name = f"Usuário {user_id}"
            
            # Converter timestamp
            device_timestamp = datetime.fromtimestamp(log_10032['time'], tz=timezone.utc)
            
            # Criar log no Django
            AccessLog.objects.create(
                device_log_id=10032,
                user_id=user_id,
                user_name=user_name,
                event_type=event_type,
                event_description=self.get_event_description(log_10032['event']),
                device_id=1,
                device_name="Catraca Principal",
                portal_id=log_10032.get('portal_id', 1),
                device_timestamp=device_timestamp,
                raw_data=log_10032,
                processing_status='processed'
            )
            
            self.stdout.write("✅ Log 10032 criado no Django:")
            self.stdout.write(f"   Usuário: {user_name}")
            self.stdout.write(f"   Data/Hora: {device_timestamp}")
            self.stdout.write(f"   Evento: {self.get_event_description(log_10032['event'])}")
            
            # Atualizar monitor
            log_monitor_service.last_processed_id = 10032
            self.stdout.write("✅ Monitor atualizado para ID 10032")
            
            # Verificar se há log 10033
            log_10033 = None
            for log in logs:
                if log['id'] == 10033:
                    log_10033 = log
                    break
            
            if log_10033:
                self.stdout.write(f"\n📊 Log 10033 também encontrado:")
                self.stdout.write(f"   User ID: {log_10033['user_id']}")
                self.stdout.write(f"   Event: {log_10033['event']}")
                self.stdout.write(f"   Time: {log_10033['time']}")
                self.stdout.write("💡 Execute novamente para processar o 10033")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
    
    def get_event_description(self, event):
        """Obtém descrição do evento."""
        descriptions = {
            1: "Entrada", 2: "Saída", 3: "Acesso Negado", 4: "Erro",
            5: "Timeout", 6: "Manutenção", 7: "Entrada", 8: "Bloqueado",
            13: "Entrada"
        }
        return descriptions.get(event, "Entrada")
