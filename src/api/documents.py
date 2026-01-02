from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import logging

from services.document_extraction_service import document_extraction_service
from services.vectorstore_service import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


class ProcessDocumentsRequest(BaseModel):
    caminho_pasta: str
    salvar_json: bool = True
    apenas_em_vigor: bool = True


class ProcessDocumentsResponse(BaseModel):
    message: str
    success: bool


@router.post("/process", response_model=ProcessDocumentsResponse)
async def processar_documentos(request: ProcessDocumentsRequest):
    """Processa PDFs de uma pasta e indexa no vector store"""
    try:
        sucesso = await document_extraction_service.processar_e_indexar(
            caminho_pasta=request.caminho_pasta,
            salvar_json=request.salvar_json,
            apenas_em_vigor=request.apenas_em_vigor
        )
        
        if sucesso:
            return ProcessDocumentsResponse(
                message="Documentos processados e indexados com sucesso",
                success=True
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao processar documentos"
            )
            
    except Exception as e:
        logger.error(f"Erro ao processar documentos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )


@router.post("/process-background")
async def processar_documentos_background(
    background_tasks: BackgroundTasks,
    request: ProcessDocumentsRequest
):
    """Processa documentos em background"""
    background_tasks.add_task(
        document_extraction_service.processar_e_indexar,
        request.caminho_pasta,
        request.salvar_json,
        request.apenas_em_vigor
    )
    
    return {"message": "Processamento iniciado em background"}


@router.get("/buscar")
async def buscar_documentos(
    query: str = Query(..., description="Texto de busca", min_length=3),
    limite: int = Query(default=5, ge=1, le=20, description="Número máximo de resultados")
):
    """Busca semântica na base de conhecimento"""
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
            status_code=500,
            detail=str(e)
        )


@router.get("/estatisticas")
async def estatisticas():
    """Estatísticas da base de conhecimento"""
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
            status_code=500,
            detail=str(e)
        )