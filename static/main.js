const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const ingestForm = document.getElementById('ingestForm');
const btnIngest = document.getElementById('btnIngest');
const ingestResult = document.getElementById('ingestResult');

fileInput.addEventListener('change', (e) => {
    if(e.target.files.length > 0) {
        fileName.textContent = `📎 ${e.target.files[0].name}`;
        fileName.style.color = '#c084fc';
    } else {
        fileName.textContent = '📁 Anexar um arquivo';
        fileName.style.color = 'inherit';
    }
});

function btnLoading(btn, text) {
    btn.disabled = true;
    btn.innerHTML = `<span class="loading-spinner"></span> ${text}`;
}

function btnReset(btn, text) {
    btn.disabled = false;
    btn.innerHTML = text;
}

ingestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const textVal = document.getElementById('textInput').value.trim();
    if(fileInput.files.length === 0 && textVal === "") {
        ingestResult.innerHTML = `<p style="color:#ef4444; margin-top:1rem;">Erro: Ou anexe um arquivo, ou cole o texto.</p>`;
        return;
    }

    const formData = new FormData(ingestForm);
    
    btnLoading(btnIngest, "Fazendo Upload mágico ao Gemini...");
    ingestResult.innerHTML = '';
    
    try {
        const response = await fetch('/api/ingest', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if(!response.ok) throw new Error(data.detail || "Erro de nuvem desconhecido");
        
        ingestResult.innerHTML = `<p style="color:#22c55e; margin-top:1rem;">✅ O Cérebro leu sua fonte! ID: ${data.id}</p>`;
        ingestForm.reset();
        fileName.textContent = '📁 Anexar um arquivo';
        fileName.style.color = 'inherit';
    } catch (err) {
        ingestResult.innerHTML = `<p style="color:#ef4444; margin-top:1rem;">❌ Fogo no parquinho: ${err.message}</p>`;
    } finally {
        btnReset(btnIngest, "Enviar à Nuvem (Vetorizar)");
    }
});

// =============================
// CHAT BOT LÓGICA
// =============================
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatBox = document.getElementById('chatBox');
const btnChat = document.getElementById('btnChat');

function appendMessage(sender, text) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    // Simple basic markdown parser for chat
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

    // 1. O user envia pergunta
    appendMessage('user', query);
    chatInput.value = '';
    btnChat.disabled = true;
    
    // 2. Colocamos o placeholder "Pensando..." pro bot
    const typingId = "typing_" + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = typingId;
    typingDiv.innerHTML = '<span class="loading-spinner" style="width:12px; height:12px; border-width:2px; padding:0; border-top-color:var(--primary); vertical-align:-2px"></span> Lendo Banco de Dados...';
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
        if(!res.ok) throw new Error(data.detail || "Erro no Servidor RAG");
        
        // 3. Imprime resposta genial do Gemini
        appendMessage('bot', data.response || "Mhm, não tenho informações suficientes na base.");
        
    } catch (err) {
        const typEl = document.getElementById(typingId);
        if(typEl) typEl.remove();
        appendMessage('bot', `<span style="color:#ef4444">Desculpe, deu erro de Proxy ou Nuvem: ${err.message}</span>`);
    } finally {
        btnChat.disabled = false;
        chatInput.focus();
    }
});
