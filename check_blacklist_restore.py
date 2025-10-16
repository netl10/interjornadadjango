#!/usr/bin/env python
"""
Script para verificar o status da restauração da blacklist
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
from apps.employees.group_service import group_service

def check_blacklist_restore():
    """Verifica o status da restauração da blacklist"""
    print("=== VERIFICAÇÃO DE RESTAURAÇÃO DA BLACKLIST ===\n")
    
    # Verificar usuários na blacklist
    blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
    if not blacklist_group:
        print("❌ Grupo de blacklist não encontrado")
        return
    
    print(f"📊 Grupo de blacklist: {blacklist_group.name} (ID: {blacklist_group.device_group_id})")
    
    # Usuários na blacklist
    blacklist_users = Employee.objects.filter(group=blacklist_group)
    print(f"👥 Usuários na blacklist: {blacklist_users.count()}")
    
    for user in blacklist_users:
        print(f"   - {user.name} (ID: {user.device_id})")
        print(f"     Grupo atual: {user.group}")
        print(f"     Grupo original: {user.original_group}")
        
        # Verificar sessão
        session = EmployeeSession.objects.filter(employee=user, state='blocked').first()
        if session:
            print(f"     Sessão: {session.state} - Retorna em: {session.return_time}")
            if timezone.now() >= session.return_time:
                print(f"     ⚠️  SESSÃO EXPIRADA - Deveria ser liberado!")
            else:
                time_remaining = session.return_time - timezone.now()
                print(f"     ⏰ Tempo restante: {time_remaining}")
        else:
            print(f"     ❌ SEM SESSÃO BLOQUEADA - Deveria ser removido da blacklist!")
        print()
    
    # Verificar sessões bloqueadas
    blocked_sessions = EmployeeSession.objects.filter(state='blocked').select_related('employee')
    print(f"🔒 Sessões bloqueadas: {blocked_sessions.count()}")
    
    for session in blocked_sessions:
        print(f"   - {session.employee.name} (ID: {session.employee.device_id})")
        print(f"     Grupo atual: {session.employee.group}")
        print(f"     Grupo original: {session.employee.original_group}")
        print(f"     Retorna em: {session.return_time}")
        
        if timezone.now() >= session.return_time:
            print(f"     ⚠️  SESSÃO EXPIRADA - Deveria ser liberado!")
        else:
            time_remaining = session.return_time - timezone.now()
            print(f"     ⏰ Tempo restante: {time_remaining}")
        print()
    
    # Verificar inconsistências
    print("🔍 Verificando inconsistências:")
    
    # Usuários na blacklist sem sessão bloqueada
    inconsistent_blacklist = []
    for user in blacklist_users:
        session = EmployeeSession.objects.filter(employee=user, state='blocked').first()
        if not session:
            inconsistent_blacklist.append(user)
    
    if inconsistent_blacklist:
        print(f"   ❌ {len(inconsistent_blacklist)} usuários na blacklist sem sessão bloqueada:")
        for user in inconsistent_blacklist:
            print(f"      - {user.name}")
    else:
        print("   ✅ Todos os usuários na blacklist têm sessão bloqueada")
    
    # Sessões bloqueadas sem usuário na blacklist
    inconsistent_sessions = []
    for session in blocked_sessions:
        if session.employee.group != blacklist_group:
            inconsistent_sessions.append(session)
    
    if inconsistent_sessions:
        print(f"   ❌ {len(inconsistent_sessions)} sessões bloqueadas sem usuário na blacklist:")
        for session in inconsistent_sessions:
            print(f"      - {session.employee.name} (grupo: {session.employee.group})")
    else:
        print("   ✅ Todas as sessões bloqueadas têm usuários na blacklist")
    
    print(f"\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_blacklist_restore()
