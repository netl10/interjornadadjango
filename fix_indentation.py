#!/usr/bin/env python
"""
Script para corrigir indentação do arquivo interjornada/services.py
"""
import os

def fix_indentation():
    """Corrige a indentação do arquivo"""
    file_path = "apps/interjornada/services.py"
    
    # Ler o arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Corrigir linhas problemáticas específicas
    fixed_lines = []
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Corrigir indentação específica
        if line_num == 268:
            # Linha 268: comentário deve ter indentação correta
            fixed_lines.append("                    # Liberar da interjornada usando o session_service que tem a implementação correta\n")
        elif line_num == 269:
            # Linha 269: chamada de função deve ter indentação correta
            fixed_lines.append("                    session_service.unblock_user_from_interjornada(employee)\n")
        elif line_num == 270:
            # Linha 270: logger deve ter indentação correta
            fixed_lines.append("                    logger.info(f\"Usuário {employee.name} liberado da interjornada - Acesso permitido\")\n")
        elif line_num == 271:
            # Linha 271: return deve ter indentação correta
            fixed_lines.append("                    return {\n")
        elif line_num == 272:
            # Linha 272: 'success' deve ter indentação correta
            fixed_lines.append("                        'success': True,\n")
        elif line_num == 273:
            # Linha 273: 'message' deve ter indentação correta
            fixed_lines.append("                        'message': 'Funcionário liberado da interjornada',\n")
        elif line_num == 274:
            # Linha 274: 'action' deve ter indentação correta
            fixed_lines.append("                        'action': 'allow'\n")
        elif line_num == 275:
            # Linha 275: } deve ter indentação correta
            fixed_lines.append("                    }\n")
        elif line_num == 276:
            # Linha 276: else deve ter indentação correta
            fixed_lines.append("                else:\n")
        else:
            # Manter linha original
            fixed_lines.append(line)
    
    # Escrever arquivo corrigido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ Indentação corrigida!")

if __name__ == "__main__":
    fix_indentation()
