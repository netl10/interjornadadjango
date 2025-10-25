@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo 🚀 INSTALADOR DO SISTEMA DE INTERJORNADA - WINDOWS
echo ============================================================

:: Verificar se Python está instalado
echo.
echo 🔍 VERIFICANDO PYTHON...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado!
    echo 💡 Instale Python 3.8+ primeiro: https://python.org
    pause
    exit /b 1
)

python --version
echo ✅ Python encontrado

:: Verificar se pip está disponível
echo.
echo 🔍 VERIFICANDO PIP...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip não encontrado!
    echo 💡 Instale pip primeiro
    pause
    exit /b 1
)

echo ✅ pip disponível

:: Criar ambiente virtual
echo.
echo 🔧 CRIANDO AMBIENTE VIRTUAL...
if exist venv (
    echo ⚠️  Ambiente virtual já existe
    set /p recreate="🔄 Recriar? (s/N): "
    if /i "!recreate!"=="s" (
        rmdir /s /q venv
    ) else (
        echo ✅ Usando ambiente virtual existente
        goto :install_deps
    )
)

python -m venv venv
if errorlevel 1 (
    echo ❌ Erro ao criar ambiente virtual
    pause
    exit /b 1
)

echo ✅ Ambiente virtual criado

:install_deps
:: Ativar ambiente virtual e instalar dependências
echo.
echo 📦 INSTALANDO DEPENDÊNCIAS...
call venv\Scripts\activate.bat

:: Atualizar pip
echo 🔄 Atualizando pip...
python -m pip install --upgrade pip

:: Instalar dependências
echo 📦 Instalando dependências...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erro ao instalar dependências
    pause
    exit /b 1
)

echo ✅ Dependências instaladas

:: Criar arquivo .env
echo.
echo 🔧 CONFIGURANDO ARQUIVO .ENV...
if not exist .env (
    if exist .env.example (
        echo 📋 Copiando .env.example para .env...
        copy .env.example .env
    ) else (
        echo 📝 Criando arquivo .env básico...
        (
            echo # Configurações do Sistema de Interjornada
            echo DEBUG=True
            echo SECRET_KEY=django-insecure-change-me-in-production
            echo ALLOWED_HOSTS=localhost,127.0.0.1,testserver,0.0.0.0
            echo.
            echo # Database
            echo DATABASE_URL=sqlite:///db.sqlite3
            echo.
            echo # Redis
            echo REDIS_URL=redis://localhost:6379/0
            echo.
            echo # Email
            echo EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
            echo.
            echo # Logging
            echo LOG_LEVEL=INFO
        ) > .env
    )
    echo ✅ Arquivo .env criado
) else (
    echo ✅ Arquivo .env já existe
)

:: Executar migrações
echo.
echo 🗄️  EXECUTANDO MIGRAÇÕES...
python manage.py migrate
if errorlevel 1 (
    echo ❌ Erro ao executar migrações
    pause
    exit /b 1
)

echo ✅ Migrações executadas

:: Criar superusuário
echo.
echo 👤 VERIFICANDO SUPERUSUÁRIO...
python manage.py shell -c "from django.contrib.auth.models import User; print('True' if User.objects.filter(is_superuser=True).exists() else 'False')" > temp_check.txt
set /p superuser_exists=<temp_check.txt
del temp_check.txt

if "!superuser_exists!"=="True" (
    echo ✅ Superusuário já existe
) else (
    echo 👤 Criando superusuário...
    echo 📝 Use: admin / admin123
    python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"
    echo ✅ Superusuário criado: admin / admin123
)

:: Coletar arquivos estáticos
echo.
echo 📁 COLETANDO ARQUIVOS ESTÁTICOS...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo ⚠️  Aviso ao coletar arquivos estáticos
) else (
    echo ✅ Arquivos estáticos coletados
)

:: Criar script de inicialização
echo.
echo 🚀 CRIANDO SCRIPT DE INICIALIZAÇÃO...
(
    echo @echo off
    echo echo 🚀 Iniciando Sistema de Interjornada...
    echo call venv\Scripts\activate.bat
    echo python manage.py runserver 8000
    echo pause
) > start_server.bat

echo ✅ Script de inicialização criado: start_server.bat

:: Mensagem de sucesso
echo.
echo ============================================================
echo 🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!
echo ============================================================
echo 📋 PRÓXIMOS PASSOS:
echo 1. Iniciar servidor:
echo    start_server.bat
echo 2. Acessar sistema:
echo    http://localhost:8000/
echo 3. Login:
echo    Usuário: admin
echo    Senha: admin123
echo ============================================================

pause
