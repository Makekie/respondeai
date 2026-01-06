# PerguntAI

**PerguntAI** é um projeto *open source* que disponibiliza uma API para geração gratuita de questões de **Direito Administrativo brasileiro**, utilizando **Large Language Models (LLMs)**. O público-alvo são estudantes de concursos públicos (*concurseiros*), auxiliando no estudo ativo por meio da prática de questões.

---

## 🚀 Visão Geral

O projeto consiste em um **webservice baseado em FastAPI**, integrado a um modelo de linguagem executado localmente via **Ollama** e a um mecanismo de busca **OpenSearch**, permitindo a geração, armazenamento e recuperação de conteúdos jurídicos.

---

## 🧰 Tecnologias Utilizadas

- **Python 3.12**
- **FastAPI**
- **uv** (gerenciamento de dependências e ambientes virtuais)
- **Ollama** (execução local de LLMs)
- **OpenSearch** (indexação e busca)
- **Docker & Docker Compose**
- **Makefile** (atalhos para execução)

---

## 📋 Pré-requisitos

Antes de executar o projeto, certifique-se de ter instalado:

- **Python 3.12**
- **Docker** e **Docker Compose**
- **uv**
  ```bash
  pip install uv
  ```
- **Ollama**

  https://ollama.com/

Após instalar o Ollama, inicie o serviço:

```bash
ollama serve
```

E faça o download dos modelos utilizados:

```bash
ollama pull llama3.2:3b
ollama pull bge-m3:latest
```

---

## ⚙️ Configuração

As configurações da aplicação estão centralizadas no arquivo:

```
config.yaml
```

### Exemplo:

```yaml
app:
  name: "Gerador de Questões"
  version: "1.0.0"
  env: "development"
  debug: true
  host: "0.0.0.0"
  port: 8000

ollama:
  base_url: "http://localhost:11434"
  model: "llama3.2:3b"
  embedding_model: "bge-m3:latest"
```

As configurações do **OpenSearch** estão definidas no arquivo `docker-compose.yml`.

---

## 🐳 Subindo o OpenSearch

Na raiz do projeto, execute:

```bash
docker compose up -d
```

Serviços disponíveis:

- **OpenSearch API**: http://localhost:9200
- **OpenSearch Dashboards**: http://localhost:5601

> ⚠️ O OpenSearch pode levar alguns segundos para ficar disponível após a inicialização.

---

## 📦 Instalação das Dependências

O projeto utiliza o **uv** para gerenciamento de dependências.

```bash
make install
```

Para instalar dependências de desenvolvimento:

```bash
make install-dev
```

---

## ▶️ Executando a Aplicação

Após subir o OpenSearch e instalar as dependências:

```bash
make run
```

A API estará disponível em:

```
http://localhost:8000
```

Documentação automática (Swagger):

```
http://localhost:8000/docs
```

---

## 🧪 Testes

Para executar os testes de serviço:

```bash
make test_service
```

---

## 🛠️ Comandos Disponíveis (Makefile)

| Comando | Descrição |
|------|----------|
| `make install` | Cria o ambiente virtual e instala dependências |
| `make install-dev` | Instala dependências de desenvolvimento |
| `make run` | Inicia a aplicação FastAPI |
| `make test_service` | Executa testes de serviço |
| `make clean` | Remove o ambiente virtual |

---

## 🤝 Contribuindo

Contribuições são bem-vindas!

1. Faça um fork do repositório
2. Crie uma branch para sua feature ou correção (`git checkout -b feature/minha-feature`)
3. Faça commit das alterações (`git commit -m 'Minha contribuição'`)
4. Faça push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto é distribuído sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.

---

## 📌 Status do Projeto

🚧 Em desenvolvimento ativo.

---

## ✨ Agradecimentos

Este projeto foi desenvolvido com fins educacionais e de apoio ao estudo para concursos públicos, incentivando o uso responsável e acessível de tecnologias baseadas em LLMs.

