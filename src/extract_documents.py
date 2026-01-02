#!/usr/bin/env python3
"""
Script CLI para extrair e indexar documentos PDF
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.append(str(Path(__file__).parent))

from services.document_extraction_service import document_extraction_service


async def main():
    parser = argparse.ArgumentParser(description="Extrai artigos de PDFs e indexa no vector store")
    parser.add_argument("pasta", help="Caminho para a pasta com PDFs")
    parser.add_argument("--no-json", action="store_true", help="Não salvar arquivo JSON")
    parser.add_argument("--incluir-vetados", action="store_true", help="Incluir artigos vetados")
    
    args = parser.parse_args()
    
    # Verifica se a pasta existe
    if not Path(args.pasta).exists():
        print(f"❌ Pasta não encontrada: {args.pasta}")
        sys.exit(1)
    
    print(f"🔍 Processando PDFs da pasta: {args.pasta}")
    print(f"📄 Salvar JSON: {not args.no_json}")
    print(f"⚖️ Apenas em vigor: {not args.incluir_vetados}")
    print("-" * 50)
    
    sucesso = await document_extraction_service.processar_e_indexar(
        caminho_pasta=args.pasta,
        salvar_json=not args.no_json,
        apenas_em_vigor=not args.incluir_vetados
    )
    
    if sucesso:
        print("🎉 Processamento concluído com sucesso!")
        sys.exit(0)
    else:
        print("❌ Falha no processamento")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())