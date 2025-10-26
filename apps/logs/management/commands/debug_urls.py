"""
Comando Django para debugar URLs.
"""
from django.core.management.base import BaseCommand
from django.urls import reverse, resolve


class Command(BaseCommand):
    help = 'Debuga URLs do sistema'

    def handle(self, *args, **options):
        self.stdout.write("🔍 DEBUGANDO URLs")
        self.stdout.write("=" * 30)
        
        try:
            # Testar reverse URL
            url = reverse('logs:realtime_monitor')
            self.stdout.write(f"✅ Reverse URL: {url}")
        except Exception as e:
            self.stdout.write(f"❌ Erro reverse: {e}")
        
        try:
            # Testar resolve URL
            resolved = resolve('/admin/logs/realtime/')
            self.stdout.write(f"✅ Resolve: {resolved.func.__name__}")
        except Exception as e:
            self.stdout.write(f"❌ Erro resolve: {e}")
        
        # Listar todas as URLs do app logs
        from django.conf import settings
        from django.urls import get_resolver
        
        resolver = get_resolver()
        self.stdout.write("\n📋 URLs do app logs:")
        
        try:
            for pattern in resolver.url_patterns:
                if hasattr(pattern, 'app_name') and pattern.app_name == 'logs':
                    self.stdout.write(f"  - {pattern.pattern}")
        except Exception as e:
            self.stdout.write(f"❌ Erro ao listar URLs: {e}")
