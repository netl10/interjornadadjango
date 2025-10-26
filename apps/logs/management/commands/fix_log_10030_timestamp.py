"""
Comando Django para corrigir o timestamp do log 10030.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Corrige o timestamp do log 10030 para a data correta'

    def handle(self, *args, **options):
        self.stdout.write("🔧 CORRIGINDO TIMESTAMP DO LOG 10030")
        self.stdout.write("=" * 50)
        
        # Buscar o log 10030
        log = AccessLog.objects.filter(device_log_id=10030).first()
        if not log:
            self.stdout.write(self.style.ERROR("❌ Log 10030 não encontrado!"))
            return
        
        self.stdout.write("📊 Dados atuais:")
        self.stdout.write(f"   ID: {log.device_log_id}")
        self.stdout.write(f"   Usuário: {log.user_name}")
        self.stdout.write(f"   Data/Hora atual: {log.device_timestamp}")
        self.stdout.write(f"   Raw data: {log.raw_data}")
        
        # Calcular timestamp correto (baseado nos logs anteriores)
        # Log 10029: 2025-10-09 19:08:25
        # Log 10030 deveria ser alguns segundos depois
        correct_timestamp = datetime(2025, 10, 9, 19, 58, 38, tzinfo=timezone.utc)
        correct_unix_timestamp = int(correct_timestamp.timestamp())
        
        self.stdout.write(f"\n🔧 Correção:")
        self.stdout.write(f"   Data/Hora correta: {correct_timestamp}")
        self.stdout.write(f"   Timestamp Unix correto: {correct_unix_timestamp}")
        
        # Atualizar o log
        log.device_timestamp = correct_timestamp
        log.raw_data['time'] = correct_unix_timestamp
        log.save()
        
        self.stdout.write(self.style.SUCCESS("✅ Log 10030 corrigido com sucesso!"))
        self.stdout.write(f"   Nova data/hora: {log.device_timestamp}")
        self.stdout.write(f"   Novo raw data: {log.raw_data}")
        
        # Verificar posição após correção
        logs = AccessLog.objects.order_by('-device_timestamp')
        position = None
        for i, l in enumerate(logs):
            if l.device_log_id == 10030:
                position = i + 1
                break
        
        if position:
            self.stdout.write(f"\n📊 Nova posição: {position} de {len(logs)} logs")
            
            # Mostrar logs próximos
            self.stdout.write(f"\n📋 Logs próximos (posições {max(1, position-2)} a {min(len(logs), position+2)}):")
            start = max(0, position-3)
            end = min(len(logs), position+2)
            
            for i in range(start, end):
                l = logs[i]
                marker = "👉" if l.device_log_id == 10030 else "  "
                self.stdout.write(f"   {marker} {i+1}. ID {l.device_log_id}: {l.user_name} - {l.device_timestamp}")
