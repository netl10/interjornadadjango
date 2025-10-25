#!/usr/bin/env python3
"""
Instalador automático para o Sistema de Interjornada Django.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class DjangoInstaller:
    """Instalador automático para o projeto Django."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.python_executable = sys.executable
        self.system = platform.system().lower()
        self.is_windows = self.system == 'windows'
        
    def print_header(self):
        """Imprime o cabeçalho do instalador."""
        print("=" * 60)
        print("🚀 INSTALADOR DO SISTEMA DE INTERJORNADA")
        print("=" * 60)
        print(f"📁 Diretório do projeto: {self.project_root}")
        print(f"🐍 Python: {self.python_executable}")
        print(f"💻 Sistema: {platform.system()} {platform.release()}")
        print("=" * 60)
        
    def check_python_version(self):
        """Verifica a versão do Python."""
        print("\n🔍 VERIFICANDO VERSÃO DO PYTHON...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Python {version.major}.{version.minor} não é suportado!")
            print("💡 Requer Python 3.8 ou superior")
            return False
            
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
        
    def check_pip(self):
        """Verifica se o pip está disponível."""
        print("\n🔍 VERIFICANDO PIP...")
        
        try:
            result = subprocess.run([self.python_executable, '-m', 'pip', '--version'], 
                                 capture_output=True, text=True, check=True)
            print(f"✅ pip disponível: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError:
            print("❌ pip não encontrado!")
            print("💡 Instale o pip primeiro")
            return False
            
    def create_virtual_environment(self):
        """Cria ambiente virtual."""
        print("\n🔧 CRIANDO AMBIENTE VIRTUAL...")
        
        venv_path = self.project_root / 'venv'
        
        if venv_path.exists():
            print("⚠️  Ambiente virtual já existe")
            response = input("🔄 Recriar? (s/N): ").lower()
            if response == 's':
                shutil.rmtree(venv_path)
            else:
                print("✅ Usando ambiente virtual existente")
                return str(venv_path)
        
        try:
            subprocess.run([self.python_executable, '-m', 'venv', str(venv_path)], 
                         check=True)
            print("✅ Ambiente virtual criado")
            return str(venv_path)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao criar ambiente virtual: {e}")
            return None
            
    def get_venv_python(self, venv_path):
        """Retorna o caminho do Python no ambiente virtual."""
        if self.is_windows:
            return venv_path / 'Scripts' / 'python.exe'
        else:
            return venv_path / 'bin' / 'python'
            
    def get_venv_pip(self, venv_path):
        """Retorna o caminho do pip no ambiente virtual."""
        if self.is_windows:
            return venv_path / 'Scripts' / 'pip.exe'
        else:
            return venv_path / 'bin' / 'pip'
            
    def install_dependencies(self, venv_path):
        """Instala as dependências."""
        print("\n📦 INSTALANDO DEPENDÊNCIAS...")
        
        pip_path = self.get_venv_pip(venv_path)
        requirements_file = self.project_root / 'requirements.txt'
        
        if not requirements_file.exists():
            print("❌ Arquivo requirements.txt não encontrado!")
            return False
            
        try:
            # Atualizar pip primeiro
            print("🔄 Atualizando pip...")
            subprocess.run([str(pip_path), 'install', '--upgrade', 'pip'], 
                         check=True)
            
            # Instalar dependências
            print("📦 Instalando dependências do requirements.txt...")
            subprocess.run([str(pip_path), 'install', '-r', str(requirements_file)], 
                         check=True)
            
            print("✅ Dependências instaladas com sucesso!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar dependências: {e}")
            return False
            
    def create_env_file(self):
        """Cria arquivo .env se não existir."""
        print("\n🔧 CONFIGURANDO ARQUIVO .ENV...")
        
        env_file = self.project_root / '.env'
        env_example = self.project_root / '.env.example'
        
        if env_file.exists():
            print("✅ Arquivo .env já existe")
            return True
            
        if env_example.exists():
            print("📋 Copiando .env.example para .env...")
            shutil.copy2(env_example, env_file)
            print("✅ Arquivo .env criado")
        else:
            print("📝 Criando arquivo .env básico...")
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("""# Configurações do Sistema de Interjornada
DEBUG=True
SECRET_KEY=django-insecure-change-me-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,testserver,0.0.0.0

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Logging
LOG_LEVEL=INFO
""")
            print("✅ Arquivo .env criado com configurações básicas")
            
        return True
        
    def run_migrations(self, venv_path):
        """Executa as migrações do Django."""
        print("\n🗄️  EXECUTANDO MIGRAÇÕES...")
        
        python_path = self.get_venv_python(venv_path)
        manage_py = self.project_root / 'manage.py'
        
        if not manage_py.exists():
            print("❌ Arquivo manage.py não encontrado!")
            return False
            
        try:
            # Executar migrações
            subprocess.run([str(python_path), str(manage_py), 'migrate'], 
                         check=True, cwd=str(self.project_root))
            
            print("✅ Migrações executadas com sucesso!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao executar migrações: {e}")
            return False
            
    def create_superuser(self, venv_path):
        """Cria superusuário se não existir."""
        print("\n👤 VERIFICANDO SUPERUSUÁRIO...")
        
        python_path = self.get_venv_python(venv_path)
        manage_py = self.project_root / 'manage.py'
        
        try:
            # Verificar se já existe superusuário
            result = subprocess.run([str(python_path), str(manage_py), 'shell', '-c', 
                                   'from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())'], 
                                  capture_output=True, text=True, check=True, cwd=str(self.project_root))
            
            if 'True' in result.stdout:
                print("✅ Superusuário já existe")
                return True
                
            print("👤 Criando superusuário...")
            print("📝 Use: admin / admin123")
            
            # Criar superusuário
            subprocess.run([str(python_path), str(manage_py), 'createsuperuser', 
                          '--username', 'admin', '--email', 'admin@example.com', '--noinput'], 
                         check=True, cwd=str(self.project_root))
            
            # Definir senha
            subprocess.run([str(python_path), str(manage_py), 'shell', '-c', 
                           'from django.contrib.auth.models import User; u = User.objects.get(username="admin"); u.set_password("admin123"); u.save()'], 
                         check=True, cwd=str(self.project_root))
            
            print("✅ Superusuário criado: admin / admin123")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao criar superusuário: {e}")
            return False
            
    def collect_static(self, venv_path):
        """Coleta arquivos estáticos."""
        print("\n📁 COLETANDO ARQUIVOS ESTÁTICOS...")
        
        python_path = self.get_venv_python(venv_path)
        manage_py = self.project_root / 'manage.py'
        
        try:
            subprocess.run([str(python_path), str(manage_py), 'collectstatic', '--noinput'], 
                         check=True, cwd=str(self.project_root))
            
            print("✅ Arquivos estáticos coletados!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Aviso ao coletar arquivos estáticos: {e}")
            return True  # Não é crítico
            
    def create_startup_scripts(self, venv_path):
        """Cria scripts de inicialização."""
        print("\n🚀 CRIANDO SCRIPTS DE INICIALIZAÇÃO...")
        
        python_path = self.get_venv_python(venv_path)
        
        # Script para Windows
        if self.is_windows:
            start_script = self.project_root / 'start_server.bat'
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write(f"""@echo off
echo 🚀 Iniciando Sistema de Interjornada...
cd /d "{self.project_root}"
"{python_path}" manage.py runserver 8000
pause
""")
            print(f"✅ Script Windows criado: {start_script}")
            
        # Script para Linux/Mac
        else:
            start_script = self.project_root / 'start_server.sh'
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write(f"""#!/bin/bash
echo "🚀 Iniciando Sistema de Interjornada..."
cd "{self.project_root}"
"{python_path}" manage.py runserver 8000
""")
            os.chmod(start_script, 0o755)
            print(f"✅ Script Unix criado: {start_script}")
            
    def print_success_message(self):
        """Imprime mensagem de sucesso."""
        print("\n" + "=" * 60)
        print("🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print("📋 PRÓXIMOS PASSOS:")
        print("1. Ativar ambiente virtual:")
        if self.is_windows:
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        print("2. Iniciar servidor:")
        if self.is_windows:
            print("   start_server.bat")
        else:
            print("   ./start_server.sh")
        print("3. Acessar sistema:")
        print("   http://localhost:8000/")
        print("4. Login:")
        print("   Usuário: admin")
        print("   Senha: admin123")
        print("=" * 60)
        
    def run(self):
        """Executa o instalador completo."""
        self.print_header()
        
        # Verificações iniciais
        if not self.check_python_version():
            return False
            
        if not self.check_pip():
            return False
            
        # Criar ambiente virtual
        venv_path = self.create_virtual_environment()
        if not venv_path:
            return False
            
        # Instalar dependências
        if not self.install_dependencies(venv_path):
            return False
            
        # Configurar arquivo .env
        if not self.create_env_file():
            return False
            
        # Executar migrações
        if not self.run_migrations(venv_path):
            return False
            
        # Criar superusuário
        if not self.create_superuser(venv_path):
            return False
            
        # Coletar arquivos estáticos
        self.collect_static(venv_path)
        
        # Criar scripts de inicialização
        self.create_startup_scripts(venv_path)
        
        # Mensagem de sucesso
        self.print_success_message()
        
        return True

def main():
    """Função principal."""
    installer = DjangoInstaller()
    success = installer.run()
    
    if success:
        print("\n✅ Instalação concluída com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Instalação falhou!")
        sys.exit(1)

if __name__ == "__main__":
    main()
