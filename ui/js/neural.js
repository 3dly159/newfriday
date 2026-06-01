import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const ACCENT = 0x5cc8ff;
const HUB = 0x8b5cf6;

let scene, camera, renderer, controls, composer, graph;

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

function node(radius, color, pos) {
    const m = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 24, 24),
        new THREE.MeshBasicMaterial({ color })
    );
    m.position.copy(pos);
    return m;
}

function edge(a, b, opacity) {
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    return new THREE.Line(g, new THREE.LineBasicMaterial({ color: ACCENT, transparent: true, opacity }));
}

function summarize(layer, value) {
    // Produce a short list of leaf labels for a memory layer.
    if (Array.isArray(value)) {
        return value.slice(-6).map((v, i) => {
            if (v && typeof v === 'object') return v.name || v.role || v.title || `${layer} ${i}`;
            return String(v).slice(0, 18);
        });
    }
    if (value && typeof value === 'object') {
        return Object.keys(value).slice(0, 6).map(k => k.slice(0, 18));
    }
    return [];
}

function buildGraph(memory) {
    graph = new THREE.Group();
    const center = new THREE.Vector3(0, 0, 0);
    graph.add(node(1.1, ACCENT, center));
    const title = makeLabel('FRIDAY', 1.4); title.position.set(0, 1.8, 0); graph.add(title);

    const layers = Object.keys(memory || {}).filter(k => k !== 'internal_monologue');
    const fallback = ['bio', 'lore', 'skill', 'script', 'social', 'task', 'episodic'];
    const keys = layers.length ? layers : fallback;

    keys.forEach((layer, li) => {
        const phi = Math.acos(-1 + (2 * li) / Math.max(keys.length, 1));
        const theta = Math.sqrt(keys.length * Math.PI) * phi;
        const r = 6;
        const hubPos = new THREE.Vector3(
            r * Math.cos(theta) * Math.sin(phi),
            r * Math.sin(theta) * Math.sin(phi),
            r * Math.cos(phi)
        );
        graph.add(node(0.55, HUB, hubPos));
        graph.add(edge(center, hubPos, 0.35));
        const lbl = makeLabel(layer.toUpperCase()); lbl.position.copy(hubPos).add(new THREE.Vector3(0, 0.9, 0));
        graph.add(lbl);

        const leaves = summarize(layer, memory ? memory[layer] : null);
        leaves.forEach((leaf, i) => {
            const a = (i / Math.max(leaves.length, 1)) * Math.PI * 2;
            const lp = hubPos.clone().add(new THREE.Vector3(Math.cos(a) * 2.2, Math.sin(a) * 2.2, (Math.random() - 0.5) * 1.5));
            graph.add(node(0.18, ACCENT, lp));
            graph.add(edge(hubPos, lp, 0.18));
        });
    });

    scene.add(graph);
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
