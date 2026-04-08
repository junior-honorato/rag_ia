// =============================
// LÓGICA DE INFO DO DOCUMENTO
// =============================

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/documents');
        const data = await res.json();
        
        document.getElementById('docLoader').style.display = 'none';
        const docContent = document.getElementById('docContent');
        docContent.style.display = 'flex';
        docContent.style.flexDirection = 'column';
        docContent.innerHTML = '';
        
        const files = Object.keys(data);
        if(files.length === 0) {
            docContent.innerHTML = '<p style="color:var(--text-muted)">Nenhum PDF encontrado na base de dados.</p>';
            return;
        }

        for(const file of files) {
            const info = data[file];
            const div = document.createElement('div');
            div.style.marginBottom = '1.5rem';
            div.innerHTML = `
                <div class="file-badge" style="font-size:0.95rem; padding:0.5rem 1rem; margin-bottom:0.5rem;">📋 ${file}</div>
                <div class="info-metric">Fatiado em: <strong style="color:var(--primary-glow)">${info.chunk_count}</strong> fragmentos matemáticos</div>
                <h3 style="font-size: 1.05rem; margin: 1rem 0 0.5rem 0; color:var(--text-main); display:flex; justify-content:space-between; align-items:center;">
                    Visão Geral
                    <button onclick="editSummary('${file}')" style="background:none; border:none; color:var(--primary); cursor:pointer; font-size:0.85rem; padding:0.2rem;">[✎ Editar]</button>
                </h3>
                <p id="summary-${file}" style="font-size: 0.9rem; line-height: 1.5; color: var(--text-muted); text-align: justify;">
                    ${info.summary.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>")}
                </p>
                <hr style="border:none; border-top:1px dashed rgba(255,255,255,0.1); margin-top: 1.5rem;">
            `;
            docContent.appendChild(div);
        }
    } catch (err) {
        document.getElementById('docLoader').innerHTML = `<span style="color:#ef4444">Falha ao buscar Banco Vetorial: ${err.message}</span>`;
    }
});

window.editSummary = async function(filename) {
    const currentEl = document.getElementById(`summary-${filename}`);
    const defaultText = currentEl.innerText || currentEl.textContent;
    const newSummary = prompt(`[CRUD] Editar o resumo mestre do documento '${filename}':`, defaultText);
    
    if (newSummary !== null && newSummary.trim() !== "") {
        currentEl.innerHTML = '<span style="color:var(--primary-glow)">Gravando no servidor...</span>';
        try {
            const res = await fetch(`/api/documents/${filename}/summary`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ summary: newSummary.trim() })
            });
            if (!res.ok) throw new Error("Falha HTTP");
            currentEl.innerHTML = newSummary.trim().replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");
        } catch(e) {
            alert('Falha ao gravar no backend.');
            currentEl.innerHTML = defaultText.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");
        }
    }
}

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
