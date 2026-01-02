from fastapi import APIRouter, HTTPException, status
import logging

from models.schemas import (
    CriarPerguntasRequest,
    CriarPerguntasResponse
)
from services.perguntas_service import PerguntasService

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