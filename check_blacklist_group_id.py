#!/usr/bin/env python3
"""
Script para consultar o ID atual do grupo blacklist no sistema.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.employees.models import EmployeeGroup
from apps.devices.device_client import DeviceClient

def check_blacklist_group_id():
    """Consulta o ID atual do grupo blacklist."""
    print("🔍 CONSULTANDO ID DO GRUPO BLACKLIST")
    print("=" * 50)
    
    try:
        # 1. Verificar no banco de dados Django
        print("\n📊 CONSULTA NO BANCO DE DADOS:")
        print("-" * 30)
        
        blacklist_groups = EmployeeGroup.objects.filter(is_blacklist=True)
        
        if blacklist_groups.exists():
            for group in blacklist_groups:
                print(f"✅ Grupo encontrado no banco:")
                print(f"   📝 Nome: {group.name}")
                print(f"   🆔 ID no Dispositivo: {group.device_group_id}")
                print(f"   📅 Criado em: {group.created_at}")
                print(f"   🔄 Atualizado em: {group.updated_at}")
                print(f"   ✅ Ativo: {group.is_active}")
                print(f"   🚫 É Blacklist: {group.is_blacklist}")
                print()
        else:
            print("❌ Nenhum grupo de blacklist encontrado no banco de dados")
        
        # 2. Verificar na catraca/dispositivo
        print("\n📊 CONSULTA NA CATRACA/DISPOSITIVO:")
        print("-" * 30)
        
        try:
            client = DeviceClient()
            if client.login():
                print("✅ Conectado ao dispositivo")
                
                # Buscar todos os grupos
                groups = client.get_groups()
                print(f"📋 Total de grupos encontrados: {len(groups)}")
                
                # Procurar por grupos com "blacklist" no nome
                blacklist_groups_device = []
                for group in groups:
                    group_name = group.get('name', '').lower()
                    if 'blacklist' in group_name:
                        blacklist_groups_device.append(group)
                
                if blacklist_groups_device:
                    print(f"\n🔍 Grupos com 'blacklist' no nome:")
                    for group in blacklist_groups_device:
                        print(f"   📝 Nome: {group.get('name')}")
                        print(f"   🆔 ID: {group.get('id')}")
                        print(f"   👥 Usuários: {group.get('user_count', 'N/A')}")
                        print()
                else:
                    print("❌ Nenhum grupo com 'blacklist' encontrado na catraca")
                
                # 3. Comparar IDs
                print("\n📊 COMPARAÇÃO DE IDs:")
                print("-" * 30)
                
                db_blacklist = EmployeeGroup.objects.filter(is_blacklist=True).first()
                if db_blacklist and db_blacklist.device_group_id:
                    print(f"📊 ID no banco: {db_blacklist.device_group_id}")
                    
                    # Verificar se o ID existe na catraca
                    device_group = None
                    for group in groups:
                        if group.get('id') == db_blacklist.device_group_id:
                            device_group = group
                            break
                    
                    if device_group:
                        print(f"✅ ID {db_blacklist.device_group_id} encontrado na catraca")
                        print(f"   📝 Nome na catraca: {device_group.get('name')}")
                        print(f"   👥 Usuários na catraca: {device_group.get('user_count', 'N/A')}")
                    else:
                        print(f"❌ ID {db_blacklist.device_group_id} NÃO encontrado na catraca")
                        print("   ⚠️  Possível problema: ID foi recriado ou alterado")
                
            else:
                print("❌ Falha ao conectar ao dispositivo")
                
        except Exception as e:
            print(f"❌ Erro ao consultar dispositivo: {e}")
        
        # 4. Verificar histórico de grupos
        print("\n📊 HISTÓRICO DE GRUPOS:")
        print("-" * 30)
        
        all_groups = EmployeeGroup.objects.all().order_by('-created_at')
        print(f"📋 Total de grupos no sistema: {all_groups.count()}")
        
        for group in all_groups[:10]:  # Mostrar os 10 mais recentes
            status = "🟢 Ativo" if group.is_active else "🔴 Inativo"
            blacklist_status = "🚫 Blacklist" if group.is_blacklist else "✅ Normal"
            print(f"   📝 {group.name} (ID: {group.device_group_id}) - {status} - {blacklist_status}")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_blacklist_group_id()
