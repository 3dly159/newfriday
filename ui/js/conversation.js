// Transcript model + sticky, persistent conversation panel.
// Phase D: the panel stays open (sticky, no auto-recede), can be collapsed/reopened,
// and the transcript persists across reloads via localStorage.
const panel = () => document.getElementById('convo-panel');
const scroll = () => document.getElementById('convo-scroll');

const STORE_KEY = 'friday_transcript';
const MAX_STORED = 100;

function _load() {
    try {
        const raw = localStorage.getItem(STORE_KEY);
        const arr = raw ? JSON.parse(raw) : [];
        return Array.isArray(arr) ? arr : [];
    } catch (e) { return []; }
}

function _save(messages) {
    try {
        localStorage.setItem(STORE_KEY, JSON.stringify(messages.slice(-MAX_STORED)));
    } catch (e) { /* storage full / unavailable — non-fatal */ }
}

let messages = _load();

function _render(role, text) {
    const who = role === 'user' ? 'YOU' : 'FRIDAY';
    const div = document.createElement('div');
    div.className = `bubble ${role === 'user' ? 'user' : 'friday'}`;
    div.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`;
    scroll().appendChild(div);
    scroll().scrollTop = scroll().scrollHeight;
}

function addMessage(role, text) {
    messages.push({ role, text });
    _save(messages);
    _render(role, text);
    open();
}

// Restore prior session's messages into the panel on load.
function restore() {
    const host = scroll();
    if (!host) return;
    host.innerHTML = '';
    messages.forEach(m => _render(m.role, m.text));
    if (messages.length) open();
}

function clearHistory() {
    messages = [];
    _save(messages);
    if (scroll()) scroll().innerHTML = '';
}

function open() {
    panel().classList.add('open');
    panel().classList.remove('collapsed');
}

function collapse() {
    panel().classList.remove('open');
    panel().classList.add('collapsed');
}

function toggle() {
    panel().classList.contains('open') ? collapse() : open();
}

// Sticky: no auto-recede. Kept as a no-op so existing callers don't break.
function scheduleRecede() { /* sticky panel — intentionally does not auto-close */ }

function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function init() {
    const closeBtn = document.getElementById('convo-close');
    if (closeBtn) closeBtn.addEventListener('click', collapse);
    const reopen = document.getElementById('convo-reopen');
    if (reopen) reopen.addEventListener('click', open);
    const clearBtn = document.getElementById('convo-clear');
    if (clearBtn) clearBtn.addEventListener('click', clearHistory);
    restore();
}

window.Conversation = { addMessage, open, collapse, toggle, scheduleRecede, restore, clearHistory, init };
