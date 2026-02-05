/**
 * GENESIS v3 ParticleSystem
 *
 * Ethereal ambient particles inspired by 超かぐや姫 (Super Kaguya-hime).
 * Two layers of particles:
 *   1. Luminescent floating dust / fireflies — 800 points with additive blending
 *   2. Cherry blossom petals — 200 gently falling pink/white sprites
 *
 * All particles loop seamlessly and are fully GPU-driven via custom shaders.
 */
import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FIREFLY_COUNT = 800;
const PETAL_COUNT = 200;

/** Spread of the particle volume (centered at origin) */
const WORLD_HALF = 100;
const WORLD_HEIGHT = 60;

// Pre-defined palette for fireflies: blue, purple, cyan, amber
const FIREFLY_PALETTE = [
  new THREE.Color(0x4fc3f7), // blue
  new THREE.Color(0xb388ff), // purple
  new THREE.Color(0x80deea), // cyan
  new THREE.Color(0xffe082), // amber
];

// ---------------------------------------------------------------------------
// Firefly shaders
// ---------------------------------------------------------------------------

const fireflyVertexShader = /* glsl */ `
  attribute float aSize;
  attribute vec3 aColor;
  attribute float aPhase;

  uniform float uTime;
  uniform float uPixelRatio;

  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vColor = aColor;

    // Pulse alpha
    float pulse = sin(uTime * 1.5 + aPhase * 6.2831) * 0.5 + 0.5;
    vAlpha = 0.3 + pulse * 0.7;

    // Animate position: gentle drift
    vec3 pos = position;
    float t = uTime * 0.15;
    pos.x += sin(t + aPhase * 12.0) * 1.5;
    pos.y += cos(t * 0.8 + aPhase * 8.0) * 0.8 + uTime * 0.05;
    pos.z += cos(t * 0.6 + aPhase * 10.0) * 1.5;

    // Wrap Y back into range [-2, WORLD_HEIGHT]
    pos.y = mod(pos.y + 2.0, ${(WORLD_HEIGHT + 2).toFixed(1)}) - 2.0;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = aSize * uPixelRatio * (180.0 / -mvPosition.z);
    gl_PointSize = clamp(gl_PointSize, 1.0, 40.0);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fireflyFragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    // Soft circle with glow falloff
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    float strength = 1.0 - dist * 2.0;
    strength = pow(strength, 1.5);

    gl_FragColor = vec4(vColor * strength, strength * vAlpha);
  }
`;

// ---------------------------------------------------------------------------
// Petal shaders
// ---------------------------------------------------------------------------

const petalVertexShader = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute float aPink;     // 0.0 = white, 1.0 = pink

  uniform float uTime;
  uniform float uPixelRatio;

  varying float vPink;
  varying float vAlpha;

  void main() {
    vPink = aPink;

    // Gentle sway
    vec3 pos = position;
    float t = uTime * 0.2;
    pos.x += sin(t + aPhase * 15.0) * 2.0;
    pos.z += cos(t * 0.7 + aPhase * 12.0) * 2.0;
    // Falling
    pos.y -= uTime * 0.3 * (0.5 + aPhase * 0.5);
    pos.y += sin(t * 1.3 + aPhase * 9.0) * 0.5; // flutter

    // Wrap Y: reset above when fallen below ground
    float range = ${(WORLD_HEIGHT + 5).toFixed(1)};
    pos.y = mod(pos.y + 2.0, range) - 2.0;

    vAlpha = 0.5 + 0.3 * sin(uTime * 0.8 + aPhase * 6.0);

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = aSize * uPixelRatio * (120.0 / -mvPosition.z);
    gl_PointSize = clamp(gl_PointSize, 1.0, 24.0);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const petalFragmentShader = /* glsl */ `
  varying float vPink;
  varying float vAlpha;

  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    float strength = 1.0 - dist * 2.0;
    strength = pow(strength, 1.0);

    // Pink / white gradient
    vec3 pink = vec3(1.0, 0.7, 0.78);
    vec3 white = vec3(1.0, 0.95, 0.96);
    vec3 color = mix(white, pink, vPink);

    gl_FragColor = vec4(color * strength, strength * vAlpha * 0.6);
  }
`;

// ---------------------------------------------------------------------------
// ParticleSystem class
// ---------------------------------------------------------------------------

export class ParticleSystem {
  private fireflyPoints: THREE.Points;
  private fireflyMaterial: THREE.ShaderMaterial;

  private petalPoints: THREE.Points;
  private petalMaterial: THREE.ShaderMaterial;

  private scene: THREE.Scene;

  constructor(scene: THREE.Scene) {
    this.scene = scene;

    // ---- Fireflies ----
    const ffGeometry = new THREE.BufferGeometry();
    const ffPositions = new Float32Array(FIREFLY_COUNT * 3);
    const ffSizes = new Float32Array(FIREFLY_COUNT);
    const ffColors = new Float32Array(FIREFLY_COUNT * 3);
    const ffPhases = new Float32Array(FIREFLY_COUNT);

    for (let i = 0; i < FIREFLY_COUNT; i++) {
      ffPositions[i * 3] = (Math.random() - 0.5) * WORLD_HALF * 2;
      ffPositions[i * 3 + 1] = Math.random() * WORLD_HEIGHT - 2;
      ffPositions[i * 3 + 2] = (Math.random() - 0.5) * WORLD_HALF * 2;

      ffSizes[i] = 0.2 + Math.random() * 0.3;
      ffPhases[i] = Math.random();

      const color = FIREFLY_PALETTE[Math.floor(Math.random() * FIREFLY_PALETTE.length)];
      ffColors[i * 3] = color.r;
      ffColors[i * 3 + 1] = color.g;
      ffColors[i * 3 + 2] = color.b;
    }

    ffGeometry.setAttribute('position', new THREE.BufferAttribute(ffPositions, 3));
    ffGeometry.setAttribute('aSize', new THREE.BufferAttribute(ffSizes, 1));
    ffGeometry.setAttribute('aColor', new THREE.BufferAttribute(ffColors, 3));
    ffGeometry.setAttribute('aPhase', new THREE.BufferAttribute(ffPhases, 1));

    this.fireflyMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      },
      vertexShader: fireflyVertexShader,
      fragmentShader: fireflyFragmentShader,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    this.fireflyPoints = new THREE.Points(ffGeometry, this.fireflyMaterial);
    this.fireflyPoints.frustumCulled = false;
    // Layer 1 so raycaster on default layer 0 ignores particles
    this.fireflyPoints.layers.set(1);
    this.scene.add(this.fireflyPoints);

    // ---- Cherry blossom petals ----
    const ptGeometry = new THREE.BufferGeometry();
    const ptPositions = new Float32Array(PETAL_COUNT * 3);
    const ptSizes = new Float32Array(PETAL_COUNT);
    const ptPhases = new Float32Array(PETAL_COUNT);
    const ptPinks = new Float32Array(PETAL_COUNT);

    for (let i = 0; i < PETAL_COUNT; i++) {
      ptPositions[i * 3] = (Math.random() - 0.5) * WORLD_HALF * 2;
      ptPositions[i * 3 + 1] = Math.random() * WORLD_HEIGHT - 2;
      ptPositions[i * 3 + 2] = (Math.random() - 0.5) * WORLD_HALF * 2;

      ptSizes[i] = 0.3 + Math.random() * 0.4;
      ptPhases[i] = Math.random();
      ptPinks[i] = Math.random(); // 0 = white, 1 = pink
    }

    ptGeometry.setAttribute('position', new THREE.BufferAttribute(ptPositions, 3));
    ptGeometry.setAttribute('aSize', new THREE.BufferAttribute(ptSizes, 1));
    ptGeometry.setAttribute('aPhase', new THREE.BufferAttribute(ptPhases, 1));
    ptGeometry.setAttribute('aPink', new THREE.BufferAttribute(ptPinks, 1));

    this.petalMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      },
      vertexShader: petalVertexShader,
      fragmentShader: petalFragmentShader,
      transparent: true,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    this.petalPoints = new THREE.Points(ptGeometry, this.petalMaterial);
    this.petalPoints.frustumCulled = false;
    this.petalPoints.layers.set(1);
    this.scene.add(this.petalPoints);
  }

  /**
   * Update particles each frame.
   * @param time - elapsed time in seconds
   */
  update(time: number): void {
    this.fireflyMaterial.uniforms.uTime.value = time;
    this.petalMaterial.uniforms.uTime.value = time;
  }

  dispose(): void {
    this.scene.remove(this.fireflyPoints);
    this.fireflyPoints.geometry.dispose();
    this.fireflyMaterial.dispose();

    this.scene.remove(this.petalPoints);
    this.petalPoints.geometry.dispose();
    this.petalMaterial.dispose();
  }
}
