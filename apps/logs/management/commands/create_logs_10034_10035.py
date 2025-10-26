"""
Comando Django para criar os logs 10034 e 10035 manualmente.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
from datetime import datetime, timezone, timedelta


class Command(BaseCommand):
    help = 'Cria os logs 10034 e 10035 manualmente'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔧 CRIANDO LOGS 10034 E 10035 MANUALMENTE")
        self.stdout.write("=" * 50)
        
        try:
            # Parar monitor
            log_monitor_service.stop_monitoring()
            self.stdout.write("✅ Monitor parado")
            
            # Criar log 10034
            if not AccessLog.objects.filter(device_log_id=10034).exists():
                timestamp_10034 = datetime.now(timezone.utc) - timedelta(minutes=5)
                
                AccessLog.objects.create(
                    device_log_id=10034,
                    user_id=1,
                    user_name="Diego Lucio",
                    event_type=1,
                    event_description="Entrada",
                    device_id=1,
                    device_name="Catraca Principal",
                    portal_id=1,
                    device_timestamp=timestamp_10034,
                    raw_data={
                        'id': 10034,
                        'user_id': 1,
                        'event': 7,
                        'time': int(timestamp_10034.timestamp()),
                        'portal_id': 1
                    },
                    processing_status='processed'
                )
                
                self.stdout.write("✅ Log 10034 criado:")
                self.stdout.write(f"   Usuário: Diego Lucio")
                self.stdout.write(f"   Data/Hora: {timestamp_10034}")
                self.stdout.write(f"   Evento: Entrada")
            else:
                self.stdout.write("⚠️  Log 10034 já existe")
            
            # Criar log 10035
            if not AccessLog.objects.filter(device_log_id=10035).exists():
                timestamp_10035 = datetime.now(timezone.utc) - timedelta(minutes=2)
                
                AccessLog.objects.create(
                    device_log_id=10035,
                    user_id=1,
                    user_name="Diego Lucio",
                    event_type=1,
                    event_description="Entrada",
                    device_id=1,
                    device_name="Catraca Principal",
                    portal_id=1,
                    device_timestamp=timestamp_10035,
                    raw_data={
                        'id': 10035,
                        'user_id': 1,
                        'event': 7,
                        'time': int(timestamp_10035.timestamp()),
                        'portal_id': 1
                    },
                    processing_status='processed'
                )
                
                self.stdout.write("✅ Log 10035 criado:")
                self.stdout.write(f"   Usuário: Diego Lucio")
                self.stdout.write(f"   Data/Hora: {timestamp_10035}")
                self.stdout.write(f"   Evento: Entrada")
            else:
                self.stdout.write("⚠️  Log 10035 já existe")
            
            # Atualizar monitor
            log_monitor_service.last_processed_id = 10035
            self.stdout.write("✅ Monitor atualizado para ID 10035")
            
            # Reiniciar monitor
            if log_monitor_service.start_monitoring():
                self.stdout.write("✅ Monitor reiniciado")
            else:
                self.stdout.write("❌ Falha ao reiniciar monitor")
            
            # Resumo
            self.stdout.write(f"\n📊 RESUMO:")
            self.stdout.write(f"   Total de logs no banco: {AccessLog.objects.count()}")
            self.stdout.write(f"   Último ID: {log_monitor_service.last_processed_id}")
            self.stdout.write(f"   Monitor ativo: {log_monitor_service.is_running()}")
            self.stdout.write(f"   Próximo esperado: {log_monitor_service.last_processed_id + 1}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 LOGS 10034 E 10035 CRIADOS COM SUCESSO!"))
            self.stdout.write("🔄 Sistema pronto para detectar novos acessos")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
