"""
Serviço para gerenciamento de grupos de usuários e blacklist.
"""
import logging
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from .models import Employee, EmployeeGroup
from apps.logs.models import SystemLog

logger = logging.getLogger(__name__)


class GroupService:
    """Serviço para gerenciar grupos de usuários e blacklist."""
    
    def __init__(self):
        self.blacklist_group_name = "BLACKLIST_INTERJORNADA"
        self.blacklist_group = None
        self._ensure_blacklist_group()
    
    def _ensure_blacklist_group(self):
        """Garante que o grupo de blacklist existe."""
        try:
            self.blacklist_group, created = EmployeeGroup.objects.get_or_create(
                name=self.blacklist_group_name,
                defaults={
                    'description': 'Grupo temporário para usuários em interjornada',
                    'is_active': True,
                    'is_blacklist': True
                }
            )
            if created:
                logger.info(f"Grupo de blacklist criado: {self.blacklist_group_name}")
        except Exception as e:
            logger.error(f"Erro ao criar grupo de blacklist: {e}")
    
    def get_original_group(self, employee: Employee) -> Optional[EmployeeGroup]:
        """Obtém o grupo original do funcionário antes de ser movido para blacklist."""
        try:
            # Verificar se o funcionário tem um grupo original salvo
            if hasattr(employee, 'original_group') and employee.original_group:
                return employee.original_group
            
            # Se não tem grupo original salvo, assumir que o grupo atual é o original
            # (exceto se for o grupo de blacklist)
            if employee.group and employee.group.name != self.blacklist_group_name:
                return employee.group
            
            # Se não tem grupo, criar um grupo padrão
            default_group, created = EmployeeGroup.objects.get_or_create(
                name='GRUPO_PADRAO',
                defaults={
                    'description': 'Grupo padrão para funcionários sem grupo específico',
                    'is_active': True,
                    'is_blacklist': False
                }
            )
            if created:
                logger.info(f"Grupo padrão criado: {default_group.name}")
            
            return default_group
        except Exception as e:
            logger.error(f"Erro ao obter grupo original de {employee.name}: {e}")
            return None
    
    def move_to_blacklist(self, employee: Employee) -> bool:
        """Move funcionário para o grupo de blacklist - Robusto contra falhas de comunicação."""
        try:
            # Verificar se o funcionário está no grupo de exceção
            if self.is_in_exemption_group(employee):
                logger.info(f"Funcionário {employee.name} está no grupo de exceção - Ignorando regras de interjornada")
                return False  # Não mover usuários da whitelist
            
                # Salvar grupo original se ainda não foi salvo
                if not hasattr(employee, 'original_group') or not employee.original_group:
                    original_group = self.get_original_group(employee)
                    if original_group:
                        employee.original_group = original_group
                        employee.save(update_fields=['original_group'])
                        logger.info(f"Grupo original salvo para {employee.name}: {original_group.name}")
                
            # Verificar se blacklist_group existe e tem device_group_id
            if not self.blacklist_group:
                logger.error("Grupo de blacklist não encontrado")
                return False
            
            if not self.blacklist_group.device_group_id:
                logger.error(f"Grupo de blacklist {self.blacklist_group.name} não tem device_group_id configurado")
                return False
            
            # Tentar mover para blacklist no dispositivo
            device_move_success = False
            try:
                from apps.devices.device_client import DeviceClient
                client = DeviceClient()
                if client.login():
                    # Mover no dispositivo
                    original_group_id = employee.original_group.device_group_id if employee.original_group and employee.original_group.device_group_id else 1
                    device_move_success = client.move_user_to_group(
                        employee.device_id, 
                        self.blacklist_group.device_group_id, 
                        original_group_id
                    )
                    if device_move_success:
                        logger.info(f"Funcionário {employee.name} movido para blacklist no dispositivo (ID: {self.blacklist_group.device_group_id})")
                    else:
                        logger.warning(f"Falha ao mover {employee.name} para blacklist no dispositivo")
                else:
                    logger.warning(f"Falha ao conectar com dispositivo para mover {employee.name}")
            except Exception as e:
                logger.warning(f"Erro ao mover {employee.name} para blacklist no dispositivo: {e}")
            
            # Tentar mover para blacklist no sistema local (sempre fazer, mesmo se falhar no dispositivo)
            local_move_success = False
            try:
                # Atualizar no banco local
                    employee.group = self.blacklist_group
                    employee.save(update_fields=['group'])
                local_move_success = True
                logger.info(f"Funcionário {employee.name} movido para blacklist no sistema local")
            except Exception as e:
                logger.error(f"Erro ao mover {employee.name} para blacklist no sistema local: {e}")
                return False
                    
                    # Log da ação
                    SystemLog.objects.create(
                        level='INFO',
                        category='interjornada',
                        message=f'Funcionário {employee.name} movido para blacklist',
                        user_id=employee.device_id,
                        user_name=employee.name,
                        details={
                            'action': 'moved_to_blacklist',
                            'original_group': employee.original_group.name if employee.original_group else 'N/A',
                            'blacklist_group': self.blacklist_group.name,
                    'device_group_id': self.blacklist_group.device_group_id,
                    'device_move_success': device_move_success,
                    'local_move_success': local_move_success,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                    
            if device_move_success and local_move_success:
                logger.info(f"Funcionário {employee.name} movido para blacklist com sucesso (dispositivo + sistema)")
                    return True
            elif local_move_success:
                logger.warning(f"Funcionário {employee.name} movido para blacklist apenas no sistema local (falha no dispositivo)")
                return True  # Retornar True pois o bloqueio local é mais importante
                else:
                logger.error(f"Falha ao mover {employee.name} para blacklist")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao mover {employee.name} para blacklist: {e}")
            return False
    
    def restore_from_blacklist(self, employee: Employee) -> bool:
        """Restaura funcionário do grupo de blacklist para o grupo original - Robusto contra falhas."""
        try:
                if not employee.original_group:
                    logger.warning(f"Funcionário {employee.name} não tem grupo original salvo")
                # Tentar usar grupo padrão como fallback
                default_group = self.get_original_group(employee)
                if default_group:
                    logger.info(f"Usando grupo padrão como fallback para {employee.name}: {default_group.name}")
                    employee.group = default_group
                    employee.original_group = None
                    employee.save(update_fields=['group', 'original_group'])
                    
                    # Log da ação com fallback
                    SystemLog.objects.create(
                        level='WARNING',
                        category='interjornada',
                        message=f'Funcionário {employee.name} restaurado do blacklist usando grupo padrão (original não encontrado)',
                        user_id=employee.device_id,
                        user_name=employee.name,
                        details={
                            'action': 'restored_from_blacklist_fallback',
                            'restored_group': default_group.name,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                    return True
                else:
                    logger.error(f"Não foi possível restaurar {employee.name} - nem grupo original nem padrão encontrados")
                    return False
                
            # Tentar restaurar no dispositivo
            device_restore_success = False
            try:
                from apps.devices.device_client import DeviceClient
                client = DeviceClient()
                if client.login():
                    # Restaurar no dispositivo
                    original_group_id = employee.original_group.device_group_id if employee.original_group and employee.original_group.device_group_id else 1
                    device_restore_success = client.move_user_to_group(
                        employee.device_id, 
                        original_group_id, 
                        self.blacklist_group.device_group_id if self.blacklist_group and self.blacklist_group.device_group_id else None
                    )
                    if device_restore_success:
                        logger.info(f"Funcionário {employee.name} restaurado do blacklist no dispositivo (ID: {original_group_id})")
                    else:
                        logger.warning(f"Falha ao restaurar {employee.name} do blacklist no dispositivo")
                else:
                    logger.warning(f"Falha ao conectar com dispositivo para restaurar {employee.name}")
            except Exception as e:
                logger.warning(f"Erro ao restaurar {employee.name} do blacklist no dispositivo: {e}")
            
            # Restaurar grupo original no sistema local (sempre fazer, mesmo se falhar no dispositivo)
            local_restore_success = False
            try:
                employee.group = employee.original_group
                employee.original_group = None  # Limpar referência
                employee.save(update_fields=['group', 'original_group'])
                local_restore_success = True
                logger.info(f"Funcionário {employee.name} restaurado do blacklist no sistema local para {employee.group.name}")
            except Exception as e:
                logger.error(f"Erro ao restaurar {employee.name} no sistema local: {e}")
                return False
                
                # Log da ação
                SystemLog.objects.create(
                    level='INFO',
                    category='interjornada',
                    message=f'Funcionário {employee.name} restaurado do blacklist',
                    user_id=employee.device_id,
                    user_name=employee.name,
                    details={
                        'action': 'restored_from_blacklist',
                        'restored_group': employee.group.name,
                    'device_group_id': employee.group.device_group_id if employee.group else None,
                    'device_restore_success': device_restore_success,
                    'local_restore_success': local_restore_success,
                        'timestamp': timezone.now().isoformat()
                    }
                )
                
            if device_restore_success and local_restore_success:
                logger.info(f"Funcionário {employee.name} restaurado do blacklist com sucesso (dispositivo + sistema)")
                return True
            elif local_restore_success:
                logger.warning(f"Funcionário {employee.name} restaurado do blacklist apenas no sistema local (falha no dispositivo)")
                return True  # Retornar True pois a liberação local é mais importante
            else:
                logger.error(f"Falha ao restaurar {employee.name} do blacklist")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao restaurar {employee.name} do blacklist: {e}")
            return False
    
    def is_in_blacklist(self, employee: Employee) -> bool:
        """Verifica se o funcionário está na blacklist."""
        try:
            return (employee.group and 
                   employee.group.name == self.blacklist_group_name)
        except Exception as e:
            logger.error(f"Erro ao verificar blacklist para {employee.name}: {e}")
            return False
    
    def is_in_exemption_group(self, employee: Employee) -> bool:
        """Verifica se o funcionário está no grupo de exceção (whitelist)."""
        try:
            if not employee.group:
                return False
            
            # Verificar se está no grupo de exceção
            exemption_group_names = ['whitelist', 'exceção', 'exemption', 'liberado']
            group_name_lower = employee.group.name.lower()
            
            for exemption_name in exemption_group_names:
                if exemption_name in group_name_lower:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar grupo de exceção para {employee.name}: {e}")
            return False
    
    def get_blacklist_users(self) -> list:
        """Retorna lista de usuários na blacklist."""
        try:
            if not self.blacklist_group:
                return []
            
            return list(Employee.objects.filter(
                group=self.blacklist_group,
                is_active=True
            ).select_related('group', 'original_group'))
        except Exception as e:
            logger.error(f"Erro ao obter usuários da blacklist: {e}")
            return []
    
    def sync_groups_with_system_state(self) -> int:
        """Sincroniza os grupos com o estado do sistema - CRÍTICO para evitar usuários travados."""
        try:
            corrected_count = 0
            
            # 1. Verificar usuários que estão na blacklist mas NÃO deveriam estar
            blacklist_users = self.get_blacklist_users()
            
            for employee in blacklist_users:
                # Verificar se o funcionário realmente deveria estar bloqueado
                from apps.employee_sessions.models import EmployeeSession
                session = EmployeeSession.objects.filter(
                    employee=employee,
                    state='blocked'
                ).first()
                
                if not session:
                    # Funcionário está na blacklist mas não deveria estar - CORRIGIR
                    logger.warning(f"Funcionário {employee.name} está na blacklist mas não está bloqueado no sistema - Corrigindo")
                    
                    # Restaurar para grupo original
                    if self.restore_from_blacklist(employee):
                        corrected_count += 1
                        logger.info(f"Funcionário {employee.name} removido da blacklist e restaurado para grupo original")
                    else:
                        logger.warning(f"Falha ao remover {employee.name} da blacklist")
            
            # 2. Verificar usuários que estão bloqueados no sistema mas NÃO estão na blacklist
            from apps.employee_sessions.models import EmployeeSession
            blocked_sessions = EmployeeSession.objects.filter(state='blocked').select_related('employee')
            
            for session in blocked_sessions:
                if not self.is_in_blacklist(session.employee):
                    # Funcionário está bloqueado no sistema mas não na blacklist - CORRIGIR
                    logger.warning(f"Funcionário {session.employee.name} está bloqueado no sistema mas não na blacklist - Corrigindo")
                    
                    # Mover para blacklist
                    if self.move_to_blacklist(session.employee):
                        corrected_count += 1
                        logger.info(f"Funcionário {session.employee.name} movido para blacklist (estava bloqueado no sistema)")
                    else:
                        logger.warning(f"Falha ao mover {session.employee.name} para blacklist")
            
            if corrected_count > 0:
                logger.info(f"Sincronização de grupos concluída: {corrected_count} correções aplicadas")
            else:
                logger.info("Sincronização de grupos: Nenhuma correção necessária")
            
            return corrected_count
            
        except Exception as e:
            logger.error(f"Erro na sincronização de grupos: {e}")
            return 0
    
    def cleanup_expired_blacklist(self) -> int:
        """Remove usuários da blacklist que não deveriam mais estar lá."""
        try:
            # Esta função pode ser chamada periodicamente para limpeza
            # Por enquanto, apenas retorna 0 (não implementado)
            return 0
        except Exception as e:
            logger.error(f"Erro na limpeza da blacklist: {e}")
            return 0


# Instância global do serviço
group_service = GroupService()
