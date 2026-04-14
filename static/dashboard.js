// A autenticação agora é feita via Cookies HttpOnly (session_app_id) injetados pelo backend.

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/stats');
        
        if (!res.ok) throw new Error("Acesso negado ou erro no servidor.");
        
        const data = await res.json();
        renderDashboard(data);
        
        // Novo: Carregar lista de documentos indexados
        loadIndexedFiles();
        
    } catch (err) {
        console.error(err);
        alert("Erro ao carregar estatísticas: " + err.message);
    }
});

function renderDashboard(data) {
    // 1. Atualizar Cards
    const totalQ = Object.values(data.daily_queries).reduce((a, b) => a + b, 0);
    document.getElementById('totalQueries').innerText = totalQ;
    document.getElementById('totalTokens').innerText = data.total_tokens.toLocaleString();
    
    const fb = data.feedback;
    const approval = fb.total > 0 ? Math.round((fb.positive / fb.total) * 100) : 0;
    document.getElementById('approvalRate').innerText = approval + "%";

    // 2. Gráfico de Tokens (Linha)
    const tokenCtx = document.getElementById('tokensChart').getContext('2d');
    const sortedDates = Object.keys(data.daily_tokens).sort();
    
    new Chart(tokenCtx, {
        type: 'line',
        data: {
            labels: sortedDates.map(d => {
                const parts = d.split('-');
                return `${parts[2]}/${parts[1]}`;
            }),
            datasets: [{
                label: 'Tokens Consumidos',
                data: sortedDates.map(d => data.daily_tokens[d]),
                borderColor: '#4a90e2',
                backgroundColor: 'rgba(74, 144, 226, 0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointBackgroundColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: 'rgba(255,255,255,0.5)' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: 'rgba(255,255,255,0.5)' }
                }
            }
        }
    });

    // 3. Gráfico de Feedback (Donut)
    const fbCtx = document.getElementById('feedbackChart').getContext('2d');
    new Chart(fbCtx, {
        type: 'doughnut',
        data: {
            labels: ['Positivo', 'Negativo'],
            datasets: [{
                data: [fb.positive, fb.negative],
                backgroundColor: ['#34a853', '#ea4335'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: 'rgba(255,255,255,0.7)', padding: 20 }
                }
            },
            cutout: '70%'
        }
    });
}

async function loadIndexedFiles() {
    const listContainer = document.getElementById('fileListContainer');
    try {
        const res = await fetch('/api/documents');
        if (!res.ok) throw new Error("Falha ao buscar documentos");
        
        const data = await res.json();
        const files = Object.keys(data);
        
        if (files.length === 0) {
            listContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">Nenhum documento indexado encontrado no ChromaDB.</div>';
            return;
        }

        listContainer.innerHTML = '';
        files.forEach(file => {
            const card = document.createElement('div');
            card.style.background = 'rgba(255,255,255,0.05)';
            card.style.border = '1px solid var(--glass-border)';
            card.style.borderRadius = '12px';
            card.style.padding = '1rem';
            card.style.display = 'flex';
            card.style.alignItems = 'center';
            card.style.gap = '0.8rem';
            card.style.transition = 'transform 0.2s';
            
            card.innerHTML = `
                <span style="font-size: 1.5rem;">📄</span>
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-main);" title="${file}">${file}</div>
                    <div style="font-size: 0.75rem; color: var(--primary-glow);">Indexado no RAG</div>
                </div>
            `;
            
            card.onmouseenter = () => card.style.transform = 'translateY(-3px)';
            card.onmouseleave = () => card.style.transform = 'translateY(0)';
            
            listContainer.appendChild(card);
        });

    } catch (err) {
        listContainer.innerHTML = `<div style="color: #ea4335;">Erro ao carregar documentos: ${err.message}</div>`;
    }
}
