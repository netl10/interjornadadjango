#!/usr/bin/env python3
"""
Script para criar dispositivo no banco de dados.
"""
import os
import sys
import django

def setup_django():
    """Configura Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
    django.setup()

def create_device():
    """Cria dispositivo no banco de dados."""
    print("📱 Criando dispositivo no banco de dados...")
    
    try:
        from apps.devices.models import Device, DeviceConfiguration
        from django.conf import settings
        
        # Verificar se já existe
        existing_device = Device.objects.filter(device_type='primary').first()
        if existing_device:
            print(f"✅ Dispositivo já existe: {existing_device.name}")
            return existing_device
        
        # Criar dispositivo
        device = Device.objects.create(
            name="Catraca Principal",
            device_type="primary",
            ip_address=settings.PRIMARY_DEVICE_IP,
            port=settings.PRIMARY_DEVICE_PORT,
            username=settings.PRIMARY_DEVICE_USERNAME,
            password=settings.PRIMARY_DEVICE_PASSWORD,
            use_https=settings.PRIMARY_DEVICE_USE_HTTPS,
            is_enabled=True,
            status="disconnected"
        )
        
        print(f"✅ Dispositivo criado: {device.name} ({device.ip_address}:{device.port})")
        
        # Criar configuração padrão
        config = DeviceConfiguration.objects.create(
            device=device,
            monitor_interval=settings.MONITOR_INTERVAL_SECONDS,
            connection_timeout=settings.DEVICE_CONNECTION_TIMEOUT,
            request_timeout=settings.DEVICE_REQUEST_TIMEOUT,
            max_reconnection_attempts=settings.MAX_RECONNECTION_ATTEMPTS,
            base_reconnection_delay=settings.BASE_RECONNECTION_DELAY,
            max_reconnection_delay=settings.MAX_RECONNECTION_DELAY
        )
        
        print(f"✅ Configuração criada para o dispositivo")
        
        return device
        
    except Exception as e:
        print(f"❌ Erro ao criar dispositivo: {e}")
        return None

def main():
    """Função principal."""
    print("=" * 50)
    print("📱 CRIAÇÃO DE DISPOSITIVO")
    print("=" * 50)
    
    # Configurar Django
    setup_django()
    
    # Criar dispositivo
    device = create_device()
    
    if device:
        print(f"\n🎉 Dispositivo criado com sucesso!")
        print(f"   ID: {device.id}")
        print(f"   Nome: {device.name}")
        print(f"   IP: {device.ip_address}:{device.port}")
        print(f"   Tipo: {device.device_type}")
        print(f"   Status: {device.status}")
    
    print("\n" + "=" * 50)
    print("🏁 CRIAÇÃO CONCLUÍDA")
    print("=" * 50)

if __name__ == '__main__':
    main()
