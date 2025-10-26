"""
Comando para verificar status geral do sistema de logs e sessões.
"""
from django.core.management.base import BaseCommand
from apps.logs.services import log_monitor_service
from apps.logs.workers import access_log_worker
from apps.logs.models import AccessLog
from apps.employees.models import EmployeeSession


class Command(BaseCommand):
    help = 'Verifica status geral do sistema de logs e sessões'

    def handle(self, *args, **options):
        self.stdout.write('📊 STATUS GERAL DO SISTEMA\n')
        
        # Status do AccessLogWorker
        self.stdout.write('🔄 ACCESSLOGWORKER (Sincronização da Catraca):')
        worker_status = access_log_worker.get_status()
        self.stdout.write(f'   Rodando: {worker_status["running"]}')
        self.stdout.write(f'   Último ID sincronizado: {worker_status["last_synced_id"]}')
        self.stdout.write(f'   Erros consecutivos: {worker_status["consecutive_errors"]}')
        self.stdout.write(f'   Conectado à catraca: {worker_status["connected"]}')
        
        # Status do LogMonitorService
        self.stdout.write('\n📋 LOGMONITORSERVICE (Processamento de Sessões):')
        monitor_status = log_monitor_service.get_status()
        self.stdout.write(f'   Rodando: {monitor_status["running"]}')
        self.stdout.write(f'   Último ID processado: {monitor_status["last_processed_id"]}')
        self.stdout.write(f'   Logs pendentes: {monitor_status["pending_logs"]}')
        
        # Estatísticas do banco
        self.stdout.write('\n📈 ESTATÍSTICAS DO BANCO:')
        total_logs = AccessLog.objects.count()
        processed_logs = AccessLog.objects.filter(session_processed=True).count()
        pending_logs = AccessLog.objects.filter(session_processed=False).count()
        
        self.stdout.write(f'   Total de logs: {total_logs}')
        self.stdout.write(f'   Logs processados: {processed_logs}')
        self.stdout.write(f'   Logs pendentes: {pending_logs}')
        
        # Sessões ativas
        active_sessions = EmployeeSession.objects.filter(state='active').count()
        blocked_sessions = EmployeeSession.objects.filter(state='blocked').count()
        total_sessions = EmployeeSession.objects.count()
        
        self.stdout.write(f'   Sessões ativas: {active_sessions}')
        self.stdout.write(f'   Sessões bloqueadas: {blocked_sessions}')
        self.stdout.write(f'   Total de sessões: {total_sessions}')
        
        # Logs recentes
        self.stdout.write('\n📝 LOGS RECENTES (últimos 5):')
        recent_logs = AccessLog.objects.order_by('-device_log_id')[:5]
        for log in recent_logs:
            status = "✅" if log.session_processed else "⏳"
            self.stdout.write(f'   {status} ID {log.device_log_id}: {log.user_name} - {log.event_description}')
        
        # Verificar lacunas na sequência
        self.stdout.write('\n🔍 VERIFICAÇÃO DE SEQUÊNCIA:')
        if total_logs > 0:
            first_log = AccessLog.objects.order_by('device_log_id').first()
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            
            expected_count = last_log.device_log_id - first_log.device_log_id + 1
            actual_count = total_logs
            
            if expected_count == actual_count:
                self.stdout.write('   ✅ Sequência de logs está íntegra')
            else:
                missing = expected_count - actual_count
                self.stdout.write(f'   ⚠️ Possível lacuna: {missing} logs podem estar faltando')
                self.stdout.write(f'   Primeiro ID: {first_log.device_log_id}, Último ID: {last_log.device_log_id}')
        
        self.stdout.write('\n' + '='*50)
        
        # Recomendações
        if not worker_status["running"]:
            self.stdout.write(self.style.WARNING('⚠️ RECOMENDAÇÃO: AccessLogWorker não está rodando'))
            self.stdout.write('   Execute: python manage.py access_log_worker start')
        
        if not monitor_status["running"]:
            self.stdout.write(self.style.WARNING('⚠️ RECOMENDAÇÃO: LogMonitorService não está rodando'))
            self.stdout.write('   Execute: python manage.py restart_monitoring')
        
        if pending_logs > 100:
            self.stdout.write(self.style.WARNING(f'⚠️ RECOMENDAÇÃO: {pending_logs} logs pendentes'))
            self.stdout.write('   Considere verificar se o processamento está funcionando')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Verificação concluída!'))
