import os
import json
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from google import genai

from extract_embeddings import get_embedding
from chroma_client import ChromaManager

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    raise Exception("ERRO: Preencha GEMINI_API_KEY no arquivo .env")

app = FastAPI(title="Agente Especialista Restrito")

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

@app.get("/api/doc_info")
def get_doc_info():
    info_path = os.path.join("repositorio", "info.json")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "file_name": "Base de Dados Desconectada",
        "original_name": "Arquivo Ausente",
        "summary": "Nenhum arquivo pré-processado encontrado no repositório. O administrador precisará rodar o py init_repo.py no servidor.",
        "chunk_count": 0
    }

@app.post("/api/chat")
async def chat_agent(req: ChatRequest):
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            if not req.query.strip():
                return {"response": ""}
                
            # Pesquisa os 7 chunks (fatias do LangChain) mais relevantes
            vector = get_embedding(genai_client, text=req.query)
            resultados = db.search_similar(vector, top_k=7)
            
            matches = resultados.get("matches", [])
            
            chat_contents = []
            context_description = ""
            
            for m in matches:
                meta = m.get("metadata", {})
                if meta.get("tipo") == "chunk" and "conteudo" in meta:
                    context_description += f"\n\n[Trecho do Documento {meta.get('original_file')}]:\n{meta['conteudo']}"
                    
            system_prompt = f"""
Você é a "Seguradora", uma assistente corporativa de elite do Sicoob.
Você foi treinado em SOMENTE 1 documento (A nossa Base de Verdade Exclusiva).
Seu objetivo é responder à pergunta do Usuário consultando ESTRITAMENTE os trechos fatiados desse PDF abaixo.
Não traga nenhum conhecimento do seu treinamento se não estiver no documento!
Se os trechos não abordarem o tema, responda que essa informação foge do escopo do documento estudado.

TRECHOS RECUPERADOS:
{context_description}

Pergunta do Usuário: {req.query}
"""
            chat_contents.append(system_prompt)
            
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=chat_contents
            )
            
            return {
                "response": response.text,
                "matches": matches
            }
        except Exception as e:
            error_str = str(e)
            # Retentar se for erro 503 (Unavailable) ou 429 (Too Many Requests)
            if attempt < max_retries - 1 and ("503" in error_str or "429" in error_str):
                await asyncio.sleep(base_delay * (2 ** attempt)) # Espera 2s, depois 4s... e tenta de novo
                continue
            
            if "429" in error_str:
                raise HTTPException(status_code=429, detail="LIMITE_DE_TOKENS")
                
            raise HTTPException(status_code=500, detail=error_str)

os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)