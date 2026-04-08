import os
import json
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
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

from typing import List, Dict, Any

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []

class SummaryUpdateBlock(BaseModel):
    summary: str

@app.get("/api/documents")
def get_documents_list():
    summaries_path = os.path.join("repositorio", "summaries.json")
    if os.path.exists(summaries_path):
        with open(summaries_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.put("/api/documents/{filename}/summary")
def update_document_summary(filename: str, payload: SummaryUpdateBlock):
    summaries_path = os.path.join("repositorio", "summaries.json")
    if os.path.exists(summaries_path):
        with open(summaries_path, "r", encoding="utf-8") as f:
            sums = json.load(f)
        
        if filename in sums:
            sums[filename]["summary"] = payload.summary
        else:
            sums[filename] = {"summary": payload.summary, "chunk_count": 0}
            
        with open(summaries_path, "w", encoding="utf-8") as f:
            json.dump(sums, f, ensure_ascii=False, indent=4)
        return {"status": "success", "message": "Resumo atualizado."}
    return {"status": "error", "message": "Banco não encontrado"}, 404

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
Você foi parametrizada para atuar EXCLUSIVAMENTE baseada no ecossistema de documentos corporativos indexados.
Seu objetivo é responder à pergunta do Usuário consultando ESTRITAMENTE os trechos fatiados das fontes documentais abaixo (que podem pertencer a um ou múltiplos arquivos).
Não invente dados nem traga conhecimento de treinamento pre-existente ao responder.
Se os trechos recuperados não abordarem a pergunta, seja transparente e responda que isso foge do escopo dos arquivos da Base de Conhecimento atual.

TRECHOS RECUPERADOS (FONTES):
{context_description}
"""
            from google.genai import types
            
            # Reconstrói o histórico tratando a rigidez obrigatória do Gemini (alternância user/model e início com user)
            last_role = None
            for msg in req.history:
                current_role = "user" if msg.get("role") == "user" else "model"
                
                # A primeira mensagem na history tem que ser sempre do Usuário
                if not chat_contents and current_role == "model":
                    continue
                    
                # Regra estrita: Histórico deve alternar obrigatoriamente
                if current_role == last_role:
                    # Concatena com a mensagem anterior da mesma role para evitar Crash 400 sem perder contexto
                    if chat_contents:
                        chat_contents[-1]["parts"][0]["text"] += "\n" + msg.get("content", "")
                    continue
                
                chat_contents.append({"role": current_role, "parts": [{"text": msg.get("content", "")}]})
                last_role = current_role
                
            # A pergunta atual que será inserida abaixo sempre tem a role "user"
            # Se a última mensagem validada do histórico também for "user" (ex: falha de rede/modelo), juntamos ambas.
            if chat_contents and chat_contents[-1]["role"] == "user":
                prev_user_msg = chat_contents.pop()
                req.query = prev_user_msg["parts"][0]["text"] + "\n\n" + req.query
            
            # Adiciona a pergunta atual
            chat_contents.append({"role": "user", "parts": [{"text": req.query}]})
            
            # Configura as instruções do sistema
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
            )
            
            response_stream = genai_client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=chat_contents,
                config=config
            )
            
            def stream_generator():
                try:
                    # Envia os metadados e citações primeiro
                    yield json.dumps({"type": "matches", "matches": matches}) + "\n"
                    # Itera enviando palavra por palavra
                    for chunk in response_stream:
                        yield json.dumps({"type": "chunk", "text": chunk.text}) + "\n"
                except Exception as stream_error:
                    error_str = str(stream_error)
                    yield json.dumps({"type": "error", "detail": error_str}) + "\n"

            return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

        except Exception as e:
            error_str = str(e)
            # Retentar se for erro 503 (Unavailable) ou 429 (Too Many Requests) - Isso pega os erros de inicialização.
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