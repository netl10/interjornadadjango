"""
Tarefas Celery para o app employees.
"""
from celery import shared_task
from django.conf import settings
from .models import Employee
from apps.logs.models import SystemLog
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='apps.employees.tasks.sync_employees_from_device_task')
def sync_employees_from_device_task(self, device_id, users_data):
    """
    Tarefa para sincronizar funcionários de um dispositivo.
    """
    try:
        from apps.devices.models import Device
        device = Device.objects.get(id=device_id)
        
        synced_count = 0
        updated_count = 0
        error_count = 0
        
        for user_data in users_data:
            try:
                device_user_id = user_data.get('id')
                user_name = user_data.get('name', f'Usuário {device_user_id}')
                
                if not device_user_id:
                    continue
                
                # Buscar ou criar funcionário
                employee, created = Employee.objects.get_or_create(
                    device_id=device_user_id,
                    defaults={
                        'name': user_name,
                        'is_active': True,
                        'is_exempt': False,
                        'groups': [],
                        'exemption_groups': []
                    }
                )
                
                if created:
                    synced_count += 1
                    SystemLog.log_info(
                        message=f"Funcionário sincronizado: {user_name} (ID: {device_user_id})",
                        category='employee',
                        user_id=device_user_id,
                        user_name=user_name,
                        device_id=device_id,
                        device_name=device.name
                    )
                else:
                    # Atualizar nome se mudou
                    if employee.name != user_name:
                        employee.name = user_name
                        employee.save(update_fields=['name'])
                        updated_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Erro ao sincronizar usuário {user_data}: {e}")
        
        SystemLog.log_info(
            message=f"Sincronização de funcionários concluída: {synced_count} novos, {updated_count} atualizados, {error_count} erros",
            category='employee',
            device_id=device_id,
            device_name=device.name,
            details={
                'synced_count': synced_count,
                'updated_count': updated_count,
                'error_count': error_count,
                'total_users': len(users_data)
            }
        )
        
        return {
            'status': 'success',
            'message': 'Sincronização concluída',
            'synced_count': synced_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'total_users': len(users_data)
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de sincronização de funcionários: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de sincronização: {str(e)}",
            category='employee',
            device_id=device_id,
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.employees.tasks.cleanup_old_sessions_task')
def cleanup_old_sessions_task(self, days=30):
    """
    Tarefa para limpar sessões antigas.
    """
    try:
        from datetime import timedelta
        
        cutoff_date = TimezoneUtils.get_utc_now() - timedelta(days=days)
        
        # Funcionalidade movida para apps.employee_sessions
        old_sessions = []
        
        sessions_deleted = old_sessions.count()
        old_sessions.delete()
        
        if sessions_deleted > 0:
            SystemLog.log_info(
                message=f"Limpeza de sessões antigas concluída: {sessions_deleted} sessões removidas",
                category='employee',
                details={
                    'sessions_deleted': sessions_deleted,
                    'cutoff_date': cutoff_date.isoformat()
                }
            )
        
        return {
            'status': 'success',
            'message': f'Limpeza concluída: {sessions_deleted} sessões removidas',
            'sessions_deleted': sessions_deleted,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de limpeza de sessões: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de limpeza: {str(e)}",
            category='employee',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.employees.tasks.update_employee_statistics_task')
def update_employee_statistics_task(self):
    """
    Tarefa para atualizar estatísticas de funcionários.
    """
    try:
        from datetime import date, timedelta
        
        today = date.today()
        
        # Estatísticas gerais
        total_employees = Employee.objects.filter(is_active=True).count()
        # Funcionalidade de sessões movida para apps.employee_sessions
        active_sessions = 0
        blocked_employees = 0
        employees_with_sessions_today = 0
        employees_accessed_today = 0
        
        SystemLog.log_info(
            message=f"Estatísticas de funcionários atualizadas",
            category='employee',
            details={
                'date': today.isoformat(),
                'total_employees': total_employees,
                'active_sessions': active_sessions,
                'blocked_employees': blocked_employees,
                'employees_with_sessions_today': employees_with_sessions_today,
                'employees_accessed_today': employees_accessed_today
            }
        )
        
        return {
            'status': 'success',
            'message': 'Estatísticas atualizadas',
            'date': today.isoformat(),
            'total_employees': total_employees,
            'active_sessions': active_sessions,
            'blocked_employees': blocked_employees,
            'employees_with_sessions_today': employees_with_sessions_today,
            'employees_accessed_today': employees_accessed_today
        }
        
    except Exception as e:
        logger.error(f"Erro na tarefa de estatísticas de funcionários: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de estatísticas: {str(e)}",
            category='employee',
            details={'error': str(e)}
        )
        raise
