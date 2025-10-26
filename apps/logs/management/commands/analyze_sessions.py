#!/usr/bin/env python
"""
Comando para analisar sessões e verificar se deveriam ter mudado de estado.
"""
from django.core.management.base import BaseCommand
from apps.employees.models import EmployeeSession
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Analisa sessões e verifica se deveriam ter mudado de estado'

    def handle(self, *args, **options):
        self.stdout.write('📊 ANÁLISE DETALHADA DAS SESSÕES...')
        
        # Verificar se há sessões que deveriam ter mudado de estado
        sessoes = EmployeeSession.objects.all()
        
        for sessao in sessoes:
            self.stdout.write(f'\n👤 {sessao.employee.name}:')
            self.stdout.write(f'   Estado: {sessao.get_state_display()}')
            self.stdout.write(f'   First Access: {sessao.first_access}')
            self.stdout.write(f'   Work Duration: {sessao.work_duration_minutes} minutos')
            
            # Calcular tempo decorrido
            tempo_decorrido = timezone.now() - sessao.first_access
            tempo_decorrido_minutos = int(tempo_decorrido.total_seconds() / 60)
            self.stdout.write(f'   Tempo decorrido: {tempo_decorrido_minutos} minutos')
            
            # Verificar se deveria ter mudado de estado
            if sessao.state == 'active' and tempo_decorrido_minutos >= sessao.work_duration_minutes:
                self.stdout.write(self.style.WARNING(f'   ⚠️  DEVERIA TER MUDADO PARA INTERJORNADA!'))
            elif sessao.state == 'blocked' and sessao.return_time and timezone.now() >= sessao.return_time:
                self.stdout.write(self.style.WARNING(f'   ⚠️  DEVERIA TER SIDO REMOVIDA!'))
            else:
                self.stdout.write(self.style.SUCCESS(f'   ✅ Estado correto'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Análise concluída!'))
