"""
Comando Django para corrigir a sequência do monitor.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from apps.logs.services import log_monitor_service
from apps.logs.models import AccessLog


class Command(BaseCommand):
    help = 'Corrige a sequência do monitor para o último log real da catraca'

    def handle(self, *args, **options):
        self.stdout.write("🔧 CORRIGINDO SEQUÊNCIA DO MONITOR")
        self.stdout.write("=" * 50)
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            logs = client.get_recent_access_logs(limit=20)
            
            if not logs:
                self.stdout.write(self.style.ERROR("❌ Nenhum log encontrado na catraca"))
                return
            
            # Encontrar o último log real da catraca
            last_catraca_log = max(logs, key=lambda x: x['id'])
            last_catraca_id = last_catraca_log['id']
            
            self.stdout.write(f"📊 Último log da catraca: ID {last_catraca_id}")
            self.stdout.write(f"   User ID: {last_catraca_log['user_id']}")
            self.stdout.write(f"   Event: {last_catraca_log['event']}")
            self.stdout.write(f"   Time: {last_catraca_log['time']}")
            
            # Verificar se esse log existe no Django
            django_log = AccessLog.objects.filter(device_log_id=last_catraca_id).first()
            if django_log:
                self.stdout.write(f"✅ Log {last_catraca_id} já existe no Django")
            else:
                self.stdout.write(f"❌ Log {last_catraca_id} NÃO existe no Django")
            
            # Verificar último log processado no Django
            last_django_log = AccessLog.objects.order_by('-device_log_id').first()
            if last_django_log:
                self.stdout.write(f"📊 Último log no Django: ID {last_django_log.device_log_id}")
            else:
                self.stdout.write("📊 Nenhum log no Django")
            
            # Verificar último ID processado pelo monitor
            current_monitor_id = log_monitor_service.last_processed_id
            self.stdout.write(f"📊 Último ID do monitor: {current_monitor_id}")
            
            # Determinar o próximo ID correto
            if last_django_log and last_django_log.device_log_id >= last_catraca_id:
                # Django está à frente da catraca
                next_id = last_django_log.device_log_id + 1
                self.stdout.write(f"✅ Django está à frente da catraca")
                self.stdout.write(f"   Próximo ID esperado: {next_id}")
            else:
                # Catraca está à frente do Django
                next_id = last_catraca_id + 1
                self.stdout.write(f"⚠️  Catraca está à frente do Django")
                self.stdout.write(f"   Próximo ID esperado: {next_id}")
            
            # Atualizar o monitor
            old_id = log_monitor_service.last_processed_id
            log_monitor_service.last_processed_id = next_id - 1
            
            self.stdout.write(f"\n🔧 CORREÇÃO APLICADA:")
            self.stdout.write(f"   ID anterior: {old_id}")
            self.stdout.write(f"   ID corrigido: {log_monitor_service.last_processed_id}")
            self.stdout.write(f"   Próximo esperado: {next_id}")
            
            self.stdout.write(self.style.SUCCESS("✅ Sequência do monitor corrigida!"))
            self.stdout.write("🔄 O monitor agora aguardará o próximo log real da catraca")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro ao corrigir sequência: {e}"))
