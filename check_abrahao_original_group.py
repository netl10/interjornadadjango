#!/usr/bin/env python
"""
Script para verificar e corrigir o grupo original do ABRAHAO
"""
import os
import sys
import django
from django.utils import timezone

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interjornada_system.settings')
django.setup()

from apps.employees.models import Employee, EmployeeGroup
from apps.employee_sessions.models import EmployeeSession

def check_abrahao_original_group():
    """Verifica e corrige o grupo original do ABRAHAO"""
    print("=== VERIFICAÇÃO DO GRUPO ORIGINAL DO ABRAHAO ===\n")
    
    # Buscar ABRAHAO
    try:
        abrahao = Employee.objects.get(device_id=1000426)
        print(f"👤 Funcionário encontrado: {abrahao.name} (ID: {abrahao.device_id})")
        print(f"   - Grupo atual: {abrahao.group}")
        print(f"   - Grupo original: {abrahao.original_group}")
        print(f"   - Ativo: {abrahao.is_active}")
        
        # Verificar sessão
        session = EmployeeSession.objects.filter(employee=abrahao).first()
        if session:
            print(f"   - Sessão: {session.state}")
            print(f"   - Primeiro acesso: {session.first_access}")
            print(f"   - Último acesso: {session.last_access}")
            if session.return_time:
                print(f"   - Retorna em: {session.return_time}")
        else:
            print(f"   - Sem sessão ativa")
        
        # Verificar se está na blacklist
        blacklist_group = EmployeeGroup.objects.filter(is_blacklist=True).first()
        if blacklist_group and abrahao.group == blacklist_group:
            print(f"   🚫 ESTÁ NA BLACKLIST")
            
            # O problema: não tem grupo original
            if not abrahao.original_group:
                print(f"   ❌ PROBLEMA: Não tem grupo original salvo")
                
                # Buscar grupo padrão
                default_group = EmployeeGroup.objects.filter(name='GRUPO_PADRAO').first()
                if default_group:
                    print(f"   🔧 CORREÇÃO: Definindo grupo padrão como original")
                    abrahao.original_group = default_group
                    abrahao.save(update_fields=['original_group'])
                    print(f"   ✅ Grupo original definido: {default_group.name}")
                    
                    # Testar restauração
                    print(f"\n🔧 Testando restauração da blacklist...")
                    from apps.employees.group_service import group_service
                    restore_success = group_service.restore_from_blacklist(abrahao)
                    
                    if restore_success:
                        print(f"   ✅ ABRAHAO restaurado da blacklist com sucesso!")
                        
                        # Verificar status final
                        abrahao.refresh_from_db()
                        print(f"   - Grupo atual após restauração: {abrahao.group}")
                        print(f"   - Grupo original após restauração: {abrahao.original_group}")
                        
                        # Verificar sessão
                        session = EmployeeSession.objects.filter(employee=abrahao).first()
                        if session:
                            print(f"   - Sessão após restauração: {session.state}")
                        else:
                            print(f"   - Sessão removida após restauração")
                    else:
                        print(f"   ❌ Falha ao restaurar ABRAHAO da blacklist")
                else:
                    print(f"   ❌ Grupo padrão não encontrado")
            else:
                print(f"   ✅ Tem grupo original: {abrahao.original_group}")
        else:
            print(f"   ✅ NÃO está na blacklist")
            
    except Employee.DoesNotExist:
        print("❌ ABRAHAO não encontrado no sistema")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print(f"\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_abrahao_original_group()
