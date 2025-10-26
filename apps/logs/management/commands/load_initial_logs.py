"""
Comando Django para carregar logs iniciais das últimas 48 horas.
"""
import time
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.devices.device_client import DeviceClient
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee


class Command(BaseCommand):
    help = 'Carrega logs iniciais das últimas 48 horas no banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=48,
            help='Número de horas para buscar logs (padrão: 48)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Tamanho do lote para processamento (padrão: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simular, não salvar no banco',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        batch_size = min(options['batch_size'], 1000)  # Máximo 1000 por lote
        dry_run = options['dry_run']
        
        self.stdout.write(f"🔄 Carregando logs das últimas {hours} horas...")
        
        if dry_run:
            self.stdout.write("⚠️ MODO DRY-RUN: Apenas simulando, não salvando no banco")
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write(self.style.ERROR("❌ Não foi possível conectar à catraca"))
                return
            
            self.stdout.write("✅ Conectado à catraca com sucesso!")
            
            # Calcular timestamp de 48 horas atrás
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            self.stdout.write(f"📅 Buscando logs a partir de: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Verificar se já existem logs no banco
            existing_logs = AccessLog.objects.count()
            if existing_logs > 0:
                self.stdout.write(f"⚠️ Já existem {existing_logs} logs no banco")
                response = input("Deseja continuar mesmo assim? (s/N): ")
                if response.lower() != 's':
                    self.stdout.write("❌ Operação cancelada")
                    return
            
            # Buscar logs em lotes
            total_processed = 0
            total_saved = 0
            total_errors = 0
            start_id = 0
            
            self.stdout.write(f"📊 Processando em lotes de {batch_size} logs...")
            
            while True:
                # Buscar próximo lote
                logs = client.get_recent_access_logs(limit=batch_size, min_id=start_id)
                
                if not logs:
                    self.stdout.write("📋 Nenhum log encontrado - carregamento concluído")
                    break
                
                # Filtrar logs das últimas 48 horas
                recent_logs = []
                for log in logs:
                    log_timestamp = self.parse_timestamp(log.get('timestamp'))
                    if log_timestamp and log_timestamp >= cutoff_time:
                        recent_logs.append(log)
                
                if not recent_logs:
                    self.stdout.write("📋 Nenhum log recente encontrado neste lote")
                    start_id = max(log.get('id', 0) for log in logs)
                    continue
                
                self.stdout.write(f"📋 Processando {len(recent_logs)} logs recentes (de {len(logs)} total)")
                
                # Processar logs
                saved_count, error_count = self.process_logs_batch(recent_logs, dry_run)
                total_saved += saved_count
                total_errors += error_count
                total_processed += len(recent_logs)
                
                # Atualizar start_id para próximo lote
                start_id = max(log.get('id', 0) for log in logs)
                
                # Mostrar progresso
                self.stdout.write(f"   ✅ {saved_count} logs salvos, ❌ {error_count} erros")
                
                # Pausa entre lotes para não sobrecarregar
                time.sleep(1)
            
            # Estatísticas finais
            self.stdout.write(f"\n📊 RESUMO DO CARREGAMENTO:")
            self.stdout.write(f"   📋 Logs processados: {total_processed}")
            self.stdout.write(f"   ✅ Logs salvos: {total_saved}")
            self.stdout.write(f"   ❌ Erros: {total_errors}")
            
            if not dry_run and total_saved > 0:
                # Log do sistema
                SystemLog.log_info(
                    f"Carregamento inicial de logs concluído: {total_saved} logs das últimas {hours}h",
                    category='system',
                    details={
                        'total_processed': total_processed,
                        'total_saved': total_saved,
                        'total_errors': total_errors,
                        'hours': hours
                    }
                )
                
                self.stdout.write(self.style.SUCCESS(f"✅ Carregamento inicial concluído com sucesso!"))
            else:
                self.stdout.write(self.style.WARNING("⚠️ Modo dry-run - nenhum log foi salvo"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro durante carregamento: {e}"))
            import traceback
            traceback.print_exc()
    
    def process_logs_batch(self, logs, dry_run=False):
        """Processa um lote de logs."""
        saved_count = 0
        error_count = 0
        
        for log in logs:
            try:
                if self.process_single_log(log, dry_run):
                    saved_count += 1
                else:
                    error_count += 1
            except Exception as e:
                self.stdout.write(f"   ❌ Erro ao processar log {log.get('id')}: {e}")
                error_count += 1
        
        return saved_count, error_count
    
    def process_single_log(self, log_data, dry_run=False):
        """Processa um único log."""
        log_id = log_data.get('id')
        user_id = log_data.get('user_id')
        event = log_data.get('event')
        
        # Verificar se já foi processado
        if not dry_run and AccessLog.objects.filter(device_log_id=log_id).exists():
            return False  # Já processado
        
        # Ignorar logs de sistema (user_id = 0) se necessário
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
            print(f"   ⚠️ Erro ao parsear timestamp: {e}")
            return datetime.now(timezone.utc)
