"""
Comando Django para começar do zero com o log 10036.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
from datetime import datetime, timezone, timedelta


class Command(BaseCommand):
    help = 'Começa do zero com o log 10036'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔄 COMEÇANDO DO ZERO COM LOG 10036")
        self.stdout.write("=" * 50)
        
        try:
            # Parar monitor
            log_monitor_service.stop_monitoring()
            self.stdout.write("✅ Monitor parado")
            
            # Criar log 10036 (último log real da catraca)
            timestamp_10036 = datetime.now(timezone.utc) - timedelta(minutes=1)
            
            AccessLog.objects.create(
                device_log_id=10036,
                user_id=1,  # Diego Lucio
                user_name="Diego Lucio",
                event_type=1,
                event_description="Entrada",
                device_id=1,
                device_name="Catraca Principal",
                portal_id=1,
                device_timestamp=timestamp_10036,
                raw_data={
                    'id': 10036,
                    'user_id': 1,
                    'event': 7,
                    'time': int(timestamp_10036.timestamp()),
                    'portal_id': 1
                },
                processing_status='processed'
            )
            
            self.stdout.write("✅ Log 10036 criado:")
            self.stdout.write(f"   Usuário: Diego Lucio")
            self.stdout.write(f"   Data/Hora: {timestamp_10036}")
            self.stdout.write(f"   Evento: Entrada")
            
            # Atualizar monitor
            log_monitor_service.last_processed_id = 10036
            self.stdout.write("✅ Monitor atualizado para ID 10036")
            
            # Reiniciar monitor
            if log_monitor_service.start_monitoring():
                self.stdout.write("✅ Monitor reiniciado")
            else:
                self.stdout.write("❌ Falha ao reiniciar monitor")
            
            # Resumo
            self.stdout.write(f"\n📊 RESUMO:")
            self.stdout.write(f"   Logs no banco: {AccessLog.objects.count()}")
            self.stdout.write(f"   Último ID: {log_monitor_service.last_processed_id}")
            self.stdout.write(f"   Monitor ativo: {log_monitor_service.is_running()}")
            self.stdout.write(f"   Próximo esperado: {log_monitor_service.last_processed_id + 1}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 SISTEMA INICIADO COM LOG 10036!"))
            self.stdout.write("🔄 Sistema pronto para detectar novos acessos")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
