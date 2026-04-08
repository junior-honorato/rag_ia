import os
import json
import uuid
import hashlib
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
    info_file = os.path.join(repo_dir, "info.json")
    
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)
        
    pdf_files = [f for f in os.listdir(repo_dir) if f.lower().endswith('.pdf')]
    
    # Carrega estado anterior
    state = {}
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            
    db = ChromaManager()
    genai_client = genai.Client()
    
    print("1. Sincronizando Repositório com Banco Vetorial...")
    
    # 2. Poda Inteligente (arquivos que não existem mais fisicamente)
    archived_files = list(state.keys())
    for archived_file in archived_files:
        if archived_file not in pdf_files:
            print(f"   [!] Arquivo isolado detectado: {archived_file}. Purgando da base vetorial...")
            db.delete_by_file(archived_file)
            del state[archived_file]
            
    total_chunks = 0
    synced_files_count = 0
    textos_para_resumir = ""
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=200, length_function=len
    )

    # 3. Processamento Iterativo
    for i, file_name in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processando '{file_name}': ", end="")
        file_path = os.path.join(repo_dir, file_name)
        current_hash = get_file_hash(file_path)
        
        if file_name in state and state[file_name] == current_hash:
            print("✔️ Sem alterações (Hash MD5 idêntico). Pulado!")
            synced_files_count += 1
            continue
            
        print("\n   🔄 Alteração/Novo arquivo detectado. Lendo PDF...")
        # Apaga qualquer versão velha se houver
        if file_name in state:
            db.delete_by_file(file_name)
            
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        texto_completo = " ".join([page.page_content for page in pages])
        textos_para_resumir += f"\nConteúdo Extraído:\n" + texto_completo[:4000]
        
        chunks = text_splitter.split_text(texto_completo)
        print(f"   ✂️ Fatiado em {len(chunks)} trechos semânticos. Injetando no ChromaDB...")
        
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
            
        total_chunks += len(chunks)
        state[file_name] = current_hash
        synced_files_count += 1

    # Atualiza o arquivo de estado Local das Hashes
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
        
    print(f"\n4. Processamento Concluído! ({total_chunks} fragmentos novos inseridos/modificados)")
    
    # 5. Reescrever Summary se ouve alguma modificação na Base.
    if total_chunks > 0:
        print("   🤖 Gerando sumário do novo Conhecimento com Gemini...")
        resumo_prompt = f"Você é uma inteligência catalogadora corporativa. Avalie estes fragmentos isolados recém injetados e, em 2 parágrafos, elabore um resumo do que trata os documentos (em tom profissional). Textos:\n{textos_para_resumir}"
        try:
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash', contents=resumo_prompt
            )
            resumo = response.text
        except Exception as e:
            resumo = f"Resumo offline devido acionamento: {str(e)}"
            
        info = {
            "file_name": f"Base Compartilhada Sicoob",
            "original_name": f"Total de Arquivos: {synced_files_count}",
            "summary": resumo,
            "chunk_count": "Indexação Multipla Distribuída"
        }
        
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    process_repository()
