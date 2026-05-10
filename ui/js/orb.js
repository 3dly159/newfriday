import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

let scene, camera, renderer, composer, orb, starfield, nebula;
let rings = [];
let uniforms = {
    uTime: { value: 0 },
    uVoiceBright: { value: 0.0 },
    uColor1: { value: new THREE.Color("#2DD4AB") },
    uColor2: { value: new THREE.Color("#8B5CF6") }
};

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({
        canvas: document.getElementById('orb-canvas'),
        antialias: true,
        alpha: true
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Starfield
    const starGeometry = new THREE.BufferGeometry();
    const starCount = 2000;
    const posArray = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 20;
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const starMaterial = new THREE.PointsMaterial({ size: 0.02, color: 0xffffff });
    starfield = new THREE.Points(starGeometry, starMaterial);
    scene.add(starfield);

    // Nebula
    const nebulaGeo = new THREE.PlaneGeometry(20, 20);
    const nebulaMat = new THREE.ShaderMaterial({
        uniforms: uniforms,
        vertexShader: document.getElementById('nebula-vs').textContent,
        fragmentShader: document.getElementById('nebula-fs').textContent,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending
    });
    nebula = new THREE.Mesh(nebulaGeo, nebulaMat);
    nebula.position.z = -2;
    scene.add(nebula);

    // JARVIS Orb (Multi-layered holographic core)
    const geometry = new THREE.SphereGeometry(1, 64, 64);
    const material = new THREE.ShaderMaterial({
        uniforms: uniforms,
        vertexShader: `
            varying vec3 vNormal;
            varying vec3 vPosition;
            void main() {
                vNormal = normalize(normalMatrix * normal);
                vPosition = position;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
        `,
        fragmentShader: `
            uniform float uTime;
            uniform float uVoiceBright;
            uniform vec3 uColor1;
            varying vec3 vNormal;
            varying vec3 vPosition;

            void main() {
                float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
                float scanline = sin(vPosition.y * 50.0 - uTime * 10.0) * 0.1 + 0.9;
                float pulse = sin(uTime * 2.0) * 0.1 + 0.9;

                vec3 color = uColor1;
                float alpha = (fresnel + 0.2) * (uVoiceBright * 2.0 + 0.5) * scanline * pulse;

                gl_FragColor = vec4(color, alpha);
            }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide
    });
    orb = new THREE.Mesh(geometry, material);
    scene.add(orb);

    // Rotating Rings (JARVIS style)
    const ringData = [
        { radius: 1.2, speed: 0.5, axis: 'z', thick: 0.02 },
        { radius: 1.4, speed: -0.3, axis: 'y', thick: 0.01 },
        { radius: 1.6, speed: 0.8, axis: 'x', thick: 0.015 }
    ];

    ringData.forEach(data => {
        const ringGeo = new THREE.TorusGeometry(data.radius, data.thick, 16, 100);
        const ringMat = new THREE.MeshBasicMaterial({
            color: uniforms.uColor1.value,
            transparent: true,
            opacity: 0.4,
            blending: THREE.AdditiveBlending
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        rings.push({ mesh: ring, speed: data.speed, axis: data.axis });
        scene.add(ring);
    });

    // Post-processing
    const renderScene = new RenderPass(scene, camera);
    const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(window.innerWidth, window.innerHeight),
        1.5, 0.4, 0.1
    );
    composer = new EffectComposer(renderer);
    composer.addPass(renderScene);
    composer.addPass(bloomPass);

    window.addEventListener('resize', onWindowResize);
    animate();
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    composer.setSize(window.innerWidth, window.innerHeight);
}

// Eco-mode state
let isWindowFocused = true;
window.addEventListener('focus', () => isWindowFocused = true);
window.addEventListener('blur', () => isWindowFocused = false);

function animate() {
    requestAnimationFrame(animate);

    // Eco-mode: Skip frames if window is blurred to save GPU (limit to ~10 FPS)
    if (!isWindowFocused && Math.random() > 0.15) return;

    uniforms.uTime.value += 0.01;
    starfield.rotation.y += 0.0005;

    rings.forEach(r => {
        r.mesh.rotation[r.axis] += r.speed * 0.02;
        // React to voice
        const scale = 1 + uniforms.uVoiceBright.value * 0.2;
        r.mesh.scale.set(scale, scale, scale);
    });
    composer.render();
}

init();

// Export for external control (Phase 2 integration)
window.setVoiceBright = (val) => {
    uniforms.uVoiceBright.value = val;
};

window.setOrbColor = (hex) => {
    const color = new THREE.Color(hex);
    uniforms.uColor1.value.copy(color);
    // Auto-derive a complementary for the nebula
    uniforms.uColor2.value.setHSL((color.getHSL({}).h + 0.5) % 1, 0.8, 0.5);
};
