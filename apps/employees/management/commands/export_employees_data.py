"""
Comando Django para exportar dados de funcionários (ID e matrícula) em CSV.
"""
import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.employees.models import Employee


class Command(BaseCommand):
    help = 'Exporta dados de funcionários (ID e matrícula) para CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='funcionarios_export.csv',
            help='Nome do arquivo de saída (padrão: funcionarios_export.csv)',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Exportar apenas funcionários ativos',
        )
        parser.add_argument(
            '--group',
            type=str,
            help='Filtrar por nome do grupo',
        )

    def handle(self, *args, **options):
        self.stdout.write("📊 Exportando dados de funcionários...")
        
        # Filtrar funcionários
        employees = Employee.objects.all()
        
        if options['active_only']:
            employees = employees.filter(is_active=True)
            self.stdout.write("🔍 Filtrando apenas funcionários ativos...")
        
        if options['group']:
            # SQLite não suporta contains, então vamos usar uma abordagem diferente
            filtered_employees = []
            for employee in employees:
                if options['group'] in employee.groups:
                    filtered_employees.append(employee)
            employees = filtered_employees
            self.stdout.write(f"🔍 Filtrando por grupo: {options['group']}")
        
        # Caminho do arquivo
        output_file = options['output']
        if not output_file.endswith('.csv'):
            output_file += '.csv'
        
        # Caminho completo
        output_path = os.path.join(settings.BASE_DIR, output_file)
        
        # Escrever CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ID_Dispositivo', 'Nome', 'Matricula', 'Status', 'Grupos']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Escrever cabeçalho
            writer.writeheader()
            
            # Escrever dados
            for employee in employees:
                groups_str = ", ".join(employee.groups) if employee.groups else "Sem grupos"
                status = "Ativo" if employee.is_active else "Inativo"
                
                writer.writerow({
                    'ID_Dispositivo': employee.device_id,
                    'Nome': employee.name,
                    'Matricula': employee.employee_code,
                    'Status': status,
                    'Grupos': groups_str
                })
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Exportação concluída!\n"
                f"📁 Arquivo: {output_path}\n"
                f"📊 {len(employees)} funcionários exportados"
            )
        )
        
        # Mostrar estatísticas
        self.stdout.write("\n📈 ESTATÍSTICAS:")
        self.stdout.write(f"  👥 Total de funcionários: {len(employees)}")
        
        # Contar por status
        active_count = sum(1 for emp in employees if emp.is_active)
        inactive_count = len(employees) - active_count
        self.stdout.write(f"  ✅ Ativos: {active_count}")
        self.stdout.write(f"  ❌ Inativos: {inactive_count}")
        
        # Contar por grupos
        group_counts = {}
        for employee in employees:
            for group in employee.groups:
                group_counts[group] = group_counts.get(group, 0) + 1
        
        if group_counts:
            self.stdout.write("  🏷️ Por grupos:")
            for group, count in group_counts.items():
                self.stdout.write(f"    - {group}: {count}")
        
        # Mostrar primeiras linhas do arquivo
        self.stdout.write(f"\n📋 Primeiras 5 linhas do arquivo:")
        with open(output_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i < 6:  # Cabeçalho + 5 linhas
                    self.stdout.write(f"  {i}: {', '.join(row)}")
                else:
                    break
