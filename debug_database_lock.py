#!/usr/bin/env python
"""
Script para debugar problemas de database lock.
"""
import os
import django

# Configurar Django PRIMEIRO
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

# Importar DEPOIS da configuração
from apps.employee_sessions.models import EmployeeSession
from apps.employees.models import Employee
from apps.logs.models import AccessLog, SystemLog
from django.utils import timezone
from django.db import connection, transaction
import time

def debug_database_lock():
    """Debuga problemas de database lock."""
    print("🔍 DEBUGANDO PROBLEMAS DE DATABASE LOCK")
    print("=" * 60)
    
    # 1. Verificar conexões ativas
    print("📋 1. VERIFICANDO CONEXÕES ATIVAS:")
    print("-" * 40)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"   ✅ Conexão com banco funcionando - {len(tables)} tabelas encontradas")
    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
        return
    
    # 2. Verificar sessões ativas
    print(f"\n📋 2. VERIFICANDO SESSÕES ATIVAS:")
    print("-" * 40)
    
    try:
        sessions = EmployeeSession.objects.filter(
            state__in=['active', 'pending_rest', 'blocked']
        ).select_related('employee')
        
        print(f"   Total de sessões ativas: {sessions.count()}")
        
        for session in sessions:
            print(f"   - {session.employee.name} (ID: {session.employee.device_id})")
            print(f"     Estado: {session.state}")
            print(f"     Primeiro acesso: {session.first_access}")
            print(f"     Grupo atual: {session.employee.group.name if session.employee.group else 'N/A'}")
            print()
    except Exception as e:
        print(f"   ❌ Erro ao verificar sessões: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Verificar logs recentes
    print(f"\n📋 3. VERIFICANDO LOGS RECENTES:")
    print("-" * 40)
    
    try:
        recent_logs = AccessLog.objects.filter(
            device_timestamp__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).order_by('-device_timestamp')[:5]
        
        print(f"   Logs recentes (últimos 10 min): {recent_logs.count()}")
        
        for log in recent_logs:
            print(f"   - ID: {log.id}")
            print(f"     Usuário: {log.user_name} (ID: {log.user_id})")
            print(f"     Evento: {log.event_type} - {log.event_description}")
            print(f"     Portal: {log.portal_id}")
            print(f"     Timestamp: {log.device_timestamp}")
            print(f"     Processado: {log.session_processed}")
            print()
    except Exception as e:
        print(f"   ❌ Erro ao verificar logs: {e}")
    
    # 4. Testar transação
    print(f"\n📋 4. TESTANDO TRANSAÇÃO:")
    print("-" * 40)
    
    try:
        with transaction.atomic():
            # Testar operação simples
            test_count = EmployeeSession.objects.count()
            print(f"   ✅ Transação funcionando - {test_count} sessões no banco")
    except Exception as e:
        print(f"   ❌ Erro na transação: {e}")
    
    # 5. Verificar se há locks
    print(f"\n📋 5. VERIFICANDO LOCKS:")
    print("-" * 40)
    
    try:
        with connection.cursor() as cursor:
            # Verificar se há locks no SQLite
            cursor.execute("PRAGMA database_list")
            databases = cursor.fetchall()
            print(f"   Bancos conectados: {len(databases)}")
            
            # Verificar configurações do SQLite
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()
            print(f"   Modo de journal: {journal_mode[0] if journal_mode else 'N/A'}")
            
            cursor.execute("PRAGMA synchronous")
            synchronous = cursor.fetchone()
            print(f"   Modo síncrono: {synchronous[0] if synchronous else 'N/A'}")
            
            cursor.execute("PRAGMA busy_timeout")
            busy_timeout = cursor.fetchone()
            print(f"   Timeout de busy: {busy_timeout[0] if busy_timeout else 'N/A'}")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar locks: {e}")
    
    # 6. Verificar logs do sistema
    print(f"\n📋 6. VERIFICANDO LOGS DO SISTEMA:")
    print("-" * 40)
    
    try:
        system_logs = SystemLog.objects.order_by('-timestamp')[:5]
        
        for log in system_logs:
            print(f"   [{log.level}] {log.timestamp.strftime('%H:%M:%S')} - {log.message}")
            if log.user_name:
                print(f"      Usuário: {log.user_name}")
            print()
    except Exception as e:
        print(f"   ❌ Erro ao verificar logs do sistema: {e}")

if __name__ == "__main__":
    debug_database_lock()
