#!/usr/bin/env python3
"""
Script rápido para inicializar o sistema Django.
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def setup_django():
    """Configura Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
    django.setup()

def main():
    """Função principal."""
    print("=" * 60)
    print("🚀 INICIALIZAÇÃO RÁPIDA - SISTEMA DE INTERJORNADA")
    print("=" * 60)
    
    # Configurar Django
    setup_django()
    
    print("📦 Criando migrações...")
    try:
        execute_from_command_line(['manage.py', 'makemigrations'])
        print("✅ Migrações criadas!")
    except Exception as e:
        print(f"⚠️ Erro ao criar migrações: {e}")
    
    print("🗄️ Executando migrações...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrações executadas!")
    except Exception as e:
        print(f"⚠️ Erro ao executar migrações: {e}")
    
    print("👤 Criando superusuário...")
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            # Criar superusuário padrão
            User.objects.create_superuser(
                username='admin',
                email='admin@interjornada.com',
                password='admin123'
            )
            print("✅ Superusuário criado: admin/admin123")
        else:
            print("✅ Superusuário já existe!")
    except Exception as e:
        print(f"⚠️ Erro ao criar superusuário: {e}")
    
    print("🔧 Criando dados padrão...")
    try:
        from apps.devices.models import Device
        from apps.interjornada.models import InterjornadaRule
        from django.conf import settings
        
        # Dispositivo padrão
        if not Device.objects.exists():
            Device.objects.create(
                name="Dispositivo Principal",
                device_type="primary",
                ip_address=settings.PRIMARY_DEVICE_IP,
                port=settings.PRIMARY_DEVICE_PORT,
                username=settings.PRIMARY_DEVICE_USERNAME,
                password=settings.PRIMARY_DEVICE_PASSWORD,
                use_https=settings.PRIMARY_DEVICE_USE_HTTPS,
                status="inactive"
            )
            print("✅ Dispositivo padrão criado!")
        
        # Regra padrão
        if not InterjornadaRule.objects.exists():
            InterjornadaRule.objects.create(
                name="Regra Padrão",
                description="Regra padrão do sistema",
                work_duration_minutes=settings.WORK_DURATION_MINUTES,
                rest_duration_minutes=settings.REST_DURATION_MINUTES,
                apply_to_all=True,
                is_active=True
            )
            print("✅ Regra padrão criada!")
            
    except Exception as e:
        print(f"⚠️ Erro ao criar dados padrão: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 SISTEMA INICIALIZADO!")
    print("=" * 60)
    print("🌐 Dashboard: http://localhost:8000/dashboard/")
    print("📚 Admin: http://localhost:8000/admin/ (admin/admin123)")
    print("🔌 API: http://localhost:8000/api/v1/")
    print("=" * 60)
    
    # Iniciar servidor
    print("\n🚀 Iniciando servidor...")
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])

if __name__ == '__main__':
    main()
