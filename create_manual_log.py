#!/usr/bin/env python
"""
Script para criar logs manuais usando IDs negativos
"""
import os
import sys
import django
from django.utils import timezone

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.logs.models import AccessLog
from apps.employees.models import Employee
from apps.logs.services import LogMonitorService

def create_manual_log():
    """Cria um log manual para teste"""
    print("=== CRIANDO LOG MANUAL - OPÇÃO A ===\n")
    
    # Buscar um funcionário para teste
    try:
        employee = Employee.objects.first()
        if not employee:
            print("❌ Nenhum funcionário encontrado no sistema")
            return
        
        print(f"👤 Funcionário selecionado: {employee.name} (ID: {employee.device_id})")
        
        # Criar log manual com ID negativo
        manual_log = AccessLog.objects.create(
            device_log_id=-1,  # ID negativo para log manual
            user_id=employee.device_id,
            user_name=employee.name,
            event_type=1,  # Entrada
            event_description="Entrada Manual",
            device_id=1,
            device_name="Sistema Manual",
            portal_id=1,
            device_timestamp=timezone.now(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
            is_manual=True  # Marcar como manual
        )
        
        print(f"✅ Log manual criado com sucesso!")
        print(f"   📋 ID: {manual_log.device_log_id}")
        print(f"   👤 Usuário: {manual_log.user_name}")
        print(f"   📅 Timestamp: {manual_log.device_timestamp}")
        print(f"   🏷️ Manual: {manual_log.is_manual}")
        
        # Processar o log manual imediatamente
        print(f"\n🔄 Processando log manual...")
        log_monitor = LogMonitorService()
        result = log_monitor.process_access_log(manual_log)
        
        if result:
            print(f"✅ Log manual processado com sucesso!")
            print(f"   📊 Resultado: {result}")
        else:
            print(f"❌ Falha ao processar log manual")
        
        # Verificar se foi processado
        manual_log.refresh_from_db()
        print(f"\n📋 Status do log após processamento:")
        print(f"   🔄 Processado: {manual_log.session_processed}")
        print(f"   ⏰ Processado em: {manual_log.session_processed_at}")
        print(f"   ❌ Erro: {manual_log.session_processing_error}")
        
    except Exception as e:
        print(f"❌ Erro ao criar log manual: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_manual_log()
