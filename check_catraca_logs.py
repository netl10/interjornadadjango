#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.devices.device_client import DeviceClient

# Conectar à catraca
client = DeviceClient()
if client.login():
    print("✅ Conectado à catraca")
    
    # Buscar logs recentes
    logs = client.get_recent_access_logs(limit=10, min_id=10095)
    print(f"\nLogs da catraca (ID >= 10095): {len(logs)} encontrados")
    
    for log in logs:
        print(f"ID {log['id']}: user_id={log.get('user_id', 0)}, event={log.get('event', 0)}, portal={log.get('portal_id', 0)}")
else:
    print("❌ Falha ao conectar à catraca")
