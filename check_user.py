#!/usr/bin/env python
"""
Script para verificar se o usuário admin existe
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

def check_user():
    print("🔍 Verificando usuário admin...")
    
    # Verificar se o usuário existe
    try:
        user = User.objects.get(username='admin')
        print(f"✅ Usuário encontrado: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Ativo: {user.is_active}")
        print(f"   Staff: {user.is_staff}")
        print(f"   Superuser: {user.is_superuser}")
        
        # Testar autenticação
        print("\n🔐 Testando autenticação...")
        auth_user = authenticate(username='admin', password='admin123')
        
        if auth_user:
            print("✅ Autenticação bem-sucedida")
        else:
            print("❌ Autenticação falhou")
            
            # Tentar criar usuário se não existir
            print("\n🔄 Tentando criar usuário...")
            try:
                new_user = User.objects.create_user(
                    username='admin',
                    password='admin123',
                    email='admin@sistema.com',
                    first_name='Administrador',
                    last_name='Sistema',
                    is_staff=True,
                    is_superuser=True,
                    is_active=True
                )
                print("✅ Usuário criado com sucesso")
                
                # Testar novamente
                auth_user = authenticate(username='admin', password='admin123')
                if auth_user:
                    print("✅ Autenticação funcionando após criação")
                else:
                    print("❌ Ainda não funciona")
                    
            except Exception as e:
                print(f"❌ Erro ao criar usuário: {e}")
        
    except User.DoesNotExist:
        print("❌ Usuário admin não encontrado")
        
        # Criar usuário
        print("🔄 Criando usuário admin...")
        try:
            user = User.objects.create_user(
                username='admin',
                password='admin123',
                email='admin@sistema.com',
                first_name='Administrador',
                last_name='Sistema',
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            print("✅ Usuário criado com sucesso")
            
            # Testar autenticação
            auth_user = authenticate(username='admin', password='admin123')
            if auth_user:
                print("✅ Autenticação funcionando")
            else:
                print("❌ Autenticação ainda não funciona")
                
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
    
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    check_user()

