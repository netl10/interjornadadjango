"""
Comando Django para sincronizar funcionários da catraca com o banco de dados.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.devices.models import Device
from apps.devices.device_client import DeviceClient
from apps.employees.models import Employee, EmployeeGroup
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza funcionários da catraca com o banco de dados Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            type=int,
            help='ID do dispositivo para sincronizar (opcional)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a sincronização mesmo se já existirem funcionários',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa sem fazer alterações no banco de dados',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔄 Iniciando sincronização de funcionários...')
        )

        try:
            # Buscar dispositivo
            device = self.get_device(options.get('device_id'))
            
            # Verificar se já existem funcionários
            if not options['force'] and Employee.objects.exists():
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️ Já existem funcionários no banco. Use --force para sobrescrever.'
                    )
                )
                return

            # Executar sincronização
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('🧪 Modo dry-run: Nenhuma alteração será feita')
                )
                self.dry_run_sync(device)
            else:
                self.sync_employees(device)

        except Exception as e:
            raise CommandError(f'Erro na sincronização: {e}')

    def get_device(self, device_id=None):
        """Obtém o dispositivo para sincronização."""
        if device_id:
            try:
                device = Device.objects.get(id=device_id)
            except Device.DoesNotExist:
                raise CommandError(f'Dispositivo com ID {device_id} não encontrado')
        else:
            # Buscar dispositivo primário
            device = Device.objects.filter(device_type='primary').first()
            if not device:
                raise CommandError('Nenhum dispositivo primário encontrado')

        self.stdout.write(f'📱 Usando dispositivo: {device.name} ({device.ip_address}:{device.port})')
        return device

    def dry_run_sync(self, device):
        """Executa sincronização em modo dry-run."""
        client = DeviceClient(device)
        
        if not client.is_connected():
            raise CommandError('Não foi possível conectar ao dispositivo')

        # Buscar usuários da catraca
        self.stdout.write('📥 Buscando usuários da catraca...')
        users = client.get_users()
        
        if not users:
            self.stdout.write(self.style.WARNING('⚠️ Nenhum usuário encontrado na catraca'))
            return

        self.stdout.write(f'👥 Encontrados {len(users)} usuários na catraca:')
        
        for user in users[:10]:  # Mostrar apenas os primeiros 10
            self.stdout.write(f'  - ID: {user.get("id")}, Nome: {user.get("name")}')
        
        if len(users) > 10:
            self.stdout.write(f'  ... e mais {len(users) - 10} usuários')

        # Buscar grupos da catraca
        self.stdout.write('🏷️ Buscando grupos da catraca...')
        groups = client.get_groups()
        
        if groups:
            self.stdout.write(f'📋 Encontrados {len(groups)} grupos:')
            for group in groups:
                self.stdout.write(f'  - ID: {group.get("id")}, Nome: {group.get("name")}')

    @transaction.atomic
    def sync_employees(self, device):
        """Executa a sincronização real dos funcionários."""
        client = DeviceClient(device)
        
        if not client.is_connected():
            raise CommandError('Não foi possível conectar ao dispositivo')

        # Limpar funcionários existentes se forçado
        if Employee.objects.exists():
            self.stdout.write('🗑️ Limpando funcionários existentes...')
            Employee.objects.all().delete()
            EmployeeGroup.objects.all().delete()

        # Sincronizar grupos primeiro
        self.sync_groups(client)
        
        # Sincronizar funcionários
        self.sync_users(client)

        self.stdout.write(
            self.style.SUCCESS('✅ Sincronização concluída com sucesso!')
        )

    def sync_groups(self, client):
        """Sincroniza grupos da catraca."""
        self.stdout.write('🏷️ Sincronizando grupos...')
        
        groups = client.get_groups()
        if not groups:
            self.stdout.write(self.style.WARNING('⚠️ Nenhum grupo encontrado'))
            return

        created_count = 0
        for group_data in groups:
            group, created = EmployeeGroup.objects.get_or_create(
                device_group_id=group_data.get('id'),
                defaults={
                    'name': group_data.get('name', f'Grupo {group_data.get("id")}'),
                    'description': f'Grupo sincronizado da catraca',
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Criado grupo: {group.name}')

        self.stdout.write(f'📊 {created_count} grupos criados')

    def sync_users(self, client):
        """Sincroniza usuários da catraca."""
        self.stdout.write('👥 Sincronizando funcionários...')
        
        users = client.get_users()
        if not users:
            self.stdout.write(self.style.WARNING('⚠️ Nenhum usuário encontrado'))
            return

        created_count = 0
        updated_count = 0
        
        for user_data in users:
            # Pular usuário 0 (sistema)
            if user_data.get('id') == 0:
                continue

            # Buscar grupos do usuário
            user_groups = client.get_user_groups(user_data.get('id'))
            group_ids = [g.get('group_id') for g in user_groups if g.get('group_id')]
            
            # Mapear grupos do dispositivo para grupos Django
            django_groups = EmployeeGroup.objects.filter(
                device_group_id__in=group_ids
            )
            group_names = [g.name for g in django_groups]

            # Usar registration como matrícula (employee_code)
            matricula = user_data.get('registration', '')
            if not matricula:
                # Se não tem matrícula, usar ID do dispositivo
                matricula = f"ID_{user_data.get('id')}"
            else:
                # Verificar se a matrícula já existe
                counter = 1
                original_matricula = matricula
                while Employee.objects.filter(employee_code=matricula).exists():
                    matricula = f"{original_matricula}_{counter}"
                    counter += 1

            employee, created = Employee.objects.get_or_create(
                device_id=user_data.get('id'),
                defaults={
                    'name': user_data.get('name', f'Usuário {user_data.get("id")}'),
                    'employee_code': matricula,
                    'is_active': True,
                    'is_exempt': False,
                    'groups': group_names,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Criado: {employee.name} (ID: {employee.device_id})')
            else:
                # Atualizar dados existentes
                employee.name = user_data.get('name', employee.name)
                employee.employee_code = matricula
                employee.groups = group_names
                employee.save()
                updated_count += 1
                self.stdout.write(f'  🔄 Atualizado: {employee.name} (ID: {employee.device_id})')

        self.stdout.write(f'📊 {created_count} funcionários criados, {updated_count} atualizados')

    def get_user_groups_info(self, client, user_id):
        """Obtém informações dos grupos de um usuário."""
        try:
            user_groups = client.get_user_groups(user_id)
            return user_groups
        except Exception as e:
            logger.warning(f'Erro ao buscar grupos do usuário {user_id}: {e}')
            return []
