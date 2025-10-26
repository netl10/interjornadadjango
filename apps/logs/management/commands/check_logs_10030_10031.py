"""
Comando Django para verificar logs específicos 10030 e 10031.
"""
from django.core.management.base import BaseCommand
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Verifica logs específicos 10030 e 10031 na catraca'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFICANDO LOGS 10030 E 10031 NA CATRACA")
        self.stdout.write("=" * 60)
        
        try:
            client = DeviceClient()
            logs = client.get_recent_access_logs(limit=100)
            
            log_10030 = None
            log_10031 = None
            
            for log in logs:
                if log['id'] == 10030:
                    log_10030 = log
                if log['id'] == 10031:
                    log_10031 = log
            
            self.stdout.write("📊 RESULTADOS:")
            self.stdout.write("")
            
            if log_10030:
                self.stdout.write("✅ Log 10030 encontrado:")
                self.stdout.write(f"   ID: {log_10030['id']}")
                self.stdout.write(f"   User ID: {log_10030['user_id']}")
                self.stdout.write(f"   Event: {log_10030['event']}")
                self.stdout.write(f"   Time: {log_10030['time']}")
                self.stdout.write(f"   Portal ID: {log_10030.get('portal_id', 'N/A')}")
            else:
                self.stdout.write("❌ Log 10030 NÃO encontrado na catraca")
            
            self.stdout.write("")
            
            if log_10031:
                self.stdout.write("✅ Log 10031 encontrado:")
                self.stdout.write(f"   ID: {log_10031['id']}")
                self.stdout.write(f"   User ID: {log_10031['user_id']}")
                self.stdout.write(f"   Event: {log_10031['event']}")
                self.stdout.write(f"   Time: {log_10031['time']}")
                self.stdout.write(f"   Portal ID: {log_10031.get('portal_id', 'N/A')}")
            else:
                self.stdout.write("❌ Log 10031 NÃO encontrado na catraca")
            
            self.stdout.write("")
            
            # Verificar qual é o próximo log esperado
            if log_10030 and log_10031:
                self.stdout.write("🔍 ANÁLISE:")
                if log_10030['time'] > log_10031['time']:
                    self.stdout.write("   Log 10030 é mais recente que 10031")
                    self.stdout.write("   Próximo log esperado: 10031")
                else:
                    self.stdout.write("   Log 10031 é mais recente que 10030")
                    self.stdout.write("   Próximo log esperado: 10032")
            elif log_10030 and not log_10031:
                self.stdout.write("   Log 10030 existe, próximo esperado: 10031")
            elif log_10031 and not log_10030:
                self.stdout.write("   Log 10030 não existe, próximo esperado: 10031")
            else:
                self.stdout.write("   Nenhum dos logs encontrado")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro ao verificar logs: {e}"))
