import os
import uuid
import shutil
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

from extract_embeddings import get_embedding
from chroma_client import ChromaManager

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    raise Exception("ERRO: Preencha GEMINI_API_KEY no arquivo .env")

app = FastAPI(title="Base Multimodal RAG Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai_client = genai.Client()
db = ChromaManager()

class ChatRequest(BaseModel):
    query: str

@app.post("/api/ingest")
async def ingest_document(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    try:
        vector = None
        metadata = {}
        
        if file and file.filename:
            temp_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            try:
                # 1. Faz Upload do PDF/Imagem diretamente na Nuvem do Gemini para conversar com ele depois
                gemini_file = genai_client.files.upload(file=temp_path)
                
                # 2. Gera o Vetor Matemático localmente
                vector = get_embedding(genai_client, file_path=temp_path)
                
                # 3. Salva a referência da Nuvem do Google dentro do nosso Banco Local (Mágica!)
                metadata = {
                    "tipo": "arquivo", 
                    "nome_arquivo": file.filename,
                    "gemini_file_name": gemini_file.name
                }
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        elif text and text.strip():
            vector = get_embedding(genai_client, text=text)
            metadata = {"tipo": "texto", "conteudo": text[:100] + "..." if len(text) > 100 else text, "full_text": text}
        else:
            raise HTTPException(status_code=400, detail="Forneça um texto ou um arquivo válido.")
            
        vector_id = f"doc_{uuid.uuid4().hex[:8]}"
        db.upsert_vector(vector_id, vector, metadata)
        
        return {"status": "success", "id": vector_id, "message": "Indexado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_agent(req: ChatRequest):
    try:
        if not req.query.strip():
            return {"response": ""}
            
        # 1. Recuperar contexto do Banco de Dados Vetorial Local
        vector = get_embedding(genai_client, text=req.query)
        resultados = db.search_similar(vector, top_k=2) # Pega os 2 mais relevantes
        
        matches = resultados.get("matches", [])
        
        # 2. Construir Prompt do Agente Injetando os Documentos Recuperados
        chat_contents = []
        
        # Inserindo RAG
        context_description = ""
        for m in matches:
            meta = m.get("metadata", {})
            if meta.get("tipo") == "arquivo" and "gemini_file_name" in meta:
                # Resgata o Objeto do Arquivo original pelo SDK da Nuvem do Google!
                cloud_file = genai_client.files.get(name=meta["gemini_file_name"])
                chat_contents.append(cloud_file)
                context_description += f"\n- Arquivo Anexado: {meta['nome_arquivo']}"
            elif meta.get("tipo") == "texto" and "full_text" in meta:
                chat_contents.append(meta["full_text"])
                context_description += f"\n- Texto Anexado."
                
        # Prompt Mestre
        system_prompt = f"""
Você é o "Nexus", um assistente de inteligência artificial de elite corporativa simpático e direto.
Abaixo você recebeu um ou mais documentos resgatados criptograficamente. Podem ser textos ou Arquivos PDF/Imagens.
Use ESTRITAMENTE o conhecimento destes arquivos para responder à pergunta do usuário. 
Se você não souber a resposta baseada neles, seja honesto.
Base resgatada:{context_description}

Pergunta do Usuário: {req.query}
"""
        chat_contents.append(system_prompt)
        
        # 3. Executamos o Chatbot usando Flash (Leitura super-rápida de PDFs)
        response = genai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=chat_contents
        )
        
        return {
            "response": response.text,
            "matches": matches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
