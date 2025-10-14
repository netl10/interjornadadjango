# Sistema de Controle de Interjornada - Django

Sistema robusto para controle de jornadas de trabalho e interjornadas desenvolvido em Django com arquitetura modular e bem separada.

## 🏗️ Arquitetura

O sistema foi desenvolvido com separação clara de responsabilidades:

### 📁 Estrutura de Apps

```
@Django/
├── interjornada_system/          # Configurações principais
│   ├── settings.py              # Todas as configurações centralizadas
│   ├── urls.py                  # URLs principais
│   └── asgi.py                  # Configuração WebSocket
├── apps/
│   ├── core/                    # Utilitários e configurações
│   │   ├── utils.py             # Utilitários de timezone e validação
│   │   └── views.py             # Views de sistema
│   ├── devices/                 # Comunicação com dispositivos
│   │   ├── models.py            # Modelos de dispositivos
│   │   ├── services.py          # Serviços de comunicação
│   │   └── views.py             # Views de dispositivos
│   ├── employees/               # Gerenciamento de funcionários
│   │   ├── models.py            # Modelos de funcionários
│   │   └── views.py             # Views de funcionários
│   ├── logs/                    # Processamento de logs
│   │   ├── models.py            # Modelos de logs
│   │   └── services.py          # Serviços de processamento
│   ├── interjornada/            # Lógica de interjornada
│   └── dashboard/               # Interface web
└── requirements.txt             # Dependências
```

## 🚀 Instalação

### 1. Pré-requisitos

- Python 3.8+
- PostgreSQL
- Redis
- Virtual Environment (recomendado)

### 2. Configuração do Ambiente

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configuração do Banco de Dados

```bash
# Criar banco PostgreSQL
createdb interjornada_db

# Executar migrações
python manage.py makemigrations
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser
```

### 4. Configuração do Redis

```bash
# Instalar Redis (Ubuntu/Debian)
sudo apt install redis-server

# Iniciar Redis
sudo systemctl start redis-server
```

### 5. Configuração do Ambiente

```bash
# Copiar arquivo de exemplo
cp env_example.txt .env

# Editar configurações
nano .env
```

## ⚙️ Configurações

Todas as configurações estão centralizadas no arquivo `settings.py` e podem ser sobrescritas via variáveis de ambiente:

### Configurações Principais

```python
# Dispositivo Principal
PRIMARY_DEVICE_IP = '192.168.1.251'
PRIMARY_DEVICE_PORT = 443
PRIMARY_DEVICE_USERNAME = 'admin'
PRIMARY_DEVICE_PASSWORD = 'admin'

# Tempos de Trabalho e Interjornada
WORK_DURATION_MINUTES = 480    # 8 horas
REST_DURATION_MINUTES = 672    # 11.2 horas

# Monitoramento
MONITOR_INTERVAL_SECONDS = 3
GIRO_VALIDATION_TIMEOUT_SECONDS = 3

# Timezone
TIMEZONE_OFFSET = -3
DISPLAY_TIMEZONE = 'America/Sao_Paulo'
```

## 🔄 Fluxo do Sistema

### 1. Comunicação com Dispositivos
- **App**: `devices`
- **Responsabilidade**: Conectar e comunicar com dispositivos IDFace
- **Serviços**: `DeviceConnectionService`, `DeviceDataService`

### 2. Recebimento de Logs
- **App**: `logs`
- **Responsabilidade**: Receber e processar logs de acesso
- **Serviços**: `LogProcessingService`, `LogQueueService`

### 3. Gerenciamento de Funcionários
- **App**: `employees`
- **Responsabilidade**: Gerenciar funcionários e suas sessões
- **Modelos**: `Employee`, `EmployeeSession`, `EmployeeGroup`

### 4. Tratamento de UTC
- **App**: `core`
- **Responsabilidade**: Conversões de timezone
- **Utilitários**: `TimezoneUtils`

## 🗄️ Modelos de Dados

### Employee (Funcionário)
```python
class Employee(models.Model):
    device_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_exempt = models.BooleanField(default=False)
    groups = models.JSONField(default=list)
    work_duration_minutes = models.IntegerField(null=True)
    rest_duration_minutes = models.IntegerField(null=True)
```

### EmployeeSession (Sessão)
```python
class EmployeeSession(models.Model):
    employee = models.ForeignKey(Employee)
    state = models.CharField(choices=STATE_CHOICES)
    first_access = models.DateTimeField()
    block_start = models.DateTimeField(null=True)
    return_time = models.DateTimeField(null=True)
```

### AccessLog (Log de Acesso)
```python
class AccessLog(models.Model):
    device_log_id = models.BigIntegerField(unique=True)
    user_id = models.IntegerField()
    user_name = models.CharField(max_length=255)
    event_type = models.IntegerField(choices=EVENT_TYPES)
    device_timestamp = models.DateTimeField()
    processing_status = models.CharField(choices=PROCESSING_STATUS)
```

## 🔧 Serviços

### DeviceConnectionService
- Gerencia conexões com dispositivos
- Autenticação e manutenção de sessões
- Reconexão automática

### LogProcessingService
- Processa logs recebidos dos dispositivos
- Valida e armazena logs
- Adiciona à fila de processamento

### LogQueueService
- Processa fila de logs
- Aplica regras de interjornada
- Atualiza sessões de funcionários

## 🌐 API Endpoints

### Dispositivos
- `GET /api/v1/devices/` - Listar dispositivos
- `POST /api/v1/devices/<id>/connect/` - Conectar dispositivo
- `GET /api/v1/devices/<id>/logs/` - Buscar logs do dispositivo

### Funcionários
- `GET /api/v1/employees/` - Listar funcionários
- `POST /api/v1/employees/check-access/` - Verificar acesso
- `GET /api/v1/employees/active-sessions/` - Sessões ativas

### Logs
- `GET /api/v1/logs/` - Listar logs
- `GET /api/v1/logs/queue/` - Status da fila

### Sistema
- `GET /api/v1/core/config/` - Configurações do sistema
- `GET /api/v1/core/health/` - Status de saúde

## 🚀 Execução

### Desenvolvimento
```bash
# Executar servidor de desenvolvimento
python manage.py runserver

# Executar com WebSocket
python manage.py runserver 0.0.0.0:8000
```

### Produção
```bash
# Usar Gunicorn
gunicorn interjornada_system.wsgi:application

# Usar Daphne para WebSocket
daphne interjornada_system.asgi:application
```

## 📊 Monitoramento

### Logs do Sistema
- Logs estruturados em arquivos separados
- Níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Categorias: system, device, employee, interjornada

### Health Check
- `GET /api/v1/core/health/` - Status de saúde
- Verifica banco de dados, Redis, timezone

### Métricas
- Taxa de sucesso de conexão
- Número de logs processados
- Sessões ativas/bloqueadas

## 🔒 Segurança

### Autenticação
- Token Authentication
- Session Authentication
- Permissões por endpoint

### Validação
- Validação de IPs e portas
- Sanitização de strings
- Validação de IDs de usuário

### Rate Limiting
- Limite de requisições por minuto
- Configurável por endpoint

## 🛠️ Manutenção

### Limpeza de Logs
```bash
# Limpar logs antigos
python manage.py shell
>>> from apps.logs.models import AccessLog
>>> AccessLog.objects.filter(created_at__lt=timezone.now() - timedelta(days=30)).delete()
```

### Backup
```bash
# Backup do banco
pg_dump interjornada_db > backup.sql

# Restore
psql interjornada_db < backup.sql
```

### Monitoramento
```bash
# Verificar status
curl http://localhost:8000/api/v1/core/health/

# Verificar dispositivos
curl http://localhost:8000/api/v1/devices/status/all/
```

## 🔄 Migração do Sistema Anterior

### Diferenças Principais

1. **Arquitetura**: Django com apps separados vs FastAPI monolítico
2. **Banco**: PostgreSQL vs SQLite
3. **Configuração**: settings.py vs config.txt
4. **Timezone**: UTC interno com conversão vs timezone local
5. **Separação**: Cada funcionalidade em app separado

### Vantagens da Nova Arquitetura

- **Manutenibilidade**: Código separado por responsabilidade
- **Escalabilidade**: Apps independentes
- **Flexibilidade**: Configurações via ambiente
- **Robustez**: PostgreSQL + Redis
- **Padrões**: Seguindo convenções Django

## 📝 Logs e Debugging

### Logs Estruturados
```python
# Exemplo de log
SystemLog.log_info(
    message="Funcionário acessou sistema",
    category='employee',
    user_id=123,
    user_name="João Silva",
    details={'device_id': 1, 'portal': 'entrada'}
)
```

### Debug
```python
# Habilitar debug de dispositivos
DEVICE_DEBUG = True

# Nível de log
LOG_LEVEL = 'DEBUG'
```

## 🎯 Próximos Passos

1. **Implementar app interjornada** - Lógica de negócio
2. **Implementar app dashboard** - Interface web
3. **Configurar Celery** - Processamento assíncrono
4. **Implementar WebSocket** - Atualizações em tempo real
5. **Testes automatizados** - Cobertura de código
6. **Documentação API** - Swagger/OpenAPI

## 📞 Suporte

Para dúvidas ou problemas:

1. Verificar logs em `logs/`
2. Consultar health check
3. Verificar configurações
4. Consultar documentação da API

---

**Sistema de Controle de Interjornada Django** - Versão 2.0.0
*Desenvolvido com Django, PostgreSQL e Redis*
*Arquitetura modular e bem separada*
