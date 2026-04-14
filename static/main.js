// =============================
// LÓGICA DE INFO DO DOCUMENTO
// =============================
// A autenticação agora é feita via Cookies HttpOnly (session_sicoob_id) injetados pelo backend.

window.sendFeedback = async function(btnEl, q, r, v) {
    const parent = btnEl.parentElement;
    parent.innerHTML = `<span style="font-size: 0.8rem; color: var(--primary-glow)">✓ Obrigado pelo feedback! Registrado.</span>`;
    try {
        await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({query: q, response: r, vote: v})
        });
    } catch(e) {
        console.error("Erro ao salvar feedback", e);
    }
}

window.copyToClipboard = async function(btnEl, text) {
    try {
        await navigator.clipboard.writeText(text);
        
        // Feedback Visual (Tooltip)
        const tooltip = document.createElement('span');
        tooltip.className = 'copy-tooltip';
        tooltip.innerText = 'Copiado!';
        btnEl.appendChild(tooltip);
        
        // Trigger animação
        setTimeout(() => tooltip.classList.add('show'), 10);
        
        // Remove após 2 segundos
        setTimeout(() => {
            tooltip.classList.remove('show');
            setTimeout(() => tooltip.remove(), 300);
        }, 2000);
        
    } catch (err) {
        console.error('Falha ao copiar texto: ', err);
    }
}

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
            let sumRaw = info.summary || "";
            let retryBtn = "";
            if (sumRaw.includes("Resumo temporariamente indisponível")) {
                retryBtn = `<button onclick="retryPdfSummary('${file}')" style="background:none; border:none; color:var(--primary-glow); cursor:pointer; font-size:0.85rem; padding:0.2rem; margin-right: 0.5rem;">[🔄 Reenviar geração do resumo]</button>`;
            }
            
            div.innerHTML = `
                <div class="file-badge" style="font-size:0.95rem; padding:0.5rem 1rem; margin-bottom:0.5rem;">📋 ${file}</div>

                <h3 style="font-size: 1.05rem; margin: 1rem 0 0.5rem 0; color:var(--text-main); display:flex; justify-content:space-between; align-items:center;">
                    Visão Geral
                    <div>
                        ${retryBtn}

                    </div>
                </h3>
                <p id="summary-${file}" style="font-size: 0.9rem; line-height: 1.5; color: var(--text-muted); text-align: justify;">
                    ${sumRaw.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>")}
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
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ summary: newSummary.trim() })
            });
            if (!res.ok) throw new Error("Falha HTTP");
            currentEl.innerHTML = newSummary.trim().replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");
        } catch(e) {
            alert('Falha ao gravar no backend.');
        }
    }
}

window.retryPdfSummary = async function(filename) {
    const currentEl = document.getElementById(`summary-${filename}`);
    currentEl.innerHTML = '<span style="color:var(--primary-glow)">⚙️ Acionando Inteligência Artificial na Nuvem...</span>';
    
    try {
        const res = await fetch(`/api/documents/${filename}/retry_summary`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.detail || "Falha HTTP");
        }
        
        // Sucesso, regarrega a UI limpando os botões antigos recarregando os JSONs gerais
        location.reload(); 
        
    } catch(e) {
        currentEl.innerHTML = `<span style="color:#ef4444">⚠️ ${e.message}</span> <button onclick="retryPdfSummary('${filename}')" style="background:none; border:none; color:var(--primary-glow); cursor:pointer; font-size:0.85rem; padding:0.2rem; margin-left: 0.5rem;">[🔄 Tentar novamente]</button>`;
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

// PERSISTÊNCIA LOCAL
function saveHistoryToLocal() {
    localStorage.setItem('sicoob_chat_history', JSON.stringify(chatHistory));
}

function loadHistoryFromLocal() {
    const saved = localStorage.getItem('sicoob_chat_history');
    if (saved) {
        try {
            chatHistory = JSON.parse(saved);
            chatHistory.forEach(msg => {
                const role = msg.role === 'model' ? 'bot' : 'user';
                appendMessage(role, msg.content, true);
            });
        } catch(e) { console.error("Erro ao carregar histórico", e); }
    }
}

// Chamar ao carregar a página
document.addEventListener('DOMContentLoaded', () => {
    loadHistoryFromLocal();
});

const renderText = (text) => {
    let htmlContent = "";
    if (window.marked) {
        htmlContent = marked.parse(text);
    } else {
        let formattedText = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        formattedText = formattedText.replace(/\*(.*?)\*/g, "<em>$1</em>");
        formattedText = formattedText.replace(/\n\n/g, "<br><br>");
        formattedText = formattedText.replace(/\n/g, "<br>");
        htmlContent = formattedText;
    }
    
    // SANITIZAÇÃO (XSS Protection)
    if (window.DOMPurify) {
        return DOMPurify.sanitize(htmlContent);
    }
    return htmlContent;
};

function appendMessage(sender, text, skipSave = false) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerHTML = renderText(text);
    
    // Se for bot, adiciona botão de cópia básico (para mensagens iniciais/histórico sem fontes detalhadas no metadado restrito)
    if (sender === 'bot') {
        const copyBtn = document.createElement('div');
        copyBtn.style.marginTop = '0.8rem';
        copyBtn.style.borderTop = '1px dashed var(--glass-border)';
        copyBtn.style.paddingTop = '0.5rem';
        const escapedText = text.replace(/['"`]/g, "\\$1").replace(/\n/g, "\\n");
        copyBtn.innerHTML = `
            <button class="btn-copy" onclick="copyToClipboard(this, \`${escapedText}\`)">
                📋 Copiar Resposta
            </button>
        `;
        div.appendChild(copyBtn);
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    if (!skipSave && (sender === 'user' || sender === 'bot')) {
        saveHistoryToLocal();
    }
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = chatInput.value.trim();
    if(!query) return;

    appendMessage('user', query);
    chatInput.value = '';
    btnChat.disabled = true;
    
    const baseTypingHtml = '<span class="loading-spinner" style="width:12px; height:12px; border-width:2px; padding:0; border-top-color:var(--primary); vertical-align:-2px"></span> ';
    
    let maxRetries = 3;
    let attempt = 0;
    let success = false;
    
    while(attempt < maxRetries && !success) {
        attempt++;
        
        const typingId = "typing_" + Date.now() + "_" + attempt;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot';
        typingDiv.id = typingId;
        
        if (attempt === 1) {
            typingDiv.innerHTML = baseTypingHtml + 'Fatiando conhecimento...';
        } else {
            typingDiv.innerHTML = baseTypingHtml + `Oscilação detectada. Tentando novamente (${attempt}/${maxRetries})...`;
        }
        
        chatBox.appendChild(typingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        
        let botMsgDiv = null;
        
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
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
                    throw new Error("⚠️ O limite da API Gemini foi atingido (Falta de tokens/Quota excedida).");
                }
                if (res.status === 503 || errorDetail.includes("503") || errorDetail.includes("UNAVAILABLE") || errorDetail.includes("high demand")) {
                    throw new Error("⚠️ Ops! Nossos servidores (Google Gemini) estão sob altíssima demanda.");
                }
                throw new Error(errorDetail);
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullResponse = "";
            let buffer = "";
            let matches = [];
            
            botMsgDiv = document.createElement('div');
            botMsgDiv.className = `message bot`;
            chatBox.appendChild(botMsgDiv);
            
            while(true) {
                const {done, value} = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Mantém o pedaço incompleto para o próximo loop
                
                for(const line of lines) {
                    if(!line.trim()) continue;
                    
                    let parsed;
                    try {
                        parsed = JSON.parse(line);
                    } catch(e) {
                        console.warn("Aviso: fragmento JSON corrompido ou cortado pela rede ignorado:", line);
                        continue;
                    }

                    if(parsed.type === "chunk") {
                        fullResponse += parsed.text;
                        botMsgDiv.innerHTML = renderText(fullResponse);
                        chatBox.scrollTop = chatBox.scrollHeight;
                    } else if (parsed.type === "matches") {
                        matches = parsed.matches;
                    } else if (parsed.type === "error") {
                        let errStr = parsed.detail;
                        if (errStr.includes("503") || errStr.includes("UNAVAILABLE") || errStr.includes("high demand")) {
                            errStr = "⚠️ Ops! Nossos servidores (Google Gemini) estão sob altíssima demanda.";
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
            
            // Adiciona botões de Feedback na resposta
            const currentQ = query.replace(/(['"])/g, "\\$1");
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = finalHtml;
            const plainResponse = (tempDiv.innerText || "").substring(0, 120).replace(/(['"\n])/g, " ");
            
            // Texto formatado para cópia (Resposta + Fontes)
            let textForCopy = fullResponse + "\n\n--- FONTES CONSULTADAS ---\n";
            matches.forEach(m => {
                textForCopy += `\n- [${m.metadata.original_file}]: "${m.metadata.conteudo}"`;
            });
            const escapedCopyText = textForCopy.replace(/[`]/g, "\\`").replace(/[$]/g, "\\$");

            finalHtml += `
                <div class="feedback-actions">
                    <div style="display:flex; flex-direction:column; gap:0.8rem; width:100%">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size: 0.8rem; color: var(--text-muted);">Esta resposta local foi útil?</span>
                            <button class="btn-copy" onclick="copyToClipboard(this, \`${escapedCopyText}\`)">
                                📋 Copiar com Fontes
                            </button>
                        </div>
                        <div>
                            <button class="btn-feedback" onclick="sendFeedback(this, '${currentQ}', '${plainResponse}...', 1)">👍 Sim</button>
                            <button class="btn-feedback" onclick="sendFeedback(this, '${currentQ}', '${plainResponse}...', -1)">👎 Não</button>
                        </div>
                    </div>
                </div>
            `;
            
            botMsgDiv.innerHTML = finalHtml;
            chatBox.scrollTop = chatBox.scrollHeight;
            
            // Atualiza a memória de conversação
            chatHistory.push({role: 'user', content: query});
            chatHistory.push({role: 'model', content: fullResponse});
            
            // Limita a memória aos últimos 10 turnos para evitar payloads pesados
            if(chatHistory.length > 10) {
                chatHistory = chatHistory.slice(chatHistory.length - 10);
            }
            
            success = true;
            
        } catch (err) {
            const typEl = document.getElementById(typingId);
            if(typEl) typEl.remove();
            if(botMsgDiv) botMsgDiv.remove(); // Limpa as mensagens incompletas da UI
            
            if (attempt >= maxRetries) {
                const currentQ = query.replace(/(['"])/g, "\\$1");
                const retryBtnStr = `<br><br><button class="btn-feedback" style="border-color:#ef4444; color:#ef4444;" onclick="retryLastQuery(this, '${currentQ}')">🔄 Tentar Reenviar a Pergunta</button>`;
                appendMessage('bot', `<span style="color:#ef4444">Desculpe, ocorreu erro crítico após ${maxRetries} tentativas: ${err.message}</span>${retryBtnStr}`);
            } else {
                // Aguarda 1.5 segundo silencioso antes de disparar o loop de tentativa novamente
                await new Promise(r => setTimeout(r, 1500));
            }
        }
    }
    
    btnChat.disabled = false;
    chatInput.focus();
});

window.retryLastQuery = function(btnEl, q) {
    btnEl.disabled = true;
    btnEl.innerHTML = "⏳ Reenviando...";
    const chatInput = document.getElementById('chatInput');
    const btnChat = document.getElementById('btnChat');
    chatInput.value = q;
    btnChat.click();
}
