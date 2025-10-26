"""
Tarefas Celery para o app logs.
"""
from celery import shared_task
from django.conf import settings
from .models import AccessLog, SystemLog, LogProcessingQueue
from .services import log_processing_service, log_queue_service
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='apps.logs.tasks.process_device_logs_task')
def process_device_logs_task(self, device_id, logs):
    """
    Tarefa para processar logs de um dispositivo.
    """
    try:
        from apps.devices.models import Device
        device = Device.objects.get(id=device_id)
        
        # Processar logs
        stats = log_processing_service.process_device_logs(logs, device_id, device.name)
        
        # Log de processamento
        SystemLog.log_info(
            message=f"Logs processados do dispositivo {device.name}: {stats['new_logs']} novos, {stats['processed_logs']} processados",
            category='logs',
            device_id=device_id,
            device_name=device.name,
            details=stats
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro na tarefa de processamento de logs do dispositivo {device_id}: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de processamento de logs: {str(e)}",
            category='logs',
            device_id=device_id,
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.logs.tasks.process_log_queue_task')
def process_log_queue_task(self):
    """
    Tarefa para processar fila de logs.
    """
    try:
        # Verificar se processamento está ativo
        if not log_queue_service.is_processing:
            return {
                'status': 'stopped',
                'message': 'Processamento não está ativo'
            }
        
        # Processar fila
        stats = log_queue_service.process_queue(batch_size=10)
        
        # Log de processamento
        if stats['status'] == 'running' and (stats['processed'] > 0 or stats['failed'] > 0):
            SystemLog.log_info(
                message=f"Fila de logs processada: {stats['processed']} processados, {stats['failed']} falharam",
                category='logs',
                details=stats
            )
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro na tarefa de processamento da fila de logs: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de processamento da fila: {str(e)}",
            category='logs',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.logs.tasks.cleanup_old_logs_task')
def cleanup_old_logs_task(self, days=30):
    """
    Tarefa para limpar logs antigos.
    """
    try:
        from datetime import datetime, timedelta
        cutoff_date = TimezoneUtils.get_utc_now() - timedelta(days=days)
        
        # Limpar logs de acesso antigos
        access_logs_deleted = AccessLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        # Limpar logs do sistema antigos
        system_logs_deleted = SystemLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        # Limpar entradas da fila antigas
        queue_entries_deleted = LogProcessingQueue.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed']
        ).delete()[0]
        
        total_deleted = access_logs_deleted + system_logs_deleted + queue_entries_deleted
        
        if total_deleted > 0:
            SystemLog.log_info(
                message=f"Limpeza de logs antigos concluída: {total_deleted} registros removidos",
                category='logs',
                details={
                    'access_logs_deleted': access_logs_deleted,
                    'system_logs_deleted': system_logs_deleted,
                    'queue_entries_deleted': queue_entries_deleted,
                    'cutoff_date': cutoff_date.isoformat()
                }
            )
        
        return {
            'status': 'success',
            'message': f'Limpeza concluída: {total_deleted} registros removidos',
            'access_logs_deleted': access_logs_deleted,
            'system_logs_deleted': system_logs_deleted,
            'queue_entries_deleted': queue_entries_deleted,
            'total_deleted': total_deleted,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de limpeza de logs antigos: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de limpeza de logs: {str(e)}",
            category='logs',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.logs.tasks.retry_failed_logs_task')
def retry_failed_logs_task(self):
    """
    Tarefa para tentar novamente logs que falharam.
    """
    try:
        # Buscar logs que falharam e podem ser tentados novamente
        failed_logs = LogProcessingQueue.objects.filter(
            status='failed',
            attempts__lt=3  # Máximo de 3 tentativas
        ).order_by('created_at')[:50]  # Limitar a 50 por vez
        
        retry_count = 0
        success_count = 0
        error_count = 0
        
        for queue_entry in failed_logs:
            try:
                # Marcar como processando
                queue_entry.mark_as_processing()
                
                # Tentar processar novamente
                success = log_queue_service._process_queue_entry(queue_entry)
                
                if success:
                    queue_entry.mark_as_completed()
                    success_count += 1
                else:
                    queue_entry.mark_as_failed("Tentativa de retry falhou")
                    error_count += 1
                
                retry_count += 1
                
            except Exception as e:
                queue_entry.mark_as_failed(f"Erro no retry: {str(e)}")
                error_count += 1
                retry_count += 1
                logger.error(f"Erro ao processar retry do log {queue_entry.id}: {e}")
        
        if retry_count > 0:
            SystemLog.log_info(
                message=f"Retry de logs falhados concluído: {retry_count} tentados, {success_count} sucessos, {error_count} falhas",
                category='logs',
                details={
                    'retry_count': retry_count,
                    'success_count': success_count,
                    'error_count': error_count
                }
            )
        
        return {
            'status': 'success',
            'message': f'Retry concluído: {retry_count} tentados',
            'retry_count': retry_count,
            'success_count': success_count,
            'error_count': error_count
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de retry de logs falhados: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de retry: {str(e)}",
            category='logs',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.logs.tasks.generate_log_report_task')
def generate_log_report_task(self, date_from, date_to):
    """
    Tarefa para gerar relatório de logs.
    """
    try:
        from datetime import datetime
        from django.db.models import Count, Q
        
        # Converter strings para datetime
        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        
        # Estatísticas de logs de acesso
        access_logs_stats = AccessLog.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        ).aggregate(
            total_logs=Count('id'),
            processed_logs=Count('id', filter=Q(processing_status='processed')),
            pending_logs=Count('id', filter=Q(processing_status='pending')),
            error_logs=Count('id', filter=Q(processing_status='error'))
        )
        
        # Estatísticas de logs do sistema
        system_logs_stats = SystemLog.objects.filter(
            timestamp__gte=date_from,
            timestamp__lte=date_to
        ).values('level').annotate(count=Count('id'))
        
        # Estatísticas por dispositivo
        device_stats = AccessLog.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        ).values('device_name').annotate(
            total_logs=Count('id'),
            processed_logs=Count('id', filter=Q(processing_status='processed'))
        )
        
        report_data = {
            'period': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'access_logs': access_logs_stats,
            'system_logs_by_level': list(system_logs_stats),
            'device_stats': list(device_stats),
            'generated_at': TimezoneUtils.get_utc_now().isoformat()
        }
        
        SystemLog.log_info(
            message=f"Relatório de logs gerado para período {date_from.date()} a {date_to.date()}",
            category='logs',
            details=report_data
        )
        
        return report_data
        
    except Exception as e:
        logger.error(f"Erro na tarefa de geração de relatório de logs: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de relatório: {str(e)}",
            category='logs',
            details={'error': str(e)}
        )
        raise
