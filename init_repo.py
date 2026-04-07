import os
import json
import uuid
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai

from extract_embeddings import get_embedding
from chroma_client import ChromaManager

load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    raise Exception("ERRO: Preencha GEMINI_API_KEY no arquivo .env")

def process_repository():
    repo_dir = "repositorio"
    file_name = "doc_fonte.pdf"
    file_path = os.path.join(repo_dir, file_name)
    
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo {file_path} não encontrado no repositorio!")
        return

    print("1. Limpando base de dados vetorial antiga (Reset ChromaDB)...")
    if os.path.exists("chroma_db"):
        shutil.rmtree("chroma_db")
        print("Banco deletado. Criando um novo.")
        
    db = ChromaManager()
    genai_client = genai.Client()

    print("2. Lendo PDF com LangChain (PyPDFLoader)...")
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    texto_completo = " ".join([page.page_content for page in pages])
    
    print(f"3. Lidos {len(texto_completo)} caracteres. Fatiando texto com RecursiveCharacterTextSplitter...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(texto_completo)
    print(f"Foram gerados {len(chunks)} fragmentos.")
    
    print("4. Vetorizando fragmentos com Gemini Embeddings e populando ChromaDB...")
    for i, chunk in enumerate(chunks):
        vector = get_embedding(genai_client, text=chunk)
        metadata = {
            "tipo": "chunk", 
            "original_file": file_name,
            "chunk_index": i,
            "conteudo": chunk
        }
        vector_id = f"chunk_{i}_{uuid.uuid4().hex[:6]}"
        db.upsert_vector(vector_id, vector, metadata)
        print(f"  -> Vetor {i+1}/{len(chunks)} indexado.")
        
    print("5. Gerando resumo mestre de apresentação do Documento usando LLM...")
    resumo_prompt = f"Você é uma IA curadora. Faça um resumo elegante e formal de 2 parágrafos contando de forma atrativa qual é o tema do documento. \nBase do Texto:\n{texto_completo[:20000]}"
    try:
        response = genai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=resumo_prompt
        )
        resumo = response.text
    except Exception as e:
        resumo = f"Erro ao gerar resumo na Nuvem: {str(e)}"
        
    info = {
        "file_name": file_name,
        "original_name": "CG individual.pdf",
        "summary": resumo,
        "chunk_count": len(chunks)
    }
    
    with open(os.path.join(repo_dir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=4)
        
    print("\n✅ Sucesso! O Agente Exclusivo foi treinado com os blocos deste PDF local!")

if __name__ == "__main__":
    process_repository()
