"""
Comando Django para resetar todos os logs e carregar os 1000 últimos corretos.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.logs.models import AccessLog, SystemLog
from apps.devices.device_client import DeviceClient
from apps.logs.services import log_monitor_service
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reseta todos os logs e carrega os 1000 últimos corretos da catraca'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação de reset')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  ATENÇÃO: Esta operação irá APAGAR TODOS os logs!"))
            self.stdout.write("   Use --confirm para executar")
            return
        
        self.stdout.write("🔄 RESETANDO LOGS E CARREGANDO 1000 ÚLTIMOS")
        self.stdout.write("=" * 60)
        
        try:
            # 1. Parar o monitoramento
            self.stdout.write("1️⃣ Parando monitoramento...")
            log_monitor_service.stop_monitoring()
            self.stdout.write("   ✅ Monitoramento parado")
            
            # 2. Apagar todos os logs
            self.stdout.write("\n2️⃣ Apagando todos os logs...")
            with transaction.atomic():
                count = AccessLog.objects.count()
                AccessLog.objects.all().delete()
                self.stdout.write(f"   ✅ {count} logs apagados")
            
            # 3. Conectar à catraca
            self.stdout.write("\n3️⃣ Conectando à catraca...")
            client = DeviceClient()
            self.stdout.write("   ✅ Conectado à catraca")
            
            # 4. Buscar os 1000 últimos logs
            self.stdout.write("\n4️⃣ Buscando 1000 últimos logs...")
            logs = client.get_recent_access_logs(limit=1000)
            self.stdout.write(f"   ✅ {len(logs)} logs encontrados")
            
            # 5. Processar e salvar logs
            self.stdout.write("\n5️⃣ Processando e salvando logs...")
            processed_count = 0
            skipped_count = 0
            last_log_id = 0
            
            with transaction.atomic():
                for log_data in logs:
                    log_id = log_data.get('id')
                    user_id = log_data.get('user_id')
                    
                    # Pular logs de sistema (user_id = 0)
                    if user_id == 0:
                        skipped_count += 1
                        continue
                    
                    # Verificar se já existe
                    if AccessLog.objects.filter(device_log_id=log_id).exists():
                        skipped_count += 1
                        continue
                    
                    # Processar log
                    try:
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
                        
                        processed_count += 1
                        last_log_id = max(last_log_id, log_id)
                        
                        if processed_count % 100 == 0:
                            self.stdout.write(f"   📊 Processados: {processed_count}")
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar log {log_id}: {e}")
                        skipped_count += 1
            
            self.stdout.write(f"   ✅ {processed_count} logs processados")
            self.stdout.write(f"   ⏭️  {skipped_count} logs pulados")
            
            # 6. Atualizar monitor
            self.stdout.write(f"\n6️⃣ Atualizando monitor...")
            log_monitor_service.last_processed_id = last_log_id
            self.stdout.write(f"   ✅ Último ID processado: {last_log_id}")
            
            # 7. Reiniciar monitoramento
            self.stdout.write(f"\n7️⃣ Reiniciando monitoramento...")
            if log_monitor_service.start_monitoring():
                self.stdout.write("   ✅ Monitoramento reiniciado")
            else:
                self.stdout.write("   ❌ Falha ao reiniciar monitoramento")
            
            # 8. Resumo final
            self.stdout.write(f"\n📊 RESUMO FINAL:")
            self.stdout.write(f"   Logs processados: {processed_count}")
            self.stdout.write(f"   Logs pulados: {skipped_count}")
            self.stdout.write(f"   Último ID: {last_log_id}")
            self.stdout.write(f"   Monitor ativo: {log_monitor_service.is_running()}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 RESET COMPLETO COM SUCESSO!"))
            self.stdout.write("🔄 Sistema pronto para detectar novos acessos")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro durante reset: {e}"))
            logger.error(f"Erro durante reset: {e}")
    
    def map_event_type(self, event):
        """Mapeia tipo de evento."""
        event_map = {
            1: 1,  # Entrada
            2: 2,  # Saída
            3: 3,  # Acesso Negado
            4: 4,  # Erro
            5: 5,  # Timeout
            6: 6,  # Manutenção
            7: 1,  # Autorizado (entrada)
            8: 3,  # Bloqueado
        }
        return event_map.get(event, 1)
    
    def get_event_description(self, event):
        """Obtém descrição do evento."""
        descriptions = {
            1: "Entrada",
            2: "Saída", 
            3: "Acesso Negado",
            4: "Erro",
            5: "Timeout",
            6: "Manutenção",
            7: "Entrada",
            8: "Bloqueado",
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
