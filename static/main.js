// =============================
// LÓGICA DE INFO DO DOCUMENTO
// =============================

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/doc_info');
        const data = await res.json();
        
        document.getElementById('docLoader').style.display = 'none';
        document.getElementById('docContent').style.display = 'block';
        
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
            body: JSON.stringify({query})
        });
        const data = await res.json();
        
        document.getElementById(typingId).remove();
        if(!res.ok) {
            if (res.status === 429 || (data.detail && data.detail === "LIMITE_DE_TOKENS")) {
                throw new Error("⚠️ O limite da API foi atingido (Falta de tokens/Quota excedida). O serviço poderá ficar temporariamente lento ou interrompido. Por favor, aguarde alguns minutos e tente novamente.");
            }
            throw new Error(data.detail || "Erro no Servidor RAG");
        }
        
        appendMessage('bot', data.response || "Vazio.");
        
    } catch (err) {
        const typEl = document.getElementById(typingId);
        if(typEl) typEl.remove();
        appendMessage('bot', `<span style="color:#ef4444">Desculpe, ocorreu erro crítico: ${err.message}</span>`);
    } finally {
        btnChat.disabled = false;
        chatInput.focus();
    }
});
