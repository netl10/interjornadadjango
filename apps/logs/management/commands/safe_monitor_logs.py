"""
Comando Django SEGURO para monitorar logs da catraca sem sobrecarregar.
"""
import time
import json
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee


class Command(BaseCommand):
    help = 'Monitora logs da catraca de forma SEGURA (máximo 100 logs por verificação)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Intervalo de verificação em segundos (padrão: 5, mínimo: 3)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Limite de logs por verificação (padrão: 20, máximo: 100)',
        )
        parser.add_argument(
            '--device-id',
            type=int,
            default=1,
            help='ID do dispositivo para monitorar (padrão: 1)',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Iniciando monitoramento SEGURO de logs da catraca...")
        
        # Configurações seguras
        interval = max(options['interval'], 3)  # Mínimo 3 segundos
        limit = min(options['limit'], 100)  # Máximo 100 logs por verificação
        device_id = options['device_id']
        
        self.stdout.write(f"⚙️ Configurações SEGURAS:")
        self.stdout.write(f"   📊 Intervalo: {interval}s (mínimo: 3s)")
        self.stdout.write(f"   📋 Limite por verificação: {limit} (máximo: 100)")
        self.stdout.write(f"   📱 Dispositivo ID: {device_id}")
        self.stdout.write(f"   ⚠️ Modo SEGURO ativado para proteger a catraca")
        
        # Criar cliente de dispositivo
        try:
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write(self.style.ERROR("❌ Não foi possível conectar à catraca"))
                return
            
            self.stdout.write("✅ Conectado à catraca com sucesso!")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro ao conectar: {e}"))
            return
        
        # Obter último ID processado
        last_processed_id = self.get_last_processed_id()
        self.stdout.write(f"📊 Último ID processado: {last_processed_id}")
        
        # Contadores
        total_processed = 0
        total_errors = 0
        start_time = datetime.now()
        
        self.stdout.write(f"\n🚀 Monitoramento SEGURO iniciado em {start_time.strftime('%H:%M:%S')}")
        self.stdout.write("Pressione Ctrl+C para parar...\n")
        
        try:
            while True:
                try:
                    # Buscar logs novos de forma segura
                    new_logs = client.get_recent_access_logs(limit=limit, min_id=last_processed_id)
                    
                    if new_logs:
                        self.stdout.write(f"📋 {len(new_logs)} logs encontrados")
                        
                        # Processar logs
                        processed_count, error_count = self.process_logs(new_logs, device_id)
                        total_processed += processed_count
                        total_errors += error_count
                        
                        # Atualizar último ID processado
                        if new_logs:
                            last_processed_id = max(log.get('id', 0) for log in new_logs)
                        
                        # Log de progresso
                        if processed_count > 0:
                            self.stdout.write(f"   ✅ {processed_count} logs processados")
                        if error_count > 0:
                            self.stdout.write(f"   ❌ {error_count} erros")
                    else:
                        self.stdout.write("📋 Nenhum log novo encontrado")
                    
                    # Aguardar próximo ciclo (intervalo seguro)
                    self.stdout.write(f"⏳ Aguardando {interval}s para próxima verificação...")
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Erro no ciclo: {e}"))
                    total_errors += 1
                    self.stdout.write(f"⏳ Aguardando {interval}s antes de tentar novamente...")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            pass
        
        # Estatísticas finais
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.stdout.write(f"\n📊 Estatísticas do monitoramento SEGURO:")
        self.stdout.write(f"   ⏱️ Duração: {duration}")
        self.stdout.write(f"   ✅ Logs processados: {total_processed}")
        self.stdout.write(f"   ❌ Erros: {total_errors}")
        if duration.total_seconds() > 0:
            self.stdout.write(f"   📊 Taxa: {total_processed/duration.total_seconds():.2f} logs/segundo")
        
        self.stdout.write(self.style.SUCCESS("✅ Monitoramento SEGURO finalizado"))
    
    def get_last_processed_id(self):
        """Obtém o último ID de log processado."""
        try:
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            return last_log.device_log_id if last_log else 0
        except Exception:
            return 0
    
    def process_logs(self, logs, device_id):
        """Processa uma lista de logs."""
        processed_count = 0
        error_count = 0
        
        for log in logs:
            try:
                if self.process_single_log(log, device_id):
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                self.stdout.write(f"   ❌ Erro ao processar log {log.get('id')}: {e}")
                error_count += 1
        
        return processed_count, error_count
    
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
        
        # Criar timestamp
        device_timestamp = self.parse_timestamp(log_data.get('timestamp'))
        
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
                f"Log processado: {user_name} - {event}",
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
    
    def parse_timestamp(self, timestamp_str):
        """Converte timestamp para datetime."""
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Tentar diferentes formatos
            if 'T' in timestamp_str:
                # Formato ISO
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str[:-1] + '+00:00'
                return datetime.fromisoformat(timestamp_str)
            else:
                # Formato timestamp Unix
                return datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
