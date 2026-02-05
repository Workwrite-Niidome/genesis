/**
 * GENESIS v3 Avatar System
 *
 * Renders entities as voxel-based 3D avatars.
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
  bodyMesh: THREE.Mesh;
  label: HTMLDivElement | null;
  targetPosition: THREE.Vector3;
  currentAction?: string;
  speechBubble: HTMLDivElement | null;
  speechTimeout: ReturnType<typeof setTimeout> | null;
  appearance: EntityAppearance;
  isAlive: boolean;
}

// Default voxel avatar: a simple humanoid shape (5x7x3 voxels)
const DEFAULT_BODY_VOXELS: [number, number, number][] = [
  // Head (1 block)
  [0, 6, 0],
  // Body (3 tall, 1 wide)
  [0, 5, 0], [0, 4, 0], [0, 3, 0],
  // Arms
  [-1, 5, 0], [1, 5, 0],
  // Legs
  [0, 2, 0], [0, 1, 0],
  [-0.4, 0, 0], [0.4, 0, 0],
];

/** A floating speech bubble not attached to any entity. */
interface FloatingBubble {
  element: HTMLDivElement;
  worldPos: THREE.Vector3;
  timeout: ReturnType<typeof setTimeout>;
}

export class AvatarSystem {
  private scene: THREE.Scene;
  private avatars: Map<string, AvatarInstance> = new Map();
  private labelContainer: HTMLElement | null = null;
  /** Speech bubbles rendered at arbitrary world positions (observer chat). */
  private floatingBubbles: FloatingBubble[] = [];

  constructor(scene: THREE.Scene) {
    this.scene = scene;
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
    avatar.isAlive = entity.isAlive;

    // Dim dead entities
    if (!entity.isAlive) {
      avatar.bodyMesh.material = new THREE.MeshStandardMaterial({
        color: 0x444444,
        transparent: true,
        opacity: 0.3,
      });
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
        child.geometry.dispose();
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose());
        } else {
          child.material.dispose();
        }
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
   * Update avatar positions (interpolation) and labels.
   * Call each frame.
   */
  update(camera: THREE.Camera): void {
    for (const avatar of this.avatars.values()) {
      // Smooth position interpolation
      avatar.group.position.lerp(avatar.targetPosition, INTERPOLATION_SPEED);

      // Gentle floating animation for alive entities
      if (avatar.isAlive) {
        const time = Date.now() * 0.001;
        const bob = Math.sin(time * 2 + avatar.group.position.x) * 0.05;
        avatar.group.position.y = avatar.targetPosition.y + bob;
      }

      // Update 2D label positions (project 3D → screen space)
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

  private createAvatar(entity: EntityV3): AvatarInstance {
    const group = new THREE.Group();
    group.name = `entity_${entity.id}`;

    const color = new THREE.Color(entity.appearance.bodyColor || '#4fc3f7');
    const accentColor = new THREE.Color(entity.appearance.accentColor || '#ffffff');

    // Build body from voxels
    const bodyGeo = new THREE.BoxGeometry(0.8, 0.8, 0.8);
    const bodyMat = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: entity.appearance.emissive ? 0.3 : 0.05,
      roughness: 0.6,
    });

    // Composite body from voxel blocks
    for (const [vx, vy, vz] of DEFAULT_BODY_VOXELS) {
      const block = new THREE.Mesh(bodyGeo, bodyMat);
      block.position.set(vx * 0.4, vy * 0.4, vz * 0.4);
      group.add(block);
    }

    // Eye dots (accent color)
    const eyeGeo = new THREE.SphereGeometry(0.06, 4, 4);
    const eyeMat = new THREE.MeshBasicMaterial({ color: accentColor });
    const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
    leftEye.position.set(-0.12, 2.5, 0.3);
    group.add(leftEye);
    const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
    rightEye.position.set(0.12, 2.5, 0.3);
    group.add(rightEye);

    // The main body mesh for raycasting (invisible bounding box)
    const hitbox = new THREE.Mesh(
      new THREE.BoxGeometry(1.2, 3, 1),
      new THREE.MeshBasicMaterial({ visible: false }),
    );
    hitbox.position.y = 1.5;
    group.add(hitbox);

    // Set initial position
    group.position.set(entity.position.x, entity.position.y, entity.position.z);

    // Create name label
    let label: HTMLDivElement | null = null;
    if (this.labelContainer) {
      label = document.createElement('div');
      label.className = 'genesis-entity-label';
      label.textContent = entity.name;
      label.style.cssText = `
        position: absolute;
        color: ${entity.appearance.bodyColor || '#4fc3f7'};
        font-size: 11px;
        font-family: monospace;
        text-shadow: 0 0 4px rgba(0,0,0,0.8);
        pointer-events: none;
        transform: translate(-50%, 0);
        white-space: nowrap;
        z-index: 10;
      `;
      this.labelContainer.appendChild(label);
    }

    return {
      entityId: entity.id,
      group,
      bodyMesh: hitbox,
      label,
      targetPosition: new THREE.Vector3(entity.position.x, entity.position.y, entity.position.z),
      currentAction: entity.state.currentAction,
      speechBubble: null,
      speechTimeout: null,
      appearance: entity.appearance,
      isAlive: entity.isAlive,
    };
  }

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
  }
}
