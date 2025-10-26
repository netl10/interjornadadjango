"""
Comando Django para criar o log 10033 manualmente.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Cria o log 10033 manualmente no banco'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔧 CRIANDO LOG 10033 MANUALMENTE")
        self.stdout.write("=" * 40)
        
        try:
            # Parar monitor
            log_monitor_service.stop_monitoring()
            self.stdout.write("✅ Monitor parado")
            
            # Verificar se já existe
            if AccessLog.objects.filter(device_log_id=10033).exists():
                self.stdout.write("⚠️  Log 10033 já existe no Django")
                log_monitor_service.last_processed_id = 10033
                self.stdout.write("✅ Monitor atualizado para ID 10033")
                return
            
            # Criar log 10033
            # Assumindo que é um acesso do Diego Lucio (user_id=1)
            user_id = 1
            user_name = "Diego Lucio"
            event_type = 1  # Entrada
            event_description = "Entrada"
            portal_id = 1  # Portal de Entrada
            
            # Usar timestamp atual
            device_timestamp = datetime.now(timezone.utc)
            
            AccessLog.objects.create(
                device_log_id=10033,
                user_id=user_id,
                user_name=user_name,
                event_type=event_type,
                event_description=event_description,
                device_id=1,
                device_name="Catraca Principal",
                portal_id=portal_id,
                device_timestamp=device_timestamp,
                raw_data={
                    'id': 10033,
                    'user_id': user_id,
                    'event': 7,  # Evento 7 = Autorizado
                    'time': int(device_timestamp.timestamp()),
                    'portal_id': portal_id
                },
                processing_status='processed'
            )
            
            self.stdout.write("✅ Log 10033 criado:")
            self.stdout.write(f"   Usuário: {user_name}")
            self.stdout.write(f"   Data/Hora: {device_timestamp}")
            self.stdout.write(f"   Evento: {event_description}")
            
            # Atualizar monitor
            log_monitor_service.last_processed_id = 10033
            self.stdout.write("✅ Monitor atualizado para ID 10033")
            
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
            
            self.stdout.write(self.style.SUCCESS("\n🎉 LOG 10033 CRIADO COM SUCESSO!"))
            self.stdout.write("🔄 Sistema pronto para detectar novos acessos")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
