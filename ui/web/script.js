const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');

const API_URL = 'http://localhost:9000/chat';

function addMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    avatarDiv.textContent = role === 'assistant' ? 'B' : 'U';
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'bubble';
    bubbleDiv.textContent = content;
    
    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(bubbleDiv);
    
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function addTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message assistant typing`;
    msgDiv.id = 'typing-indicator';
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    avatarDiv.textContent = 'B';
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'bubble';
    
    const typingIndicatorDiv = document.createElement('div');
    typingIndicatorDiv.className = 'typing-indicator';
    typingIndicatorDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    
    bubbleDiv.appendChild(typingIndicatorDiv);
    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(bubbleDiv);
    
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    
    messageInput.value = '';
    addMessage('user', text);
    
    addTypingIndicator();
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: text })
        });
        
        const data = await response.json();
        removeTypingIndicator();
        
        if (data.reply) {
            addMessage('assistant', data.reply);
        } else {
            console.error("Backend returned unexpected data:", data);
            addMessage('assistant', "Error: Check browser console. " + JSON.stringify(data));
        }
    } catch (err) {
        console.error(err);
        removeTypingIndicator();
        addMessage('assistant', "Connection error: Unable to reach the API backend at " + API_URL);
    }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

let isRecording = false;
micBtn.addEventListener('click', () => {
    isRecording = !isRecording;
    if (isRecording) {
        micBtn.classList.add('active');
        messageInput.placeholder = 'Listening...';
    } else {
        micBtn.classList.remove('active');
        messageInput.placeholder = 'Message Blinsky...';
    }
});

// ── Phase 2: Wake Word toggle ────────────────────────────────────────────
const wakeBtn = document.getElementById('wake-btn');
const wakeLabel = document.getElementById('wake-label');
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
let wakeActive = false;

wakeBtn.addEventListener('click', () => {
    wakeActive = !wakeActive;
    if (wakeActive) {
        wakeBtn.classList.add('active');
        wakeLabel.textContent = 'Listening...';
        statusText.textContent = 'Wake word active';
        statusDot.style.background = '#2ea043';
        addMessage('assistant',
            '🎙️ Wake word mode is ON. Say "blueberry" (or your configured keyword) to activate me. ' +
            'Make sure the backend is running with: python main.py --wake'
        );
    } else {
        wakeBtn.classList.remove('active');
        wakeLabel.textContent = 'Wake Word';
        statusText.textContent = 'Connected';
        statusDot.style.background = '#2ea043';
        addMessage('assistant', '⏹️ Wake word mode turned off.');
    }
});
