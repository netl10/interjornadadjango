"""
Comando Django para sincronizar logs em sequência, preenchendo lacunas.
"""
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee


class Command(BaseCommand):
    help = 'Sincroniza logs em sequência, preenchendo lacunas se necessário'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-id',
            type=int,
            help='ID inicial para sincronização',
        )
        parser.add_argument(
            '--end-id',
            type=int,
            help='ID final para sincronização',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Tamanho do lote para processamento (padrão: 50)',
        )
        parser.add_argument(
            '--fill-gaps',
            action='store_true',
            help='Preencher lacunas na sequência',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simular, não salvar no banco',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔄 Sincronizando logs em sequência...")
        
        start_id = options.get('start_id')
        end_id = options.get('end_id')
        batch_size = min(options['batch_size'], 100)
        fill_gaps = options['fill_gaps']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("⚠️ MODO DRY-RUN: Apenas simulando, não salvando no banco")
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write(self.style.ERROR("❌ Não foi possível conectar à catraca"))
                return
            
            self.stdout.write("✅ Conectado à catraca com sucesso!")
            
            # Determinar IDs de início e fim
            if not start_id:
                start_id = self.get_last_processed_id() + 1
                self.stdout.write(f"📊 ID inicial: {start_id} (último processado + 1)")
            
            if not end_id:
                # Buscar o maior ID disponível na catraca
                end_id = self.get_max_available_id()
                self.stdout.write(f"📊 ID final: {end_id} (maior disponível na catraca)")
            
            self.stdout.write(f"📋 Sincronizando IDs {start_id} a {end_id}")
            
            # Sincronizar logs em sequência
            total_processed = 0
            total_saved = 0
            total_errors = 0
            gaps_filled = 0
            
            current_id = start_id
            
            while current_id <= end_id:
                # Buscar lote de logs
                logs = self.get_logs_by_range(current_id, min(current_id + batch_size - 1, end_id))
                
                if not logs:
                    self.stdout.write(f"⚠️ Nenhum log encontrado para ID {current_id}")
                    current_id += 1
                    continue
                
                # Processar logs em sequência
                saved_count, error_count, gaps_count = self.process_logs_sequence(logs, dry_run)
                total_saved += saved_count
                total_errors += error_count
                gaps_filled += gaps_count
                
                # Atualizar ID atual
                if logs:
                    current_id = logs[-1]['id'] + 1
                else:
                    current_id += batch_size
                
                total_processed += len(logs)
                
                # Mostrar progresso
                progress = ((current_id - start_id) / (end_id - start_id + 1)) * 100
                self.stdout.write(f"📊 Progresso: {progress:.1f}% - {saved_count} salvos, {error_count} erros")
                
                # Pausa entre lotes
                time.sleep(1)
            
            # Estatísticas finais
            self.stdout.write(f"\n📊 RESUMO DA SINCRONIZAÇÃO:")
            self.stdout.write(f"   📋 Logs processados: {total_processed}")
            self.stdout.write(f"   ✅ Logs salvos: {total_saved}")
            self.stdout.write(f"   ❌ Erros: {total_errors}")
            self.stdout.write(f"   🔧 Lacunas preenchidas: {gaps_filled}")
            
            if not dry_run and total_saved > 0:
                self.stdout.write(self.style.SUCCESS("✅ Sincronização concluída com sucesso!"))
            else:
                self.stdout.write(self.style.WARNING("⚠️ Modo dry-run - nenhum log foi salvo"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro durante sincronização: {e}"))
            import traceback
            traceback.print_exc()

    def get_last_processed_id(self):
        """Obtém o último ID de log processado no banco."""
        try:
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            return last_log.device_log_id if last_log else 0
        except Exception:
            return 0

    def get_max_available_id(self):
        """Obtém o maior ID disponível na catraca."""
        try:
            # Buscar logs recentes para encontrar o maior ID
            logs = self.client.get_recent_access_logs(limit=100, min_id=0)
            if logs:
                return max(log['id'] for log in logs)
            return 0
        except Exception:
            return 0

    def get_logs_by_range(self, start_id, end_id):
        """Busca logs em um range específico de IDs."""
        try:
            logs = []
            for log_id in range(start_id, end_id + 1):
                # Buscar log específico por ID
                log = self.client.get_access_log_by_id(log_id)
                if log:
                    logs.append(log)
                else:
                    # Log não encontrado - pode ser uma lacuna
                    self.stdout.write(f"⚠️ Log ID {log_id} não encontrado na catraca")
            
            return logs
        except Exception as e:
            self.stdout.write(f"❌ Erro ao buscar logs por range: {e}")
            return []

    def process_logs_sequence(self, logs, dry_run=False):
        """Processa uma lista de logs em sequência."""
        saved_count = 0
        error_count = 0
        gaps_count = 0
        
        for log in logs:
            try:
                log_id = log['id']
                
                # Verificar se já foi processado
                if not dry_run and AccessLog.objects.filter(device_log_id=log_id).exists():
                    continue  # Já processado
                
                if self.process_single_log(log, dry_run):
                    saved_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(f"   ❌ Erro ao processar log {log.get('id')}: {e}")
                error_count += 1
        
        return saved_count, error_count, gaps_count

    def process_single_log(self, log_data, dry_run=False):
        """Processa um único log."""
        log_id = log_data.get('id')
        user_id = log_data.get('user_id')
        event = log_data.get('event')
        
        # Ignorar logs de sistema (user_id = 0)
        if user_id == 0:
            return False
        
        # Mapear evento para tipo
        event_type = self.map_event_type(event)
        
        # Obter nome do usuário
        user_name = self.get_user_name(user_id)
        
        # Criar timestamp usando os dados brutos
        device_timestamp = self.parse_timestamp(log_data)
        
        if dry_run:
            # Apenas simular
            return True
        
        # Criar log no banco
        with transaction.atomic():
            AccessLog.objects.create(
                device_log_id=log_id,
                user_id=user_id,
                user_name=user_name,
                event_type=event_type,
                event_description=event,
                device_id=1,
                device_name="Catraca Principal",
                portal_id=log_data.get('portal_id'),
                device_timestamp=device_timestamp,
                raw_data=log_data,
                processing_status='processed'
            )
        
        return True

    def map_event_type(self, event):
        """Mapeia evento para tipo de log."""
        event_map = {
            'entry': 1,      # Entrada
            'exit': 2,       # Saída
            'denied': 3,     # Acesso Negado
            'error': 4,      # Erro de Leitura
            'timeout': 5,    # Timeout
            'maintenance': 6, # Manutenção
            'authorized': 7, # Acesso Autorizado
            'blocked': 8,    # Acesso Bloqueado
        }
        return event_map.get(event, 1)  # Entrada por padrão

    def get_user_name(self, user_id):
        """Obtém nome do usuário."""
        try:
            employee = Employee.objects.filter(device_id=user_id).first()
            return employee.name if employee else f"Usuário {user_id}"
        except Exception:
            return f"Usuário {user_id}"

    def parse_timestamp(self, log_data):
        """Converte timestamp para datetime usando o campo 'time' dos dados brutos."""
        try:
            # Usar o campo 'time' dos dados brutos (timestamp Unix)
            if isinstance(log_data, dict) and 'time' in log_data:
                timestamp_unix = log_data['time']
                if timestamp_unix:
                    # Converter timestamp Unix para datetime UTC
                    from datetime import datetime, timezone
                    return datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            
            # Se não conseguir parsear, usar data atual
            from datetime import datetime, timezone
            return datetime.now(timezone.utc)
            
        except Exception as e:
            self.stdout.write(f"   ⚠️ Erro ao parsear timestamp: {e}")
            from datetime import datetime, timezone
            return datetime.now(timezone.utc)
