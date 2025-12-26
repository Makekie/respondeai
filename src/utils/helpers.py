from langchain_core.documents import Document
from typing import List
import re


def limpar_texto(texto: str) -> str:
    """Remove caracteres especiais e normaliza espaços"""
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def truncar_texto(texto: str, max_chars: int = 1000) -> str:
    """Trunca texto mantendo palavras completas"""
    if not texto or len(texto) <= max_chars:
        return texto
    
    truncado = texto[:max_chars]
    ultimo_espaco = truncado.rfind(' ')
    
    if ultimo_espaco > 0:
        truncado = truncado[:ultimo_espaco]
    
    return truncado + "..."


def documentos_para_texto(docs: List[Document], max_por_doc: int = 1500) -> str:
    """Converte lista de Documents em texto formatado"""
    if not docs:
        return ""
    
    partes = []
    for i, doc in enumerate(docs, 1):
        titulo = doc.metadata.get('titulo', f'Documento {i}')
        conteudo = truncar_texto(doc.page_content, max_por_doc)
        partes.append(f"### {titulo}\n{conteudo}")
    
    return "\n\n---\n\n".join(partes)


def extrair_letra_resposta(texto: str) -> str:
    """Extrai letra de resposta de um texto"""
    # Procura padrões como "A)", "a)", "Letra A", etc
    padroes = [
        r'\b([A-E])\)',
        r'\b[Ll]etra\s+([A-E])\b',
        r'\b[Rr]esposta[:\s]+([A-E])\b',
        r'\b([A-E])\b'
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            return match.group(1).upper()
    
    return texto.strip().upper()