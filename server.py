import os
import json
import time
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

class FeedbackRequest(BaseModel):
    query: str
    response: str
    vote: int

def expand_query(client: genai.Client, query: str) -> str:
    """Usa o Gemini para reescrever a query focando em busca corporativa (Query Expansion)."""
    prompt = f"Reescreva a seguinte pergunta de um usuário para que ela seja mais eficaz em uma busca semântica em documentos corporativos técnicos. Mantenha o idioma original. Retorne APENAS o texto da nova pergunta.\\n\\nPergunta: {query}"
    try:
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL_NAME"),
            contents=prompt
        )
        expanded = response.text.strip()
        return expanded if expanded else query
    except:
        return query

def log_usage(usage):
    """Grava métricas de consumo de tokens em arquivo local."""
    if not usage: return
    log_path = os.path.join("repositorio", "usage_metrics.json")
    logs = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            try: logs = json.load(f)
            except: pass
    logs.append({
        "timestamp": time.time(),
        "prompt_tokens": usage.prompt_token_count,
        "candidates_tokens": usage.candidates_token_count,
        "total_tokens": usage.total_token_count
    })
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs[-100:], f, indent=4)

@app.post("/api/feedback")
def submit_feedback(payload: FeedbackRequest):
    feedbacks_path = os.path.join("repositorio", "feedbacks.json")
    feedbacks = []
    if os.path.exists(feedbacks_path):
        with open(feedbacks_path, "r", encoding="utf-8") as f:
            feedbacks = json.load(f)
            
    feedbacks.append({
        "timestamp": time.time(),
        "query": payload.query,
        "response": payload.response,
        "vote": payload.vote
    })
            
    with open(feedbacks_path, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=4)
        
    return {"status": "success"}

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

@app.post("/api/documents/{filename}/retry_summary")
def retry_document_summary(filename: str):
    # 1. Recuperar chunks de Contexto via ChromaDB
    texto_contexto = db.get_parent_content_by_file(filename, max_chars=5000)
    if not texto_contexto:
        raise HTTPException(status_code=404, detail="Conteúdo do arquivo não encontrado no banco vetorial.")
        
    # 2. Enviar para LLM
    resumo_prompt = f"Faça 1 parágrafo bem curto com um resumo profissional do que se trata este documento específico. Base-se nos seguintes trechos:\\n{texto_contexto}"
    
    try:
        response = genai_client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL_NAME"), contents=resumo_prompt
        )
        resumo = response.text
    except Exception as e:
        error_str = str(e)
        if "503" in error_str or "UNAVAILABLE" in error_str or "high demand" in error_str:
            raise HTTPException(status_code=503, detail="Os servidores do Google Gemini estão com tráfego extremo no momento. Aguarde alguns instantes e clique novamente.")
        elif "429" in error_str:
            raise HTTPException(status_code=429, detail="A cota (Limites/Tokens) temporária da conta do Google Gemini foi excedida. Pise no freio e tente em breve.")
        else:
            raise HTTPException(status_code=500, detail="Falha inesperada de comunicação com a Nuvem. Tente mais tarde.")
        
    # 3. Atualizar o Summaries
    summaries_path = os.path.join("repositorio", "summaries.json")
    if os.path.exists(summaries_path):
        with open(summaries_path, "r", encoding="utf-8") as f:
            sums = json.load(f)
            
        if filename in sums:
            sums[filename]["summary"] = resumo
        else:
            sums[filename] = {"summary": resumo, "chunk_count": 0}
            
        with open(summaries_path, "w", encoding="utf-8") as f:
            json.dump(sums, f, ensure_ascii=False, indent=4)
            
    return {"status": "success", "summary": resumo}

@app.post("/api/chat")
async def chat_agent(req: ChatRequest):
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            if not req.query.strip():
                return {"response": ""}

            # --- ITEM 1: QUERY EXPANSION ---
            search_query = expand_query(genai_client, req.query)
            print(f"[RAG Evolution] Original: {req.query} | Expanded: {search_query}")
                
            # Pesquisa os chunks com a query expandida
            vector = get_embedding(genai_client, text=search_query)
            
            # --- START SEMANTIC CACHE ---
            cached_answer = db.check_cache(vector, threshold=0.04) # 96% similarity
            if cached_answer:
                # Retorna a resposta engavetada instantaneamente
                def cache_stream_generator():
                    # matches pode conter flag de hit no cache
                    yield json.dumps({"type": "matches", "matches": [{"metadata": {"original_file": "Semantic Cache Hit", "conteudo": "Resposta recuperada direto da memória do cache semântico economizando tokens."}, "score": 1.0}]}) + "\n"
                    # Fatiar para simular a digitação rápida
                    chunk_size = 40
                    for i in range(0, len(cached_answer), chunk_size):
                        yield json.dumps({"type": "chunk", "text": cached_answer[i:i+chunk_size]}) + "\n"
                        time.sleep(0.015) 
                return StreamingResponse(cache_stream_generator(), media_type="application/x-ndjson")
            # --- END SEMANTIC CACHE ---
            
            # --- ITEM 1: ENHANCED RETRIEVAL (TOP 15) ---
            resultados = db.search_similar(vector, top_k=15)
            
            matches = resultados.get("matches", [])
            
            chat_contents = []
            context_description = ""
            
            seen_parents = set()
            for m in matches:
                meta = m.get("metadata", {})
                
                # Suporte à nova Arquitetura Pai-Filho (Hydrated RAG)
                if meta.get("tipo") == "child_chunk" and meta.get("parent_id") not in seen_parents:
                    seen_parents.add(meta.get("parent_id"))
                    parent_text = meta.get('parent_content', 'Conteúdo Vazio')
                    context_description += f"\n\n[Trecho Completo do Documento {meta.get('original_file')}]:\n{parent_text}"
                
                # Fallback de compatibilidade (para banco legado)
                elif meta.get("tipo") == "chunk" and "conteudo" in meta:
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
                model=os.environ.get("GEMINI_MODEL_NAME"),
                contents=chat_contents,
                config=config
            )
            
            def stream_generator(query_vector, query_text):
                assembled_text = ""
                try:
                    # Envia os metadados e citações primeiro
                    yield json.dumps({"type": "matches", "matches": matches}) + "\n"
                    # Itera enviando palavra por palavra
                    for chunk in response_stream:
                        assembled_text += chunk.text
                        yield json.dumps({"type": "chunk", "text": chunk.text}) + "\n"
                        # Se o chunk trouxer metadados de uso (geralmente no último), loga
                        if chunk.usage_metadata:
                            log_usage(chunk.usage_metadata)
                        
                    # Finalizou com sucesso, grava a resposta no Semantic Cache para a próxima!
                    db.save_to_cache(query_vector, assembled_text, query_text)
                    
                except Exception as stream_error:
                    error_str = str(stream_error)
                    yield json.dumps({"type": "error", "detail": error_str}) + "\n"

            return StreamingResponse(stream_generator(vector, req.query), media_type="application/x-ndjson")

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
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)