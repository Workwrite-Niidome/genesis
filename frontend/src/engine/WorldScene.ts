/**
 * GENESIS v3 WorldScene
 *
 * WebGPU-first renderer with WebGL fallback.
 * Clean, simple, and performant.
 */
import * as THREE from 'three';
import WebGPURenderer from 'three/addons/renderers/webgpu/WebGPURenderer.js';
import { VoxelRenderer } from './VoxelRenderer';
import { AvatarSystem } from './AvatarSystem';
import { CameraController, type CameraMode } from './Camera';
import { BuildingTool, type BuildMode } from './BuildingTool';
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
  // Three.js core
  private renderer!: THREE.WebGLRenderer | WebGPURenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;

  // Renderer type
  private isWebGPU = false;

  // Subsystems
  voxelRenderer: VoxelRenderer;
  avatarSystem: AvatarSystem;
  cameraController: CameraController;
  buildingTool: BuildingTool;

  // State
  private animationFrameId: number | null = null;
  private mouseNDC = new THREE.Vector2();
  private raycaster = new THREE.Raycaster();
  private onEntityClick: ((entityId: string) => void) | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private canvas: HTMLCanvasElement;

  // Touch tap detection
  private touchStartPos: { x: number; y: number } | null = null;
  private touchStartTime = 0;

  // Initialization promise
  private initPromise: Promise<void>;

  constructor(options: WorldSceneOptions) {
    const { canvas, labelContainer, onProposal, onEntityClick } = options;
    this.canvas = canvas;

    // Scene setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0a1a);

    // Camera
    this.camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      1000,
    );

    this.clock = new THREE.Clock();

    // Initialize subsystems (before renderer - they don't need it)
    this.voxelRenderer = new VoxelRenderer(this.scene);
    this.avatarSystem = new AvatarSystem(this.scene);
    this.avatarSystem.setLabelContainer(labelContainer);
    this.cameraController = new CameraController(this.camera);
    this.cameraController.attach(canvas);
    this.buildingTool = new BuildingTool(this.scene, this.camera, this.voxelRenderer);

    if (onProposal) {
      this.buildingTool.setProposalCallback(onProposal);
    }
    this.onEntityClick = onEntityClick || null;

    // Initialize renderer (async for WebGPU)
    this.initPromise = this.initRenderer(canvas);

    // Setup lighting
    this.setupLighting();

    // Input events
    canvas.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('click', this.onClick);
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('resize', this.onResize);

    // Touch events
    canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });

    // ResizeObserver
    this.resizeObserver = new ResizeObserver(() => this.onResize());
    this.resizeObserver.observe(canvas);
  }

  /**
   * Initialize renderer - WebGPU if available, WebGL fallback.
   */
  private async initRenderer(canvas: HTMLCanvasElement): Promise<void> {
    // Check WebGPU support
    if (navigator.gpu) {
      try {
        const adapter = await navigator.gpu.requestAdapter();
        if (adapter) {
          console.log('[WorldScene] WebGPU supported, initializing...');

          const renderer = new WebGPURenderer({
            canvas,
            antialias: true,
          });

          await renderer.init();

          renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
          renderer.setSize(canvas.clientWidth, canvas.clientHeight);

          this.renderer = renderer;
          this.isWebGPU = true;
          console.log('[WorldScene] WebGPU renderer initialized');

          // Start render loop
          this.animate();
          return;
        }
      } catch (e) {
        console.warn('[WorldScene] WebGPU init failed, falling back to WebGL:', e);
      }
    }

    // Fallback to WebGL
    console.log('[WorldScene] Using WebGL renderer');

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
    });

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;

    this.renderer = renderer;
    this.isWebGPU = false;

    // Start render loop
    this.animate();
  }

  /**
   * Setup scene lighting.
   */
  private setupLighting(): void {
    // Ambient light - soft blue-purple tint
    const ambient = new THREE.AmbientLight(0x4444aa, 0.6);
    this.scene.add(ambient);

    // Hemisphere light - sky/ground colors
    const hemi = new THREE.HemisphereLight(0x6666ff, 0x444422, 0.4);
    this.scene.add(hemi);

    // Main directional light - warm tone
    const directional = new THREE.DirectionalLight(0xffeedd, 1.0);
    directional.position.set(50, 80, 30);
    directional.castShadow = true;
    directional.shadow.mapSize.width = 2048;
    directional.shadow.mapSize.height = 2048;
    directional.shadow.camera.near = 0.5;
    directional.shadow.camera.far = 200;
    directional.shadow.camera.left = -50;
    directional.shadow.camera.right = 50;
    directional.shadow.camera.top = 50;
    directional.shadow.camera.bottom = -50;
    directional.shadow.bias = -0.001;
    this.scene.add(directional);

    // Add simple ground plane for reference
    const groundGeo = new THREE.PlaneGeometry(200, 200);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x222233,
      roughness: 0.9,
      metalness: 0.1,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.5;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Simple fog for atmosphere
    this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.008);
  }

  // ---- Public API ----

  /**
   * Wait for renderer initialization.
   */
  async ready(): Promise<void> {
    return this.initPromise;
  }

  /**
   * Check if using WebGPU.
   */
  isUsingWebGPU(): boolean {
    return this.isWebGPU;
  }

  /**
   * Load initial world voxels.
   */
  loadVoxels(voxels: Voxel[]): void {
    this.voxelRenderer.loadWorld(voxels);
  }

  /**
   * Apply incremental voxel updates from server.
   */
  applyVoxelUpdates(updates: VoxelUpdate[]): void {
    this.voxelRenderer.applyUpdates(updates);
  }

  /**
   * Update all entities from server state.
   */
  updateEntities(entities: EntityV3[]): void {
    const currentIds = new Set(entities.map(e => e.id));

    // Remove entities no longer present
    for (const id of Array.from(this.avatarSystem.getAllPositions().keys())) {
      if (!currentIds.has(id)) {
        this.avatarSystem.removeEntity(id);
      }
    }

    // Upsert all entities
    for (const entity of entities) {
      this.avatarSystem.upsertEntity(entity);
    }
  }

  /**
   * Update entity positions from socket event.
   */
  updateEntityPositions(positions: SocketEntityPosition[]): void {
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

  /**
   * Show speech bubble for an entity.
   */
  handleSpeechEvent(event: SocketSpeechEvent): void {
    const entityPos = this.avatarSystem.getEntityPosition(event.entityId);
    if (entityPos) {
      this.avatarSystem.showSpeech(event.entityId, event.text);
    } else if (event.position) {
      this.avatarSystem.showSpeechAtPosition(event.text, event.position);
    }
  }

  /**
   * Load structures (for sign rendering).
   */
  loadStructures(_structures: StructureInfo[]): void {
    // TODO: Implement sign rendering
  }

  /**
   * Set camera mode.
   */
  setCameraMode(mode: CameraMode): void {
    this.cameraController.setMode(mode);
  }

  /**
   * Follow an entity with the camera.
   */
  followEntity(entityId: string): void {
    this.cameraController.followEntity(entityId, 'third_person');
  }

  /**
   * Pan the observer camera to a world position.
   */
  panTo(x: number, z: number): void {
    this.cameraController.panTo(x, z);
  }

  /**
   * Get the current camera world position.
   */
  getCameraPosition(): { x: number; y: number; z: number } {
    const p = this.cameraController.getPosition();
    return { x: p.x, y: p.y, z: p.z };
  }

  /**
   * Set building mode.
   */
  setBuildMode(mode: BuildMode): void {
    this.buildingTool.setMode(mode);
  }

  /**
   * Set build color.
   */
  setBuildColor(color: string): void {
    this.buildingTool.setColor(color);
  }

  /**
   * Set build material.
   */
  setBuildMaterial(material: 'solid' | 'glass' | 'emissive' | 'liquid'): void {
    this.buildingTool.setMaterial(material);
  }

  /**
   * Set the human player's entity ID.
   */
  setPlayerEntityId(entityId: string): void {
    this.buildingTool.setEntityId(entityId);
  }

  // ---- Animation Loop ----

  private animate = (): void => {
    this.animationFrameId = requestAnimationFrame(this.animate);

    const delta = this.clock.getDelta();

    // Update subsystems
    const entityPositions = this.avatarSystem.getAllPositions();
    this.cameraController.update(delta, entityPositions);
    this.avatarSystem.update(this.camera);

    if (this.buildingTool.getMode() !== 'none') {
      this.buildingTool.updateGhost(this.mouseNDC);
    }

    // Render
    this.renderer.render(this.scene, this.camera);
  };

  // ---- Event Handlers ----

  private onMouseMove = (e: MouseEvent): void => {
    this.mouseNDC.x = (e.clientX / this.canvas.clientWidth) * 2 - 1;
    this.mouseNDC.y = -(e.clientY / this.canvas.clientHeight) * 2 + 1;
  };

  private onClick = (_e: MouseEvent): void => {
    if (this.buildingTool.getMode() !== 'none') {
      this.buildingTool.execute();
      return;
    }

    if (this.onEntityClick) {
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

        if (this.buildingTool.getMode() !== 'none') {
          this.buildingTool.execute();
        } else if (this.onEntityClick) {
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
    this.renderer.setSize(width, height);
  };

  // ---- Cleanup ----

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

    this.voxelRenderer.dispose();
    this.avatarSystem.dispose();
    this.cameraController.dispose();
    this.buildingTool.dispose();

    this.renderer.dispose();
  }
}
