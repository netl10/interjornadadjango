"""
Configuração da aplicação de logs.
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.logs'
    verbose_name = 'Logs de Acesso'

    def ready(self):
        """Inicializa os serviços automáticos quando o Django estiver pronto."""
        # Importar aqui para evitar import circular
        from .services import log_monitor_service
        from .workers import access_log_worker
        
        # Verificar se estamos em modo de desenvolvimento ou produção
        import os
        from django.conf import settings
        
        # Só iniciar os serviços se não estiver em modo de teste
        if not os.environ.get('DJANGO_TESTING') and not os.environ.get('TESTING'):
            try:
                # Iniciar AccessLogWorker para sincronização da catraca
                if access_log_worker.start_worker():
                    logger.info("✅ AccessLogWorker iniciado com sucesso!")
                else:
                    logger.warning("⚠️ Falha ao iniciar AccessLogWorker")
                
                # Iniciar monitoramento automático de sessões
                if log_monitor_service.start_monitoring():
                    logger.info("✅ Monitoramento automático de sessões iniciado com sucesso!")
                else:
                    logger.warning("⚠️ Falha ao iniciar monitoramento automático de sessões")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar serviços automáticos: {e}")
        else:
            logger.info("🔍 Serviços automáticos desabilitados - modo de teste")
