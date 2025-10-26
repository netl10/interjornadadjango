"""
Comando Django para encontrar a posição de um log específico.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog


class Command(BaseCommand):
    help = 'Encontra a posição de um log específico na ordenação'

    def add_arguments(self, parser):
        parser.add_argument('log_id', type=int, help='ID do log para encontrar')

    def handle(self, *args, **options):
        log_id = options['log_id']
        
        self.stdout.write(f"🔍 PROCURANDO LOG ID {log_id}")
        self.stdout.write("=" * 50)
        
        # Verificar se o log existe
        log = AccessLog.objects.filter(device_log_id=log_id).first()
        if not log:
            self.stdout.write(self.style.ERROR(f"❌ Log ID {log_id} não encontrado!"))
            return
        
        # Encontrar posição na ordenação por device_timestamp
        logs = AccessLog.objects.order_by('-device_timestamp')
        position = None
        
        for i, l in enumerate(logs):
            if l.device_log_id == log_id:
                position = i + 1
                break
        
        if position:
            self.stdout.write(f"✅ Log ID {log_id} encontrado!")
            self.stdout.write(f"   Posição: {position} de {len(logs)} logs")
            self.stdout.write(f"   Usuário: {log.user_name}")
            self.stdout.write(f"   Data/Hora: {log.device_timestamp}")
            self.stdout.write(f"   Evento: {log.event_description}")
            
            # Mostrar logs próximos
            self.stdout.write(f"\n📋 Logs próximos (posições {max(1, position-2)} a {min(len(logs), position+2)}):")
            start = max(0, position-3)
            end = min(len(logs), position+2)
            
            for i in range(start, end):
                l = logs[i]
                marker = "👉" if l.device_log_id == log_id else "  "
                self.stdout.write(f"   {marker} {i+1}. ID {l.device_log_id}: {l.user_name} - {l.device_timestamp}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Log ID {log_id} não encontrado na ordenação!"))
