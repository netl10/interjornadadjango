"""
Views para logs de acesso.
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import AccessLog, SystemLog
from .services import log_monitor_service
from apps.employees.models import Employee


@staff_member_required
def historico_acessos(request):
    """Página de histórico de acessos."""
    
    # Parâmetros de filtro
    search = request.GET.get('search', '')
    event_type = request.GET.get('event_type', '')
    portal_id = request.GET.get('portal_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_id = request.GET.get('user_id', '')
    
    # Query base
    logs = AccessLog.objects.all().order_by('-device_timestamp')
    
    # Aplicar filtros
    if search:
        logs = logs.filter(
            Q(user_name__icontains=search) |
            Q(user_id__icontains=search) |
            Q(device_log_id__icontains=search)
        )
    
    if event_type:
        logs = logs.filter(event_type=event_type)
    
    if portal_id:
        logs = logs.filter(portal_id=portal_id)
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            logs = logs.filter(device_timestamp__date__gte=date_from_obj.date())
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            logs = logs.filter(device_timestamp__date__lte=date_to_obj.date())
        except ValueError:
            pass
    
    # Paginação
    paginator = Paginator(logs, 50)  # 50 logs por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    total_logs = logs.count()
    today_logs = logs.filter(device_timestamp__date=timezone.now().date()).count()
    
    # Logs por evento
    event_stats = {}
    for event_type, event_name in AccessLog.EVENT_TYPES:
        count = logs.filter(event_type=event_type).count()
        if count > 0:
            event_stats[event_name] = count
    
    # Logs por portal
    portal_stats = {}
    portal_1_count = logs.filter(portal_id=1).count()
    portal_2_count = logs.filter(portal_id=2).count()
    if portal_1_count > 0:
        portal_stats['Portal 1 (Entrada)'] = portal_1_count
    if portal_2_count > 0:
        portal_stats['Portal 2 (Saída)'] = portal_2_count
    
    # Top usuários
    top_users = {}
    for log in logs[:100]:  # Apenas os primeiros 100 para performance
        user_name = log.user_name
        if user_name not in top_users:
            top_users[user_name] = 0
        top_users[user_name] += 1
    
    # Ordenar top usuários
    top_users = dict(sorted(top_users.items(), key=lambda x: x[1], reverse=True)[:10])
    
    context = {
        'page_obj': page_obj,
        'total_logs': total_logs,
        'today_logs': today_logs,
        'event_stats': event_stats,
        'portal_stats': portal_stats,
        'top_users': top_users,
        'search': search,
        'event_type': event_type,
        'portal_id': portal_id,
        'date_from': date_from,
        'date_to': date_to,
        'user_id': user_id,
        'event_types': AccessLog.EVENT_TYPES,
    }
    
    return render(request, 'admin/logs/historico_acessos.html', context)


@staff_member_required
def dashboard_sessoes(request):
    """Dashboard de sessões em tempo real."""
    return render(request, 'admin/logs/dashboard_sessoes.html')

@staff_member_required
def dashboard_logs(request):
    """Dashboard com estatísticas dos logs."""
    
    # Período padrão: últimos 7 dias
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    # Logs dos últimos 7 dias
    recent_logs = AccessLog.objects.filter(
        device_timestamp__range=[start_date, end_date]
    )
    
    # Estatísticas gerais
    total_logs = recent_logs.count()
    unique_users = recent_logs.values('user_id').distinct().count()
    
    # Logs por dia
    daily_stats = {}
    for i in range(7):
        date = (end_date - timedelta(days=i)).date()
        count = recent_logs.filter(device_timestamp__date=date).count()
        daily_stats[date.strftime('%d/%m')] = count
    
    # Logs por hora (últimas 24 horas)
    hourly_stats = {}
    for i in range(24):
        hour = (end_date - timedelta(hours=i)).hour
        count = recent_logs.filter(
            device_timestamp__hour=hour,
            device_timestamp__date=end_date.date()
        ).count()
        hourly_stats[f"{hour:02d}:00"] = count
    
    # Eventos mais comuns
    event_stats = {}
    for event_type, event_name in AccessLog.EVENT_TYPES:
        count = recent_logs.filter(event_type=event_type).count()
        if count > 0:
            event_stats[event_name] = count
    
    # Usuários mais ativos
    user_stats = {}
    for log in recent_logs:
        user_name = log.user_name
        if user_name not in user_stats:
            user_stats[user_name] = 0
        user_stats[user_name] += 1
    
    # Top 10 usuários
    top_users = dict(sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:10])
    
    context = {
        'total_logs': total_logs,
        'unique_users': unique_users,
        'daily_stats': daily_stats,
        'hourly_stats': hourly_stats,
        'event_stats': event_stats,
        'top_users': top_users,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin/logs/dashboard_sessoes.html', context)


@staff_member_required
def api_logs_stats(request):
    """API para estatísticas dos logs (AJAX)."""
    
    # Logs das últimas 24 horas
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=24)
    
    logs = AccessLog.objects.filter(
        device_timestamp__range=[start_time, end_time]
    )
    
    # Estatísticas por hora
    hourly_data = []
    for i in range(24):
        hour = (end_time - timedelta(hours=i)).hour
        count = logs.filter(device_timestamp__hour=hour).count()
        hourly_data.append({
            'hour': f"{hour:02d}:00",
            'count': count
        })
    
    # Estatísticas por evento
    event_data = []
    for event_type, event_name in AccessLog.EVENT_TYPES:
        count = logs.filter(event_type=event_type).count()
        if count > 0:
            event_data.append({
                'event': event_name,
                'count': count
            })
    
    return JsonResponse({
        'hourly_data': hourly_data,
        'event_data': event_data,
        'total_logs': logs.count(),
        'unique_users': logs.values('user_id').distinct().count(),
    })


@staff_member_required
def monitor_control(request):
    """Página de controle do monitoramento automático."""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start':
            success = log_monitor_service.start_monitoring()
            if success:
                return JsonResponse({'success': True, 'message': 'Monitoramento iniciado com sucesso!'})
            else:
                return JsonResponse({'success': False, 'message': 'Falha ao iniciar monitoramento'})
        
        elif action == 'stop':
            log_monitor_service.stop_monitoring()
            return JsonResponse({'success': True, 'message': 'Monitoramento parado com sucesso!'})
        
        elif action == 'restart':
            log_monitor_service.stop_monitoring()
            time.sleep(2)  # Aguardar parada completa
            success = log_monitor_service.start_monitoring()
            if success:
                return JsonResponse({'success': True, 'message': 'Monitoramento reiniciado com sucesso!'})
            else:
                return JsonResponse({'success': False, 'message': 'Falha ao reiniciar monitoramento'})
    
    # Obter status do monitoramento
    status = log_monitor_service.get_status()
    
    # Estatísticas dos logs
    total_logs = AccessLog.objects.count()
    recent_logs = AccessLog.objects.filter(
        device_timestamp__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    context = {
        'status': status,
        'total_logs': total_logs,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'admin/logs/monitor_control.html', context)


@staff_member_required
def api_monitor_status(request):
    """API para status do monitoramento (AJAX)."""
    status = log_monitor_service.get_status()
    
    # Adicionar estatísticas
    total_logs = AccessLog.objects.count()
    recent_logs = AccessLog.objects.filter(
        device_timestamp__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    status.update({
        'total_logs': total_logs,
        'recent_logs': recent_logs,
    })
    
    return JsonResponse(status)

@staff_member_required
def realtime_monitor(request):
    """Página de monitor em tempo real."""
    return render(request, 'admin/logs/realtime_monitor.html')

@staff_member_required
def api_realtime_logs(request):
    """API para logs em tempo real (AJAX)."""
    try:
        from django.conf import settings
        
        # Parâmetros da requisição
        limit = int(request.GET.get('limit', 20))
        last_id = int(request.GET.get('last_id', 0))
        
        # Buscar logs mais recentes (ordenados por timestamp para mostrar os mais recentes primeiro)
        if last_id > 0:
            # Se last_id for fornecido, buscar logs com timestamp mais recente que o último log conhecido
            last_log = AccessLog.objects.filter(device_log_id=last_id).first()
            if last_log:
                logs = AccessLog.objects.filter(
                    device_timestamp__gt=last_log.device_timestamp
                ).order_by('-device_timestamp')[:limit]
            else:
                logs = AccessLog.objects.order_by('-device_timestamp')[:limit]
        else:
            logs = AccessLog.objects.order_by('-device_timestamp')[:limit]
        
        # Converter para formato JSON
        logs_data = []
        
        for log in logs:
            # Determinar descrição do evento baseada no event_type se event_description estiver vazio
            event_description = log.event_description
            if not event_description or event_description.strip() == '':
                # Mapear event_type para descrição
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
            
            # Usar timestamps originais (já estão no horário local correto)
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
        
        # Status do monitor
        monitor_status = log_monitor_service.get_status()
        
        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'monitor_status': monitor_status,
            'total_logs': AccessLog.objects.count(),
            'timestamp': timezone.now().isoformat(),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        })


def api_logs_publicos(request):
    """API pública para logs (sem autenticação)."""
    try:
        # Parâmetros da requisição
        limit = int(request.GET.get('limit', 10))
        last_id = int(request.GET.get('last_id', 0))
        
        # Buscar logs mais recentes
        if last_id > 0:
            last_log = AccessLog.objects.filter(device_log_id=last_id).first()
            if last_log:
                logs = AccessLog.objects.filter(
                    device_timestamp__gt=last_log.device_timestamp
                ).order_by('-device_timestamp')[:limit]
            else:
                logs = AccessLog.objects.order_by('-device_timestamp')[:limit]
        else:
            logs = AccessLog.objects.order_by('-device_timestamp')[:limit]
        
        # Converter para formato JSON
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
        
        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'total_logs': AccessLog.objects.count(),
            'timestamp': timezone.now().isoformat(),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        })

