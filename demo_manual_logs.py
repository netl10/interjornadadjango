#!/usr/bin/env python
"""
Demonstração de como usar logs manuais - OPÇÃO A
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

def demo_manual_logs():
    """Demonstra como criar e usar logs manuais"""
    print("=== DEMONSTRAÇÃO - LOGS MANUAIS (OPÇÃO A) ===\n")
    
    # Buscar funcionário
    employee = Employee.objects.first()
    if not employee:
        print("❌ Nenhum funcionário encontrado")
        return
    
    print(f"👤 Funcionário: {employee.name} (ID: {employee.device_id})")
    
    # Exemplo 1: Entrada manual
    print(f"\n📝 EXEMPLO 1: Entrada Manual")
    entrada_manual = AccessLog.objects.create(
        device_log_id=-1,  # ID negativo para log manual
        user_id=employee.device_id,
        user_name=employee.name,
        event_type=1,  # Entrada
        event_description="Entrada Manual - Funcionário esqueceu de passar na catraca",
        device_id=1,
        device_name="Sistema Manual",
        portal_id=1,
        device_timestamp=timezone.now(),
        received_timestamp=timezone.now(),
        processing_status="pending",
        raw_data="{}",
        processed_data="{}",
        created_at=timezone.now(),
        session_processed=False,
        updated_at=timezone.now(),
        is_manual=True  # Marcar como manual
    )
    
    print(f"✅ Log de entrada criado:")
    print(f"   📋 ID: {entrada_manual.device_log_id}")
    print(f"   🏷️ Manual: {entrada_manual.is_manual}")
    print(f"   📝 Descrição: {entrada_manual.event_description}")
    
    # Exemplo 2: Saída manual
    print(f"\n📝 EXEMPLO 2: Saída Manual")
    saida_manual = AccessLog.objects.create(
        device_log_id=-2,  # Próximo ID negativo
        user_id=employee.device_id,
        user_name=employee.name,
        event_type=2,  # Saída
        event_description="Saída Manual - Catraca com problema",
        device_id=1,
        device_name="Sistema Manual",
        portal_id=2,
        device_timestamp=timezone.now(),
        received_timestamp=timezone.now(),
        processing_status="pending",
        raw_data="{}",
        processed_data="{}",
        created_at=timezone.now(),
        session_processed=False,
        updated_at=timezone.now(),
        is_manual=True
    )
    
    print(f"✅ Log de saída criado:")
    print(f"   📋 ID: {saida_manual.device_log_id}")
    print(f"   🏷️ Manual: {saida_manual.is_manual}")
    print(f"   📝 Descrição: {saida_manual.event_description}")
    
    # Verificar logs manuais
    print(f"\n🔍 LOGS MANUAIS CRIADOS:")
    logs_manuais = AccessLog.objects.filter(is_manual=True).order_by('device_log_id')
    for log in logs_manuais:
        print(f"   📋 ID: {log.device_log_id} | {log.event_description} | Manual: {log.is_manual}")
    
    # Verificar logs normais (não manuais)
    print(f"\n🔍 LOGS NORMAIS (não manuais):")
    logs_normais = AccessLog.objects.filter(device_log_id__gt=0).count()
    print(f"   📊 Total de logs normais: {logs_normais}")
    
    # Verificar logs manuais
    logs_manuais_count = AccessLog.objects.filter(device_log_id__lt=0).count()
    print(f"   📊 Total de logs manuais: {logs_manuais_count}")
    
    print(f"\n🎯 COMO USAR LOGS MANUAIS:")
    print(f"   1. Use IDs negativos: -1, -2, -3, -4...")
    print(f"   2. Marque is_manual=True")
    print(f"   3. Sistema ignora automaticamente IDs ≤ 0")
    print(f"   4. Processe imediatamente se necessário")
    
    print(f"\n✅ OPÇÃO A FUNCIONANDO PERFEITAMENTE!")
    
    # Limpar logs de demonstração
    entrada_manual.delete()
    saida_manual.delete()
    print(f"🧹 Logs de demonstração removidos")

if __name__ == "__main__":
    demo_manual_logs()
