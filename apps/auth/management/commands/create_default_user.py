from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cria usuário padrão para login'

    def handle(self, *args, **options):
        # Verificar se já existe um usuário admin
        if User.objects.filter(username='admin').exists():
            self.stdout.write(
                self.style.WARNING('Usuário admin já existe')
            )
            return

        # Criar usuário padrão
        user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@sistema.com',
            first_name='Administrador',
            last_name='Sistema',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

        self.stdout.write(
            self.style.SUCCESS(f'Usuário padrão criado com sucesso!')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Usuário: admin')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Senha: admin123')
        )
        self.stdout.write(
            self.style.WARNING('⚠️  IMPORTANTE: Altere a senha padrão em produção!')
        )

