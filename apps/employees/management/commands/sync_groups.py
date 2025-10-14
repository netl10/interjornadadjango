#!/usr/bin/env python
"""
Comando para sincronizar grupos com o estado do sistema.
"""
from django.core.management.base import BaseCommand
from apps.employees.group_service import group_service


class Command(BaseCommand):
    help = 'Sincroniza grupos com o estado do sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força sincronização mesmo se não houver inconsistências',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔄 Iniciando sincronização de grupos...")
        
        try:
            corrected_count = group_service.sync_groups_with_system_state()
            
            if corrected_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Sincronização concluída: {corrected_count} correções aplicadas"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✅ Sincronização concluída: Nenhuma correção necessária"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erro na sincronização: {e}")
            )
            raise
