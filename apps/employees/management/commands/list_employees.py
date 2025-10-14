"""
Comando Django para listar funcionários do banco de dados.
"""
from django.core.management.base import BaseCommand
from apps.employees.models import Employee, EmployeeGroup
from django.db.models import Count


class Command(BaseCommand):
    help = 'Lista funcionários cadastrados no banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limite de funcionários a exibir (padrão: 50)',
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Buscar funcionários por nome',
        )
        parser.add_argument(
            '--group',
            type=str,
            help='Filtrar por nome do grupo',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Mostrar apenas funcionários ativos',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('👥 Listando funcionários...')
        )

        # Construir query
        queryset = Employee.objects.all()
        
        # Aplicar filtros
        if options['search']:
            queryset = queryset.filter(name__icontains=options['search'])
            self.stdout.write(f'🔍 Buscando por: "{options["search"]}"')
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)
            self.stdout.write('✅ Mostrando apenas funcionários ativos')
        
        if options['group']:
            queryset = queryset.filter(groups__name__icontains=options['group'])
            self.stdout.write(f'🏷️ Filtrando por grupo: "{options["group"]}"')

        # Aplicar limite
        limit = options['limit']
        total_count = queryset.count()
        queryset = queryset[:limit]

        # Exibir estatísticas
        self.stdout.write(f'📊 Total de funcionários: {total_count}')
        if limit < total_count:
            self.stdout.write(f'📋 Exibindo {limit} de {total_count} funcionários')

        if not queryset.exists():
            self.stdout.write(self.style.WARNING('⚠️ Nenhum funcionário encontrado'))
            return

        # Exibir funcionários
        self.stdout.write('\n' + '='*80)
        self.stdout.write(f'{"ID":<6} {"Nome":<30} {"Código":<10} {"Status":<8} {"Grupos":<20}')
        self.stdout.write('='*80)

        for employee in queryset:
            status = "✅ Ativo" if employee.is_active else "❌ Inativo"
            exempt = " (Isento)" if employee.is_exempt else ""
            
            # Obter nomes dos grupos (já estão armazenados como nomes)
            groups_str = ", ".join(employee.groups) if employee.groups else "Sem grupos"
            
            self.stdout.write(
                f'{employee.device_id:<6} {employee.name[:29]:<30} {employee.employee_code[:9]:<10} {status:<8} {groups_str[:19]:<20}'
            )

        # Exibir estatísticas de grupos
        self.show_group_statistics()

    def show_group_statistics(self):
        """Exibe estatísticas dos grupos."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('📊 ESTATÍSTICAS DE GRUPOS')
        self.stdout.write('='*50)

        groups = EmployeeGroup.objects.all().order_by('name')

        if not groups.exists():
            self.stdout.write('⚠️ Nenhum grupo encontrado')
            return

        for group in groups:
            # Contar funcionários no grupo usando o campo groups JSON
            # SQLite não suporta contains, então vamos usar uma abordagem diferente
            employee_count = 0
            for employee in Employee.objects.all():
                if group.name in employee.groups:
                    employee_count += 1
            self.stdout.write(f'🏷️ {group.name}: {employee_count} funcionários')

        # Estatísticas gerais
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(is_active=True).count()
        exempt_employees = Employee.objects.filter(is_exempt=True).count()

        self.stdout.write('\n📈 RESUMO GERAL:')
        self.stdout.write(f'  👥 Total de funcionários: {total_employees}')
        self.stdout.write(f'  ✅ Funcionários ativos: {active_employees}')
        self.stdout.write(f'  🆓 Funcionários isentos: {exempt_employees}')
        self.stdout.write(f'  🏷️ Total de grupos: {groups.count()}')
