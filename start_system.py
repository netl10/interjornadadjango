#!/usr/bin/env python3
"""
Script para inicializar o Sistema de Controle de Interjornada Django.
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def setup_django():
    """Configura Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
    django.setup()

def create_migrations():
    """Cria migrações do banco de dados."""
    print("📦 Criando migrações...")
    try:
        execute_from_command_line(['manage.py', 'makemigrations'])
        print("✅ Migrações criadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar migrações: {e}")
        return False
    return True

def run_migrations():
    """Executa migrações do banco de dados."""
    print("🗄️ Executando migrações...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrações executadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao executar migrações: {e}")
        return False
    return True

def create_superuser():
    """Cria superusuário se não existir."""
    print("👤 Verificando superusuário...")
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            print("Criando superusuário...")
            execute_from_command_line(['manage.py', 'createsuperuser', '--noinput'])
            print("✅ Superusuário criado!")
        else:
            print("✅ Superusuário já existe!")
    except Exception as e:
        print(f"❌ Erro ao criar superusuário: {e}")
        return False
    return True

def create_default_data():
    """Cria dados padrão do sistema."""
    print("🔧 Criando dados padrão...")
    try:
        from apps.devices.models import Device
        from apps.interjornada.models import InterjornadaRule
        from django.conf import settings
        
        # Criar dispositivo padrão se não existir
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
        
        # Criar regra padrão se não existir
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
        
        print("✅ Dados padrão criados com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar dados padrão: {e}")
        return False
    return True

def start_services():
    """Inicia serviços do sistema."""
    print("🚀 Iniciando serviços...")
    try:
        from apps.devices.services import device_monitoring_service
        from apps.logs.services import log_queue_service
        from apps.interjornada.services import interjornada_monitoring_service
        
        # Iniciar monitoramento
        device_monitoring_service.start_monitoring()
        log_queue_service.start_processing()
        interjornada_monitoring_service.start_monitoring()
        
        print("✅ Serviços iniciados com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao iniciar serviços: {e}")
        return False
    return True

def main():
    """Função principal."""
    print("=" * 60)
    print("🎯 SISTEMA DE CONTROLE DE INTERJORNADA - DJANGO")
    print("=" * 60)
    
    # Configurar Django
    setup_django()
    
    # Executar inicialização
    steps = [
        ("Criar migrações", create_migrations),
        ("Executar migrações", run_migrations),
        ("Criar superusuário", create_superuser),
        ("Criar dados padrão", create_default_data),
        ("Iniciar serviços", start_services),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"❌ Falha na etapa: {step_name}")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 SISTEMA INICIALIZADO COM SUCESSO!")
    print("=" * 60)
    print("🌐 Dashboard: http://localhost:8000/dashboard/")
    print("📚 API Docs: http://localhost:8000/api/v1/")
    print("🔌 WebSocket: ws://localhost:8000/ws/dashboard/")
    print("=" * 60)
    
    # Iniciar servidor
    print("\n🚀 Iniciando servidor Django...")
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])

if __name__ == '__main__':
    main()
