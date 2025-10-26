"""
Comando Django para processar logs faltantes na sequência.
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
    help = 'Processa logs faltantes na sequência'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔧 PROCESSANDO LOGS FALTANTES NA SEQUÊNCIA")
        self.stdout.write("=" * 60)
        
        try:
            # Parar monitor
            log_monitor_service.stop_monitoring()
            self.stdout.write("✅ Monitor parado")
            
            # Conectar à catraca
            client = DeviceClient()
            self.stdout.write("✅ Conectado à catraca")
            
            # Buscar logs recentes
            logs = client.get_recent_access_logs(limit=10)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado na catraca")
                return
            
            # Encontrar logs com ID >= 10034
            missing_logs = []
            for log in logs:
                log_id = log.get('id')
                if log_id >= 10034:
                    # Verificar se já existe no Django
                    if not AccessLog.objects.filter(device_log_id=log_id).exists():
                        missing_logs.append(log)
            
            if not missing_logs:
                self.stdout.write("✅ Nenhum log faltante encontrado")
                return
            
            self.stdout.write(f"📊 Logs faltantes encontrados: {len(missing_logs)}")
            
            # Processar logs faltantes
            processed_count = 0
            last_processed_id = log_monitor_service.last_processed_id
            
            with transaction.atomic():
                for log_data in missing_logs:
                    log_id = log_data.get('id')
                    user_id = log_data.get('user_id')
                    
                    self.stdout.write(f"\n🔧 Processando log ID {log_id}...")
                    
                    # Pular logs de sistema (user_id = 0)
                    if user_id == 0:
                        self.stdout.write(f"   ⚠️  Log {log_id} é de sistema (user_id=0), pulando")
                        last_processed_id = max(last_processed_id, log_id)
                        continue
                    
                    # Processar log
                    event_type = self.map_event_type(log_data.get('event'))
                    user_name = self.get_user_name(user_id)
                    device_timestamp = self.parse_timestamp(log_data)
                    
                    AccessLog.objects.create(
                        device_log_id=log_id,
                        user_id=user_id,
                        user_name=user_name,
                        event_type=event_type,
                        event_description=self.get_event_description(log_data.get('event')),
                        device_id=1,
                        device_name="Catraca Principal",
                        portal_id=log_data.get('portal_id', 1),
                        device_timestamp=device_timestamp,
                        raw_data=log_data,
                        processing_status='processed'
                    )
                    
                    self.stdout.write(f"   ✅ Log {log_id} processado:")
                    self.stdout.write(f"      Usuário: {user_name}")
                    self.stdout.write(f"      Data/Hora: {device_timestamp}")
                    self.stdout.write(f"      Evento: {self.get_event_description(log_data.get('event'))}")
                    
                    processed_count += 1
                    last_processed_id = max(last_processed_id, log_id)
            
            # Atualizar monitor
            log_monitor_service.last_processed_id = last_processed_id
            self.stdout.write(f"\n✅ Monitor atualizado para ID {last_processed_id}")
            
            # Reiniciar monitor
            if log_monitor_service.start_monitoring():
                self.stdout.write("✅ Monitor reiniciado")
            else:
                self.stdout.write("❌ Falha ao reiniciar monitor")
            
            # Resumo
            self.stdout.write(f"\n📊 RESUMO:")
            self.stdout.write(f"   Logs processados: {processed_count}")
            self.stdout.write(f"   Último ID: {last_processed_id}")
            self.stdout.write(f"   Total de logs no banco: {AccessLog.objects.count()}")
            self.stdout.write(f"   Monitor ativo: {log_monitor_service.is_running()}")
            self.stdout.write(f"   Próximo esperado: {last_processed_id + 1}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 LOGS FALTANTES PROCESSADOS COM SUCESSO!"))
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
