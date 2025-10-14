"""
Serviços para comunicação com dispositivos.
"""
import requests
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from .models import Device, DeviceLog, DeviceSession
from .device_client import DeviceClient
from apps.core.utils import TimezoneUtils, CacheUtils
import json
import time

logger = logging.getLogger(__name__)


class DeviceConnectionService:
    """Serviço para gerenciar conexões com dispositivos."""
    
    def __init__(self):
        self.device_clients = {}  # Cache de clientes por dispositivo
    
    def connect_to_device(self, device: Device) -> Tuple[bool, str, Optional[str]]:
        """
        Conecta a um dispositivo.
        
        Args:
            device: Instância do dispositivo
            
        Returns:
            Tuple[bool, str, Optional[str]]: (sucesso, mensagem, token)
        """
        try:
            # Verificar se dispositivo está habilitado
            if not device.is_enabled:
                return False, "Dispositivo desabilitado", None
            
            # Obter ou criar cliente para o dispositivo
            client = self.get_device_client(device)
            
            # Tentar conectar
            if client.is_connected():
                # Criar/atualizar sessão
                session = self._create_or_update_session(device, client.session_token)
                
                # Atualizar status do dispositivo
                device.update_connection_status(success=True)
                
                # Log de sucesso
                DeviceLog.objects.create(
                    device=device,
                    log_type='connection',
                    level='INFO',
                    message=f"Conexão estabelecida com sucesso",
                    details={'token': client.session_token[:20] + '...' if client.session_token else None}
                )
                
                return True, "Conexão estabelecida com sucesso", client.session_token
            else:
                # Atualizar status do dispositivo
                device.update_connection_status(success=False, error_message="Falha na conexão")
                
                # Log de erro
                DeviceLog.objects.create(
                    device=device,
                    log_type='connection',
                    level='ERROR',
                    message=f"Falha na conexão",
                    details={'error': 'Falha na conexão'}
                )
                
                return False, "Falha na conexão", None
                
        except Exception as e:
            logger.error(f"Erro ao conectar ao dispositivo {device.name}: {e}")
            
            # Atualizar status do dispositivo
            device.update_connection_status(success=False, error_message=str(e))
            
            # Log de erro
            DeviceLog.objects.create(
                device=device,
                log_type='connection',
                level='CRITICAL',
                message=f"Erro crítico na conexão: {str(e)}",
                details={'error': str(e)}
            )
            
            return False, f"Erro crítico: {str(e)}", None
    
    def get_device_client(self, device: Device) -> DeviceClient:
        """Obtém ou cria um cliente para o dispositivo."""
        device_key = f"{device.id}_{device.ip_address}_{device.port}"
        
        if device_key not in self.device_clients:
            self.device_clients[device_key] = DeviceClient(device)
        
        return self.device_clients[device_key]
    
    def _authenticate_device(self, device: Device) -> Tuple[bool, str, Optional[str]]:
        """
        Autentica no dispositivo.
        
        Args:
            device: Instância do dispositivo
            
        Returns:
            Tuple[bool, str, Optional[str]]: (sucesso, mensagem, token)
        """
        try:
            # URL de login
            login_url = f"{device.base_url}/login.fcgi"
            
            # Dados de login
            login_data = {
                "login": device.username,
                "password": device.password
            }
            
            # Fazer requisição de login
            response = self.session.post(
                login_url,
                json=login_data,
                timeout=device.request_timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Verificar se há token de sessão (indica sucesso)
                    if 'session' in data:
                        token = data.get('session')
                        return True, "Autenticação bem-sucedida", token
                    elif data.get('success'):
                        token = data.get('session')
                        return True, "Autenticação bem-sucedida", token
                    else:
                        return False, f"Falha na autenticação: {data.get('message', 'Erro desconhecido')}", None
                except json.JSONDecodeError:
                    return False, "Resposta inválida do dispositivo", None
            else:
                return False, f"Erro HTTP {response.status_code}: {response.text}", None
                
        except requests.exceptions.Timeout:
            return False, "Timeout na autenticação", None
        except requests.exceptions.ConnectionError:
            return False, "Erro de conexão", None
        except Exception as e:
            return False, f"Erro na autenticação: {str(e)}", None
    
    def _create_or_update_session(self, device: Device, token: Optional[str]) -> DeviceSession:
        """
        Cria ou atualiza sessão do dispositivo.
        
        Args:
            device: Instância do dispositivo
            token: Token de sessão
            
        Returns:
            DeviceSession: Sessão criada/atualizada
        """
        # Buscar sessão ativa existente
        existing_session = DeviceSession.objects.filter(
            device=device,
            is_active=True
        ).first()
        
        if existing_session:
            # Atualizar sessão existente
            existing_session.session_token = token
            existing_session.last_activity = TimezoneUtils.get_utc_now()
            existing_session.save(update_fields=['session_token', 'last_activity'])
            return existing_session
        else:
            # Criar nova sessão
            return DeviceSession.objects.create(
                device=device,
                session_token=token,
                is_active=True,
                started_at=TimezoneUtils.get_utc_now(),
                last_activity=TimezoneUtils.get_utc_now()
            )
    
    def disconnect_device(self, device: Device) -> bool:
        """
        Desconecta de um dispositivo.
        
        Args:
            device: Instância do dispositivo
            
        Returns:
            bool: Sucesso da desconexão
        """
        try:
            # Finalizar sessão ativa
            active_session = DeviceSession.objects.filter(
                device=device,
                is_active=True
            ).first()
            
            if active_session:
                active_session.end_session()
            
            # Atualizar status do dispositivo
            device.status = 'inactive'
            device.save(update_fields=['status'])
            
            # Log de desconexão
            DeviceLog.objects.create(
                device=device,
                log_type='connection',
                level='INFO',
                message="Dispositivo desconectado",
                details={}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao desconectar dispositivo {device.name}: {e}")
            return False


class DeviceDataService:
    """Serviço para buscar dados de dispositivos."""
    
    def __init__(self):
        self.connection_service = DeviceConnectionService()
    
    def get_device_logs(self, device: Device, limit: int = 100, last_processed_id: int = 0) -> Tuple[bool, str, List[Dict]]:
        """
        Busca logs de acesso do dispositivo.
        
        Args:
            device: Instância do dispositivo
            limit: Limite de logs a buscar
            last_processed_id: ID do último log processado
            
        Returns:
            Tuple[bool, str, List[Dict]]: (sucesso, mensagem, logs)
        """
        try:
            # Obter cliente do dispositivo
            client = self.connection_service.get_device_client(device)
            
            # Verificar se está conectado
            if not client.is_connected():
                success, message, token = self.connection_service.connect_to_device(device)
                if not success:
                    return False, message, []
            
            # Buscar logs usando o cliente
            logs = client.get_access_logs(last_processed_id)
            
            if logs is not None:
                # Log de sucesso
                DeviceLog.objects.create(
                    device=device,
                    log_type='data_fetch',
                    level='INFO',
                    message=f"Logs obtidos com sucesso: {len(logs)} registros",
                    details={'count': len(logs), 'last_processed_id': last_processed_id}
                )
                
                return True, "Logs obtidos com sucesso", logs
            else:
                return False, "Erro ao buscar logs", []
                
        except Exception as e:
            logger.error(f"Erro ao buscar logs do dispositivo {device.name}: {e}")
            
            # Log de erro
            DeviceLog.objects.create(
                device=device,
                log_type='data_fetch',
                level='ERROR',
                message=f"Erro ao buscar logs: {str(e)}",
                details={'error': str(e)}
            )
            
            return False, f"Erro ao buscar logs: {str(e)}", []
    
    def get_device_status(self, device: Device) -> Tuple[bool, str, Dict]:
        """
        Busca status do dispositivo.
        
        Args:
            device: Instância do dispositivo
            
        Returns:
            Tuple[bool, str, Dict]: (sucesso, mensagem, status)
        """
        try:
            # URL para status
            status_url = f"{device.base_url}/getstatus.fcgi"
            
            # Buscar sessão ativa
            active_session = DeviceSession.objects.filter(
                device=device,
                is_active=True
            ).first()
            
            if not active_session:
                return False, "Nenhuma sessão ativa encontrada", {}
            
            # Parâmetros da requisição
            params = {
                'session': active_session.session_token
            }
            
            # Fazer requisição
            response = requests.get(
                status_url,
                params=params,
                timeout=device.request_timeout,
                verify=settings.SSL_VERIFY
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        status_data = data.get('data', {})
                        
                        # Atualizar atividade da sessão
                        active_session.update_activity(success=True)
                        
                        return True, "Status obtido com sucesso", status_data
                    else:
                        active_session.update_activity(success=False)
                        return False, f"Erro do dispositivo: {data.get('message', 'Erro desconhecido')}", {}
                        
                except json.JSONDecodeError:
                    active_session.update_activity(success=False)
                    return False, "Resposta inválida do dispositivo", {}
            else:
                active_session.update_activity(success=False)
                return False, f"Erro HTTP {response.status_code}: {response.text}", {}
                
        except Exception as e:
            logger.error(f"Erro ao buscar status do dispositivo {device.name}: {e}")
            return False, f"Erro ao buscar status: {str(e)}", {}
    
    def get_device_users(self, device: Device) -> Tuple[bool, str, List[Dict]]:
        """
        Busca usuários do dispositivo.
        
        Args:
            device: Instância do dispositivo
            
        Returns:
            Tuple[bool, str, List[Dict]]: (sucesso, mensagem, usuários)
        """
        try:
            # URL para usuários
            users_url = f"{device.base_url}/getuser.fcgi"
            
            # Buscar sessão ativa
            active_session = DeviceSession.objects.filter(
                device=device,
                is_active=True
            ).first()
            
            if not active_session:
                return False, "Nenhuma sessão ativa encontrada", []
            
            # Parâmetros da requisição
            params = {
                'session': active_session.session_token
            }
            
            # Fazer requisição
            response = requests.get(
                users_url,
                params=params,
                timeout=device.request_timeout,
                verify=settings.SSL_VERIFY
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        users = data.get('data', [])
                        
                        # Atualizar atividade da sessão
                        active_session.update_activity(success=True)
                        
                        return True, "Usuários obtidos com sucesso", users
                    else:
                        active_session.update_activity(success=False)
                        return False, f"Erro do dispositivo: {data.get('message', 'Erro desconhecido')}", []
                        
                except json.JSONDecodeError:
                    active_session.update_activity(success=False)
                    return False, "Resposta inválida do dispositivo", []
            else:
                active_session.update_activity(success=False)
                return False, f"Erro HTTP {response.status_code}: {response.text}", []
                
        except Exception as e:
            logger.error(f"Erro ao buscar usuários do dispositivo {device.name}: {e}")
            return False, f"Erro ao buscar usuários: {str(e)}", []
    
    def get_device_groups(self, device: Device) -> Tuple[bool, str, List[Dict]]:
        """
        Busca grupos do dispositivo.
        
        Args:
            device: Instância do dispositivo
            
        Returns:
            Tuple[bool, str, List[Dict]]: (sucesso, mensagem, grupos)
        """
        try:
            # URL para grupos
            groups_url = f"{device.base_url}/getgroup.fcgi"
            
            # Buscar sessão ativa
            active_session = DeviceSession.objects.filter(
                device=device,
                is_active=True
            ).first()
            
            if not active_session:
                return False, "Nenhuma sessão ativa encontrada", []
            
            # Parâmetros da requisição
            params = {
                'session': active_session.session_token
            }
            
            # Fazer requisição
            response = requests.get(
                groups_url,
                params=params,
                timeout=device.request_timeout,
                verify=settings.SSL_VERIFY
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        groups = data.get('data', [])
                        
                        # Atualizar atividade da sessão
                        active_session.update_activity(success=True)
                        
                        return True, "Grupos obtidos com sucesso", groups
                    else:
                        active_session.update_activity(success=False)
                        return False, f"Erro do dispositivo: {data.get('message', 'Erro desconhecido')}", []
                        
                except json.JSONDecodeError:
                    active_session.update_activity(success=False)
                    return False, "Resposta inválida do dispositivo", []
            else:
                active_session.update_activity(success=False)
                return False, f"Erro HTTP {response.status_code}: {response.text}", []
                
        except Exception as e:
            logger.error(f"Erro ao buscar grupos do dispositivo {device.name}: {e}")
            return False, f"Erro ao buscar grupos: {str(e)}", []


class DeviceMonitoringService:
    """Serviço para monitoramento de dispositivos."""
    
    def __init__(self):
        self.data_service = DeviceDataService()
        self.is_monitoring = False
    
    def start_monitoring(self):
        """Inicia monitoramento de dispositivos."""
        self.is_monitoring = True
        logger.info("Monitoramento de dispositivos iniciado")
    
    def stop_monitoring(self):
        """Para monitoramento de dispositivos."""
        self.is_monitoring = False
        logger.info("Monitoramento de dispositivos parado")
    
    def monitor_devices(self):
        """
        Monitora todos os dispositivos ativos.
        
        Returns:
            Dict: Estatísticas do monitoramento
        """
        if not self.is_monitoring:
            return {'status': 'stopped', 'message': 'Monitoramento não está ativo'}
        
        try:
            # Buscar dispositivos ativos
            active_devices = Device.objects.filter(
                is_enabled=True,
                device_type='primary'  # Por enquanto, apenas dispositivos primários
            )
            
            stats = {
                'status': 'running',
                'devices_checked': 0,
                'devices_connected': 0,
                'devices_error': 0,
                'total_logs_fetched': 0,
                'errors': []
            }
            
            for device in active_devices:
                stats['devices_checked'] += 1
                
                try:
                    # Buscar logs do dispositivo
                    success, message, logs = self.data_service.get_device_logs(device)
                    
                    if success:
                        stats['devices_connected'] += 1
                        stats['total_logs_fetched'] += len(logs)
                        
                        # Processar logs (será implementado no app de logs)
                        if logs:
                            self._process_device_logs(device, logs)
                    else:
                        stats['devices_error'] += 1
                        stats['errors'].append(f"{device.name}: {message}")
                        
                except Exception as e:
                    stats['devices_error'] += 1
                    stats['errors'].append(f"{device.name}: {str(e)}")
                    logger.error(f"Erro ao monitorar dispositivo {device.name}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de dispositivos: {e}")
            return {
                'status': 'error',
                'message': f'Erro no monitoramento: {str(e)}',
                'devices_checked': 0,
                'devices_connected': 0,
                'devices_error': 0,
                'total_logs_fetched': 0,
                'errors': [str(e)]
            }
    
    def _process_device_logs(self, device: Device, logs: List[Dict]):
        """
        Processa logs do dispositivo.
        
        Args:
            device: Instância do dispositivo
            logs: Lista de logs
        """
        try:
            # Aqui será implementada a lógica de processamento de logs
            # que será integrada com o app de logs
            logger.info(f"Processando {len(logs)} logs do dispositivo {device.name}")
            
            # Por enquanto, apenas logar
            for log in logs:
                logger.debug(f"Log do dispositivo {device.name}: {log}")
                
        except Exception as e:
            logger.error(f"Erro ao processar logs do dispositivo {device.name}: {e}")


# Instâncias globais dos serviços
device_connection_service = DeviceConnectionService()
device_data_service = DeviceDataService()
device_monitoring_service = DeviceMonitoringService()
