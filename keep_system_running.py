#!/usr/bin/env python
"""
Script para manter o sistema funcionando automaticamente
"""
import os
import sys
import django
import time
import threading

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service
from django.utils import timezone
from django.db import transaction

class SystemKeeper:
    """Classe para manter o sistema funcionando"""
    
    def __init__(self):
        self.running = True
        self.sync_interval = 5  # segundos
        
    def sync_logs(self):
        """Sincroniza logs do dispositivo"""
        try:
            client = DeviceClient(None)
            if not client.login():
                print("❌ Falha ao conectar com dispositivo")
                return 0
            
            logs = client.get_recent_access_logs(limit=10)
            if not logs:
                return 0
            
            existing_ids = set(AccessLog.objects.values_list('device_log_id', flat=True))
            new_logs = [log for log in logs if log.get('id') not in existing_ids]
            
            synced_count = 0
            for log_data in new_logs:
                try:
                    with transaction.atomic():
                        AccessLog.objects.create(
                            device_log_id=log_data.get('id'),
                            user_id=log_data.get('user_id', 0),
                            user_name=log_data.get('user_name', ''),
                            event_type=log_data.get('event_type', 0),
                            event_description=log_data.get('event_description', ''),
                            portal_id=log_data.get('portal_id', 1),
                            device_timestamp=log_data.get('timestamp', timezone.now()),
                            processing_status='pending',
                            created_at=timezone.now(),
                            updated_at=timezone.now()
                        )
                        synced_count += 1
                except Exception as e:
                    print(f"❌ Erro ao sincronizar log {log_data.get('id')}: {e}")
            
            return synced_count
            
        except Exception as e:
            print(f"❌ Erro na sincronização: {e}")
            return 0
    
    def process_logs(self):
        """Processa logs não processados"""
        try:
            unprocessed = AccessLog.objects.filter(session_processed=False).order_by('device_log_id')
            processed_count = 0
            
            for log in unprocessed[:5]:  # Processar apenas 5 por vez
                try:
                    log_monitor_service.process_access_log(log)
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Erro ao processar log {log.device_log_id}: {e}")
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Erro no processamento: {e}")
            return 0
    
    def run(self):
        """Loop principal"""
        print("🚀 Sistema Keeper iniciado - Mantendo logs sincronizados...")
        print("📊 Dashboard limpa: http://localhost:8000/admin/sessions/dashboard-clean/")
        print("📊 Monitor tempo real: http://localhost:8000/admin/logs/realtime/")
        print("⏹️  Pressione Ctrl+C para parar")
        
        while self.running:
            try:
                # Sincronizar logs
                synced = self.sync_logs()
                if synced > 0:
                    print(f"✅ {synced} logs sincronizados")
                
                # Processar logs
                processed = self.process_logs()
                if processed > 0:
                    print(f"✅ {processed} logs processados")
                
                # Aguardar próximo ciclo
                time.sleep(self.sync_interval)
                
            except KeyboardInterrupt:
                print("\n⏹️  Parando Sistema Keeper...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Erro no loop principal: {e}")
                time.sleep(self.sync_interval)
        
        print("✅ Sistema Keeper parado")

def main():
    """Função principal"""
    keeper = SystemKeeper()
    keeper.run()

if __name__ == "__main__":
    main()
