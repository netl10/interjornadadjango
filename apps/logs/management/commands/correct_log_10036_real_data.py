"""
Comando Django para corrigir o log 10036 com os dados reais da catraca.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Corrige o log 10036 com os dados reais da catraca'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔧 CORRIGINDO LOG 10036 COM DADOS REAIS DA CATRACA")
        self.stdout.write("=" * 60)
        
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
            
            # Corrigir com dados reais da catraca
            # Data/Hora: 09/10/2025 20:42:45 (UTC-3 = 23:42:45 UTC)
            correct_timestamp = datetime(2025, 10, 9, 23, 42, 45, tzinfo=timezone.utc)
            
            log_10036.user_id = 1000426
            log_10036.user_name = "ABRAHAO CORREA DA SILVA FILHO"
            log_10036.event_type = 1  # Entrada
            log_10036.event_description = "Entrada"
            log_10036.portal_id = 1  # Portal de Entrada
            log_10036.device_timestamp = correct_timestamp
            log_10036.raw_data = {
                'id': 10036,
                'user_id': 1000426,
                'event': 7,  # Cartão autorizado
                'time': int(correct_timestamp.timestamp()),
                'portal_id': 1,
                'register': 245882
            }
            log_10036.save()
            
            self.stdout.write("✅ Log 10036 corrigido com dados reais:")
            self.stdout.write(f"   Usuário: {log_10036.user_name}")
            self.stdout.write(f"   User ID: {log_10036.user_id}")
            self.stdout.write(f"   Data/Hora: {log_10036.device_timestamp}")
            self.stdout.write(f"   Evento: {log_10036.event_description}")
            self.stdout.write(f"   Portal: Portal de Entrada")
            self.stdout.write(f"   Register: 245882")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 LOG 10036 CORRIGIDO COM DADOS REAIS!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
