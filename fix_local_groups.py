#!/usr/bin/env python
"""
Script para corrigir grupos de usuários apenas no sistema local
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

def fix_local_groups():
    """Corrige grupos de usuários apenas no sistema local"""
    print("=== CORRIGINDO GRUPOS NO SISTEMA LOCAL ===\n")
    
    # Buscar grupo padrão
    default_group = EmployeeGroup.objects.filter(name='GRUPO_PADRAO').first()
    if not default_group:
        print("❌ Grupo padrão não encontrado")
        return
    
    print(f"📊 Grupo padrão: {default_group.name}")
    
    # Buscar usuários que podem estar com grupos incorretos
    print(f"\n👥 Verificando usuários no sistema local...")
    
    # Usuários sem grupo
    users_without_group = Employee.objects.filter(group__isnull=True)
    print(f"📊 Usuários sem grupo: {users_without_group.count()}")
    
    # Usuários na blacklist
    blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
    if blacklist_group:
        users_in_blacklist = Employee.objects.filter(group=blacklist_group)
        print(f"📊 Usuários na blacklist local: {users_in_blacklist.count()}")
    else:
        users_in_blacklist = Employee.objects.none()
        print("📊 Grupo de blacklist não encontrado")
    
    # Sessões bloqueadas
    blocked_sessions = EmployeeSession.objects.filter(state='blocked')
    print(f"📊 Sessões bloqueadas: {blocked_sessions.count()}")
    
    # Corrigir usuários sem grupo
    fixed_count = 0
    if users_without_group.exists():
        print(f"\n🔧 Corrigindo usuários sem grupo...")
        for user in users_without_group:
            try:
                user.group = default_group
                user.save(update_fields=['group'])
                print(f"   ✅ {user.name} (ID: {user.device_id}) - Grupo definido como padrão")
                fixed_count += 1
            except Exception as e:
                print(f"   ❌ Erro ao corrigir {user.name}: {e}")
    
    # Corrigir usuários na blacklist local
    if users_in_blacklist.exists():
        print(f"\n🔧 Corrigindo usuários na blacklist local...")
        for user in users_in_blacklist:
            try:
                # Verificar se tem sessão bloqueada
                session = EmployeeSession.objects.filter(employee=user, state='blocked').first()
                if not session:
                    # Não tem sessão bloqueada - mover para grupo padrão
                    user.group = default_group
                    user.original_group = None
                    user.save(update_fields=['group', 'original_group'])
                    print(f"   ✅ {user.name} (ID: {user.device_id}) - Movido para grupo padrão")
                    fixed_count += 1
                else:
                    print(f"   ⚠️  {user.name} (ID: {user.device_id}) - Tem sessão bloqueada, mantendo na blacklist")
            except Exception as e:
                print(f"   ❌ Erro ao corrigir {user.name}: {e}")
    
    # Limpar sessões bloqueadas expiradas
    expired_count = 0
    if blocked_sessions.exists():
        print(f"\n🔧 Verificando sessões bloqueadas expiradas...")
        now = timezone.now()
        
        for session in blocked_sessions:
            if session.return_time and now >= session.return_time:
                try:
                    # Restaurar do blacklist
                    from apps.employees.group_service import group_service
                    blacklist_success = group_service.restore_from_blacklist(session.employee)
                    
                    # Deletar sessão
                    session.delete()
                    
                    print(f"   ✅ {session.employee.name} - Sessão expirada removida (blacklist: {blacklist_success})")
                    expired_count += 1
                except Exception as e:
                    print(f"   ❌ Erro ao remover sessão de {session.employee.name}: {e}")
        
        if expired_count == 0:
            print(f"   ℹ️  Nenhuma sessão expirada encontrada")
    
    print(f"\n📈 Resumo:")
    print(f"   - Usuários corrigidos: {fixed_count}")
    print(f"   - Sessões expiradas removidas: {expired_count}")
    
    # Verificação final
    print(f"\n🔍 Verificação final:")
    final_users_without_group = Employee.objects.filter(group__isnull=True).count()
    final_users_in_blacklist = Employee.objects.filter(group=blacklist_group).count() if blacklist_group else 0
    final_blocked_sessions = EmployeeSession.objects.filter(state='blocked').count()
    
    print(f"   - Usuários sem grupo: {final_users_without_group}")
    print(f"   - Usuários na blacklist: {final_users_in_blacklist}")
    print(f"   - Sessões bloqueadas: {final_blocked_sessions}")
    
    print(f"\n=== OPERAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_local_groups()
