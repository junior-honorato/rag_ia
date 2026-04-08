import os
import json
import uuid
import hashlib
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai

from extract_embeddings import get_embedding
from chroma_client import ChromaManager

load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    raise Exception("ERRO: Preencha GEMINI_API_KEY no arquivo .env")

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def process_repository():
    repo_dir = "repositorio"
    state_file = os.path.join(repo_dir, "repo_state.json")
    summaries_file = os.path.join(repo_dir, "summaries.json")
    
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)
        
    pdf_files = [f for f in os.listdir(repo_dir) if f.lower().endswith('.pdf')]
    
    state = {}
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            
    summaries = {}
    if os.path.exists(summaries_file):
        with open(summaries_file, "r", encoding="utf-8") as f:
            summaries = json.load(f)
            
    db = ChromaManager()
    genai_client = genai.Client()
    
    print("1. Sincronizando Automações Iniciais...")
    
    archived_files = list(state.keys())
    for archived_file in archived_files:
        if archived_file not in pdf_files:
            print(f"   [!] Arquivo isolado detectado: {archived_file}. Purgando da base vetorial...")
            db.delete_by_file(archived_file)
            del state[archived_file]
            if archived_file in summaries:
                del summaries[archived_file]
            
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=200, length_function=len
    )

    for i, file_name in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processando '{file_name}': ", end="")
        file_path = os.path.join(repo_dir, file_name)
        current_hash = get_file_hash(file_path)
        
        if file_name in state and state[file_name] == current_hash and file_name in summaries:
            print("✔️ Sem alterações (Hash + Resumo Existente). Pulado!")
            continue
            
        print("\n   🔄 Alteração detectada. Processando e Gerando Resumo...")
        if file_name in state:
            db.delete_by_file(file_name)
            
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        texto_completo = " ".join([page.page_content for page in pages])
        
        chunks = text_splitter.split_text(texto_completo)
        print(f"   ✂️ Fatiado em {len(chunks)} trechos. Injetando...")
        
        for idx, chunk in enumerate(chunks):
            vector = get_embedding(genai_client, text=chunk)
            metadata = {
                "tipo": "chunk", 
                "original_file": file_name,
                "chunk_index": idx,
                "conteudo": chunk
            }
            vector_id = f"v_chk_{uuid.uuid4().hex[:8]}"
            db.upsert_vector(vector_id, vector, metadata)
            
        print("   🤖 Extraindo sinopse isolada...")
        resumo_prompt = f"Faça 1 parágrafo bem curto com um resumo profissional do que se trata este documento específico. Base-se nos seguintes trechos:\n{texto_completo[:4000]}"
        
        resumo = "Resumo Pendente"
        for attempt in range(3):
            try:
                response = genai_client.models.generate_content(
                    model='gemini-2.5-flash', contents=resumo_prompt
                )
                resumo = response.text
                break
            except Exception as e:
                error_str = str(e)
                if ("503" in error_str or "429" in error_str) and attempt < 2:
                    print(f"   ⏳ Servidor ocupado. Aguardando {3 * (2**attempt)}s...")
                    time.sleep(3 * (2 ** attempt))
                else:
                    print(f"   ❌ Falha na geração: {error_str}")
                    resumo = "⚠️ Resumo temporariamente indisponível. O PDF foi indexado e está pronto para RAG, mas não foi possível gerar a ementa devido a tráfego na nuvem."
                    break
                    
        summaries[file_name] = {
            "summary": resumo,
            "chunk_count": len(chunks)
        }
        state[file_name] = current_hash
        
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        with open(summaries_file, "w", encoding="utf-8") as f:
            json.dump(summaries, f, ensure_ascii=False, indent=4)

    info_legacy = os.path.join(repo_dir, "info.json")
    if os.path.exists(info_legacy):
        os.remove(info_legacy)
        
    print(f"\n✅ Banco Multimodal Local Completamente Sincronizado!")

if __name__ == "__main__":
    process_repository()
