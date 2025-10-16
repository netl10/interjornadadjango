#!/usr/bin/env python
"""
Script para remover usuários da blacklist na catraca e colocá-los no grupo padrão
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
from apps.devices.device_client import DeviceClient

def remove_users_from_blacklist():
    """Remove usuários da blacklist na catraca e coloca no grupo padrão"""
    print("=== REMOVENDO USUÁRIOS DA BLACKLIST ===\n")
    
    try:
        # Conectar com a catraca
        client = DeviceClient()
        if not client.login():
            print("❌ Falha ao conectar com a catraca")
            return
        
        print("✅ Conectado com a catraca")
        
        # Buscar grupo de blacklist
        blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
        if not blacklist_group:
            print("❌ Grupo de blacklist não encontrado no sistema")
            return
        
        print(f"📊 Grupo de blacklist: {blacklist_group.name} (ID: {blacklist_group.device_group_id})")
        
        # Buscar grupo padrão
        default_group = EmployeeGroup.objects.filter(name='GRUPO_PADRAO').first()
        if not default_group:
            print("❌ Grupo padrão não encontrado")
            return
        
        print(f"📊 Grupo padrão: {default_group.name} (ID: {default_group.device_group_id})")
        
        # Buscar usuários na blacklist na catraca
        print(f"\n🔍 Buscando usuários na blacklist na catraca...")
        
        # Obter grupos da catraca
        groups = client.get_groups()
        if not groups:
            print("❌ Falha ao obter grupos da catraca")
            return
        
        # Encontrar grupo de blacklist na catraca
        catraca_blacklist_group = None
        for group in groups:
            if group.get('id') == blacklist_group.device_group_id:
                catraca_blacklist_group = group
                break
        
        if not catraca_blacklist_group:
            print(f"❌ Grupo de blacklist não encontrado na catraca (ID: {blacklist_group.device_group_id})")
            return
        
        print(f"✅ Grupo de blacklist encontrado na catraca: {catraca_blacklist_group.get('name', 'N/A')}")
        
        # Obter usuários do grupo de blacklist na catraca
        blacklist_users = client.get_user_groups(blacklist_group.device_group_id)
        if not blacklist_users:
            print("ℹ️  Nenhum usuário encontrado na blacklist na catraca")
            return
        
        print(f"👥 Usuários na blacklist na catraca: {len(blacklist_users)}")
        
        # Processar cada usuário
        success_count = 0
        error_count = 0
        
        for user_data in blacklist_users:
            user_id = user_data.get('id')
            user_name = user_data.get('name', f'Usuário {user_id}')
            
            print(f"\n👤 Processando: {user_name} (ID: {user_id})")
            
            try:
                # Buscar funcionário no sistema local
                employee = Employee.objects.filter(device_id=user_id).first()
                if not employee:
                    print(f"   ⚠️  Funcionário não encontrado no sistema local")
                    # Criar funcionário temporário se não existir
                    employee = Employee.objects.create(
                        device_id=user_id,
                        name=user_name,
                        is_active=True,
                        group=blacklist_group,
                        original_group=default_group
                    )
                    print(f"   ✅ Funcionário criado temporariamente")
                
                # Verificar se tem grupo original
                if not employee.original_group:
                    employee.original_group = default_group
                    employee.save(update_fields=['original_group'])
                    print(f"   ✅ Grupo original definido como padrão")
                
                # Mover usuário para grupo padrão na catraca
                print(f"   🔄 Movendo para grupo padrão na catraca...")
                move_success = client.move_user_to_group(
                    user_id, 
                    default_group.device_group_id, 
                    blacklist_group.device_group_id
                )
                
                if move_success:
                    # Atualizar no sistema local
                    employee.group = default_group
                    employee.original_group = None
                    employee.save(update_fields=['group', 'original_group'])
                    
                    # Remover sessão bloqueada se existir
                    session = EmployeeSession.objects.filter(employee=employee, state='blocked').first()
                    if session:
                        session.delete()
                        print(f"   ✅ Sessão bloqueada removida")
                    
                    print(f"   ✅ {user_name} removido da blacklist com sucesso")
                    success_count += 1
                else:
                    print(f"   ❌ Falha ao mover {user_name} na catraca")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Erro ao processar {user_name}: {e}")
                error_count += 1
        
        print(f"\n📈 Resumo:")
        print(f"   - Total processados: {len(blacklist_users)}")
        print(f"   - Sucessos: {success_count}")
        print(f"   - Erros: {error_count}")
        
        # Verificar se ainda há usuários na blacklist
        remaining_users = client.get_user_groups(blacklist_group.device_group_id)
        if remaining_users:
            print(f"   ⚠️  Ainda há {len(remaining_users)} usuários na blacklist")
        else:
            print(f"   ✅ Blacklist limpa - todos os usuários removidos")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    
    print(f"\n=== OPERAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    remove_users_from_blacklist()
