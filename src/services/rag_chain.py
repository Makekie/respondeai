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
    
    def _expandir_query_com_metadados(self, tema: str) -> str:
        """Expande a query incluindo termos relacionados a leis específicas"""
        # Mapeia termos comuns para leis específicas
        mapeamento_leis = {
            "lei de introdução": "Lei 4657 LINDB",
            "lindb": "Lei 4657 Lei de Introdução às Normas do Direito Brasileiro",
            "4657": "Lei 4657 LINDB Lei de Introdução",
            "código civil": "Lei 10406 Código Civil",
            "10406": "Lei 10406 Código Civil",
            "constituição": "Constituição Federal CF/88",
            "cf/88": "Constituição Federal",
            "código penal": "Decreto-Lei 2848 Código Penal",
            "2848": "Decreto-Lei 2848 Código Penal"
        }
        
        tema_lower = tema.lower()
        query_expandida = tema
        
        # Adiciona termos relacionados
        for termo, expansao in mapeamento_leis.items():
            if termo in tema_lower:
                query_expandida += f" {expansao}"
        
        return query_expandida
    
    async def _buscar_contexto_inteligente(self, tema: str, k: int = 5) -> List[Document]:
        """Busca contexto considerando metadados e conteúdo"""
        try:
            # 1. Expande query com termos relacionados
            query_expandida = self._expandir_query_com_metadados(tema)
            
            # 2. Busca artigos em vigor primeiro
            docs_vigor = await self.vectorstore_service.buscar_similares(
                query_expandida, k=max(1, k//2), filtro={"em_vigor": True}
            )
            
            # 3. Busca geral para complementar
            docs_geral = await self.vectorstore_service.buscar_similares(
                query_expandida, k=k
            )
            
            # 4. Combina priorizando artigos em vigor e remove duplicatas
            docs_combinados = docs_vigor.copy() if docs_vigor else []
            for doc in (docs_geral or []):
                if doc not in docs_combinados and len(docs_combinados) < k:
                    docs_combinados.append(doc)
            
            # 5. Filtra por relevância de metadados se possível
            if docs_combinados:
                docs_filtrados = self._filtrar_por_metadados(docs_combinados, tema)
                return docs_filtrados[:k]
            else:
                logger.warning("Nenhum documento encontrado na busca")
                return []
                
        except Exception as e:
            logger.error(f"Erro na busca inteligente: {e}")
            # Fallback para busca simples
            try:
                return await self.vectorstore_service.buscar_similares(tema, k=k)
            except Exception as fallback_error:
                logger.error(f"Erro no fallback da busca: {fallback_error}")
                return []
    
    def _filtrar_por_metadados(self, docs: List[Document], tema: str) -> List[Document]:
        """Filtra documentos por relevância de metadados"""
        tema_lower = tema.lower()
        docs_relevantes = []
        docs_outros = []
        
        for doc in docs:
            titulo = doc.metadata.get('titulo', '').lower()
            fonte = doc.metadata.get('fonte', '').lower()
            
            # Verifica se metadados são relevantes para o tema
            relevante = False
            
            # Busca por números de lei
            if any(num in tema_lower for num in ['4657', '10406', '2848']) and \
               any(num in titulo + fonte for num in ['4657', '10406', '2848']):
                relevante = True
            
            # Busca por nomes de leis
            termos_relevantes = ['introdução', 'lindb', 'civil', 'penal', 'constituição']
            if any(termo in tema_lower for termo in termos_relevantes) and \
               any(termo in titulo + fonte for termo in termos_relevantes):
                relevante = True
            
            if relevante:
                docs_relevantes.append(doc)
            else:
                docs_outros.append(doc)
        
        # Retorna relevantes primeiro, depois outros
        return docs_relevantes + docs_outros
    
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
        1. Busca contexto relevante considerando metadados
        2. Monta o prompt com contexto e questões existentes
        3. Gera questões via LLM
        4. Parseia resultado em JSON
        """
        try:
            # 1. Busca contexto inteligente considerando metadados
            logger.info(f"Buscando contexto para: {tema}")
            docs = await self._buscar_contexto_inteligente(tema, k=5)
            
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
            
            # 5. Executa com tratamento de erro robusto
            logger.info("Gerando questões via LLM...")
            
            try:
                resultado = await chain.ainvoke({
                    "contexto": contexto,
                    "tema": tema,
                    "quantidade": quantidade,
                    "nivel_dificuldade": nivel_dificuldade,
                    "tipo_questao": tipo.value,
                    "formato_questao": formato_questao,
                    "questoes_existentes": questoes_existentes_texto
                })
                
                # Verifica se o resultado é válido
                if not isinstance(resultado, dict) or "questoes" not in resultado:
                    logger.error(f"Resultado inválido do LLM: {resultado}")
                    return {
                        "sucesso": False,
                        "questoes": [],
                        "erro": "LLM retornou formato inválido"
                    }
                
            except Exception as parse_error:
                logger.error(f"Erro no parsing JSON: {parse_error}")
                # Fallback: tenta sem parser JSON
                try:
                    chain_fallback = prompt | llm
                    resultado_texto = await chain_fallback.ainvoke({
                        "contexto": contexto,
                        "tema": tema,
                        "quantidade": quantidade,
                        "nivel_dificuldade": nivel_dificuldade,
                        "tipo_questao": tipo.value,
                        "formato_questao": formato_questao,
                        "questoes_existentes": questoes_existentes_texto
                    })
                    logger.warning(f"Fallback - resposta em texto: {resultado_texto[:500]}...")
                    return {
                        "sucesso": False,
                        "questoes": [],
                        "erro": f"Erro no parsing JSON: {str(parse_error)}"
                    }
                except Exception as fallback_error:
                    logger.error(f"Erro no fallback: {fallback_error}")
                    return {
                        "sucesso": False,
                        "questoes": [],
                        "erro": f"Erro completo: {str(parse_error)}"
                    }
            
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
            
            # 4. Executa com tratamento de erro
            logger.info("Gerando resposta via LLM...")
            
            try:
                resultado = await chain.ainvoke({
                    "contexto": contexto,
                    "pergunta": pergunta,
                    "alternativas_texto": alternativas_texto,
                    "contexto_adicional": ctx_adicional
                })
                
                # Verifica se o resultado é válido
                if not isinstance(resultado, dict):
                    logger.error(f"Resultado inválido do LLM: {resultado}")
                    return {
                        "sucesso": False,
                        "resposta_correta": "",
                        "explicacao_detalhada": "LLM retornou formato inválido",
                        "fundamento_legal": "",
                        "dicas_estudo": [],
                        "referencias": []
                    }
                
            except Exception as parse_error:
                logger.error(f"Erro no parsing JSON da resposta: {parse_error}")
                return {
                    "sucesso": False,
                    "resposta_correta": "",
                    "explicacao_detalhada": f"Erro no parsing: {str(parse_error)}",
                    "fundamento_legal": "",
                    "dicas_estudo": [],
                    "referencias": []
                }
            
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