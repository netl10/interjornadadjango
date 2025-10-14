"""
Views para sessões de funcionários.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from datetime import timedelta

from .models import EmployeeSession
from .services import session_service


@staff_member_required
def dashboard_sessoes(request):
    """Dashboard de sessões em tempo real."""
    return render(request, 'admin/sessions/dashboard_sessoes.html')


@staff_member_required
def api_sessoes_ativas(request):
    """API para sessões ativas (AJAX)."""
    try:
        # Buscar todas as sessões ativas
        sessoes = EmployeeSession.objects.filter(
            state__in=['active', 'blocked', 'pending_rest']
        ).select_related('employee').order_by('-created_at')
        
        # Converter para formato JSON
        sessoes_data = []
        for sessao in sessoes:
            # Calcular tempo decorrido
            tempo_decorrido = timezone.now() - sessao.first_access
            tempo_decorrido_minutos = int(tempo_decorrido.total_seconds() / 60)
            
            # Calcular tempo restante para interjornada (se ativa)
            tempo_restante_interjornada = None
            if sessao.state == 'active':
                tempo_limite = sessao.first_access + timedelta(minutes=sessao.work_duration_minutes)
                if timezone.now() < tempo_limite:
                    tempo_restante = tempo_limite - timezone.now()
                    tempo_restante_interjornada = int(tempo_restante.total_seconds() / 60)
            
            # Calcular tempo restante para sair da interjornada (se bloqueado)
            tempo_restante_liberacao = None
            if sessao.state == 'blocked' and sessao.return_time:
                if timezone.now() < sessao.return_time:
                    tempo_restante = sessao.return_time - timezone.now()
                    tempo_restante_liberacao = int(tempo_restante.total_seconds() / 60)
                else:
                    tempo_restante_liberacao = 0  # Já pode sair
            
            # Usar timestamps originais (já estão no horário local correto)
            first_access_local = sessao.first_access
            last_access_local = sessao.last_access
            block_start_local = sessao.block_start
            return_time_local = sessao.return_time
            created_at_local = sessao.created_at
            
            sessoes_data.append({
                'id': sessao.id,
                'employee_id': sessao.employee.device_id,
                'employee_name': sessao.employee.name,
                'state': sessao.state,
                'state_display': sessao.get_state_display(),
                'first_access': sessao.display_first_access,
                'last_access': sessao.display_last_access,
                'block_start': sessao.display_block_start,
                'return_time': sessao.display_return_time,
                'work_duration_minutes': sessao.work_duration_minutes,
                'rest_duration_minutes': sessao.rest_duration_minutes,
                'tempo_decorrido_minutos': tempo_decorrido_minutos,
                'tempo_restante_interjornada': tempo_restante_interjornada,
                'tempo_restante_liberacao': tempo_restante_liberacao,
                'created_at': created_at_local.strftime('%Y-%m-%dT%H:%M:%S'),
            })
        
        return JsonResponse({
            'success': True,
            'sessoes': sessoes_data,
            'total_sessoes': len(sessoes_data),
            'timestamp': timezone.now().isoformat(),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        })