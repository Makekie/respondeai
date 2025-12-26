# src/debug_test.py
"""
Script para testar se todos os componentes estão funcionando.
Execute com: python src/debug_test.py
"""
import asyncio
import sys
from pathlib import Path

# Adiciona src ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

sys.path.insert(0, str(ROOT_DIR))


async def main():
    print("=" * 60)
    print("🔍 TESTE DE COMPONENTES")
    print("=" * 60)
    print(f"📂 Raiz do projeto: {ROOT_DIR}")
    print(f"📂 Diretório src: {SRC_DIR}")
    
    # 1. Teste de imports
    from core.config import settings  
    print("\n1️⃣ Testando imports...")
    try:
        print(f"   ✅ Config carregada")
        print(f"      - Modelo LLM: {settings.OLLAMA_MODEL}")
        print(f"      - Modelo Embedding: {settings.OLLAMA_EMBEDDING_MODEL}")
        print(f"      - OpenSearch: {settings.OPENSEARCH_HOST}:{settings.OPENSEARCH_PORT}")
    except Exception as e:
        print(f"   ❌ Erro no config: {e}")
        return
    
    # 2. Teste LangChain Ollama
    print("\n2️⃣ Testando imports do LangChain...")
    try:
        from langchain_ollama import ChatOllama, OllamaEmbeddings
        print("   ✅ langchain-ollama importado com sucesso!")
    except ImportError:
        print("   ⚠️ langchain-ollama não encontrado, tentando langchain-community...")
        try:
            from langchain_community.chat_models import ChatOllama
            from langchain_community.embeddings import OllamaEmbeddings
            print("   ✅ Usando langchain-community como fallback")
        except ImportError as e:
            print(f"   ❌ Erro: {e}")
            print("   💡 Execute: uv pip install langchain-ollama langchain-community")
            return
    
    # 3. Teste conexão Ollama
    print("\n3️⃣ Testando conexão com Ollama...")
    try:
        from services.llm_service import verificar_ollama
        status = await verificar_ollama()
        
        if status["disponivel"]:
            print(f"   ✅ Ollama conectado!")
            print(f"      - Modelos disponíveis: {status['modelos']}")
            
            if status.get('modelo_llm', {}).get('disponivel'):
                print(f"      - ✅ {settings.OLLAMA_MODEL} está disponível")
            else:
                print(f"      - ⚠️ {settings.OLLAMA_MODEL} NÃO encontrado!")
                print(f"        💡 Execute: ollama pull {settings.OLLAMA_MODEL}")
            
            if status.get('modelo_embedding', {}).get('disponivel'):
                print(f"      - ✅ {settings.OLLAMA_EMBEDDING_MODEL} está disponível")
            else:
                print(f"      - ⚠️ {settings.OLLAMA_EMBEDDING_MODEL} NÃO encontrado!")
                print(f"        💡 Execute: ollama pull {settings.OLLAMA_EMBEDDING_MODEL}")
        else:
            print("   ❌ Ollama não está rodando!")
            print("   💡 Execute: ollama serve")
            return
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    # 4. Teste LLM
    print("\n4️⃣ Testando geração de texto (LLM)...")
    try:
        from services.llm_service import get_llm
        llm = get_llm(temperature=0)
        response = await llm.ainvoke("Diga apenas: TESTE OK")
        print(f"   ✅ LLM respondeu: {response.content[:100]}")
    except Exception as e:
        print(f"   ❌ Erro no LLM: {e}")
    
    # 5. Teste Embeddings
    print("\n5️⃣ Testando embeddings...")
    try:
        from services.llm_service import get_embeddings
        embeddings = get_embeddings()
        vector = embeddings.embed_query("Teste de embedding")
        print(f"   ✅ Embedding gerado!")
        print(f"      - Dimensão: {len(vector)}")
        print(f"      - Primeiros valores: {vector[:5]}")
    except Exception as e:
        print(f"   ❌ Erro nos embeddings: {e}")
    
    # 6. Teste OpenSearch
    print("\n6️⃣ Testando conexão com OpenSearch...")
    try:
        from services.vectorstore_service import VectorStoreService
        vs = VectorStoreService()
        
        if await vs.verificar_conexao():
            print("   ✅ OpenSearch conectado!")
            await vs.criar_indice()
            total = await vs.contar_documentos()
            print(f"      - Índice: {settings.OPENSEARCH_INDEX}")
            print(f"      - Documentos: {total}")
        else:
            print("   ❌ OpenSearch não está acessível!")
            print("   💡 Execute: docker run -d -p 9200:9200 -e 'discovery.type=single-node' -e 'DISABLE_SECURITY_PLUGIN=true' opensearchproject/opensearch:2.11.0")
    except Exception as e:
        print(f"   ❌ Erro no OpenSearch: {e}")
    
    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())