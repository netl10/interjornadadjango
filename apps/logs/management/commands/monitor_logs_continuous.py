"""
Comando Django para monitoramento contínuo de logs com sequência correta.
"""
import time
import signal
import sys
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee


class Command(BaseCommand):
    help = 'Monitora logs da catraca continuamente, processando apenas logs novos em sequência'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        self.client = None
        self.last_processed_id = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Intervalo de verificação em segundos (padrão: 5)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Tamanho do lote para processamento (padrão: 50)',
        )
        parser.add_argument(
            '--device-id',
            type=int,
            default=1,
            help='ID do dispositivo para monitorar (padrão: 1)',
        )
        parser.add_argument(
            '--start-from-last',
            action='store_true',
            help='Começar a partir do último log processado no banco',
        )
        parser.add_argument(
            '--force-start-id',
            type=int,
            help='Forçar início a partir de um ID específico',
        )

    def handle(self, *args, **options):
        # Configurar handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        interval = max(options['interval'], 3)  # Mínimo 3 segundos
        batch_size = min(options['batch_size'], 100)  # Máximo 100 logs por lote
        device_id = options['device_id']
        start_from_last = options['start_from_last']
        force_start_id = options.get('force_start_id')
        
        self.stdout.write("🔄 Iniciando monitoramento contínuo de logs...")
        self.stdout.write(f"⚙️ Configurações:")
        self.stdout.write(f"   📊 Intervalo: {interval}s")
        self.stdout.write(f"   📋 Tamanho do lote: {batch_size}")
        self.stdout.write(f"   📱 Dispositivo ID: {device_id}")
        
        try:
            # Conectar à catraca
            self.client = DeviceClient()
            if not self.client.is_connected():
                self.stdout.write(self.style.ERROR("❌ Não foi possível conectar à catraca"))
                return
            
            self.stdout.write("✅ Conectado à catraca com sucesso!")
            
            # Determinar ID inicial
            if force_start_id:
                self.last_processed_id = force_start_id
                self.stdout.write(f"🎯 ID inicial forçado: {self.last_processed_id}")
            elif start_from_last:
                self.last_processed_id = self.get_last_processed_id()
                self.stdout.write(f"📊 Último ID processado no banco: {self.last_processed_id}")
            else:
                # Buscar o menor ID disponível na catraca
                self.last_processed_id = self.get_min_available_id()
                self.stdout.write(f"🔍 Menor ID disponível na catraca: {self.last_processed_id}")
            
            # Contadores
            total_processed = 0
            total_saved = 0
            total_errors = 0
            start_time = datetime.now()
            
            self.stdout.write(f"\n🚀 Monitoramento iniciado em {start_time.strftime('%H:%M:%S')}")
            self.stdout.write("Pressione Ctrl+C para parar...\n")
            
            self.running = True
            
            while self.running:
                try:
                    # Buscar logs novos em sequência
                    new_logs = self.get_logs_in_sequence(batch_size)
                    
                    if new_logs:
                        self.stdout.write(f"📋 {len(new_logs)} logs encontrados (ID {new_logs[0]['id']} - {new_logs[-1]['id']})")
                        
                        # Processar logs em sequência
                        saved_count, error_count, sequence_errors = self.process_logs_sequence(new_logs, device_id)
                        total_saved += saved_count
                        total_errors += error_count
                        
                        # Atualizar último ID processado
                        if new_logs:
                            self.last_processed_id = new_logs[-1]['id']
                        
                        # Log de progresso
                        if saved_count > 0:
                            self.stdout.write(f"   ✅ {saved_count} logs salvos")
                        if error_count > 0:
                            self.stdout.write(f"   ❌ {error_count} erros")
                        if sequence_errors > 0:
                            self.stdout.write(f"   ⚠️ {sequence_errors} erros de sequência")
                        
                        # Reset contador de erros consecutivos
                        self.consecutive_errors = 0
                    else:
                        # Mostrar status a cada 10 ciclos sem logs
                        if total_processed % 10 == 0:
                            self.stdout.write(f"📋 Nenhum log novo encontrado (último ID: {self.last_processed_id})")
                    
                    # Aguardar próximo ciclo
                    time.sleep(interval)
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Erro no ciclo: {e}"))
                    self.consecutive_errors += 1
                    total_errors += 1
                    
                    # Se muitos erros consecutivos, parar
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        self.stdout.write(self.style.ERROR(f"❌ Muitos erros consecutivos ({self.consecutive_errors}). Parando monitoramento."))
                        break
                    
                    self.stdout.write(f"⏳ Aguardando {interval}s antes de tentar novamente...")
                    time.sleep(interval)
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro crítico: {e}"))
        
        finally:
            # Estatísticas finais
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.stdout.write(f"\n📊 Estatísticas do monitoramento:")
            self.stdout.write(f"   ⏱️ Duração: {duration}")
            self.stdout.write(f"   📋 Logs processados: {total_processed}")
            self.stdout.write(f"   ✅ Logs salvos: {total_saved}")
            self.stdout.write(f"   ❌ Erros: {total_errors}")
            self.stdout.write(f"   🎯 Último ID processado: {self.last_processed_id}")
            if duration.total_seconds() > 0:
                self.stdout.write(f"   📊 Taxa: {total_saved/duration.total_seconds():.2f} logs/segundo")
            
            self.stdout.write(self.style.SUCCESS("✅ Monitoramento finalizado"))
    
    def signal_handler(self, signum, frame):
        """Handler para sinais de interrupção."""
        self.stdout.write(f"\n🛑 Recebido sinal {signum}, finalizando monitoramento...")
        self.running = False
    
    def get_last_processed_id(self):
        """Obtém o último ID de log processado no banco."""
        try:
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            return last_log.device_log_id if last_log else 0
        except Exception:
            return 0
    
    def get_min_available_id(self):
        """Obtém o menor ID disponível na catraca."""
        try:
            # Buscar alguns logs para encontrar o menor ID
            logs = self.client.get_recent_access_logs(limit=100, min_id=0)
            if logs:
                return min(log['id'] for log in logs)
            return 0
        except Exception:
            return 0
    
    def get_logs_in_sequence(self, batch_size):
        """Busca logs em sequência a partir do último ID processado."""
        try:
            # Buscar logs a partir do próximo ID
            next_id = self.last_processed_id + 1
            logs = self.client.get_recent_access_logs(limit=batch_size, min_id=next_id)
            
            if not logs:
                return []
            
            # Verificar se os logs estão em sequência
            expected_id = next_id
            sequence_logs = []
            
            for log in logs:
                log_id = log['id']
                
                # Se o ID não for o esperado, há uma lacuna
                if log_id != expected_id:
                    self.stdout.write(f"⚠️ Lacuna na sequência: esperado {expected_id}, encontrado {log_id}")
                    # Parar aqui para não processar logs fora de sequência
                    break
                
                sequence_logs.append(log)
                expected_id += 1
            
            return sequence_logs
            
        except Exception as e:
            self.stdout.write(f"❌ Erro ao buscar logs em sequência: {e}")
            return []
    
    def process_logs_sequence(self, logs, device_id):
        """Processa uma lista de logs em sequência."""
        saved_count = 0
        error_count = 0
        sequence_errors = 0
        
        for i, log in enumerate(logs):
            try:
                # Verificar se o log está na sequência esperada
                expected_id = self.last_processed_id + i + 1
                if log['id'] != expected_id:
                    self.stdout.write(f"⚠️ Erro de sequência: esperado {expected_id}, encontrado {log['id']}")
                    sequence_errors += 1
                    continue
                
                if self.process_single_log(log, device_id):
                    saved_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(f"   ❌ Erro ao processar log {log.get('id')}: {e}")
                error_count += 1
        
        return saved_count, error_count, sequence_errors
    
    def process_single_log(self, log_data, device_id):
        """Processa um único log."""
        log_id = log_data.get('id')
        user_id = log_data.get('user_id')
        event = log_data.get('event')
        
        # Verificar se já foi processado
        if AccessLog.objects.filter(device_log_id=log_id).exists():
            return False  # Já processado
        
        # Ignorar logs de sistema (user_id = 0)
        if user_id == 0:
            return False
        
        # Mapear evento para tipo
        event_type = self.map_event_type(event)
        
        # Obter nome do usuário
        user_name = self.get_user_name(user_id)
        
        # Criar timestamp usando os dados brutos
        device_timestamp = self.parse_timestamp(log_data)
        
        # Criar log no banco
        with transaction.atomic():
            access_log = AccessLog.objects.create(
                device_log_id=log_id,
                user_id=user_id,
                user_name=user_name,
                event_type=event_type,
                event_description=event,
                device_id=device_id,
                device_name="Catraca Principal",
                portal_id=log_data.get('portal_id'),
                device_timestamp=device_timestamp,
                raw_data=log_data,
                processing_status='processed'
            )
            
            # Log do sistema
            SystemLog.log_info(
                f"Log processado: {user_name} - {event} (ID: {log_id})",
                category='device',
                user_id=user_id,
                user_name=user_name,
                device_id=device_id,
                details={'log_id': log_id, 'event': event}
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
                    return datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            
            # Fallback: tentar campo 'timestamp' se existir
            if isinstance(log_data, dict) and 'timestamp' in log_data:
                timestamp_str = log_data['timestamp']
                if timestamp_str:
                    if 'T' in timestamp_str:
                        # Formato ISO
                        if timestamp_str.endswith('Z'):
                            timestamp_str = timestamp_str[:-1] + '+00:00'
                        return datetime.fromisoformat(timestamp_str)
                    else:
                        # Formato timestamp Unix
                        return datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
            
            # Se não conseguir parsear, usar data atual
            return datetime.now(timezone.utc)
            
        except Exception as e:
            self.stdout.write(f"   ⚠️ Erro ao parsear timestamp: {e}")
            return datetime.now(timezone.utc)
