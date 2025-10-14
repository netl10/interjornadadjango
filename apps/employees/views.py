"""
Views para o app employees.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Employee, EmployeeGroup
from .serializers import (
    EmployeeSerializer, EmployeeGroupSerializer, EmployeeAccessCheckSerializer, EmployeeAccessResponseSerializer
)
from apps.core.utils import TimezoneUtils
import logging

logger = logging.getLogger(__name__)


class EmployeeListCreateView(generics.ListCreateAPIView):
    """View para listar e criar funcionários."""
    
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra funcionários baseado nos parâmetros."""
        queryset = Employee.objects.all()
        
        # Filtro por nome
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # Filtro por código
        employee_code = self.request.query_params.get('employee_code')
        if employee_code:
            queryset = queryset.filter(employee_code__icontains=employee_code)
        
        # Filtro por ID do dispositivo
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        # Filtro por status ativo
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filtro por isenção
        is_exempt = self.request.query_params.get('is_exempt')
        if is_exempt is not None:
            queryset = queryset.filter(is_exempt=is_exempt.lower() == 'true')
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        """Define o usuário que criou o funcionário."""
        serializer.save(created_by=self.request.user)


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View para detalhes, atualização e exclusão de funcionário."""
    
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'device_id'




class EmployeeGroupListCreateView(generics.ListCreateAPIView):
    """View para listar e criar grupos de funcionários."""
    
    queryset = EmployeeGroup.objects.all()
    serializer_class = EmployeeGroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtra grupos baseado nos parâmetros."""
        queryset = EmployeeGroup.objects.all()
        
        # Filtro por nome
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # Filtro por grupo de isenção
        is_exemption_group = self.request.query_params.get('is_exemption_group')
        if is_exemption_group is not None:
            queryset = queryset.filter(is_exemption_group=is_exemption_group.lower() == 'true')
        
        return queryset.order_by('name')


class EmployeeGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View para detalhes, atualização e exclusão de grupo."""
    
    queryset = EmployeeGroup.objects.all()
    serializer_class = EmployeeGroupSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_employee_access(request):
    """
    Verifica se um funcionário pode acessar baseado no ID do dispositivo.
    """
    try:
        serializer = EmployeeAccessCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Dados inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        device_id = serializer.validated_data['device_id']
        
        # Buscar funcionário
        try:
            employee = Employee.objects.get(device_id=device_id, is_active=True)
        except Employee.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Funcionário com ID {device_id} não encontrado ou inativo'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar se está em grupo de isenção
        if employee.is_in_exemption_group():
            return Response({
                'status': 'success',
                'data': {
                    'can_access': True,
                    'reason': 'Funcionário isento de interjornada',
                    'return_time': None,
                    'employee': EmployeeSerializer(employee).data,
                    'session': None,
                    'time_remaining': None
                }
            })
        
        # Funcionalidade de sessão movida para apps.employee_sessions
        return Response({
            'status': 'success',
            'data': {
                'can_access': True,
                'reason': 'Funcionalidade de sessão movida para apps.employee_sessions',
                'return_time': None,
                'employee': EmployeeSerializer(employee).data,
                'session': None,
                'time_remaining': None
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar acesso do funcionário: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


