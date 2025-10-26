"""
Workers para processamento de logs de acesso.
"""
import threading
import time
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from typing import List, Dict, Optional
from django.db import transaction
from django.conf import settings
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee
from apps.core.utils import TimezoneUtils

logger = logging.getLogger(__name__)


class AccessLogWorker:
    """
    Worker responsável por sincronizar logs da catraca com o banco de dados,
    garantindo sequência e tolerância a quedas.
    """
    
    def __init__(self):
        self.running = False
        self.worker_thread = None
        self.client = None
        self.last_synced_id = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        self.sync_interval = getattr(settings, 'LOG_SYNC_INTERVAL', 2)  # 2 segundos
        self.batch_size = getattr(settings, 'LOG_SYNC_BATCH_SIZE', 50)
        self.device_id = getattr(settings, 'LOG_SYNC_DEVICE_ID', 1)
        
        # Configurações de retry
        self.retry_delay = 5  # segundos
        self.max_retry_delay = 60  # segundos
        
    def start_worker(self) -> bool:
        """Inicia o worker de sincronização."""
        if self.running:
            logger.warning("AccessLogWorker já está rodando")
            return False
            
        try:
            # Inicializar cliente da catraca
            self.client = DeviceClient(None)  # Usar configurações do settings
            if not self.client.login():
                logger.error("Falha ao fazer login na catraca")
                return False
                
            # Obter último ID sincronizado
            self._load_last_synced_id()
            
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            
            logger.info(f"AccessLogWorker iniciado (intervalo: {self.sync_interval}s, batch: {self.batch_size})")
            logger.info(f"Último ID sincronizado: {self.last_synced_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar AccessLogWorker: {e}")
            self.running = False
            return False
    
    def stop_worker(self):
        """Para o worker de sincronização."""
        if not self.running:
            return
            
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            
        logger.info("AccessLogWorker parado")
    
    def _load_last_synced_id(self):
        """Carrega o último ID sincronizado do banco."""
        try:
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            if last_log:
                self.last_synced_id = last_log.device_log_id
                logger.info(f"Último log sincronizado: ID {self.last_synced_id}")
            else:
                self.last_synced_id = 0
                logger.info("Nenhum log anterior encontrado, iniciando do zero")
        except Exception as e:
            logger.error(f"Erro ao carregar último ID sincronizado: {e}")
            self.last_synced_id = 0
    
    def _worker_loop(self):
        """Loop principal do worker."""
        logger.info("Loop do AccessLogWorker iniciado")
        
        while self.running:
            try:
                # Sincronizar logs
                synced_count = self._sync_logs()
                
                if synced_count > 0:
                    logger.info(f"{synced_count} logs sincronizados (último ID: {self.last_synced_id})")
                    self.consecutive_errors = 0
                else:
                    # Log apenas a cada 30 ciclos sem novos logs
                    if not hasattr(self, '_no_sync_count'):
                        self._no_sync_count = 0
                    self._no_sync_count += 1
                    if self._no_sync_count % 30 == 0:
                        logger.debug(f"Nenhum log novo para sincronizar (último ID: {self.last_synced_id})")
                
                # Aguardar próximo ciclo
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Erro no ciclo do AccessLogWorker: {e}")
                self.consecutive_errors += 1
                
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.error(f"Muitos erros consecutivos ({self.consecutive_errors}). Parando worker.")
                    self.running = False
                    break
                
                # Delay exponencial para retry
                delay = min(self.retry_delay * (2 ** self.consecutive_errors), self.max_retry_delay)
                logger.warning(f"Aguardando {delay}s antes de tentar novamente...")
                time.sleep(delay)
        
        logger.info("Loop do AccessLogWorker finalizado")
    
    def _sync_logs(self) -> int:
        """Sincroniza logs da catraca com o banco."""
        try:
            # Verificar conexão
            if not self.client.is_connected():
                logger.warning("Conexão perdida, tentando reconectar...")
                if not self.client.login():
                    logger.error("Falha ao reconectar")
                    return 0
            
            # Buscar logs da catraca (apenas IDs positivos para evitar logs manuais)
            logs = self.client.get_recent_access_logs(
                limit=self.batch_size,
                min_id=max(1, self.last_synced_id)  # Garantir que min_id seja sempre positivo
            )
            
            if not logs:
                return 0
            
            # Verificar se o dispositivo foi reinicializado
            # Se todos os logs do dispositivo têm IDs menores que o último sincronizado,
            # provavelmente o dispositivo foi reinicializado
            max_device_log_id = max(log.get('id', 0) for log in logs)
            if max_device_log_id < self.last_synced_id:
                logger.warning(f"Dispositivo pode ter sido reinicializado! "
                             f"Último ID sincronizado: {self.last_synced_id}, "
                             f"Maior ID no dispositivo: {max_device_log_id}")
                
                # Buscar logs mais recentes sem filtro de min_id
                logs = self.client.get_recent_access_logs(
                    limit=self.batch_size,
                    min_id=0
                )
                
                if not logs:
                    return 0
                
                logger.info(f"Buscando logs sem filtro de ID. Encontrados {len(logs)} logs")
            
            # Processar logs em lote
            synced_count = 0
            with transaction.atomic():
                for log_data in logs:
                    if self._process_log_data(log_data):
                        synced_count += 1
                        self.last_synced_id = max(self.last_synced_id, log_data.get('id', 0))
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar logs: {e}")
            return 0
    
    def _process_log_data(self, log_data: Dict) -> bool:
        """Processa um log individual da catraca."""
        try:
            log_id = log_data.get('id')
            if not log_id:
                logger.warning("Log sem ID, ignorando")
                return False
            
            # Filtrar logs manuais (IDs negativos)
            if log_id <= 0:
                logger.debug(f"Log {log_id} é manual (ID negativo), ignorando")
                return True
            
            # Verificar se já existe
            if AccessLog.objects.filter(device_log_id=log_id).exists():
                logger.debug(f"Log {log_id} já existe, ignorando")
                return True
            
            # Mapear dados do log
            user_id = log_data.get('user_id', 0)
            event_code = log_data.get('event', 0)
            portal_id = log_data.get('portal_id', 1)
            timestamp = log_data.get('time', 0)
            
            # Usar timestamp exato da catraca (sem conversão)
            if timestamp:
                # A catraca envia timestamp Unix que precisa ser ajustado
                # O timestamp Unix da catraca está 3 horas atrás do correto
                import pytz
                local_tz = pytz.timezone('America/Sao_Paulo')
                # Ajustar o timestamp Unix adicionando 3 horas (10800 segundos)
                adjusted_timestamp = timestamp + 10800
                local_time = datetime.fromtimestamp(adjusted_timestamp, tz=local_tz)
                device_timestamp = local_time.astimezone(pytz.UTC)
            else:
                device_timestamp = timezone.now()
            
            # Obter nome do usuário
            user_name = self._get_user_name(user_id, log_data)
            
            # Mapear evento
            event_description = self._map_event_code(event_code)
            
            # Criar log no banco
            # created_at deve ser exatamente igual ao device_timestamp (horário local)
            access_log = AccessLog.objects.create(
                device_log_id=log_id,
                user_id=user_id,
                user_name=user_name,
                event_type=event_code,
                event_description=event_description,
                portal_id=portal_id,
                device_timestamp=device_timestamp,
                raw_data=log_data,
                processing_status='pending',
                created_at=device_timestamp,
                updated_at=device_timestamp
            )
            
            logger.debug(f"Log {log_id} criado: {user_name} - {event_description}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar log {log_data.get('id', 'unknown')}: {e}")
            return False
    
    def _get_user_name(self, user_id: int, log_data: Dict) -> str:
        """Obtém o nome do usuário."""
        if user_id == 0:
            return "Não Identificado"
        
        try:
            # Tentar buscar no banco local primeiro
            employee = Employee.objects.filter(device_id=user_id, is_active=True).first()
            if employee:
                return employee.name
            
            # Se não encontrou, tentar buscar na catraca
            if self.client:
                users = self.client.get_users()
                for user in users:
                    if user.get('id') == user_id:
                        return user.get('name', f'Usuário {user_id}')
            
            return f'Usuário {user_id}'
            
        except Exception as e:
            logger.warning(f"Erro ao obter nome do usuário {user_id}: {e}")
            return f'Usuário {user_id}'
    
    def _map_event_code(self, event_code: int) -> str:
        """Mapeia código do evento para descrição."""
        event_map = {
            1: "Entrada",
            2: "Saída", 
            3: "Não Identificado",
            4: "Erro de Leitura",
            5: "Timeout",
            6: "Acesso Negado",
            7: "Acesso Autorizado",
            8: "Acesso Bloqueado",
            9: "Negado",
            10: "Negado",
            11: "Negado",
            12: "Negado",
            13: "Desistência",
            14: "Negado",
            15: "Negado"
        }
        return event_map.get(event_code, f"Evento {event_code}")
    
    def get_status(self) -> Dict:
        """Retorna status do worker."""
        return {
            'running': self.running,
            'last_synced_id': self.last_synced_id,
            'consecutive_errors': self.consecutive_errors,
            'sync_interval': self.sync_interval,
            'batch_size': self.batch_size,
            'connected': self.client.is_connected() if self.client else False
        }


# Instância global do worker
access_log_worker = AccessLogWorker()
