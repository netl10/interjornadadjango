"""
Tarefas Celery para o app interjornada.
"""
from celery import shared_task
from django.conf import settings
from .models import InterjornadaCycle, InterjornadaViolation, InterjornadaStatistics
from .services import interjornada_service, interjornada_monitoring_service
from apps.logs.models import SystemLog
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='apps.interjornada.tasks.monitor_interjornada_task')
def monitor_interjornada_task(self):
    """
    Tarefa para monitorar ciclos de interjornada.
    """
    try:
        # Verificar se monitoramento está ativo
        if not interjornada_monitoring_service.is_monitoring:
            return {
                'status': 'stopped',
                'message': 'Monitoramento não está ativo'
            }
        
        # Executar monitoramento
        stats = interjornada_monitoring_service.monitor_cycles()
        
        # Log de sucesso
        if stats['status'] == 'running':
            SystemLog.log_info(
                message=f"Monitoramento de interjornada executado: {stats['total_active_cycles']} ciclos ativos",
                category='interjornada',
                details=stats
            )
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro na tarefa de monitoramento de interjornada: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de monitoramento de interjornada: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.interjornada.tasks.process_access_event_task')
def process_access_event_task(self, employee_id, event_type, timestamp_str):
    """
    Tarefa para processar evento de acesso de funcionário.
    """
    try:
        from apps.employees.models import Employee
        from datetime import datetime
        
        employee = Employee.objects.get(device_id=employee_id, is_active=True)
        
        # Converter timestamp
        if isinstance(timestamp_str, str):
            timestamp = TimezoneUtils.parse_datetime(timestamp_str)
            if not timestamp:
                timestamp = TimezoneUtils.get_utc_now()
        else:
            timestamp = TimezoneUtils.get_utc_now()
        
        # Processar evento
        result = interjornada_service.process_access_event(employee, event_type, timestamp)
        
        # Log do resultado
        if result['success']:
            SystemLog.log_info(
                message=f"Evento de acesso processado para {employee.name}: {result['message']}",
                category='interjornada',
                user_id=employee.device_id,
                user_name=employee.name,
                details=result
            )
        else:
            SystemLog.log_warning(
                message=f"Evento de acesso negado para {employee.name}: {result['message']}",
                category='interjornada',
                user_id=employee.device_id,
                user_name=employee.name,
                details=result
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro na tarefa de processamento de evento de acesso: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de evento de acesso: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.interjornada.tasks.create_cycle_task')
def create_cycle_task(self, employee_id):
    """
    Tarefa para criar ciclo de interjornada.
    """
    try:
        from apps.employees.models import Employee
        
        employee = Employee.objects.get(device_id=employee_id, is_active=True)
        
        # Criar ciclo
        cycle = interjornada_service.create_cycle(employee)
        
        if cycle:
            SystemLog.log_info(
                message=f"Ciclo de interjornada criado para {employee.name}",
                category='interjornada',
                user_id=employee.device_id,
                user_name=employee.name,
                details={
                    'cycle_id': cycle.id,
                    'rule_id': cycle.rule.id,
                    'work_duration': cycle.rule.work_duration_minutes,
                    'rest_duration': cycle.rule.rest_duration_minutes
                }
            )
            
            return {
                'success': True,
                'message': 'Ciclo criado com sucesso',
                'cycle_id': cycle.id,
                'employee_id': employee_id
            }
        else:
            return {
                'success': False,
                'message': 'Não foi possível criar ciclo',
                'employee_id': employee_id
            }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de criação de ciclo: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de criação de ciclo: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.interjornada.tasks.complete_cycle_task')
def complete_cycle_task(self, employee_id):
    """
    Tarefa para completar ciclo de interjornada.
    """
    try:
        from apps.employees.models import Employee
        
        employee = Employee.objects.get(device_id=employee_id, is_active=True)
        
        # Completar ciclo
        success = interjornada_service.complete_cycle(employee)
        
        if success:
            SystemLog.log_info(
                message=f"Ciclo de interjornada completado para {employee.name}",
                category='interjornada',
                user_id=employee.device_id,
                user_name=employee.name
            )
            
            return {
                'success': True,
                'message': 'Ciclo completado com sucesso',
                'employee_id': employee_id
            }
        else:
            return {
                'success': False,
                'message': 'Nenhum ciclo ativo encontrado',
                'employee_id': employee_id
            }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de conclusão de ciclo: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de conclusão de ciclo: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.interjornada.tasks.update_daily_statistics_task')
def update_daily_statistics_task(self):
    """
    Tarefa para atualizar estatísticas diárias.
    """
    try:
        from datetime import date, timedelta
        from django.db.models import Count, Sum, Avg
        
        today = date.today()
        
        # Buscar ciclos do dia
        today_cycles = InterjornadaCycle.objects.filter(
            cycle_start__date=today
        )
        
        # Estatísticas gerais do dia
        total_cycles = today_cycles.count()
        completed_cycles = today_cycles.filter(current_state='completed').count()
        active_cycles = today_cycles.filter(current_state__in=['work', 'rest']).count()
        
        # Violações do dia
        today_violations = InterjornadaViolation.objects.filter(
            violation_time__date=today
        )
        
        total_violations = today_violations.count()
        critical_violations = today_violations.filter(severity='critical').count()
        resolved_violations = today_violations.filter(resolved=True).count()
        
        # Atualizar estatísticas por funcionário
        employees_with_cycles = today_cycles.values('employee').distinct()
        
        for employee_data in employees_with_cycles:
            employee_id = employee_data['employee']
            
            # Buscar ou criar estatística do dia
            stats, created = InterjornadaStatistics.objects.get_or_create(
                employee_id=employee_id,
                date=today,
                defaults={
                    'total_cycles': 0,
                    'completed_cycles': 0,
                    'total_work_time_minutes': 0,
                    'total_rest_time_minutes': 0,
                    'total_violations': 0,
                }
            )
            
            # Calcular estatísticas do funcionário
            employee_cycles = today_cycles.filter(employee_id=employee_id)
            employee_violations = today_violations.filter(cycle__employee_id=employee_id)
            
            stats.total_cycles = employee_cycles.count()
            stats.completed_cycles = employee_cycles.filter(current_state='completed').count()
            stats.total_violations = employee_violations.count()
            stats.resolved_violations = employee_violations.filter(resolved=True).count()
            stats.critical_violations = employee_violations.filter(severity='critical').count()
            
            # Calcular tempos
            work_times = employee_cycles.exclude(actual_work_duration_minutes__isnull=True).values_list('actual_work_duration_minutes', flat=True)
            rest_times = employee_cycles.exclude(actual_rest_duration_minutes__isnull=True).values_list('actual_rest_duration_minutes', flat=True)
            
            stats.total_work_time_minutes = sum(work_times) if work_times else 0
            stats.total_rest_time_minutes = sum(rest_times) if rest_times else 0
            
            # Calcular médias
            if stats.total_cycles > 0:
                stats.average_work_time_minutes = stats.total_work_time_minutes / stats.total_cycles
                stats.average_rest_time_minutes = stats.total_rest_time_minutes / stats.total_cycles
            
            stats.save()
        
        # Log de atualização
        SystemLog.log_info(
            message=f"Estatísticas diárias atualizadas: {total_cycles} ciclos, {total_violations} violações",
            category='interjornada',
            details={
                'date': today.isoformat(),
                'total_cycles': total_cycles,
                'completed_cycles': completed_cycles,
                'active_cycles': active_cycles,
                'total_violations': total_violations,
                'critical_violations': critical_violations,
                'resolved_violations': resolved_violations,
                'employees_updated': len(employees_with_cycles)
            }
        )
        
        return {
            'status': 'success',
            'message': 'Estatísticas atualizadas com sucesso',
            'date': today.isoformat(),
            'total_cycles': total_cycles,
            'completed_cycles': completed_cycles,
            'active_cycles': active_cycles,
            'total_violations': total_violations,
            'critical_violations': critical_violations,
            'resolved_violations': resolved_violations,
            'employees_updated': len(employees_with_cycles)
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de atualização de estatísticas: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de estatísticas: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.interjornada.tasks.check_violations_task')
def check_violations_task(self):
    """
    Tarefa para verificar violações pendentes.
    """
    try:
        # Buscar violações não resolvidas
        unresolved_violations = InterjornadaViolation.objects.filter(
            resolved=False
        ).select_related('cycle__employee')
        
        # Violações críticas
        critical_violations = unresolved_violations.filter(severity='critical')
        
        # Violações antigas (mais de 1 hora)
        from datetime import timedelta
        old_violations = unresolved_violations.filter(
            violation_time__lt=TimezoneUtils.get_utc_now() - timedelta(hours=1)
        )
        
        # Log de violações
        if critical_violations.exists():
            SystemLog.log_warning(
                message=f"Violations críticas pendentes: {critical_violations.count()}",
                category='interjornada',
                details={
                    'critical_count': critical_violations.count(),
                    'total_unresolved': unresolved_violations.count(),
                    'old_violations': old_violations.count()
                }
            )
        
        return {
            'status': 'success',
            'message': 'Verificação de violações concluída',
            'total_unresolved': unresolved_violations.count(),
            'critical_violations': critical_violations.count(),
            'old_violations': old_violations.count()
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de verificação de violações: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de violações: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.interjornada.tasks.cleanup_old_cycles_task')
def cleanup_old_cycles_task(self, days=30):
    """
    Tarefa para limpar ciclos antigos.
    """
    try:
        from datetime import timedelta
        
        cutoff_date = TimezoneUtils.get_utc_now() - timedelta(days=days)
        
        # Limpar ciclos antigos completados
        old_cycles = InterjornadaCycle.objects.filter(
            current_state='completed',
            cycle_start__lt=cutoff_date
        )
        
        cycles_deleted = old_cycles.count()
        old_cycles.delete()
        
        # Limpar violações antigas resolvidas
        old_violations = InterjornadaViolation.objects.filter(
            resolved=True,
            violation_time__lt=cutoff_date
        )
        
        violations_deleted = old_violations.count()
        old_violations.delete()
        
        total_deleted = cycles_deleted + violations_deleted
        
        if total_deleted > 0:
            SystemLog.log_info(
                message=f"Limpeza de ciclos antigos concluída: {total_deleted} registros removidos",
                category='interjornada',
                details={
                    'cycles_deleted': cycles_deleted,
                    'violations_deleted': violations_deleted,
                    'cutoff_date': cutoff_date.isoformat()
                }
            )
        
        return {
            'status': 'success',
            'message': f'Limpeza concluída: {total_deleted} registros removidos',
            'cycles_deleted': cycles_deleted,
            'violations_deleted': violations_deleted,
            'total_deleted': total_deleted,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de limpeza de ciclos antigos: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de limpeza: {str(e)}",
            category='interjornada',
            details={'error': str(e)}
        )
        raise
