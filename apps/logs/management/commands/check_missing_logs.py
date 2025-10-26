"""
Comando para verificar logs faltantes na sequência.
"""
from django.core.management.base import BaseCommand
from apps.logs.models import AccessLog
from apps.devices.device_client import DeviceClient


class Command(BaseCommand):
    help = 'Verifica logs faltantes na sequência e tenta recuperá-los da catraca'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Verificando logs faltantes na sequência...')
        
        # Obter todos os logs do banco
        logs = AccessLog.objects.order_by('device_log_id')
        if not logs:
            self.stdout.write('Nenhum log encontrado no banco')
            return
        
        ids_presentes = [log.device_log_id for log in logs]
        primeiro_id = min(ids_presentes)
        ultimo_id = max(ids_presentes)
        
        self.stdout.write(f'Primeiro ID: {primeiro_id}')
        self.stdout.write(f'Último ID: {ultimo_id}')
        self.stdout.write(f'Total de logs no banco: {len(ids_presentes)}')
        
        # Encontrar lacunas
        ids_esperados = set(range(primeiro_id, ultimo_id + 1))
        ids_faltantes = ids_esperados - set(ids_presentes)
        
        if not ids_faltantes:
            self.stdout.write(self.style.SUCCESS('✅ Nenhuma lacuna encontrada - sequência está íntegra!'))
            return
        
        self.stdout.write(f'⚠️ Lacunas encontradas: {sorted(ids_faltantes)}')
        
        # Tentar recuperar da catraca
        self.stdout.write('\n🔄 Tentando recuperar logs faltantes da catraca...')
        
        try:
            client = DeviceClient()
            if not client.login():
                self.stdout.write(self.style.ERROR('❌ Falha ao conectar com a catraca'))
                return
            
            # Buscar logs da catraca
            logs_catraca = client.get_recent_access_logs(limit=100, min_id=primeiro_id-10)
            logs_catraca_ids = {log['id'] for log in logs_catraca}
            
            self.stdout.write(f'Logs encontrados na catraca: {len(logs_catraca_ids)}')
            
            # Verificar quais logs faltantes existem na catraca
            logs_recuperaveis = ids_faltantes & logs_catraca_ids
            
            if logs_recuperaveis:
                self.stdout.write(f'Logs recuperáveis da catraca: {sorted(logs_recuperaveis)}')
                
                # Mostrar detalhes dos logs recuperáveis
                for log_data in logs_catraca:
                    if log_data['id'] in logs_recuperaveis:
                        user_id = log_data.get('user_id', 0)
                        event = log_data.get('event', 0)
                        portal = log_data.get('portal_id', 0)
                        self.stdout.write(f'   ID {log_data["id"]}: user_id={user_id}, event={event}, portal={portal}')
            else:
                self.stdout.write('Nenhum log faltante encontrado na catraca')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao verificar catraca: {e}'))
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Para recuperar logs faltantes, execute:')
        self.stdout.write('python manage.py access_log_worker restart')