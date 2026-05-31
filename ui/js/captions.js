// Word-sync ("karaoke") caption renderer with sentence-fade fallback.
const stage = () => document.getElementById('caption-line');
let timers = [];

function clear() {
    timers.forEach(clearTimeout); timers = [];
    const el = stage(); el.classList.remove('show'); el.innerHTML = '';
}

function play(seg, audioMs) {
    clear();
    const el = stage();
    if (seg.mode === 'word' && seg.words && seg.words.length) {
        el.innerHTML = seg.words.map((w, i) => `<span class="w" data-i="${i}">${escapeHtml(w.word)}</span>`).join(' ');
        el.classList.add('show');
        seg.words.forEach((w, i) => {
            timers.push(setTimeout(() => {
                const span = el.querySelector(`.w[data-i="${i}"]`);
                if (span) span.classList.add('lit');
            }, w.offset_ms));
        });
    } else {
        el.innerHTML = `<span class="w lit">${escapeHtml(seg.text)}</span>`;
        el.classList.add('show');
    }
    timers.push(setTimeout(() => el.classList.remove('show'), (audioMs || 2000) + 600));
}

function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

window.Captions = { play, clear };
