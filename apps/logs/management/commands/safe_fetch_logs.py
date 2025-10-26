"""
Comando Django SEGURO para buscar logs da catraca sem sobrecarregar.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee
import json


class Command(BaseCommand):
    help = 'Busca logs da catraca de forma SEGURA (máximo 1000 logs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limite de logs a buscar (padrão: 50, máximo: 1000)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Filtrar por ID do usuário',
        )
        parser.add_argument(
            '--event',
            type=str,
            help='Filtrar por tipo de evento (entry, exit, denied)',
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Salvar logs no banco de dados',
        )
        parser.add_argument(
            '--recent-only',
            action='store_true',
            help='Buscar apenas logs muito recentes (últimos 20)',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Buscando logs da catraca de forma SEGURA...")
        
        # Limitar para não sobrecarregar a catraca
        limit = min(options['limit'], 1000)  # Máximo 1000 logs
        user_id = options.get('user_id')
        event = options.get('event')
        save_logs = options['save']
        recent_only = options['recent_only']
        
        # Se recent_only, limitar ainda mais
        if recent_only:
            limit = min(limit, 20)
            self.stdout.write("⚠️ Modo SEGURO: buscando apenas logs muito recentes")
        
        self.stdout.write(f"📊 Limite máximo: {limit} logs")
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write(self.style.ERROR("❌ Não foi possível conectar à catraca"))
                return
            
            self.stdout.write("✅ Conectado à catraca com sucesso!")
            
            # Buscar logs de forma segura
            if recent_only:
                # Buscar apenas os últimos logs
                logs = client.get_recent_access_logs(limit=limit, min_id=0)
                self.stdout.write(f"📊 Buscando últimos {limit} logs (modo seguro)")
            else:
                # Buscar logs a partir do último ID processado
                last_processed_id = self.get_last_processed_id()
                logs = client.get_recent_access_logs(limit=limit, min_id=last_processed_id)
                self.stdout.write(f"📊 Buscando logs a partir do ID {last_processed_id}")
            
            if not logs:
                self.stdout.write("📋 Nenhum log encontrado")
                return
            
            # Filtrar logs se necessário
            original_count = len(logs)
            if user_id:
                logs = [log for log in logs if log.get('user_id') == user_id]
                self.stdout.write(f"🔍 Filtrado por usuário {user_id}: {len(logs)} logs")
            
            if event:
                logs = [log for log in logs if log.get('event') == event]
                self.stdout.write(f"🔍 Filtrado por evento '{event}': {len(logs)} logs")
            
            # Exibir logs
            self.stdout.write(f"\n📋 {len(logs)} logs encontrados (de {original_count} total):")
            self.stdout.write("=" * 80)
            
            saved_count = 0
            for i, log in enumerate(logs, 1):
                self.display_log(log, i)
                
                # Salvar se solicitado
                if save_logs:
                    if self.save_log(log):
                        saved_count += 1
            
            if save_logs:
                self.stdout.write(f"\n💾 {saved_count} logs salvos no banco de dados")
            
            # Estatísticas
            self.show_statistics(logs)
            
            # Aviso de segurança
            if len(logs) >= 100:
                self.stdout.write(self.style.WARNING("\n⚠️ ATENÇÃO: Muitos logs encontrados. Use --recent-only para modo mais seguro."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
    
    def get_last_processed_id(self):
        """Obtém o último ID de log processado."""
        try:
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            return last_log.device_log_id if last_log else 0
        except Exception:
            return 0
    
    def display_log(self, log, index):
        """Exibe um log formatado."""
        log_id = log.get('id', 'N/A')
        user_id = log.get('user_id', 'N/A')
        event = log.get('event', 'N/A')
        portal_id = log.get('portal_id', 'N/A')
        timestamp = log.get('timestamp', 'N/A')
        
        # Obter nome do usuário se possível
        user_name = self.get_user_name(user_id)
        
        self.stdout.write(f"{index:2d}. ID: {log_id}")
        self.stdout.write(f"    👤 Usuário: {user_id} ({user_name})")
        self.stdout.write(f"    🚪 Evento: {event}")
        self.stdout.write(f"    🏢 Portal: {portal_id}")
        self.stdout.write(f"    ⏰ Timestamp: {timestamp}")
        self.stdout.write()
    
    def get_user_name(self, user_id):
        """Obtém nome do usuário."""
        if user_id == 0:
            return "Sistema"
        
        try:
            employee = Employee.objects.filter(device_id=user_id).first()
            return employee.name if employee else "Usuário Desconhecido"
        except Exception:
            return "Usuário Desconhecido"
    
    def save_log(self, log_data):
        """Salva um log no banco de dados."""
        try:
            log_id = log_data.get('id')
            
            # Verificar se já existe
            if AccessLog.objects.filter(device_log_id=log_id).exists():
                return False
            
            # Mapear evento
            event_type = self.map_event_type(log_data.get('event'))
            user_id = log_data.get('user_id')
            user_name = self.get_user_name(user_id)
            
            # Criar log
            AccessLog.objects.create(
                device_log_id=log_id,
                user_id=user_id,
                user_name=user_name,
                event_type=event_type,
                event_description=log_data.get('event', 'Desconhecido'),
                device_id=1,
                device_name="Catraca Principal",
                portal_id=log_data.get('portal_id'),
                device_timestamp=log_data.get('timestamp', ''),
                raw_data=log_data,
                processing_status='processed'
            )
            
            return True
            
        except Exception as e:
            self.stdout.write(f"   ❌ Erro ao salvar log {log_id}: {e}")
            return False
    
    def map_event_type(self, event):
        """Mapeia evento para tipo."""
        event_map = {
            'entry': 1,
            'exit': 2,
            'denied': 3,
            'error': 4,
            'timeout': 5,
            'maintenance': 6,
            'authorized': 7,
            'blocked': 8,
        }
        return event_map.get(event, 1)
    
    def show_statistics(self, logs):
        """Mostra estatísticas dos logs."""
        if not logs:
            return
        
        # Contar por evento
        event_counts = {}
        user_counts = {}
        
        for log in logs:
            event = log.get('event', 'unknown')
            user_id = log.get('user_id', 0)
            
            event_counts[event] = event_counts.get(event, 0) + 1
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        self.stdout.write("📊 ESTATÍSTICAS:")
        self.stdout.write("=" * 40)
        
        # Eventos
        self.stdout.write("🚪 Por evento:")
        for event, count in sorted(event_counts.items()):
            self.stdout.write(f"   {event}: {count}")
        
        # Usuários
        self.stdout.write("\n👥 Por usuário:")
        for user_id, count in sorted(user_counts.items()):
            user_name = self.get_user_name(user_id)
            self.stdout.write(f"   {user_id} ({user_name}): {count}")
        
        # IDs
        if logs:
            min_id = min(log.get('id', 0) for log in logs)
            max_id = max(log.get('id', 0) for log in logs)
            self.stdout.write(f"\n📋 Faixa de IDs: {min_id} - {max_id}")
