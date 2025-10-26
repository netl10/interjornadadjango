"""
Comando Django para monitorar novos logs em tempo real.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
import time


class Command(BaseCommand):
    help = 'Monitora novos logs em tempo real'

    def add_arguments(self, parser):
        parser.add_argument('--duration', type=int, default=60, help='Duração do monitoramento em segundos (padrão: 60)')

    def handle(self, *args, **options):
        duration = options['duration']
        
        self.stdout.write("👀 MONITORANDO NOVOS LOGS EM TEMPO REAL")
        self.stdout.write("=" * 60)
        self.stdout.write(f"⏱️  Duração: {duration} segundos")
        self.stdout.write(f"🔄 Intervalo: {log_monitor_service.monitor_interval} segundo(s)")
        self.stdout.write(f"📊 Último ID processado: {log_monitor_service.last_processed_id}")
        self.stdout.write("")
        self.stdout.write("💡 Faça um acesso na catraca para testar!")
        self.stdout.write("")
        
        start_time = time.time()
        last_log_count = AccessLog.objects.count()
        last_processed_id = log_monitor_service.last_processed_id
        
        self.stdout.write(f"📊 Logs iniciais no banco: {last_log_count}")
        self.stdout.write(f"📊 Último ID inicial: {last_processed_id}")
        self.stdout.write("")
        
        try:
            while time.time() - start_time < duration:
                current_time = time.time()
                elapsed = int(current_time - start_time)
                remaining = duration - elapsed
                
                # Verificar novos logs
                current_log_count = AccessLog.objects.count()
                current_processed_id = log_monitor_service.last_processed_id
                
                if current_log_count > last_log_count:
                    new_logs = current_log_count - last_log_count
                    self.stdout.write(self.style.SUCCESS(f"🆕 {elapsed}s: {new_logs} novo(s) log(s) detectado(s)! Total: {current_log_count}"))
                    
                    # Mostrar o último log
                    last_log = AccessLog.objects.order_by('-device_log_id').first()
                    if last_log:
                        self.stdout.write(f"   📝 Último: ID {last_log.device_log_id} - {last_log.user_name} - {last_log.device_timestamp}")
                    
                    last_log_count = current_log_count
                
                if current_processed_id > last_processed_id:
                    self.stdout.write(self.style.SUCCESS(f"🔄 {elapsed}s: Último ID processado atualizado: {current_processed_id}"))
                    last_processed_id = current_processed_id
                
                # Status a cada 10 segundos
                if elapsed % 10 == 0 and elapsed > 0:
                    self.stdout.write(f"⏰ {elapsed}s: Monitorando... (restam {remaining}s)")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stdout.write("\n🛑 Monitoramento interrompido pelo usuário")
        
        # Resumo final
        final_log_count = AccessLog.objects.count()
        final_processed_id = log_monitor_service.last_processed_id
        
        self.stdout.write("")
        self.stdout.write("📊 RESUMO FINAL:")
        self.stdout.write(f"   Logs iniciais: {last_log_count}")
        self.stdout.write(f"   Logs finais: {final_log_count}")
        self.stdout.write(f"   Novos logs: {final_log_count - last_log_count}")
        self.stdout.write(f"   Último ID inicial: {log_monitor_service.last_processed_id}")
        self.stdout.write(f"   Último ID final: {final_processed_id}")
        
        if final_log_count > last_log_count:
            self.stdout.write(self.style.SUCCESS("✅ Novos logs foram detectados e processados!"))
        else:
            self.stdout.write(self.style.WARNING("⚠️  Nenhum novo log foi detectado"))
