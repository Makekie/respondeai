from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File
from pydantic import BaseModel
from typing import List
import logging
import tempfile
import os

from services.document_extraction_service import document_extraction_service
from services.vectorstore_service import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


class ProcessDocumentsRequest(BaseModel):
    salvar_json: bool = True
    incluir_vetados: bool = True


class ProcessDocumentsResponse(BaseModel):
    message: str
    success: bool
    total_artigos: int = 0
    artigos_em_vigor: int = 0
    artigos_vetados: int = 0


@router.post("/process", response_model=ProcessDocumentsResponse)
async def processar_documentos(
    files: List[UploadFile] = File(..., description="Arquivos PDF para processar"),
    salvar_json: bool = True,
    incluir_vetados: bool = True
):
    """Processa arquivos PDF enviados e indexa no vector store"""
    try:
        # Cria diretório temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            # Salva arquivos enviados
            for file in files:
                if not file.filename.lower().endswith('.pdf'):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Arquivo {file.filename} não é um PDF"
                    )
                
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
            
            # Processa os arquivos
            resultado = await document_extraction_service.processar_e_indexar(
                caminho_pasta=temp_dir,
                salvar_json=salvar_json,
                incluir_vetados=incluir_vetados
            )
            
            if resultado["sucesso"]:
                return ProcessDocumentsResponse(
                    message="Documentos processados e indexados com sucesso",
                    success=True,
                    total_artigos=resultado["total_artigos"],
                    artigos_em_vigor=resultado["artigos_em_vigor"],
                    artigos_vetados=resultado["artigos_vetados"]
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Falha ao processar documentos"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar documentos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )


@router.post("/process-background")
async def processar_documentos_background(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    salvar_json: bool = True,
    incluir_vetados: bool = True
):
    """Processa documentos em background"""
    # Salva arquivos em diretório temporário
    temp_dir = tempfile.mkdtemp()
    
    try:
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Arquivo {file.filename} não é um PDF"
                )
            
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
        
        background_tasks.add_task(
            document_extraction_service.processar_e_indexar,
            temp_dir,
            salvar_json,
            incluir_vetados
        )
        
        return {"message": "Processamento iniciado em background"}
        
    except Exception as e:
        # Limpa diretório em caso de erro
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


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