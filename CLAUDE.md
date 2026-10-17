# CLAUDE.md — rag_ia

RAG corporativo: API FastAPI + frontend estático (chat e dashboard) que responde com Google Gemini sobre PDFs indexados no ChromaDB local.

## Stack

- Python 3.10 (Dockerfile `python:3.10-slim`), FastAPI, uvicorn, ChromaDB, google-genai, LangChain, pypdf, slowapi.
- `server.py`: API (`/api/chat`, `/api/documents`, `/api/feedback`, `/api/stats`) e serve `static/`.
- `init_repo.py`: ingestão incremental (hash MD5) dos PDFs em `repositorio/`. `governance.py`: mascaramento de PII. `chroma_client.py`, `extract_embeddings.py`.

## Como rodar localmente (macOS)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python init_repo.py     # indexa os PDFs de repositorio/
python server.py        # uvicorn em http://localhost:8000 (reload=True)
```

## Variáveis de ambiente (`.env`)

`GEMINI_API_KEY` (obrigatória), `GEMINI_MODEL_NAME`, `GEMINI_EMBEDDING_MODEL_NAME` (sem padrão no código), `APP_INTERNAL_API_KEY`, `ALLOWED_ORIGINS`, `GOVERNANCE_MAX_LEVEL`, `ECONOMY_MODE`, `RERANK_THRESHOLD`

## Armadilhas

- Não há `.env.example`; os nomes acima vêm do código.
- ChromaDB local em `./chroma_db` (caminho fixo, ignorado pelo git); rodar sempre a partir da raiz.
- `repositorio/*.json` (feedbacks, métricas, resumos) e `*.pdf` são ignorados pelo git.
- O README cita `debug_models.py`, que não existe no repo.
- O `chroma_db/` deste projeto é compartilhado com `rag_ia_teams` via `CHROMA_DB_PATH`.

## Fluxo de trabalho

- Autonomia para commitar e dar push na main (projeto pessoal).
- Responder sempre em português do Brasil.
