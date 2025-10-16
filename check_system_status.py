#!/usr/bin/env python
"""
Script para verificar o status atual do sistema
"""
import os
import sys
import django
from django.utils import timezone

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.employees.models import Employee, EmployeeGroup
from apps.employee_sessions.models import EmployeeSession
from apps.devices.device_client import DeviceClient

def check_system_status():
    """Verifica o status atual do sistema"""
    print("=== STATUS ATUAL DO SISTEMA ===\n")
    
    # Verificar grupos
    print("📊 Grupos no sistema:")
    groups = EmployeeGroup.objects.all()
    for group in groups:
        print(f"   - {group.name} (ID: {group.device_group_id}, Blacklist: {group.is_blacklist})")
    
    # Verificar usuários
    print(f"\n👥 Usuários:")
    total_users = Employee.objects.count()
    users_with_group = Employee.objects.filter(group__isnull=False).count()
    users_without_group = Employee.objects.filter(group__isnull=True).count()
    
    print(f"   - Total: {total_users}")
    print(f"   - Com grupo: {users_with_group}")
    print(f"   - Sem grupo: {users_without_group}")
    
    # Verificar usuários na blacklist
    blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
    if blacklist_group:
        blacklist_users = Employee.objects.filter(group=blacklist_group).count()
        print(f"   - Na blacklist: {blacklist_users}")
    else:
        print(f"   - Na blacklist: 0 (grupo não encontrado)")
    
    # Verificar sessões
    print(f"\n🔒 Sessões:")
    active_sessions = EmployeeSession.objects.filter(state='active').count()
    blocked_sessions = EmployeeSession.objects.filter(state='blocked').count()
    pending_rest_sessions = EmployeeSession.objects.filter(state='pending_rest').count()
    
    print(f"   - Ativas: {active_sessions}")
    print(f"   - Bloqueadas: {blocked_sessions}")
    print(f"   - Aguardando saída: {pending_rest_sessions}")
    
    # Verificar sessões expiradas
    now = timezone.now()
    expired_sessions = EmployeeSession.objects.filter(
        state='blocked',
        return_time__lte=now
    ).count()
    print(f"   - Expiradas (deveriam ser liberadas): {expired_sessions}")
    
    # Testar conexão com catraca
    print(f"\n🔌 Teste de conexão com catraca:")
    try:
        client = DeviceClient()
        if client.login():
            print("   ✅ Conexão com catraca: OK")
            
            # Verificar grupos na catraca
            groups = client.get_groups()
            if groups:
                print(f"   📊 Grupos na catraca: {len(groups)}")
                for group in groups:
                    group_id = group.get('id')
                    group_name = group.get('name', 'N/A')
                    users_count = len(client.get_user_groups(group_id)) if group_id else 0
                    print(f"      - {group_name} (ID: {group_id}): {users_count} usuários")
            else:
                print("   ❌ Falha ao obter grupos da catraca")
        else:
            print("   ❌ Falha ao conectar com catraca")
    except Exception as e:
        print(f"   ❌ Erro ao testar catraca: {e}")
    
    # Verificar inconsistências
    print(f"\n🔍 Verificando inconsistências:")
    
    # Usuários na blacklist sem sessão bloqueada
    if blacklist_group:
        inconsistent_blacklist = Employee.objects.filter(
            group=blacklist_group
        ).exclude(
            id__in=EmployeeSession.objects.filter(state='blocked').values_list('employee_id', flat=True)
        ).count()
        print(f"   - Usuários na blacklist sem sessão bloqueada: {inconsistent_blacklist}")
    
    # Sessões bloqueadas sem usuário na blacklist
    if blacklist_group:
        inconsistent_sessions = EmployeeSession.objects.filter(
            state='blocked'
        ).exclude(
            employee__group=blacklist_group
        ).count()
        print(f"   - Sessões bloqueadas sem usuário na blacklist: {inconsistent_sessions}")
    
    # Sessões expiradas que deveriam ser liberadas
    if expired_sessions > 0:
        print(f"   ⚠️  {expired_sessions} sessões expiradas que deveriam ser liberadas automaticamente")
    
    print(f"\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_system_status()
