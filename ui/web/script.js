/* ─── script.js — Blinsky UI v2 ─────────────────────────────────────────── */

let apiURL = localStorage.getItem('blinsky_backend_url') || 'http://localhost:9001';
let tavilyKey = localStorage.getItem('blinsky_tavily_key') || '';
let ollamaURL = localStorage.getItem('blinsky_ollama_url') || 'http://localhost:11434';
let ollamaModel = localStorage.getItem('blinsky_ollama_model') || 'qwen2.5:7b';

let conversationHistory = [];
try {
    conversationHistory = JSON.parse(localStorage.getItem('blinsky_history')) || [];
} catch {
    conversationHistory = [];
}

function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-Tavily-Key': tavilyKey,
        'X-Ollama-URL': ollamaURL,
        'X-Ollama-Model': ollamaModel
    };
}

// ── DOM refs ──────────────────────────────────────────────────────────────────
const chatMessages   = document.getElementById('chat-messages');
const chatScroll     = document.getElementById('chat-scroll');
const msgInput       = document.getElementById('msg-input');
const sendBtn        = document.getElementById('send-btn');
const micBtn         = document.getElementById('mic-btn');
const voiceBars      = document.getElementById('voice-bars');
const wakeBtn        = document.getElementById('wake-btn');
const wakeLabel      = document.getElementById('wake-label');
const connDot        = document.getElementById('conn-dot');
const connLabel      = document.getElementById('conn-label');
const clearHistBtn   = document.getElementById('clear-history-btn');
const sidebarToggle  = document.getElementById('sidebar-toggle');
const sidebar        = document.querySelector('.sidebar');
const skillsList     = document.getElementById('skills-list');
const skillCount     = document.getElementById('skill-count');
const skillNameIn    = document.getElementById('skill-name-input');
const skillContentIn = document.getElementById('skill-content-input');
const skillAddBtn    = document.getElementById('skill-add-btn');
const uptimeBadge    = document.getElementById('uptime-badge');

// ── Animated background (particle field) ─────────────────────────────────────
const canvas = document.getElementById('bg-canvas');
const ctx    = canvas.getContext('2d');

let W, H, particles = [];

function resizeCanvas() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
}
window.addEventListener('resize', () => { resizeCanvas(); initParticles(); });
resizeCanvas();

function initParticles() {
    particles = Array.from({ length: 70 }, () => ({
        x:     Math.random() * W,
        y:     Math.random() * H,
        r:     Math.random() * 1.5 + 0.3,
        vx:    (Math.random() - 0.5) * 0.2,
        vy:    (Math.random() - 0.5) * 0.2,
        alpha: Math.random() * 0.5 + 0.1,
    }));
}
initParticles();

function drawParticles() {
    ctx.clearRect(0, 0, W, H);

    // Subtle radial gradient glow
    const g = ctx.createRadialGradient(W * 0.5, H * 0.15, 0, W * 0.5, H * 0.15, W * 0.6);
    g.addColorStop(0,   'rgba(124,58,237,0.04)');
    g.addColorStop(0.5, 'rgba(6,182,212,0.02)');
    g.addColorStop(1,   'transparent');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);

    // Draw particle connections
    for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
            const b = particles[j];
            const dx = a.x - b.x, dy = a.y - b.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            if (dist < 120) {
                ctx.strokeStyle = `rgba(124,58,237,${0.06 * (1 - dist / 120)})`;
                ctx.lineWidth = 0.5;
                ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
                ctx.stroke();
            }
        }
    }

    // Draw particles
    particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180,160,255,${p.alpha})`;
        ctx.fill();

        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;
    });

    requestAnimationFrame(drawParticles);
}
drawParticles();

// ── Utilities ─────────────────────────────────────────────────────────────────
function scrollBottom() {
    setTimeout(() => chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: 'smooth' }), 50);
}

function timestamp() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function fmtUptime(s) {
    if (s < 60)   return `⏱ ${s}s`;
    if (s < 3600) return `⏱ ${Math.floor(s/60)}m`;
    return `⏱ ${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
}

// ── Message rendering ─────────────────────────────────────────────────────────
function renderMessage(role, text, opts = {}) {
    const row = document.createElement('div');
    row.className = `msg-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = role === 'assistant' ? 'B' : 'U';

    const body = document.createElement('div');
    body.className = 'msg-body';

    // Optional badge (tool call or skill action)
    if (opts.toolCall) {
        const badge = document.createElement('div');
        badge.className = 'tool-badge';
        badge.innerHTML = `🔧 <span>${opts.toolCall.name}(${Object.values(opts.toolCall.args || {}).join(', ')})</span>`;
        body.appendChild(badge);
    }
    if (opts.skillAction) {
        const badge = document.createElement('div');
        badge.className = 'skill-badge';
        badge.innerHTML = `🧠 Skill command`;
        body.appendChild(badge);
    }

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = text;

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    meta.textContent = timestamp();

    body.appendChild(bubble);
    body.appendChild(meta);

    row.appendChild(avatar);
    row.appendChild(body);

    chatMessages.appendChild(row);
    scrollBottom();
    return row;
}

function showTyping() {
    const row = document.createElement('div');
    row.className = 'typing-row';
    row.id = 'typing-indicator';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.style.cssText = 'background: linear-gradient(135deg,#7c3aed,#06b6d4); color: white; width:34px; height:34px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700;';
    avatar.textContent = 'B';

    const bubble = document.createElement('div');
    bubble.className = 'typing-bubble';
    bubble.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    scrollBottom();
}

function hideTyping() {
    document.getElementById('typing-indicator')?.remove();
}

// ── Status polling ─────────────────────────────────────────────────────────────
async function fetchStatus() {
    try {
        const r = await fetch(`${apiURL}/status`, { headers: getHeaders() });
        const d = await r.json();

        // Connection indicator
        connDot.className = 'conn-dot online';
        connLabel.textContent = 'Connected';

        // Phases
        const phases = [d.phase1, d.phase2, d.phase3, d.phase4];
        ['ph1','ph2','ph3','ph4'].forEach((id, i) => {
            const dot = document.getElementById(id)?.querySelector('.phase-dot');
            if (dot) {
                dot.className = `phase-dot ${phases[i]?.active ? 'active' : 'inactive'}`;
            }
        });

        // Tools
        const searchChip = document.getElementById('tool-search');
        if (searchChip) searchChip.className = `tool-chip ${d.tools?.web_search ? 'active' : ''}`;

        // Uptime
        if (d.uptime !== undefined) uptimeBadge.textContent = fmtUptime(d.uptime);

    } catch {
        connDot.className = 'conn-dot offline';
        connLabel.textContent = 'Disconnected';
    }
}

// ── Skills ────────────────────────────────────────────────────────────────────
async function fetchSkills() {
    try {
        const r = await fetch(`${apiURL}/skills`, { headers: getHeaders() });
        const d = await r.json();
        renderSkills(d.skills || []);
    } catch { /* silent */ }
}

function renderSkills(skills) {
    skillCount.textContent = skills.length;
    if (!skills.length) {
        skillsList.innerHTML = '<p class="empty-state">No skills yet. Teach me something!</p>';
        return;
    }
    skillsList.innerHTML = '';
    skills.forEach(s => {
        const chip = document.createElement('div');
        chip.className = 'skill-chip';
        chip.innerHTML = `
            <span class="skill-chip-name" title="${s.name}">${s.name}</span>
            <span class="skill-chip-val" title="${s.content}">${s.content}</span>
            <button class="skill-del-btn" data-name="${s.name}" title="Forget this skill">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        `;
        chip.querySelector('.skill-del-btn').addEventListener('click', async e => {
            const name = e.currentTarget.dataset.name;
            await fetch(`${apiURL}/skills/${encodeURIComponent(name)}`, { method: 'DELETE', headers: getHeaders() });
            fetchSkills();
        });
        skillsList.appendChild(chip);
    });
}

skillAddBtn.addEventListener('click', async () => {
    const name    = skillNameIn.value.trim();
    const content = skillContentIn.value.trim();
    if (!name || !content) return;
    await fetch(`${apiURL}/skills`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ name, content }),
    });
    skillNameIn.value = '';
    skillContentIn.value = '';
    fetchSkills();
});

// Enter key in skill inputs
[skillNameIn, skillContentIn].forEach(el => {
    el.addEventListener('keypress', e => { if (e.key === 'Enter') skillAddBtn.click(); });
});

// ── Send message ──────────────────────────────────────────────────────────────
let agentActive = false;

async function sendMessage() {
    const text = msgInput.value.trim();
    if (!text) return;

    msgInput.value = '';
    msgInput.style.height = 'auto';
    renderMessage('user', text);
    showTyping();

    try {
        const endpoint = agentActive ? `${apiURL}/agent` : `${apiURL}/chat`;
        const r = await fetch(endpoint, {
            method:  'POST',
            headers: getHeaders(),
            body:    JSON.stringify({ message: text, history: conversationHistory }),
        });
        const d = await r.json();
        hideTyping();

        let replyText = d.reply || 'No response.';
        if (agentActive && d.steps && d.steps.length > 0) {
            // format reasoning steps
            const reasoning = d.steps.map(step => `> ${step}`).join('\n');
            replyText = `**Reasoning Steps:**\n${reasoning}\n\n${replyText}`;
        }

        renderMessage('assistant', replyText, {
            toolCall:    (d.tool_calls && d.tool_calls[0]) || d.tool_call || null,
            skillAction: d.skill_action || false,
        });

        // Save to client history
        conversationHistory.push({ user: text, assistant: d.reply || '' });
        localStorage.setItem('blinsky_history', JSON.stringify(conversationHistory));

        // Refresh skills in case a skill command was run
        if (d.skill_action) fetchSkills();
    } catch (err) {
        hideTyping();
        renderMessage('assistant', `Connection error — is the backend running on ${apiURL}?`);
    }
}

sendBtn.addEventListener('click', sendMessage);
msgInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// Quick action buttons
document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        msgInput.value = btn.dataset.msg;
        sendMessage();
    });
});

// ── Sidebar toggle ────────────────────────────────────────────────────────────
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

// ── Clear history ─────────────────────────────────────────────────────────────
clearHistBtn.addEventListener('click', async () => {
    chatMessages.innerHTML = '';
    conversationHistory = [];
    localStorage.removeItem('blinsky_history');
    renderMessage('assistant', '🗑️ Conversation history cleared. Starting fresh!');
});

// ── Wake word toggle ──────────────────────────────────────────────────────────
let wakeActive = false;
wakeBtn.addEventListener('click', () => {
    wakeActive = !wakeActive;
    wakeBtn.classList.toggle('active', wakeActive);
    wakeLabel.textContent = wakeActive ? 'Listening…' : 'Wake Word';
    if (wakeActive) {
        renderMessage('assistant',
            `🎙️ Wake word mode ON — say "${document.getElementById('ph2')?.querySelector('.phase-name')?.textContent || 'blueberry'}" to activate.\n` +
            `Make sure the backend is running with:\n  python main.py --wake`
        );
    } else {
        renderMessage('assistant', '⏹️ Wake word mode off.');
    }
});

// ── Mic button (UI state only — actual voice handled by Python backend) ───────
let recording = false;
micBtn.addEventListener('click', () => {
    recording = !recording;
    micBtn.classList.toggle('recording', recording);
    voiceBars.classList.toggle('active', recording);
    if (recording) {
        msgInput.placeholder = 'Listening…';
    } else {
        msgInput.placeholder = 'Ask Blinsky anything…';
        voiceBars.classList.remove('active');
    }
});

// ── Agent toggle ──────────────────────────────────────────────────────────────
const agentBtn = document.getElementById('agent-btn');
const agentLabel = document.getElementById('agent-label');
agentBtn.addEventListener('click', () => {
    agentActive = !agentActive;
    agentBtn.classList.toggle('active', agentActive);
    agentLabel.textContent = agentActive ? 'Agent: Active' : 'Agent Mode';
});

// ── Export / Import ───────────────────────────────────────────────────────────
document.getElementById('export-btn').addEventListener('click', () => {
    try {
        const data = {
            history: conversationHistory,
            exported_at: new Date().toISOString()
        };
        const content = JSON.stringify(data, null, 2);
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'blinsky_conversation.json';
        a.click(); URL.revokeObjectURL(url);
    } catch { renderMessage('assistant', 'Export failed.'); }
});

document.getElementById('import-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    try {
        const data = JSON.parse(text);
        conversationHistory = data.history || [];
        localStorage.setItem('blinsky_history', JSON.stringify(conversationHistory));
        
        chatMessages.innerHTML = '';
        conversationHistory.forEach(turn => {
            renderMessage('user', turn.user);
            renderMessage('assistant', turn.assistant);
        });
        renderMessage('assistant', `📂 Imported ${conversationHistory.length} conversation turns.`);
    } catch { renderMessage('assistant', 'Import failed — invalid JSON file.'); }
});

// ── Settings Modal ────────────────────────────────────────────────────────────
const settingsModal = document.getElementById('settings-modal');
const settingsBtn = document.getElementById('settings-btn');
const modalCloseBtn = document.getElementById('modal-close-btn');
const modalSaveBtn = document.getElementById('modal-save-btn');
const modalTestBtn = document.getElementById('modal-test-btn');
const modalStatus = document.getElementById('modal-status');

const setBackendUrl = document.getElementById('set-backend-url');
const setTavilyKey = document.getElementById('set-tavily-key');
const setOllamaUrl = document.getElementById('set-ollama-url');
const setOllamaModel = document.getElementById('set-ollama-model');

function showModal() {
    setBackendUrl.value = apiURL;
    setTavilyKey.value = tavilyKey;
    setOllamaUrl.value = ollamaURL;
    setOllamaModel.value = ollamaModel;
    modalStatus.style.display = 'none';
    settingsModal.style.display = 'flex';
}

function hideModal() {
    settingsModal.style.display = 'none';
}

function showModalStatus(text, type) {
    modalStatus.textContent = text;
    modalStatus.className = `modal-status ${type}`;
}

settingsBtn.addEventListener('click', showModal);
modalCloseBtn.addEventListener('click', hideModal);

settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) hideModal();
});

modalTestBtn.addEventListener('click', async () => {
    const tempBackend = setBackendUrl.value.trim();
    const tempTavily = setTavilyKey.value.trim();
    const tempOllamaUrl = setOllamaUrl.value.trim();
    const tempOllamaModel = setOllamaModel.value.trim();
    
    if (!tempBackend || !tempTavily || !tempOllamaUrl) {
        showModalStatus('Backend URL, Tavily Key, and Ollama URL are required to test!', 'error');
        return;
    }
    
    showModalStatus('Testing connection...', 'pending');
    
    try {
        const r = await fetch(`${tempBackend}/validate-keys`, {
            method: 'POST',
            headers: {
                'X-Tavily-Key': tempTavily,
                'X-Ollama-URL': tempOllamaUrl,
                'X-Ollama-Model': tempOllamaModel
            }
        });
        const d = await r.json();
        if (r.ok && d.ok) {
            showModalStatus('Connection test successful! Keys are valid.', 'success');
        } else {
            showModalStatus(`Test failed: ${d.detail || 'Unknown error'}`, 'error');
        }
    } catch (err) {
        showModalStatus(`Failed to connect to backend: ${err.message}`, 'error');
    }
});

modalSaveBtn.addEventListener('click', () => {
    apiURL = setBackendUrl.value.trim();
    tavilyKey = setTavilyKey.value.trim();
    ollamaURL = setOllamaUrl.value.trim();
    ollamaModel = setOllamaModel.value.trim();
    
    localStorage.setItem('blinsky_backend_url', apiURL);
    localStorage.setItem('blinsky_tavily_key', tavilyKey);
    localStorage.setItem('blinsky_ollama_url', ollamaURL);
    localStorage.setItem('blinsky_ollama_model', ollamaModel);
    
    hideModal();
    renderMessage('assistant', '⚙️ Settings saved successfully!');
    
    // Refresh status and skills with new settings
    fetchStatus();
    fetchSkills();
});

function checkSetup() {
    if (!tavilyKey || !ollamaURL || !apiURL) {
        showModal();
    }
}

// ── Initial load ──────────────────────────────────────────────────────────────
checkSetup();
if (conversationHistory.length > 0) {
    chatMessages.innerHTML = ''; // clear welcome card
    conversationHistory.forEach(turn => {
        renderMessage('user', turn.user);
        renderMessage('assistant', turn.assistant);
    });
}
fetchStatus();
fetchSkills();
setInterval(fetchStatus, 8000);   // poll every 8s
setInterval(fetchSkills, 15000);  // sync skills every 15s
