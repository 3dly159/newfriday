// Cinematic boot overlay: prints init lines, then dissolves into the HUD.
const LINES = [
    "INITIALIZING COGNITIVE CORE…",
    "MOUNTING MEMORY LAYERS [7/7]",
    "CALIBRATING VOICE SYNTHESIS…",
    "AGENCY SUBSYSTEMS ONLINE",
    "FRIDAY READY.",
];

function runBoot(onDone) {
    const overlay = document.getElementById('boot-overlay');
    const host = document.getElementById('boot-lines');
    if (!overlay || !host) { onDone && onDone(); return; }
    let i = 0;
    let finished = false;
    function finish() {
        if (finished) return;
        finished = true;
        overlay.removeEventListener('click', skip);
        overlay.classList.add('gone');
        setTimeout(() => { overlay.style.display = 'none'; onDone && onDone(); }, 800);
    }
    function skip() { finish(); }
    overlay.addEventListener('click', skip);
    const tick = () => {
        if (finished) return;
        if (i < LINES.length) {
            const div = document.createElement('div');
            div.className = 'bl';
            div.textContent = '› ' + LINES[i];
            host.appendChild(div);
            i++;
            setTimeout(tick, 420);
        } else {
            setTimeout(finish, 500);
        }
    };
    tick();
}

window.Boot = { runBoot };
