from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
import logging

from models.schemas import (
    CriarPerguntasRequest,
    CriarPerguntasResponse,
    DocumentoRequest,
    DocumentoResponse
)
from services.perguntas_service import PerguntasService
from services.vectorstore_service import VectorStoreService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/perguntas", tags=["Perguntas"])


@router.post(
    "/criar",
    response_model=CriarPerguntasResponse,
    summary="Gerar questões de concurso",
    description="Gera questões baseadas em um tema usando RAG com LangChain"
)
async def criar_perguntas(request: CriarPerguntasRequest):
    """
    Gera questões para estudo de concursos públicos.
    
    ## Parâmetros:
    - **tema**: Tema jurídico (ex: "Direito Constitucional - Direitos Fundamentais")
    - **quantidade**: Número de questões a gerar (1-20)
    - **dificuldade**: Nível de dificuldade (facil, medio, dificil)
    - **tipo**: Formato da questão (multipla_escolha, certo_errado, dissertativa)
    - **banca**: Estilo de banca examinadora (CESPE, FCC, FGV, VUNESP, ESAF)
    
    ## Retorno:
    - Lista de questões com enunciado, alternativas, gabarito e justificativa
    - Fontes consultadas no processo de RAG
    """
    try:
        service = PerguntasService()
        resultado = await service.criar_perguntas(request)
        
        if not resultado.sucesso:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao gerar questões. Verifique os logs."
            )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint criar_perguntas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/indexar",
    response_model=DocumentoResponse,
    summary="Indexar documento na base de conhecimento",
    description="Adiciona um documento ao vector store para enriquecer o RAG"
)
async def indexar_documento(documento: DocumentoRequest):
    """
    Adiciona um documento à base de conhecimento.
    
    ## Tipos aceitos:
    - **lei**: Legislação (CF, Códigos, Leis ordinárias)
    - **jurisprudencia**: Decisões de tribunais
    - **doutrina**: Textos doutrinários
    - **sumula**: Súmulas vinculantes e não vinculantes
    
    ## Exemplo de uso:
    ```json
    {
        "titulo": "Art. 5º da Constituição Federal",
        "conteudo": "Todos são iguais perante a lei...",
        "tipo": "lei",
        "fonte": "CF/88"
    }
    ```
    """
    try:
        service = VectorStoreService()
        doc_id = await service.adicionar_documento(
            titulo=documento.titulo,
            conteudo=documento.conteudo,
            tipo=documento.tipo,
            fonte=documento.fonte
        )
        
        if not doc_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao indexar documento"
            )
        
        return DocumentoResponse(
            sucesso=True,
            documento_id=doc_id,
            mensagem=f"Documento '{documento.titulo}' indexado com sucesso"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao indexar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/buscar",
    summary="Buscar documentos similares",
    description="Busca semântica na base de conhecimento"
)
async def buscar_documentos(
    query: str = Query(..., description="Texto de busca", min_length=3),
    limite: int = Query(default=5, ge=1, le=20, description="Número máximo de resultados")
):
    """
    Realiza busca semântica na base de conhecimento.
    
    Útil para verificar o contexto que será usado na geração de questões.
    """
    try:
        service = VectorStoreService()
        docs = await service.buscar_similares(query, k=limite)
        
        resultados = []
        for doc in docs:
            resultados.append({
                "titulo": doc.metadata.get("titulo", ""),
                "tipo": doc.metadata.get("tipo", ""),
                "fonte": doc.metadata.get("fonte", ""),
                "trecho": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
            })
        
        return {
            "query": query,
            "total_encontrados": len(resultados),
            "documentos": resultados
        }
        
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/estatisticas",
    summary="Estatísticas da base de conhecimento"
)
async def estatisticas():
    """Retorna estatísticas sobre a base de conhecimento"""
    try:
        service = VectorStoreService()
        total = await service.contar_documentos()
        
        return {
            "total_documentos": total,
            "indice": service._index_name,
            "status": "ativo" if await service.verificar_conexao() else "offline"
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )