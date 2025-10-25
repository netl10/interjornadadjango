#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo "🚀 INSTALADOR DO SISTEMA DE INTERJORNADA - LINUX/MAC"
echo "============================================================"

# Verificar se Python está instalado
echo ""
echo "🔍 VERIFICANDO PYTHON..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado!${NC}"
    echo "💡 Instale Python 3.8+ primeiro"
    exit 1
fi

python3 --version
echo -e "${GREEN}✅ Python encontrado${NC}"

# Verificar se pip está disponível
echo ""
echo "🔍 VERIFICANDO PIP..."
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}❌ pip não encontrado!${NC}"
    echo "💡 Instale pip primeiro"
    exit 1
fi

echo -e "${GREEN}✅ pip disponível${NC}"

# Criar ambiente virtual
echo ""
echo "🔧 CRIANDO AMBIENTE VIRTUAL..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Ambiente virtual já existe${NC}"
    read -p "🔄 Recriar? (s/N): " recreate
    if [[ $recreate == "s" || $recreate == "S" ]]; then
        rm -rf venv
    else
        echo -e "${GREEN}✅ Usando ambiente virtual existente${NC}"
        source venv/bin/activate
        goto_install_deps=true
    fi
fi

if [ "$goto_install_deps" != "true" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Erro ao criar ambiente virtual${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Ambiente virtual criado${NC}"
    
    # Ativar ambiente virtual
    source venv/bin/activate
fi

# Instalar dependências
echo ""
echo "📦 INSTALANDO DEPENDÊNCIAS..."

# Atualizar pip
echo "🔄 Atualizando pip..."
python -m pip install --upgrade pip

# Instalar dependências
echo "📦 Instalando dependências..."
python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro ao instalar dependências${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependências instaladas${NC}"

# Criar arquivo .env
echo ""
echo "🔧 CONFIGURANDO ARQUIVO .ENV..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📋 Copiando .env.example para .env..."
        cp .env.example .env
    else
        echo "📝 Criando arquivo .env básico..."
        cat > .env << 'EOF'
# Configurações do Sistema de Interjornada
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
EOF
    fi
    echo -e "${GREEN}✅ Arquivo .env criado${NC}"
else
    echo -e "${GREEN}✅ Arquivo .env já existe${NC}"
fi

# Executar migrações
echo ""
echo "🗄️  EXECUTANDO MIGRAÇÕES..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro ao executar migrações${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Migrações executadas${NC}"

# Criar superusuário
echo ""
echo "👤 VERIFICANDO SUPERUSUÁRIO..."
superuser_exists=$(python manage.py shell -c "from django.contrib.auth.models import User; print('True' if User.objects.filter(is_superuser=True).exists() else 'False')")

if [ "$superuser_exists" == "True" ]; then
    echo -e "${GREEN}✅ Superusuário já existe${NC}"
else
    echo "👤 Criando superusuário..."
    echo "📝 Use: admin / admin123"
    python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"
    echo -e "${GREEN}✅ Superusuário criado: admin / admin123${NC}"
fi

# Coletar arquivos estáticos
echo ""
echo "📁 COLETANDO ARQUIVOS ESTÁTICOS..."
python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Aviso ao coletar arquivos estáticos${NC}"
else
    echo -e "${GREEN}✅ Arquivos estáticos coletados${NC}"
fi

# Criar script de inicialização
echo ""
echo "🚀 CRIANDO SCRIPT DE INICIALIZAÇÃO..."
cat > start_server.sh << 'EOF'
#!/bin/bash
echo "🚀 Iniciando Sistema de Interjornada..."
source venv/bin/activate
python manage.py runserver 8000
EOF

chmod +x start_server.sh
echo -e "${GREEN}✅ Script de inicialização criado: start_server.sh${NC}"

# Mensagem de sucesso
echo ""
echo "============================================================"
echo -e "${GREEN}🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo "============================================================"
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Iniciar servidor:"
echo "   ./start_server.sh"
echo "2. Acessar sistema:"
echo "   http://localhost:8000/"
echo "3. Login:"
echo "   Usuário: admin"
echo "   Senha: admin123"
echo "============================================================"
