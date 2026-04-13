# RAG Corporativo - Agente Especialista

Este projeto implementa um **Agente Exclusivo / ChatBot Local** usando RAG (Retrieval-Augmented Generation). O sistema processa documentos (neste momento somente PDFs) de forma local, realiza fatiamento, armazena seus vetores no `ChromaDB` (banco de dados vetorial local) e usa os poderosos modelos **Gemini** do Google para buscar informações altamente precisas no escopo corporativo.

A Interface Gráfica permite conversar de modo fácil enquanto a Inteligência Artificial responde baseando-se única e estritamente na base de conhecimento vetorial parametrizada.

## Principais Funcionalidades

- **RAG Específico Corporativo**: A Inteligência Artificial responde perguntas exclusivamente com base no documento indexado, bloqueando "delírios" e alucinações.
- **Hierarchical RAG (Parent-Child Retrieval)**: A ingestão fatiará o conteúdo em dois níveis. Pequenos recortes geram precisão de Embeddings para busca no `ChromaDB`, mas na hora do Prompt, injetamos Pedaços Maiores ("Textos Pais") para passar contexto pleno ao LLM.
- **Expansão de Consultas (Query Expansion)**: O sistema utiliza o Gemini para reescrever e otimizar a pergunta original do usuário, aumentando drasticamente a taxa de acerto na recuperação semântica.
- **Cache Semântico Vetorial**: Consultas com mais de 96% de intencionalidade semântica igual a respostas passadas pulam o acionamento custoso do Google Gemini e são retornadas imediatamente do cache!
- **Auditoria de Feedback & Métricas**: Balões trazem os amigáveis 👍/👎 ao final. O comportamento alimenta o arquivo `feedbacks.json` para calibragem.
- **Observabilidade de Consumo**: Rastreamento automático de tokens (Prompt, Candidates e Total) gravados em `usage_metrics.json` para controle de custos e performance.
- **Busca Profunda (Top 15 Retrieval)**: O motor realiza o ranking dos 15 trechos mais relevantes, garantindo que nenhum fragmento crítico de contexto seja ignorado pela IA.
- **Respostas em Tempo Real (Streaming)**: As respostas são exibidas com o "efeito máquina de escrever", idêntico ao fluxo nativo do ChatGPT, sem necessidade de esperar todo o processamento.
- **Renderização Markdown**: Suporte total a negrito, itálico e listas nas respostas da IA usando `marked.js`.
- **Persistência de Histórico**: O robô lembra das perguntas e respostas anteriores da mesma aba do navegador e o histórico é persistido localmente via `LocalStorage`.
- **Citações Dinâmicas Visuais**: Após entregar a resposta, você conta com um seletor visual na interface para atestar fidedignamente qual fragmento pai embasou a resposta original.
- **Sincronização Vetorial Incremental Inteligente**: O script `init_repo.py` analisa a "Identidade/Hash" MD5 dos arquivos.
- **Botão Inteligente de Retentativa (Resubmit)**: O frontend se adapta a quebras de internet acionando automaticamente novas tentativas. Se houver total blackout, o usuário pode repassar a pergunta num click sem copiar-colar.
- **Bypass de Resumo sob Demanda (Retry UI)**: Caso a IA sofra queda temporária na hora de gerar a Ementa Visão Geral do documento (pico 503), oferecemos na própria tela um botão "Reenviar geração do resumo" que acessa a engrenagem do ChromaDB por trás dos panos e aciona o LLM na hora.
- **Dashboard de Observabilidade (Analytics)**: Interface gerencial dedicada para visualização de gráficos de consumo de tokens, volume de interações e métricas de satisfação (👍/👎).
- **Utilitário de Diagnóstico**: Inclui o script `debug_models.py` para validar a conectividade e os modelos disponíveis na sua chave de API em segundos.

## Arquitetura e Fluxo de Dados

```mermaid
graph TD
    %% Estilos e Cores Principais
    style A fill:#4a90e2,stroke:#fff,color:#fff
    style B fill:#34a853,stroke:#fff,color:#fff
    style C fill:#ea4335,stroke:#fff,color:#fff
    style D fill:#fbbc05,stroke:#fff,color:#333

    subgraph INGESTÃO ["Processo de Ingestão (Offline)"]
        direction TB
        A["Documentos (PDFs)"] -->|PDFLoader| B["Fatiamento Hierárquico<br/>(Pai e Filho)"]
        B -->|"Geração de Vetores"| C["Google Gemini<br/>Embeddings"]
        C -->|Persistência| D[("ChromaDB<br/>(Base Vetorial Local)")]
        B -.->|Metadados| D
    end

    subgraph CONSULTA ["Interface e Busca (Online)"]
        direction TB
        U["Usuário (Frontend)"] -->|Pergunta| S["FastAPI (server.py)"]
        S -->|Consulta Cache| CH{Intencionalidade?}
        CH -->|"Hit (96% ou mais)"| U
        
        CH -->|Miss| GE["Conversão Pergunta<br/>p/ Vetor"]
        GE -->|"Pesquisa Similarity"| D
        D -->|"Recupera Trechos Pai/Filho"| S
    end

    subgraph RESPOSTA ["Geração e Entrega"]
        direction TB
        S -->|"Prompt Parametrizado"| L["Google Gemini<br/>Flash 3"]
        L -->|Streaming | U
        U -->|Feedback| F[("feedbacks.json")]
    end

    %% Conexões entre blocos
    INGESTÃO --> D
    D <--> CONSULTA
    CONSULTA --> RESPOSTA
```

## Estrutura do Projeto

* `server.py` — Código principal da API FastAPI (Backend). Responsável por receber o prompt, consultar o ChromaDB e chamar a API do Gemini.
* `init_repo.py` — Script responsável por resetar, ler PDFs, vetorizar e inserir os embeddings de conhecimento na base local ChromaDB.
* `extract_embeddings.py` (Módulo) — Funções auxiliares de integração com modelagem Embedding.
* `chroma_client.py` (Módulo) — Classes e funções CRUD intermedirárias de uso do vetor.
* `static/` — HTML, CSS e JS que compõem o frontend.
    * `dashboard.html` — Interface do painel de estatísticas.
    * `dashboard.js` — Lógica de renderização de gráficos (Chart.js).
* `.env` — Variáveis de ambiente secretas.
* `repositorio/usage_metrics.json` — Log histórico de consumo de tokens.
* `repositorio/feedbacks.json` — Registro de votos 👍/👎 dos usuários.

## Como Instalar e Rodar o Projeto

### Pré-Requisitos

No terminal ou PowerShell, verifique se você possui o Python instalado e então instale as dependências.
(Certifique-se de configurar e fornecer sua API Key do Google no arquivo `.env`)

```bash
# 1. Clone o repositório
git clone https://github.com/junior-honorato/rag_ia.git
cd rag_ia

# 2. Crie um ambiente virtual (Opcional, mas recomendado)
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Instale as Bibliotecas Necessárias
pip install fastapi uvicorn pydantic python-dotenv chromadb langchain langchain-community pypdf "google-genai>=0.1.2"
```

### Passo a Passo de Execução

1. **Gere a sua Base de Conhecimento**
   Certifique-se de ter um documento em PDF de teste dentro da pasta especificada. Então inicialize seu ChromaDB com:
   ```bash
   python init_repo.py
   ```
   *(Ele fará a varredura, fatiamento em N partes e armazenamento vetorizado permanente no db local).*

2. **Inicie o Servidor Interno de Chat**
   ```bash
   python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Acesse a Aplicação**
   No seu navegador acesse `http://localhost:8000` ou compartilhe na sua rede o IP da sua máquina.

### Execução via Docker (Opcional)

Para facilitar o deploy ou garantir um ambiente idêntico, você pode usar o Docker:

```bash
# 1. Construir a imagem
docker build -t rag-ia-sicoob .

# 2. Rodar o container
docker run -p 8000:8000 --env-file .env rag-ia-sicoob
```

### Segurança e Limits

- **Rate Limits & API Spikes**: O backend está customizado com `Max Retries` e algorítimo *Exponential Backoff*. Se os servidores do Google sobrecarregarem, o sistema tentará silenciosamente contornar a fila antes de devolver erro final.
- **Frontend Fallbacks**: Caso a quota total da sua API Account acabe e o modelo recuse serviço (429), a tela exibirá uma mensagem de erro visível, indicando pausa do serviço ao uso geral. 

## Segurança e Blindagem

Este Agente foi projetado para operar em ambientes corporativos, possuindo camadas de segurança ativas:

1. **Autenticação de Sessão (Cookies HttpOnly)**: Todas as chamadas entre o Frontend e o Backend são protegidas por cookies de sessão seguros (`HttpOnly`). Isso elimina chaves hardcoded no código JavaScript, impedindo que usuários mal-intencionados visualizem ou copiem credenciais via "Inspecionar Elemento".
2. **Proteção contra XSS (DOMPurify)**: No frontend, todas as respostas do modelo Gemini passam por uma sanitização rigorosa utilizando a biblioteca `DOMPurify`. Isso garante que eventuais scripts ou códigos maliciosos injetados nos PDFs ou gerados pela IA não sejam executados no navegador do usuário.
3. **Blindagem de Prompt (Guardrails)**: O `system_prompt` possui diretrizes estritas de "blindagem" para impedir ataques de *Prompt Injection*. A IA está instruída a ignorar tentativas de desvio de conduta (ex: "ignore all previous instructions") e a nunca revelar suas instruções internas.
4. **Isolamento de Dados**: Os arquivos de PDF originais, o banco vetorial e os logs de métricas são mantidos localmente e estão configurados no `.gitignore` para nunca serem expostos no repositório público.

---
_Criado sob rigorosa parametrização Corporativa via Gemini & FastAPI._
