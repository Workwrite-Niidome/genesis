/**
 * GENESIS v3 WorldScene
 *
 * Master scene manager that ties together:
 * - VoxelRenderer (blocks)
 * - AvatarSystem (entities)
 * - CameraController (navigation)
 * - BuildingTool (construction)
 * - Lighting, environment, post-processing & atmospheric effects
 *
 * Visual style: Twilight/dusk atmosphere inspired by 超かぐや姫 (Super Kaguya-hime)
 */
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { SSAOPass } from 'three/examples/jsm/postprocessing/SSAOPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { GodRaysShader } from './shaders/GodRaysShader';
import { VignetteShader } from './shaders/VignetteShader';
import { FilmGrainShader } from './shaders/FilmGrainShader';
import { VoxelRenderer } from './VoxelRenderer';
import { AvatarSystem } from './AvatarSystem';
import { CameraController, type CameraMode } from './Camera';
import { BuildingTool, type BuildMode } from './BuildingTool';
import { WaterPlane } from './WaterPlane';
import { GroundSystem } from './GroundSystem';
import { ParticleSystem } from './ParticleSystem';
import { ProceduralStructures } from './ProceduralStructures';
import { AssetLoader } from './AssetLoader';
import { AssetManager } from './AssetManager';
import { ProceduralSky } from './ProceduralSky';
import type {
  EntityV3, Voxel, VoxelUpdate, StructureInfo,
  ActionProposal, SocketEntityPosition,
  SocketSpeechEvent,
} from '../types/v3';

/** Data needed to render a sign in the world. */
export interface SignData {
  id: string;
  text: string;
  fontSize: number;
  position: { x: number; y: number; z: number };
}

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

  // Post-processing
  private composer: EffectComposer;
  private filmGrainPass: ShaderPass;

  // Subsystems
  voxelRenderer: VoxelRenderer;
  avatarSystem: AvatarSystem;
  cameraController: CameraController;
  buildingTool: BuildingTool;

  // Atmospheric effects
  private waterPlane: WaterPlane;
  private groundSystem: GroundSystem;
  private particleSystem: ParticleSystem;
  private proceduralStructures: ProceduralStructures;

  // Asset loading system
  private assetLoader: AssetLoader;
  private assetManager: AssetManager;

  // State
  private animationFrameId: number | null = null;
  private mouseNDC = new THREE.Vector2();
  private raycaster = new THREE.Raycaster();
  private onEntityClick: ((entityId: string) => void) | null = null;
  private resizeObserver: ResizeObserver | null = null;

  // Touch tap detection
  private touchStartPos: { x: number; y: number } | null = null;
  private touchStartTime = 0;

  // Procedural sky texture (equirectangular, used as background + environment)
  private skyTexture: THREE.Texture | null = null;

  // Sign rendering
  private signSprites: Map<string, THREE.Sprite> = new Map();

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

    // Cinematic tone mapping (ACESFilmic for rich color grading)
    // Exposure reduced to prevent washed-out appearance
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.9;

    this.scene = new THREE.Scene();

    // Atmospheric fog: deep indigo-purple tint for depth and mystery
    // Color matches the sky horizon for seamless blending
    // Density reduced to allow structures to be visible at reasonable distances
    const fogColor = new THREE.Color(0x1a0a2e);
    this.scene.fog = new THREE.FogExp2(fogColor, 0.004);

    this.camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      2000,
    );

    this.clock = new THREE.Clock();

    // Setup lighting and environment details
    this.setupLighting();
    this.setupEnvironment();

    // Procedural equirectangular sky: replaces the old sky dome mesh with a
    // canvas-rendered texture featuring stars, aurora, moon, and clouds.
    // Also sets scene.environment for PBR reflections on all materials.
    this.skyTexture = ProceduralSky.apply(this.scene, this.renderer);

    // Post-processing pipeline
    this.composer = new EffectComposer(this.renderer);

    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);

    // SSAOPass: soft contact shadows in crevices and where objects meet surfaces
    const ssaoPass = new SSAOPass(this.scene, this.camera, canvas.clientWidth, canvas.clientHeight);
    ssaoPass.kernelRadius = 8;
    ssaoPass.minDistance = 0.005;
    ssaoPass.maxDistance = 0.1;
    ssaoPass.output = SSAOPass.OUTPUT.Default;
    this.composer.addPass(ssaoPass);

    // UnrealBloomPass: emissive voxels and lights bloom beautifully
    // Threshold raised to 0.85 so only truly emissive objects (lanterns, ornaments) bloom
    // and the gradient sky doesn't wash out the entire scene
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(canvas.clientWidth, canvas.clientHeight),
      0.6,  // strength (reduced from 0.8)
      0.3,  // radius (reduced from 0.4)
      0.85, // threshold (raised from 0.7 to prevent sky bloom)
    );
    this.composer.addPass(bloomPass);

    // GodRaysPass: volumetric light scattering from the main directional light
    // Exposure reduced to prevent washing out the scene
    const godRaysPass = new ShaderPass(GodRaysShader);
    godRaysPass.uniforms.lightPosition.value.set(0.5, 0.3); // lower on screen
    godRaysPass.uniforms.exposure.value = 0.1;  // reduced from 0.25
    godRaysPass.uniforms.decay.value = 0.93;
    godRaysPass.uniforms.density.value = 0.5;   // reduced from 0.8
    godRaysPass.uniforms.weight.value = 0.3;    // reduced from 0.5
    this.composer.addPass(godRaysPass);

    // VignettePass: gentle edge darkening for cinematic focus
    const vignettePass = new ShaderPass(VignetteShader);
    vignettePass.uniforms.offset.value = 1.0;
    vignettePass.uniforms.darkness.value = 1.2;
    this.composer.addPass(vignettePass);

    // FilmGrainPass: barely-perceptible animated grain for film-like quality
    this.filmGrainPass = new ShaderPass(FilmGrainShader);
    this.filmGrainPass.uniforms.intensity.value = 0.04;
    this.composer.addPass(this.filmGrainPass);

    // OutputPass: final output with tone mapping applied
    const outputPass = new OutputPass();
    this.composer.addPass(outputPass);

    // Initialize subsystems
    this.voxelRenderer = new VoxelRenderer(this.scene);
    this.avatarSystem = new AvatarSystem(this.scene);
    this.avatarSystem.setLabelContainer(labelContainer);
    this.cameraController = new CameraController(this.camera);
    this.cameraController.attach(canvas);
    this.buildingTool = new BuildingTool(this.scene, this.camera, this.voxelRenderer);

    // Atmospheric effects: textured ground, reflective water + ethereal particles
    this.groundSystem = new GroundSystem(this.scene);
    this.waterPlane = new WaterPlane(this.scene);
    this.particleSystem = new ParticleSystem(this.scene);

    // Procedural Japanese-themed 3D structures (torii, lanterns, shrines, paths, trees)
    this.proceduralStructures = new ProceduralStructures(this.scene);

    // Asset loading system: tries to load HDRI skybox and GLTF models from /assets/
    // Falls back gracefully to procedural sky dome and structures if no assets exist
    this.assetLoader = new AssetLoader();
    this.assetManager = new AssetManager(this.scene, this.renderer, this.assetLoader);

    // Kick off async asset loading (non-blocking -- scene renders immediately with procedural fallbacks)
    this.assetManager.applySkybox().catch((err) => {
      console.warn('[WorldScene] Skybox loading failed, using procedural sky dome:', err);
    });
    this.assetManager.loadAndPlaceModels(this.proceduralStructures).catch((err) => {
      console.warn('[WorldScene] Model loading failed, using procedural structures:', err);
    });

    if (onProposal) {
      this.buildingTool.setProposalCallback(onProposal);
    }
    this.onEntityClick = onEntityClick || null;

    // Input events
    canvas.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('click', this.onClick);
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('resize', this.onResize);

    // Touch events for mobile entity selection
    canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });

    // ResizeObserver for reliable sizing (mobile URL bar, orientation change)
    this.resizeObserver = new ResizeObserver(() => this.onResize());
    this.resizeObserver.observe(canvas);

    // Start render loop
    this.animate();
  }

  // ---- Scene Setup ----

  private setupLighting(): void {
    // Ambient light: subtle blue-purple moonlight tint
    const ambient = new THREE.AmbientLight(0x2a1a4e, 0.5);
    this.scene.add(ambient);

    // Hemisphere light: deep blue sky / warm amber ground for natural ambient
    const hemi = new THREE.HemisphereLight(0x1a1a5e, 0xcc8844, 0.4);
    this.scene.add(hemi);

    // Directional light: warm sunset/twilight tone (the "last light" in the sky)
    const directional = new THREE.DirectionalLight(0xffd4a0, 0.9);
    directional.position.set(50, 100, 30);
    directional.castShadow = true;
    directional.shadow.mapSize.width = 2048;
    directional.shadow.mapSize.height = 2048;
    directional.shadow.camera.near = 0.5;
    directional.shadow.camera.far = 200;
    directional.shadow.camera.left = -60;
    directional.shadow.camera.right = 60;
    directional.shadow.camera.top = 60;
    directional.shadow.camera.bottom = -60;
    directional.shadow.bias = -0.001;
    this.scene.add(directional);

    // Point lights for atmosphere (purple and cyan theme -- Kaguya-hime feel)
    const purpleLight = new THREE.PointLight(0x7b2ff7, 0.6, 250);
    purpleLight.position.set(-30, 20, -30);
    this.scene.add(purpleLight);

    const cyanLight = new THREE.PointLight(0x00d4ff, 0.6, 250);
    cyanLight.position.set(30, 15, 30);
    this.scene.add(cyanLight);

    // Additional soft pink/magenta fill from opposite side (anime glow feel)
    const pinkLight = new THREE.PointLight(0xff69b4, 0.3, 300);
    pinkLight.position.set(0, 40, -50);
    this.scene.add(pinkLight);
  }

  private setupEnvironment(): void {
    // Ground is now handled by GroundSystem (instantiated separately)
    // Stars are now part of the procedural equirectangular sky texture

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
   * If the entity has no avatar (e.g. observer chat), render the bubble
   * at the provided position instead.  The visual is identical either way.
   */
  handleSpeechEvent(event: SocketSpeechEvent): void {
    // Try entity-attached bubble first
    const entityPos = this.avatarSystem.getEntityPosition(event.entityId);
    if (entityPos) {
      this.avatarSystem.showSpeech(event.entityId, event.text);
    } else if (event.position) {
      // No avatar found — render at the world position (observer chat)
      this.avatarSystem.showSpeechAtPosition(event.text, event.position);
    }
  }

  /**
   * Load structures and render any signs among them.
   */
  loadStructures(structures: StructureInfo[]): void {
    for (const structure of structures) {
      if (structure.structureType === 'sign') {
        const props = structure.properties || {};
        const text = props.text || '';
        const fontSize = props.font_size ?? 1.0;
        if (text) {
          this.addSign({
            id: structure.id,
            text,
            fontSize,
            position: {
              x: (structure.bounds.min.x + structure.bounds.max.x) / 2,
              y: (structure.bounds.min.y + structure.bounds.max.y) / 2 + 1.5,
              z: (structure.bounds.min.z + structure.bounds.max.z) / 2,
            },
          });
        }
      }
    }
  }

  /**
   * Add a single sign sprite to the scene.
   */
  addSign(sign: SignData): void {
    // Remove existing sign at the same ID if present
    this.removeSign(sign.id);

    const sprite = this.createSignSprite(sign.text, sign.fontSize);
    sprite.position.set(sign.position.x, sign.position.y, sign.position.z);
    this.scene.add(sprite);
    this.signSprites.set(sign.id, sprite);
  }

  /**
   * Remove a sign sprite from the scene.
   */
  removeSign(signId: string): void {
    const existing = this.signSprites.get(signId);
    if (existing) {
      this.scene.remove(existing);
      existing.material.map?.dispose();
      (existing.material as THREE.SpriteMaterial).dispose();
      this.signSprites.delete(signId);
    }
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
   * Pan the observer camera to a world position (x, z).
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
   * Set the human player's entity ID (for building).
   */
  setPlayerEntityId(entityId: string): void {
    this.buildingTool.setEntityId(entityId);
  }

  // ---- Sign Rendering ----

  /**
   * Create a text sprite for a sign using a canvas texture.
   */
  private createSignSprite(text: string, fontSize: number): THREE.Sprite {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;

    // Measure and configure the canvas
    const baseFontSize = Math.round(32 * fontSize);
    const font = `bold ${baseFontSize}px monospace`;
    ctx.font = font;

    const padding = 20;
    const maxWidth = 512;

    // Word-wrap the text to fit within maxWidth
    const lines = this.wrapText(ctx, text, maxWidth - padding * 2);
    const lineHeight = baseFontSize * 1.3;

    const textWidth = Math.min(
      maxWidth,
      Math.max(...lines.map(line => ctx.measureText(line).width)) + padding * 2
    );
    const textHeight = lines.length * lineHeight + padding * 2;

    // Resize canvas to power-of-two friendly dimensions
    canvas.width = Math.min(512, Math.pow(2, Math.ceil(Math.log2(textWidth))));
    canvas.height = Math.min(256, Math.pow(2, Math.ceil(Math.log2(textHeight))));

    // Background (dark translucent panel)
    ctx.fillStyle = 'rgba(10, 10, 20, 0.85)';
    ctx.roundRect(2, 2, canvas.width - 4, canvas.height - 4, 8);
    ctx.fill();

    // Border (subtle glow)
    ctx.strokeStyle = 'rgba(123, 47, 247, 0.6)';
    ctx.lineWidth = 2;
    ctx.roundRect(2, 2, canvas.width - 4, canvas.height - 4, 8);
    ctx.stroke();

    // Text
    ctx.font = font;
    ctx.fillStyle = '#FFFFFF';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    const startY = (canvas.height - lines.length * lineHeight) / 2;
    for (let i = 0; i < lines.length; i++) {
      ctx.fillText(lines[i], canvas.width / 2, startY + i * lineHeight);
    }

    // Create sprite material from the canvas
    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;

    const spriteMaterial = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: true,
      depthWrite: false,
    });

    const sprite = new THREE.Sprite(spriteMaterial);

    // Scale the sprite to world units (roughly 1 unit per 64 pixels)
    const aspect = canvas.width / canvas.height;
    const spriteHeight = 1.5 * fontSize;
    sprite.scale.set(spriteHeight * aspect, spriteHeight, 1);

    return sprite;
  }

  /**
   * Word-wrap text to fit within a maximum pixel width.
   */
  private wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
    const words = text.split(' ');
    const lines: string[] = [];
    let currentLine = '';

    for (const word of words) {
      const testLine = currentLine ? `${currentLine} ${word}` : word;
      const metrics = ctx.measureText(testLine);

      if (metrics.width > maxWidth && currentLine) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = testLine;
      }
    }

    if (currentLine) {
      lines.push(currentLine);
    }

    return lines.length > 0 ? lines : [''];
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

    // Update atmospheric effects
    const elapsed = this.clock.elapsedTime;
    this.waterPlane.update(elapsed);
    this.waterPlane.setCameraPosition(this.camera.position);
    this.particleSystem.update(elapsed);

    // Animate film grain noise pattern each frame
    this.filmGrainPass.uniforms.time.value = elapsed;

    // Render through post-processing pipeline
    // Pipeline: RenderPass -> SSAOPass -> UnrealBloomPass -> GodRaysPass -> VignettePass -> FilmGrainPass -> OutputPass
    this.composer.render();
  };

  // ---- Event Handlers ----

  private onMouseMove = (e: MouseEvent): void => {
    const canvas = this.renderer.domElement;
    this.mouseNDC.x = (e.clientX / canvas.clientWidth) * 2 - 1;
    this.mouseNDC.y = -(e.clientY / canvas.clientHeight) * 2 + 1;
  };

  private onClick = (_e: MouseEvent): void => {
    // Building mode: place/destroy/paint
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

      // Short tap with minimal movement → entity click
      if (dist < 15 && duration < 400) {
        const canvas = this.renderer.domElement;
        const rect = canvas.getBoundingClientRect();
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
    const canvas = this.renderer.domElement;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (width === 0 || height === 0) return; // skip if not laid out yet
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
    this.composer.setSize(width, height);
  };

  // ---- Cleanup ----

  dispose(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
    }

    const canvas = this.renderer.domElement;
    canvas.removeEventListener('mousemove', this.onMouseMove);
    canvas.removeEventListener('click', this.onClick);
    canvas.removeEventListener('touchstart', this.onTouchStart);
    canvas.removeEventListener('touchend', this.onTouchEnd);
    window.removeEventListener('resize', this.onResize);
    this.resizeObserver?.disconnect();

    this.voxelRenderer.dispose();
    this.avatarSystem.dispose();
    this.cameraController.dispose();
    this.buildingTool.dispose();
    this.groundSystem.dispose();
    this.waterPlane.dispose();
    this.particleSystem.dispose();
    this.proceduralStructures.dispose();
    this.assetManager.dispose();
    this.assetLoader.dispose();
    this.skyTexture?.dispose();

    // Dispose all sign sprites
    for (const [_id, sprite] of this.signSprites) {
      this.scene.remove(sprite);
      sprite.material.map?.dispose();
      (sprite.material as THREE.SpriteMaterial).dispose();
    }
    this.signSprites.clear();

    this.composer.dispose();
    this.renderer.dispose();
  }
}
