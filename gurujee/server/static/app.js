/* GURUJEE PWA — chat logic (T039). No external dependencies. */
'use strict';

const HISTORY_KEY = 'gurujee_history';
const MAX_HISTORY = 100;

let currentBubble = null;
let cursorEl = null;
let ws = null;

// ---- DOM refs ----
const chatEl      = document.getElementById('chat-container');
const inputEl     = document.getElementById('message-input');
const sendBtn     = document.getElementById('send-btn');
const voiceBtn    = document.getElementById('voice-btn');
const statusLabel = document.getElementById('status-label');
const indicator   = document.getElementById('agent-indicator');

// ---- Init ----
loadHistory();
connectWebSocket();

sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// ---- Send ----
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = '';
  appendBubble('user', text);
  saveToHistory('user', text);

  currentBubble = appendBubble('assistant', '');
  cursorEl = document.createElement('span');
  cursorEl.className = 'cursor';
  cursorEl.textContent = '|';
  currentBubble.appendChild(cursorEl);
  scrollBottom();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const raw = decoder.decode(value, { stream: true });
      for (const line of raw.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const json = line.slice(6);
        try {
          const ev = JSON.parse(json);
          if (ev.error) {
            finishBubble(currentBubble, cursorEl);
            const errSpan = document.createElement('span');
            errSpan.className = 'interrupted';
            errSpan.textContent = ` [${ev.error}]`;
            currentBubble.appendChild(errSpan);
            break;
          }
          if (ev.chunk) {
            fullText += ev.chunk;
            if (cursorEl) cursorEl.before(ev.chunk);
            scrollBottom();
          }
          if (ev.done) {
            finishBubble(currentBubble, cursorEl);
            saveToHistory('assistant', fullText);
            break;
          }
        } catch { /* ignore malformed lines */ }
      }
    }
  } catch (err) {
    if (currentBubble) {
      finishBubble(currentBubble, cursorEl);
      const errSpan = document.createElement('span');
      errSpan.className = 'interrupted';
      errSpan.textContent = ' [interrupted]';
      currentBubble.appendChild(errSpan);
    }
    console.error('Chat error:', err);
  }
  currentBubble = null;
  cursorEl = null;
}

// ---- WebSocket ----
function connectWebSocket() {
  const url = `ws://${location.host}/ws`;
  ws = new WebSocket(url);

  ws.onmessage = (e) => {
    try {
      const ev = JSON.parse(e.data);
      if (ev.type === 'agent_status') updateStatusBar(ev);
      if (ev.type === 'automate_result') showAutomationBubble(ev);
      if (ev.type === 'shizuku_unavailable') showShizukuBanner(ev.message);
    } catch { /* ignore */ }
  };

  ws.onopen  = () => { statusLabel.textContent = 'Connected'; };
  ws.onclose = () => {
    statusLabel.textContent = 'Reconnecting…';
    setTimeout(connectWebSocket, 3000);
  };
  ws.onerror = () => ws.close();
}

function updateStatusBar(ev) {
  const allRunning = Object.values(ev.agents || {}).every(s => s === 'RUNNING');
  const anyError   = Object.values(ev.agents || {}).some(s => s === 'ERROR');
  indicator.className = 'indicator indicator--' +
    (anyError ? 'red' : allRunning ? 'green' : 'amber');
  statusLabel.textContent = anyError ? 'Agent error' : allRunning ? 'Ready' : 'Starting…';
}

function showAutomationBubble(ev) {
  const b = appendBubble('automation', `⚡ ${ev.result || 'Done'}`);
  scrollBottom();
}

function showShizukuBanner(msg) {
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;top:28px;left:0;right:0;background:#7c2d12;color:#fff;' +
    'padding:8px 16px;font-size:13px;z-index:200;';
  banner.textContent = msg || 'Shizuku is unavailable. Re-activate it to enable automation.';
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 8000);
}

// ---- History ----
function loadHistory() {
  const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  saved.slice(-50).forEach(({ role, content }) => appendBubble(role, content));
  scrollBottom();
}

function saveToHistory(role, content) {
  const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  history.push({ role, content });
  if (history.length > MAX_HISTORY) history.splice(0, history.length - MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

// ---- Helpers ----
function appendBubble(role, text) {
  const el = document.createElement('div');
  el.className = `bubble bubble--${role}`;
  el.textContent = text;
  chatEl.appendChild(el);
  scrollBottom();
  return el;
}

function finishBubble(bubble, cursor) {
  if (cursor && cursor.parentNode) cursor.remove();
}

function scrollBottom() {
  chatEl.scrollTop = chatEl.scrollHeight;
}

// ---- Voice input ----
voiceBtn.addEventListener('click', () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('Voice input is not supported in this browser.');
    return;
  }
  const rec = new SpeechRecognition();
  rec.lang = 'en-US';
  rec.interimResults = false;
  rec.onresult = (e) => {
    inputEl.value = e.results[0][0].transcript;
    sendMessage();
  };
  rec.start();
});
