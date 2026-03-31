// Cornerstone AI — Chat interface JavaScript

let convId = window.CONV_ID || null;

const messagesEl = document.getElementById('messages');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const modelSelect = document.getElementById('modelSelect');

function appendMessage(role, content) {
    // Remove empty state if present
    const empty = messagesEl.querySelector('.chat-empty');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `
        <div class="msg-role">${role === 'user' ? 'You' : 'Cornerstone AI'}</div>
        <div class="msg-content">${escapeHtml(content)}</div>
    `;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setLoading(loading) {
    sendBtn.disabled = loading;
    sendBtn.textContent = loading ? '...' : 'Send';
    userInput.disabled = loading;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;

    appendMessage('user', message);
    userInput.value = '';
    setLoading(true);

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_id: convId,
                model: modelSelect.value,
            }),
        });

        const data = await resp.json();

        if (resp.ok) {
            appendMessage('assistant', data.response);
            if (data.conversation_id && !convId) {
                convId = data.conversation_id;
                window.history.replaceState({}, '', `/chat?id=${convId}`);
            }
        } else {
            appendMessage('assistant', `Error: ${data.detail || data.error || 'Something went wrong'}`);
        }
    } catch (err) {
        appendMessage('assistant', `Error: ${err.message}`);
    }

    setLoading(false);
    userInput.focus();
});

function newChat() {
    convId = null;
    window.location.href = '/chat';
}

// Scroll to bottom on load
if (messagesEl) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}
