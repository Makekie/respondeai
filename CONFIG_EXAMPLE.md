# Exemplo de uso das configurações

## Arquivo .env
Edite o arquivo `.env` na raiz do projeto para alterar as configurações:

```env
# App Configuration
APP_NAME=Meu Gerador de Questões
APP_VERSION=2.0.0
DEBUG=false
PORT=8080

# Ollama Configuration  
OLLAMA_BASE_URL=http://meu-ollama:11434
OLLAMA_MODEL=llama3.2:7b
```

## Arquivo config.yaml
Alternativamente, edite o arquivo `config.yaml`:

```yaml
app:
  name: "Meu Gerador de Questões"
  version: "2.0.0"
  debug: false
  port: 8080

ollama:
  base_url: "http://meu-ollama:11434"
  model: "llama3.2:7b"
```

## Prioridade
1. Variáveis de ambiente (.env)
2. Configurações YAML (config.yaml)
3. Valores padrão no código

As configurações do .env têm prioridade sobre o YAML.