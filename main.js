// Update Clock
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').innerText = now.toTimeString().split(' ')[0];
}
setInterval(updateTime, 1000);
updateTime();

const startBtn = document.getElementById('start-scan');
const terminal = document.getElementById('terminal-log');
const intelGrid = document.getElementById('intel-grid');
const aiStatus = document.getElementById('ai-status');

function addLog(message, type = 'default') {
    const entry = document.createElement('p');
    entry.className = 'log-entry';
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span style="color: #555">[${timestamp}]</span> > ${message}`;
    if (type === 'alert') entry.style.color = 'var(--alert-color)';
    terminal.appendChild(entry);
    terminal.scrollTop = terminal.scrollHeight;
}

startBtn.addEventListener('click', () => {
    startBtn.disabled = true;
    startBtn.innerText = 'SCANNING IN PROGRESS...';
    aiStatus.innerText = 'ANALYZING';
    aiStatus.style.color = 'var(--alert-color)';

    addLog('Initiating global drone warfare information crawl...');
    addLog('Connecting to Defense News servers...', 'default');
    
    // Simulate steps
    setTimeout(() => {
        addLog('Target identified: /unmanned/ section found.');
        addLog('Extracting latest 5 intel reports...');
    }, 1500);

    setTimeout(() => {
        addLog('Calling Gemini AI Core for strategic brief...', 'alert');
        addLog('Processing neural networks for warfare impact analysis...');
    }, 3000);

    setTimeout(() => {
        addLog('Intel extraction complete. 5 reports archived.', 'default');
        displayIntel();
        startBtn.disabled = false;
        startBtn.innerText = 'INITIATE GLOBAL SCAN';
        aiStatus.innerText = 'ONLINE';
        aiStatus.style.color = 'var(--accent-color)';
    }, 6000);
});

function displayIntel() {
    intelGrid.innerHTML = ''; // Clear placeholder

    const mockIntel = [
        {
            title: "U.S. Navy testing new loitering munitions",
            source: "Defense News",
            summary: "Recent tests in the Pacific show increased range for autonomous swarm drones.",
            tags: ["Swarm", "Pacific", "Loitering"],
            aiRating: "Strategic Value: HIGH"
        },
        {
            title: "EW systems evolving to counter FPV threats",
            source: "UAS Magazine",
            summary: "New portable jamming units are being deployed to frontlines.",
            tags: ["EW", "FPV", "Jamming"],
            aiRating: "Strategic Value: CRITICAL"
        }
    ];

    mockIntel.forEach(item => {
        const card = document.createElement('div');
        card.className = 'intel-card';
        card.innerHTML = `
            <div class="card-header">
                <h3>${item.title}</h3>
                <span class="source">${item.source}</span>
            </div>
            <div class="card-body">
                <p>${item.summary}</p>
                <div class="tags">
                    ${item.tags.map(t => `<span class="tag">#${t}</span>`).join('')}
                </div>
            </div>
            <div class="card-footer">
                <span class="ai-rating">${item.aiRating}</span>
            </div>
        `;
        intelGrid.appendChild(card);
    });
}

// Add card styling dynamically if not in CSS
const style = document.createElement('style');
style.textContent = `
    .intel-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border-color);
        padding: 15px;
        transition: all 0.3s;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .intel-card:hover {
        background: rgba(0, 255, 157, 0.05);
        transform: translateY(-5px);
        box-shadow: var(--glow-shadow);
    }
    .card-header h3 {
        font-size: 0.9rem;
        color: var(--accent-color);
    }
    .card-header .source {
        font-size: 0.7rem;
        color: var(--text-dim);
    }
    .card-body p {
        font-size: 0.8rem;
        color: var(--text-bright);
        line-height: 1.4;
    }
    .tags {
        display: flex;
        gap: 8px;
        margin-top: 10px;
    }
    .tag {
        font-size: 0.65rem;
        color: var(--alert-color);
    }
    .card-footer {
        margin-top: auto;
        border-top: 1px solid rgba(255,255,255,0.05);
        padding-top: 10px;
        font-size: 0.7rem;
        font-weight: bold;
        color: var(--accent-color);
    }
`;
document.head.appendChild(style);
