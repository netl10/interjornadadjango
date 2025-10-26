"""
Comando Django para verificar o log 10032.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Verifica o log 10032'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO LOG 10032")
        self.stdout.write("=" * 40)
        
        # Verificar no Django
        django_log = AccessLog.objects.filter(device_log_id=10032).first()
        if django_log:
            self.stdout.write("✅ Log 10032 encontrado no Django:")
            self.stdout.write(f"   Usuário: {django_log.user_name}")
            self.stdout.write(f"   Data/Hora: {django_log.device_timestamp}")
            self.stdout.write(f"   Evento: {django_log.event_description}")
        else:
            self.stdout.write("❌ Log 10032 NÃO encontrado no Django")
        
        # Verificar na catraca
        try:
            client = DeviceClient()
            logs = client.get_recent_access_logs(limit=10)
            
            catraca_log = None
            for log in logs:
                if log['id'] == 10032:
                    catraca_log = log
                    break
            
            if catraca_log:
                self.stdout.write("\n✅ Log 10032 encontrado na catraca:")
                self.stdout.write(f"   User ID: {catraca_log['user_id']}")
                self.stdout.write(f"   Event: {catraca_log['event']}")
                self.stdout.write(f"   Time: {catraca_log['time']}")
                self.stdout.write(f"   Portal ID: {catraca_log.get('portal_id', 'N/A')}")
            else:
                self.stdout.write("\n❌ Log 10032 NÃO encontrado na catraca")
                
        except Exception as e:
            self.stdout.write(f"\n❌ Erro ao verificar catraca: {e}")
        
        # Verificar último log no Django
        last_django = AccessLog.objects.order_by('-device_log_id').first()
        if last_django:
            self.stdout.write(f"\n📊 Último log no Django: ID {last_django.device_log_id}")
        
        # Verificar status do monitor
        from apps.logs.services import log_monitor_service
        self.stdout.write(f"📊 Monitor ativo: {log_monitor_service.is_running()}")
        self.stdout.write(f"📊 Último ID processado: {log_monitor_service.last_processed_id}")
