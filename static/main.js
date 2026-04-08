// =============================
// LÓGICA DE INFO DO DOCUMENTO
// =============================

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/doc_info');
        const data = await res.json();
        
        document.getElementById('docLoader').style.display = 'none';
        document.getElementById('docContent').style.display = 'flex';
        
        document.getElementById('docTitle').textContent = `📋 ${data.file_name}`;
        document.getElementById('docChunks').textContent = data.chunk_count;
        document.getElementById('docSummary').innerHTML = data.summary.replace(/\n\n/g, "<br><br>");
        
    } catch (err) {
        document.getElementById('docLoader').innerHTML = `<span style="color:#ef4444">Falha ao buscar Repo: ${err.message}</span>`;
    }
});

// =============================
// CHAT BOT LÓGICA RAG
// =============================
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatBox = document.getElementById('chatBox');
const btnChat = document.getElementById('btnChat');

let chatHistory = [];

function appendMessage(sender, text) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    let formattedText = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    formattedText = formattedText.replace(/\*(.*?)\*/g, "<em>$1</em>");
    formattedText = formattedText.replace(/\n\n/g, "<br><br>");
    formattedText = formattedText.replace(/\n/g, "<br>");
    div.innerHTML = formattedText;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = chatInput.value.trim();
    if(!query) return;

    appendMessage('user', query);
    chatInput.value = '';
    btnChat.disabled = true;
    
    const typingId = "typing_" + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = typingId;
    typingDiv.innerHTML = '<span class="loading-spinner" style="width:12px; height:12px; border-width:2px; padding:0; border-top-color:var(--primary); vertical-align:-2px"></span> Fatiando conhecimento...';
    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query, history: chatHistory})
        });
        document.getElementById(typingId).remove();
        if(!res.ok) {
            let errorDetail = "Erro no Servidor RAG";
            try {
                const errData = await res.json();
                errorDetail = errData.detail || errorDetail;
            } catch(e) {}
            if (res.status === 429 || errorDetail === "LIMITE_DE_TOKENS") {
                throw new Error("⚠️ O limite da API foi atingido (Falta de tokens/Quota excedida). O serviço poderá ficar temporariamente lento ou interrompido. Por favor, aguarde alguns minutos e tente novamente.");
            }
            if (res.status === 503 || errorDetail.includes("503") || errorDetail.includes("UNAVAILABLE") || errorDetail.includes("high demand")) {
                throw new Error("⚠️ Ops! Nossos servidores (Google Gemini) estão sob altíssima demanda no momento. Essa indisponibilidade é temporária. Por favor, aguarde alguns segundos e tente perguntar novamente!");
            }
            throw new Error(errorDetail);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullResponse = "";
        let buffer = "";
        let matches = [];
        
        const botMsgDiv = document.createElement('div');
        botMsgDiv.className = `message bot`;
        chatBox.appendChild(botMsgDiv);
        
        const renderText = (text) => {
            let formattedText = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
            formattedText = formattedText.replace(/\*(.*?)\*/g, "<em>$1</em>");
            formattedText = formattedText.replace(/\n\n/g, "<br><br>");
            formattedText = formattedText.replace(/\n/g, "<br>");
            return formattedText;
        };

        while(true) {
            const {done, value} = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, {stream: true});
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Mantém o pedaço incompleto para o próximo loop
            
            for(const line of lines) {
                if(!line.trim()) continue;
                const parsed = JSON.parse(line);
                if(parsed.type === "chunk") {
                    fullResponse += parsed.text;
                    botMsgDiv.innerHTML = renderText(fullResponse);
                    chatBox.scrollTop = chatBox.scrollHeight;
                } else if (parsed.type === "matches") {
                    matches = parsed.matches;
                } else if (parsed.type === "error") {
                    let errStr = parsed.detail;
                    if (errStr.includes("503") || errStr.includes("UNAVAILABLE") || errStr.includes("high demand")) {
                        errStr = "⚠️ Ops! Nossos servidores (Google Gemini) estão sob altíssima demanda no momento. Essa indisponibilidade é temporária. Por favor, aguarde alguns segundos e tente perguntar novamente!";
                    }
                    throw new Error(errStr);
                }
            }
        }
        
        if(!fullResponse) {
            fullResponse = "Vazio.";
        }
        
        let finalHtml = renderText(fullResponse);
        if (matches && matches.length > 0) {
            let sourcesHtml = `<div class="sources-list">`;
            for(let m of matches) {
                const meta = m.metadata || {};
                const titulo = meta.original_file || "Documento";
                const score = (m.score * 100).toFixed(1) + "%";
                const texto = meta.conteudo || "Sem texto armazenado";
                sourcesHtml += `
                    <div class="source-card">
                        <div class="source-card-title"><span>📄 ${titulo}</span><span class="source-score">Ref: ${score}</span></div>
                        <em>"${texto}"</em>
                    </div>
                `;
            }
            sourcesHtml += `</div>`;
            finalHtml += `
                <div class="sources-container">
                    <details>
                        <summary>🔍 Ver Fontes Analisadas (${matches.length})</summary>
                        ${sourcesHtml}
                    </details>
                </div>
            `;
        }
        botMsgDiv.innerHTML = finalHtml;
        chatBox.scrollTop = chatBox.scrollHeight;
        
        // Atualiza a memória de conversação
        chatHistory.push({role: 'user', content: query});
        chatHistory.push({role: 'model', content: fullResponse});
        
        // Limita a memória aos últimos 10 turnos para evitar payloads pesados
        if(chatHistory.length > 10) {
            chatHistory = chatHistory.slice(chatHistory.length - 10);
        }
        
    } catch (err) {
        const typEl = document.getElementById(typingId);
        if(typEl) typEl.remove();
        appendMessage('bot', `<span style="color:#ef4444">Desculpe, ocorreu erro crítico: ${err.message}</span>`);
    } finally {
        btnChat.disabled = false;
        chatInput.focus();
    }
});
