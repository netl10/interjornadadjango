"""
Comando Django para verificar os últimos 5 logs da catraca com todas as informações.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from apps.employees.models import Employee
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Verifica os últimos 5 logs da catraca com todas as informações'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO ÚLTIMOS 5 LOGS DA CATRACA")
        self.stdout.write("=" * 80)
        
        try:
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write("❌ Não foi possível conectar à catraca")
                return
            
            self.stdout.write("✅ Conectado à catraca")
            
            # Buscar logs recentes
            logs = client.get_recent_access_logs(limit=50)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado na catraca")
                return
            
            # Filtrar apenas logs com usuário válido (user_id > 0)
            user_logs = [log for log in logs if log.get('user_id', 0) > 0]
            
            if not user_logs:
                self.stdout.write("❌ Nenhum log de usuário válido encontrado")
                return
            
            # Pegar os últimos 5 logs de usuário
            last_5_logs = user_logs[-5:]
            
            self.stdout.write(f"📊 Últimos 5 logs de usuário encontrados:")
            self.stdout.write("")
            
            for i, log in enumerate(last_5_logs, 1):
                log_id = log.get('id', 'N/A')
                user_id = log.get('user_id', 'N/A')
                event = log.get('event', 'N/A')
                portal_id = log.get('portal_id', 'N/A')
                timestamp_unix = log.get('time', 'N/A')
                
                # Obter nome do usuário
                try:
                    employee = Employee.objects.filter(device_id=user_id).first()
                    user_name = employee.name if employee else f"Usuário {user_id}"
                except:
                    user_name = f"Usuário {user_id}"
                
                # Converter timestamp
                if timestamp_unix and timestamp_unix != 'N/A':
                    try:
                        dt = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
                        timestamp_str = dt.strftime('%d/%m/%Y %H:%M:%S')
                    except:
                        timestamp_str = str(timestamp_unix)
                else:
                    timestamp_str = 'N/A'
                
                # Mapear evento
                event_map = {
                    'entry': 'Entrada',
                    'exit': 'Saída',
                    'denied': 'Acesso Negado',
                    'error': 'Erro de Leitura',
                    'timeout': 'Timeout',
                    'maintenance': 'Manutenção',
                    'authorized': 'Acesso Autorizado',
                    'blocked': 'Acesso Bloqueado',
                }
                event_name = event_map.get(event, event)
                
                # Mapear portal
                portal_map = {
                    1: '🚪 Portal 1 (Entrada)',
                    2: '🚪 Portal 2 (Saída)',
                }
                portal_name = portal_map.get(portal_id, f'Portal {portal_id}')
                
                self.stdout.write(f"{i}. ID {log_id}:")
                self.stdout.write(f"   Nome: {user_name}")
                self.stdout.write(f"   Evento: {event_name}")
                self.stdout.write(f"   Portal: {portal_name}")
                self.stdout.write(f"   Data/Hora: {timestamp_str}")
                self.stdout.write(f"   User ID: {user_id}")
                self.stdout.write(f"   Event Code: {event}")
                self.stdout.write(f"   Portal ID: {portal_id}")
                self.stdout.write(f"   Timestamp Unix: {timestamp_unix}")
                self.stdout.write("")
            
            # Comparar com os dados informados
            self.stdout.write("📋 COMPARAÇÃO COM DADOS INFORMADOS:")
            self.stdout.write("=" * 80)
            
            expected_logs = [
                {'id': 10029, 'name': 'Diego Lucio', 'event': 'Entrada', 'portal': '🚪 Portal 1 (Entrada)', 'datetime': '09/10/2025 16:08:25'},
                {'id': 10028, 'name': 'Diego Lucio', 'event': 'Entrada', 'portal': '🚪 Portal 2 (Saída)', 'datetime': '09/10/2025 16:08:17'},
                {'id': 10027, 'name': 'Diego Lucio', 'event': 'Entrada', 'portal': '🚪 Portal 1 (Entrada)', 'datetime': '09/10/2025 16:06:59'},
                {'id': 10025, 'name': 'Diego Lucio', 'event': 'Entrada', 'portal': '🚪 Portal 1 (Entrada)', 'datetime': '09/10/2025 11:40:16'},
                {'id': 10021, 'name': 'PEDRO HENRIQUE DA SILVA VAN DER MAS', 'event': 'Entrada', 'portal': '🚪 Portal 1 (Entrada)', 'datetime': '08/10/2025 19:01:10'},
            ]
            
            for i, (found_log, expected_log) in enumerate(zip(last_5_logs, expected_logs), 1):
                found_id = found_log.get('id')
                expected_id = expected_log['id']
                
                self.stdout.write(f"Log {i}:")
                self.stdout.write(f"   ID encontrado: {found_id}")
                self.stdout.write(f"   ID esperado: {expected_id}")
                
                if found_id == expected_id:
                    self.stdout.write("   ✅ ID CORRESPONDE")
                else:
                    self.stdout.write("   ❌ ID NÃO CORRESPONDE")
                
                self.stdout.write("")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
