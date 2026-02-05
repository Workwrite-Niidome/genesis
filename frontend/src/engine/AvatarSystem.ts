/**
 * GENESIS v3 Avatar System
 *
 * Renders entities as stylized humanoid 3D avatars.
 * All entities (AI, user agent, human) use the same visual system.
 * No labels or indicators reveal whether an entity is AI or human.
 */
import * as THREE from 'three';
import type { EntityV3, EntityAppearance } from '../types/v3';

const INTERPOLATION_SPEED = 0.15;
const SPEECH_BUBBLE_DURATION = 5000; // ms
const FLOATING_SPEECH_DURATION = 6000; // ms — slightly longer for position-based bubbles

interface AvatarInstance {
  entityId: string;
  group: THREE.Group;
  bodyMesh: THREE.Mesh; // invisible hitbox for raycasting
  headMesh: THREE.Mesh;
  torsoMesh: THREE.Mesh;
  leftEyeMesh: THREE.Mesh;
  rightEyeMesh: THREE.Mesh;
  accentMesh: THREE.Mesh;
  glowLight: THREE.PointLight | null;
  label: HTMLDivElement | null;
  targetPosition: THREE.Vector3;
  currentAction?: string;
  speechBubble: HTMLDivElement | null;
  speechTimeout: ReturnType<typeof setTimeout> | null;
  appearance: EntityAppearance;
  isAlive: boolean;
  /** Stable hash derived from entity ID, used to stagger animations. */
  entityHash: number;
}

/** A floating speech bubble not attached to any entity. */
interface FloatingBubble {
  element: HTMLDivElement;
  worldPos: THREE.Vector3;
  timeout: ReturnType<typeof setTimeout>;
}

/**
 * Derive a stable numeric hash from a string (entity ID).
 * Used for staggered idle animation so entities don't bob in unison.
 */
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + ch;
    hash |= 0; // Convert to 32-bit integer
  }
  return hash;
}

/**
 * Lighten a THREE.Color by mixing it toward white.
 */
function lightenColor(color: THREE.Color, amount: number): THREE.Color {
  const lightened = color.clone();
  lightened.r = lightened.r + (1 - lightened.r) * amount;
  lightened.g = lightened.g + (1 - lightened.g) * amount;
  lightened.b = lightened.b + (1 - lightened.b) * amount;
  return lightened;
}

export class AvatarSystem {
  private scene: THREE.Scene;
  private avatars: Map<string, AvatarInstance> = new Map();
  private labelContainer: HTMLElement | null = null;
  /** Speech bubbles rendered at arbitrary world positions (observer chat). */
  private floatingBubbles: FloatingBubble[] = [];

  // Shared geometries (created once, reused across all avatars)
  private torsoGeometry: THREE.CapsuleGeometry;
  private headGeometry: THREE.SphereGeometry;
  private eyeGeometry: THREE.SphereGeometry;
  private accentGeometry: THREE.BoxGeometry;
  private hitboxGeometry: THREE.BoxGeometry;

  constructor(scene: THREE.Scene) {
    this.scene = scene;

    // Pre-create shared geometries for performance
    // Torso: capsule ~1.0 tall, ~0.25 radius
    this.torsoGeometry = new THREE.CapsuleGeometry(0.25, 0.5, 8, 16);
    // Head: sphere radius ~0.25
    this.headGeometry = new THREE.SphereGeometry(0.25, 16, 16);
    // Eyes: small spheres
    this.eyeGeometry = new THREE.SphereGeometry(0.05, 8, 8);
    // Accent belt: thin box wrapping around the torso middle
    this.accentGeometry = new THREE.BoxGeometry(0.55, 0.06, 0.35);
    // Invisible hitbox for raycasting
    this.hitboxGeometry = new THREE.BoxGeometry(1.0, 2.0, 0.8);
  }

  /**
   * Set the HTML container for floating labels.
   */
  setLabelContainer(container: HTMLElement): void {
    this.labelContainer = container;
  }

  /**
   * Create or update an avatar for an entity.
   */
  upsertEntity(entity: EntityV3): void {
    let avatar = this.avatars.get(entity.id);

    if (!avatar) {
      avatar = this.createAvatar(entity);
      this.avatars.set(entity.id, avatar);
      this.scene.add(avatar.group);
    }

    // Update target position for interpolation
    avatar.targetPosition.set(
      entity.position.x,
      entity.position.y,
      entity.position.z,
    );
    avatar.currentAction = entity.state.currentAction;

    // Handle alive <-> dead transitions
    const wasAlive = avatar.isAlive;
    avatar.isAlive = entity.isAlive;

    if (!entity.isAlive && wasAlive) {
      // Entity just died: gray out, disable glow, lie down
      this.applyDeadAppearance(avatar);
    } else if (entity.isAlive && !wasAlive) {
      // Entity revived: restore appearance
      this.applyAliveAppearance(avatar, entity.appearance);
    }
  }

  /**
   * Remove an entity's avatar.
   */
  removeEntity(entityId: string): void {
    const avatar = this.avatars.get(entityId);
    if (!avatar) return;

    this.scene.remove(avatar.group);
    avatar.group.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        // Don't dispose shared geometries -- only dispose materials
        child.material instanceof THREE.Material
          ? child.material.dispose()
          : Array.isArray(child.material) && child.material.forEach(m => m.dispose());
      }
    });

    if (avatar.label && avatar.label.parentNode) {
      avatar.label.parentNode.removeChild(avatar.label);
    }
    if (avatar.speechBubble && avatar.speechBubble.parentNode) {
      avatar.speechBubble.parentNode.removeChild(avatar.speechBubble);
    }
    if (avatar.speechTimeout) clearTimeout(avatar.speechTimeout);

    this.avatars.delete(entityId);
  }

  /**
   * Show a speech bubble above an entity.
   */
  showSpeech(entityId: string, text: string): void {
    const avatar = this.avatars.get(entityId);
    if (!avatar || !this.labelContainer) return;

    if (avatar.speechTimeout) {
      clearTimeout(avatar.speechTimeout);
    }

    if (!avatar.speechBubble) {
      const bubble = document.createElement('div');
      bubble.className = 'genesis-speech-bubble';
      bubble.style.cssText = `
        position: absolute;
        padding: 4px 8px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        border-radius: 6px;
        font-size: 12px;
        max-width: 200px;
        word-wrap: break-word;
        pointer-events: none;
        transform: translate(-50%, -100%);
        z-index: 100;
      `;
      this.labelContainer.appendChild(bubble);
      avatar.speechBubble = bubble;
    }

    avatar.speechBubble.textContent = text.slice(0, 100);
    avatar.speechBubble.style.display = 'block';

    avatar.speechTimeout = setTimeout(() => {
      if (avatar.speechBubble) {
        avatar.speechBubble.style.display = 'none';
      }
    }, SPEECH_BUBBLE_DURATION);
  }

  /**
   * Show a speech bubble at a world position (no entity required).
   * Used for observer chat messages that have no avatar in the system.
   * The visual style is identical to entity speech bubbles.
   */
  showSpeechAtPosition(text: string, position: { x: number; y: number; z: number }): void {
    if (!this.labelContainer) return;

    const bubble = document.createElement('div');
    bubble.className = 'genesis-speech-bubble';
    bubble.style.cssText = `
      position: absolute;
      padding: 4px 8px;
      background: rgba(0, 0, 0, 0.8);
      color: white;
      border-radius: 6px;
      font-size: 12px;
      max-width: 200px;
      word-wrap: break-word;
      pointer-events: none;
      transform: translate(-50%, -100%);
      z-index: 100;
    `;
    bubble.textContent = text.slice(0, 100);
    this.labelContainer.appendChild(bubble);

    const worldPos = new THREE.Vector3(position.x, position.y + 3, position.z);

    const entry: FloatingBubble = {
      element: bubble,
      worldPos,
      timeout: setTimeout(() => {
        bubble.remove();
        const idx = this.floatingBubbles.indexOf(entry);
        if (idx !== -1) this.floatingBubbles.splice(idx, 1);
      }, FLOATING_SPEECH_DURATION),
    };

    this.floatingBubbles.push(entry);
  }

  /**
   * Update avatar positions (interpolation), idle animation, and labels.
   * Call each frame.
   */
  update(camera: THREE.Camera): void {
    const time = Date.now() * 0.001;

    for (const avatar of this.avatars.values()) {
      // Smooth position interpolation
      avatar.group.position.lerp(avatar.targetPosition, INTERPOLATION_SPEED);

      // Idle animation for alive entities
      if (avatar.isAlive) {
        // Gentle vertical bobbing, staggered per entity
        const bob = Math.sin(time * 2 + avatar.entityHash) * 0.05;
        avatar.group.position.y = avatar.targetPosition.y + bob;
      }

      // Update 2D label positions (project 3D -> screen space)
      if (avatar.label || avatar.speechBubble) {
        const worldPos = avatar.group.position.clone();
        worldPos.y += 3; // Above the entity
        worldPos.project(camera);

        const x = (worldPos.x * 0.5 + 0.5) * window.innerWidth;
        const y = (-worldPos.y * 0.5 + 0.5) * window.innerHeight;

        // Only show if in front of camera
        const visible = worldPos.z < 1;

        if (avatar.label) {
          avatar.label.style.left = `${x}px`;
          avatar.label.style.top = `${y}px`;
          avatar.label.style.display = visible ? 'block' : 'none';
        }
        if (avatar.speechBubble && avatar.speechBubble.style.display !== 'none') {
          avatar.speechBubble.style.left = `${x}px`;
          avatar.speechBubble.style.top = `${y - 20}px`;
        }
      }
    }

    // Project floating speech bubbles (observer chat)
    for (const fb of this.floatingBubbles) {
      const projected = fb.worldPos.clone().project(camera);
      const sx = (projected.x * 0.5 + 0.5) * window.innerWidth;
      const sy = (-projected.y * 0.5 + 0.5) * window.innerHeight;
      const visible = projected.z < 1;
      fb.element.style.left = `${sx}px`;
      fb.element.style.top = `${sy}px`;
      fb.element.style.display = visible ? 'block' : 'none';
    }
  }

  /**
   * Get entity position (for camera follow).
   */
  getEntityPosition(entityId: string): THREE.Vector3 | null {
    const avatar = this.avatars.get(entityId);
    return avatar ? avatar.group.position.clone() : null;
  }

  /**
   * Get all entity positions (for camera).
   */
  getAllPositions(): Map<string, THREE.Vector3> {
    const positions = new Map<string, THREE.Vector3>();
    for (const [id, avatar] of this.avatars) {
      positions.set(id, avatar.group.position.clone());
    }
    return positions;
  }

  /**
   * Get entity at screen position (for clicking).
   */
  raycast(raycaster: THREE.Raycaster): string | null {
    const meshes = Array.from(this.avatars.values()).map(a => a.bodyMesh);
    const intersects = raycaster.intersectObjects(meshes, false);

    if (intersects.length > 0) {
      for (const [id, avatar] of this.avatars) {
        if (avatar.bodyMesh === intersects[0].object) {
          return id;
        }
      }
    }
    return null;
  }

  // ------------------------------------------------------------------
  // Avatar Construction
  // ------------------------------------------------------------------

  private createAvatar(entity: EntityV3): AvatarInstance {
    const group = new THREE.Group();
    group.name = `entity_${entity.id}`;

    const bodyColor = new THREE.Color(entity.appearance.bodyColor || '#4fc3f7');
    const accentColor = new THREE.Color(entity.appearance.accentColor || '#ffffff');
    const headColor = lightenColor(bodyColor, 0.2);
    const size = entity.appearance.size || 1;
    const entityHash = hashString(entity.id);

    // -- Torso (capsule) --
    const torsoMat = new THREE.MeshStandardMaterial({
      color: bodyColor,
      emissive: bodyColor,
      emissiveIntensity: entity.appearance.emissive ? 0.3 : 0.15,
      roughness: 0.4,
      metalness: 0.2,
    });
    const torsoMesh = new THREE.Mesh(this.torsoGeometry, torsoMat);
    torsoMesh.position.y = 0.75; // center of torso
    torsoMesh.castShadow = true;
    group.add(torsoMesh);

    // -- Head (sphere) --
    const headMat = new THREE.MeshStandardMaterial({
      color: headColor,
      emissive: headColor,
      emissiveIntensity: entity.appearance.emissive ? 0.3 : 0.15,
      roughness: 0.4,
      metalness: 0.2,
    });
    const headMesh = new THREE.Mesh(this.headGeometry, headMat);
    headMesh.position.y = 1.5; // on top of torso
    headMesh.castShadow = true;
    group.add(headMesh);

    // -- Eyes (two small emissive white spheres) --
    const eyeMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0xffffff,
      emissiveIntensity: 0.8,
      roughness: 0.2,
      metalness: 0.0,
    });
    const leftEye = new THREE.Mesh(this.eyeGeometry, eyeMat);
    leftEye.position.set(-0.1, 1.53, 0.22);
    leftEye.castShadow = true;
    group.add(leftEye);

    const rightEye = new THREE.Mesh(this.eyeGeometry, eyeMat);
    rightEye.position.set(0.1, 1.53, 0.22);
    rightEye.castShadow = true;
    group.add(rightEye);

    // -- Accent belt (thin box around middle of torso) --
    const accentMat = new THREE.MeshStandardMaterial({
      color: accentColor,
      emissive: accentColor,
      emissiveIntensity: 0.3,
      roughness: 0.3,
      metalness: 0.3,
    });
    const accentMesh = new THREE.Mesh(this.accentGeometry, accentMat);
    accentMesh.position.y = 0.75; // center of torso
    accentMesh.castShadow = true;
    group.add(accentMesh);

    // -- Glow indicator (PointLight) --
    const glowLight = new THREE.PointLight(bodyColor, 0.3, 5);
    glowLight.position.y = 1.0;
    group.add(glowLight);

    // -- Invisible hitbox for raycasting --
    const hitboxMat = new THREE.MeshBasicMaterial({ visible: false });
    const hitbox = new THREE.Mesh(this.hitboxGeometry, hitboxMat);
    hitbox.position.y = 1.0; // center of the avatar
    group.add(hitbox);

    // Apply entity size scaling
    group.scale.setScalar(size);

    // Set initial position
    group.position.set(entity.position.x, entity.position.y, entity.position.z);

    // -- Name label (HTML overlay) --
    let label: HTMLDivElement | null = null;
    if (this.labelContainer) {
      label = document.createElement('div');
      label.className = 'genesis-entity-label';

      // Use a wrapper with a dark background for readability
      const labelColor = entity.appearance.bodyColor || '#4fc3f7';
      label.style.cssText = `
        position: absolute;
        color: ${labelColor};
        font-size: 13px;
        font-family: monospace;
        font-weight: bold;
        padding: 2px 6px;
        background: rgba(0, 0, 0, 0.55);
        border-radius: 3px;
        text-shadow: 0 0 6px rgba(0,0,0,0.9);
        pointer-events: none;
        transform: translate(-50%, 0);
        white-space: nowrap;
        z-index: 10;
      `;
      label.textContent = entity.name;
      this.labelContainer.appendChild(label);
    }

    // Handle initially dead entities
    const instance: AvatarInstance = {
      entityId: entity.id,
      group,
      bodyMesh: hitbox,
      headMesh,
      torsoMesh,
      leftEyeMesh: leftEye,
      rightEyeMesh: rightEye,
      accentMesh,
      glowLight,
      label,
      targetPosition: new THREE.Vector3(entity.position.x, entity.position.y, entity.position.z),
      currentAction: entity.state.currentAction,
      speechBubble: null,
      speechTimeout: null,
      appearance: entity.appearance,
      isAlive: entity.isAlive,
      entityHash,
    };

    if (!entity.isAlive) {
      this.applyDeadAppearance(instance);
    }

    return instance;
  }

  // ------------------------------------------------------------------
  // Dead / Alive appearance helpers
  // ------------------------------------------------------------------

  private applyDeadAppearance(avatar: AvatarInstance): void {
    const deadMat = new THREE.MeshStandardMaterial({
      color: 0x444444,
      emissive: 0x000000,
      emissiveIntensity: 0,
      roughness: 0.7,
      metalness: 0.0,
      transparent: true,
      opacity: 0.5,
    });

    avatar.torsoMesh.material = deadMat;
    avatar.headMesh.material = deadMat.clone();
    avatar.leftEyeMesh.material = deadMat.clone();
    avatar.rightEyeMesh.material = deadMat.clone();
    avatar.accentMesh.material = deadMat.clone();

    // Disable glow
    if (avatar.glowLight) {
      avatar.glowLight.intensity = 0;
    }

    // Lie down (rotate 90 degrees on X axis)
    avatar.group.rotation.x = Math.PI / 2;
  }

  private applyAliveAppearance(avatar: AvatarInstance, appearance: EntityAppearance): void {
    const bodyColor = new THREE.Color(appearance.bodyColor || '#4fc3f7');
    const accentColor = new THREE.Color(appearance.accentColor || '#ffffff');
    const headColor = lightenColor(bodyColor, 0.2);

    avatar.torsoMesh.material = new THREE.MeshStandardMaterial({
      color: bodyColor,
      emissive: bodyColor,
      emissiveIntensity: appearance.emissive ? 0.3 : 0.15,
      roughness: 0.4,
      metalness: 0.2,
    });

    avatar.headMesh.material = new THREE.MeshStandardMaterial({
      color: headColor,
      emissive: headColor,
      emissiveIntensity: appearance.emissive ? 0.3 : 0.15,
      roughness: 0.4,
      metalness: 0.2,
    });

    const eyeMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0xffffff,
      emissiveIntensity: 0.8,
      roughness: 0.2,
      metalness: 0.0,
    });
    avatar.leftEyeMesh.material = eyeMat;
    avatar.rightEyeMesh.material = eyeMat.clone();

    avatar.accentMesh.material = new THREE.MeshStandardMaterial({
      color: accentColor,
      emissive: accentColor,
      emissiveIntensity: 0.3,
      roughness: 0.3,
      metalness: 0.3,
    });

    // Re-enable glow
    if (avatar.glowLight) {
      avatar.glowLight.color.copy(bodyColor);
      avatar.glowLight.intensity = 0.3;
    }

    // Stand up
    avatar.group.rotation.x = 0;
  }

  // ------------------------------------------------------------------
  // Disposal
  // ------------------------------------------------------------------

  /**
   * Dispose all avatars and floating bubbles.
   */
  dispose(): void {
    for (const id of Array.from(this.avatars.keys())) {
      this.removeEntity(id);
    }

    // Clean up floating speech bubbles
    for (const fb of this.floatingBubbles) {
      clearTimeout(fb.timeout);
      fb.element.remove();
    }
    this.floatingBubbles = [];

    // Dispose shared geometries
    this.torsoGeometry.dispose();
    this.headGeometry.dispose();
    this.eyeGeometry.dispose();
    this.accentGeometry.dispose();
    this.hitboxGeometry.dispose();
  }
}
