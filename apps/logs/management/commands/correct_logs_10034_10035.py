"""
Comando Django para corrigir os logs 10034 e 10035 com os dados corretos.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Corrige os logs 10034 e 10035 com os dados corretos'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔧 CORRIGINDO LOGS 10034 E 10035 COM DADOS CORRETOS")
        self.stdout.write("=" * 60)
        
        try:
            # Corrigir log 10034
            log_10034 = AccessLog.objects.filter(device_log_id=10034).first()
            if log_10034:
                # Dados corretos: ABRAHAO CORREA DA SILVA FILHO, register 245882, 20:34:26
                timestamp_10034 = datetime(2025, 10, 9, 20, 34, 26, tzinfo=timezone.utc)
                
                log_10034.user_id = 1000426
                log_10034.user_name = "ABRAHAO CORREA DA SILVA FILHO"
                log_10034.event_type = 1  # Entrada
                log_10034.event_description = "Entrada"
                log_10034.portal_id = 1  # Portal de Entrada
                log_10034.device_timestamp = timestamp_10034
                log_10034.raw_data = {
                    'id': 10034,
                    'user_id': 1000426,
                    'event': 7,  # Cartão autorizado
                    'time': int(timestamp_10034.timestamp()),
                    'portal_id': 1,
                    'register': 245882
                }
                log_10034.save()
                
                self.stdout.write("✅ Log 10034 corrigido:")
                self.stdout.write(f"   Usuário: {log_10034.user_name}")
                self.stdout.write(f"   User ID: {log_10034.user_id}")
                self.stdout.write(f"   Data/Hora: {log_10034.device_timestamp}")
                self.stdout.write(f"   Evento: {log_10034.event_description}")
                self.stdout.write(f"   Register: 245882")
            else:
                self.stdout.write("❌ Log 10034 não encontrado")
            
            # Corrigir log 10035
            log_10035 = AccessLog.objects.filter(device_log_id=10035).first()
            if log_10035:
                # Dados corretos: ABRAHAO CORREA DA SILVA FILHO, register 245882, 20:36:41
                timestamp_10035 = datetime(2025, 10, 9, 20, 36, 41, tzinfo=timezone.utc)
                
                log_10035.user_id = 1000426
                log_10035.user_name = "ABRAHAO CORREA DA SILVA FILHO"
                log_10035.event_type = 1  # Entrada
                log_10035.event_description = "Entrada"
                log_10035.portal_id = 1  # Portal de Entrada
                log_10035.device_timestamp = timestamp_10035
                log_10035.raw_data = {
                    'id': 10035,
                    'user_id': 1000426,
                    'event': 7,  # Cartão autorizado
                    'time': int(timestamp_10035.timestamp()),
                    'portal_id': 1,
                    'register': 245882
                }
                log_10035.save()
                
                self.stdout.write("✅ Log 10035 corrigido:")
                self.stdout.write(f"   Usuário: {log_10035.user_name}")
                self.stdout.write(f"   User ID: {log_10035.user_id}")
                self.stdout.write(f"   Data/Hora: {log_10035.device_timestamp}")
                self.stdout.write(f"   Evento: {log_10035.event_description}")
                self.stdout.write(f"   Register: 245882")
            else:
                self.stdout.write("❌ Log 10035 não encontrado")
            
            # Resumo
            self.stdout.write(f"\n📊 RESUMO:")
            self.stdout.write(f"   Total de logs no banco: {AccessLog.objects.count()}")
            
            # Mostrar todos os logs
            logs = AccessLog.objects.order_by('-device_log_id')
            self.stdout.write(f"\n📋 Todos os logs:")
            for log in logs:
                self.stdout.write(f"   ID {log.device_log_id}: {log.user_name} - {log.device_timestamp}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 LOGS 10034 E 10035 CORRIGIDOS COM SUCESSO!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
