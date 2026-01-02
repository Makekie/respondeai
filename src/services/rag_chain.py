from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
import logging

from services.llm_service import get_llm_creative, get_llm_precise
from services.vectorstore_service import VectorStoreService
from prompts.templates import (
    PromptTemplates,
    get_gerar_questoes_prompt,
    get_responder_prompt
)
from models.schemas import (
    DificuldadeEnum,
    TipoQuestaoEnum,
    QuestoesOutput,
    RespostaOutput
)

logger = logging.getLogger(__name__)


class RAGChainService:
    """Serviço que implementa as chains RAG usando LangChain"""
    
    def __init__(self):
        self.vectorstore_service = VectorStoreService()
    
    def _formatar_documentos(self, docs: List[Document]) -> str:
        """Formata documentos recuperados em texto para o contexto"""
        if not docs:
            return "Nenhum contexto específico disponível. Use seu conhecimento geral sobre legislação brasileira."
        
        partes = []
        for i, doc in enumerate(docs, 1):
            titulo = doc.metadata.get('titulo', 'Documento')
            fonte = doc.metadata.get('fonte', '')
            tipo = doc.metadata.get('tipo', '')
            
            parte = f"### Documento {i}: {titulo}"
            if fonte:
                parte += f" (Fonte: {fonte})"
            if tipo:
                parte += f" [Tipo: {tipo}]"
            parte += f"\n{doc.page_content[:2000]}"
            
            partes.append(parte)
        
        return "\n\n---\n\n".join(partes)
    
    def _extrair_fontes(self, docs: List[Document]) -> List[str]:
        """Extrai lista de fontes dos documentos"""
        fontes = []
        for doc in docs:
            titulo = doc.metadata.get('titulo', '')
            fonte = doc.metadata.get('fonte', '')
            if titulo or fonte:
                fontes.append(f"{titulo} - {fonte}" if fonte else titulo)
        return fontes
    
    async def gerar_questoes(
        self,
        tema: str,
        quantidade: int,
        dificuldade: DificuldadeEnum,
        tipo: TipoQuestaoEnum,
        questoes_existentes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Chain RAG para geração de questões no estilo FCC.
        
        Fluxo:
        1. Busca contexto relevante no VectorStore
        2. Monta o prompt com contexto e questões existentes
        3. Gera questões via LLM
        4. Parseia resultado em JSON
        """
        try:
            # 1. Recupera contexto
            logger.info(f"Buscando contexto para: {tema}")
            docs = await self.vectorstore_service.buscar_similares(tema, k=5)
            contexto = self._formatar_documentos(docs)
            fontes = self._extrair_fontes(docs)
            
            # 2. Formata questões existentes
            questoes_existentes_texto = ""
            if questoes_existentes:
                questoes_existentes_texto = "## QUESTÕES SIMILARES JÁ EXISTENTES (NÃO REPETIR):\n"
                for i, questao in enumerate(questoes_existentes, 1):
                    questoes_existentes_texto += f"### Questão {i}:\n{questao}\n\n"
            
            # 3. Prepara variáveis do prompt
            nivel_dificuldade = PromptTemplates.NIVEIS_DIFICULDADE[dificuldade]
            formato_questao = PromptTemplates.FORMATOS_QUESTAO[tipo]
            
            # 4. Monta a chain
            prompt = get_gerar_questoes_prompt()
            llm = get_llm_creative(temperature=0.7)
            parser = JsonOutputParser(pydantic_object=QuestoesOutput)
            
            chain = prompt | llm | parser
            
            # 5. Executa
            logger.info("Gerando questões via LLM...")
            resultado = await chain.ainvoke({
                "contexto": contexto,
                "tema": tema,
                "quantidade": quantidade,
                "nivel_dificuldade": nivel_dificuldade,
                "tipo_questao": tipo.value,
                "formato_questao": formato_questao,
                "questoes_existentes": questoes_existentes_texto
            })
            
            return {
                "sucesso": True,
                "questoes": resultado.get("questoes", []),
                "fontes_consultadas": fontes
            }
            
        except Exception as e:
            logger.error(f"Erro na chain de geração: {e}")
            return {
                "sucesso": False,
                "questoes": [],
                "erro": str(e)
            }
    
    async def responder_questao(
        self,
        pergunta: str,
        alternativas: List[str] = None,
        contexto_adicional: str = None
    ) -> Dict[str, Any]:
        """
        Chain RAG para responder questões.
        
        Fluxo:
        1. Busca contexto jurídico relevante
        2. Monta prompt com a questão
        3. Gera resposta explicativa
        4. Retorna resposta estruturada
        """
        try:
            # 1. Recupera contexto
            logger.info("Buscando contexto para resposta...")
            docs = await self.vectorstore_service.buscar_similares(pergunta, k=5)
            contexto = self._formatar_documentos(docs)
            fontes = self._extrair_fontes(docs)
            
            # 2. Formata alternativas
            alternativas_texto = ""
            if alternativas:
                alternativas_texto = "## ALTERNATIVAS:\n" + "\n".join(alternativas)
            
            # Contexto adicional do usuário
            ctx_adicional = ""
            if contexto_adicional:
                ctx_adicional = f"## INFORMAÇÃO ADICIONAL DO USUÁRIO:\n{contexto_adicional}"
            
            # 3. Monta a chain
            prompt = get_responder_prompt()
            llm = get_llm_precise(temperature=0.2)
            parser = JsonOutputParser(pydantic_object=RespostaOutput)
            
            chain = prompt | llm | parser
            
            # 4. Executa
            logger.info("Gerando resposta via LLM...")
            resultado = await chain.ainvoke({
                "contexto": contexto,
                "pergunta": pergunta,
                "alternativas_texto": alternativas_texto,
                "contexto_adicional": ctx_adicional
            })
            
            # Adiciona fontes às referências
            referencias = resultado.get("referencias", [])
            referencias.extend(fontes)
            resultado["referencias"] = list(set(referencias))
            
            return {
                "sucesso": True,
                **resultado
            }
            
        except Exception as e:
            logger.error(f"Erro na chain de resposta: {e}")
            return {
                "sucesso": False,
                "resposta_correta": "",
                "explicacao_detalhada": f"Erro ao processar: {str(e)}",
                "fundamento_legal": "",
                "dicas_estudo": [],
                "referencias": []
            }


# Singleton
rag_chain_service = RAGChainService()