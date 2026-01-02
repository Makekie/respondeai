import logging
from typing import List
from langchain_core.documents import Document

from models.schemas import (
    CriarPerguntasRequest,
    CriarPerguntasResponse,
    ResponderPerguntaRequest,
    ResponderPerguntaResponse,
    QuestaoGerada,
    Alternativa
)
from services.rag_chain import RAGChainService
from services.vectorstore_service import vectorstore_service

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
            # Busca questões similares existentes
            questoes_similares = await self._buscar_questoes_similares(request.tema)
            
            resultado = await self.rag_chain.gerar_questoes(
                tema=request.tema,
                quantidade=request.quantidade,
                dificuldade=request.dificuldade,
                tipo=request.tipo,
                questoes_existentes=questoes_similares
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
            
            # Salva as questões geradas no vector store
            await self._salvar_questoes(questoes, request)
            
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
        
        Verifica se já existe resposta salva antes de processar.
        """
        try:
            # 1. Busca se já existe resposta para esta pergunta
            resposta_existente = await self._buscar_resposta_existente(request.pergunta)
            
            if resposta_existente:
                logger.info("✅ Resposta encontrada no cache")
                return resposta_existente
            
            # 2. Gera nova resposta
            resultado = await self.rag_chain.responder_questao(
                pergunta=request.pergunta,
                alternativas=request.alternativas,
                contexto_adicional=request.contexto_adicional
            )
            
            response = ResponderPerguntaResponse(
                sucesso=resultado.get("sucesso", False),
                pergunta=request.pergunta,
                resposta_correta=resultado.get("resposta_correta", ""),
                explicacao_detalhada=resultado.get("explicacao_detalhada", ""),
                fundamento_legal=resultado.get("fundamento_legal", ""),
                dicas_estudo=resultado.get("dicas_estudo"),
                referencias=resultado.get("referencias")
            )
            
            # 3. Salva a resposta para futuras consultas
            if response.sucesso:
                await self._salvar_resposta(request, response)
            
            return response
            
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
    
    async def _buscar_questoes_similares(self, tema: str) -> List[str]:
        """Busca questões similares já existentes"""
        try:
            docs = await vectorstore_service.buscar_similares(
                query=tema,
                k=3,
                filtro={"tipo": "questao"}
            )
            
            questoes_similares = []
            for doc in docs:
                questoes_similares.append(doc.page_content)
            
            return questoes_similares
            
        except Exception as e:
            logger.warning(f"Erro ao buscar questões similares: {e}")
            return []
    
    async def _salvar_questoes(self, questoes: List[QuestaoGerada], request: CriarPerguntasRequest):
        """Salva questões geradas no vector store"""
        try:
            documentos = []
            
            for questao in questoes:
                # Monta o conteúdo da questão
                conteudo = f"Enunciado: {questao.enunciado}\n"
                
                if questao.alternativas:
                    conteudo += "Alternativas:\n"
                    for alt in questao.alternativas:
                        conteudo += f"{alt.letra}) {alt.texto}\n"
                
                conteudo += f"Resposta: {questao.resposta_correta}\n"
                conteudo += f"Justificativa: {questao.justificativa}"
                
                doc = Document(
                    page_content=conteudo,
                    metadata={
                        "tipo": "questao",
                        "tema": request.tema,
                        "dificuldade": request.dificuldade,
                        "tipo_questao": request.tipo,
                        "banca": "FCC",
                        "numero": questao.numero,
                        "fonte_legal": questao.fonte_legal or ""
                    }
                )
                documentos.append(doc)
            
            await vectorstore_service.adicionar_documentos(documentos)
            logger.info(f"✅ Salvadas {len(documentos)} questões no vector store")
            
        except Exception as e:
            logger.error(f"Erro ao salvar questões: {e}")
    
    async def _buscar_resposta_existente(self, pergunta: str) -> ResponderPerguntaResponse:
        """Busca resposta já existente para a pergunta"""
        try:
            docs = await vectorstore_service.buscar_similares(
                query=pergunta,
                k=3,
                filtro={"tipo": "resposta"}
            )
            
            # Verifica se alguma pergunta é muito similar (evita duplicações)
            for doc in docs:
                pergunta_salva = doc.metadata.get("pergunta", "")
                
                # Comparação simples de similaridade
                if self._perguntas_similares(pergunta, pergunta_salva):
                    logger.info(f"✅ Resposta encontrada para pergunta similar")
                    metadata = doc.metadata
                    
                    return ResponderPerguntaResponse(
                        sucesso=True,
                        pergunta=pergunta,  # Usa a pergunta atual
                        resposta_correta=metadata.get("resposta_correta", ""),
                        explicacao_detalhada=metadata.get("explicacao_detalhada", ""),
                        fundamento_legal=metadata.get("fundamento_legal", ""),
                        dicas_estudo=metadata.get("dicas_estudo", []),
                        referencias=metadata.get("referencias", [])
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao buscar resposta existente: {e}")
            return None
    
    def _perguntas_similares(self, pergunta1: str, pergunta2: str) -> bool:
        """Verifica se duas perguntas são muito similares"""
        # Remove espaços e converte para minúsculo
        p1 = pergunta1.lower().strip()
        p2 = pergunta2.lower().strip()
        
        # Se são idênticas
        if p1 == p2:
            return True
        
        # Verifica similaridade por palavras-chave
        palavras1 = set(p1.split())
        palavras2 = set(p2.split())
        
        # Se mais de 80% das palavras são comuns
        intersecao = len(palavras1.intersection(palavras2))
        uniao = len(palavras1.union(palavras2))
        
        similaridade = intersecao / uniao if uniao > 0 else 0
        return similaridade > 0.8
    
    async def _salvar_resposta(self, request: ResponderPerguntaRequest, response: ResponderPerguntaResponse):
        """Salva resposta no vector store para cache"""
        try:
            # Monta conteúdo da resposta
            conteudo = f"Pergunta: {request.pergunta}\n"
            
            if request.alternativas:
                conteudo += "Alternativas:\n"
                for alt in request.alternativas:
                    conteudo += f"{alt}\n"
            
            conteudo += f"\nResposta Correta: {response.resposta_correta}\n"
            conteudo += f"Explicação: {response.explicacao_detalhada}\n"
            conteudo += f"Fundamento Legal: {response.fundamento_legal}"
            
            doc = Document(
                page_content=conteudo,
                metadata={
                    "tipo": "resposta",
                    "pergunta": request.pergunta,
                    "resposta_correta": response.resposta_correta,
                    "explicacao_detalhada": response.explicacao_detalhada,
                    "fundamento_legal": response.fundamento_legal,
                    "dicas_estudo": response.dicas_estudo or [],
                    "referencias": response.referencias or []
                }
            )
            
            await vectorstore_service.adicionar_documentos([doc])
            logger.info("✅ Resposta salva no vector store")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resposta: {e}")


# Singleton
perguntas_service = PerguntasService()