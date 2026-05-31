// Transcript model + Hybrid panel show/recede choreography.
const panel = () => document.getElementById('convo-panel');
const scroll = () => document.getElementById('convo-scroll');
let recedeTimer = null;

function addMessage(role, text) {
    const who = role === 'user' ? 'YOU' : 'FRIDAY';
    const div = document.createElement('div');
    div.className = `bubble ${role === 'user' ? 'user' : 'friday'}`;
    div.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`;
    scroll().appendChild(div);
    scroll().scrollTop = scroll().scrollHeight;
    open();
}
function open() {
    panel().classList.add('open');
    if (recedeTimer) clearTimeout(recedeTimer);
}
function scheduleRecede() {
    if (recedeTimer) clearTimeout(recedeTimer);
    recedeTimer = setTimeout(() => panel().classList.remove('open'), 12000);
}
function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

window.Conversation = { addMessage, open, scheduleRecede };
