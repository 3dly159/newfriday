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

// ---- Settings sidebar (scrollable, collapsible dropdown groups) ----

// Known enums get a <select>; everything else is a text field.
const ENUMS = {
    model_provider: ['ollama', 'anthropic', 'openai'],
    interaction_mode: ['continuous', 'wake_word'],
    auto_approve_hid: ['true', 'false'],
    capture_dataset: ['true', 'false'],
};
const PERM_VALUES = ['allow', 'ask', 'deny'];

function sidebar() { return document.getElementById('settings-sidebar'); }
function scrim() { return document.getElementById('settings-scrim'); }

function init() {
    document.getElementById('settings-btn').addEventListener('click', openSettings);
    document.getElementById('close-settings').addEventListener('click', closeSettings);
    scrim().addEventListener('click', closeSettings);
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    setInterval(updateVitals, 2500);
}

async function openSettings() {
    const body = document.getElementById('settings-body');
    body.innerHTML = '';
    try {
        const cfg = await (await fetch('/api/config')).json();
        for (const section in cfg) {
            if (typeof cfg[section] !== 'object' || cfg[section] === null) continue; // skip system_memory blob etc.
            body.appendChild(configGroup(section, cfg[section]));
        }
        const perms = await (await fetch('/api/permissions')).json();
        if (perms && typeof perms === 'object') body.appendChild(permGroup(perms));
    } catch (e) {
        body.innerHTML = `<p class="settings-error">Could not load settings: ${e}</p>`;
    }
    scrim().classList.remove('hidden');
    sidebar().classList.remove('hidden');
    requestAnimationFrame(() => { sidebar().classList.add('open'); scrim().classList.add('open'); });
}

function closeSettings() {
    sidebar().classList.remove('open');
    scrim().classList.remove('open');
    setTimeout(() => { sidebar().classList.add('hidden'); scrim().classList.add('hidden'); }, 350);
}

function field(section, key, value) {
    const row = document.createElement('label');
    row.className = 'settings-field';
    row.innerHTML = `<span class="fk">${key.replace(/_/g, ' ')}</span>`;
    let input;
    if (ENUMS[key]) {
        input = document.createElement('select');
        ENUMS[key].forEach(opt => {
            const o = document.createElement('option');
            o.value = opt; o.textContent = opt;
            if (String(value) === opt) o.selected = true;
            input.appendChild(o);
        });
    } else {
        input = document.createElement('input');
        input.type = 'text';
        input.value = value;
    }
    input.dataset.section = section;
    input.dataset.key = key;
    row.appendChild(input);
    return row;
}

function configGroup(section, obj) {
    const d = document.createElement('details');
    d.className = 'settings-group';
    d.open = true;
    const sum = document.createElement('summary');
    sum.textContent = section.replace(/_/g, ' ');
    d.appendChild(sum);
    for (const key in obj) d.appendChild(field(section, key, obj[key]));
    return d;
}

function permGroup(perms) {
    const d = document.createElement('details');
    d.className = 'settings-group';
    d.open = true;
    const sum = document.createElement('summary');
    sum.textContent = 'security permissions';
    d.appendChild(sum);
    for (const key in perms) {
        const row = document.createElement('label');
        row.className = 'settings-field';
        row.innerHTML = `<span class="fk">${key.replace(/_/g, ' ')}</span>`;
        const sel = document.createElement('select');
        sel.dataset.perm = key;
        PERM_VALUES.forEach(v => {
            const o = document.createElement('option');
            o.value = v; o.textContent = v.toUpperCase();
            if (perms[key] === v) o.selected = true;
            sel.appendChild(o);
        });
        row.appendChild(sel);
        d.appendChild(row);
    }
    return d;
}

async function saveSettings() {
    const cfg = {};
    document.querySelectorAll('#settings-body [data-section]').forEach(i => {
        const { section, key } = i.dataset;
        cfg[section] = cfg[section] || {};
        let v = i.value;
        if (v !== '' && !isNaN(v) && i.tagName !== 'SELECT') v = parseFloat(v);
        cfg[section][key] = v;
    });
    await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) });

    const perms = {};
    document.querySelectorAll('#settings-body [data-perm]').forEach(s => perms[s.dataset.perm] = s.value);
    if (Object.keys(perms).length) {
        await fetch('/api/permissions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(perms) });
    }
    closeSettings();
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
