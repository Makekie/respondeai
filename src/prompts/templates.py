from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from models.schemas import QuestoesOutput, RespostaOutput, DificuldadeEnum, TipoQuestaoEnum


class PromptTemplates:
    """Templates de prompts para o sistema de questões"""
    
    # ============ MAPEAMENTOS ============
    NIVEIS_DIFICULDADE = {
        DificuldadeEnum.FACIL: "básico, cobrando conceitos fundamentais e letra de lei",
        DificuldadeEnum.MEDIO: "intermediário, exigindo interpretação e correlação de conceitos",
        DificuldadeEnum.DIFICIL: "avançado, com pegadinhas, exceções e jurisprudência consolidada"
    }
    
    FORMATOS_QUESTAO = {
        TipoQuestaoEnum.MULTIPLA_ESCOLHA: """
- Enunciado claro e objetivo
- 5 alternativas (A, B, C, D, E) 
- Apenas UMA alternativa correta
- Distratores plausíveis nas alternativas incorretas""",
        
#         TipoQuestaoEnum.CERTO_ERRADO: """
# - Uma afirmação assertiva para ser julgada
# - Resposta: CERTO ou ERRADO
# - A afirmação deve ser totalmente certa ou totalmente errada""",
        
#         TipoQuestaoEnum.DISSERTATIVA: """
# - Pergunta aberta que exija desenvolvimento
# - Resposta esperada com pontos principais
# - Critérios de correção claros"""
    }


# ============ PROMPT PARA GERAR QUESTÕES ============
GERAR_QUESTOES_TEMPLATE = """Você é um especialista em elaboração de questões para concursos públicos brasileiros no estilo FCC, com profundo conhecimento jurídico.

## CONTEXTO JURÍDICO (use como base para as questões):
{contexto}

{questoes_existentes}

## TAREFA:
Elabore exatamente {quantidade} questão(ões) sobre: "{tema}"

## ESPECIFICAÇÕES:
- Nível: {nivel_dificuldade}
- Tipo: {tipo_questao}
- Formato esperado: {formato_questao}
- Estilo: FCC com 5 alternativas, linguagem formal e foco em letra de lei

## REGRAS OBRIGATÓRIAS:
1. Baseie-se PRIORITARIAMENTE no contexto jurídico fornecido
2. Cite artigos, leis, súmulas e jurisprudências quando aplicável
3. Evite questões ambíguas ou com múltiplas respostas possíveis
4. A justificativa deve ser didática, explicando o porquê de cada alternativa
5. Use linguagem formal apropriada para concursos públicos
6. Cada questão deve testar um aspecto diferente do tema
7. **IMPORTANTE**: NÃO repita ou crie questões similares às já existentes mostradas acima
8. Crie questões originais e diferentes das existentes
9. Siga rigorosamente o estilo FCC: formal, direto, baseado em lei

## FORMATO DE SAÍDA:
{format_instructions}

Gere as {quantidade} questões agora:"""


def get_gerar_questoes_prompt() -> ChatPromptTemplate:
    """Retorna o prompt template para geração de questões"""
    parser = JsonOutputParser(pydantic_object=QuestoesOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um especialista em elaboração de questões para concursos públicos brasileiros."),
        ("human", GERAR_QUESTOES_TEMPLATE)
    ])
    
    return prompt.partial(format_instructions=parser.get_format_instructions())


# ============ PROMPT PARA RESPONDER QUESTÕES ============
RESPONDER_QUESTAO_TEMPLATE = """Você é um professor especialista em preparação para concursos públicos brasileiros, conhecido por suas explicações claras e didáticas.

## CONTEXTO JURÍDICO RELEVANTE:
{contexto}

## QUESTÃO A SER RESPONDIDA:
{pergunta}

{alternativas_texto}

{contexto_adicional}

## SUA TAREFA:
1. Analise cuidadosamente a questão e todas as alternativas
2. Identifique a resposta correta com certeza
3. Explique de forma didática e completa o porquê da resposta
4. Cite a fundamentação legal (artigos, leis, súmulas, jurisprudência)
5. Explique por que as outras alternativas estão erradas
6. Forneça dicas de estudo para aprofundamento

## FORMATO DE SAÍDA:
{format_instructions}

Responda a questão:"""


def get_responder_prompt() -> ChatPromptTemplate:
    """Retorna o prompt template para responder questões"""
    parser = JsonOutputParser(pydantic_object=RespostaOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um professor especialista em concursos públicos, focado em explicações didáticas."),
        ("human", RESPONDER_QUESTAO_TEMPLATE)
    ])
    
    return prompt.partial(format_instructions=parser.get_format_instructions())


# ============ PROMPT PARA BUSCA SEMÂNTICA ============
QUERY_REWRITE_TEMPLATE = """Reescreva a seguinte consulta para melhorar a busca em uma base de conhecimento jurídico brasileiro.
Inclua termos relacionados, sinônimos jurídicos e conceitos correlatos.

Consulta original: {query}

Consulta otimizada:"""


def get_query_rewrite_prompt() -> PromptTemplate:
    """Retorna prompt para reescrita de queries"""
    return PromptTemplate.from_template(QUERY_REWRITE_TEMPLATE)