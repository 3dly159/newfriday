import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

let scene, camera, renderer, composer, orb, starfield, nebula;
let rings = [];
const uniforms = {
    uTime: { value: 0 },
    uVoiceBright: { value: 0.0 },
    uColor1: { value: new THREE.Color('#5cc8ff') },
    uColor2: { value: new THREE.Color('#8B5CF6') },
};

const STATES = {
    idle:      { spin: 0.4, pulse: 1.0, bloom: 1.0 },
    listening: { spin: 0.8, pulse: 1.4, bloom: 1.3 },
    thinking:  { spin: 2.2, pulse: 1.1, bloom: 1.2 },
    speaking:  { spin: 1.0, pulse: 1.2, bloom: 1.6 },
    acting:    { spin: 2.6, pulse: 1.3, bloom: 1.4 },
};
let current = STATES.idle;
let bloomPass;

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, innerWidth / innerHeight, 0.1, 1000);
    camera.position.z = 5;
    renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('orb-canvas'), antialias: true, alpha: true });
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(devicePixelRatio);

    const starGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(2000 * 3);
    for (let i = 0; i < pos.length; i++) pos[i] = (Math.random() - 0.5) * 20;
    starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    starfield = new THREE.Points(starGeo, new THREE.PointsMaterial({ size: 0.02, color: 0xffffff }));
    scene.add(starfield);

    const nebulaMat = new THREE.ShaderMaterial({
        uniforms, vertexShader: document.getElementById('nebula-vs').textContent,
        fragmentShader: document.getElementById('nebula-fs').textContent,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    nebula = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), nebulaMat);
    nebula.position.z = -2; scene.add(nebula);

    const coreMat = new THREE.ShaderMaterial({
        uniforms,
        vertexShader: `varying vec3 vNormal; varying vec3 vPosition;
            void main(){ vNormal=normalize(normalMatrix*normal); vPosition=position;
            gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
        fragmentShader: `uniform float uTime; uniform float uVoiceBright; uniform vec3 uColor1;
            varying vec3 vNormal; varying vec3 vPosition;
            void main(){
                float fresnel=pow(1.0-dot(vNormal,vec3(0.0,0.0,1.0)),3.0);
                float scan=sin(vPosition.y*50.0-uTime*10.0)*0.1+0.9;
                float pulse=sin(uTime*2.0)*0.1+0.9;
                float alpha=(fresnel+0.2)*(uVoiceBright*2.0+0.5)*scan*pulse;
                gl_FragColor=vec4(uColor1, alpha);
            }`,
        transparent: true, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    });
    orb = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), coreMat);
    scene.add(orb);

    [{ r: 1.2, s: 0.5, a: 'z', t: 0.02 }, { r: 1.4, s: -0.3, a: 'y', t: 0.01 }, { r: 1.6, s: 0.8, a: 'x', t: 0.015 }]
      .forEach(d => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(d.r, d.t, 16, 100),
            new THREE.MeshBasicMaterial({ color: uniforms.uColor1.value, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending }));
        rings.push({ mesh: ring, speed: d.s, axis: d.a }); scene.add(ring);
      });

    bloomPass = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 1.5, 0.4, 0.1);
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
    starfield.rotation.y += 0.0005;
    bloomPass.strength = 1.5 * current.bloom;
    rings.forEach(r => {
        r.mesh.rotation[r.axis] += r.speed * 0.02 * current.spin;
        const scale = 1 + uniforms.uVoiceBright.value * 0.2;
        r.mesh.scale.set(scale, scale, scale);
        r.mesh.material.color.copy(uniforms.uColor1.value);
    });
    composer.render();
}
init();

window.Orb = {
    setVoiceBright: (v) => { uniforms.uVoiceBright.value = v; },
    setState: (name) => { current = STATES[name] || STATES.idle; },
    setColor: (hex) => {
        const c = new THREE.Color(hex);
        uniforms.uColor1.value.copy(c);
        const hsl = {}; c.getHSL(hsl);
        uniforms.uColor2.value.setHSL((hsl.h + 0.5) % 1, 0.8, 0.5);
        document.documentElement.style.setProperty('--accent', hex);
    },
};
window.setVoiceBright = (v) => window.Orb.setVoiceBright(v);
window.setOrbColor = (hex) => window.Orb.setColor(hex);
