#!/usr/bin/env python
"""
Script para resetar a senha do usuário admin
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def reset_password():
    print("🔄 Resetando senha do usuário admin...")
    
    try:
        # Buscar usuário
        user = User.objects.get(username='admin')
        print(f"✅ Usuário encontrado: {user.username}")
        
        # Resetar senha
        user.set_password('admin123')
        user.save()
        print("✅ Senha resetada para 'admin123'")
        
        # Testar autenticação
        print("\n🔐 Testando autenticação...")
        auth_user = authenticate(username='admin', password='admin123')
        
        if auth_user:
            print("✅ Autenticação bem-sucedida!")
            print(f"   Usuário: {auth_user.username}")
            print(f"   Ativo: {auth_user.is_active}")
        else:
            print("❌ Autenticação ainda falha")
            
            # Tentar com senha diferente
            print("\n🔄 Tentando senha 'admin'...")
            user.set_password('admin')
            user.save()
            
            auth_user = authenticate(username='admin', password='admin')
            if auth_user:
                print("✅ Autenticação funciona com senha 'admin'")
            else:
                print("❌ Ainda não funciona")
                
    except User.DoesNotExist:
        print("❌ Usuário admin não encontrado")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    reset_password()

