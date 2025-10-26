"""
Comando Django para corrigir o log 10036 com os dados exatos.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Corrige o log 10036 com os dados exatos'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔧 CORRIGINDO LOG 10036 COM DADOS EXATOS")
        self.stdout.write("=" * 50)
        
        try:
            # Buscar log 10036
            log_10036 = AccessLog.objects.filter(device_log_id=10036).first()
            if not log_10036:
                self.stdout.write("❌ Log 10036 não encontrado no banco")
                return
            
            self.stdout.write("📊 Dados atuais do log 10036:")
            self.stdout.write(f"   Usuário: {log_10036.user_name}")
            self.stdout.write(f"   Data/Hora: {log_10036.device_timestamp}")
            self.stdout.write(f"   Evento: {log_10036.event_description}")
            
            # Corrigir com dados exatos
            # Data/Hora: 09/10/2025 20:46:35 (UTC-3 = 23:46:35 UTC)
            correct_timestamp = datetime(2025, 10, 9, 23, 46, 35, tzinfo=timezone.utc)
            
            log_10036.user_id = 1
            log_10036.user_name = "Diego Lucio"
            log_10036.event_type = 1  # Entrada
            log_10036.event_description = "Entrada"
            log_10036.portal_id = 1  # Portal 1 (Entrada)
            log_10036.device_timestamp = correct_timestamp
            log_10036.raw_data = {
                'id': 10036,
                'user_id': 1,
                'event': 7,  # Evento 7 = Autorizado
                'time': int(correct_timestamp.timestamp()),
                'portal_id': 1
            }
            log_10036.save()
            
            self.stdout.write("✅ Log 10036 corrigido:")
            self.stdout.write(f"   Usuário: {log_10036.user_name}")
            self.stdout.write(f"   Data/Hora: {log_10036.device_timestamp}")
            self.stdout.write(f"   Evento: {log_10036.event_description}")
            self.stdout.write(f"   Portal: Portal 1 (Entrada)")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 LOG 10036 CORRIGIDO COM SUCESSO!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
