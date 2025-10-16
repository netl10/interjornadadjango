#!/usr/bin/env python
"""
Script para verificar todos os grupos e usuários na catraca
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
from apps.employees.models import EmployeeGroup

def check_catraca_groups():
    """Verifica todos os grupos e usuários na catraca"""
    print("=== VERIFICAÇÃO COMPLETA DA CATRACA ===\n")
    
    try:
        # Conectar com a catraca
        client = DeviceClient()
        if not client.login():
            print("❌ Falha ao conectar com a catraca")
            return
        
        print("✅ Conectado com a catraca")
        
        # Obter todos os grupos da catraca
        print(f"\n📊 Grupos na catraca:")
        groups = client.get_groups()
        if not groups:
            print("❌ Falha ao obter grupos da catraca")
            return
        
        for group in groups:
            group_id = group.get('id')
            group_name = group.get('name', 'N/A')
            print(f"   - ID: {group_id}, Nome: {group_name}")
        
        # Verificar cada grupo
        print(f"\n👥 Usuários por grupo:")
        for group in groups:
            group_id = group.get('id')
            group_name = group.get('name', 'N/A')
            
            users = client.get_user_groups(group_id)
            if users:
                print(f"\n   📁 Grupo {group_id} ({group_name}): {len(users)} usuários")
                for user in users:
                    user_id = user.get('id')
                    user_name = user.get('name', f'Usuário {user_id}')
                    print(f"      - {user_name} (ID: {user_id})")
            else:
                print(f"\n   📁 Grupo {group_id} ({group_name}): 0 usuários")
        
        # Verificar grupos do sistema local
        print(f"\n🏠 Grupos no sistema local:")
        local_groups = EmployeeGroup.objects.all()
        for group in local_groups:
            print(f"   - ID: {group.device_group_id}, Nome: {group.name}, Blacklist: {group.is_blacklist}")
        
        # Verificar se há usuários em grupos que podem ser blacklist
        print(f"\n🔍 Verificando grupos suspeitos:")
        for group in groups:
            group_id = group.get('id')
            group_name = group.get('name', '').lower()
            
            # Verificar se o nome sugere blacklist ou bloqueio
            if any(keyword in group_name for keyword in ['blacklist', 'bloqueado', 'blocked', 'interjornada', 'rest']):
                users = client.get_user_groups(group_id)
                if users:
                    print(f"   ⚠️  Grupo suspeito {group_id} ({group.get('name')}): {len(users)} usuários")
                    for user in users:
                        user_id = user.get('id')
                        user_name = user.get('name', f'Usuário {user_id}')
                        print(f"      - {user_name} (ID: {user_id})")
        
        # Verificar usuários que podem estar bloqueados
        print(f"\n🚫 Verificando usuários que podem estar bloqueados:")
        all_users = client.get_users()
        if all_users:
            for user in all_users:
                user_id = user.get('id')
                user_name = user.get('name', f'Usuário {user_id}')
                user_groups = user.get('groups', [])
                
                # Verificar se está em grupo suspeito
                blocked = False
                for group_id in user_groups:
                    group = next((g for g in groups if g.get('id') == group_id), None)
                    if group:
                        group_name = group.get('name', '').lower()
                        if any(keyword in group_name for keyword in ['blacklist', 'bloqueado', 'blocked', 'interjornada', 'rest']):
                            blocked = True
                            break
                
                if blocked:
                    print(f"   🚫 {user_name} (ID: {user_id}) - Pode estar bloqueado")
                    print(f"      Grupos: {user_groups}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print(f"\n=== VERIFICAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    check_catraca_groups()
