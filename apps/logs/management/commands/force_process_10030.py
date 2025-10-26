"""
Comando Django para forçar o processamento do log ID 10030.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.logs.models import AccessLog, SystemLog
from apps.employees.models import Employee
from datetime import datetime, timezone


class Command(BaseCommand):
    help = 'Força o processamento do log ID 10030'

    def handle(self, *args, **options):
        self.stdout.write("🔧 FORÇANDO PROCESSAMENTO DO LOG ID 10030")
        self.stdout.write("=" * 50)
        
        # Verificar se já existe no banco
        existing_log = AccessLog.objects.filter(device_log_id=10030).first()
        if existing_log:
            self.stdout.write("ℹ️ Log ID 10030 já existe no banco:")
            self.stdout.write(f"   Usuário: {existing_log.user_name}")
            self.stdout.write(f"   Evento: {existing_log.event_description}")
            self.stdout.write(f"   Timestamp: {existing_log.device_timestamp}")
            return
        
        # Criar log manualmente baseado nos dados informados
        self.stdout.write("📋 Criando log manualmente...")
        
        try:
            # Dados do log ID 10030 baseados na informação fornecida
            log_data = {
                'id': 10030,
                'user_id': 1,  # Diego Lucio
                'event': 7,    # Entrada
                'time': 1759954718,  # Timestamp aproximado para 09/10/2025 19:58:38
                'portal_id': 1,  # Portal de Entrada
            }
            
            # Obter nome do usuário
            employee = Employee.objects.filter(device_id=1).first()
            user_name = employee.name if employee else "Diego Lucio"
            
            # Mapear evento
            event_type = 1  # Entrada
            
            # Criar timestamp
            device_timestamp = datetime.fromtimestamp(1759954718, tz=timezone.utc)
            
            # Criar log no banco
            with transaction.atomic():
                access_log = AccessLog.objects.create(
                    device_log_id=10030,
                    user_id=1,
                    user_name=user_name,
                    event_type=event_type,
                    event_description="Entrada",
                    device_id=1,
                    device_name="Catraca Principal",
                    portal_id=1,
                    device_timestamp=device_timestamp,
                    raw_data=log_data,
                    processing_status='processed'
                )
                
                # Log do sistema
                SystemLog.log_info(
                    f"Log ID 10030 processado manualmente: {user_name} - Entrada",
                    category='device',
                    user_id=1,
                    user_name=user_name,
                    device_id=1,
                    details={'log_id': 10030, 'event': 'Entrada', 'manual_processed': True}
                )
            
            self.stdout.write("✅ Log ID 10030 criado com sucesso!")
            self.stdout.write(f"   Usuário: {user_name}")
            self.stdout.write(f"   Evento: Entrada")
            self.stdout.write(f"   Timestamp: {device_timestamp}")
            
            # Atualizar último ID processado
            from apps.logs.services import log_monitor_service
            log_monitor_service.last_processed_id = 10030
            self.stdout.write(f"✅ Último ID processado atualizado para: {log_monitor_service.last_processed_id}")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
