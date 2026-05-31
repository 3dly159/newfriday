const rail = () => document.getElementById('action-rail');
const chips = {};

function setStateLabel(state) {
    const map = { idle: 'STANDBY', listening: 'LISTENING', thinking: 'THINKING', speaking: 'SPEAKING', acting: 'WORKING' };
    document.getElementById('state-label').textContent = map[state] || state.toUpperCase();
}

function action(msg) {
    let chip = chips[msg.tool];
    if (msg.phase === 'start') {
        if (!chip) {
            chip = document.createElement('div');
            chip.className = 'chip';
            chip.innerHTML = `<span class="spin"></span><span class="lbl"></span>`;
            rail().appendChild(chip);
            chips[msg.tool] = chip;
        }
        chip.querySelector('.lbl').textContent = msg.label;
        requestAnimationFrame(() => chip.classList.add('show'));
    } else if (chip) {
        chip.classList.add(msg.phase === 'error' ? 'error' : 'done');
        chip.querySelector('.lbl').textContent = msg.label;
        setTimeout(() => { chip.classList.remove('show'); setTimeout(() => chip.remove(), 400); delete chips[msg.tool]; }, 2500);
    }
}

function glitch() {
    document.body.classList.add('glitch-mode');
    setTimeout(() => document.body.classList.remove('glitch-mode'), 3000);
}

function init() {
    document.getElementById('settings-btn').addEventListener('click', openSettings);
    document.getElementById('close-settings').addEventListener('click', () => modal().classList.add('hidden'));
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    setInterval(updateVitals, 2500);
}
const modal = () => document.getElementById('settings-modal');
async function openSettings() {
    const cfg = await (await fetch('/api/config')).json();
    renderSettings(cfg);
    const perms = await (await fetch('/api/permissions')).json();
    renderPermissions(perms);
    modal().classList.remove('hidden');
}
function renderSettings(cfg) {
    const form = document.getElementById('settings-form'); form.innerHTML = '';
    for (const section in cfg) {
        if (typeof cfg[section] !== 'object' || cfg[section] === null) continue;
        for (const key in cfg[section]) {
            const label = document.createElement('label'); label.textContent = `${section}.${key}`; label.style.fontSize = '11px';
            const input = document.createElement('input'); input.type = 'text'; input.value = cfg[section][key];
            input.dataset.section = section; input.dataset.key = key;
            input.style.cssText = 'background:rgba(255,255,255,.08);border:1px solid var(--border);color:#fff;padding:6px;border-radius:6px';
            form.appendChild(label); form.appendChild(input);
        }
    }
}
function renderPermissions(perms) {
    const form = document.getElementById('permissions-form'); form.innerHTML = '';
    if (typeof perms !== 'object') return;
    for (const key in perms) {
        const label = document.createElement('label'); label.textContent = key.replace(/_/g, ' '); label.style.fontSize = '11px';
        const sel = document.createElement('select'); sel.dataset.key = key;
        ['allow', 'ask', 'deny'].forEach(o => { const op = document.createElement('option'); op.value = o; op.textContent = o.toUpperCase(); if (o === perms[key]) op.selected = true; sel.appendChild(op); });
        sel.style.cssText = 'background:rgba(255,255,255,.08);border:1px solid var(--border);color:#fff;padding:6px;border-radius:6px';
        form.appendChild(label); form.appendChild(sel);
    }
}
async function saveSettings() {
    const cfg = {};
    document.querySelectorAll('#settings-form input').forEach(i => {
        const { section, key } = i.dataset; cfg[section] = cfg[section] || {};
        let v = i.value; if (v !== '' && !isNaN(v)) v = parseFloat(v); cfg[section][key] = v;
    });
    await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) });
    const perms = {}; document.querySelectorAll('#permissions-form select').forEach(s => perms[s.dataset.key] = s.value);
    await fetch('/api/permissions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(perms) });
    modal().classList.add('hidden');
}
async function updateVitals() {
    try {
        const v = await (await fetch('/api/vitals')).json();
        window.__vitals = v;
    } catch (e) { /* ignore */ }
}

function requestApproval(perm) {
    const toast = document.getElementById('permission-toast');
    document.getElementById('toast-message').textContent = `Friday requests permission: ${perm.toUpperCase()}`;
    toast.classList.remove('hidden');
    document.getElementById('toast-allow').onclick = async () => { await setPerm(perm, 'allow'); toast.classList.add('hidden'); };
    document.getElementById('toast-deny').onclick = async () => { await setPerm(perm, 'deny'); toast.classList.add('hidden'); };
}
async function setPerm(perm, val) {
    await fetch('/api/permissions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ [perm]: val }) });
}

window.Hud = { init, action, glitch, setStateLabel, requestApproval };
