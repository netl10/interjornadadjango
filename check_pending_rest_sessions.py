#!/usr/bin/env python
"""
Script para verificar sessões em pending_rest
"""
import os
import sys
import django
from django.utils import timezone

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.employees.models import Employee
from apps.employee_sessions.models import EmployeeSession
from apps.core.models import SystemConfiguration

def check_pending_rest_sessions():
    """Verifica sessões em pending_rest"""
    print("=== VERIFICAÇÃO DE SESSÕES PENDING_REST ===\n")
    
    # Buscar sessões em pending_rest
    pending_sessions = EmployeeSession.objects.filter(state='pending_rest').select_related('employee')
    
    if not pending_sessions.exists():
        print("ℹ️  Nenhuma sessão em pending_rest encontrada")
        return
    
    print(f"📊 Sessões em pending_rest: {pending_sessions.count()}")
    
    # Obter configuração do sistema
    config = SystemConfiguration.objects.get(id=1)
    now = timezone.now()
    
    for session in pending_sessions:
        print(f"\n👤 {session.employee.name} (ID: {session.employee.device_id})")
        print(f"   - Estado: {session.state}")
        print(f"   - Primeiro acesso: {session.first_access}")
        print(f"   - Último acesso: {session.last_access}")
        print(f"   - Grupo atual: {session.employee.group}")
        print(f"   - Grupo original: {session.employee.original_group}")
        
        # Calcular tempos
        time_since_first = now - session.first_access
        time_since_last = now - session.last_access
        
        print(f"   - Tempo desde primeiro acesso: {time_since_first}")
        print(f"   - Tempo desde último acesso: {time_since_last}")
        
        # Verificar se deveria ser bloqueado
        work_time_limit = session.first_access + timezone.timedelta(minutes=config.liberado_minutes)
        if now > work_time_limit:
            time_over_limit = now - work_time_limit
            print(f"   ⚠️  EXCEDEU TEMPO DE TRABALHO: {time_over_limit}")
            print(f"   - Deveria estar bloqueado há: {time_over_limit}")
        else:
            time_remaining = work_time_limit - now
            print(f"   ✅ Ainda dentro do tempo de trabalho: {time_remaining}")
    
    # Testar o método enforce_session_timeouts
    print(f"\n🔧 Testando enforce_session_timeouts...")
    try:
        from apps.employee_sessions.services import session_service
        session_service.enforce_session_timeouts()
        print("   ✅ enforce_session_timeouts executado com sucesso")
        
        # Verificar se alguma sessão foi alterada
        updated_pending = EmployeeSession.objects.filter(state='pending_rest').count()
        updated_blocked = EmployeeSession.objects.filter(state='blocked').count()
        
        print(f"   - Sessões pending_rest após execução: {updated_pending}")
        print(f"   - Sessões bloqueadas após execução: {updated_blocked}")
        
    except Exception as e:
        print(f"   ❌ Erro ao executar enforce_session_timeouts: {e}")
    
    print(f"\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_pending_rest_sessions()
