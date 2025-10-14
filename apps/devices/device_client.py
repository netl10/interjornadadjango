"""
Cliente para comunicação com dispositivos IDFace - Adaptado do sistema FastAPI.
"""
import requests
import logging
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from django.conf import settings
import json

logger = logging.getLogger(__name__)


class DeviceClient:
    """Cliente para comunicação com dispositivos IDFace."""
    
    def __init__(self, device=None):
        """
        Inicializa o cliente de dispositivo.
        
        Args:
            device: Instância do modelo Device (opcional)
        """
        self.device = device
        self.session_token = None
        self.session = requests.Session()
        
        # Configurações de SSL
        self.session.verify = getattr(settings, 'SSL_VERIFY', False)
        
        # Desabilitar warnings de SSL se necessário
        if not self.session.verify:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configurações de timeout
        self.connection_timeout = getattr(settings, 'DEVICE_CONNECTION_TIMEOUT', 15)
        self.request_timeout = getattr(settings, 'DEVICE_REQUEST_TIMEOUT', 10)
        
        # Sistema de reconexão
        self.reconnection_attempts = 0
        self.max_reconnection_attempts = getattr(settings, 'MAX_RECONNECTION_ATTEMPTS', 10)
        self.base_reconnection_delay = getattr(settings, 'BASE_RECONNECTION_DELAY', 2)
        self.max_reconnection_delay = getattr(settings, 'MAX_RECONNECTION_DELAY', 60)
        
        # Controle de erros 401
        self.error_401_count = 0
        self.last_401_time = None
        self.max_401_errors = 5
        
        # Cache de última verificação de conexão
        self.last_connection_check = None
        
        # Configurar URL base
        if device:
            self.base_url = device.base_url
            self.device_ip = device.ip_address
            self.port = device.port
            self.username = device.username
            self.password = device.password
        else:
            # Usar configurações do settings
            self.device_ip = settings.PRIMARY_DEVICE_IP
            self.port = settings.PRIMARY_DEVICE_PORT
            self.username = settings.PRIMARY_DEVICE_USERNAME
            self.password = settings.PRIMARY_DEVICE_PASSWORD
            use_https = settings.PRIMARY_DEVICE_USE_HTTPS
            protocol = "https" if use_https else "http"
            self.base_url = f"{protocol}://{self.device_ip}:{self.port}"
    
    def is_connected(self) -> bool:
        """Verifica se está conectado ao dispositivo."""
        # Se não tem token, tentar fazer login
        if not self.session_token:
            return self.attempt_smart_reconnection()
        
        # Verificar a cada 60 segundos
        if (self.last_connection_check and 
            (datetime.utcnow() - self.last_connection_check).seconds < 60):
            return True
        
        try:
            # Teste simples de conexão
            response = self.session.get(f"{self.base_url}/", timeout=3)
            self.last_connection_check = datetime.utcnow()
            
            if response.status_code == 200:
                self.reconnection_attempts = 0
                return True
            else:
                self.session_token = None
                return self.attempt_smart_reconnection()
                
        except Exception as e:
            logger.debug(f"Teste de conexão falhou: {e}")
            self.session_token = None
            return self.attempt_smart_reconnection()
    
    def login(self) -> bool:
        """Faz login no dispositivo."""
        try:
            url = f"{self.base_url}/login.fcgi"
            data = {"login": self.username, "password": self.password}
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.connection_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                self.session_token = result.get("session")
                if self.session_token:
                    logger.info("Login bem-sucedido no dispositivo")
                    self.reset_401_counter()
                    return True
            
            logger.error(f"Falha no login: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao fazer login: {e}")
            return False
    
    def get_users(self) -> List[Dict]:
        """Carrega lista de usuários."""
        try:
            url = f"{self.base_url}/load_objects.fcgi?session={self.session_token}"
            data = {"object": "users"}
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("users", [])
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return []
            else:
                logger.error(f"Erro ao carregar usuários: {response.status_code}")
                return []
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao carregar usuários: {e}")
            return []
    
    def get_groups(self) -> List[Dict]:
        """Carrega lista de todos os grupos."""
        try:
            url = f"{self.base_url}/load_objects.fcgi?session={self.session_token}"
            data = {"object": "groups"}
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("groups", [])
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return []
            else:
                logger.error(f"Erro ao carregar grupos: {response.status_code}")
                return []
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao carregar grupos: {e}")
            return []
    
    def get_user_groups(self, user_id: int) -> List[Dict]:
        """Carrega grupos de um usuário específico."""
        try:
            url = f"{self.base_url}/load_objects.fcgi?session={self.session_token}"
            data = {
                "object": "user_groups",
                "where": {"user_groups": {"user_id": user_id}}
            }
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("user_groups", [])
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return []
            else:
                logger.error(f"Erro ao carregar grupos do usuário {user_id}: {response.status_code}")
                return []
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao carregar grupos do usuário {user_id}: {e}")
            return []
    
    def get_access_logs(self, last_processed_id: int = 0) -> List[Dict]:
        """Carrega logs de acesso recentes."""
        try:
            if last_processed_id > 0:
                return self.get_recent_access_logs(limit=500, min_id=last_processed_id)
            else:
                # Buscar apenas os últimos 10 logs se não há ID processado
                return self.get_recent_access_logs(limit=10, min_id=0)
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao carregar logs: {e}")
            return []
    
    def get_recent_access_logs(self, limit: int = 100, min_id: int = 0) -> List[Dict]:
        """Carrega logs de acesso mais recentes usando filtro where."""
        # Limitar para não sobrecarregar a catraca
        limit = min(limit, 1000)  # Máximo 1000 logs
        
        try:
            url = f"{self.base_url}/load_objects.fcgi?session={self.session_token}"
            
            data = {
                "object": "access_logs",
                "where": {
                    "access_logs": {
                        "id": {">": min_id}
                    }
                },
                "order": ["id", "descending"],
                "limit": limit
            }
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logs = result.get("access_logs", [])
                if logs:
                    logger.debug(f"Logs recentes carregados (ID > {min_id}): {len(logs)} logs")
                return logs
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return []
            else:
                logger.error(f"Erro ao carregar logs recentes: {response.status_code}")
                return []
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao carregar logs recentes: {e}")
            return []
    
    def get_access_logs_from_id(self, start_id: int, limit: int = 100) -> List[Dict]:
        """Carrega logs de acesso a partir de um ID específico."""
        # Limitar para não sobrecarregar a catraca
        limit = min(limit, 1000)  # Máximo 1000 logs
        
        try:
            url = f"{self.base_url}/load_objects.fcgi?session={self.session_token}"
            data = {
                "object": "access_logs",
                "start_id": start_id,
                "limit": limit
            }
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logs = result.get("access_logs", [])
                logger.info(f"Logs carregados a partir do ID {start_id}: {len(logs)} logs")
                return logs
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return []
            else:
                logger.error(f"Erro ao carregar logs a partir do ID {start_id}: {response.status_code}")
                return []
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao carregar logs a partir do ID {start_id}: {e}")
            return []
    
    def get_device_config(self) -> Dict:
        """Obtém configuração do dispositivo."""
        try:
            url = f"{self.base_url}/get_configuration.fcgi?session={self.session_token}"
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json={}, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return {}
            else:
                logger.error(f"Erro ao obter configuração: {response.status_code}")
                return {}
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao obter configuração: {e}")
            return {}
    
    def get_device_role(self) -> str:
        """Obtém o role do dispositivo (1=Primário, 2=Secundário)."""
        try:
            config = self.get_device_config()
            sec_box = config.get("sec_box", {})
            role = sec_box.get("catra_role", "0")
            return role
        except Exception as e:
            logger.error(f"Erro ao obter role do dispositivo: {e}")
            return "0"
    
    def handle_401_error(self) -> bool:
        """Gerencia erros 401 e determina se deve fazer restart."""
        current_time = datetime.utcnow()
        
        # Reset contador se passou muito tempo desde o último erro 401
        if (self.last_401_time and 
            (current_time - self.last_401_time).total_seconds() > 300):  # 5 minutos
            self.error_401_count = 0
        
        self.error_401_count += 1
        self.last_401_time = current_time
        
        logger.warning(f"Erro 401 detectado - Contador: {self.error_401_count}/{self.max_401_errors}")
        
        if self.error_401_count >= self.max_401_errors:
            logger.error(f"CRÍTICO: {self.error_401_count} erros 401 consecutivos - SUGERINDO RESTART DO SISTEMA")
            return True  # Sugerir restart
        
        return False  # Não fazer restart ainda
    
    def reset_401_counter(self):
        """Reseta o contador de erros 401."""
        self.error_401_count = 0
        self.last_401_time = None
        self.reconnection_attempts = 0
        logger.info("Contador de erros 401 resetado - Conexão restaurada")
    
    def calculate_reconnection_delay(self) -> float:
        """Calcula o delay para próxima tentativa de reconexão usando backoff exponencial."""
        if self.reconnection_attempts == 0:
            return 0
        
        # Backoff exponencial com jitter
        import random
        delay = min(
            self.base_reconnection_delay * (2 ** (self.reconnection_attempts - 1)),
            self.max_reconnection_delay
        )
        
        # Adicionar jitter para evitar thundering herd
        jitter = random.uniform(0.1, 0.5) * delay
        return delay + jitter
    
    def should_attempt_reconnection(self) -> bool:
        """Determina se deve tentar reconectar baseado no número de tentativas."""
        if self.reconnection_attempts >= self.max_reconnection_attempts:
            logger.error(f"Máximo de tentativas de reconexão atingido ({self.max_reconnection_attempts})")
            return False
        
        return True
    
    def attempt_smart_reconnection(self) -> bool:
        """Tenta reconectar com backoff exponencial e retry inteligente."""
        if not self.should_attempt_reconnection():
            return False
        
        self.reconnection_attempts += 1
        delay = self.calculate_reconnection_delay()
        
        if delay > 0:
            logger.info(f"Tentativa de reconexão {self.reconnection_attempts}/{self.max_reconnection_attempts} em {delay:.1f}s")
            time.sleep(delay)
        
        try:
            # Tentar login
            if self.login():
                logger.info(f"Reconexão bem-sucedida na tentativa {self.reconnection_attempts}")
                self.reconnection_attempts = 0
                return True
            else:
                logger.warning(f"Falha na reconexão - tentativa {self.reconnection_attempts}")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante reconexão - tentativa {self.reconnection_attempts}: {e}")
            return False
    
    def move_user_to_group(self, user_id: int, new_group_id: int, original_group_id: Optional[int] = None) -> bool:
        """Move usuário para um grupo específico."""
        try:
            url = f"{self.base_url}/modify_objects.fcgi?session={self.session_token}"
            
            if original_group_id:
                data = {
                    "object": "user_groups",
                    "values": {
                        "user_id": user_id,
                        "group_id": new_group_id
                    },
                    "where": {
                        "user_groups": {
                            "user_id": user_id,
                            "group_id": original_group_id
                        }
                    }
                }
            else:
                data = {
                    "object": "user_groups",
                    "values": {
                        "user_id": user_id,
                        "group_id": new_group_id
                    }
                }
            
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Usuário {user_id} movido para grupo {new_group_id}")
                return True
            elif response.status_code == 401:
                if self.handle_401_error():
                    raise Exception("RESTART_REQUIRED")
                return False
            else:
                logger.error(f"Erro ao mover usuário {user_id}: {response.status_code}")
                return False
                
        except Exception as e:
            if "RESTART_REQUIRED" in str(e):
                raise e
            logger.error(f"Erro ao mover usuário {user_id}: {e}")
            return False
