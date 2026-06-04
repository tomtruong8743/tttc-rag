const messagesEl = document.getElementById('chat-messages');
const inputEl    = document.getElementById('user-input');
const sendBtn    = document.getElementById('send-btn');

// ── Render helpers ────────────────────────────────────────────────

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}

function formatAnswer(text) {
  // Bold **text**
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Newlines
  text = text.replace(/\n/g, '<br>');
  return text;
}

function appendMessage(role, content, sources, wikiCreated, wikiName) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'You' : 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatAnswer(content);

  if (wikiCreated && wikiName) {
    const notice = document.createElement('div');
    notice.className = 'sources';
    notice.innerHTML = `📄 <strong>New wiki page created:</strong> <span class="source-tag">📝 ${escapeHtml(wikiName)}</span>`;
    bubble.appendChild(notice);
  }

  if (sources && sources.length > 0) {
    const src = document.createElement('div');
    src.className = 'sources';
    src.innerHTML = '<strong>Sources:</strong><br>' +
      sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('');
    bubble.appendChild(src);
  }

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

function showTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'message bot typing';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `
    <div class="avatar">AI</div>
    <div class="bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

// ── Send message ──────────────────────────────────────────────────

async function sendMessage(text) {
  text = (text || inputEl.value).trim();
  if (!text) return;

  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;

  appendMessage('user', escapeHtml(text));
  showTyping();

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text })
    });

    const data = await res.json();
    removeTyping();

    if (data.error) {
      appendMessage('bot', '⚠️ ' + escapeHtml(data.error));
    } else {
      appendMessage('bot', data.answer, data.sources, data.wiki_created, data.wiki_name);
    }
  } catch (err) {
    removeTyping();
    appendMessage('bot', '⚠️ Could not reach the server. Please try again.');
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

// ── Event listeners ───────────────────────────────────────────────

sendBtn.addEventListener('click', () => sendMessage());

// Track IME composition (Vietnamese, Chinese, Japanese, etc.)
let isComposing = false;
inputEl.addEventListener('compositionstart', () => { isComposing = true; });
inputEl.addEventListener('compositionend',   () => { isComposing = false; });

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
    e.preventDefault();
    // Capture and clear immediately so autocomplete
    // cannot append anything after keydown fires
    const text = inputEl.value;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    sendMessage(text);
  }
});

// Auto-resize textarea
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});
