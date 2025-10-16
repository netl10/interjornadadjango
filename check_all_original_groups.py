#!/usr/bin/env python
"""
Script para verificar e corrigir grupos originais de todos os usuários
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

def check_all_original_groups():
    """Verifica e corrige grupos originais de todos os usuários"""
    print("=== VERIFICAÇÃO DE GRUPOS ORIGINAIS ===\n")
    
    # Buscar grupo padrão
    default_group = EmployeeGroup.objects.filter(name='GRUPO_PADRAO').first()
    if not default_group:
        print("❌ Grupo padrão não encontrado")
        return
    
    print(f"📊 Grupo padrão: {default_group.name}")
    
    # Buscar usuários sem grupo original
    users_without_original = Employee.objects.filter(original_group__isnull=True)
    print(f"👥 Usuários sem grupo original: {users_without_original.count()}")
    
    if users_without_original.exists():
        print(f"\n🔧 Corrigindo grupos originais...")
        fixed_count = 0
        
        for user in users_without_original:
            try:
                # Definir grupo padrão como original
                user.original_group = default_group
                user.save(update_fields=['original_group'])
                print(f"   ✅ {user.name} (ID: {user.device_id}) - Grupo original definido")
                fixed_count += 1
            except Exception as e:
                print(f"   ❌ Erro ao corrigir {user.name}: {e}")
        
        print(f"\n📈 Resumo da correção:")
        print(f"   - Usuários corrigidos: {fixed_count}")
    
    # Verificar usuários na blacklist
    blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
    if blacklist_group:
        blacklist_users = Employee.objects.filter(group=blacklist_group)
        print(f"\n🚫 Usuários na blacklist: {blacklist_users.count()}")
        
        for user in blacklist_users:
            print(f"\n👤 {user.name} (ID: {user.device_id})")
            print(f"   - Grupo atual: {user.group}")
            print(f"   - Grupo original: {user.original_group}")
            
            # Verificar sessão
            session = EmployeeSession.objects.filter(employee=user, state='blocked').first()
            if session:
                print(f"   - Sessão: {session.state}")
                print(f"   - Bloqueado desde: {session.block_start}")
                print(f"   - Retorna em: {session.return_time}")
                
                if session.return_time:
                    now = timezone.now()
                    if now >= session.return_time:
                        time_over = now - session.return_time
                        print(f"   ⚠️  SESSÃO EXPIRADA há: {time_over}")
                        
                        # Tentar restaurar
                        if user.original_group:
                            print(f"   🔧 Tentando restaurar da blacklist...")
                            from apps.employees.group_service import group_service
                            restore_success = group_service.restore_from_blacklist(user)
                            
                            if restore_success:
                                print(f"   ✅ {user.name} restaurado da blacklist!")
                            else:
                                print(f"   ❌ Falha ao restaurar {user.name}")
                        else:
                            print(f"   ❌ Não pode restaurar - sem grupo original")
                    else:
                        time_remaining = session.return_time - now
                        print(f"   ⏰ Tempo restante: {time_remaining}")
            else:
                print(f"   ❌ SEM SESSÃO BLOQUEADA - Deveria ser removido da blacklist")
                
                # Remover da blacklist se não tem sessão
                if user.original_group:
                    print(f"   🔧 Removendo da blacklist (sem sessão)...")
                    from apps.employees.group_service import group_service
                    restore_success = group_service.restore_from_blacklist(user)
                    
                    if restore_success:
                        print(f"   ✅ {user.name} removido da blacklist!")
                    else:
                        print(f"   ❌ Falha ao remover {user.name}")
                else:
                    print(f"   ❌ Não pode remover - sem grupo original")
    
    # Verificação final
    print(f"\n🔍 Verificação final:")
    final_without_original = Employee.objects.filter(original_group__isnull=True).count()
    final_in_blacklist = Employee.objects.filter(group=blacklist_group).count() if blacklist_group else 0
    
    print(f"   - Usuários sem grupo original: {final_without_original}")
    print(f"   - Usuários na blacklist: {final_in_blacklist}")
    
    print(f"\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_all_original_groups()
