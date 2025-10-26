"""
Comando Django para encontrar logs recentes por timestamp.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from apps.employees.models import Employee
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Encontra logs recentes por timestamp'

    def handle(self, *args, **options):
        self.stdout.write("🔍 BUSCANDO LOGS RECENTES POR TIMESTAMP")
        self.stdout.write("=" * 60)
        
        try:
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write("❌ Não foi possível conectar à catraca")
                return
            
            self.stdout.write("✅ Conectado à catraca")
            
            # Buscar logs recentes
            logs = client.get_recent_access_logs(limit=200)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado na catraca")
                return
            
            self.stdout.write(f"📊 Total de logs encontrados: {len(logs)}")
            
            # Filtrar logs com usuário válido
            user_logs = [log for log in logs if log.get('user_id', 0) > 0]
            self.stdout.write(f"📊 Logs com usuário válido: {len(user_logs)}")
            
            # Buscar logs do Diego Lucio (user_id = 1)
            diego_logs = [log for log in user_logs if log.get('user_id') == 1]
            self.stdout.write(f"📊 Logs do Diego Lucio: {len(diego_logs)}")
            
            if diego_logs:
                self.stdout.write("\n📋 Logs do Diego Lucio encontrados:")
                for log in diego_logs:
                    log_id = log.get('id')
                    timestamp_unix = log.get('time')
                    event = log.get('event')
                    portal_id = log.get('portal_id')
                    
                    # Converter timestamp
                    if timestamp_unix:
                        try:
                            dt = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
                            timestamp_str = dt.strftime('%d/%m/%Y %H:%M:%S')
                        except:
                            timestamp_str = str(timestamp_unix)
                    else:
                        timestamp_str = 'N/A'
                    
                    # Mapear portal
                    portal_map = {
                        1: 'Portal de Entrada',
                        2: 'Portal de Saída',
                    }
                    portal_name = portal_map.get(portal_id, f'Portal {portal_id}')
                    
                    self.stdout.write(f"   ID {log_id}: {timestamp_str} - {portal_name} - Evento {event}")
            
            # Buscar logs mais recentes que 10029
            recent_logs = [log for log in user_logs if log['id'] > 10029]
            if recent_logs:
                self.stdout.write(f"\n🆕 Logs mais recentes que 10029: {len(recent_logs)}")
                for log in recent_logs:
                    log_id = log.get('id')
                    user_id = log.get('user_id')
                    timestamp_unix = log.get('time')
                    event = log.get('event')
                    
                    # Obter nome do usuário
                    try:
                        employee = Employee.objects.filter(device_id=user_id).first()
                        user_name = employee.name if employee else f"Usuário {user_id}"
                    except:
                        user_name = f"Usuário {user_id}"
                    
                    # Converter timestamp
                    if timestamp_unix:
                        try:
                            dt = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
                            timestamp_str = dt.strftime('%d/%m/%Y %H:%M:%S')
                        except:
                            timestamp_str = str(timestamp_unix)
                    else:
                        timestamp_str = 'N/A'
                    
                    self.stdout.write(f"   ID {log_id}: {user_name} - {timestamp_str} - Evento {event}")
            else:
                self.stdout.write("\nℹ️ Nenhum log mais recente que 10029 encontrado")
            
            # Verificar se há logs não identificados (user_id = 0)
            system_logs = [log for log in logs if log.get('user_id', 0) == 0]
            if system_logs:
                self.stdout.write(f"\n⚠️ Logs de sistema (não identificados): {len(system_logs)}")
                recent_system_logs = [log for log in system_logs if log['id'] > 10029]
                if recent_system_logs:
                    self.stdout.write("   Logs de sistema mais recentes que 10029:")
                    for log in recent_system_logs[:5]:  # Mostrar apenas os 5 mais recentes
                        log_id = log.get('id')
                        timestamp_unix = log.get('time')
                        event = log.get('event')
                        
                        if timestamp_unix:
                            try:
                                dt = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
                                timestamp_str = dt.strftime('%d/%m/%Y %H:%M:%S')
                            except:
                                timestamp_str = str(timestamp_unix)
                        else:
                            timestamp_str = 'N/A'
                        
                        self.stdout.write(f"   ID {log_id}: {timestamp_str} - Evento {event}")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
