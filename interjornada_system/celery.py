"""
Configuração do Celery para o projeto interjornada_system.
"""
import os
from celery import Celery

# Configurar Django settings para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')

app = Celery('interjornada_system')

# Configurar Celery usando Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobrir tarefas em todos os apps
app.autodiscover_tasks()

# Configurações específicas do Celery
app.conf.update(
    # Configurações de timezone
    timezone='UTC',
    enable_utc=True,
    
    # Configurações de serialização
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Configurações de resultado
    result_backend='redis://localhost:6379/0',
    result_expires=3600,
    
    # Configurações de worker
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    
    # Configurações de roteamento
    task_routes={
        'apps.devices.tasks.*': {'queue': 'devices'},
        'apps.logs.tasks.*': {'queue': 'logs'},
        'apps.interjornada.tasks.*': {'queue': 'interjornada'},
        'apps.dashboard.tasks.*': {'queue': 'dashboard'},
    },
    
    # Configurações de beat (agendamento)
    beat_schedule={
        'monitor-devices': {
            'task': 'apps.devices.tasks.monitor_devices_task',
            'schedule': 3.0,  # A cada 3 segundos
        },
        'process-log-queue': {
            'task': 'apps.logs.tasks.process_log_queue_task',
            'schedule': 1.0,  # A cada 1 segundo
        },
        'monitor-interjornada': {
            'task': 'apps.interjornada.tasks.monitor_interjornada_task',
            'schedule': 5.0,  # A cada 5 segundos
        },
        'cleanup-old-logs': {
            'task': 'apps.logs.tasks.cleanup_old_logs_task',
            'schedule': 3600.0,  # A cada hora
        },
        'update-statistics': {
            'task': 'apps.interjornada.tasks.update_daily_statistics_task',
            'schedule': 300.0,  # A cada 5 minutos
        },
    },
)

@app.task(bind=True)
def debug_task(self):
    """Tarefa de debug para testar Celery."""
    print(f'Request: {self.request!r}')
    return 'Celery está funcionando!'
