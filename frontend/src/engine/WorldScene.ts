/**
 * GENESIS v3 WorldScene — WebGPU
 *
 * 「超かぐや姫」インスパイアの美しい3Dボクセルワールド
 * WebGPUで高パフォーマンスレンダリング
 * Post-processing bloom and aurora borealis effects
 */
import * as THREE from 'three';
// @ts-ignore - Three.js WebGPU types not fully exposed
import { WebGPURenderer } from 'three/webgpu';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { VoxelRenderer } from './VoxelRenderer';
import { AvatarSystem } from './AvatarSystem';
import { CameraController, type CameraMode } from './Camera';
import { BuildingTool, type BuildMode } from './BuildingTool';
import { VoxelTemplates } from './VoxelTemplates';
import type {
  EntityV3, Voxel, VoxelUpdate, StructureInfo,
  ActionProposal, SocketEntityPosition,
  SocketSpeechEvent,
} from '../types/v3';

export interface WorldSceneOptions {
  canvas: HTMLCanvasElement;
  labelContainer: HTMLElement;
  onProposal?: (proposal: ActionProposal) => void;
  onEntityClick?: (entityId: string) => void;
}

export class WorldScene {
  private renderer!: WebGPURenderer | THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;
  private canvas: HTMLCanvasElement;
  private isWebGPU = false;

  // Post-processing
  private composer: EffectComposer | null = null;
  private bloomPass: UnrealBloomPass | null = null;

  // Subsystems
  voxelRenderer!: VoxelRenderer;
  avatarSystem!: AvatarSystem;
  cameraController!: CameraController;
  buildingTool!: BuildingTool;

  // Visual elements
  private waterPlane: THREE.Mesh | null = null;
  private floatingLanterns: THREE.Group | null = null;
  private particles: THREE.Points | null = null;
  private skyMesh: THREE.Mesh | null = null;

  // State
  private animationFrameId: number | null = null;
  private mouseNDC = new THREE.Vector2();
  private raycaster = new THREE.Raycaster();
  private onEntityClick: ((entityId: string) => void) | null = null;
  private resizeObserver: ResizeObserver | null = null;

  // Touch
  private touchStartPos: { x: number; y: number } | null = null;
  private touchStartTime = 0;

  // Template loaded flag
  private templateLoaded = false;
  private initialized = false;

  // Callbacks stored for init
  private labelContainer: HTMLElement;
  private onProposalCallback: ((proposal: ActionProposal) => void) | undefined;

  constructor(options: WorldSceneOptions) {
    const { canvas, labelContainer, onProposal, onEntityClick } = options;
    this.canvas = canvas;
    this.labelContainer = labelContainer;
    this.onProposalCallback = onProposal;
    this.onEntityClick = onEntityClick || null;

    console.log('[WorldScene] 初期化開始...');

    // === Scene ===
    this.scene = new THREE.Scene();
    this.clock = new THREE.Clock();

    // === Camera ===
    this.camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      500,
    );
    this.camera.position.set(0, 15, 45);
    this.camera.lookAt(0, 0, 0);

    // Initialize (async)
    this.initRenderer();
  }

  private async initRenderer(): Promise<void> {
    try {
      // WebGPUを試行
      if ('gpu' in navigator) {
        console.log('[WorldScene] WebGPU利用可能、初期化中...');
        const webgpuRenderer = new WebGPURenderer({
          canvas: this.canvas,
          antialias: true,
        });
        await webgpuRenderer.init();
        this.renderer = webgpuRenderer;
        this.isWebGPU = true;
        console.log('[WorldScene] ✓ WebGPUレンダラー初期化完了');
      } else {
        throw new Error('WebGPU not available');
      }
    } catch (e) {
      console.log('[WorldScene] WebGPU利用不可、WebGLにフォールバック:', e);
      this.renderer = new THREE.WebGLRenderer({
        canvas: this.canvas,
        antialias: true,
      });
      this.isWebGPU = false;
    }

    // Renderer settings
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);

    if (!this.isWebGPU && this.renderer instanceof THREE.WebGLRenderer) {
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.2;
    }

    // Setup post-processing (WebGL only for now, WebGPU has different post-processing)
    this.setupPostProcessing();

    // 美しいグラデーション空 with aurora
    this.createGradientSkyWithAurora();

    // 幻想的な霧
    this.scene.fog = new THREE.FogExp2(0x1a0a2e, 0.008);

    // Lighting
    this.setupLighting();

    // Water with luminous cyan glow
    this.createLuminousWater();

    // Floating Lanterns
    this.createFloatingLanterns();

    // Particles
    this.createParticles();

    // === Subsystems ===
    this.voxelRenderer = new VoxelRenderer(this.scene);
    this.avatarSystem = new AvatarSystem(this.scene);
    this.avatarSystem.setLabelContainer(this.labelContainer);
    this.cameraController = new CameraController(this.camera);
    this.cameraController.attach(this.canvas);
    this.buildingTool = new BuildingTool(this.scene, this.camera, this.voxelRenderer);

    if (this.onProposalCallback) {
      this.buildingTool.setProposalCallback(this.onProposalCallback);
    }

    // Load template
    this.loadInitialTemplate();

    // Events
    this.canvas.addEventListener('mousemove', this.onMouseMove);
    this.canvas.addEventListener('click', this.onClick);
    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('resize', this.onResize);
    this.canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    this.canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });

    this.resizeObserver = new ResizeObserver(() => this.onResize());
    this.resizeObserver.observe(this.canvas);

    this.initialized = true;

    // Start
    this.animate();

    console.log('[WorldScene] 初期化完了 (WebGPU:', this.isWebGPU, ')');
  }

  private setupPostProcessing(): void {
    // Post-processing works with WebGLRenderer
    // For WebGPU, we skip post-processing for now (Three.js WebGPU post-processing is still evolving)
    if (this.isWebGPU) {
      console.log('[WorldScene] WebGPU mode: post-processing disabled (use native WebGPU effects)');
      return;
    }

    if (!(this.renderer instanceof THREE.WebGLRenderer)) {
      return;
    }

    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;

    // Create EffectComposer
    this.composer = new EffectComposer(this.renderer);

    // Add RenderPass (renders the scene)
    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);

    // Add UnrealBloomPass
    const resolution = new THREE.Vector2(width, height);
    this.bloomPass = new UnrealBloomPass(
      resolution,
      1.5,  // bloom strength
      0.8,  // bloom radius
      0.2   // bloom threshold
    );
    this.composer.addPass(this.bloomPass);

    console.log('[WorldScene] Post-processing bloom enabled (strength: 1.5, threshold: 0.2, radius: 0.8)');
  }

  private createGradientSkyWithAurora(): void {
    const skyGeo = new THREE.SphereGeometry(400, 32, 32);

    const skyMat = new THREE.ShaderMaterial({
      uniforms: {
        topColor: { value: new THREE.Color(0x0a0015) },
        midColor: { value: new THREE.Color(0x1a0a3e) },
        bottomColor: { value: new THREE.Color(0x2d1b4e) },
        offset: { value: 20 },
        exponent: { value: 0.6 },
        time: { value: 0 },
        auroraIntensity: { value: 1.0 },
      },
      vertexShader: `
        varying vec3 vWorldPosition;
        varying vec2 vUv;
        void main() {
          vec4 worldPosition = modelMatrix * vec4(position, 1.0);
          vWorldPosition = worldPosition.xyz;
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 topColor;
        uniform vec3 midColor;
        uniform vec3 bottomColor;
        uniform float offset;
        uniform float exponent;
        uniform float time;
        uniform float auroraIntensity;
        varying vec3 vWorldPosition;
        varying vec2 vUv;

        // Simplex noise function for aurora
        vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

        float snoise(vec2 v) {
          const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                             -0.577350269189626, 0.024390243902439);
          vec2 i  = floor(v + dot(v, C.yy));
          vec2 x0 = v -   i + dot(i, C.xx);
          vec2 i1;
          i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
          vec4 x12 = x0.xyxy + C.xxzz;
          x12.xy -= i1;
          i = mod289(i);
          vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                          + i.x + vec3(0.0, i1.x, 1.0));
          vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
                                  dot(x12.zw,x12.zw)), 0.0);
          m = m*m;
          m = m*m;
          vec3 x = 2.0 * fract(p * C.www) - 1.0;
          vec3 h = abs(x) - 0.5;
          vec3 ox = floor(x + 0.5);
          vec3 a0 = x - ox;
          m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
          vec3 g;
          g.x  = a0.x  * x0.x  + h.x  * x0.y;
          g.yz = a0.yz * x12.xz + h.yz * x12.yw;
          return 130.0 * dot(m, g);
        }

        void main() {
          float h = normalize(vWorldPosition + offset).y;
          float t = max(pow(max(h, 0.0), exponent), 0.0);
          vec3 color = mix(bottomColor, midColor, t);
          color = mix(color, topColor, t * t);

          // Aurora borealis effect - only in upper hemisphere
          if (h > 0.1) {
            // Create flowing aurora waves
            float auroraY = (h - 0.1) / 0.9; // Normalize to 0-1 range in upper sky

            // Multiple layers of noise for complex aurora patterns
            float noise1 = snoise(vec2(vWorldPosition.x * 0.01 + time * 0.1, auroraY * 2.0 + time * 0.05));
            float noise2 = snoise(vec2(vWorldPosition.z * 0.015 - time * 0.08, auroraY * 3.0 + time * 0.03));
            float noise3 = snoise(vec2(vWorldPosition.x * 0.02 + vWorldPosition.z * 0.02 + time * 0.12, auroraY * 1.5));

            // Combine noises for aurora curtain effect
            float aurora = (noise1 + noise2 * 0.7 + noise3 * 0.5) / 2.2;
            aurora = aurora * 0.5 + 0.5; // Normalize to 0-1

            // Create vertical curtain bands
            float curtain = sin(vWorldPosition.x * 0.05 + time * 0.2) * 0.5 + 0.5;
            curtain *= sin(vWorldPosition.z * 0.03 - time * 0.15) * 0.5 + 0.5;

            // Aurora visibility peaks at certain heights
            float heightFade = sin(auroraY * 3.14159) * exp(-auroraY * 0.5);

            // Combine all factors
            float auroraStrength = aurora * curtain * heightFade * auroraIntensity;
            auroraStrength = pow(auroraStrength, 1.5) * 2.0;

            // Aurora colors - green and cyan with hints of purple
            vec3 auroraGreen = vec3(0.2, 1.0, 0.4);
            vec3 auroraCyan = vec3(0.1, 0.9, 0.95);
            vec3 auroraPurple = vec3(0.6, 0.2, 0.8);

            // Mix aurora colors based on noise
            vec3 auroraColor = mix(auroraGreen, auroraCyan, noise1 * 0.5 + 0.5);
            auroraColor = mix(auroraColor, auroraPurple, noise2 * 0.3 + 0.15);

            // Add aurora to sky color
            color += auroraColor * auroraStrength * 0.6;
          }

          gl_FragColor = vec4(color, 1.0);
        }
      `,
      side: THREE.BackSide,
    });

    this.skyMesh = new THREE.Mesh(skyGeo, skyMat);
    this.scene.add(this.skyMesh);

    this.addStars();
  }

  private addStars(): void {
    const starCount = 2000;
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);

    for (let i = 0; i < starCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.5;
      const r = 350 + Math.random() * 30;

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.cos(phi) + 50;
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

      const colorChoice = Math.random();
      if (colorChoice < 0.7) {
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 1.0;
        colors[i * 3 + 2] = 1.0;
      } else if (colorChoice < 0.85) {
        colors[i * 3] = 0.7;
        colors[i * 3 + 1] = 0.9;
        colors[i * 3 + 2] = 1.0;
      } else {
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 0.7;
        colors[i * 3 + 2] = 0.9;
      }
    }

    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const starMat = new THREE.PointsMaterial({
      size: 2,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      sizeAttenuation: true,
    });

    const stars = new THREE.Points(starGeo, starMat);
    this.scene.add(stars);
  }

  private setupLighting(): void {
    const ambient = new THREE.AmbientLight(0x2a1a4a, 0.4);
    this.scene.add(ambient);

    const hemi = new THREE.HemisphereLight(0x4a3a8a, 0x1a1a3a, 0.5);
    this.scene.add(hemi);

    const moon = new THREE.DirectionalLight(0x8888ff, 0.6);
    moon.position.set(30, 60, 20);
    moon.castShadow = true;
    moon.shadow.mapSize.width = 2048;
    moon.shadow.mapSize.height = 2048;
    moon.shadow.camera.near = 1;
    moon.shadow.camera.far = 200;
    moon.shadow.camera.left = -60;
    moon.shadow.camera.right = 60;
    moon.shadow.camera.top = 60;
    moon.shadow.camera.bottom = -60;
    moon.shadow.bias = -0.0005;
    this.scene.add(moon);

    const warm1 = new THREE.PointLight(0xff9944, 0.8, 50);
    warm1.position.set(0, 8, 0);
    this.scene.add(warm1);

    const cyan = new THREE.PointLight(0x44ddff, 0.5, 40);
    cyan.position.set(-20, 5, -20);
    this.scene.add(cyan);

    const magenta = new THREE.PointLight(0xff44aa, 0.4, 35);
    magenta.position.set(20, 5, 20);
    this.scene.add(magenta);
  }

  private createLuminousWater(): void {
    const waterGeo = new THREE.PlaneGeometry(300, 300, 100, 100);

    const waterMat = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        waterColor: { value: new THREE.Color(0x0a4a6a) },
        deepColor: { value: new THREE.Color(0x051a2a) },
        glowColor: { value: new THREE.Color(0x00ffff) },
        glowIntensity: { value: 1.2 },
      },
      vertexShader: `
        uniform float time;
        varying vec2 vUv;
        varying float vWave;
        varying vec3 vPosition;
        void main() {
          vUv = uv;
          vec3 pos = position;
          float wave = sin(pos.x * 0.1 + time) * cos(pos.y * 0.1 + time * 0.7) * 0.3;
          wave += sin(pos.x * 0.05 - time * 0.5) * 0.2;
          pos.z = wave;
          vWave = wave;
          vPosition = pos;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 waterColor;
        uniform vec3 deepColor;
        uniform vec3 glowColor;
        uniform float glowIntensity;
        uniform float time;
        varying vec2 vUv;
        varying float vWave;
        varying vec3 vPosition;

        // Simple noise for glow patterns
        float hash(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
        }

        float noise(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          float a = hash(i);
          float b = hash(i + vec2(1.0, 0.0));
          float c = hash(i + vec2(0.0, 1.0));
          float d = hash(i + vec2(1.0, 1.0));
          return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
        }

        void main() {
          float t = (vWave + 0.5) * 0.5;
          vec3 color = mix(deepColor, waterColor, t);

          // Original highlight
          float highlight = pow(max(vWave, 0.0) * 2.0, 3.0) * 0.5;
          color += vec3(0.2, 0.4, 0.6) * highlight;

          // Luminous cyan glow effect
          float glow1 = noise(vUv * 20.0 + time * 0.3);
          float glow2 = noise(vUv * 15.0 - time * 0.2 + vec2(100.0, 50.0));
          float glow3 = noise(vPosition.xy * 0.1 + time * 0.1);

          // Create flowing glow patterns
          float glowPattern = (glow1 + glow2 * 0.7 + glow3 * 0.5) / 2.2;
          glowPattern = pow(glowPattern, 2.0);

          // Add wave-synchronized glow
          float waveGlow = pow(max(vWave + 0.3, 0.0), 2.0);

          // Combine glow effects
          float totalGlow = (glowPattern * 0.6 + waveGlow * 0.4) * glowIntensity;

          // Pulsing effect
          float pulse = sin(time * 2.0) * 0.15 + 0.85;
          totalGlow *= pulse;

          // Add cyan glow to color
          color += glowColor * totalGlow * 0.4;

          // Edge shimmer
          float shimmer = sin(vPosition.x * 0.5 + time * 3.0) * sin(vPosition.y * 0.5 + time * 2.5);
          shimmer = shimmer * 0.5 + 0.5;
          color += glowColor * shimmer * waveGlow * 0.2;

          float dist = length(vUv - 0.5) * 2.0;
          float alpha = 1.0 - smoothstep(0.4, 1.0, dist);

          // Boost alpha slightly for glow visibility
          alpha = min(alpha + totalGlow * 0.1, 0.95);

          gl_FragColor = vec4(color, alpha * 0.85);
        }
      `,
      transparent: true,
      side: THREE.DoubleSide,
    });

    this.waterPlane = new THREE.Mesh(waterGeo, waterMat);
    this.waterPlane.rotation.x = -Math.PI / 2;
    this.waterPlane.position.y = -0.5;
    this.scene.add(this.waterPlane);
  }

  private createFloatingLanterns(): void {
    this.floatingLanterns = new THREE.Group();
    this.floatingLanterns.name = 'floating_lanterns';

    const lanternCount = 80;
    const lanternGeo = new THREE.BoxGeometry(0.4, 0.6, 0.4);

    for (let i = 0; i < lanternCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 15 + Math.random() * 60;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = -0.3 + Math.random() * 0.4;

      const hue = 0.08 + Math.random() * 0.05;
      const color = new THREE.Color().setHSL(hue, 1, 0.6);

      const lanternMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.9,
      });

      const lantern = new THREE.Mesh(lanternGeo, lanternMat);
      lantern.position.set(x, y, z);
      lantern.userData = {
        baseY: y,
        phase: Math.random() * Math.PI * 2,
        speed: 0.5 + Math.random() * 0.5,
      };

      const light = new THREE.PointLight(color, 0.3, 8);
      light.position.set(0, 0.3, 0);
      lantern.add(light);

      this.floatingLanterns.add(lantern);
    }

    this.scene.add(this.floatingLanterns);
  }

  private createParticles(): void {
    const particleCount = 500;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 150;
      positions[i * 3 + 1] = Math.random() * 30;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 150;

      const pink = Math.random();
      colors[i * 3] = 1.0;
      colors[i * 3 + 1] = 0.6 + pink * 0.3;
      colors[i * 3 + 2] = 0.7 + pink * 0.2;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.3,
      vertexColors: true,
      transparent: true,
      opacity: 0.7,
      sizeAttenuation: true,
    });

    this.particles = new THREE.Points(particleGeo, particleMat);
    this.scene.add(this.particles);
  }

  private loadInitialTemplate(): void {
    console.log('[WorldScene] テンプレート読み込み中...');
    const voxels = VoxelTemplates.generateInitialWorld();
    console.log('[WorldScene] ボクセル生成数:', voxels.length);
    this.voxelRenderer.loadWorld(voxels);
    this.templateLoaded = true;
    console.log('[WorldScene] テンプレート読み込み完了');
  }

  // === Public API ===

  async ready(): Promise<void> {
    // Wait for init to complete
    while (!this.initialized) {
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    return Promise.resolve();
  }

  isUsingWebGPU(): boolean {
    return this.isWebGPU;
  }

  loadVoxels(voxels: Voxel[]): void {
    if (!this.voxelRenderer) return;
    if (voxels.length > 0) {
      console.log('[WorldScene] サーバーから', voxels.length, 'ボクセルを読み込み');
      this.voxelRenderer.loadWorld(voxels);
    } else if (!this.templateLoaded) {
      this.loadInitialTemplate();
    }
  }

  applyVoxelUpdates(updates: VoxelUpdate[]): void {
    if (!this.voxelRenderer) return;
    this.voxelRenderer.applyUpdates(updates);
  }

  updateEntities(entities: EntityV3[]): void {
    if (!this.avatarSystem) return;
    const currentIds = new Set(entities.map(e => e.id));
    for (const id of Array.from(this.avatarSystem.getAllPositions().keys())) {
      if (!currentIds.has(id)) {
        this.avatarSystem.removeEntity(id);
      }
    }
    for (const entity of entities) {
      this.avatarSystem.upsertEntity(entity);
    }
  }

  updateEntityPositions(positions: SocketEntityPosition[]): void {
    if (!this.avatarSystem) return;
    for (const pos of positions) {
      this.avatarSystem.upsertEntity({
        id: pos.id,
        name: pos.name,
        position: { x: pos.x, y: pos.y, z: pos.z },
        facing: { x: pos.fx || 1, z: pos.fz || 0 },
        appearance: { bodyColor: '#4fc3f7', accentColor: '#ffffff', shape: 'humanoid', size: 1, emissive: false },
        personality: {} as any,
        state: { needs: {} as any, behaviorMode: 'normal', energy: 1, inventory: [], currentAction: pos.action },
        isAlive: true,
        isGod: false,
        metaAwareness: 0,
        birthTick: 0,
        createdAt: '',
      });
    }
  }

  handleSpeechEvent(event: SocketSpeechEvent): void {
    if (!this.avatarSystem) return;
    const entityPos = this.avatarSystem.getEntityPosition(event.entityId);
    if (entityPos) {
      this.avatarSystem.showSpeech(event.entityId, event.text);
    } else if (event.position) {
      this.avatarSystem.showSpeechAtPosition(event.text, event.position);
    }
  }

  loadStructures(_structures: StructureInfo[]): void {}

  setCameraMode(mode: CameraMode): void {
    if (!this.cameraController) return;
    this.cameraController.setMode(mode);
  }

  followEntity(entityId: string): void {
    if (!this.cameraController) return;
    this.cameraController.followEntity(entityId, 'third_person');
  }

  panTo(x: number, z: number): void {
    if (!this.cameraController) return;
    this.cameraController.panTo(x, z);
  }

  getCameraPosition(): { x: number; y: number; z: number } {
    if (!this.cameraController) return { x: 0, y: 15, z: 45 };
    const p = this.cameraController.getPosition();
    return { x: p.x, y: p.y, z: p.z };
  }

  setBuildMode(mode: BuildMode): void {
    if (!this.buildingTool) return;
    this.buildingTool.setMode(mode);
  }

  setBuildColor(color: string): void {
    if (!this.buildingTool) return;
    this.buildingTool.setColor(color);
  }

  setBuildMaterial(material: 'solid' | 'glass' | 'emissive' | 'liquid'): void {
    if (!this.buildingTool) return;
    this.buildingTool.setMaterial(material);
  }

  setPlayerEntityId(entityId: string): void {
    if (!this.buildingTool) return;
    this.buildingTool.setEntityId(entityId);
  }

  // === Animation Loop ===

  private animate = (): void => {
    this.animationFrameId = requestAnimationFrame(this.animate);

    if (!this.initialized) return;

    const delta = this.clock.getDelta();
    const elapsed = this.clock.getElapsedTime();

    // Update sky aurora animation
    if (this.skyMesh) {
      const mat = this.skyMesh.material as THREE.ShaderMaterial;
      mat.uniforms.time.value = elapsed;
    }

    // Update water
    if (this.waterPlane) {
      const mat = this.waterPlane.material as THREE.ShaderMaterial;
      mat.uniforms.time.value = elapsed;
    }

    // Update floating lanterns
    if (this.floatingLanterns) {
      this.floatingLanterns.children.forEach((lantern) => {
        const data = lantern.userData;
        lantern.position.y = data.baseY + Math.sin(elapsed * data.speed + data.phase) * 0.15;
        lantern.rotation.y = elapsed * 0.1 + data.phase;
      });
    }

    // Update particles
    if (this.particles) {
      const positions = this.particles.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < positions.length; i += 3) {
        positions[i] += Math.sin(elapsed + i) * 0.01;
        positions[i + 1] -= 0.02;
        positions[i + 2] += Math.cos(elapsed + i) * 0.01;

        if (positions[i + 1] < -1) {
          positions[i + 1] = 30;
          positions[i] = (Math.random() - 0.5) * 150;
          positions[i + 2] = (Math.random() - 0.5) * 150;
        }
      }
      this.particles.geometry.attributes.position.needsUpdate = true;
    }

    // Update subsystems
    if (this.avatarSystem && this.cameraController) {
      const entityPositions = this.avatarSystem.getAllPositions();
      this.cameraController.update(delta, entityPositions);
      this.avatarSystem.update(this.camera);
    }

    if (this.buildingTool && this.buildingTool.getMode() !== 'none') {
      this.buildingTool.updateGhost(this.mouseNDC);
    }

    // Render with post-processing or standard
    if (this.composer && !this.isWebGPU) {
      // Use EffectComposer for WebGL with bloom
      this.composer.render();
    } else if (this.renderer) {
      // Direct render for WebGPU or if composer not available
      this.renderer.render(this.scene, this.camera);
    }
  };

  // === Event Handlers ===

  private onMouseMove = (e: MouseEvent): void => {
    const rect = this.canvas.getBoundingClientRect();
    this.mouseNDC.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouseNDC.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  };

  private onClick = (): void => {
    if (!this.initialized) return;

    if (this.buildingTool && this.buildingTool.getMode() !== 'none') {
      this.buildingTool.execute();
      return;
    }

    if (this.onEntityClick && this.avatarSystem) {
      this.raycaster.setFromCamera(this.mouseNDC, this.camera);
      const entityId = this.avatarSystem.raycast(this.raycaster);
      if (entityId) {
        this.onEntityClick(entityId);
      }
    }
  };

  private onTouchStart = (e: TouchEvent): void => {
    if (e.touches.length === 1) {
      this.touchStartPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      this.touchStartTime = Date.now();
    }
  };

  private onTouchEnd = (e: TouchEvent): void => {
    if (this.touchStartPos && e.changedTouches.length >= 1) {
      const touch = e.changedTouches[0];
      const dx = touch.clientX - this.touchStartPos.x;
      const dy = touch.clientY - this.touchStartPos.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const duration = Date.now() - this.touchStartTime;

      if (dist < 15 && duration < 400) {
        const rect = this.canvas.getBoundingClientRect();
        this.mouseNDC.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouseNDC.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;

        if (this.buildingTool && this.buildingTool.getMode() !== 'none') {
          this.buildingTool.execute();
        } else if (this.onEntityClick && this.avatarSystem) {
          this.raycaster.setFromCamera(this.mouseNDC, this.camera);
          const entityId = this.avatarSystem.raycast(this.raycaster);
          if (entityId) {
            this.onEntityClick(entityId);
          }
        }
      }
    }
    this.touchStartPos = null;
  };

  private onResize = (): void => {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    if (this.renderer) {
      this.renderer.setSize(width, height);
    }

    // Update composer size for post-processing
    if (this.composer) {
      this.composer.setSize(width, height);
    }

    // Update bloom pass resolution
    if (this.bloomPass) {
      this.bloomPass.resolution.set(width, height);
    }
  };

  // === Cleanup ===

  dispose(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
    }

    this.canvas.removeEventListener('mousemove', this.onMouseMove);
    this.canvas.removeEventListener('click', this.onClick);
    this.canvas.removeEventListener('touchstart', this.onTouchStart);
    this.canvas.removeEventListener('touchend', this.onTouchEnd);
    window.removeEventListener('resize', this.onResize);
    this.resizeObserver?.disconnect();

    if (this.voxelRenderer) this.voxelRenderer.dispose();
    if (this.avatarSystem) this.avatarSystem.dispose();
    if (this.cameraController) this.cameraController.dispose();
    if (this.buildingTool) this.buildingTool.dispose();

    // Dispose post-processing
    if (this.composer) this.composer.dispose();

    if (this.renderer) this.renderer.dispose();
  }
}
