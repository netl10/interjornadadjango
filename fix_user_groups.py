#!/usr/bin/env python
"""
Script para corrigir grupos de usuários na catraca
"""
import os
import sys
import django
from django.utils import timezone

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.devices.device_client import DeviceClient
from apps.employees.models import Employee, EmployeeGroup

def fix_user_groups():
    """Corrige grupos de usuários na catraca"""
    print("=== CORRIGINDO GRUPOS DE USUÁRIOS ===\n")
    
    try:
        # Conectar com a catraca
        client = DeviceClient()
        if not client.login():
            print("❌ Falha ao conectar com a catraca")
            return
        
        print("✅ Conectado com a catraca")
        
        # Buscar grupo padrão
        default_group = EmployeeGroup.objects.filter(name='GRUPO_PADRAO').first()
        if not default_group:
            print("❌ Grupo padrão não encontrado")
            return
        
        print(f"📊 Grupo padrão: {default_group.name}")
        
        # Obter todos os usuários da catraca
        print(f"\n👥 Buscando todos os usuários na catraca...")
        all_users = client.get_users()
        if not all_users:
            print("❌ Falha ao obter usuários da catraca")
            return
        
        print(f"📊 Total de usuários na catraca: {len(all_users)}")
        
        # Processar cada usuário
        fixed_count = 0
        error_count = 0
        
        for user_data in all_users:
            user_id = user_data.get('id')
            user_name = user_data.get('name', f'Usuário {user_id}')
            user_groups = user_data.get('groups', [])
            
            # Pular usuários com ID None
            if user_id is None:
                print(f"⚠️  Pulando usuário com ID None: {user_name}")
                continue
            
            print(f"\n👤 Processando: {user_name} (ID: {user_id})")
            print(f"   Grupos atuais: {user_groups}")
            
            try:
                # Buscar funcionário no sistema local
                employee = Employee.objects.filter(device_id=user_id).first()
                if not employee:
                    print(f"   ⚠️  Funcionário não encontrado no sistema local")
                    # Criar funcionário se não existir
                    employee = Employee.objects.create(
                        device_id=user_id,
                        name=user_name,
                        is_active=True,
                        group=default_group
                    )
                    print(f"   ✅ Funcionário criado no sistema local")
                
                # Verificar se está no grupo correto
                should_be_in_group = default_group.device_group_id or 1  # Grupo 1 é o padrão na catraca
                
                if should_be_in_group not in user_groups:
                    print(f"   🔄 Movendo para grupo padrão (ID: {should_be_in_group})...")
                    
                    # Mover para grupo padrão
                    move_success = client.move_user_to_group(
                        user_id, 
                        should_be_in_group, 
                        None  # Não especificar grupo de origem
                    )
                    
                    if move_success:
                        # Atualizar no sistema local
                        employee.group = default_group
                        employee.save(update_fields=['group'])
                        
                        print(f"   ✅ {user_name} movido para grupo padrão")
                        fixed_count += 1
                    else:
                        print(f"   ❌ Falha ao mover {user_name}")
                        error_count += 1
                else:
                    print(f"   ✅ {user_name} já está no grupo correto")
                    
                    # Garantir que está no grupo correto no sistema local
                    if employee.group != default_group:
                        employee.group = default_group
                        employee.save(update_fields=['group'])
                        print(f"   ✅ Grupo atualizado no sistema local")
                
            except Exception as e:
                print(f"   ❌ Erro ao processar {user_name}: {e}")
                error_count += 1
        
        print(f"\n📈 Resumo:")
        print(f"   - Total processados: {len([u for u in all_users if u.get('id') is not None])}")
        print(f"   - Corrigidos: {fixed_count}")
        print(f"   - Erros: {error_count}")
        
        # Verificar resultado final
        print(f"\n🔍 Verificação final:")
        final_groups = client.get_groups()
        for group in final_groups:
            group_id = group.get('id')
            group_name = group.get('name', 'N/A')
            users = client.get_user_groups(group_id)
            print(f"   Grupo {group_id} ({group_name}): {len(users)} usuários")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    
    print(f"\n=== OPERAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_user_groups()
