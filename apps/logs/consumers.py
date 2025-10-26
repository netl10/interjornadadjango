"""
WebSocket consumers para logs em tempo real.
"""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.logs.models import AccessLog
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


class RealtimeLogsConsumer(AsyncWebsocketConsumer):
    """Consumer para logs em tempo real."""
    
    async def connect(self):
        """Conecta ao WebSocket."""
        self.room_group_name = 'realtime_logs'
        
        # Entrar no grupo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar logs iniciais
        await self.send_initial_logs()
        
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
                await self.send_logs_update()
            
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON do WebSocket")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem WebSocket: {e}")
    
    async def send_initial_logs(self):
        """Envia logs iniciais."""
        try:
            logs_data = await self.get_recent_logs(20)
            await self.send(text_data=json.dumps({
                'type': 'initial_logs',
                'data': logs_data
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar logs iniciais: {e}")
    
    async def send_logs_update(self):
        """Envia atualização de logs."""
        try:
            logs_data = await self.get_recent_logs(20)
            await self.send(text_data=json.dumps({
                'type': 'logs_update',
                'data': logs_data
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar atualização de logs: {e}")
    
    async def periodic_updates(self):
        """Loop de atualizações periódicas."""
        while True:
            try:
                await asyncio.sleep(1)  # Atualizar a cada 1 segundo
                
                # Verificar se ainda está conectado
                if self.channel_name not in self.channel_layer.groups.get(self.room_group_name, []):
                    break
                
                # Enviar atualização
                await self.send_logs_update()
                
            except Exception as e:
                logger.error(f"Erro no loop de atualizações: {e}")
                break
    
    @database_sync_to_async
    def get_recent_logs(self, limit=20):
        """Busca logs recentes."""
        try:
            logs = AccessLog.objects.order_by('-device_timestamp')[:limit]
            
            logs_data = []
            for log in logs:
                # Determinar descrição do evento
                event_description = log.event_description
                if not event_description or event_description.strip() == '':
                    event_type_map = {
                        1: 'Entrada',
                        2: 'Saída', 
                        3: 'Não Identificado',
                        4: 'Erro de Leitura',
                        5: 'Timeout',
                        6: 'Acesso Negado',
                        7: 'Acesso Autorizado',
                        8: 'Acesso Bloqueado',
                        13: 'Desistência',
                    }
                    event_description = event_type_map.get(log.event_type, f'Evento {log.event_type}')
                
                logs_data.append({
                    'id': log.device_log_id,
                    'user_name': log.user_name,
                    'user_id': log.user_id,
                    'event_type': log.event_type,
                    'event_description': event_description,
                    'portal_id': log.portal_id,
                    'device_timestamp': log.device_timestamp.strftime('%Y-%m-%dT%H:%M:%S'),
                    'processing_status': log.processing_status,
                    'created_at': log.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
                })
            
            return {
                'logs': logs_data,
                'total_logs': AccessLog.objects.count(),
                'timestamp': TimezoneUtils.get_utc_now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar logs: {e}")
            return {
                'logs': [],
                'total_logs': 0,
                'timestamp': TimezoneUtils.get_utc_now().isoformat(),
                'error': str(e)
            }
    
    async def access_denied_notification(self, event):
        """Envia notificação de acesso negado."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'access_denied',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de acesso negado: {e}")
    
    async def new_log_notification(self, event):
        """Envia notificação de novo log."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'new_log',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de novo log: {e}")

