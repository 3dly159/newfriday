import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const BASE_COLOR = '#5cc8ff'; // arc-reactor blue; orb returns here when idle

let scene, camera, renderer, composer, orb, starfield, nebula, bloomPass;

const uniforms = {
    uTime: { value: 0 },
    uVoiceBright: { value: 0.0 },   // 0..~1 audio amplitude while speaking
    uWobble: { value: 0.18 },       // current displacement amplitude (eased)
    uColor: { value: new THREE.Color(BASE_COLOR) },          // orb color (mood)
    uColorTarget: { value: new THREE.Color(BASE_COLOR) },    // eased toward
};

// Background nebula colors are FIXED — they never react to mood.
const nebulaUniforms = {
    uTime: { value: 0 },
    uColor1: { value: new THREE.Color('#0a2a44') },
    uColor2: { value: new THREE.Color('#1b1040') },
};

// State channel: drives wobble energy + bloom, independent of color.
const STATES = {
    idle:      { wobble: 0.16, bloom: 0.9, spin: 0.04 },
    listening: { wobble: 0.28, bloom: 1.2, spin: 0.06 },
    thinking:  { wobble: 0.42, bloom: 1.15, spin: 0.14 },
    speaking:  { wobble: 0.34, bloom: 1.5, spin: 0.08 },
    acting:    { wobble: 0.48, bloom: 1.3, spin: 0.16 },
};
let current = STATES.idle;
let spin = 0.04;

// Classic 3D simplex noise (Ashima) for organic vertex displacement.
const NOISE_GLSL = `
vec4 permute(vec4 x){ return mod(((x*34.0)+1.0)*x, 289.0); }
vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v){
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + 1.0 * C.xxx;
    vec3 x2 = x0 - i2 + 2.0 * C.xxx;
    vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
        i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 1.0/7.0;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}`;

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, innerWidth / innerHeight, 0.1, 1000);
    camera.position.z = 4.2;
    renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('orb-canvas'), antialias: true, alpha: true });
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(devicePixelRatio);

    const starGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(2000 * 3);
    for (let i = 0; i < pos.length; i++) pos[i] = (Math.random() - 0.5) * 20;
    starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    starfield = new THREE.Points(starGeo, new THREE.PointsMaterial({ size: 0.02, color: 0xffffff }));
    scene.add(starfield);

    // Background nebula — fixed colors, never mood-driven.
    const nebulaMat = new THREE.ShaderMaterial({
        uniforms: nebulaUniforms,
        vertexShader: document.getElementById('nebula-vs').textContent,
        fragmentShader: document.getElementById('nebula-fs').textContent,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    nebula = new THREE.Mesh(new THREE.PlaneGeometry(24, 24), nebulaMat);
    nebula.position.z = -3; scene.add(nebula);

    // The energy-ball orb: a high-res sphere displaced by layered 3D noise so
    // its surface ripples in and out — "not quite a ball", wobbly.
    const orbMat = new THREE.ShaderMaterial({
        uniforms,
        transparent: true,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
        depthWrite: false,
        vertexShader: `
            uniform float uTime; uniform float uWobble; uniform float uVoiceBright;
            varying vec3 vNormal; varying float vDisp;
            ${NOISE_GLSL}
            void main(){
                float amp = uWobble + uVoiceBright * 0.35;
                // Two octaves of moving noise for a roiling, liquid-energy feel.
                float n = snoise(normal * 1.6 + vec3(uTime * 0.6));
                n += 0.5 * snoise(normal * 3.2 - vec3(uTime * 0.9));
                float disp = n * amp;
                vDisp = disp;
                vec3 p = position + normal * disp;
                vNormal = normalize(normalMatrix * normal);
                gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
            }`,
        fragmentShader: `
            uniform float uTime; uniform float uVoiceBright; uniform vec3 uColor;
            varying vec3 vNormal; varying float vDisp;
            void main(){
                float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.2);
                // Brighter where the surface bulges; darker in the troughs -> inner glow.
                float energy = 0.55 + vDisp * 1.6;
                float pulse = sin(uTime * 2.0) * 0.08 + 0.92;
                vec3 col = uColor * energy;
                float alpha = (fresnel + 0.25) * (uVoiceBright * 1.5 + 0.7) * pulse;
                gl_FragColor = vec4(col, clamp(alpha, 0.0, 1.0));
            }`,
    });
    orb = new THREE.Mesh(new THREE.IcosahedronGeometry(1, 32), orbMat);
    scene.add(orb);

    bloomPass = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 1.4, 0.5, 0.1);
    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(bloomPass);

    addEventListener('resize', onResize);
    animate();
}

function onResize() {
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
}

let focused = true;
addEventListener('focus', () => focused = true);
addEventListener('blur', () => focused = false);

function animate() {
    requestAnimationFrame(animate);
    if (!focused && Math.random() > 0.15) return;
    uniforms.uTime.value += 0.01;
    nebulaUniforms.uTime.value += 0.01;
    starfield.rotation.y += 0.0005;

    // Ease wobble + spin toward the current state's target.
    uniforms.uWobble.value += (current.wobble - uniforms.uWobble.value) * 0.05;
    spin += (current.spin - spin) * 0.05;
    orb.rotation.y += spin * 0.05;
    orb.rotation.x += spin * 0.02;

    // Ease orb color toward its target (smooth mood transitions / reset to blue).
    uniforms.uColor.value.lerp(uniforms.uColorTarget.value, 0.06);

    bloomPass.strength = 1.4 * current.bloom;
    composer.render();
}

init();

// Public API consumed by app.js
window.Orb = {
    setVoiceBright: (v) => { uniforms.uVoiceBright.value = v; },
    setState: (name) => { current = STATES[name] || STATES.idle; },
    // Orb color changes only on mood; pass a hex. Nebula/background is untouched.
    setColor: (hex) => { uniforms.uColorTarget.value.set(hex || BASE_COLOR); },
    // Reset to arc-reactor blue when Friday is done.
    resetColor: () => { uniforms.uColorTarget.value.set(BASE_COLOR); },
    BASE_COLOR,
};
