from fastapi import APIRouter, HTTPException, status
import logging

from models.schemas import (
    ResponderPerguntaRequest,
    ResponderPerguntaResponse
)
from services.perguntas_service import PerguntasService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/responder", tags=["Responder Questões"])


@router.post(
    "/",
    response_model=ResponderPerguntaResponse,
    summary="Responder questão de concurso",
    description="Analisa e responde uma questão usando RAG com LangChain"
)
async def responder_pergunta(request: ResponderPerguntaRequest):
    """
    Responde uma questão de concurso com explicação detalhada.
    
    ## Parâmetros:
    - **pergunta**: Texto completo da questão
    - **alternativas**: Lista de alternativas (opcional, para múltipla escolha)
    - **contexto_adicional**: Informações extras que possam ajudar (opcional)
    
    ## Retorno:
    - Resposta correta identificada
    - Explicação didática e detalhada
    - Fundamentação legal
    - Dicas de estudo relacionadas
    - Referências utilizadas
    
    ## Exemplo:
    ```json
    {
        "pergunta": "Segundo a CF/88, são direitos sociais, EXCETO:",
        "alternativas": [
            "A) Educação",
            "B) Saúde",
            "C) Propriedade privada",
            "D) Trabalho",
            "E) Moradia"
        ]
    }
    ```
    """
    try:
        service = PerguntasService()
        resultado = await service.responder_pergunta(request)
        
        if not resultado.sucesso:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao processar resposta"
            )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint responder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


from pydantic import BaseModel, Field
from typing import List, Optional

class ValidarRespostaRequest(BaseModel):
    pergunta: str = Field(..., description="Pergunta a ser validada")
    alternativas: Optional[List[str]] = Field(default=None, description="Alternativas se houver")
    contexto_adicional: Optional[str] = Field(default=None, description="Contexto extra")
    resposta_usuario: str = Field(..., description="Resposta escolhida pelo usuário")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pergunta": "De acordo com a CF/88, são direitos sociais, EXCETO:",
                "alternativas": [
                    "A) Educação",
                    "B) Saúde", 
                    "C) Propriedade privada",
                    "D) Trabalho",
                    "E) Moradia"
                ],
                "resposta_usuario": "C"
            }
        }


@router.post(
    "/validar",
    summary="Validar resposta do usuário",
    description="Verifica se a resposta do usuário está correta"
)
async def validar_resposta(request: ValidarRespostaRequest):
    """
    Valida a resposta do usuário e fornece feedback.
    
    ## Parâmetros:
    - **pergunta**: Texto completo da questão
    - **alternativas**: Lista de alternativas (opcional)
    - **contexto_adicional**: Informações extras (opcional)
    - **resposta_usuario**: Resposta escolhida pelo usuário (letra ou CERTO/ERRADO)
    """
    try:
        # Converte para ResponderPerguntaRequest
        pergunta_request = ResponderPerguntaRequest(
            pergunta=request.pergunta,
            alternativas=request.alternativas,
            contexto_adicional=request.contexto_adicional
        )
        
        service = PerguntasService()
        resultado = await service.responder_pergunta(pergunta_request)
        
        resposta_correta = resultado.resposta_correta.upper().strip()
        resposta_user = request.resposta_usuario.upper().strip()
        
        acertou = resposta_correta == resposta_user
        
        return {
            "acertou": acertou,
            "resposta_usuario": request.resposta_usuario,
            "resposta_correta": resultado.resposta_correta,
            "explicacao": resultado.explicacao_detalhada,
            "fundamento_legal": resultado.fundamento_legal,
            "dicas": resultado.dicas_estudo if not acertou else ["Parabéns! Continue estudando!"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao validar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )