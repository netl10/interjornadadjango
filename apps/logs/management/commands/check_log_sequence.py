"""
Comando Django para verificar a sequência de logs e identificar lacunas.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Verifica a sequência de logs e identifica lacunas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-catraca',
            action='store_true',
            help='Verificar também logs disponíveis na catraca',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limite de logs para verificar (padrão: 100)',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando sequência de logs...")
        
        check_catraca = options['check_catraca']
        limit = options['limit']
        
        # Verificar logs no banco
        self.check_database_sequence(limit)
        
        if check_catraca:
            self.check_catraca_sequence(limit)
        
        # Mostrar estatísticas
        self.show_statistics()

    def check_database_sequence(self, limit):
        """Verifica sequência de logs no banco de dados."""
        self.stdout.write("\n📊 VERIFICANDO SEQUÊNCIA NO BANCO DE DADOS:")
        self.stdout.write("=" * 60)
        
        # Buscar logs ordenados por ID
        logs = list(AccessLog.objects.order_by('device_log_id')[:limit])
        
        if not logs:
            self.stdout.write("❌ Nenhum log encontrado no banco")
            return
        
        gaps = []
        last_id = None
        
        for log in logs:
            current_id = log.device_log_id
            
            if last_id is not None:
                expected_id = last_id + 1
                if current_id != expected_id:
                    gap_size = current_id - expected_id
                    gaps.append({
                        'start': expected_id,
                        'end': current_id - 1,
                        'size': gap_size
                    })
                    self.stdout.write(f"⚠️ LACUNA: IDs {expected_id} a {current_id - 1} ({gap_size} logs faltando)")
            
            last_id = current_id
        
        if not gaps:
            self.stdout.write("✅ Sequência no banco está correta!")
        else:
            self.stdout.write(f"❌ Encontradas {len(gaps)} lacunas na sequência")
        
        # Mostrar primeiros e últimos logs
        first_log = logs[0] if logs else None
        last_log = logs[-1] if logs else None
        
        self.stdout.write(f"\n📋 Primeiro log: ID {first_log.device_log_id} - {first_log.user_name}")
        self.stdout.write(f"📋 Último log: ID {last_log.device_log_id} - {last_log.user_name}")
        self.stdout.write(f"📊 Total de logs verificados: {len(logs)}")

    def check_catraca_sequence(self, limit):
        """Verifica sequência de logs na catraca."""
        self.stdout.write("\n📱 VERIFICANDO SEQUÊNCIA NA CATRACA:")
        self.stdout.write("=" * 60)
        
        try:
            # Conectar à catraca
            client = DeviceClient()
            if not client.is_connected():
                self.stdout.write("❌ Não foi possível conectar à catraca")
                return
            
            self.stdout.write("✅ Conectado à catraca com sucesso!")
            
            # Buscar logs da catraca
            logs = client.get_recent_access_logs(limit=limit, min_id=0)
            
            if not logs:
                self.stdout.write("❌ Nenhum log encontrado na catraca")
                return
            
            # Ordenar por ID
            logs.sort(key=lambda x: x['id'])
            
            gaps = []
            last_id = None
            
            for log in logs:
                current_id = log['id']
                
                if last_id is not None:
                    expected_id = last_id + 1
                    if current_id != expected_id:
                        gap_size = current_id - expected_id
                        gaps.append({
                            'start': expected_id,
                            'end': current_id - 1,
                            'size': gap_size
                        })
                        self.stdout.write(f"⚠️ LACUNA: IDs {expected_id} a {current_id - 1} ({gap_size} logs faltando)")
                
                last_id = current_id
            
            if not gaps:
                self.stdout.write("✅ Sequência na catraca está correta!")
            else:
                self.stdout.write(f"❌ Encontradas {len(gaps)} lacunas na sequência")
            
            # Mostrar primeiros e últimos logs
            first_log = logs[0]
            last_log = logs[-1]
            
            self.stdout.write(f"\n📋 Primeiro log: ID {first_log['id']} - {first_log.get('user_id', 'N/A')}")
            self.stdout.write(f"📋 Último log: ID {last_log['id']} - {last_log.get('user_id', 'N/A')}")
            self.stdout.write(f"📊 Total de logs verificados: {len(logs)}")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro ao verificar catraca: {e}")

    def show_statistics(self):
        """Mostra estatísticas gerais."""
        self.stdout.write("\n📊 ESTATÍSTICAS GERAIS:")
        self.stdout.write("=" * 60)
        
        # Estatísticas do banco
        total_logs = AccessLog.objects.count()
        if total_logs > 0:
            first_log = AccessLog.objects.order_by('device_log_id').first()
            last_log = AccessLog.objects.order_by('-device_log_id').first()
            
            self.stdout.write(f"📊 Total de logs no banco: {total_logs}")
            self.stdout.write(f"📋 Faixa de IDs: {first_log.device_log_id} - {last_log.device_log_id}")
            
            # Verificar se há logs recentes
            from datetime import datetime, timezone, timedelta
            recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_logs = AccessLog.objects.filter(device_timestamp__gte=recent_time).count()
            self.stdout.write(f"🕐 Logs da última hora: {recent_logs}")
            
            # Logs por evento
            from django.db.models import Count
            event_stats = AccessLog.objects.values('event_type').annotate(count=Count('id')).order_by('event_type')
            self.stdout.write(f"\n🚪 Logs por evento:")
            for stat in event_stats:
                event_name = self.get_event_name(stat['event_type'])
                self.stdout.write(f"   {event_name}: {stat['count']}")
        else:
            self.stdout.write("❌ Nenhum log encontrado no banco")

    def get_event_name(self, event_type):
        """Obtém nome do evento."""
        event_names = {
            1: 'Entrada',
            2: 'Saída',
            3: 'Acesso Negado',
            4: 'Erro de Leitura',
            5: 'Timeout',
            6: 'Manutenção',
            7: 'Acesso Autorizado',
            8: 'Acesso Bloqueado',
        }
        return event_names.get(event_type, f'Evento {event_type}')
