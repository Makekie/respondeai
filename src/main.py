from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn

from api.perguntas import router as rotas_perguntas
from api.responder import router as rotas_responder
from api.documents import router as rotas_documents
from core.config import settings
from services.llm_service import verificar_ollama
from services.vectorstore_service import VectorStoreService

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    logger.info("🚀 Iniciando aplicação com LangChain...")
    
    # Verifica Ollama
    ollama_status = await verificar_ollama()
    if ollama_status["disponivel"]:
        logger.info(f"✅ Ollama conectado - Modelos: {ollama_status['modelos']}")
    else:
        logger.warning("⚠️ Ollama não disponível - Verifique se está rodando")
    
    # Verifica e inicializa OpenSearch
    try:
        vectorstore = VectorStoreService()
        if await vectorstore.verificar_conexao():
            logger.info("✅ OpenSearch conectado")
            await vectorstore.criar_indice()
            total_docs = await vectorstore.contar_documentos()
            logger.info(f"📚 Documentos indexados: {total_docs}")
        else:
            logger.warning("⚠️ OpenSearch não disponível")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar OpenSearch: {e}")
    
    logger.info("=" * 50)
    logger.info(f"📖 Documentação: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 50)
    
    yield
    
    logger.info("👋 Encerrando aplicação...")


# Criação da aplicação
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 📚 API para Geração de Questões de Concursos

Esta API utiliza **LangChain** com **RAG** (Retrieval-Augmented Generation) para:

- 📝 **Gerar questões** personalizadas por tema, dificuldade e estilo de banca
- ✅ **Responder questões** com explicações detalhadas e fundamentação legal
- 📖 **Indexar documentos** para enriquecer a base de conhecimento

### Tecnologias:
- 🦜 LangChain para orquestração de LLM
- 🦙 Ollama para inferência local
- 🔍 OpenSearch para busca vetorial
- ⚡ FastAPI para a API REST
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Routers
app.include_router(rotas_perguntas)
app.include_router(rotas_responder)
app.include_router(rotas_documents)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "framework": "LangChain + FastAPI",
        "environment": settings.APP_ENV,
        "message": "API está rodando!",
        "documentacao": "/docs",
        "endpoints": {
            "gerar_questoes": "POST /perguntas/criar",
            "responder_questao": "POST /responder/",
            "processar_pdfs": "POST /documents/process",
            "buscar_documentos": "GET /documents/buscar",
            "estatisticas": "GET /documents/estatisticas"
        }
    }


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Verifica saúde de todos os serviços"""
    
    # Verifica Ollama
    ollama_status = await verificar_ollama()
    
    # Verifica OpenSearch
    try:
        vectorstore = VectorStoreService()
        opensearch_ok = await vectorstore.verificar_conexao()
        docs_count = await vectorstore.contar_documentos() if opensearch_ok else 0
    except:
        opensearch_ok = False
        docs_count = 0
    
    todos_ok = ollama_status["disponivel"] and opensearch_ok
    
    return {
        "status": "healthy" if todos_ok else "degraded",
        "services": {
            "ollama": {
                "status": "up" if ollama_status["disponivel"] else "down",
                "model": settings.OLLAMA_MODEL,
                "embedding_model": settings.OLLAMA_EMBEDDING_MODEL
            },
            "opensearch": {
                "status": "up" if opensearch_ok else "down",
                "index": settings.OPENSEARCH_INDEX,
                "documents": docs_count
            }
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )