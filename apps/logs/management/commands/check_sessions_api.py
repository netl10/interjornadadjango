"""
Comando para verificar a API de sessões.
"""
from django.core.management.base import BaseCommand
from apps.employee_sessions.models import EmployeeSession
from apps.employee_sessions.views import api_sessoes_ativas
from django.test import RequestFactory
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Verifica a API de sessões'

    def handle(self, *args, **options):
        # Verificar sessões no banco
        sessions = EmployeeSession.objects.filter(
            state__in=['active', 'blocked', 'pending_rest']
        ).select_related('employee').order_by('-created_at')
        
        self.stdout.write(f'Total de sessões ativas no banco: {sessions.count()}')
        
        for session in sessions:
            self.stdout.write(f'  - Sessão {session.id}: {session.employee.name} - {session.state}')
        
        # Testar a API diretamente
        factory = RequestFactory()
        request = factory.get('/admin/sessions/api/sessoes-ativas/')
        
        # Criar um usuário admin para o teste
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        request.user = user
        
        try:
            response = api_sessoes_ativas(request)
            self.stdout.write(f'Status da API: {response.status_code}')
            if hasattr(response, 'content'):
                self.stdout.write(f'Conteúdo: {response.content.decode()}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro na API: {e}'))
