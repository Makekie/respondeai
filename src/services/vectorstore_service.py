# src/services/vectorstore_service.py
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.documents import Document
from opensearchpy import OpenSearch
from typing import List, Optional, Dict, Any
import logging

from core.config import settings
from services.llm_service import get_embeddings

logger = logging.getLogger(__name__)

# Dimensão do embedding do bge-m3
BGE_M3_DIMENSION = 1024


class VectorStoreService:
    """Serviço para gerenciar o vector store com OpenSearch"""
    
    _instance: Optional['VectorStoreService'] = None
    _vectorstore: Optional[OpenSearchVectorSearch] = None
    _client: Optional[OpenSearch] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._embeddings = get_embeddings()
            self._index_name = settings.OPENSEARCH_INDEX
            self._initialize_client()
            self._initialized = True
    
    def _initialize_client(self):
        """Inicializa o cliente OpenSearch"""
        try:
            self._client = OpenSearch(
                hosts=[{
                    'host': settings.OPENSEARCH_HOST,
                    'port': settings.OPENSEARCH_PORT
                }],
                http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
                use_ssl=settings.OPENSEARCH_USE_SSL,
                verify_certs=False,
                ssl_show_warn=False,
                timeout=30
            )
            
            self._vectorstore = OpenSearchVectorSearch(
                opensearch_url=settings.opensearch_url,
                index_name=self._index_name,
                embedding_function=self._embeddings,
                http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
                use_ssl=settings.OPENSEARCH_USE_SSL,
                verify_certs=False,
                ssl_show_warn=False,
            )
            
            logger.info("✅ VectorStore inicializado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar VectorStore: {e}")
            raise
    
    @property
    def vectorstore(self) -> OpenSearchVectorSearch:
        return self._vectorstore
    
    async def verificar_conexao(self) -> bool:
        """Verifica conexão com OpenSearch"""
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"Erro ao verificar conexão: {e}")
            return False
    
    async def criar_indice(self) -> bool:
        """
        Cria o índice com configurações para KNN.
        
        Usa 'lucene' engine (compatível com OpenSearch 2.x e 3.x)
        """
        try:
            if self._client.indices.exists(index=self._index_name):
                logger.info(f"📦 Índice '{self._index_name}' já existe")
                return True
            
            # Configuração compatível com OpenSearch 2.x e 3.x
            # Usando 'lucene' engine ao invés de 'nmslib' (deprecated)
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    }
                },
                "mappings": {
                    "properties": {
                        "vector_field": {
                            "type": "knn_vector",
                            "dimension": BGE_M3_DIMENSION,  # 1024 para bge-m3
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "lucene",  # ✅ Compatível com OpenSearch 3.x
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 16
                                }
                            }
                        },
                        "text": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "metadata": {
                            "type": "object",
                            "enabled": True
                        }
                    }
                }
            }
            
            self._client.indices.create(
                index=self._index_name,
                body=index_body
            )
            logger.info(f"✅ Índice '{self._index_name}' criado (engine=lucene, dim={BGE_M3_DIMENSION})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar índice: {e}")
            return False
    
    async def deletar_indice(self) -> bool:
        """Deleta o índice (útil para recriar com novas configs)"""
        try:
            if self._client.indices.exists(index=self._index_name):
                self._client.indices.delete(index=self._index_name)
                logger.info(f"🗑️ Índice '{self._index_name}' deletado")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao deletar índice: {e}")
            return False
    
    async def recriar_indice(self) -> bool:
        """Deleta e recria o índice"""
        await self.deletar_indice()
        return await self.criar_indice()
    
    async def adicionar_documentos(self, documentos: List[Document]) -> List[str]:
        """Adiciona documentos ao vector store"""
        try:
            ids = self._vectorstore.add_documents(documentos)
            logger.info(f"✅ Adicionados {len(ids)} documentos")
            return ids
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar documentos: {e}")
            return []
    
    async def adicionar_documento(
        self,
        titulo: str,
        conteudo: str,
        tipo: str,
        fonte: str = None,
        metadata: dict = None
    ) -> Optional[str]:
        """Adiciona um único documento"""
        try:
            doc_metadata = {
                "titulo": titulo,
                "tipo": tipo,
                "fonte": fonte or "",
                **(metadata or {})
            }
            
            documento = Document(
                page_content=f"{titulo}\n\n{conteudo}",
                metadata=doc_metadata
            )
            
            ids = await self.adicionar_documentos([documento])
            return ids[0] if ids else None
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar documento: {e}")
            return None
    
    async def buscar_similares(
        self,
        query: str,
        k: int = None,
        filtro: Dict[str, Any] = None
    ) -> List[Document]:
        """Busca documentos similares à query"""
        try:
            k = k or settings.RAG_TOP_K
            
            docs_with_scores = self._vectorstore.similarity_search_with_score(
                query=query,
                k=k
            )
            
            documentos = [
                doc for doc, score in docs_with_scores
                if score >= settings.RAG_SCORE_THRESHOLD
            ]
            
            logger.info(f"🔍 Encontrados {len(documentos)} documentos")
            return documentos
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return []
    
    async def buscar_similares_com_score(
        self,
        query: str,
        k: int = None
    ) -> List[tuple]:
        """Busca documentos com seus scores"""
        try:
            k = k or settings.RAG_TOP_K
            return self._vectorstore.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return []
    
    def get_retriever(self, k: int = None, score_threshold: float = None):
        """Retorna retriever para uso em chains"""
        k = k or settings.RAG_TOP_K
        threshold = score_threshold or settings.RAG_SCORE_THRESHOLD
        
        return self._vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": k,
                "score_threshold": threshold
            }
        )
    
    async def contar_documentos(self) -> int:
        """Conta total de documentos no índice"""
        try:
            result = self._client.count(index=self._index_name)
            return result.get('count', 0)
        except:
            return 0


# Singleton
vectorstore_service = VectorStoreService()