"""
Serviços para monitoramento automático de logs.
"""
import threading
import time
import logging
from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee
from apps.employee_sessions.models import EmployeeSession
from apps.core.models import SystemConfiguration
from apps.interjornada.services import InterjornadaService
from apps.employee_sessions.services import session_service

logger = logging.getLogger(__name__)


class LogMonitorService:
    """Serviço para monitoramento automático de logs da catraca."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.running = False
            self.monitor_thread = None
            self.client = None
            self.last_processed_id = 0
            self.consecutive_errors = 0
            self.max_consecutive_errors = 5
            self.monitor_interval = max(getattr(settings, 'LOG_MONITOR_INTERVAL', 1), 1)  # Mínimo 1 segundo
            self.batch_size = min(getattr(settings, 'LOG_MONITOR_BATCH_SIZE', 20), 20)  # Máximo 20 para resposta rápida
            self.device_id = getattr(settings, 'LOG_MONITOR_DEVICE_ID', 1)
            self._no_logs_count = 0
            
            # Serviço de interjornada
            self.interjornada_service = InterjornadaService()
            
            # Registrar handlers de eventos
            session_service.register_event_handler('session_created', self._handle_session_created)
            session_service.register_event_handler('interjornada_started', self._handle_interjornada_started)
            session_service.register_event_handler('interjornada_ended', self._handle_interjornada_ended)
            
            self._initialized = True
    
    def start_monitoring(self):
        """Inicia o monitoramento automático."""
        if self.running:
            logger.warning("Monitoramento já está rodando")
            return
        
        try:
            # Obter último log processado para sessões
            last_processed = AccessLog.objects.filter(session_processed=True).order_by('-device_log_id').first()
            if last_processed:
                self.last_processed_id = last_processed.device_log_id
                logger.info(f"Último log processado para sessões: ID {self.last_processed_id}")
            else:
                self.last_processed_id = 0
                logger.info("Nenhum log anterior processado para sessões, iniciando do zero")
            
            # Iniciar thread de monitoramento
            self.running = True
            self._no_logs_count = 0
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info(f"Monitoramento iniciado (intervalo: {self.monitor_interval}s)")
        except Exception as e:
            logger.error(f"Erro ao iniciar monitoramento: {e}")
            self.running = False
    
    def stop_monitoring(self):
        """Para o monitoramento automático."""
        if not self.running:
            logger.warning("Monitoramento não está rodando")
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self._no_logs_count = 0
        
        logger.info("Monitoramento parado")
    
    def get_status(self):
        """Retorna status do monitoramento."""
        status = {
            'running': self.running,
            'last_processed_id': self.last_processed_id,
            'consecutive_errors': self.consecutive_errors,
            'monitor_interval': self.monitor_interval,
            'batch_size': self.batch_size
        }
        try:
            status['pending_logs'] = AccessLog.objects.filter(session_processed=False).count()
            last_processed_log = AccessLog.objects.filter(session_processed=True).order_by('-session_processed_at').only('session_processed_at').first()
            status['last_session_processed_at'] = last_processed_log.session_processed_at if last_processed_log else None
        except Exception as e:
            logger.debug(f"Não foi possível obter estatísticas complementares: {e}")
        return status
    
    def _monitor_loop(self):
        """Loop principal de monitoramento."""
        logger.info("Loop de monitoramento iniciado")
        
        # Contador para verificar validações de giro
        giro_check_counter = 0
        
        while self.running:
            try:
                # Processar logs pendentes para sessões
                processed_count = self.process_pending_logs()
                
                if processed_count:
                    logger.info(f"{processed_count} logs processados para sessões (último ID {self.last_processed_id})")
                    self.consecutive_errors = 0
                    self._no_logs_count = 0
                else:
                    if not hasattr(self, '_no_logs_count'):
                        self._no_logs_count = 0
                        self._no_logs_count += 1
                    if self._no_logs_count % 10 == 0:
                        logger.debug(f"Nenhum log novo para processar (último ID: {self.last_processed_id})")
                
                # Verificar validações de giro pendentes a cada 10 iterações
                giro_check_counter += 1
                if giro_check_counter >= 10:
                    try:
                        self.interjornada_service.check_pending_giro_validations()
                        giro_check_counter = 0
                    except Exception as e:
                        logger.error(f"Erro ao verificar validações de giro: {e}")
                
                # Aplicar regras de tempo e limpeza de sessões
                self.enforce_session_timeouts()
                
                # Sincronizar grupos com o estado do sistema
                self.sync_groups_with_system_state()
                
                # Aguardar próximo ciclo
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Erro no ciclo de monitoramento: {e}")
                self.consecutive_errors += 1
                
                # Se muitos erros consecutivos, parar
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.error(f"Muitos erros consecutivos ({self.consecutive_errors}). Parando monitoramento.")
                    self.running = False
                    break
                
                time.sleep(self.monitor_interval)
        
        logger.info("Loop de monitoramento finalizado")
    
    def process_pending_logs(self):
        """Busca logs ainda não processados para sessões e executa pipeline determinístico."""
        try:
            pending_logs = AccessLog.objects.filter(
                device_log_id__gt=self.last_processed_id
            ).order_by('device_log_id')[: self.batch_size]
            
            processed = 0
            last_id = self.last_processed_id
            
            for log in pending_logs:
                try:
                    self.process_access_log(log)
                    processed += 1
                    last_id = log.device_log_id
                except Exception as e:
                    logger.error(f"Erro ao processar log {log.device_log_id}: {e}")
                    log.mark_session_error(str(e))
            
            if processed:
                self.last_processed_id = last_id
            
            return processed
        except Exception as e:
            logger.error(f"Erro ao processar logs pendentes: {e}")
            self.consecutive_errors += 1
            return 0
    
    def process_access_log(self, access_log: AccessLog):
        """Processa um log persistido no banco para a lógica de sessões/interjornada."""
        if access_log.session_processed:
            return
        
        user_id = access_log.user_id
        event = access_log.event_description
        event_type = access_log.event_type
        portal_id = access_log.portal_id or 1
        
        # Mapear evento para tipo interno de interjornada
        # Priorizar event_type (código numérico) sobre event_description (texto)
        if event_type is not None:
            interjornada_event_type = self.map_to_interjornada_event(event_type, portal_id)
        else:
            interjornada_event_type = self.map_to_interjornada_event(event, portal_id)
        
        # Mesmo logs sem usuário devem ser marcados como processados para manter sequência
        if user_id == 0 or not interjornada_event_type:
            # Eventos com user_id=0 são eventos de manutenção (cartão inválido, não encontrado, etc.)
            access_log.mark_session_processed({'reason': 'maintenance_event'})
            return
        
        employee = Employee.objects.filter(device_id=user_id, is_active=True).first()
        if not employee:
            access_log.mark_session_processed({'reason': 'employee_not_found'})
            return
        
        # CRÍTICO: Verificar se funcionário está na blacklist ANTES de processar evento
        # Baseado na lógica do arquivo de referência (linhas 1009-1024)
        from apps.employees.models import EmployeeGroup
        blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
        if blacklist_group and employee.group == blacklist_group:
            logger.warning(f"Usuário {employee.name} está na blacklist - Acesso negado (Log ID: {access_log.id})")
            access_log.mark_session_processed({
                'reason': 'blacklist_blocked',
                'message': 'Usuário está na blacklist'
            })
            return
        
        # Usar transação com retry para evitar "database is locked"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    result = self.interjornada_service.process_access_event(
                        employee=employee,
                        event_type=interjornada_event_type,
                        timestamp=access_log.device_timestamp,
                        portal_id=access_log.portal_id
                    )
                    
                    if result.get('success'):
                        session_data = {
                            'result': result,
                            'action': result.get('action'),
                            'state': result.get('state'),
                        }
                        access_log.mark_session_processed(session_data)
                    else:
                        access_log.mark_session_error(result.get('message'), {'result': result})
                break  # Sucesso, sair do loop de retry
            
            except Exception as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, tentativa {attempt + 1}/{max_retries}")
                    time.sleep(0.1 * (attempt + 1))  # Backoff exponencial
                    continue
                else:
                    logger.error(f"Erro ao processar log {access_log.device_log_id}: {e}")
                    access_log.mark_session_error(str(e))
                    break
    
    def process_interjornada_event_direct(self, access_log):
        """Processa evento de interjornada diretamente usando dados do banco."""
        try:
            # Buscar funcionário
            employee = Employee.objects.filter(device_id=access_log.user_id, is_active=True).first()
            if not employee:
                logger.warning(f"Funcionário não encontrado para user_id {access_log.user_id}")
                return
            
            # Mapear evento da catraca para evento de interjornada
            interjornada_event_type = self.map_to_interjornada_event(access_log.event_description, access_log.portal_id)
            if not interjornada_event_type:
                logger.debug(f"Evento {access_log.event_description} (Portal {access_log.portal_id}) não mapeado para interjornada")
                return
            
            # Processar evento de acesso
            result = self.interjornada_service.process_access_event(
                employee=employee,
                event_type=interjornada_event_type,
                timestamp=access_log.device_timestamp
            )
            
            if result['success']:
                logger.info(f"Evento de interjornada processado: {access_log.user_name} - {result['message']}")
            else:
                logger.warning(f"Evento de interjornada negado: {access_log.user_name} - {result['message']}")
                
        except Exception as e:
            logger.error(f"Erro ao processar evento de interjornada para {access_log.user_name}: {e}")
    
    def process_interjornada_event_async(self, access_log):
        """Processa evento de interjornada em background usando dados do banco."""
        try:
            # Usar threading para processar em background
            import threading
            
            def process_background():
                try:
                    # Buscar funcionário
                    employee = Employee.objects.filter(device_id=access_log.user_id, is_active=True).first()
                    if not employee:
                        logger.warning(f"Funcionário não encontrado para user_id {access_log.user_id}")
                        return
                    
                    # Mapear evento da catraca para evento de interjornada
                    interjornada_event_type = self.map_to_interjornada_event(access_log.event_description, access_log.portal_id)
                    if not interjornada_event_type:
                        logger.debug(f"Evento {access_log.event_description} (Portal {access_log.portal_id}) não mapeado para interjornada")
                        return
                    
                    # Processar evento de acesso
                    result = self.interjornada_service.process_access_event(
                        employee=employee,
                        event_type=interjornada_event_type,
                        timestamp=access_log.device_timestamp,
                        portal_id=access_log.portal_id
                    )
                    
                    if result['success']:
                        logger.info(f"Evento de interjornada processado: {access_log.user_name} - {result['message']}")
                    else:
                        logger.warning(f"Evento de interjornada negado: {access_log.user_name} - {result['message']}")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar evento de interjornada para {access_log.user_name}: {e}")
            
            # Executar em thread separada
            thread = threading.Thread(target=process_background, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"Erro ao iniciar processamento assíncrono: {e}")
    
    def process_interjornada_event(self, user_id, user_name, event, portal_id, timestamp):
        """Processa evento de acesso para sistema de interjornada (método legado)."""
        try:
            # Buscar funcionário
            employee = Employee.objects.filter(device_id=user_id, is_active=True).first()
            if not employee:
                logger.warning(f"Funcionário não encontrado para user_id {user_id}")
                return
            
            # Mapear evento da catraca para evento de interjornada
            interjornada_event_type = self.map_to_interjornada_event(event, portal_id)
            if not interjornada_event_type:
                logger.debug(f"Evento {event} (Portal {portal_id}) não mapeado para interjornada")
                return
            
            # Processar evento de acesso
            result = self.interjornada_service.process_access_event(
                employee=employee,
                event_type=interjornada_event_type,
                timestamp=timestamp
            )
            
            if result['success']:
                logger.info(f"Evento de interjornada processado: {user_name} - {result['message']}")
            else:
                logger.warning(f"Evento de interjornada negado: {user_name} - {result['message']}")
                
        except Exception as e:
            logger.error(f"Erro ao processar evento de interjornada para {user_name}: {e}")
    
    def map_to_interjornada_event(self, event, portal_id):
        """Mapeia evento da catraca (texto ou código) para evento de interjornada."""
        if event is None:
            return None
        
        event_str = str(event).strip().lower()
        if not event_str:
            return None
        
        # Eventos que representam entrada/saída pelos códigos numéricos
        if event_str.isdigit():
            if event_str == '7':
                # Evento "7" = Acesso autorizado - considerar o portal
                if portal_id == 2:
                    # Portal 2 = Saída - processar como saída
                    return 2
                else:
                    # Portal 1 = Entrada - aguardar validação de giro
                    return 'pending_validation'
            elif event_str == '6':
                # Evento "6" = Acesso negado - negar acesso
                return 'unauthorized_access'
            elif event_str == '13':
                # Evento "13" = Desistência - cancelar validação pendente
                return 'abandonment'
            elif event_str == '3':
                # Evento "3" = Não identificado - ignorar
                return None
            # Demais códigos não impactam a lógica de sessão
            return None
        
        # Normalizar strings com e sem acento
        normalized = event_str
        replacements = {
            'á': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o',
            'ú': 'u',
            'ç': 'c'
        }
        for accented, plain in replacements.items():
            normalized = normalized.replace(accented, plain)
        
        entrada_aliases = {
            'entrada', 'entrada autorizada', 'entrada reconhecida', 'entrada manual',
            'entrada portal 1', 'entrada portal 2', 'entrada reconhecida portal 1'
        }
        saida_aliases = {
            'saida', 'saida autorizada', 'saida reconhecida', 'saida manual',
            'saida portal 2', 'saida reconhecida portal 2'
        }
        
        # Verificar se é "acesso autorizado" - deve aguardar validação do portal
        if normalized == 'acesso autorizado':
            return 'pending_validation'
        
        # Verificar se é "acesso não autorizado" - NEGAR ACESSO
        if normalized == 'acesso nao autorizado' or normalized == 'acesso não autorizado':
            return 'unauthorized_access'
        
        # Verificar se é "negado" - NEGAR ACESSO
        if normalized == 'negado':
            return 'unauthorized_access'
        
        # APENAS eventos de entrada/saída explícitos são permitidos
        if normalized in entrada_aliases:
            if portal_id == 2:
                return 2
            return 1
        if normalized in saida_aliases:
            return 2
        
        # Verificar padrões de entrada/saída
        if 'entrada' in normalized and 'saida' not in normalized:
            return 1 if portal_id != 2 else 2
        if 'saida' in normalized:
            return 2
        
        # Não mapeado — eventos como desistência, não encontrado etc.
        return None
    
    def check_and_cleanup_expired_sessions(self):
        """Verifica e remove sessões expiradas automaticamente."""
        try:
            from django.utils import timezone
            
            # Buscar sessões bloqueadas que já expiraram
            current_time = timezone.now()
            expired_sessions = EmployeeSession.objects.filter(
                state='blocked',
                return_time__lte=current_time
            ).select_related('employee')
            
            if expired_sessions.exists():
                logger.info(f"Encontradas {expired_sessions.count()} sessões expiradas para limpeza")
                
                for session in expired_sessions:
                    try:
                        # Log da limpeza
                        logger.info(f"Removendo sessão expirada: {session.employee.name} (ID: {session.employee.device_id})")
                        
                        # IMPORTANTE: Remover da blacklist antes de deletar a sessão
                        from apps.employee_sessions.services import session_service
                        blacklist_success = session_service.unblock_user_from_interjornada(session.employee)
                        
                        # Criar log do sistema
                        SystemLog.objects.create(
                            level='info',
                            message=f'Sessão de interjornada finalizada automaticamente - {session.employee.name}',
                            category='interjornada',
                            user_id=session.employee.device_id,
                            user_name=session.employee.name,
                            details={
                                'session_id': session.id,
                                'work_duration': session.work_duration_minutes,
                                'rest_duration': session.rest_duration_minutes,
                                'finalized_at': current_time.isoformat(),
                                'blacklist_removed': blacklist_success
                            }
                        )
                        
                    except Exception as e:
                        logger.error(f"Erro ao remover sessão expirada {session.employee.name}: {e}")
                        
        except Exception as e:
            logger.error(f"Erro ao verificar sessões expiradas: {e}")
    
    def enforce_session_timeouts(self):
        """Aplica regras de tempo para sessões já existentes (expiração, retorno da interjornada)."""
        try:
            now = timezone.now()
            
            # Finalizar sessões bloqueadas cujo retorno já venceu
            expired_sessions = EmployeeSession.objects.filter(
                state='blocked',
                return_time__lte=now
            ).select_related('employee')
            
            for session in expired_sessions:
                try:
                    logger.info(f"Sessão expirada detectada para {session.employee.name} - removendo automaticamente")
                    
                    # IMPORTANTE: Remover da blacklist antes de deletar a sessão
                    from apps.employee_sessions.services import session_service
                    blacklist_success = session_service.unblock_user_from_interjornada(session.employee)
                    
                    SystemLog.objects.create(
                        level='INFO',
                        category='interjornada',
                        message=f'Sessão de interjornada finalizada automaticamente - {session.employee.name}',
                        user_id=session.employee.device_id,
                        user_name=session.employee.name,
                        details={
                            'session_id': session.id,
                            'work_duration': session.work_duration_minutes,
                            'rest_duration': session.rest_duration_minutes,
                            'finalized_at': now.isoformat(),
                            'blacklist_removed': blacklist_success
                        }
                    )
                except Exception as e:
                    logger.error(f"Erro ao remover sessão expirada de {session.employee.name}: {e}")
            
            # Verificar sessões ativas que excederam o tempo de acesso livre
            from apps.core.models import SystemConfiguration
            config = SystemConfiguration.objects.first()
            if config:
                # Calcular o limite de tempo considerando o timezone correto
                time_limit = now - timedelta(minutes=config.liberado_minutes)
                sessions_pending_exit = EmployeeSession.objects.filter(
                    state='active',
                    first_access__lte=time_limit
                ).select_related('employee')
                
                logger.info(f"Verificando sessões ativas. Limite: {time_limit}, Config: {config.liberado_minutes} minutos")
                
                for session in sessions_pending_exit:
                    try:
                        logger.info(f"Sessão de {session.employee.name} excedeu tempo livre. Aguardando saída Portal 2.")
                        # Mudar estado para pending_rest (aguardando saída)
                        session.state = 'pending_rest'
                        session.save(update_fields=['state'])
                        logger.info(f"Usuário {session.employee.name} em estado 'aguardando saída'")
                    except Exception as e:
                        logger.error(f"Erro ao atualizar estado da sessão de {session.employee.name}: {e}")
            
            # Verificar sessões pending_rest que já excederam o tempo de trabalho
            # IMPORTANTE: NÃO bloquear automaticamente - aguardar saída manual pelo Portal 2
            pending_sessions = EmployeeSession.objects.filter(state='pending_rest').select_related('employee')
            for session in pending_sessions:
                try:
                    # Calcular se já excedeu o tempo de trabalho
                    work_time_limit = session.first_access + timedelta(minutes=session.work_duration_minutes)
                    if now > work_time_limit:
                        logger.info(f"Usuário {session.employee.name} em pending_rest excedeu tempo de trabalho - Aguardando saída manual pelo Portal 2")
                        
                        # NÃO bloquear automaticamente - aguardar saída manual
                        # O usuário deve sair pelo Portal 2 para iniciar a interjornada
                        logger.info(f"Usuário {session.employee.name} deve sair pelo Portal 2 para iniciar interjornada")
                        
                except Exception as e:
                    logger.error(f"Erro ao verificar sessão pending_rest de {session.employee.name}: {e}")
            
            # Garantir que sessões ativas tenham last_access atualizado
            active_sessions = EmployeeSession.objects.filter(state='active').select_related('employee')
            for session in active_sessions:
                if session.last_access is None or session.last_access < session.first_access:
                    session.last_access = session.first_access
                    session.save(update_fields=['last_access'])
        except Exception as e:
            logger.error(f"Erro ao aplicar regras de tempo para sessões: {e}")
    
    def _handle_session_created(self, event_data):
        """Handler para evento de sessão criada."""
        try:
            logger.info(f"Sessão criada: {event_data.get('employee_name')} - {event_data.get('state')}")
            # Aqui pode adicionar lógica adicional se necessário
        except Exception as e:
            logger.error(f"Erro no handler de sessão criada: {e}")
    
    def _handle_interjornada_started(self, event_data):
        """Handler para evento de interjornada iniciada."""
        try:
            logger.info(f"Interjornada iniciada: {event_data.get('employee_name')} - Retorna às {event_data.get('return_time')}")
            # Aqui pode adicionar lógica adicional se necessário
        except Exception as e:
            logger.error(f"Erro no handler de interjornada iniciada: {e}")
    
    def _handle_interjornada_ended(self, event_data):
        """Handler para evento de interjornada finalizada."""
        try:
            logger.info(f"Interjornada finalizada: {event_data.get('employee_name')}")
            # Aqui pode adicionar lógica adicional se necessário
        except Exception as e:
            logger.error(f"Erro no handler de interjornada finalizada: {e}")
    
    def sync_groups_with_system_state(self):
        """Sincroniza grupos com o estado do sistema."""
        try:
            from apps.employees.group_service import group_service
            corrected_count = group_service.sync_groups_with_system_state()
            if corrected_count > 0:
                logger.info(f"Sincronização de grupos executada: {corrected_count} correções aplicadas")
        except Exception as e:
            logger.error(f"Erro na sincronização de grupos: {e}")


# Instância global do serviço
log_monitor_service = LogMonitorService()