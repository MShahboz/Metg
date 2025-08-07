import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Loading Manager
const loadingManager = new THREE.LoadingManager();
const loadingScreen = document.getElementById('loading-screen');
const ambientMusic = document.getElementById('ambient-music');

function startExperience() {
    // Fade out the loading screen
    loadingScreen.style.transition = 'opacity 1s';
    loadingScreen.style.opacity = 0;

    // Remove the loading screen from the DOM after the transition
    setTimeout(() => {
        loadingScreen.remove();
    }, 1000);

    // Add a one-time event listener to play music on the first interaction
    const playMusic = () => {
        ambientMusic.play().catch(error => console.error("Audio play failed:", error));
        window.removeEventListener('pointerdown', playMusic);
    };
    window.addEventListener('pointerdown', playMusic);
}

loadingManager.onLoad = startExperience;

// Scene
const scene = new THREE.Scene();

// Camera
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 0.1;

// Renderer
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableZoom = false;
controls.enablePan = false;
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.rotateSpeed = -0.25; // Invert rotation for a more natural feel

// Create a sphere to be our skybox
const geometry = new THREE.SphereGeometry(500, 60, 40);
geometry.scale(-1, 1, 1); // Invert the sphere normals to see the texture from the inside

// Load the texture
const textureLoader = new THREE.TextureLoader(loadingManager); // Pass the manager
const texture = textureLoader.load('assets/milky_way.jpg');

// Create the material
const material = new THREE.MeshBasicMaterial({
    map: texture
});

// Create the mesh
const skybox = new THREE.Mesh(geometry, material);
scene.add(skybox);

// Animation loop
function animate() {
    requestAnimationFrame(animate);

    // required if controls.enableDamping is set to true
    controls.update();

    renderer.render(scene, camera);
}

animate();

// Handle window resizing
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
