import * as THREE from 'three';

/**
 * NeuralMap - A Knowledge Graph Visualization for Friday's Memory
 * Visualizes Semantic Memory nodes and their relationships.
 */
class NeuralMap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

        this.nodes = new THREE.Group();
        this.edges = new THREE.Group();
        this.scene.add(this.nodes);
        this.scene.add(this.edges);

        this.init();
    }

    init() {
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        this.camera.position.z = 50;

        // Add some dummy nodes to demonstrate the "Neural Pathway"
        this.generateGraph();
        this.animate();

        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    generateGraph() {
        const nodeCount = 12;
        const geometry = new THREE.SphereGeometry(0.5, 16, 16);
        const material = new THREE.MeshBasicMaterial({ color: 0x2DD4AB });

        const positions = [];

        for (let i = 0; i < nodeCount; i++) {
            const node = new THREE.Mesh(geometry, material);
            const x = (Math.random() - 0.5) * 40;
            const y = (Math.random() - 0.5) * 40;
            const z = (Math.random() - 0.5) * 40;
            node.position.set(x, y, z);
            this.nodes.add(node);
            positions.push(node.position);
        }

        // Connect nodes with lines (Edges)
        const lineMaterial = new THREE.LineBasicMaterial({
            color: 0x2DD4AB,
            transparent: true,
            opacity: 0.2
        });

        for (let i = 0; i < nodeCount; i++) {
            for (let j = i + 1; j < nodeCount; j++) {
                if (Math.random() > 0.8) {
                    const points = [positions[i], positions[j]];
                    const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
                    const line = new THREE.Line(lineGeometry, lineMaterial);
                    this.edges.add(line);
                }
            }
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.nodes.rotation.y += 0.002;
        this.edges.rotation.y += 0.002;

        this.renderer.render(this.scene, this.camera);
    }

    show() {
        this.container.style.display = 'block';
    }

    hide() {
        this.container.style.display = 'none';
    }
}

export default NeuralMap;
