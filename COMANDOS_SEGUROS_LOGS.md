# 🛡️ COMANDOS SEGUROS PARA LOGS DA CATRACA

## ⚠️ IMPORTANTE: Proteção da Catraca IDFace

**NUNCA** busque todos os logs de uma vez! Isso pode sobrecarregar e derrubar a catraca IDFace.

## 🔒 Comandos Seguros Implementados

### 1. **Busca Segura de Logs**
```bash
# Buscar apenas logs muito recentes (máximo 20)
python manage.py safe_fetch_logs --recent-only --limit 10

# Buscar logs com limite seguro (máximo 1000)
python manage.py safe_fetch_logs --limit 50 --save

# Filtrar por usuário específico
python manage.py safe_fetch_logs --user-id 1 --limit 20

# Filtrar por evento
python manage.py safe_fetch_logs --event entry --limit 30
```

### 2. **Monitoramento Seguro**
```bash
# Monitoramento com intervalos seguros (mínimo 3s)
python manage.py safe_monitor_logs --interval 5 --limit 20

# Monitoramento mais conservador
python manage.py safe_monitor_logs --interval 10 --limit 10
```

## 📊 Limites de Segurança Implementados

### **DeviceClient**
- ✅ Máximo 1000 logs por requisição
- ✅ Padrão de 100 logs por requisição
- ✅ Validação automática de limites

### **Comandos de Busca**
- ✅ `safe_fetch_logs`: Máximo 1000 logs
- ✅ `--recent-only`: Máximo 20 logs
- ✅ Validação automática de limites

### **Comandos de Monitoramento**
- ✅ `safe_monitor_logs`: Máximo 100 logs por verificação
- ✅ Intervalo mínimo de 3 segundos
- ✅ Padrão de 5 segundos entre verificações

## 🚫 Comandos NÃO Seguros (Evitar)

```bash
# ❌ NÃO FAÇA ISSO - Pode derrubar a catraca
python manage.py fetch_logs --limit 50000
python manage.py monitor_logs --interval 1 --limit 1000

# ❌ NÃO FAÇA ISSO - Busca todos os logs
python manage.py fetch_logs --limit 999999
```

## ✅ Boas Práticas

1. **Sempre use os comandos `safe_*`**
2. **Limite máximo: 1000 logs por operação**
3. **Intervalo mínimo: 3 segundos entre verificações**
4. **Use `--recent-only` para logs muito recentes**
5. **Monitore a resposta da catraca**

## 📋 Exemplo de Uso Seguro

```bash
# 1. Verificar logs recentes
python manage.py safe_fetch_logs --recent-only --limit 10

# 2. Buscar logs de um usuário específico
python manage.py safe_fetch_logs --user-id 1 --limit 20 --save

# 3. Monitorar em tempo real (seguro)
python manage.py safe_monitor_logs --interval 5 --limit 20

# 4. Parar monitoramento: Ctrl+C
```

## 🔧 Configurações de Segurança

- **Limite máximo por requisição**: 1000 logs
- **Intervalo mínimo entre verificações**: 3 segundos
- **Modo recent-only**: Máximo 20 logs
- **Monitoramento padrão**: 20 logs a cada 5 segundos

## 📊 Resultados dos Testes

✅ **Testado com sucesso:**
- Busca de 10 logs recentes
- Identificação de usuários reais
- Salvamento no banco de dados
- Monitoramento seguro

**O sistema está protegido contra sobrecarga da catraca!** 🛡️
