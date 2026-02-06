/**
 * GENESIS v3 WorldScene
 *
 * WebGPU対応の美しい3Dボクセルワールド
 * WebGPUレンダラー優先（フォールバック: WebGL + Bloom）
 * MeshBasicMaterial/MeshLambertMaterial使用（ShaderMaterial非対応のため）
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

  // Post-processing (WebGL only)
  private composer: EffectComposer | null = null;
  private bloomPass: UnrealBloomPass | null = null;

  // WebGPU state
  private usingWebGPU = false;

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
  private stars: THREE.Points | null = null;

  // Star twinkle data
  private starBaseOpacities: Float32Array | null = null;
  private starTwinkleSpeeds: Float32Array | null = null;
  private starTwinklePhases: Float32Array | null = null;

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
    console.log('[WorldScene] レンダラー初期化中...');

    // Try WebGPU first
    let webgpuAvailable = false;
    try {
      if ('gpu' in navigator) {
        const adapter = await (navigator as any).gpu.requestAdapter();
        if (adapter) {
          webgpuAvailable = true;
          console.log('[WorldScene] WebGPU利用可能');
        }
      }
    } catch (e) {
      console.log('[WorldScene] WebGPUチェック失敗:', e);
    }

    if (webgpuAvailable) {
      // Use WebGPU - note: EffectComposer not supported, use emissive materials for glow
      try {
        // Dynamic import for WebGPU renderer
        const { WebGPURenderer } = await import('three/webgpu');

        const webgpuRenderer = new WebGPURenderer({
          canvas: this.canvas,
          antialias: true,
          powerPreference: 'high-performance',
        });

        await webgpuRenderer.init();

        this.renderer = webgpuRenderer as unknown as THREE.WebGLRenderer;
        this.usingWebGPU = true;

        console.log('[WorldScene] ✓ WebGPUレンダラー初期化完了');
        console.log('[WorldScene] 注意: WebGPUモードではEffectComposer非対応のため、emissive素材で疑似グロー効果を使用');
      } catch (e) {
        console.warn('[WorldScene] WebGPUレンダラー初期化失敗、WebGLにフォールバック:', e);
        this.initWebGLRenderer();
      }
    } else {
      console.log('[WorldScene] WebGPU非対応、WebGLを使用');
      this.initWebGLRenderer();
    }

    // Renderer settings
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);

    if (!this.usingWebGPU) {
      // WebGL specific settings
      (this.renderer as THREE.WebGLRenderer).shadowMap.enabled = true;
      (this.renderer as THREE.WebGLRenderer).shadowMap.type = THREE.PCFSoftShadowMap;
      (this.renderer as THREE.WebGLRenderer).toneMapping = THREE.ACESFilmicToneMapping;
      (this.renderer as THREE.WebGLRenderer).toneMappingExposure = 1.2;

      // Setup post-processing (WebGL only)
      this.setupPostProcessing();
    }

    // グラデーション空（MeshBasicMaterial使用）
    this.createGradientSky();

    // 強化された星空
    this.addEnhancedStars();

    // 幻想的な霧
    this.scene.fog = new THREE.FogExp2(0x1a0a2e, 0.008);
    console.log('[WorldScene] ✓ 霧効果設定完了 (FogExp2, density: 0.008)');

    // Lighting
    this.setupLighting();

    // シンプルな水面（MeshBasicMaterial使用）
    this.createSimpleWater();

    // Floating Lanterns with emissive glow
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

    const mode = this.usingWebGPU ? 'WebGPU + Emissive Glow' : 'WebGL + Bloom';
    console.log(`[WorldScene] 初期化完了 (${mode})`);
    console.log('[WorldScene] 星の数: 3500, きらめきアニメーション有効');
  }

  private initWebGLRenderer(): void {
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance',
    });
    this.usingWebGPU = false;
    console.log('[WorldScene] ✓ WebGLレンダラー初期化完了');
  }

  private setupPostProcessing(): void {
    if (this.usingWebGPU) {
      console.log('[WorldScene] WebGPUモード: post-processingスキップ（emissive素材で代替）');
      return;
    }

    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;

    // Create EffectComposer
    this.composer = new EffectComposer(this.renderer as THREE.WebGLRenderer);

    // Add RenderPass (renders the scene)
    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);

    // Add UnrealBloomPass for glowing effects
    const resolution = new THREE.Vector2(width, height);
    this.bloomPass = new UnrealBloomPass(
      resolution,
      1.5,  // bloom strength - strong glow
      0.8,  // bloom radius
      0.2   // bloom threshold - low for more glow
    );
    this.composer.addPass(this.bloomPass);

    console.log('[WorldScene] ✓ Post-processing bloom有効 (strength: 1.5, threshold: 0.2, radius: 0.8)');
  }

  private createGradientSky(): void {
    // MeshBasicMaterialを使用したグラデーション空
    // 頂点カラーでグラデーションを実現
    const skyGeo = new THREE.SphereGeometry(400, 64, 32);

    // 頂点カラーでグラデーションを設定
    const colors = new Float32Array(skyGeo.attributes.position.count * 3);
    const positions = skyGeo.attributes.position.array;

    // 色の定義
    const topColor = new THREE.Color(0x0a0a2a);      // 深い藍色（上部）
    const midColor = new THREE.Color(0x1a0a3e);      // 紫
    const bottomColor = new THREE.Color(0xff6b4a);   // 夕焼けオレンジ
    const horizonColor = new THREE.Color(0xff8866);  // ピンクオレンジ（地平線）

    for (let i = 0; i < skyGeo.attributes.position.count; i++) {
      const y = positions[i * 3 + 1];
      const normalizedY = (y + 400) / 800; // 0 to 1

      let color: THREE.Color;
      if (normalizedY > 0.7) {
        // 上部: 深い紫/藍色
        const t = (normalizedY - 0.7) / 0.3;
        color = midColor.clone().lerp(topColor, t);
      } else if (normalizedY > 0.4) {
        // 中間部: グラデーション
        const t = (normalizedY - 0.4) / 0.3;
        color = horizonColor.clone().lerp(midColor, t);
      } else {
        // 下部: 夕焼けオレンジ/ピンク
        const t = normalizedY / 0.4;
        color = bottomColor.clone().lerp(horizonColor, t);
      }

      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }

    skyGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const skyMat = new THREE.MeshBasicMaterial({
      vertexColors: true,
      side: THREE.BackSide,
    });

    this.skyMesh = new THREE.Mesh(skyGeo, skyMat);
    this.scene.add(this.skyMesh);

    console.log('[WorldScene] ✓ グラデーション空作成完了（MeshBasicMaterial + 頂点カラー）');
    console.log('[WorldScene]   上部: 深い紫/藍色 (0x0a0a2a)');
    console.log('[WorldScene]   下部: 夕焼けオレンジ/ピンク (0xff6b4a - 0xff8866)');
  }

  private addEnhancedStars(): void {
    const starCount = 3500; // 星の数を3000+に増加
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);
    const sizes = new Float32Array(starCount);

    // きらめきアニメーション用データ
    this.starBaseOpacities = new Float32Array(starCount);
    this.starTwinkleSpeeds = new Float32Array(starCount);
    this.starTwinklePhases = new Float32Array(starCount);

    for (let i = 0; i < starCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.5; // 上半球のみ
      const r = 350 + Math.random() * 40;

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.cos(phi) + 50;
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

      // 星の色のバリエーション
      const colorChoice = Math.random();
      if (colorChoice < 0.6) {
        // 白い星（最も多い）
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 1.0;
        colors[i * 3 + 2] = 1.0;
      } else if (colorChoice < 0.75) {
        // 青白い星
        colors[i * 3] = 0.7;
        colors[i * 3 + 1] = 0.85;
        colors[i * 3 + 2] = 1.0;
      } else if (colorChoice < 0.85) {
        // 黄色い星
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 0.95;
        colors[i * 3 + 2] = 0.7;
      } else if (colorChoice < 0.93) {
        // ピンクの星
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 0.7;
        colors[i * 3 + 2] = 0.85;
      } else {
        // 赤い星（希少）
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 0.6;
        colors[i * 3 + 2] = 0.5;
      }

      // 星のサイズにバリエーション（0.5 - 4.0）
      const sizeRand = Math.random();
      if (sizeRand < 0.7) {
        sizes[i] = 0.5 + Math.random() * 1.0; // 小さな星（多数）
      } else if (sizeRand < 0.9) {
        sizes[i] = 1.5 + Math.random() * 1.5; // 中くらいの星
      } else {
        sizes[i] = 3.0 + Math.random() * 1.0; // 大きな明るい星（少数）
      }

      // きらめきパラメータ
      this.starBaseOpacities[i] = 0.6 + Math.random() * 0.4;
      this.starTwinkleSpeeds[i] = 1.0 + Math.random() * 3.0;
      this.starTwinklePhases[i] = Math.random() * Math.PI * 2;
    }

    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    starGeo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const starMat = new THREE.PointsMaterial({
      size: 2,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      sizeAttenuation: true,
    });

    this.stars = new THREE.Points(starGeo, starMat);
    this.scene.add(this.stars);

    console.log(`[WorldScene] ✓ 強化された星空作成完了 (${starCount}個の星)`);
    console.log('[WorldScene]   サイズバリエーション: 0.5 - 4.0');
    console.log('[WorldScene]   色: 白、青白、黄、ピンク、赤');
  }

  private setupLighting(): void {
    const ambient = new THREE.AmbientLight(0x2a1a4a, 0.4);
    this.scene.add(ambient);

    const hemi = new THREE.HemisphereLight(0x4a3a8a, 0x1a1a3a, 0.5);
    this.scene.add(hemi);

    const moon = new THREE.DirectionalLight(0x8888ff, 0.6);
    moon.position.set(30, 60, 20);
    moon.castShadow = !this.usingWebGPU; // WebGPUではシャドウを無効化（互換性のため）
    if (!this.usingWebGPU) {
      moon.shadow.mapSize.width = 2048;
      moon.shadow.mapSize.height = 2048;
      moon.shadow.camera.near = 1;
      moon.shadow.camera.far = 200;
      moon.shadow.camera.left = -60;
      moon.shadow.camera.right = 60;
      moon.shadow.camera.top = 60;
      moon.shadow.camera.bottom = -60;
      moon.shadow.bias = -0.0005;
    }
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

    console.log('[WorldScene] ✓ ライティング設定完了');
  }

  private createSimpleWater(): void {
    // シンプルなMeshBasicMaterialで半透明シアン水面
    const waterGeo = new THREE.PlaneGeometry(300, 300, 1, 1);

    const waterMat = new THREE.MeshBasicMaterial({
      color: 0x0088aa, // シアン
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide,
    });

    this.waterPlane = new THREE.Mesh(waterGeo, waterMat);
    this.waterPlane.rotation.x = -Math.PI / 2;
    this.waterPlane.position.y = -0.5;
    this.scene.add(this.waterPlane);

    console.log('[WorldScene] ✓ 水面作成完了（MeshBasicMaterial, 半透明シアン）');
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

      // WebGPU対応: emissive効果のためMeshLambertMaterialを使用
      let lanternMat: THREE.Material;
      if (this.usingWebGPU) {
        // WebGPUモード: MeshLambertMaterialでemissive疑似グロー
        lanternMat = new THREE.MeshLambertMaterial({
          color: color,
          emissive: color,
          emissiveIntensity: 0.8,
          transparent: true,
          opacity: 0.9,
        });
      } else {
        // WebGLモード: MeshBasicMaterial（Bloomが効果を追加）
        lanternMat = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.9,
        });
      }

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
    console.log('[WorldScene] ✓ 浮遊灯籠作成完了 (80個)');
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
    console.log('[WorldScene] ✓ パーティクル作成完了 (500個)');
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
    return this.usingWebGPU;
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

    // Update star twinkle animation
    if (this.stars && this.starBaseOpacities && this.starTwinkleSpeeds && this.starTwinklePhases) {
      const colorAttr = this.stars.geometry.attributes.color;
      const colors = colorAttr.array as Float32Array;
      const starCount = colors.length / 3;

      for (let i = 0; i < starCount; i++) {
        // きらめき計算
        const twinkle = Math.sin(elapsed * this.starTwinkleSpeeds[i] + this.starTwinklePhases[i]);
        const brightness = this.starBaseOpacities[i] + twinkle * 0.3;

        // 色の明るさを調整（元の色を保持しながら）
        const baseR = colors[i * 3];
        const baseG = colors[i * 3 + 1];
        const baseB = colors[i * 3 + 2];

        // 明るさの範囲を0.3-1.0に制限
        const factor = Math.max(0.3, Math.min(1.0, brightness));
        colors[i * 3] = baseR * factor;
        colors[i * 3 + 1] = baseG * factor;
        colors[i * 3 + 2] = baseB * factor;
      }
      colorAttr.needsUpdate = true;
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

    // Render
    if (!this.usingWebGPU && this.composer) {
      // WebGL with post-processing bloom
      this.composer.render();
    } else if (this.renderer) {
      // WebGPU or WebGL without composer
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

    // Update composer size for post-processing (WebGL only)
    if (!this.usingWebGPU && this.composer) {
      this.composer.setSize(width, height);
    }

    // Update bloom pass resolution (WebGL only)
    if (!this.usingWebGPU && this.bloomPass) {
      this.bloomPass.resolution.set(width, height);
    }
  };

  // === Cleanup ===

  dispose(): void {
    console.log('[WorldScene] dispose開始...');

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

    console.log('[WorldScene] dispose完了');
  }
}
