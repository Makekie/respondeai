# src/services/llm_service.py
"""
Serviço de LLM usando Ollama via LangChain.
"""
import logging
from typing import List, Optional

from core.config import settings

logger = logging.getLogger(__name__)

# Imports com fallback
try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings
    logger.info("✅ Usando langchain-ollama")
except ImportError:
    logger.warning("⚠️ langchain-ollama não encontrado, usando langchain-community")
    from langchain_community.chat_models import ChatOllama
    from langchain_community.embeddings import OllamaEmbeddings


def get_llm(temperature: float = 0.7, model: str = None) -> ChatOllama:
    """Retorna instância do ChatOllama configurada."""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model or settings.OLLAMA_MODEL,
        temperature=temperature,
    )


def get_llm_creative(temperature: float = 0.8) -> ChatOllama:
    """LLM com maior criatividade para geração de questões variadas"""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=temperature,
    )


def get_llm_precise(temperature: float = 0.2) -> ChatOllama:
    """LLM com baixa temperatura para respostas precisas"""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=temperature,
    )


def get_embeddings() -> OllamaEmbeddings:
    """Retorna instância do OllamaEmbeddings configurada com parâmetros otimizados."""
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_EMBEDDING_MODEL,
        # Parâmetros para evitar problemas de contexto
        show_progress=False,
        # Processa um documento por vez para evitar problemas de batch
        embed_instruction="",
        query_instruction=""
    )


async def verificar_ollama() -> dict:
    """Verifica se o Ollama está disponível e lista modelos"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                modelos = [m['name'] for m in data.get('models', [])]
                
                # Extrai nome base do modelo configurado (sem :latest, :3b, etc)
                modelo_llm_base = settings.OLLAMA_MODEL.split(':')[0]
                modelo_emb_base = settings.OLLAMA_EMBEDDING_MODEL.split(':')[0]
                
                # Verifica se algum modelo disponível começa com o nome base
                modelo_llm_ok = any(m.startswith(modelo_llm_base) for m in modelos)
                modelo_emb_ok = any(m.startswith(modelo_emb_base) for m in modelos)
                
                return {
                    "disponivel": True,
                    "modelos": modelos,
                    "modelo_llm": {
                        "configurado": settings.OLLAMA_MODEL,
                        "disponivel": modelo_llm_ok
                    },
                    "modelo_embedding": {
                        "configurado": settings.OLLAMA_EMBEDDING_MODEL,
                        "disponivel": modelo_emb_ok
                    }
                }
    except Exception as e:
        logger.error(f"Erro ao verificar Ollama: {e}")
    
    return {
        "disponivel": False, 
        "modelos": [],
        "erro": "Não foi possível conectar ao Ollama"
    }