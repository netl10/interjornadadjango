"""
Views para o app dashboard.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.employees.models import Employee
from apps.employee_sessions.models import EmployeeSession
from apps.interjornada.models import InterjornadaCycle, InterjornadaViolation
from apps.devices.models import Device
from apps.core.utils import TimezoneUtils
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """
    View principal do dashboard.
    """
    return render(request, 'dashboard/index.html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    """
    Retorna dados para o dashboard.
    """
    try:
        # Estatísticas gerais
        total_employees = Employee.objects.filter(is_active=True).count()
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
        
        # Últimas atividades
        recent_sessions = EmployeeSession.objects.select_related('employee').order_by('-updated_at')[:10]
        recent_violations = InterjornadaViolation.objects.select_related(
            'cycle__employee'
        ).order_by('-violation_time')[:5]
        
        # Dados dos funcionários bloqueados
        blocked_sessions = EmployeeSession.objects.filter(
            state='blocked'
        ).select_related('employee').order_by('return_time')
        
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
        
        # Dados das sessões ativas
        active_sessions_data = []
        for session in EmployeeSession.objects.filter(
            state__in=['active', 'pending_rest']
        ).select_related('employee'):
            active_sessions_data.append({
                'employee_id': session.employee.device_id,
                'employee_name': session.employee.name,
                'state': session.state,
                'first_access': session.display_first_access,
                'last_access': session.display_last_access,
            })
        
        return Response({
            'status': 'success',
            'data': {
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
                'recent_activities': {
                    'sessions': [
                        {
                            'employee_name': session.employee.name,
                            'state': session.get_state_display(),
                            'updated_at': TimezoneUtils.format_datetime(session.updated_at)
                        }
                        for session in recent_sessions
                    ],
                    'violations': [
                        {
                            'employee_name': violation.cycle.employee.name,
                            'violation_type': violation.get_violation_type_display(),
                            'severity': violation.get_severity_display(),
                            'violation_time': violation.display_violation_time
                        }
                        for violation in recent_violations
                    ]
                },
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do dashboard: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employee_details(request, device_id):
    """
    Retorna detalhes de um funcionário específico.
    """
    try:
        employee = Employee.objects.get(device_id=device_id, is_active=True)
        
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
        
        # Violações recentes
        recent_violations = InterjornadaViolation.objects.filter(
            cycle__employee=employee
        ).order_by('-violation_time')[:5]
        
        # Estatísticas do mês
        from datetime import date, timedelta
        month_start = date.today().replace(day=1)
        month_stats = InterjornadaStatistics.objects.filter(
            employee=employee,
            date__gte=month_start
        ).order_by('-date')
        
        employee_data = {
            'employee': {
                'id': employee.id,
                'device_id': employee.device_id,
                'name': employee.name,
                'employee_code': employee.employee_code,
                'is_exempt': employee.is_exempt,
                'groups': employee.groups,
                'effective_work_duration': employee.effective_work_duration,
                'effective_rest_duration': employee.effective_rest_duration,
            },
            'active_session': {
                'id': active_session.id if active_session else None,
                'state': active_session.state if active_session else None,
                'first_access': active_session.display_first_access if active_session else None,
                'last_access': active_session.display_last_access if active_session else None,
                'block_start': active_session.display_block_start if active_session else None,
                'return_time': active_session.display_return_time if active_session else None,
                'time_remaining': active_session.time_remaining_until_return if active_session else None,
            } if active_session else None,
            'active_cycle': {
                'id': active_cycle.id if active_cycle else None,
                'current_state': active_cycle.current_state if active_cycle else None,
                'cycle_start': TimezoneUtils.format_datetime(active_cycle.cycle_start) if active_cycle else None,
                'work_time_remaining': active_cycle.work_time_remaining if active_cycle else None,
                'rest_time_remaining': active_cycle.rest_time_remaining if active_cycle else None,
                'rule_name': active_cycle.rule.name if active_cycle else None,
            } if active_cycle else None,
            'recent_violations': [
                {
                    'id': violation.id,
                    'violation_type': violation.get_violation_type_display(),
                    'severity': violation.get_severity_display(),
                    'description': violation.description,
                    'violation_time': violation.display_violation_time,
                    'resolved': violation.resolved,
                }
                for violation in recent_violations
            ],
            'month_stats': [
                {
                    'date': stat.date.isoformat(),
                    'total_cycles': stat.total_cycles,
                    'completed_cycles': stat.completed_cycles,
                    'total_work_time': stat.work_time_formatted,
                    'total_rest_time': stat.rest_time_formatted,
                    'total_violations': stat.total_violations,
                    'completion_rate': stat.completion_rate,
                    'violation_rate': stat.violation_rate,
                }
                for stat in month_stats
            ]
        }
        
        return Response({
            'status': 'success',
            'data': employee_data
        })
        
    except Employee.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Funcionário não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do funcionário {device_id}: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_system_status(request):
    """
    Retorna status geral do sistema.
    """
    try:
        # Status dos dispositivos
        devices = Device.objects.all()
        device_status = []
        for device in devices:
            device_status.append({
                'id': device.id,
                'name': device.name,
                'device_type': device.device_type,
                'ip_address': device.ip_address,
                'port': device.port,
                'status': device.status,
                'is_connected': device.is_connected,
                'last_connection': device.last_connection.isoformat() if device.last_connection else None,
                'connection_success_rate': device.connection_success_rate,
            })
        
        # Status do monitoramento
        from apps.devices.services import device_monitoring_service
        from apps.interjornada.services import interjornada_monitoring_service
        
        monitoring_status = {
            'device_monitoring': device_monitoring_service.is_monitoring,
            'interjornada_monitoring': interjornada_monitoring_service.is_monitoring,
        }
        
        # Estatísticas de performance
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM employees_employee WHERE is_active = true")
            active_employees = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM employees_employeesession WHERE state IN ('active', 'pending_rest', 'blocked')")
            active_sessions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM interjornada_interjornadacycle WHERE current_state IN ('work', 'rest')")
            active_cycles = cursor.fetchone()[0]
        
        return Response({
            'status': 'success',
            'data': {
                'system_info': {
                    'active_employees': active_employees,
                    'active_sessions': active_sessions,
                    'active_cycles': active_cycles,
                    'total_devices': devices.count(),
                    'connected_devices': sum(1 for d in devices if d.is_connected),
                },
                'device_status': device_status,
                'monitoring_status': monitoring_status,
                'timestamp': TimezoneUtils.get_utc_now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status do sistema: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_access_denied(request):
    """
    Simula evento de acesso negado para teste do modal.
    """
    try:
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({
                'status': 'error',
                'message': 'device_id é obrigatório'
            }, status=400)
        
        employee = Employee.objects.get(device_id=device_id, is_active=True)
        
        # Buscar sessão ativa
        active_session = EmployeeSession.objects.filter(
            employee=employee,
            state='blocked'
        ).first()
        
        if not active_session:
            return Response({
                'status': 'error',
                'message': 'Funcionário não está bloqueado'
            }, status=400)
        
        # Simular evento de acesso negado
        from apps.logs.models import SystemLog
        SystemLog.log_warning(
            message=f"Simulação: Acesso negado para {employee.name}",
            category='employee',
            user_id=employee.device_id,
            user_name=employee.name,
            details={'simulated': True}
        )
        
        return Response({
            'status': 'success',
            'message': 'Evento de acesso negado simulado',
            'data': {
                'employee_name': employee.name,
                'employee_id': employee.device_id,
                'return_time': active_session.display_return_time,
                'time_remaining': active_session.time_remaining_until_return,
            }
        })
        
    except Employee.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Funcionário não encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao simular acesso negado: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """
    Retorna notificações para o dashboard.
    """
    try:
        notifications = []
        
        # Violações críticas não resolvidas
        critical_violations = InterjornadaViolation.objects.filter(
            resolved=False,
            severity='critical'
        ).select_related('cycle__employee')[:5]
        
        for violation in critical_violations:
            notifications.append({
                'type': 'critical_violation',
                'title': 'Violação Crítica',
                'message': f"{violation.cycle.employee.name}: {violation.description}",
                'timestamp': violation.display_violation_time,
                'severity': 'critical',
                'action_required': True,
            })
        
        # Dispositivos desconectados
        disconnected_devices = Device.objects.filter(
            is_enabled=True,
            status__in=['error', 'inactive']
        )[:3]
        
        for device in disconnected_devices:
            notifications.append({
                'type': 'device_disconnected',
                'title': 'Dispositivo Desconectado',
                'message': f"Dispositivo {device.name} está desconectado",
                'timestamp': TimezoneUtils.format_datetime(device.last_error) if device.last_error else 'Desconhecido',
                'severity': 'high',
                'action_required': True,
            })
        
        # Funcionários com tempo de retorno expirado
        expired_sessions = EmployeeSession.objects.filter(
            state='blocked',
            return_time__lt=TimezoneUtils.get_utc_now()
        ).select_related('employee')[:3]
        
        for session in expired_sessions:
            notifications.append({
                'type': 'expired_rest_period',
                'title': 'Período de Interjornada Expirado',
                'message': f"{session.employee.name} pode retornar ao trabalho",
                'timestamp': TimezoneUtils.format_datetime(session.return_time),
                'severity': 'medium',
                'action_required': False,
            })
        
        return Response({
            'status': 'success',
            'data': {
                'notifications': notifications,
                'total_count': len(notifications),
                'critical_count': len([n for n in notifications if n['severity'] == 'critical']),
                'high_count': len([n for n in notifications if n['severity'] == 'high']),
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter notificações: {e}")
        return Response({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }, status=500)
