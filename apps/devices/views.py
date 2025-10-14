"""
Views para o app devices.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from .models import Device, DeviceLog, DeviceSession
from .serializers import DeviceSerializer, DeviceLogSerializer, DeviceSessionSerializer
from .services import device_connection_service, device_data_service, device_monitoring_service
from apps.core.utils import CacheUtils
import logging

logger = logging.getLogger(__name__)


class DeviceListCreateView(generics.ListCreateAPIView):
    """View para listar e criar dispositivos."""
    
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra dispositivos baseado nos parâmetros."""
        queryset = Device.objects.all()
        
        # Filtro por tipo
        device_type = self.request.query_params.get('device_type')
        if device_type:
            queryset = queryset.filter(device_type=device_type)
        
        # Filtro por status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filtro por habilitado
        is_enabled = self.request.query_params.get('is_enabled')
        if is_enabled is not None:
            queryset = queryset.filter(is_enabled=is_enabled.lower() == 'true')
        
        return queryset.order_by('device_type', 'name')


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View para detalhes, atualização e exclusão de dispositivo."""
    
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]


class DeviceLogListView(generics.ListAPIView):
    """View para listar logs de dispositivos."""
    
    queryset = DeviceLog.objects.all()
    serializer_class = DeviceLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra logs baseado nos parâmetros."""
        queryset = DeviceLog.objects.select_related('device')
        
        # Filtro por dispositivo
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        # Filtro por tipo de log
        log_type = self.request.query_params.get('log_type')
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        
        # Filtro por nível
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Limite de registros
        limit = self.request.query_params.get('limit', 100)
        try:
            limit = int(limit)
            queryset = queryset[:limit]
        except ValueError:
            queryset = queryset[:100]
        
        return queryset.order_by('-timestamp')


class DeviceSessionListView(generics.ListAPIView):
    """View para listar sessões de dispositivos."""
    
    queryset = DeviceSession.objects.all()
    serializer_class = DeviceSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra sessões baseado nos parâmetros."""
        queryset = DeviceSession.objects.select_related('device')
        
        # Filtro por dispositivo
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        # Filtro por sessões ativas
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-started_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def connect_device(request, device_id):
    """
    Conecta a um dispositivo específico.
    """
    try:
        device = get_object_or_404(Device, id=device_id)
        
        # Conectar ao dispositivo
        success, message, token = device_connection_service.connect_to_device(device)
        
        if success:
            return Response({
                'status': 'success',
                'message': message,
                'data': {
                    'device_id': device.id,
                    'device_name': device.name,
                    'token': token[:20] + '...' if token else None,
                    'connected_at': device.last_connection.isoformat() if device.last_connection else None
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao conectar dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_device(request, device_id):
    """
    Desconecta de um dispositivo específico.
    """
    try:
        device = get_object_or_404(Device, id=device_id)
        
        # Desconectar do dispositivo
        success = device_connection_service.disconnect_device(device)
        
        if success:
            return Response({
                'status': 'success',
                'message': 'Dispositivo desconectado com sucesso',
                'data': {
                    'device_id': device.id,
                    'device_name': device.name,
                    'disconnected_at': TimezoneUtils.get_utc_now().isoformat()
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Erro ao desconectar dispositivo'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao desconectar dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_logs(request, device_id):
    """
    Busca logs de acesso de um dispositivo específico.
    """
    try:
        device = get_object_or_404(Device, id=device_id)
        limit = request.query_params.get('limit', 100)
        
        try:
            limit = int(limit)
        except ValueError:
            limit = 100
        
        # Buscar logs do dispositivo
        success, message, logs = device_data_service.get_device_logs(device, limit)
        
        if success:
            return Response({
                'status': 'success',
                'message': message,
                'data': {
                    'device_id': device.id,
                    'device_name': device.name,
                    'logs': logs,
                    'count': len(logs)
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao buscar logs do dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_status(request, device_id):
    """
    Busca status de um dispositivo específico.
    """
    try:
        device = get_object_or_404(Device, id=device_id)
        
        # Buscar status do dispositivo
        success, message, status_data = device_data_service.get_device_status(device)
        
        if success:
            return Response({
                'status': 'success',
                'message': message,
                'data': {
                    'device_id': device.id,
                    'device_name': device.name,
                    'device_status': device.status,
                    'is_connected': device.is_connected,
                    'last_connection': device.last_connection.isoformat() if device.last_connection else None,
                    'connection_success_rate': device.connection_success_rate,
                    'status_data': status_data
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao buscar status do dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_users(request, device_id):
    """
    Busca usuários de um dispositivo específico.
    """
    try:
        device = get_object_or_404(Device, id=device_id)
        
        # Buscar usuários do dispositivo
        success, message, users = device_data_service.get_device_users(device)
        
        if success:
            return Response({
                'status': 'success',
                'message': message,
                'data': {
                    'device_id': device.id,
                    'device_name': device.name,
                    'users': users,
                    'count': len(users)
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao buscar usuários do dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_groups(request, device_id):
    """
    Busca grupos de um dispositivo específico.
    """
    try:
        device = get_object_or_404(Device, id=device_id)
        
        # Buscar grupos do dispositivo
        success, message, groups = device_data_service.get_device_groups(device)
        
        if success:
            return Response({
                'status': 'success',
                'message': message,
                'data': {
                    'device_id': device.id,
                    'device_name': device.name,
                    'groups': groups,
                    'count': len(groups)
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao buscar grupos do dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_monitoring(request):
    """
    Inicia monitoramento de dispositivos.
    """
    try:
        device_monitoring_service.start_monitoring()
        
        return Response({
            'status': 'success',
            'message': 'Monitoramento iniciado com sucesso',
            'data': {
                'monitoring_active': True,
                'started_at': TimezoneUtils.get_utc_now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao iniciar monitoramento: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_monitoring(request):
    """
    Para monitoramento de dispositivos.
    """
    try:
        device_monitoring_service.stop_monitoring()
        
        return Response({
            'status': 'success',
            'message': 'Monitoramento parado com sucesso',
            'data': {
                'monitoring_active': False,
                'stopped_at': TimezoneUtils.get_utc_now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao parar monitoramento: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_monitoring_status(request):
    """
    Retorna status do monitoramento de dispositivos.
    """
    try:
        # Executar monitoramento se estiver ativo
        if device_monitoring_service.is_monitoring:
            stats = device_monitoring_service.monitor_devices()
        else:
            stats = {'status': 'stopped', 'message': 'Monitoramento não está ativo'}
        
        return Response({
            'status': 'success',
            'data': {
                'monitoring_active': device_monitoring_service.is_monitoring,
                'stats': stats,
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status do monitoramento: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_devices_status(request):
    """
    Retorna status de todos os dispositivos.
    """
    try:
        devices = Device.objects.all()
        devices_status = []
        
        for device in devices:
            # Verificar se dispositivo está conectado
            is_connected = device.is_connected
            
            # Buscar sessão ativa
            active_session = DeviceSession.objects.filter(
                device=device,
                is_active=True
            ).first()
            
            device_status = {
                'id': device.id,
                'name': device.name,
                'device_type': device.device_type,
                'ip_address': device.ip_address,
                'port': device.port,
                'status': device.status,
                'is_enabled': device.is_enabled,
                'is_connected': is_connected,
                'last_connection': device.last_connection.isoformat() if device.last_connection else None,
                'last_error': device.last_error.isoformat() if device.last_error else None,
                'error_count': device.error_count,
                'success_count': device.success_count,
                'connection_success_rate': device.connection_success_rate,
                'active_session': {
                    'id': active_session.id if active_session else None,
                    'started_at': active_session.started_at.isoformat() if active_session else None,
                    'requests_count': active_session.requests_count if active_session else 0,
                    'errors_count': active_session.errors_count if active_session else 0,
                    'success_rate': active_session.success_rate if active_session else 0
                } if active_session else None
            }
            
            devices_status.append(device_status)
        
        return Response({
            'status': 'success',
            'data': {
                'devices': devices_status,
                'total_count': len(devices_status),
                'active_count': sum(1 for d in devices_status if d['is_connected']),
                'error_count': sum(1 for d in devices_status if d['status'] == 'error'),
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status de todos os dispositivos: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
