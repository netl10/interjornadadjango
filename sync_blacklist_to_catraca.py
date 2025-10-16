#!/usr/bin/env python
"""
Script para sincronizar usuários da blacklist local para a catraca
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
from apps.devices.device_client import DeviceClient

def sync_blacklist_to_catraca():
    """Sincroniza usuários da blacklist local para a catraca"""
    print("=== SINCRONIZANDO BLACKLIST PARA CATRACA ===\n")
    
    # Buscar grupo de blacklist
    blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
    if not blacklist_group:
        print("❌ Grupo de blacklist não encontrado")
        return
    
    if not blacklist_group.device_group_id:
        print("❌ Grupo de blacklist não tem device_group_id configurado")
        return
    
    print(f"📊 Grupo de blacklist: {blacklist_group.name} (ID: {blacklist_group.device_group_id})")
    
    # Buscar usuários na blacklist local
    blacklist_users = Employee.objects.filter(group=blacklist_group)
    print(f"👥 Usuários na blacklist local: {blacklist_users.count()}")
    
    if not blacklist_users.exists():
        print("ℹ️  Nenhum usuário na blacklist local")
        return
    
    # Conectar com catraca
    try:
        client = DeviceClient()
        if not client.login():
            print("❌ Falha ao conectar com catraca")
            return
        
        print("✅ Conectado com catraca")
        
        # Verificar usuários atuais na blacklist na catraca
        current_catraca_users = client.get_user_groups(blacklist_group.device_group_id)
        print(f"📊 Usuários atuais na blacklist na catraca: {len(current_catraca_users)}")
        
        # Processar cada usuário
        success_count = 0
        error_count = 0
        
        for user in blacklist_users:
            print(f"\n👤 Processando: {user.name} (ID: {user.device_id})")
            
            try:
                # Verificar se já está na blacklist na catraca
                already_in_catraca = any(
                    user_data.get('id') == user.device_id 
                    for user_data in current_catraca_users
                )
                
                if already_in_catraca:
                    print(f"   ✅ Já está na blacklist na catraca")
                    success_count += 1
                    continue
                
                # Mover para blacklist na catraca
                print(f"   🔄 Movendo para blacklist na catraca...")
                
                # Usar grupo padrão como origem (ID 1)
                move_success = client.move_user_to_group(
                    user.device_id, 
                    blacklist_group.device_group_id, 
                    1  # Grupo padrão como origem
                )
                
                if move_success:
                    print(f"   ✅ {user.name} movido para blacklist na catraca")
                    success_count += 1
                else:
                    print(f"   ❌ Falha ao mover {user.name} para blacklist na catraca")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Erro ao processar {user.name}: {e}")
                error_count += 1
        
        print(f"\n📈 Resumo:")
        print(f"   - Total processados: {blacklist_users.count()}")
        print(f"   - Sucessos: {success_count}")
        print(f"   - Erros: {error_count}")
        
        # Verificação final
        print(f"\n🔍 Verificação final:")
        final_catraca_users = client.get_user_groups(blacklist_group.device_group_id)
        print(f"   - Usuários na blacklist na catraca: {len(final_catraca_users)}")
        
        if len(final_catraca_users) == blacklist_users.count():
            print(f"   ✅ Sincronização completa!")
        else:
            print(f"   ⚠️  Ainda há diferença entre local ({blacklist_users.count()}) e catraca ({len(final_catraca_users)})")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    
    print(f"\n=== OPERAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    sync_blacklist_to_catraca()
