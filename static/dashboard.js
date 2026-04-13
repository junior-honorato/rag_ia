const INTERNAL_API_KEY = "sicoob-internal-dev-key";

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/stats', {
            headers: { 'X-API-KEY': INTERNAL_API_KEY }
        });
        
        if (!res.ok) throw new Error("Acesso negado ou erro no servidor.");
        
        const data = await res.json();
        renderDashboard(data);
        
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
