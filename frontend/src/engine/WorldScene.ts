/**
 * GENESIS v3 WorldScene
 *
 * 「超かぐや姫」インスパイアの美しい3Dボクセルワールド
 * WebGL + Post-processing Bloom + Aurora + Luminous Water
 */
import * as THREE from 'three';
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
  private renderer!: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;
  private canvas: HTMLCanvasElement;

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

    this.scene = new THREE.Scene();
    this.clock = new THREE.Clock();

    this.camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      800,
    );
    this.camera.position.set(0, 30, 80);
    this.camera.lookAt(0, 0, 0);

    this.initRenderer();
  }

  private async initRenderer(): Promise<void> {
    console.log('[WorldScene] WebGLレンダラー初期化中...');

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance',
    });

    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.2;

    console.log('[WorldScene] ✓ WebGLレンダラー初期化完了');

    this.setupPostProcessing();
    this.createGradientSkyWithAurora();
    this.scene.fog = new THREE.FogExp2(0x1a0a2e, 0.004);
    this.setupLighting();
    this.createLuminousWater();
    this.createFloatingLanterns();
    this.createParticles();

    this.voxelRenderer = new VoxelRenderer(this.scene);
    this.avatarSystem = new AvatarSystem(this.scene);
    this.avatarSystem.setLabelContainer(this.labelContainer);
    this.cameraController = new CameraController(this.camera);
    this.cameraController.attach(this.canvas);
    this.buildingTool = new BuildingTool(this.scene, this.camera, this.voxelRenderer);

    if (this.onProposalCallback) {
      this.buildingTool.setProposalCallback(this.onProposalCallback);
    }

    this.loadInitialTemplate();

    this.canvas.addEventListener('mousemove', this.onMouseMove);
    this.canvas.addEventListener('click', this.onClick);
    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('resize', this.onResize);
    this.canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    this.canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });

    this.resizeObserver = new ResizeObserver(() => this.onResize());
    this.resizeObserver.observe(this.canvas);

    this.initialized = true;
    this.animate();

    console.log('[WorldScene] 初期化完了 (WebGL + Bloom + Aurora)');
  }

  private setupPostProcessing(): void {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;

    this.composer = new EffectComposer(this.renderer);
    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);

    const resolution = new THREE.Vector2(width, height);
    this.bloomPass = new UnrealBloomPass(resolution, 1.5, 0.8, 0.2);
    this.composer.addPass(this.bloomPass);

    console.log('[WorldScene] ✓ Bloom有効');
  }

  private createGradientSkyWithAurora(): void {
    const skyGeo = new THREE.SphereGeometry(600, 32, 32);

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
        void main() {
          vec4 worldPosition = modelMatrix * vec4(position, 1.0);
          vWorldPosition = worldPosition.xyz;
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

        vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

        float snoise(vec2 v) {
          const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
          vec2 i = floor(v + dot(v, C.yy));
          vec2 x0 = v - i + dot(i, C.xx);
          vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
          vec4 x12 = x0.xyxy + C.xxzz;
          x12.xy -= i1;
          i = mod289(i);
          vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
          vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
          m = m*m; m = m*m;
          vec3 x = 2.0 * fract(p * C.www) - 1.0;
          vec3 h = abs(x) - 0.5;
          vec3 ox = floor(x + 0.5);
          vec3 a0 = x - ox;
          m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
          vec3 g;
          g.x = a0.x * x0.x + h.x * x0.y;
          g.yz = a0.yz * x12.xz + h.yz * x12.yw;
          return 130.0 * dot(m, g);
        }

        void main() {
          float h = normalize(vWorldPosition + offset).y;
          float t = max(pow(max(h, 0.0), exponent), 0.0);
          vec3 color = mix(bottomColor, midColor, t);
          color = mix(color, topColor, t * t);

          if (h > 0.1) {
            float auroraY = (h - 0.1) / 0.9;
            float noise1 = snoise(vec2(vWorldPosition.x * 0.01 + time * 0.1, auroraY * 2.0 + time * 0.05));
            float noise2 = snoise(vec2(vWorldPosition.z * 0.015 - time * 0.08, auroraY * 3.0 + time * 0.03));
            float aurora = (noise1 + noise2 * 0.7) / 1.7 * 0.5 + 0.5;
            float curtain = sin(vWorldPosition.x * 0.05 + time * 0.2) * 0.5 + 0.5;
            float heightFade = sin(auroraY * 3.14159) * exp(-auroraY * 0.5);
            float auroraStrength = pow(aurora * curtain * heightFade * auroraIntensity, 1.5) * 2.0;

            vec3 auroraGreen = vec3(0.2, 1.0, 0.4);
            vec3 auroraCyan = vec3(0.1, 0.9, 0.95);
            vec3 auroraColor = mix(auroraGreen, auroraCyan, noise1 * 0.5 + 0.5);
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
    console.log('[WorldScene] ✓ オーロラ空作成完了');
  }

  private addStars(): void {
    const starCount = 3000;
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);

    for (let i = 0; i < starCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.5;
      const r = 500 + Math.random() * 50;
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.cos(phi) + 50;
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

      const c = Math.random();
      if (c < 0.7) { colors[i*3]=1; colors[i*3+1]=1; colors[i*3+2]=1; }
      else if (c < 0.85) { colors[i*3]=0.7; colors[i*3+1]=0.9; colors[i*3+2]=1; }
      else { colors[i*3]=1; colors[i*3+1]=0.7; colors[i*3+2]=0.9; }
    }

    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const starMat = new THREE.PointsMaterial({ size: 2, vertexColors: true, transparent: true, opacity: 0.8, sizeAttenuation: true });
    this.scene.add(new THREE.Points(starGeo, starMat));
  }

  private setupLighting(): void {
    this.scene.add(new THREE.AmbientLight(0x2a1a4a, 0.4));
    this.scene.add(new THREE.HemisphereLight(0x4a3a8a, 0x1a1a3a, 0.5));

    const moon = new THREE.DirectionalLight(0x8888ff, 0.6);
    moon.position.set(30, 60, 20);
    moon.castShadow = true;
    moon.shadow.mapSize.set(2048, 2048);
    moon.shadow.camera.near = 1;
    moon.shadow.camera.far = 200;
    moon.shadow.camera.left = -100;
    moon.shadow.camera.right = 100;
    moon.shadow.camera.top = 100;
    moon.shadow.camera.bottom = -100;
    this.scene.add(moon);

    this.scene.add(new THREE.PointLight(0xff9944, 0.8, 80).translateY(10));
    const cyan = new THREE.PointLight(0x44ddff, 0.5, 60); cyan.position.set(-40, 8, -40); this.scene.add(cyan);
    const magenta = new THREE.PointLight(0xff44aa, 0.4, 50); magenta.position.set(40, 8, 40); this.scene.add(magenta);
  }

  private createLuminousWater(): void {
    const waterGeo = new THREE.PlaneGeometry(500, 500, 100, 100);

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
          float wave = sin(pos.x * 0.08 + time) * cos(pos.y * 0.08 + time * 0.7) * 0.4;
          wave += sin(pos.x * 0.04 - time * 0.5) * 0.3;
          pos.z = wave;
          vWave = wave;
          vPosition = pos;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 waterColor, deepColor, glowColor;
        uniform float glowIntensity, time;
        varying vec2 vUv;
        varying float vWave;
        varying vec3 vPosition;

        float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float noise(vec2 p) {
          vec2 i = floor(p), f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(mix(hash(i), hash(i + vec2(1,0)), f.x), mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x), f.y);
        }

        void main() {
          float t = (vWave + 0.5) * 0.5;
          vec3 color = mix(deepColor, waterColor, t);
          color += vec3(0.2, 0.4, 0.6) * pow(max(vWave, 0.0) * 2.0, 3.0) * 0.5;

          float glow = (noise(vUv * 20.0 + time * 0.3) + noise(vUv * 15.0 - time * 0.2) * 0.7) / 1.7;
          glow = pow(glow, 2.0);
          float waveGlow = pow(max(vWave + 0.3, 0.0), 2.0);
          float totalGlow = (glow * 0.6 + waveGlow * 0.4) * glowIntensity * (sin(time * 2.0) * 0.15 + 0.85);

          color += glowColor * totalGlow * 0.4;
          float shimmer = sin(vPosition.x * 0.5 + time * 3.0) * sin(vPosition.y * 0.5 + time * 2.5) * 0.5 + 0.5;
          color += glowColor * shimmer * waveGlow * 0.2;

          float alpha = min((1.0 - smoothstep(0.4, 1.0, length(vUv - 0.5) * 2.0)) + totalGlow * 0.1, 0.95);
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
    const lanternGeo = new THREE.BoxGeometry(0.4, 0.6, 0.4);

    for (let i = 0; i < 50; i++) {
      const angle = (i / 50) * Math.PI * 2 + Math.random() * 0.5;
      const radius = 30 + Math.random() * 80;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = -0.2 + Math.random() * 0.3;
      const hue = 0.08 + Math.random() * 0.05;
      const color = new THREE.Color().setHSL(hue, 1, 0.6);

      const lantern = new THREE.Mesh(lanternGeo, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 }));
      lantern.position.set(x, y, z);
      lantern.userData = { baseY: y, phase: Math.random() * Math.PI * 2, speed: 0.5 + Math.random() * 0.5 };
      lantern.add(new THREE.PointLight(color, 0.3, 8));
      this.floatingLanterns.add(lantern);
    }
    this.scene.add(this.floatingLanterns);
  }

  private createParticles(): void {
    const count = 800;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      positions[i*3] = (Math.random() - 0.5) * 200;
      positions[i*3+1] = Math.random() * 50;
      positions[i*3+2] = (Math.random() - 0.5) * 200;
      colors[i*3] = 1;
      colors[i*3+1] = 0.6 + Math.random() * 0.3;
      colors[i*3+2] = 0.7 + Math.random() * 0.2;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    this.particles = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.4, vertexColors: true, transparent: true, opacity: 0.8, sizeAttenuation: true }));
    this.scene.add(this.particles);
  }

  private loadInitialTemplate(): void {
    console.log('[WorldScene] テンプレート読み込み中...');
    const voxels = VoxelTemplates.generateInitialWorld();
    console.log('[WorldScene] ボクセル生成数:', voxels.length);
    this.voxelRenderer.loadWorld(voxels);
    this.templateLoaded = true;
  }

  async ready(): Promise<void> {
    while (!this.initialized) await new Promise(r => setTimeout(r, 50));
  }

  isUsingWebGPU(): boolean { return false; }

  loadVoxels(voxels: Voxel[]): void {
    if (!this.voxelRenderer) return;
    if (voxels.length > 0) {
      console.log('[WorldScene] サーバーから', voxels.length, 'ボクセルを読み込み');
      this.voxelRenderer.loadWorld(voxels);
    } else if (!this.templateLoaded) this.loadInitialTemplate();
  }

  applyVoxelUpdates(updates: VoxelUpdate[]): void { this.voxelRenderer?.applyUpdates(updates); }

  updateEntities(entities: EntityV3[]): void {
    if (!this.avatarSystem) return;
    const currentIds = new Set(entities.map(e => e.id));
    for (const id of Array.from(this.avatarSystem.getAllPositions().keys())) {
      if (!currentIds.has(id)) this.avatarSystem.removeEntity(id);
    }
    for (const entity of entities) this.avatarSystem.upsertEntity(entity);
  }

  updateEntityPositions(positions: SocketEntityPosition[]): void {
    if (!this.avatarSystem) return;
    for (const pos of positions) {
      this.avatarSystem.upsertEntity({
        id: pos.id, name: pos.name,
        position: { x: pos.x, y: pos.y, z: pos.z },
        facing: { x: pos.fx || 1, z: pos.fz || 0 },
        appearance: { bodyColor: '#4fc3f7', accentColor: '#ffffff', shape: 'humanoid', size: 1, emissive: false },
        personality: {} as any,
        state: { needs: {} as any, behaviorMode: 'normal', energy: 1, inventory: [], currentAction: pos.action },
        isAlive: true, isGod: false, metaAwareness: 0, birthTick: 0, createdAt: '',
      });
    }
  }

  handleSpeechEvent(event: SocketSpeechEvent): void {
    if (!this.avatarSystem) return;
    const pos = this.avatarSystem.getEntityPosition(event.entityId);
    if (pos) this.avatarSystem.showSpeech(event.entityId, event.text);
    else if (event.position) this.avatarSystem.showSpeechAtPosition(event.text, event.position);
  }

  loadStructures(_s: StructureInfo[]): void {}
  setCameraMode(mode: CameraMode): void { this.cameraController?.setMode(mode); }
  followEntity(entityId: string): void { this.cameraController?.followEntity(entityId, 'third_person'); }
  panTo(x: number, z: number): void { this.cameraController?.panTo(x, z); }
  getCameraPosition(): { x: number; y: number; z: number } {
    if (!this.cameraController) return { x: 0, y: 30, z: 80 };
    const p = this.cameraController.getPosition();
    return { x: p.x, y: p.y, z: p.z };
  }
  setBuildMode(mode: BuildMode): void { this.buildingTool?.setMode(mode); }
  setBuildColor(color: string): void { this.buildingTool?.setColor(color); }
  setBuildMaterial(material: 'solid' | 'glass' | 'emissive' | 'liquid'): void { this.buildingTool?.setMaterial(material); }
  setPlayerEntityId(entityId: string): void { this.buildingTool?.setEntityId(entityId); }

  private animate = (): void => {
    this.animationFrameId = requestAnimationFrame(this.animate);
    if (!this.initialized) return;

    const delta = this.clock.getDelta();
    const elapsed = this.clock.getElapsedTime();

    if (this.skyMesh) (this.skyMesh.material as THREE.ShaderMaterial).uniforms.time.value = elapsed;
    if (this.waterPlane) (this.waterPlane.material as THREE.ShaderMaterial).uniforms.time.value = elapsed;

    if (this.floatingLanterns) {
      this.floatingLanterns.children.forEach(l => {
        l.position.y = l.userData.baseY + Math.sin(elapsed * l.userData.speed + l.userData.phase) * 0.15;
        l.rotation.y = elapsed * 0.1 + l.userData.phase;
      });
    }

    if (this.particles) {
      const pos = this.particles.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < pos.length; i += 3) {
        pos[i] += Math.sin(elapsed + i) * 0.01;
        pos[i+1] -= 0.03;
        pos[i+2] += Math.cos(elapsed + i) * 0.01;
        if (pos[i+1] < -1) { pos[i+1] = 50; pos[i] = (Math.random() - 0.5) * 200; pos[i+2] = (Math.random() - 0.5) * 200; }
      }
      this.particles.geometry.attributes.position.needsUpdate = true;
    }

    if (this.avatarSystem && this.cameraController) {
      this.cameraController.update(delta, this.avatarSystem.getAllPositions());
      this.avatarSystem.update(this.camera);
    }

    if (this.buildingTool?.getMode() !== 'none') this.buildingTool.updateGhost(this.mouseNDC);

    if (this.composer) this.composer.render();
    else this.renderer.render(this.scene, this.camera);
  };

  private onMouseMove = (e: MouseEvent): void => {
    const rect = this.canvas.getBoundingClientRect();
    this.mouseNDC.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouseNDC.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  };

  private onClick = (): void => {
    if (!this.initialized) return;
    if (this.buildingTool?.getMode() !== 'none') { this.buildingTool.execute(); return; }
    if (this.onEntityClick && this.avatarSystem) {
      this.raycaster.setFromCamera(this.mouseNDC, this.camera);
      const id = this.avatarSystem.raycast(this.raycaster);
      if (id) this.onEntityClick(id);
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
      const dx = touch.clientX - this.touchStartPos.x, dy = touch.clientY - this.touchStartPos.y;
      if (Math.sqrt(dx*dx + dy*dy) < 15 && Date.now() - this.touchStartTime < 400) {
        const rect = this.canvas.getBoundingClientRect();
        this.mouseNDC.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouseNDC.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
        if (this.buildingTool?.getMode() !== 'none') this.buildingTool.execute();
        else if (this.onEntityClick && this.avatarSystem) {
          this.raycaster.setFromCamera(this.mouseNDC, this.camera);
          const id = this.avatarSystem.raycast(this.raycaster);
          if (id) this.onEntityClick(id);
        }
      }
    }
    this.touchStartPos = null;
  };

  private onResize = (): void => {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer?.setSize(w, h);
    this.composer?.setSize(w, h);
    this.bloomPass?.resolution.set(w, h);
  };

  dispose(): void {
    if (this.animationFrameId !== null) cancelAnimationFrame(this.animationFrameId);
    this.canvas.removeEventListener('mousemove', this.onMouseMove);
    this.canvas.removeEventListener('click', this.onClick);
    this.canvas.removeEventListener('touchstart', this.onTouchStart);
    this.canvas.removeEventListener('touchend', this.onTouchEnd);
    window.removeEventListener('resize', this.onResize);
    this.resizeObserver?.disconnect();
    this.voxelRenderer?.dispose();
    this.avatarSystem?.dispose();
    this.cameraController?.dispose();
    this.buildingTool?.dispose();
    this.composer?.dispose();
    this.renderer?.dispose();
  }
}
