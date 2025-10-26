"""
Comando Django para diagnosticar problemas de monitoramento.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Diagnostica problemas de monitoramento de logs'

    def handle(self, *args, **options):
        self.stdout.write("🔍 DIAGNÓSTICO DO MONITORAMENTO")
        self.stdout.write("=" * 60)
        
        # 1. Verificar status do monitoramento
        self.stdout.write("\n1️⃣ STATUS DO MONITORAMENTO:")
        status = log_monitor_service.get_status()
        self.stdout.write(f"   Rodando: {status['running']}")
        self.stdout.write(f"   Último ID processado: {status['last_processed_id']}")
        self.stdout.write(f"   Intervalo: {status['monitor_interval']}s")
        self.stdout.write(f"   Tamanho do lote: {status['batch_size']}")
        self.stdout.write(f"   Erros consecutivos: {status['consecutive_errors']}")
        
        # 2. Verificar logs no banco
        self.stdout.write("\n2️⃣ LOGS NO BANCO:")
        total_logs = AccessLog.objects.count()
        if total_logs > 0:
            first_log = AccessLog.objects.order_by('device_log_id').first()
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            self.stdout.write(f"   Total de logs: {total_logs}")
            self.stdout.write(f"   Primeiro log: ID {first_log.device_log_id}")
            self.stdout.write(f"   Último log: ID {last_log.device_log_id}")
            self.stdout.write(f"   Último usuário: {last_log.user_name}")
            self.stdout.write(f"   Último timestamp: {last_log.device_timestamp}")
        else:
            self.stdout.write("   ❌ Nenhum log encontrado no banco")
        
        # 3. Testar conexão com catraca
        self.stdout.write("\n3️⃣ CONEXÃO COM CATRACA:")
        try:
            client = DeviceClient()
            if client.is_connected():
                self.stdout.write("   ✅ Conectado à catraca")
                
                # Buscar logs da catraca
                logs = client.get_recent_access_logs(limit=20)
                if logs:
                    self.stdout.write(f"   📊 Logs encontrados na catraca: {len(logs)}")
                    self.stdout.write(f"   📋 Primeiro ID: {logs[0]['id']}")
                    self.stdout.write(f"   📋 Último ID: {logs[-1]['id']}")
                    
                    # Verificar se há logs novos
                    last_catraca_id = logs[-1]['id']
                    last_banco_id = status['last_processed_id']
                    
                    if last_catraca_id > last_banco_id:
                        self.stdout.write(f"   🆕 Há {last_catraca_id - last_banco_id} logs novos na catraca!")
                    else:
                        self.stdout.write("   ℹ️ Nenhum log novo na catraca")
                else:
                    self.stdout.write("   ⚠️ Nenhum log encontrado na catraca")
            else:
                self.stdout.write("   ❌ Não foi possível conectar à catraca")
        except Exception as e:
            self.stdout.write(f"   ❌ Erro ao conectar: {e}")
        
        # 4. Verificar sequência
        self.stdout.write("\n4️⃣ VERIFICAÇÃO DE SEQUÊNCIA:")
        try:
            if total_logs > 0:
                # Buscar logs em sequência
                logs = list(AccessLog.objects.order_by('device_log_id')[:20])
                gaps = []
                last_id = None
                
                for log in logs:
                    current_id = log.device_log_id
                    if last_id is not None and current_id != last_id + 1:
                        gaps.append(f"IDs {last_id + 1} a {current_id - 1}")
                    last_id = current_id
                
                if gaps:
                    self.stdout.write(f"   ⚠️ Lacunas encontradas: {', '.join(gaps)}")
                else:
                    self.stdout.write("   ✅ Sequência está correta")
            else:
                self.stdout.write("   ℹ️ Nenhum log para verificar")
        except Exception as e:
            self.stdout.write(f"   ❌ Erro ao verificar sequência: {e}")
        
        # 5. Recomendações
        self.stdout.write("\n5️⃣ RECOMENDAÇÕES:")
        
        if not status['running']:
            self.stdout.write("   🔧 Reiniciar monitoramento:")
            self.stdout.write("      python manage.py shell -c \"from apps.logs.services import log_monitor_service; log_monitor_service.start_monitoring()\"")
        
        if status['consecutive_errors'] > 0:
            self.stdout.write("   🔧 Reiniciar monitoramento devido a erros:")
            self.stdout.write("      python manage.py shell -c \"from apps.logs.services import log_monitor_service; log_monitor_service.stop_monitoring(); log_monitor_service.start_monitoring()\"")
        
        # Verificar se há logs novos não processados
        try:
            if client.is_connected():
                logs = client.get_recent_access_logs(limit=10)
                if logs:
                    last_catraca_id = logs[-1]['id']
                    last_banco_id = status['last_processed_id']
                    
                    if last_catraca_id > last_banco_id:
                        self.stdout.write("   🔧 Processar logs pendentes:")
                        self.stdout.write(f"      python manage.py shell -c \"from apps.logs.services import log_monitor_service; log_monitor_service.last_processed_id = {last_catraca_id - 1}\"")
        except:
            pass
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("✅ Diagnóstico concluído")
