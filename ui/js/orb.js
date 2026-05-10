import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

let scene, camera, renderer, composer, orb, starfield;
let uniforms = {
    uTime: { value: 0 },
    uVoiceBright: { value: 0.0 }
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

    // Orb
    const geometry = new THREE.SphereGeometry(1, 64, 64);
    const material = new THREE.ShaderMaterial({
        uniforms: uniforms,
        vertexShader: `
            varying vec2 vUv;
            void main() {
                vUv = uv;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
        `,
        fragmentShader: `
            uniform float uTime;
            uniform float uVoiceBright;
            varying vec2 vUv;

            void main() {
                float distance = length(vUv - 0.5);
                // Gentle idle pulse (sine over ~4s)
                float idlePulse = sin(uTime * 1.5) * 0.05 + 0.95;
                // Voice intensification
                float brightness = (uVoiceBright * 2.5 + idlePulse);

                vec3 color = vec3(0.176, 0.831, 0.671); // #2DD4AB
                float alpha = smoothstep(0.5, 0.1, distance) * brightness;

                gl_FragColor = vec4(color, alpha);
            }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending
    });
    orb = new THREE.Mesh(geometry, material);
    scene.add(orb);

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
    composer.render();
}

init();

// Export for external control (Phase 2 integration)
window.setVoiceBright = (val) => {
    uniforms.uVoiceBright.value = val;
};
