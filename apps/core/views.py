"""
Views para configurações do sistema.
"""
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import SystemConfiguration


@staff_member_required
def configuracao_sistema(request):
    """Página de configuração do sistema."""
    
    # Obter configuração ativa
    config = SystemConfiguration.get_active_config()
    
    if request.method == 'POST':
        try:
            # Atualizar configurações
            config.device_ip = request.POST.get('device_ip', config.device_ip)
            config.device_port = int(request.POST.get('device_port', config.device_port))
            config.device_username = request.POST.get('device_username', config.device_username)
            config.device_password = request.POST.get('device_password', config.device_password)
            
            # Dispositivo secundário
            secondary_ip = request.POST.get('secondary_device_ip', '')
            config.secondary_device_ip = secondary_ip if secondary_ip else None
            secondary_port = request.POST.get('secondary_device_port', '')
            config.secondary_device_port = int(secondary_port) if secondary_port else None
            config.secondary_device_username = request.POST.get('secondary_device_username', '')
            config.secondary_device_password = request.POST.get('secondary_device_password', '')
            
            # Timezone e tempo
            config.timezone_offset = int(request.POST.get('timezone_offset', config.timezone_offset))
            config.giro_validation_timeout = int(request.POST.get('giro_validation_timeout', config.giro_validation_timeout))
            config.monitor_interval = int(request.POST.get('monitor_interval', config.monitor_interval))
            
            # Interjornada
            config.liberado_minutes = int(request.POST.get('liberado_minutes', config.liberado_minutes))
            config.bloqueado_minutes = int(request.POST.get('bloqueado_minutes', config.bloqueado_minutes))
            config.exemption_group_name = request.POST.get('exemption_group_name', config.exemption_group_name)
            
            # Reinícios
            restart_1 = request.POST.get('restart_time_1', '')
            config.restart_time_1 = restart_1 if restart_1 else None
            restart_2 = request.POST.get('restart_time_2', '')
            config.restart_time_2 = restart_2 if restart_2 else None
            restart_3 = request.POST.get('restart_time_3', '')
            config.restart_time_3 = restart_3 if restart_3 else None
            restart_4 = request.POST.get('restart_time_4', '')
            config.restart_time_4 = restart_4 if restart_4 else None
            
            # Segurança e logs
            config.ssl_verify = request.POST.get('ssl_verify') == 'on'
            config.max_logs_per_request = int(request.POST.get('max_logs_per_request', config.max_logs_per_request))
            
            # Salvar
            config.save()
            
            messages.success(request, '✅ Configurações salvas com sucesso!')
            return redirect('core:configuracao_sistema')
            
        except Exception as e:
            messages.error(request, f'❌ Erro ao salvar configurações: {e}')
    
    context = {
        'config': config,
        'timezone_options': [
            (-12, 'UTC-12'),
            (-11, 'UTC-11'),
            (-10, 'UTC-10'),
            (-9, 'UTC-9'),
            (-8, 'UTC-8'),
            (-7, 'UTC-7'),
            (-6, 'UTC-6'),
            (-5, 'UTC-5'),
            (-4, 'UTC-4'),
            (-3, 'UTC-3 (Brasil)'),
            (-2, 'UTC-2'),
            (-1, 'UTC-1'),
            (0, 'UTC'),
            (1, 'UTC+1'),
            (2, 'UTC+2'),
            (3, 'UTC+3'),
            (4, 'UTC+4'),
            (5, 'UTC+5'),
            (6, 'UTC+6'),
            (7, 'UTC+7'),
            (8, 'UTC+8'),
            (9, 'UTC+9'),
            (10, 'UTC+10'),
            (11, 'UTC+11'),
            (12, 'UTC+12'),
            (13, 'UTC+13'),
            (14, 'UTC+14'),
        ]
    }
    
    return render(request, 'admin/core/configuracao_sistema.html', context)


@staff_member_required
@require_http_methods(["POST"])
def test_device_connection(request):
    """Testa conexão com o dispositivo."""
    try:
        data = json.loads(request.body)
        device_ip = data.get('device_ip')
        device_port = data.get('device_port')
        device_username = data.get('device_username')
        device_password = data.get('device_password')
        
        if not all([device_ip, device_port, device_username, device_password]):
            return JsonResponse({
                'success': False,
                'message': 'Todos os campos de conexão são obrigatórios'
            })
        
        # Importar cliente de dispositivo
        from apps.devices.device_client import DeviceClient
        
        # Criar cliente temporário para teste
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Testar conexão básica
        url = f"https://{device_ip}:{device_port}/api/login"
        if device_port == 80:
            url = f"http://{device_ip}:{device_port}/api/login"
        
        session = requests.Session()
        session.verify = False
        
        login_data = {
            'username': device_username,
            'password': device_password
        }
        
        response = session.post(url, json=login_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'session' in data:
                return JsonResponse({
                    'success': True,
                    'message': 'Conexão bem-sucedida! Dispositivo respondeu corretamente.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Dispositivo respondeu, mas credenciais podem estar incorretas'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Erro de conexão: {response.status_code}'
            })
            
    except requests.exceptions.ConnectTimeout:
        return JsonResponse({
            'success': False,
            'message': 'Timeout de conexão. Verifique o IP e porta.'
        })
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'success': False,
            'message': 'Erro de conexão. Verifique se o dispositivo está ligado e acessível.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro inesperado: {str(e)}'
        })


@staff_member_required
def configuracao_help(request):
    """Página de ajuda para configurações."""
    return render(request, 'admin/core/configuracao_help.html')