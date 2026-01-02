import re
import os
import pymupdf
import json
from typing import List, Dict, Any
from pathlib import Path
import logging
from langchain_core.documents import Document

from core.config import settings
from services.vectorstore_service import vectorstore_service

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    """Serviço para extrair artigos de PDFs e indexar no vector store"""
    
    def __init__(self):
        self.padrao_artigo = r"(?<!['\"])\b(Art\.\s*\d+[ºo]?)\s*(.*?)(?=\s*(?<!['\"])\bArt\.\s*\d+[ºo]?|\Z)"
    
    def processar_pdf(self, caminho_pdf: str) -> List[Dict[str, Any]]:
        """Processa um único PDF e extrai artigos"""
        artigos = []
        texto = ""
        bloco_textual = []

        try:
            with pymupdf.open(caminho_pdf) as pdf_file:
                for page in pdf_file:
                    texto += page.get_text()
                    bloco_textual.append(page.get_text("blocks", sort=False))

            # Nome da Lei (título no topo da primeira página)
            try:
                nome_lei = bloco_textual[0][2][4][:-1]
            except Exception:
                nome_lei = os.path.basename(caminho_pdf).replace(".pdf", "")

            correspondencia = re.findall(self.padrao_artigo, texto, re.DOTALL)

            # Contador de repetições
            contador_artigos = {}
            for numero_artigo, _ in correspondencia:
                numeracao = re.search(r'\d+', numero_artigo).group()
                chave = f"Art. {numeracao}"
                contador_artigos[chave] = contador_artigos.get(chave, 0) + 1

            for numero_artigo, texto_artigo in correspondencia:
                numeracao = re.search(r'\d+', numero_artigo).group()
                chave = f"Art. {numeracao}"
                corpo_texto_artigo = ' '.join(texto_artigo.strip().split())
                
                # Determina se está em vigor
                em_vigor = True
                if contador_artigos[chave] > 1:
                    corpo_texto_artigo += " (VETADO)"
                    contador_artigos[chave] -= 1
                    em_vigor = False

                artigos.append({
                    "area": "Direito Administrativo",
                    "titulo": nome_lei,
                    "numero": numero_artigo.strip(),
                    "conteudo": corpo_texto_artigo,
                    "em_vigor": em_vigor,
                    "arquivo_origem": os.path.basename(caminho_pdf)
                })

            logger.info(f"✅ Extraídos {len(artigos)} artigos de {os.path.basename(caminho_pdf)}")
            return artigos
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar {caminho_pdf}: {e}")
            return []
    
    def processar_pasta(self, caminho_pasta: str) -> List[Dict[str, Any]]:
        """Processa todos os PDFs de uma pasta"""
        todos_artigos = []
        
        if not os.path.exists(caminho_pasta):
            logger.error(f"❌ Pasta não encontrada: {caminho_pasta}")
            return []
        
        for arquivo in os.listdir(caminho_pasta):
            if arquivo.lower().endswith(".pdf"):
                caminho_pdf = os.path.join(caminho_pasta, arquivo)
                logger.info(f"🔍 Processando: {arquivo}")
                artigos_extraidos = self.processar_pdf(caminho_pdf)
                todos_artigos.extend(artigos_extraidos)
        
        logger.info(f"✅ Total de artigos extraídos: {len(todos_artigos)}")
        return todos_artigos
    
    def salvar_json(self, artigos: List[Dict[str, Any]], caminho_json: str):
        """Salva artigos em arquivo JSON"""
        try:
            with open(caminho_json, "w", encoding="utf-8") as f:
                json.dump(artigos, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Artigos salvos em: {caminho_json}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar JSON: {e}")
    
    def criar_chunks(self, artigos: List[Dict[str, Any]], chunk_size: int = 1000) -> List[Document]:
        """Converte artigos em chunks para o vector store"""
        documentos = []
        
        for artigo in artigos:
            conteudo = artigo["conteudo"]
            
            # Se o artigo é pequeno, usa como um chunk único
            if len(conteudo) <= chunk_size:
                doc = Document(
                    page_content=f"{artigo['numero']}: {conteudo}",
                    metadata={
                        "area": artigo["area"],
                        "titulo": artigo["titulo"],
                        "numero": artigo["numero"],
                        "em_vigor": artigo["em_vigor"],
                        "arquivo_origem": artigo["arquivo_origem"],
                        "tipo": "artigo_completo"
                    }
                )
                documentos.append(doc)
            else:
                # Divide artigos grandes em chunks menores
                palavras = conteudo.split()
                for i in range(0, len(palavras), chunk_size // 10):  # ~100 palavras por chunk
                    chunk_palavras = palavras[i:i + chunk_size // 10]
                    chunk_texto = " ".join(chunk_palavras)
                    
                    doc = Document(
                        page_content=f"{artigo['numero']} (parte {i//100 + 1}): {chunk_texto}",
                        metadata={
                            "area": artigo["area"],
                            "titulo": artigo["titulo"],
                            "numero": artigo["numero"],
                            "em_vigor": artigo["em_vigor"],
                            "arquivo_origem": artigo["arquivo_origem"],
                            "tipo": "artigo_chunk",
                            "chunk_index": i//100
                        }
                    )
                    documentos.append(doc)
        
        return documentos
    
    async def indexar_documentos(self, documentos: List[Document]) -> bool:
        """Indexa documentos no vector store"""
        try:
            # Verifica conexão
            if not await vectorstore_service.verificar_conexao():
                logger.error("❌ Sem conexão com OpenSearch")
                return False
            
            # Cria índice se não existir
            await vectorstore_service.criar_indice()
            
            # Adiciona documentos
            ids = await vectorstore_service.adicionar_documentos(documentos)
            
            if ids:
                logger.info(f"✅ {len(ids)} documentos indexados no vector store")
                return True
            else:
                logger.error("❌ Falha ao indexar documentos")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao indexar documentos: {e}")
            return False
    
    async def processar_e_indexar(
        self, 
        caminho_pasta: str, 
        salvar_json: bool = True,
        incluir_vetados: bool = True
    ) -> dict:
        """Pipeline completo: extrai PDFs, cria chunks e indexa"""
        try:
            # 1. Extrai artigos dos PDFs
            artigos = self.processar_pasta(caminho_pasta)
            if not artigos:
                logger.error("❌ Nenhum artigo extraído")
                return {"sucesso": False}
            
            # 2. Conta estatísticas
            total_artigos = len(artigos)
            artigos_em_vigor = len([a for a in artigos if a["em_vigor"]])
            artigos_vetados = total_artigos - artigos_em_vigor
            
            logger.info(f"📊 Total: {total_artigos} | Em vigor: {artigos_em_vigor} | Vetados: {artigos_vetados}")
            
            # 3. Filtra artigos se necessário
            artigos_para_indexar = artigos
            if not incluir_vetados:
                artigos_para_indexar = [a for a in artigos if a["em_vigor"]]
                logger.info(f"📋 Indexando apenas artigos em vigor: {len(artigos_para_indexar)}")
            
            # 4. Salva JSON se solicitado
            if salvar_json:
                caminho_json = os.path.join(caminho_pasta, "leis_unificadas.json")
                self.salvar_json(artigos, caminho_json)
            
            # 5. Cria chunks para indexação
            documentos = self.criar_chunks(artigos_para_indexar)
            logger.info(f"📄 Criados {len(documentos)} chunks")
            
            # 6. Indexa no vector store
            sucesso_indexacao = await self.indexar_documentos(documentos)
            
            if sucesso_indexacao:
                logger.info("🎉 Pipeline concluído com sucesso!")
                return {
                    "sucesso": True,
                    "total_artigos": total_artigos,
                    "artigos_em_vigor": artigos_em_vigor,
                    "artigos_vetados": artigos_vetados
                }
            else:
                logger.error("❌ Falha na indexação")
                return {"sucesso": False}
                
        except Exception as e:
            logger.error(f"❌ Erro no pipeline: {e}")
            return {"sucesso": False}


# Singleton
document_extraction_service = DocumentExtractionService()