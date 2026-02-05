/**
 * GENESIS v3 WorldScene
 *
 * Minimal, reliable 3D scene.
 * Step 1: Just render a cube. Make sure it works.
 */
import * as THREE from 'three';
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
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;
  private canvas: HTMLCanvasElement;

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

  // Touch
  private touchStartPos: { x: number; y: number } | null = null;
  private touchStartTime = 0;

  // Template loaded flag
  private templateLoaded = false;

  constructor(options: WorldSceneOptions) {
    const { canvas, labelContainer, onProposal, onEntityClick } = options;
    this.canvas = canvas;

    console.log('[WorldScene] Initializing...');

    // === Renderer (WebGL only - simple and reliable) ===
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    this.renderer.setClearColor(0x1a1a2e);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    console.log('[WorldScene] Renderer created');

    // === Scene ===
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a2e);

    // === Camera ===
    this.camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      500,
    );
    this.camera.position.set(0, 15, 40);
    this.camera.lookAt(0, 0, 0);

    this.clock = new THREE.Clock();

    // === Lighting ===
    this.setupLighting();

    // === Ground plane (simple reference) ===
    const groundGeo = new THREE.PlaneGeometry(200, 200);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x2a2a3a,
      roughness: 0.9,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.5;
    ground.receiveShadow = true;
    this.scene.add(ground);

    console.log('[WorldScene] Ground added');

    // === Subsystems ===
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

    console.log('[WorldScene] Subsystems initialized');

    // === Load initial template ===
    this.loadInitialTemplate();

    // === Events ===
    canvas.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('click', this.onClick);
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('resize', this.onResize);
    canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });

    this.resizeObserver = new ResizeObserver(() => this.onResize());
    this.resizeObserver.observe(canvas);

    // === Start render loop ===
    this.animate();

    console.log('[WorldScene] Initialization complete');
  }

  private setupLighting(): void {
    // Ambient - make sure everything is visible
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambient);

    // Hemisphere
    const hemi = new THREE.HemisphereLight(0x8888ff, 0x444422, 0.5);
    this.scene.add(hemi);

    // Main directional light
    const sun = new THREE.DirectionalLight(0xffffff, 1.0);
    sun.position.set(30, 50, 30);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 150;
    sun.shadow.camera.left = -50;
    sun.shadow.camera.right = 50;
    sun.shadow.camera.top = 50;
    sun.shadow.camera.bottom = -50;
    this.scene.add(sun);

    console.log('[WorldScene] Lighting setup complete');
  }

  private loadInitialTemplate(): void {
    console.log('[WorldScene] Loading initial template...');

    const voxels = VoxelTemplates.generateInitialWorld();
    console.log('[WorldScene] Generated', voxels.length, 'voxels');

    this.voxelRenderer.loadWorld(voxels);
    this.templateLoaded = true;

    console.log('[WorldScene] Template loaded, voxel count:', this.voxelRenderer.getVoxelCount());
  }

  // === Public API ===

  async ready(): Promise<void> {
    // No async init needed for WebGL
    return Promise.resolve();
  }

  isUsingWebGPU(): boolean {
    return false;
  }

  loadVoxels(voxels: Voxel[]): void {
    // Only load if we have voxels from server (override template)
    if (voxels.length > 0) {
      console.log('[WorldScene] Loading', voxels.length, 'voxels from server');
      this.voxelRenderer.loadWorld(voxels);
    } else if (!this.templateLoaded) {
      // Fallback to template if not already loaded
      this.loadInitialTemplate();
    }
  }

  applyVoxelUpdates(updates: VoxelUpdate[]): void {
    this.voxelRenderer.applyUpdates(updates);
  }

  updateEntities(entities: EntityV3[]): void {
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
    const entityPos = this.avatarSystem.getEntityPosition(event.entityId);
    if (entityPos) {
      this.avatarSystem.showSpeech(event.entityId, event.text);
    } else if (event.position) {
      this.avatarSystem.showSpeechAtPosition(event.text, event.position);
    }
  }

  loadStructures(_structures: StructureInfo[]): void {
    // TODO
  }

  setCameraMode(mode: CameraMode): void {
    this.cameraController.setMode(mode);
  }

  followEntity(entityId: string): void {
    this.cameraController.followEntity(entityId, 'third_person');
  }

  panTo(x: number, z: number): void {
    this.cameraController.panTo(x, z);
  }

  getCameraPosition(): { x: number; y: number; z: number } {
    const p = this.cameraController.getPosition();
    return { x: p.x, y: p.y, z: p.z };
  }

  setBuildMode(mode: BuildMode): void {
    this.buildingTool.setMode(mode);
  }

  setBuildColor(color: string): void {
    this.buildingTool.setColor(color);
  }

  setBuildMaterial(material: 'solid' | 'glass' | 'emissive' | 'liquid'): void {
    this.buildingTool.setMaterial(material);
  }

  setPlayerEntityId(entityId: string): void {
    this.buildingTool.setEntityId(entityId);
  }

  // === Animation Loop ===

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

  // === Event Handlers ===

  private onMouseMove = (e: MouseEvent): void => {
    this.mouseNDC.x = (e.clientX / this.canvas.clientWidth) * 2 - 1;
    this.mouseNDC.y = -(e.clientY / this.canvas.clientHeight) * 2 + 1;
  };

  private onClick = (): void => {
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

    this.voxelRenderer.dispose();
    this.avatarSystem.dispose();
    this.cameraController.dispose();
    this.buildingTool.dispose();

    this.renderer.dispose();
  }
}
