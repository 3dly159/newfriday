import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const ACCENT = 0x5cc8ff;
const HUB = 0x8b5cf6;
const ROOT = 0x7cf5d5;

// Human-readable descriptions of each memory layer (the 7-layer architecture).
const LAYER_DESC = {
    bio: 'Persistent facts about you — name, preferences, identity.',
    lore: 'Friday backstory & ARG narrative state (unlocked flags).',
    skill: 'Learned tools and installed Clawhub skill manifests.',
    script: 'History of executed scripts and their outcomes.',
    social: 'Relationship metrics — trust level and banter score.',
    task: 'Current goals, quests, and the proactive queue.',
    episodic: 'Recent conversation turns (rolling session memory).',
    internal_monologue: "Friday's private proactive thoughts.",
};

let scene, camera, renderer, controls, composer, graph;
let raycaster, pointer;
const clickable = []; // meshes carrying .userData.detail

function makeLabel(text, scale = 1) {
    const canvas = document.createElement('canvas');
    canvas.width = 256; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.font = '600 26px Inter, sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.92)';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 128, 34);
    const tex = new THREE.CanvasTexture(canvas);
    const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    spr.scale.set(2.4 * scale, 0.6 * scale, 1);
    return spr;
}

function node(radius, color, pos, detail) {
    const m = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 24, 24),
        new THREE.MeshBasicMaterial({ color })
    );
    m.position.copy(pos);
    if (detail) { m.userData.detail = detail; clickable.push(m); }
    return m;
}

function edge(a, b, opacity) {
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    return new THREE.Line(g, new THREE.LineBasicMaterial({ color: ACCENT, transparent: true, opacity }));
}

// Turn a memory layer value into [{label, detail}] leaf descriptors carrying real content.
function leavesFor(layer, value) {
    const out = [];
    if (Array.isArray(value)) {
        value.slice(-8).forEach((v, i) => {
            if (v && typeof v === 'object') {
                const label = v.name || v.title || v.role || `${layer} ${i}`;
                out.push({ label: String(label).slice(0, 20), detail: { kind: layer + ' item', title: String(label), data: v } });
            } else {
                out.push({ label: String(v).slice(0, 20), detail: { kind: layer + ' item', title: String(v).slice(0, 60), data: v } });
            }
        });
    } else if (value && typeof value === 'object') {
        Object.keys(value).slice(0, 8).forEach(k => {
            out.push({ label: k.slice(0, 20), detail: { kind: layer + ' field', title: k, data: value[k] } });
        });
    }
    return out;
}

function buildGraph(memory) {
    graph = new THREE.Group();
    const center = new THREE.Vector3(0, 0, 0);
    const layers = Object.keys(memory || {});
    const fallback = ['bio', 'lore', 'skill', 'script', 'social', 'task', 'episodic'];
    const keys = layers.length ? layers : fallback;

    graph.add(node(1.1, ROOT, center, {
        kind: 'core', title: 'FRIDAY',
        data: { layers: keys, note: 'The 7-layer cognitive memory. Click a hub to inspect a layer.' },
    }));
    const title = makeLabel('FRIDAY', 1.4); title.position.set(0, 1.8, 0); graph.add(title);

    keys.forEach((layer, li) => {
        const phi = Math.acos(-1 + (2 * li) / Math.max(keys.length, 1));
        const theta = Math.sqrt(keys.length * Math.PI) * phi;
        const r = 6;
        const hubPos = new THREE.Vector3(
            r * Math.cos(theta) * Math.sin(phi),
            r * Math.sin(theta) * Math.sin(phi),
            r * Math.cos(phi)
        );
        const value = memory ? memory[layer] : null;
        const count = Array.isArray(value) ? value.length
            : (value && typeof value === 'object' ? Object.keys(value).length : 0);
        graph.add(node(0.55, HUB, hubPos, {
            kind: 'memory layer', title: layer,
            data: { description: LAYER_DESC[layer] || 'Memory layer.', entries: count, value },
        }));
        graph.add(edge(center, hubPos, 0.35));
        const lbl = makeLabel(layer.toUpperCase()); lbl.position.copy(hubPos).add(new THREE.Vector3(0, 0.9, 0));
        graph.add(lbl);

        const leaves = leavesFor(layer, value);
        leaves.forEach((leaf, i) => {
            const a = (i / Math.max(leaves.length, 1)) * Math.PI * 2;
            const lp = hubPos.clone().add(new THREE.Vector3(Math.cos(a) * 2.2, Math.sin(a) * 2.2, (Math.random() - 0.5) * 1.5));
            graph.add(node(0.2, ACCENT, lp, leaf.detail));
            graph.add(edge(hubPos, lp, 0.18));
        });
    });

    scene.add(graph);
}

// --- Detail panel ---
function fmtValue(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'object') {
        try { return JSON.stringify(v, null, 2); } catch (e) { return String(v); }
    }
    return String(v);
}

function showDetail(detail) {
    const panel = document.getElementById('neural-detail');
    document.getElementById('nd-kind').textContent = (detail.kind || 'node').toUpperCase();
    document.getElementById('nd-title').textContent = detail.title || '—';
    const body = document.getElementById('nd-body');
    body.innerHTML = '';
    const data = detail.data;
    if (data && typeof data === 'object' && !Array.isArray(data)) {
        Object.keys(data).forEach(k => {
            const row = document.createElement('div');
            row.className = 'nd-row';
            const val = data[k];
            if (val && typeof val === 'object') {
                row.innerHTML = `<b>${k}</b>`;
                const pre = document.createElement('pre');
                pre.textContent = fmtValue(val);
                row.appendChild(pre);
            } else {
                row.innerHTML = `<b>${k}</b> ${escapeHtml(String(val))}`;
            }
            body.appendChild(row);
        });
    } else {
        const pre = document.createElement('pre');
        pre.textContent = fmtValue(data);
        body.appendChild(pre);
    }
    panel.classList.add('open');
}

function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function onClick(ev) {
    pointer.x = (ev.clientX / innerWidth) * 2 - 1;
    pointer.y = -(ev.clientY / innerHeight) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(clickable, false);
    if (hits.length) showDetail(hits[0].object.userData.detail);
}

async function loadMemory() {
    try {
        const cfg = await (await fetch('/api/config')).json();
        return cfg.system_memory || null;
    } catch (e) {
        return null;
    }
}

async function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 1000);
    camera.position.set(0, 0, 20);
    renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('neural-canvas'), antialias: true, alpha: true });
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(devicePixelRatio);

    const starGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(1500 * 3);
    for (let i = 0; i < pos.length; i++) pos[i] = (Math.random() - 0.5) * 80;
    starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ size: 0.08, color: 0xffffff, transparent: true, opacity: 0.5 })));

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.6;

    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 1.1, 0.6, 0.1));

    raycaster = new THREE.Raycaster();
    pointer = new THREE.Vector2();
    // Pause auto-rotate while interacting so clicking is easy.
    controls.addEventListener('start', () => { controls.autoRotate = false; });
    renderer.domElement.addEventListener('click', onClick);
    document.getElementById('nd-close').addEventListener('click', () =>
        document.getElementById('neural-detail').classList.remove('open'));

    buildGraph(await loadMemory());

    addEventListener('resize', () => {
        camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
        renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
    });
    animate();
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    composer.render();
}

init();
