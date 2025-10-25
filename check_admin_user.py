#!/usr/bin/env python3
"""
Script para verificar o usuário admin.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from django.contrib.auth.models import User

def check_admin_user():
    """Verifica o usuário admin."""
    print("🔍 VERIFICANDO USUÁRIO ADMIN")
    print("=" * 40)
    
    try:
        # Verificar se o usuário admin existe
        admin_user = User.objects.filter(username='admin').first()
        
        if admin_user:
            print(f"✅ Usuário admin encontrado")
            print(f"📧 Email: {admin_user.email}")
            print(f"👤 Nome: {admin_user.first_name} {admin_user.last_name}")
            print(f"🔐 É superusuário: {admin_user.is_superuser}")
            print(f"👥 É staff: {admin_user.is_staff}")
            print(f"✅ Ativo: {admin_user.is_active}")
            print(f"📅 Último login: {admin_user.last_login}")
            print(f"📅 Data de criação: {admin_user.date_joined}")
        else:
            print("❌ Usuário admin NÃO encontrado")
            print("💡 Criando usuário admin...")
            
            # Criar usuário admin
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("✅ Usuário admin criado com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro ao verificar usuário: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_admin_user()
