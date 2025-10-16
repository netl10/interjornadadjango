"""
Serviços para gerenciamento de sessões de funcionários.
"""
import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta

from .models import EmployeeSession
from apps.employees.models import Employee
from apps.employees.group_service import group_service
from apps.core.models import SystemConfiguration
from apps.logs.models import SystemLog

logger = logging.getLogger(__name__)


class SessionService:
    """Serviço para gerenciar sessões de funcionários."""
    
    def __init__(self):
        self.event_handlers = {}
    
    def register_event_handler(self, event_type: str, handler):
        """Registra um handler para um tipo de evento."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: str, data: Dict):
        """Emite um evento para todos os handlers registrados."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Erro no handler de evento {event_type}: {e}")
    
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
            # Usar UTC para consistência no banco
            access_time = timezone.now()
        elif access_time.tzinfo is None:
            # Timestamp vindo da catraca está no horário local, converter para UTC
            import pytz
            local_tz = pytz.timezone('America/Sao_Paulo')
            local_time = local_tz.localize(access_time)
            access_time = local_time.astimezone(pytz.UTC)
        else:
            # Se já tem timezone, garantir que está em UTC
            import pytz
            access_time = access_time.astimezone(pytz.UTC)
        
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
            rest_duration_minutes=config.bloqueado_minutes,
            created_at=access_time,
            updated_at=access_time
        )
        
        logger.info(f"Sessão criada para {employee.name} - ID: {session.id}")
        
        # Emitir evento de sessão criada
        self.emit_event('session_created', {
            'session_id': session.id,
            'employee_id': employee.device_id,
            'employee_name': employee.name,
            'state': session.state,
            'timestamp': access_time.isoformat()
        })
        
        return session
    
    def block_user_for_interjornada(self, employee: Employee, block_start_time: datetime = None) -> bool:
        """Bloqueia funcionário para interjornada."""
        try:
            session = self.get_user_session(employee)
            if not session:
                logger.warning(f"Funcionário {employee.name} não tem sessão ativa")
                return False
            
            # Verificar se já atingiu tempo mínimo de trabalho
            config = self.get_system_config()
            current_time = timezone.now()
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
            
            # Mover funcionário para blacklist com tratamento robusto
            blacklist_success = group_service.move_to_blacklist(employee)
            if not blacklist_success:
                logger.warning(f"Falha ao mover {employee.name} para blacklist - Continuando com bloqueio local")
                # Continuar mesmo se falhar no grupo - o bloqueio local é mais importante
            
            # Emitir evento de interjornada iniciada
            self.emit_event('interjornada_started', {
                'session_id': session.id,
                'employee_id': employee.device_id,
                'employee_name': employee.name,
                'block_start': block_start_time.isoformat(),
                'return_time': return_time.isoformat(),
                'blacklist_moved': blacklist_success
            })
            
            logger.info(f"Funcionário {employee.name} colocado em interjornada - Retorna às {return_time.strftime('%H:%M:%S')}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao bloquear funcionário {employee.name}: {e}")
            return False
    
    def unblock_user_from_interjornada(self, employee: Employee) -> bool:
        """Libera funcionário da interjornada."""
        try:
            session = self.get_user_session(employee)
            if not session or session.state != 'blocked':
                logger.warning(f"Funcionário {employee.name} não está em interjornada")
                return False
            
            # Restaurar funcionário do blacklist com tratamento robusto
            blacklist_success = group_service.restore_from_blacklist(employee)
            if not blacklist_success:
                logger.warning(f"Falha ao restaurar {employee.name} do blacklist - Continuando com liberação local")
                # Continuar mesmo se falhar no grupo - a liberação local é mais importante
            
            # Remover sessão (interjornada finalizada)
            session.delete()
            
            # Emitir evento de interjornada finalizada
            self.emit_event('interjornada_ended', {
                'employee_id': employee.device_id,
                'employee_name': employee.name,
                'timestamp': timezone.now().isoformat(),
                'blacklist_restored': blacklist_success
            })
            
            logger.info(f"Funcionário {employee.name} liberado da interjornada")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao liberar funcionário {employee.name}: {e}")
            return False
    
    def get_active_sessions(self) -> List[EmployeeSession]:
        """Retorna todas as sessões ativas."""
        return EmployeeSession.objects.filter(
            state__in=['active', 'blocked', 'pending_rest']
        ).select_related('employee').order_by('-created_at')
    
    def cleanup_expired_sessions(self) -> int:
        """Remove sessões expiradas."""
        try:
            now = timezone.now()
            expired_sessions = EmployeeSession.objects.filter(
                state='blocked',
                return_time__lte=now
            ).select_related('employee')
            
            count = 0
            for session in expired_sessions:
                try:
                    logger.info(f"Sessão expirada detectada para {session.employee.name} - removendo automaticamente")
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
                            'finalized_at': now.isoformat()
                        }
                    )
                    session.delete()
                    count += 1
                except Exception as e:
                    logger.error(f"Erro ao remover sessão expirada de {session.employee.name}: {e}")
            
            return count
            
        except Exception as e:
            logger.error(f"Erro ao limpar sessões expiradas: {e}")
            return 0
    
    def enforce_session_timeouts(self):
        """Aplica regras de tempo para sessões já existentes."""
        try:
            now = timezone.now()
            
            # Finalizar sessões bloqueadas cujo retorno já venceu
            expired_sessions = EmployeeSession.objects.filter(
                state='blocked',
                return_time__lte=now
            ).select_related('employee')
            
            for session in expired_sessions:
                try:
                    logger.info(f"Sessão expirada detectada para {session.employee.name} - liberando automaticamente")
                    
                    # CRÍTICO: Restaurar do blacklist antes de deletar a sessão
                    from apps.employees.group_service import group_service
                    blacklist_success = group_service.restore_from_blacklist(session.employee)
                    
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
                            'blacklist_restored': blacklist_success
                        }
                    )
                    
                    # Deletar sessão após restaurar do blacklist
                    session.delete()
                    
                    if blacklist_success:
                        logger.info(f"Funcionário {session.employee.name} restaurado do blacklist automaticamente")
                    else:
                        logger.warning(f"Falha ao restaurar {session.employee.name} do blacklist automaticamente")
                        
                except Exception as e:
                    logger.error(f"Erro ao remover sessão expirada de {session.employee.name}: {e}")
            
            # Verificar sessões ativas que excederam o tempo de acesso livre
            config = self.get_system_config()
            sessions_pending_exit = EmployeeSession.objects.filter(
                state='active',
                first_access__lte=now - timedelta(minutes=config.liberado_minutes)
            ).select_related('employee')
            
            for session in sessions_pending_exit:
                try:
                    logger.info(f"Sessão de {session.employee.name} excedeu tempo livre. Aguardando saída Portal 2.")
                    # Mudar estado para pending_rest (aguardando saída)
                    session.state = 'pending_rest'
                    session.save(update_fields=['state'])
                    logger.info(f"Usuário {session.employee.name} em estado 'aguardando saída'")
                except Exception as e:
                    logger.error(f"Erro ao atualizar estado da sessão de {session.employee.name}: {e}")
            
            # Verificar sessões pending_rest que excederam o tempo total de trabalho
            sessions_pending_block = EmployeeSession.objects.filter(
                state='pending_rest',
                first_access__lte=now - timedelta(minutes=config.liberado_minutes + config.bloqueado_minutes)
            ).select_related('employee')
            
            for session in sessions_pending_block:
                try:
                    logger.info(f"Sessão de {session.employee.name} excedeu tempo total. Bloqueando automaticamente.")
                    
                    # Bloquear usuário para interjornada
                    from apps.employees.group_service import group_service
                    blacklist_success = group_service.move_to_blacklist(session.employee)
                    
                    # Atualizar sessão para bloqueada
                    session.state = 'blocked'
                    session.block_start = now
                    session.return_time = now + timedelta(minutes=config.bloqueado_minutes)
                    session.save(update_fields=['state', 'block_start', 'return_time'])
                    
                    logger.info(f"Usuário {session.employee.name} bloqueado automaticamente (blacklist: {blacklist_success})")
                except Exception as e:
                    logger.error(f"Erro ao bloquear sessão de {session.employee.name}: {e}")
            
            # Garantir que sessões ativas tenham last_access atualizado
            active_sessions = EmployeeSession.objects.filter(state='active').select_related('employee')
            for session in active_sessions:
                if session.last_access is None or session.last_access < session.first_access:
                    session.last_access = session.first_access
                    session.save(update_fields=['last_access'])
                    
        except Exception as e:
            logger.error(f"Erro ao aplicar regras de tempo para sessões: {e}")


# Instância global do serviço
session_service = SessionService()
