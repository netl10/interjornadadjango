"""
Comando Django simples para resetar logs.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.logs.models import AccessLog
from apps.logs.services import log_monitor_service


class Command(BaseCommand):
    help = 'Reset simples dos logs'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirma a operação')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING("⚠️  Use --confirm para executar"))
            return
        
        self.stdout.write("🔄 RESET SIMPLES DOS LOGS")
        self.stdout.write("=" * 40)
        
        # Parar monitor
        self.stdout.write("1️⃣ Parando monitor...")
        log_monitor_service.stop_monitoring()
        self.stdout.write("   ✅ Monitor parado")
        
        # Apagar logs
        self.stdout.write("\n2️⃣ Apagando logs...")
        with transaction.atomic():
            count = AccessLog.objects.count()
            AccessLog.objects.all().delete()
            self.stdout.write(f"   ✅ {count} logs apagados")
        
        # Resetar monitor
        self.stdout.write("\n3️⃣ Resetando monitor...")
        log_monitor_service.last_processed_id = 0
        self.stdout.write("   ✅ Monitor resetado")
        
        self.stdout.write(self.style.SUCCESS("\n🎉 RESET COMPLETO!"))
        self.stdout.write("💡 Agora execute: python manage.py load_initial_logs")
