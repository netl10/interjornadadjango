#!/usr/bin/env python
"""
Script para verificar detalhes da blacklist
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

def check_blacklist_details():
    """Verifica detalhes da blacklist"""
    print("=== DETALHES DA BLACKLIST ===\n")
    
    # Verificar usuários na blacklist local
    blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
    if blacklist_group:
        print(f"📊 Grupo de blacklist: {blacklist_group.name} (ID: {blacklist_group.device_group_id})")
        
        blacklist_users = Employee.objects.filter(group=blacklist_group)
        print(f"👥 Usuários na blacklist local: {blacklist_users.count()}")
        
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
                    else:
                        time_remaining = session.return_time - now
                        print(f"   ⏰ Tempo restante: {time_remaining}")
            else:
                print(f"   ❌ SEM SESSÃO BLOQUEADA")
    
    # Verificar na catraca
    print(f"\n🔌 Verificando na catraca:")
    try:
        client = DeviceClient()
        if client.login():
            # Verificar usuários no grupo de blacklist na catraca
            if blacklist_group and blacklist_group.device_group_id:
                catraca_users = client.get_user_groups(blacklist_group.device_group_id)
                print(f"   📊 Usuários na blacklist na catraca: {len(catraca_users)}")
                
                for user_data in catraca_users:
                    user_id = user_data.get('id')
                    user_name = user_data.get('name', f'Usuário {user_id}')
                    print(f"      - {user_name} (ID: {user_id})")
            else:
                print(f"   ❌ Grupo de blacklist não tem device_group_id configurado")
        else:
            print(f"   ❌ Falha ao conectar com catraca")
    except Exception as e:
        print(f"   ❌ Erro ao verificar catraca: {e}")
    
    # Verificar inconsistências
    print(f"\n🔍 Inconsistências:")
    if blacklist_group:
        local_count = Employee.objects.filter(group=blacklist_group).count()
        if blacklist_group.device_group_id:
            try:
                client = DeviceClient()
                if client.login():
                    catraca_count = len(client.get_user_groups(blacklist_group.device_group_id))
                    if local_count != catraca_count:
                        print(f"   ⚠️  Inconsistência: {local_count} usuários no sistema local vs {catraca_count} na catraca")
                    else:
                        print(f"   ✅ Sincronizado: {local_count} usuários em ambos")
                else:
                    print(f"   ❌ Não foi possível verificar catraca")
            except Exception as e:
                print(f"   ❌ Erro ao verificar: {e}")
        else:
            print(f"   ⚠️  Grupo de blacklist não tem device_group_id configurado")
    
    print(f"\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_blacklist_details()
