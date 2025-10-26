"""
Comando Django para carregar apenas o último log da catraca.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.logs.models import AccessLog
from apps.devices.device_client import DeviceClient
from apps.logs.services import log_monitor_service
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Carrega apenas o último log da catraca no banco'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔄 CARREGANDO ÚLTIMO LOG DA CATRACA")
        self.stdout.write("=" * 50)
        
        try:
            # 1. Parar monitoramento
            self.stdout.write("1️⃣ Parando monitoramento...")
            log_monitor_service.stop_monitoring()
            self.stdout.write("   ✅ Monitoramento parado")
            
            # 2. Conectar à catraca
            self.stdout.write("\n2️⃣ Conectando à catraca...")
            client = DeviceClient()
            self.stdout.write("   ✅ Conectado à catraca")
            
            # 3. Buscar o último log
            self.stdout.write("\n3️⃣ Buscando último log...")
            logs = client.get_recent_access_logs(limit=1)
            
            if not logs:
                self.stdout.write("   ❌ Nenhum log encontrado na catraca")
                return
            
            last_log = logs[0]
            log_id = last_log.get('id')
            user_id = last_log.get('user_id')
            
            self.stdout.write(f"   📊 Último log encontrado: ID {log_id}")
            self.stdout.write(f"   📊 User ID: {user_id}")
            self.stdout.write(f"   📊 Event: {last_log.get('event')}")
            self.stdout.write(f"   📊 Time: {last_log.get('time')}")
            
            # 4. Verificar se já existe no Django
            if AccessLog.objects.filter(device_log_id=log_id).exists():
                self.stdout.write(f"   ⚠️  Log {log_id} já existe no Django")
                log_monitor_service.last_processed_id = log_id
                self.stdout.write(f"   ✅ Monitor atualizado para ID {log_id}")
            else:
                # 5. Processar o último log
                self.stdout.write("\n4️⃣ Processando último log...")
                
                if user_id == 0:
                    self.stdout.write("   ⚠️  Log é de sistema (user_id=0), pulando")
                    log_monitor_service.last_processed_id = log_id
                    self.stdout.write(f"   ✅ Monitor atualizado para ID {log_id}")
                else:
                    # Processar log
                    event_type = self.map_event_type(last_log.get('event'))
                    user_name = self.get_user_name(user_id)
                    device_timestamp = self.parse_timestamp(last_log)
                    
                    with transaction.atomic():
                        AccessLog.objects.create(
                            device_log_id=log_id,
                            user_id=user_id,
                            user_name=user_name,
                            event_type=event_type,
                            event_description=self.get_event_description(last_log.get('event')),
                            device_id=1,
                            device_name="Catraca Principal",
                            portal_id=last_log.get('portal_id', 1),
                            device_timestamp=device_timestamp,
                            raw_data=last_log,
                            processing_status='processed'
                        )
                    
                    self.stdout.write(f"   ✅ Log {log_id} criado no Django:")
                    self.stdout.write(f"      Usuário: {user_name}")
                    self.stdout.write(f"      Data/Hora: {device_timestamp}")
                    self.stdout.write(f"      Evento: {self.get_event_description(last_log.get('event'))}")
                    
                    # Atualizar monitor
                    log_monitor_service.last_processed_id = log_id
                    self.stdout.write(f"   ✅ Monitor atualizado para ID {log_id}")
            
            # 6. Reiniciar monitoramento
            self.stdout.write(f"\n5️⃣ Reiniciando monitoramento...")
            if log_monitor_service.start_monitoring():
                self.stdout.write("   ✅ Monitoramento reiniciado")
            else:
                self.stdout.write("   ❌ Falha ao reiniciar monitoramento")
            
            # 7. Resumo final
            self.stdout.write(f"\n📊 RESUMO FINAL:")
            self.stdout.write(f"   Logs no banco: {AccessLog.objects.count()}")
            self.stdout.write(f"   Último ID: {log_monitor_service.last_processed_id}")
            self.stdout.write(f"   Monitor ativo: {log_monitor_service.is_running()}")
            self.stdout.write(f"   Próximo esperado: {log_monitor_service.last_processed_id + 1}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 ÚLTIMO LOG CARREGADO COM SUCESSO!"))
            self.stdout.write("🔄 Sistema pronto para detectar novos acessos")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
            logger.error(f"Erro: {e}")
    
    def map_event_type(self, event):
        """Mapeia tipo de evento."""
        event_map = {
            1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 1, 8: 3, 13: 1
        }
        return event_map.get(event, 1)
    
    def get_event_description(self, event):
        """Obtém descrição do evento."""
        descriptions = {
            1: "Entrada", 2: "Saída", 3: "Acesso Negado", 4: "Erro",
            5: "Timeout", 6: "Manutenção", 7: "Entrada", 8: "Bloqueado",
            13: "Entrada"
        }
        return descriptions.get(event, "Entrada")
    
    def get_user_name(self, user_id):
        """Obtém nome do usuário."""
        try:
            from apps.employees.models import Employee
            employee = Employee.objects.filter(device_user_id=user_id).first()
            return employee.name if employee else f"Usuário {user_id}"
        except:
            return f"Usuário {user_id}"
    
    def parse_timestamp(self, log_data):
        """Converte timestamp Unix para datetime."""
        try:
            timestamp = log_data.get('time')
            if timestamp:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                return datetime.now(timezone.utc)
        except:
            return datetime.now(timezone.utc)
