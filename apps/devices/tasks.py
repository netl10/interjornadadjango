"""
Tarefas Celery para o app devices.
"""
from celery import shared_task
from django.conf import settings
from .models import Device
from .services import device_monitoring_service
from apps.logs.models import SystemLog
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='apps.devices.tasks.monitor_devices_task')
def monitor_devices_task(self):
    """
    Tarefa para monitorar dispositivos.
    """
    try:
        # Verificar se monitoramento está ativo
        if not device_monitoring_service.is_monitoring:
            return {
                'status': 'stopped',
                'message': 'Monitoramento não está ativo'
            }
        
        # Executar monitoramento
        stats = device_monitoring_service.monitor_devices()
        
        # Log de sucesso
        if stats['status'] == 'running':
            SystemLog.log_info(
                message=f"Monitoramento de dispositivos executado: {stats['devices_connected']}/{stats['devices_checked']} conectados",
                category='device',
                details=stats
            )
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro na tarefa de monitoramento de dispositivos: {e}")
        SystemLog.log_error(
            message=f"Erro na tarefa de monitoramento de dispositivos: {str(e)}",
            category='device',
            details={'error': str(e)}
        )
        raise


@shared_task(bind=True, name='apps.devices.tasks.connect_device_task')
def connect_device_task(self, device_id):
    """
    Tarefa para conectar a um dispositivo específico.
    """
    try:
        device = Device.objects.get(id=device_id)
        
        from .services import device_connection_service
        success, message, token = device_connection_service.connect_to_device(device)
        
        if success:
            SystemLog.log_info(
                message=f"Dispositivo {device.name} conectado com sucesso",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'token': token[:20] + '...' if token else None}
            )
        else:
            SystemLog.log_error(
                message=f"Falha ao conectar dispositivo {device.name}: {message}",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'error': message}
            )
        
        return {
            'device_id': device_id,
            'success': success,
            'message': message,
            'token': token[:20] + '...' if token else None
        }
        
    except Device.DoesNotExist:
        logger.error(f"Dispositivo {device_id} não encontrado")
        return {
            'device_id': device_id,
            'success': False,
            'message': 'Dispositivo não encontrado'
        }
    except Exception as e:
        logger.error(f"Erro na tarefa de conexão do dispositivo {device_id}: {e}")
        raise


@shared_task(bind=True, name='apps.devices.tasks.fetch_device_logs_task')
def fetch_device_logs_task(self, device_id, limit=100):
    """
    Tarefa para buscar logs de um dispositivo específico.
    """
    try:
        device = Device.objects.get(id=device_id)
        
        from .services import device_data_service
        success, message, logs = device_data_service.get_device_logs(device, limit)
        
        if success:
            SystemLog.log_info(
                message=f"Logs obtidos do dispositivo {device.name}: {len(logs)} registros",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'logs_count': len(logs)}
            )
            
            # Processar logs se houver
            if logs:
                from apps.logs.tasks import process_device_logs_task
                process_device_logs_task.delay(device_id, logs)
        else:
            SystemLog.log_error(
                message=f"Falha ao obter logs do dispositivo {device.name}: {message}",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'error': message}
            )
        
        return {
            'device_id': device_id,
            'success': success,
            'message': message,
            'logs_count': len(logs) if success else 0
        }
        
    except Device.DoesNotExist:
        logger.error(f"Dispositivo {device_id} não encontrado")
        return {
            'device_id': device_id,
            'success': False,
            'message': 'Dispositivo não encontrado'
        }
    except Exception as e:
        logger.error(f"Erro na tarefa de busca de logs do dispositivo {device_id}: {e}")
        raise


@shared_task(bind=True, name='apps.devices.tasks.check_device_health_task')
def check_device_health_task(self, device_id):
    """
    Tarefa para verificar saúde de um dispositivo.
    """
    try:
        device = Device.objects.get(id=device_id)
        
        from .services import device_data_service
        success, message, status_data = device_data_service.get_device_status(device)
        
        # Atualizar status do dispositivo
        device.update_connection_status(success=success, error_message=message if not success else None)
        
        if success:
            SystemLog.log_info(
                message=f"Status do dispositivo {device.name} verificado com sucesso",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details=status_data
            )
        else:
            SystemLog.log_warning(
                message=f"Problema na verificação do dispositivo {device.name}: {message}",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'error': message}
            )
        
        return {
            'device_id': device_id,
            'success': success,
            'message': message,
            'status_data': status_data,
            'connection_success_rate': device.connection_success_rate
        }
        
    except Device.DoesNotExist:
        logger.error(f"Dispositivo {device_id} não encontrado")
        return {
            'device_id': device_id,
            'success': False,
            'message': 'Dispositivo não encontrado'
        }
    except Exception as e:
        logger.error(f"Erro na tarefa de verificação de saúde do dispositivo {device_id}: {e}")
        raise


@shared_task(bind=True, name='apps.devices.tasks.sync_device_users_task')
def sync_device_users_task(self, device_id):
    """
    Tarefa para sincronizar usuários de um dispositivo.
    """
    try:
        device = Device.objects.get(id=device_id)
        
        from .services import device_data_service
        success, message, users = device_data_service.get_device_users(device)
        
        if success:
            # Processar usuários se houver
            if users:
                from apps.employees.tasks import sync_employees_from_device_task
                sync_employees_from_device_task.delay(device_id, users)
            
            SystemLog.log_info(
                message=f"Usuários sincronizados do dispositivo {device.name}: {len(users)} usuários",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'users_count': len(users)}
            )
        else:
            SystemLog.log_error(
                message=f"Falha ao sincronizar usuários do dispositivo {device.name}: {message}",
                category='device',
                device_id=device.id,
                device_name=device.name,
                details={'error': message}
            )
        
        return {
            'device_id': device_id,
            'success': success,
            'message': message,
            'users_count': len(users) if success else 0
        }
        
    except Device.DoesNotExist:
        logger.error(f"Dispositivo {device_id} não encontrado")
        return {
            'device_id': device_id,
            'success': False,
            'message': 'Dispositivo não encontrado'
        }
    except Exception as e:
        logger.error(f"Erro na tarefa de sincronização de usuários do dispositivo {device_id}: {e}")
        raise
