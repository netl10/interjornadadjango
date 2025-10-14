"""
Views para o app interjornada.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import InterjornadaRule, InterjornadaCycle, InterjornadaViolation, InterjornadaStatistics
from .serializers import (
    InterjornadaRuleSerializer, InterjornadaCycleSerializer, 
    InterjornadaViolationSerializer, InterjornadaStatisticsSerializer
)
from .services import interjornada_service, interjornada_monitoring_service
from apps.employees.models import Employee
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


class InterjornadaRuleListCreateView(generics.ListCreateAPIView):
    """View para listar e criar regras de interjornada."""
    
    queryset = InterjornadaRule.objects.all()
    serializer_class = InterjornadaRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra regras baseado nos parâmetros."""
        queryset = InterjornadaRule.objects.all()
        
        # Filtro por ativa
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filtro por nome
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        return queryset.order_by('name')


class InterjornadaRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View para detalhes, atualização e exclusão de regra."""
    
    queryset = InterjornadaRule.objects.all()
    serializer_class = InterjornadaRuleSerializer
    permission_classes = [IsAuthenticated]


class InterjornadaCycleListView(generics.ListAPIView):
    """View para listar ciclos de interjornada."""
    
    queryset = InterjornadaCycle.objects.all()
    serializer_class = InterjornadaCycleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra ciclos baseado nos parâmetros."""
        queryset = InterjornadaCycle.objects.select_related('employee', 'rule')
        
        # Filtro por funcionário
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filtro por ID do dispositivo
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(employee__device_id=device_id)
        
        # Filtro por estado
        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(current_state=state)
        
        # Filtro por ciclos ativos
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(current_state__in=['work', 'rest'])
        
        return queryset.order_by('-cycle_start')


class InterjornadaViolationListView(generics.ListAPIView):
    """View para listar violações de interjornada."""
    
    queryset = InterjornadaViolation.objects.all()
    serializer_class = InterjornadaViolationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra violações baseado nos parâmetros."""
        queryset = InterjornadaViolation.objects.select_related('cycle__employee', 'resolved_by')
        
        # Filtro por funcionário
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(cycle__employee_id=employee_id)
        
        # Filtro por tipo
        violation_type = self.request.query_params.get('violation_type')
        if violation_type:
            queryset = queryset.filter(violation_type=violation_type)
        
        # Filtro por severidade
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filtro por resolvida
        resolved = self.request.query_params.get('resolved')
        if resolved is not None:
            queryset = queryset.filter(resolved=resolved.lower() == 'true')
        
        return queryset.order_by('-violation_time')


class InterjornadaStatisticsListView(generics.ListAPIView):
    """View para listar estatísticas de interjornada."""
    
    queryset = InterjornadaStatistics.objects.all()
    serializer_class = InterjornadaStatisticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra estatísticas baseado nos parâmetros."""
        queryset = InterjornadaStatistics.objects.select_related('employee')
        
        # Filtro por funcionário
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filtro por data
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cycle(request, device_id):
    """
    Cria novo ciclo de interjornada para funcionário.
    """
    try:
        employee = get_object_or_404(Employee, device_id=device_id, is_active=True)
        
        # Criar ciclo
        cycle = interjornada_service.create_cycle(employee)
        
        if cycle:
            serializer = InterjornadaCycleSerializer(cycle)
            return Response({
                'status': 'success',
                'message': 'Ciclo de interjornada criado com sucesso',
                'data': serializer.data
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Não foi possível criar ciclo de interjornada'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao criar ciclo para dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_access_event(request, device_id):
    """
    Processa evento de acesso do funcionário.
    """
    try:
        employee = get_object_or_404(Employee, device_id=device_id, is_active=True)
        
        # Obter dados do evento
        event_type = request.data.get('event_type')
        timestamp_str = request.data.get('timestamp')
        
        if not event_type or not timestamp_str:
            return Response({
                'status': 'error',
                'message': 'Parâmetros event_type e timestamp são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Converter timestamp
        try:
            timestamp = TimezoneUtils.parse_datetime(timestamp_str)
            if not timestamp:
                timestamp = TimezoneUtils.get_utc_now()
        except:
            timestamp = TimezoneUtils.get_utc_now()
        
        # Processar evento
        result = interjornada_service.process_access_event(employee, event_type, timestamp)
        
        return Response({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar evento de acesso para dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employee_status(request, device_id):
    """
    Obtém status atual do funcionário.
    """
    try:
        employee = get_object_or_404(Employee, device_id=device_id, is_active=True)
        
        # Obter status
        status = interjornada_service.get_employee_status(employee)
        
        return Response({
            'status': 'success',
            'data': {
                'employee': {
                    'id': employee.id,
                    'device_id': employee.device_id,
                    'name': employee.name,
                    'is_exempt': employee.is_exempt
                },
                'interjornada_status': status
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status do funcionário {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_cycle(request, device_id):
    """
    Completa ciclo ativo do funcionário.
    """
    try:
        employee = get_object_or_404(Employee, device_id=device_id, is_active=True)
        
        # Completar ciclo
        success = interjornada_service.complete_cycle(employee)
        
        if success:
            return Response({
                'status': 'success',
                'message': 'Ciclo completado com sucesso'
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Nenhum ciclo ativo encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Erro ao completar ciclo para dispositivo {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_violation(request, violation_id):
    """
    Resolve violação de interjornada.
    """
    try:
        violation = get_object_or_404(InterjornadaViolation, id=violation_id)
        
        # Obter dados da resolução
        action_taken = request.data.get('action_taken')
        
        if not action_taken:
            return Response({
                'status': 'error',
                'message': 'Parâmetro action_taken é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Resolver violação
        violation.resolve(request.user, action_taken)
        
        serializer = InterjornadaViolationSerializer(violation)
        
        return Response({
            'status': 'success',
            'message': 'Violação resolvida com sucesso',
            'data': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Erro ao resolver violação {violation_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_monitoring(request):
    """
    Inicia monitoramento de interjornada.
    """
    try:
        interjornada_monitoring_service.start_monitoring()
        
        return Response({
            'status': 'success',
            'message': 'Monitoramento de interjornada iniciado',
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
    Para monitoramento de interjornada.
    """
    try:
        interjornada_monitoring_service.stop_monitoring()
        
        return Response({
            'status': 'success',
            'message': 'Monitoramento de interjornada parado',
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
    Retorna status do monitoramento de interjornada.
    """
    try:
        # Executar monitoramento se estiver ativo
        if interjornada_monitoring_service.is_monitoring:
            stats = interjornada_monitoring_service.monitor_cycles()
        else:
            stats = {'status': 'stopped', 'message': 'Monitoramento não está ativo'}
        
        return Response({
            'status': 'success',
            'data': {
                'monitoring_active': interjornada_monitoring_service.is_monitoring,
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
def get_active_cycles(request):
    """
    Retorna todos os ciclos ativos.
    """
    try:
        cycles = InterjornadaCycle.objects.filter(
            current_state__in=['work', 'rest']
        ).select_related('employee', 'rule').order_by('-cycle_start')
        
        serializer = InterjornadaCycleSerializer(cycles, many=True)
        
        return Response({
            'status': 'success',
            'data': {
                'cycles': serializer.data,
                'total_count': cycles.count(),
                'work_cycles': cycles.filter(current_state='work').count(),
                'rest_cycles': cycles.filter(current_state='rest').count(),
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter ciclos ativos: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_violations_summary(request):
    """
    Retorna resumo de violações.
    """
    try:
        # Violações não resolvidas
        unresolved_violations = InterjornadaViolation.objects.filter(
            resolved=False
        ).select_related('cycle__employee')
        
        # Violações por severidade
        severity_counts = {}
        for severity, _ in InterjornadaViolation.SEVERITY_LEVELS:
            severity_counts[severity] = unresolved_violations.filter(severity=severity).count()
        
        # Violações por tipo
        type_counts = {}
        for violation_type, _ in InterjornadaViolation.VIOLATION_TYPES:
            type_counts[violation_type] = unresolved_violations.filter(violation_type=violation_type).count()
        
        return Response({
            'status': 'success',
            'data': {
                'total_unresolved': unresolved_violations.count(),
                'severity_counts': severity_counts,
                'type_counts': type_counts,
                'critical_violations': severity_counts.get('critical', 0),
                'high_violations': severity_counts.get('high', 0),
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo de violações: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
