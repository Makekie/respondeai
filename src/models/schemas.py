from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


# ============ ENUMS ============
class DificuldadeEnum(str, Enum):
    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"


class TipoQuestaoEnum(str, Enum):
    MULTIPLA_ESCOLHA = "multipla_escolha"
    CERTO_ERRADO = "certo_errado"
    DISSERTATIVA = "dissertativa"


# ============ SCHEMAS PARA OUTPUT PARSER ============
class Alternativa(BaseModel):
    """Schema para alternativa de questão"""
    letra: str = Field(description="Letra da alternativa (A, B, C, D, E)")
    texto: str = Field(description="Texto da alternativa")
    correta: bool = Field(default=False, description="Se é a alternativa correta")


class QuestaoGerada(BaseModel):
    """Schema para questão gerada pelo LLM"""
    numero: int = Field(description="Número da questão")
    enunciado: str = Field(description="Texto do enunciado da questão")
    alternativas: Optional[List[Alternativa]] = Field(
        default=None, 
        description="Lista de alternativas (para múltipla escolha)"
    )
    resposta_correta: str = Field(description="Letra ou CERTO/ERRADO da resposta correta")
    justificativa: str = Field(description="Explicação detalhada da resposta")
    fonte_legal: Optional[str] = Field(
        default=None, 
        description="Artigo, lei ou jurisprudência de referência"
    )


class QuestoesOutput(BaseModel):
    """Schema de saída para geração de questões"""
    questoes: List[QuestaoGerada] = Field(description="Lista de questões geradas")


class RespostaOutput(BaseModel):
    """Schema de saída para resposta de questão"""
    resposta_correta: str = Field(description="Letra ou CERTO/ERRADO da resposta")
    explicacao_detalhada: str = Field(description="Explicação completa e didática")
    fundamento_legal: str = Field(description="Base legal da resposta")
    dicas_estudo: List[str] = Field(description="Dicas para aprofundar o estudo")
    referencias: List[str] = Field(default=[], description="Referências utilizadas")


# ============ REQUESTS ============
class CriarPerguntasRequest(BaseModel):
    tema: str = Field(..., description="Tema jurídico para gerar questões", min_length=3)
    quantidade: int = Field(default=5, ge=1, le=20, description="Quantidade de questões")
    dificuldade: DificuldadeEnum = Field(default=DificuldadeEnum.MEDIO)
    tipo: TipoQuestaoEnum = Field(default=TipoQuestaoEnum.MULTIPLA_ESCOLHA)
    
    class Config:
        json_schema_extra = {
            "example": {
                "tema": "Direito Constitucional - Direitos Fundamentais",
                "quantidade": 5,
                "dificuldade": "medio",
                "tipo": "multipla_escolha"
            }
        }


class ResponderPerguntaRequest(BaseModel):
    pergunta: str = Field(..., description="Pergunta a ser respondida", min_length=10)
    alternativas: Optional[List[str]] = Field(default=None, description="Alternativas se houver")
    contexto_adicional: Optional[str] = Field(default=None, description="Contexto extra")
    
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
                ]
            }
        }


# ============ RESPONSES ============
class CriarPerguntasResponse(BaseModel):
    sucesso: bool
    tema: str
    quantidade_gerada: int
    questoes: List[QuestaoGerada]
    fontes_consultadas: Optional[List[str]] = None


class ResponderPerguntaResponse(BaseModel):
    sucesso: bool
    pergunta: str
    resposta_correta: str
    explicacao_detalhada: str
    fundamento_legal: str
    dicas_estudo: Optional[List[str]] = None
    referencias: Optional[List[str]] = None


# ============ DOCUMENTOS ============
class DocumentoRequest(BaseModel):
    titulo: str = Field(..., description="Título do documento")
    conteudo: str = Field(..., description="Conteúdo do documento")
    tipo: str = Field(..., description="Tipo: lei, jurisprudencia, doutrina, sumula")
    fonte: Optional[str] = Field(default=None, description="Fonte do documento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "titulo": "Constituição Federal - Art. 5º",
                "conteudo": "Art. 5º Todos são iguais perante a lei, sem distinção de qualquer natureza...",
                "tipo": "lei",
                "fonte": "CF/88"
            }
        }


class DocumentoResponse(BaseModel):
    sucesso: bool
    documento_id: str
    mensagem: str