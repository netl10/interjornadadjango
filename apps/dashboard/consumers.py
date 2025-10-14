"""
WebSocket consumers para o app dashboard.
"""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.employees.models import EmployeeSession
from apps.interjornada.models import InterjornadaCycle, InterjornadaViolation
from apps.devices.models import Device
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """Consumer para atualizações em tempo real do dashboard."""
    
    async def connect(self):
        """Conecta ao WebSocket."""
        self.room_group_name = 'dashboard_updates'
        
        # Entrar no grupo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar dados iniciais
        await self.send_initial_data()
        
        # Iniciar loop de atualizações
        asyncio.create_task(self.periodic_updates())
    
    async def disconnect(self, close_code):
        """Desconecta do WebSocket."""
        # Sair do grupo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Recebe mensagem do cliente."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': TimezoneUtils.get_utc_now().isoformat()
                }))
            elif message_type == 'request_update':
                await self.send_dashboard_update()
            elif message_type == 'subscribe_employee':
                employee_id = data.get('employee_id')
                if employee_id:
                    await self.subscribe_employee_updates(employee_id)
            
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON do WebSocket")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem WebSocket: {e}")
    
    async def send_initial_data(self):
        """Envia dados iniciais do dashboard."""
        try:
            dashboard_data = await self.get_dashboard_data()
            await self.send(text_data=json.dumps({
                'type': 'initial_data',
                'data': dashboard_data
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar dados iniciais: {e}")
    
    async def send_dashboard_update(self):
        """Envia atualização do dashboard."""
        try:
            dashboard_data = await self.get_dashboard_data()
            await self.send(text_data=json.dumps({
                'type': 'dashboard_update',
                'data': dashboard_data
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar atualização do dashboard: {e}")
    
    async def periodic_updates(self):
        """Loop de atualizações periódicas."""
        while True:
            try:
                await asyncio.sleep(3)  # Atualizar a cada 3 segundos
                
                # Verificar se ainda está conectado
                if self.channel_name not in self.channel_layer.groups.get(self.room_group_name, []):
                    break
                
                # Enviar atualização
                await self.send_dashboard_update()
                
            except Exception as e:
                logger.error(f"Erro no loop de atualizações: {e}")
                break
    
    async def subscribe_employee_updates(self, employee_id):
        """Inscreve-se em atualizações de um funcionário específico."""
        try:
            employee_data = await self.get_employee_data(employee_id)
            await self.send(text_data=json.dumps({
                'type': 'employee_update',
                'employee_id': employee_id,
                'data': employee_data
            }))
        except Exception as e:
            logger.error(f"Erro ao obter dados do funcionário {employee_id}: {e}")
    
    async def access_denied_notification(self, event):
        """Envia notificação de acesso negado."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'access_denied',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de acesso negado: {e}")
    
    async def violation_detected(self, event):
        """Envia notificação de violação detectada."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'violation_detected',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de violação: {e}")
    
    async def device_status_change(self, event):
        """Envia notificação de mudança de status do dispositivo."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'device_status_change',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de status do dispositivo: {e}")
    
    @database_sync_to_async
    def get_dashboard_data(self):
        """Obtém dados do dashboard."""
        try:
            # Estatísticas gerais
            total_employees = EmployeeSession.objects.filter(
                employee__is_active=True
            ).values('employee').distinct().count()
            
            active_sessions = EmployeeSession.objects.filter(
                state__in=['active', 'pending_rest', 'blocked']
            ).count()
            
            blocked_employees = EmployeeSession.objects.filter(state='blocked').count()
            active_cycles = InterjornadaCycle.objects.filter(
                current_state__in=['work', 'rest']
            ).count()
            
            # Dispositivos
            total_devices = Device.objects.count()
            connected_devices = Device.objects.filter(status='active').count()
            
            # Violações não resolvidas
            unresolved_violations = InterjornadaViolation.objects.filter(resolved=False).count()
            critical_violations = InterjornadaViolation.objects.filter(
                resolved=False, severity='critical'
            ).count()
            
            # Funcionários bloqueados
            blocked_sessions = EmployeeSession.objects.filter(
                state='blocked'
            ).select_related('employee').order_by('return_time')[:10]
            
            blocked_data = []
            for session in blocked_sessions:
                time_remaining = session.time_remaining_until_return
                blocked_data.append({
                    'employee_id': session.employee.device_id,
                    'employee_name': session.employee.name,
                    'block_start': session.display_block_start,
                    'return_time': session.display_return_time,
                    'time_remaining': time_remaining,
                    'can_access_now': time_remaining['is_expired'] if time_remaining else False
                })
            
            # Sessões ativas - usar os mesmos dados da API
            active_sessions_data = []
            for session in EmployeeSession.objects.filter(
                state__in=['active', 'pending_rest']
            ).select_related('employee')[:10]:
                # Calcular tempo decorrido (igual à API)
                from django.utils import timezone
                from datetime import timedelta
                tempo_decorrido = timezone.now() - session.first_access
                tempo_decorrido_minutos = int(tempo_decorrido.total_seconds() / 60)
                
                # Calcular tempo restante para interjornada (se ativa)
                tempo_restante_interjornada = None
                if session.state == 'active':
                    tempo_limite = session.first_access + timedelta(minutes=session.work_duration_minutes)
                    if timezone.now() < tempo_limite:
                        tempo_restante = tempo_limite - timezone.now()
                        tempo_restante_interjornada = int(tempo_restante.total_seconds() / 60)
                
                active_sessions_data.append({
                    'employee_id': session.employee.device_id,
                    'employee_name': session.employee.name,
                    'state': session.state,
                    'first_access': session.display_first_access,
                    'last_access': session.display_last_access,
                    'tempo_decorrido_minutos': tempo_decorrido_minutos,
                    'tempo_restante_interjornada': tempo_restante_interjornada,
                })
            
            return {
                'statistics': {
                    'total_employees': total_employees,
                    'active_sessions': active_sessions,
                    'blocked_employees': blocked_employees,
                    'active_cycles': active_cycles,
                    'total_devices': total_devices,
                    'connected_devices': connected_devices,
                    'unresolved_violations': unresolved_violations,
                    'critical_violations': critical_violations,
                },
                'blocked_employees': blocked_data,
                'active_sessions': active_sessions_data,
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter dados do dashboard: {e}")
            return {
                'error': str(e),
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
    
    @database_sync_to_async
    def get_employee_data(self, employee_id):
        """Obtém dados de um funcionário específico."""
        try:
            from apps.employees.models import Employee
            
            employee = Employee.objects.get(device_id=employee_id, is_active=True)
            
            # Sessão ativa
            active_session = EmployeeSession.objects.filter(
                employee=employee,
                state__in=['active', 'pending_rest', 'blocked']
            ).first()
            
            # Ciclo ativo
            active_cycle = InterjornadaCycle.objects.filter(
                employee=employee,
                current_state__in=['work', 'rest']
            ).first()
            
            return {
                'employee': {
                    'id': employee.id,
                    'device_id': employee.device_id,
                    'name': employee.name,
                    'is_exempt': employee.is_exempt,
                },
                'active_session': {
                    'id': active_session.id if active_session else None,
                    'state': active_session.state if active_session else None,
                    'return_time': active_session.display_return_time if active_session else None,
                    'time_remaining': active_session.time_remaining_until_return if active_session else None,
                } if active_session else None,
                'active_cycle': {
                    'id': active_cycle.id if active_cycle else None,
                    'current_state': active_cycle.current_state if active_cycle else None,
                    'work_time_remaining': active_cycle.work_time_remaining if active_cycle else None,
                    'rest_time_remaining': active_cycle.rest_time_remaining if active_cycle else None,
                } if active_cycle else None,
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter dados do funcionário {employee_id}: {e}")
            return {
                'error': str(e),
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
