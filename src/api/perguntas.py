from fastapi import APIRouter, HTTPException, status, Form
from typing import Optional
import logging

from models.schemas import (
    CriarPerguntasResponse,
    DificuldadeEnum,
    TipoQuestaoEnum
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
async def criar_perguntas(
    tema: str = Form(..., description="Tema jurídico para gerar questões"),
    quantidade: int = Form(default=5, ge=1, le=20, description="Quantidade de questões"),
    dificuldade: DificuldadeEnum = Form(default=DificuldadeEnum.MEDIO, description="Nível de dificuldade"),
    tipo: TipoQuestaoEnum = Form(default=TipoQuestaoEnum.MULTIPLA_ESCOLHA, description="Formato da questão")
):
    """
    Gera questões para estudo de concursos públicos.
    
    ## Parâmetros:
    - **tema**: Tema jurídico (ex: "Direito Constitucional - Direitos Fundamentais")
    - **quantidade**: Número de questões a gerar (1-20)
    - **dificuldade**: Nível de dificuldade (facil, medio, dificil)
    - **tipo**: Formato da questão (multipla_escolha)
    
    ## Retorno:
    - Lista de questões com enunciado, alternativas, gabarito e justificativa
    - Fontes consultadas no processo de RAG
    """
    try:
        # Cria objeto request interno
        from models.schemas import CriarPerguntasRequest
        request = CriarPerguntasRequest(
            tema=tema,
            quantidade=quantidade,
            dificuldade=dificuldade,
            tipo=tipo
        )
        
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