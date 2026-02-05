/**
 * GENESIS v3 WorldScene
 *
 * Master scene manager that ties together:
 * - VoxelRenderer (blocks)
 * - AvatarSystem (entities)
 * - CameraController (navigation)
 * - BuildingTool (construction)
 * - Lighting and environment
 */
import * as THREE from 'three';
import { VoxelRenderer } from './VoxelRenderer';
import { AvatarSystem } from './AvatarSystem';
import { CameraController, type CameraMode } from './Camera';
import { BuildingTool, type BuildMode } from './BuildingTool';
import type {
  EntityV3, Voxel, VoxelUpdate,
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
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;

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

  constructor(options: WorldSceneOptions) {
    const { canvas, labelContainer, onProposal, onEntityClick } = options;

    // Three.js setup
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0a0f);
    this.scene.fog = new THREE.FogExp2(0x0a0a0f, 0.003);

    this.camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      2000,
    );

    this.clock = new THREE.Clock();

    // Setup lighting
    this.setupLighting();
    this.setupEnvironment();

    // Initialize subsystems
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

    // Input events
    canvas.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('click', this.onClick);
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('resize', this.onResize);

    // Start render loop
    this.animate();
  }

  // ---- Scene Setup ----

  private setupLighting(): void {
    // Ambient light (dim, to see in the void)
    const ambient = new THREE.AmbientLight(0x1a1a2e, 0.4);
    this.scene.add(ambient);

    // Hemisphere light (sky/ground color)
    const hemi = new THREE.HemisphereLight(0x2d1b69, 0x0a0a0f, 0.3);
    this.scene.add(hemi);

    // Directional light (sun-like)
    const directional = new THREE.DirectionalLight(0xffeedd, 0.8);
    directional.position.set(50, 100, 30);
    directional.castShadow = true;
    directional.shadow.mapSize.width = 2048;
    directional.shadow.mapSize.height = 2048;
    directional.shadow.camera.near = 0.5;
    directional.shadow.camera.far = 500;
    directional.shadow.camera.left = -100;
    directional.shadow.camera.right = 100;
    directional.shadow.camera.top = 100;
    directional.shadow.camera.bottom = -100;
    this.scene.add(directional);

    // Point lights for atmosphere (purple and cyan theme from v2)
    const purpleLight = new THREE.PointLight(0x7b2ff7, 0.5, 200);
    purpleLight.position.set(-30, 20, -30);
    this.scene.add(purpleLight);

    const cyanLight = new THREE.PointLight(0x00d4ff, 0.5, 200);
    cyanLight.position.set(30, 15, 30);
    this.scene.add(cyanLight);
  }

  private setupEnvironment(): void {
    // Ground grid (subtle reference plane)
    const gridHelper = new THREE.GridHelper(400, 400, 0x111122, 0x0a0a14);
    gridHelper.position.y = -0.5;
    this.scene.add(gridHelper);

    // Starfield
    const starGeometry = new THREE.BufferGeometry();
    const starCount = 3000;
    const positions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 1600;
      positions[i + 1] = Math.random() * 400 + 50;
      positions[i + 2] = (Math.random() - 0.5) * 1600;
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const starMaterial = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.5,
      transparent: true,
      opacity: 0.6,
    });
    const stars = new THREE.Points(starGeometry, starMaterial);
    this.scene.add(stars);

    // Origin marker (where the world begins)
    const originGeo = new THREE.RingGeometry(0.5, 1.0, 32);
    const originMat = new THREE.MeshBasicMaterial({
      color: 0x7b2ff7,
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide,
    });
    const originRing = new THREE.Mesh(originGeo, originMat);
    originRing.rotation.x = -Math.PI / 2;
    originRing.position.y = -0.49;
    this.scene.add(originRing);
  }

  // ---- Public API ----

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
   * Update entity positions from socket event (lightweight).
   */
  updateEntityPositions(positions: SocketEntityPosition[]): void {
    for (const pos of positions) {
      // Create a minimal entity update for position only
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
    this.avatarSystem.showSpeech(event.entityId, event.text);
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
   * Set the human player's entity ID (for building).
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
    const canvas = this.renderer.domElement;
    this.mouseNDC.x = (e.clientX / canvas.clientWidth) * 2 - 1;
    this.mouseNDC.y = -(e.clientY / canvas.clientHeight) * 2 + 1;
  };

  private onClick = (e: MouseEvent): void => {
    // Building mode: place/destroy
    if (this.buildingTool.getMode() !== 'none') {
      this.buildingTool.execute();
      return;
    }

    // Entity click detection
    if (this.onEntityClick) {
      this.raycaster.setFromCamera(this.mouseNDC, this.camera);
      const entityId = this.avatarSystem.raycast(this.raycaster);
      if (entityId) {
        this.onEntityClick(entityId);
      }
    }
  };

  private onResize = (): void => {
    const canvas = this.renderer.domElement;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  };

  // ---- Cleanup ----

  dispose(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
    }

    const canvas = this.renderer.domElement;
    canvas.removeEventListener('mousemove', this.onMouseMove);
    canvas.removeEventListener('click', this.onClick);
    window.removeEventListener('resize', this.onResize);

    this.voxelRenderer.dispose();
    this.avatarSystem.dispose();
    this.cameraController.dispose();
    this.buildingTool.dispose();
    this.renderer.dispose();
  }
}
