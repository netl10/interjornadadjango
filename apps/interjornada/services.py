"""
Serviços para lógica de interjornada.
"""
import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.cache import cache
from .models import InterjornadaRule, InterjornadaCycle, InterjornadaViolation, InterjornadaStatistics
from apps.employees.models import Employee
from apps.employee_sessions.models import EmployeeSession
from apps.employee_sessions.services import session_service
from apps.logs.models import SystemLog
from apps.core.models import SystemConfiguration
from apps.core.utils import TimezoneUtils, CacheUtils
from datetime import datetime, timedelta, date

logger = logging.getLogger(__name__)


class InterjornadaService:
    """Serviço principal para lógica de interjornada."""
    
    def __init__(self):
        self.active_cycles = {}
        self.violation_thresholds = {
            'early_access': 5,  # minutos
            'late_access': 10,  # minutos
            'exceeded_work_time': 5,  # minutos
            'insufficient_rest': 5,  # minutos
        }
    
    def get_system_config(self) -> SystemConfiguration:
        """Obtém configuração do sistema."""
        config, created = SystemConfiguration.objects.get_or_create(
            id=1,
            defaults={
                'liberado_minutes': 480,  # 8 horas
                'bloqueado_minutes': 672,    # 11.2 horas
                'device_ip': '192.168.1.251',
                'giro_validation_timeout': 30,
                'timezone_offset': -3,
            }
        )
        return config
    
    def get_user_session(self, employee: Employee) -> Optional[EmployeeSession]:
        """Busca sessão ativa do funcionário."""
        return EmployeeSession.objects.filter(
            employee=employee,
            state__in=['active', 'blocked', 'pending_rest']
        ).first()
    
    def create_user_session(self, employee: Employee, access_time: datetime = None) -> EmployeeSession:
        """Cria nova sessão de funcionário."""
        if access_time is None:
            access_time = TimezoneUtils.get_utc_now()
        
        # Verificar se já existe uma sessão
        existing_session = self.get_user_session(employee)
        if existing_session:
            logger.info(f"Funcionário {employee.name} já tem sessão ativa - Reutilizando sessão existente")
            return existing_session
        
        # Obter configurações do sistema
        config = self.get_system_config()
        
        # Criar nova sessão
        session = EmployeeSession.objects.create(
            employee=employee,
            state='active',
            first_access=access_time,
            work_duration_minutes=config.liberado_minutes,
            rest_duration_minutes=config.bloqueado_minutes
        )
        
        logger.info(f"Sessão criada para {employee.name} - ID: {session.id}")
        return session
    
    def block_user_for_interjornada(self, employee: Employee, block_start_time: datetime = None) -> bool:
        """Bloqueia funcionário para interjornada."""
        try:
            session = session_service.get_user_session(employee)
            if not session:
                logger.warning(f"Funcionário {employee.name} não tem sessão ativa")
                return False
            
            # Verificar se já atingiu tempo mínimo de trabalho
            config = self.get_system_config()
            current_time = TimezoneUtils.get_utc_now()
            session_age = current_time - session.first_access
            work_duration = timedelta(minutes=config.liberado_minutes)
            
            if session_age < work_duration:
                remaining_time = work_duration - session_age
                remaining_minutes = remaining_time.total_seconds() / 60
                logger.warning(f"Funcionário {employee.name} tentou sair antes do tempo mínimo - Ainda faltam {remaining_minutes:.1f} minutos")
                return False
            
            # Usar timestamp fornecido ou atual
            if block_start_time is None:
                block_start_time = current_time
            
            # Calcular horário de retorno
            rest_duration = timedelta(minutes=config.bloqueado_minutes)
            return_time = block_start_time + rest_duration
            
            # Atualizar sessão
            session.state = 'blocked'
            session.block_start = block_start_time
            session.return_time = return_time
            session.save()
            
            # TODO: Implementar movimentação para blacklist no IDFace
            # Por enquanto, apenas bloquear no sistema local
            
            logger.info(f"Funcionário {employee.name} colocado em interjornada - Retorna às {return_time.strftime('%H:%M:%S')}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao bloquear funcionário {employee.name}: {e}")
            return False
    
    def unblock_user_from_interjornada(self, employee: Employee) -> bool:
        """Libera funcionário da interjornada."""
        try:
            session = session_service.get_user_session(employee)
            if not session or session.state != 'blocked':
                logger.debug(f"Funcionário {employee.name} não está bloqueado")
                return False
            
            # Verificar se já pode sair da interjornada
            current_time = TimezoneUtils.get_utc_now()
            if current_time < session.return_time:
                time_remaining = session.return_time - current_time
                remaining_minutes = time_remaining.total_seconds() / 60
                logger.warning(f"Funcionário {employee.name} ainda não pode sair da interjornada - {remaining_minutes:.1f} minutos restantes")
                return False
            
            # Remover sessão (finalizar interjornada)
            session.delete()
            
            # TODO: Implementar remoção do blacklist no IDFace
            # Por enquanto, apenas liberar no sistema local
            
            logger.info(f"Funcionário {employee.name} liberado da interjornada")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao liberar funcionário {employee.name}: {e}")
            return False
    
    def get_applicable_rule(self, employee: Employee) -> Optional[InterjornadaRule]:
        """
        Obtém regra aplicável para um funcionário.
        
        Args:
            employee: Funcionário
            
        Returns:
            InterjornadaRule ou None
        """
        try:
            # Buscar regra específica para o funcionário
            rules = InterjornadaRule.objects.filter(
                is_active=True
            ).order_by('-created_at')
            
            for rule in rules:
                # Verificar se aplica a todos
                if rule.apply_to_all:
                    return rule
                
                # Verificar grupos do funcionário
                if any(group in rule.employee_groups for group in employee.groups):
                    return rule
                
                # Verificar se funcionário não está em grupo isento
                if not any(group in rule.exempt_employee_groups for group in employee.groups):
                    return rule
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter regra aplicável para {employee.name}: {e}")
            return None
    
    def create_cycle(self, employee: Employee, rule: InterjornadaRule = None) -> Optional[InterjornadaCycle]:
        """
        Cria novo ciclo de interjornada para funcionário.
        
        Args:
            employee: Funcionário
            rule: Regra (opcional, será buscada se não informada)
            
        Returns:
            InterjornadaCycle ou None
        """
        try:
            with transaction.atomic():
                # Verificar se já existe ciclo ativo
                active_cycle = InterjornadaCycle.objects.filter(
                    employee=employee,
                    current_state__in=['work', 'rest']
                ).first()
                
                if active_cycle:
                    logger.warning(f"Funcionário {employee.name} já possui ciclo ativo")
                    return active_cycle
                
                # Obter regra se não informada
                if not rule:
                    rule = self.get_applicable_rule(employee)
                    if not rule:
                        logger.warning(f"Nenhuma regra aplicável para {employee.name}")
                        return None
                
                # Criar novo ciclo
                cycle = InterjornadaCycle.objects.create(
                    employee=employee,
                    rule=rule,
                    cycle_start=TimezoneUtils.get_utc_now()
                )
                
                # Iniciar período de trabalho
                cycle.start_work_period()
                
                # Log de criação
                SystemLog.log_info(
                    message=f"Novo ciclo de interjornada criado para {employee.name}",
                    category='interjornada',
                    user_id=employee.device_id,
                    user_name=employee.name,
                    details={
                        'cycle_id': cycle.id,
                        'rule_id': rule.id,
                        'work_duration': rule.work_duration_minutes,
                        'rest_duration': rule.rest_duration_minutes
                    }
                )
                
                return cycle
                
        except Exception as e:
            logger.error(f"Erro ao criar ciclo para {employee.name}: {e}")
            return None
    
    def process_access_event(self, employee: Employee, event_type, timestamp: datetime, portal_id: int = 1) -> Dict:
        """
        Processa evento de acesso do funcionário.
        
        Args:
            employee: Funcionário
            event_type: Tipo do evento ('pending_validation', 'abandonment', 1=entrada, 2=saída)
            timestamp: Timestamp do evento
            portal_id: ID do portal (1=entrada, 2=saída)
            
        Returns:
            Dict: Resultado do processamento
        """
        try:
            # CRÍTICO: Verificar se funcionário está bloqueado ANTES de qualquer processamento
            # Baseado na lógica do arquivo de referência (linhas 1009-1024)
            session = session_service.get_user_session(employee)
            if session and session.state == 'blocked':
                # Verificar se já pode sair da interjornada
                current_time = TimezoneUtils.get_utc_now()
                if current_time >= session.return_time:
                    # Liberar da interjornada usando o session_service que tem a implementação correta
                    session_service.unblock_user_from_interjornada(employee)
                    logger.info(f"Usuário {employee.name} liberado da interjornada - Acesso permitido")
                    return {
                        'success': True,
                        'message': 'Funcionário liberado da interjornada',
                        'action': 'allow'
                    }
                else:
                    # Ainda bloqueado - verificar se é saída pelo Portal 2
                    if event_type == 2 and portal_id == 2:
                        # Permitir saída pelo Portal 2 mesmo em interjornada
                        logger.info(f"Usuário {employee.name} em interjornada - Permitindo saída pelo Portal 2")
                        return {
                            'success': True,
                            'message': 'Saída permitida - Usuário em interjornada',
                            'action': 'allow'
                        }
                    else:
                        # Ainda bloqueado - NEGAR ACESSO (exceto saída Portal 2)
                        time_remaining = session.return_time - current_time
                        remaining_minutes = time_remaining.total_seconds() / 60
                        return_time_str = session.return_time.strftime("%H:%M:%S")
                        
                        logger.warning(f"Acesso negado para {employee.name} - Em interjornada até {return_time_str} ({remaining_minutes:.1f}min restantes)")
                        return {
                            'success': False,
                            'message': f'Acesso negado - {remaining_minutes:.1f} minutos restantes de interjornada',
                            'action': 'deny'
                        }
                
            # NOTA: Verificação de blacklist é feita no LogMonitorService
            # para evitar processamento desnecessário
                
            # Processar baseado no tipo de evento
            if event_type == 'pending_validation':
                # Evento 7 - Acesso autorizado, aguardar validação de giro
                return self._process_pending_validation(employee, timestamp, portal_id)
            elif event_type == 'abandonment':
                # Evento 13 - Desistência, cancelar validação pendente
                return self._process_abandonment(employee, timestamp)
            elif event_type == 'unauthorized_access':
                # Acesso não autorizado - NEGAR
                return self._process_unauthorized_access(employee, timestamp)
            elif event_type == 1:  # Entrada (legado)
                return self._process_entry_event_new(employee, timestamp)
            elif event_type == 2:  # Saída (legado)
                return self._process_exit_event_new(employee, timestamp)
            else:
                return {
                    'success': True,
                    'message': 'Evento processado',
                    'action': 'allow'
                }
                    
        except Exception as e:
            logger.error(f"Erro ao processar evento de acesso: {e}")
            return {
                'success': False,
                'message': f'Erro interno: {str(e)}',
                'action': 'deny'
            }
    
    def _process_pending_validation(self, employee: Employee, timestamp: datetime, portal_id: int) -> Dict:
        """
        Processa evento 7 - Acesso autorizado, aguardar validação de giro.
        Baseado na lógica do arquivo de referência.
        """
        try:
            logger.info(f"Evento 7 - Acesso autorizado para {employee.name} no Portal {portal_id} - Processando entrada diretamente")
            
            # Verificar se já existe validação pendente para este usuário
            cache_key = f"pending_validation_{employee.device_id}"
            existing_validation = cache.get(cache_key)
            
            if existing_validation:
                logger.info(f"Usuário {employee.name} já tem validação pendente - Processando entrada")
                # Remover validação pendente e processar entrada
                cache.delete(cache_key)
                return self._process_entry_event_new(employee, timestamp, skip_validation_check=True)
            
            # Criar validação pendente
            validation_data = {
                'employee_id': employee.device_id,
                'employee_name': employee.name,
                'portal_id': portal_id,
                'timestamp': timestamp.isoformat(),
                'created_at': TimezoneUtils.get_utc_now().isoformat()
            }
            
            # Armazenar validação pendente no cache por 5 minutos
            cache.set(cache_key, validation_data, 300)
            
            logger.info(f"Validação pendente criada para {employee.name} - Portal {portal_id}")
            
            # Processar entrada diretamente (simular giro)
            result = self._process_entry_event_new(employee, timestamp, skip_validation_check=True)
            
            if result.get('success'):
                # Remover validação pendente se entrada foi bem-sucedida
                cache.delete(cache_key)
                logger.info(f"Sessão criada para {employee.name} após evento 7")
                return result
            else:
                return {
                    'success': True,
                    'message': f'Acesso autorizado - Aguardando validação de giro (Portal {portal_id})',
                    'action': 'pending_validation',
                    'state': 'pending_validation'
                }
            
        except Exception as e:
            logger.error(f"Erro ao processar validação pendente para {employee.name}: {e}")
            return {
                'success': False,
                'message': str(e),
                'action': 'error'
            }
    
    def _process_abandonment(self, employee: Employee, timestamp: datetime) -> Dict:
        """
        Processa evento 13 - Desistência, cancelar validação pendente.
        Baseado na lógica do arquivo de referência.
        """
        try:
            logger.info(f"Evento 13 - Desistência de acesso para {employee.name}")
            
            # Cancelar validação pendente se existir
            cache_key = f"pending_validation_{employee.device_id}"
            existing_validation = cache.get(cache_key)
            
            if existing_validation:
                cache.delete(cache_key)
                logger.info(f"Validação cancelada para {employee.name} - Usuário desistiu")
                return {
                    'success': True,
                    'message': 'Validação cancelada - Usuário desistiu',
                    'action': 'abandonment'
                }
            else:
                logger.info(f"Desistência para {employee.name} - Nenhuma validação pendente")
                return {
                    'success': True,
                    'message': 'Desistência registrada - Nenhuma validação pendente',
                    'action': 'abandonment'
                }
                
        except Exception as e:
            logger.error(f"Erro ao processar desistência para {employee.name}: {e}")
            return {
                'success': False,
                'message': str(e),
                'action': 'error'
            }
    
    def _process_unauthorized_access(self, employee: Employee, timestamp: datetime) -> Dict:
        """
        Processa acesso não autorizado - NEGAR ACESSO.
        """
        try:
            logger.warning(f"Acesso não autorizado para {employee.name} - Negando acesso")
            
            return {
                'success': False,
                'message': 'Acesso não autorizado',
                'action': 'deny'
            }
                
        except Exception as e:
            logger.error(f"Erro ao processar acesso não autorizado para {employee.name}: {e}")
            return {
                'success': False,
                'message': str(e),
                'action': 'error'
            }
    
    def check_pending_giro_validations(self):
        """
        Verifica validações de giro pendentes.
        Baseado na lógica do arquivo de referência (linhas 758-864).
        """
        try:
            logger.debug("Verificando validações de giro pendentes...")
            
            # Buscar eventos de acesso (giros) do dispositivo
            from apps.devices.device_client import DeviceClient
            device_client = DeviceClient()
            
            try:
                access_events = device_client.get_access_events()
                
                if access_events:
                    logger.debug(f"Encontrados {len(access_events)} eventos de acesso")
                    
                    # Processar cada evento de giro
                    for event in access_events:
                        if event.get('event') == 'catra' and event.get('type') in ['TURN_LEFT', 'TURN_RIGHT']:
                            self.process_giro_event(event)
                else:
                    logger.debug("Nenhum evento de acesso encontrado")
                    
            except Exception as e:
                logger.error(f"Erro ao buscar eventos de acesso: {e}")
            
        except Exception as e:
            logger.error(f"Erro ao verificar validações pendentes: {e}")
    
    def process_giro_event(self, event_data: dict) -> bool:
        """
        Processa eventos de giro da catraca.
        Baseado na lógica do arquivo de referência (linhas 2806-2905).
        """
        try:
            event_type = event_data.get('type', '')
            event_timestamp = event_data.get('timestamp', 0)
            device_id = event_data.get('device_id', 0)
            
            if event_type in ['TURN_RIGHT', 'TURN_LEFT']:
                logger.info(f"Evento de giro detectado: {event_type}")
                
                # Buscar validação pendente para este dispositivo
                # Como não temos acesso direto às chaves do cache, vamos buscar por todos os funcionários
                from apps.employees.models import Employee
                
                employees = Employee.objects.filter(is_active=True)
                for employee in employees:
                    cache_key = f"pending_validation_{employee.device_id}"
                    validation = cache.get(cache_key)
                    
                    if validation:
                        logger.info(f"Validação pendente encontrada para {employee.name} - Processando giro")
                        
                        # Remover validação pendente do cache
                        cache.delete(cache_key)
                        
                        # Processar entrada (criar sessão) - pular verificação de validação pois já foi confirmada
                        result = self._process_entry_event_new(employee, TimezoneUtils.get_utc_now(), skip_validation_check=True)
                        
                        if result.get('success'):
                            logger.info(f"Sessão criada para {employee.name} após giro {event_type}")
                            return True
                        else:
                            logger.warning(f"Falha ao criar sessão para {employee.name}: {result.get('message')}")
                            return False
                
                logger.info(f"Giro {event_type} processado em {event_timestamp} - Nenhuma validação pendente encontrada")
                return True
            else:
                logger.debug(f"Evento não é giro: {event_type}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao processar evento de giro: {e}")
            return False
    
    def _process_entry_event_new(self, employee: Employee, timestamp: datetime, skip_validation_check: bool = False) -> Dict:
        """
        Processa evento de entrada (nova lógica baseada em sessões).
        REGRA RIGOROSA: APENAS permitir entrada se houver validação pendente (evento 7 + giro).
        """
        try:
            # Verificar se há validação pendente para este usuário (exceto quando chamado após giro)
            if not skip_validation_check:
                cache_key = f"pending_validation_{employee.device_id}"
                pending_validation = cache.get(cache_key)
                
                if pending_validation:
                    # Remover validação pendente do cache
                    cache.delete(cache_key)
                    logger.info(f"Validação confirmada para {employee.name} - Processando entrada")
                else:
                    # SEM validação pendente - NEGAR ACESSO (regra rigorosa)
                    logger.warning(f"Evento de entrada SEM validação pendente para {employee.name} - ACESSO NEGADO")
                    return {
                        'success': False,
                        'message': 'Entrada ignorada - Sem validação pendente (evento 7 + giro obrigatório)',
                        'action': 'deny'
                    }
            else:
                logger.info(f"Validação confirmada para {employee.name} - Processando entrada (após giro)")
            
            # Verificar se já tem sessão ativa
            session = session_service.get_user_session(employee)
            if session and session.state == 'active':
                # Já tem sessão ativa - permitir acesso
                return {
                    'success': True,
                    'message': 'Funcionário já tem sessão ativa',
                    'action': 'allow',
                    'state': session.state
                }
            
            # Criar nova sessão usando o SessionService
            session = session_service.create_user_session(employee, timestamp)
            
            return {
                'success': True,
                'message': 'Nova sessão criada - Acesso liberado',
                'action': 'allow',
                'state': session.state
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar entrada: {e}")
            return {
                'success': False,
                'message': f'Erro ao processar entrada: {str(e)}',
                'action': 'deny'
            }
    
    def _process_exit_event_new(self, employee: Employee, timestamp: datetime) -> Dict:
        """Processa evento de saída (nova lógica baseada em sessões)."""
        try:
            # Verificar se tem sessão ativa ou aguardando saída
            session = session_service.get_user_session(employee)
            if not session or session.state not in ['active', 'pending_rest']:
                return {
                    'success': False,
                    'message': 'Funcionário não tem sessão ativa ou aguardando saída',
                    'action': 'deny'
                }
            
            # Verificar se pode entrar em interjornada
            config = self.get_system_config()
            current_time = TimezoneUtils.get_utc_now()
            session_age = current_time - session.first_access
            work_duration = timedelta(minutes=config.liberado_minutes)
            
            if session_age < work_duration:
                remaining_time = work_duration - session_age
                remaining_minutes = remaining_time.total_seconds() / 60
                return {
                    'success': False,
                    'message': f'Ainda faltam {remaining_minutes:.1f} minutos de trabalho',
                    'action': 'deny'
                }
            
            # Bloquear para interjornada
            success = self.block_user_for_interjornada(employee, timestamp)
            if success:
                return {
                    'success': True,
                    'message': 'Funcionário colocado em interjornada',
                    'action': 'allow'
                }
            else:
                return {
                    'success': False,
                    'message': 'Erro ao colocar em interjornada',
                    'action': 'deny'
                }
                
        except Exception as e:
            logger.error(f"Erro ao processar saída: {e}")
            return {
                'success': False,
                'message': f'Erro ao processar saída: {str(e)}',
                'action': 'deny'
            }
    
    def _process_entry_event(self, cycle: InterjornadaCycle, timestamp: datetime) -> Dict:
        """
        Processa evento de entrada.
        
        Args:
            cycle: Ciclo de interjornada
            timestamp: Timestamp do evento
            
        Returns:
            Dict: Resultado do processamento
        """
        try:
            if cycle.is_work_period:
                # Já está no período de trabalho
                return {
                    'success': True,
                    'message': 'Funcionário já está no período de trabalho',
                    'action': 'allow',
                    'cycle_state': 'work'
                }
            
            elif cycle.is_rest_period:
                # Verificar se pode sair da interjornada
                if cycle.can_start_work:
                    # Iniciar novo período de trabalho
                    cycle.start_work_period()
                    
                    SystemLog.log_info(
                        message=f"Funcionário {cycle.employee.name} iniciou novo período de trabalho",
                        category='interjornada',
                        user_id=cycle.employee.device_id,
                        user_name=cycle.employee.name,
                        details={'cycle_id': cycle.id}
                    )
                    
                    return {
                        'success': True,
                        'message': 'Período de trabalho iniciado',
                        'action': 'allow',
                        'cycle_state': 'work'
                    }
                else:
                    # Ainda em período de interjornada
                    time_remaining = cycle.rest_time_remaining
                    
                    # Verificar violação de acesso antecipado
                    if time_remaining and time_remaining['total_seconds'] > self.violation_thresholds['early_access'] * 60:
                        self._create_violation(
                            cycle,
                            'early_access',
                            f"Acesso antecipado - {time_remaining['formatted']} restantes",
                            timestamp
                        )
                    
                    return {
                        'success': False,
                        'message': f'Acesso negado - {time_remaining["formatted"] if time_remaining else "tempo indeterminado"} restantes',
                        'action': 'deny',
                        'cycle_state': 'rest',
                        'time_remaining': time_remaining
                    }
            
            return {
                'success': False,
                'message': 'Estado de ciclo inválido',
                'action': 'deny'
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar evento de entrada: {e}")
            return {
                'success': False,
                'message': f'Erro ao processar entrada: {str(e)}',
                'action': 'deny'
            }
    
    def _process_exit_event(self, cycle: InterjornadaCycle, timestamp: datetime) -> Dict:
        """
        Processa evento de saída.
        
        Args:
            cycle: Ciclo de interjornada
            timestamp: Timestamp do evento
            
        Returns:
            Dict: Resultado do processamento
        """
        try:
            if cycle.is_work_period:
                # Verificar se deve iniciar interjornada
                if cycle.should_start_rest:
                    # Iniciar período de interjornada
                    cycle.start_rest_period()
                    
                    SystemLog.log_info(
                        message=f"Funcionário {cycle.employee.name} iniciou período de interjornada",
                        category='interjornada',
                        user_id=cycle.employee.device_id,
                        user_name=cycle.employee.name,
                        details={'cycle_id': cycle.id}
                    )
                    
                    return {
                        'success': True,
                        'message': 'Período de interjornada iniciado',
                        'action': 'allow',
                        'cycle_state': 'rest'
                    }
                else:
                    # Ainda pode trabalhar
                    time_remaining = cycle.work_time_remaining
                    
                    # Verificar violação de saída antecipada
                    if time_remaining and time_remaining['total_seconds'] > self.violation_thresholds['exceeded_work_time'] * 60:
                        self._create_violation(
                            cycle,
                            'exceeded_work_time',
                            f"Saída antecipada - {time_remaining['formatted']} restantes",
                            timestamp
                        )
                    
                    return {
                        'success': True,
                        'message': f'Saída registrada - {time_remaining["formatted"] if time_remaining else "tempo indeterminado"} restantes',
                        'action': 'allow',
                        'cycle_state': 'work',
                        'time_remaining': time_remaining
                    }
            
            elif cycle.is_rest_period:
                # Já está em período de interjornada
                return {
                    'success': True,
                    'message': 'Funcionário já está em período de interjornada',
                    'action': 'allow',
                    'cycle_state': 'rest'
                }
            
            return {
                'success': False,
                'message': 'Estado de ciclo inválido',
                'action': 'deny'
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar evento de saída: {e}")
            return {
                'success': False,
                'message': f'Erro ao processar saída: {str(e)}',
                'action': 'deny'
            }
    
    def _create_violation(self, cycle: InterjornadaCycle, violation_type: str, description: str, timestamp: datetime):
        """
        Cria violação de interjornada.
        
        Args:
            cycle: Ciclo de interjornada
            violation_type: Tipo da violação
            description: Descrição da violação
            timestamp: Timestamp da violação
        """
        try:
            # Determinar severidade baseada no tipo
            severity_map = {
                'early_access': 'medium',
                'late_access': 'low',
                'exceeded_work_time': 'high',
                'insufficient_rest': 'critical',
                'unauthorized_access': 'critical',
            }
            
            violation = InterjornadaViolation.objects.create(
                cycle=cycle,
                violation_type=violation_type,
                severity=severity_map.get(violation_type, 'medium'),
                description=description,
                violation_time=timestamp,
                details={
                    'employee_id': cycle.employee.id,
                    'cycle_id': cycle.id,
                    'rule_id': cycle.rule.id
                }
            )
            
            # Log da violação
            SystemLog.log_warning(
                message=f"Violação de interjornada detectada: {description}",
                category='interjornada',
                user_id=cycle.employee.device_id,
                user_name=cycle.employee.name,
                details={
                    'violation_id': violation.id,
                    'violation_type': violation_type,
                    'severity': violation.severity
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar violação: {e}")
    
    def get_employee_status(self, employee: Employee) -> Dict:
        """
        Obtém status atual do funcionário.
        
        Args:
            employee: Funcionário
            
        Returns:
            Dict: Status do funcionário
        """
        try:
            # Buscar ciclo ativo
            active_cycle = InterjornadaCycle.objects.filter(
                employee=employee,
                current_state__in=['work', 'rest']
            ).first()
            
            if not active_cycle:
                return {
                    'has_active_cycle': False,
                    'can_access': True,
                    'message': 'Nenhum ciclo ativo - pode iniciar trabalho',
                    'next_action': 'start_work'
                }
            
            # Verificar se pode acessar
            if active_cycle.is_work_period:
                time_remaining = active_cycle.work_time_remaining
                return {
                    'has_active_cycle': True,
                    'can_access': True,
                    'cycle_state': 'work',
                    'message': 'Funcionário em período de trabalho',
                    'time_remaining': time_remaining,
                    'next_action': 'continue_work'
                }
            else:
                time_remaining = active_cycle.rest_time_remaining
                can_access = active_cycle.can_start_work
                
                return {
                    'has_active_cycle': True,
                    'can_access': can_access,
                    'cycle_state': 'rest',
                    'message': 'Funcionário em período de interjornada' if not can_access else 'Pode iniciar trabalho',
                    'time_remaining': time_remaining,
                    'next_action': 'start_work' if can_access else 'wait_rest'
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter status do funcionário {employee.name}: {e}")
            return {
                'has_active_cycle': False,
                'can_access': False,
                'message': f'Erro ao obter status: {str(e)}',
                'next_action': 'error'
            }
    
    def complete_cycle(self, employee: Employee) -> bool:
        """
        Completa ciclo ativo do funcionário.
        
        Args:
            employee: Funcionário
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            with transaction.atomic():
                active_cycle = InterjornadaCycle.objects.filter(
                    employee=employee,
                    current_state__in=['work', 'rest']
                ).first()
                
                if not active_cycle:
                    return False
                
                # Completar ciclo
                active_cycle.complete_cycle()
                
                # Atualizar estatísticas
                self._update_daily_statistics(employee, active_cycle)
                
                SystemLog.log_info(
                    message=f"Ciclo de interjornada completado para {employee.name}",
                    category='interjornada',
                    user_id=employee.device_id,
                    user_name=employee.name,
                    details={'cycle_id': active_cycle.id}
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Erro ao completar ciclo para {employee.name}: {e}")
            return False
    
    def _update_daily_statistics(self, employee: Employee, cycle: InterjornadaCycle):
        """
        Atualiza estatísticas diárias do funcionário.
        
        Args:
            employee: Funcionário
            cycle: Ciclo completado
        """
        try:
            today = date.today()
            
            # Buscar ou criar estatística do dia
            stats, created = InterjornadaStatistics.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={
                    'total_cycles': 0,
                    'completed_cycles': 0,
                    'total_work_time_minutes': 0,
                    'total_rest_time_minutes': 0,
                    'total_violations': 0,
                }
            )
            
            # Atualizar estatísticas
            stats.total_cycles += 1
            stats.completed_cycles += 1
            
            if cycle.actual_work_duration_minutes:
                stats.total_work_time_minutes += cycle.actual_work_duration_minutes
            
            if cycle.actual_rest_duration_minutes:
                stats.total_rest_time_minutes += cycle.actual_rest_duration_minutes
            
            # Contar violações
            violations_count = cycle.violations.count()
            stats.total_violations += violations_count
            
            # Calcular médias
            if stats.total_cycles > 0:
                stats.average_work_time_minutes = stats.total_work_time_minutes / stats.total_cycles
                stats.average_rest_time_minutes = stats.total_rest_time_minutes / stats.total_cycles
            
            stats.save()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas diárias: {e}")


class InterjornadaMonitoringService:
    """Serviço para monitoramento de interjornada."""
    
    def __init__(self):
        self.is_monitoring = False
    
    def start_monitoring(self):
        """Inicia monitoramento de interjornada."""
        self.is_monitoring = True
        logger.info("Monitoramento de interjornada iniciado")
    
    def stop_monitoring(self):
        """Para monitoramento de interjornada."""
        self.is_monitoring = False
        logger.info("Monitoramento de interjornada parado")
    
    def monitor_cycles(self) -> Dict:
        """
        Monitora ciclos ativos.
        
        Returns:
            Dict: Estatísticas do monitoramento
        """
        if not self.is_monitoring:
            return {'status': 'stopped', 'message': 'Monitoramento não está ativo'}
        
        try:
            # Buscar ciclos ativos
            active_cycles = InterjornadaCycle.objects.filter(
                current_state__in=['work', 'rest']
            ).select_related('employee', 'rule')
            
            stats = {
                'status': 'running',
                'total_active_cycles': active_cycles.count(),
                'work_cycles': active_cycles.filter(current_state='work').count(),
                'rest_cycles': active_cycles.filter(current_state='rest').count(),
                'violations_detected': 0,
                'cycles_completed': 0,
                'errors': []
            }
            
            for cycle in active_cycles:
                try:
                    # Verificar se ciclo deve ser completado
                    if cycle.is_work_period and cycle.should_start_rest:
                        cycle.start_rest_period()
                        stats['cycles_completed'] += 1
                    
                    elif cycle.is_rest_period and cycle.can_start_work:
                        # Ciclo pode ser completado
                        cycle.complete_cycle()
                        stats['cycles_completed'] += 1
                        
                except Exception as e:
                    stats['errors'].append(f"Erro no ciclo {cycle.id}: {str(e)}")
                    logger.error(f"Erro ao monitorar ciclo {cycle.id}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de ciclos: {e}")
            return {
                'status': 'error',
                'message': f'Erro no monitoramento: {str(e)}',
                'total_active_cycles': 0,
                'work_cycles': 0,
                'rest_cycles': 0,
                'violations_detected': 0,
                'cycles_completed': 0,
                'errors': [str(e)]
            }


# Instâncias globais dos serviços
interjornada_service = InterjornadaService()
interjornada_monitoring_service = InterjornadaMonitoringService()
