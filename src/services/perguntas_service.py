import logging
from typing import List

from models.schemas import (
    CriarPerguntasRequest,
    CriarPerguntasResponse,
    ResponderPerguntaRequest,
    ResponderPerguntaResponse,
    QuestaoGerada,
    Alternativa
)
from services.rag_chain import RAGChainService

logger = logging.getLogger(__name__)


class PerguntasService:
    """Serviço principal que orquestra a geração e resposta de questões"""
    
    def __init__(self):
        self.rag_chain = RAGChainService()
    
    async def criar_perguntas(
        self,
        request: CriarPerguntasRequest
    ) -> CriarPerguntasResponse:
        """
        Cria questões de concurso baseadas no tema.
        
        Usa RAG para enriquecer o contexto e gerar
        questões mais precisas e fundamentadas.
        """
        try:
            resultado = await self.rag_chain.gerar_questoes(
                tema=request.tema,
                quantidade=request.quantidade,
                dificuldade=request.dificuldade,
                tipo=request.tipo,
                banca=request.banca
            )
            
            if not resultado.get("sucesso"):
                return CriarPerguntasResponse(
                    sucesso=False,
                    tema=request.tema,
                    quantidade_gerada=0,
                    questoes=[]
                )
            
            # Converte para modelos Pydantic
            questoes = self._processar_questoes(resultado.get("questoes", []))
            
            return CriarPerguntasResponse(
                sucesso=True,
                tema=request.tema,
                quantidade_gerada=len(questoes),
                questoes=questoes,
                fontes_consultadas=resultado.get("fontes_consultadas")
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar perguntas: {e}")
            return CriarPerguntasResponse(
                sucesso=False,
                tema=request.tema,
                quantidade_gerada=0,
                questoes=[]
            )
    
    async def responder_pergunta(
        self,
        request: ResponderPerguntaRequest
    ) -> ResponderPerguntaResponse:
        """
        Responde uma questão de concurso.
        
        Usa RAG para buscar fundamentos legais
        e fornecer explicação detalhada.
        """
        try:
            resultado = await self.rag_chain.responder_questao(
                pergunta=request.pergunta,
                alternativas=request.alternativas,
                contexto_adicional=request.contexto_adicional
            )
            
            return ResponderPerguntaResponse(
                sucesso=resultado.get("sucesso", False),
                pergunta=request.pergunta,
                resposta_correta=resultado.get("resposta_correta", ""),
                explicacao_detalhada=resultado.get("explicacao_detalhada", ""),
                fundamento_legal=resultado.get("fundamento_legal", ""),
                dicas_estudo=resultado.get("dicas_estudo"),
                referencias=resultado.get("referencias")
            )
            
        except Exception as e:
            logger.error(f"Erro ao responder: {e}")
            return ResponderPerguntaResponse(
                sucesso=False,
                pergunta=request.pergunta,
                resposta_correta="",
                explicacao_detalhada=str(e),
                fundamento_legal=""
            )
    
    def _processar_questoes(self, questoes_raw: List[dict]) -> List[QuestaoGerada]:
        """Converte dicts em objetos QuestaoGerada"""
        questoes = []
        
        for i, q in enumerate(questoes_raw, 1):
            try:
                alternativas = None
                if q.get("alternativas"):
                    alternativas = [
                        Alternativa(
                            letra=alt.get("letra", ""),
                            texto=alt.get("texto", ""),
                            correta=alt.get("correta", False)
                        )
                        for alt in q["alternativas"]
                    ]
                
                questao = QuestaoGerada(
                    numero=q.get("numero", i),
                    enunciado=q.get("enunciado", ""),
                    alternativas=alternativas,
                    resposta_correta=q.get("resposta_correta", ""),
                    justificativa=q.get("justificativa", ""),
                    fonte_legal=q.get("fonte_legal")
                )
                questoes.append(questao)
                
            except Exception as e:
                logger.warning(f"Erro ao processar questão {i}: {e}")
                continue
        
        return questoes


# Singleton
perguntas_service = PerguntasService()