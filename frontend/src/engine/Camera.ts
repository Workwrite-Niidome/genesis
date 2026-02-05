/**
 * GENESIS v3 Camera Controller
 *
 * Supports two modes:
 * - Observer mode: Free-flying camera with orbit controls
 * - Participant mode: First/third person following an entity
 */
import * as THREE from 'three';

export type CameraMode = 'observer' | 'first_person' | 'third_person';

export interface CameraState {
  mode: CameraMode;
  position: THREE.Vector3;
  target: THREE.Vector3;
  followEntityId: string | null;
}

const MOVE_SPEED = 0.5;
const SPRINT_MULTIPLIER = 3.0;
const MOUSE_SENSITIVITY = 0.002;
const ZOOM_SPEED = 2.0;
const THIRD_PERSON_DISTANCE = 8;
const THIRD_PERSON_HEIGHT = 5;
const SMOOTH_FACTOR = 0.1;

export class CameraController {
  private camera: THREE.PerspectiveCamera;
  private mode: CameraMode = 'observer';
  private followEntityId: string | null = null;

  // Observer mode state
  private yaw = 0;
  private pitch = -0.3;
  private targetPosition = new THREE.Vector3(0, 30, 50);
  private velocity = new THREE.Vector3();

  // Input state
  private keys: Set<string> = new Set();
  private isPointerLocked = false;
  private canvas: HTMLCanvasElement | null = null;

  constructor(camera: THREE.PerspectiveCamera) {
    this.camera = camera;
    this.camera.position.copy(this.targetPosition);
  }

  /**
   * Attach to a canvas element for input handling.
   */
  attach(canvas: HTMLCanvasElement): void {
    this.canvas = canvas;

    canvas.addEventListener('click', this.onCanvasClick);
    document.addEventListener('pointerlockchange', this.onPointerLockChange);
    document.addEventListener('mousemove', this.onMouseMove);
    document.addEventListener('keydown', this.onKeyDown);
    document.addEventListener('keyup', this.onKeyUp);
    canvas.addEventListener('wheel', this.onWheel, { passive: false });
  }

  /**
   * Detach input listeners.
   */
  detach(): void {
    if (this.canvas) {
      this.canvas.removeEventListener('click', this.onCanvasClick);
      this.canvas.removeEventListener('wheel', this.onWheel);
    }
    document.removeEventListener('pointerlockchange', this.onPointerLockChange);
    document.removeEventListener('mousemove', this.onMouseMove);
    document.removeEventListener('keydown', this.onKeyDown);
    document.removeEventListener('keyup', this.onKeyUp);
    this.canvas = null;
  }

  setMode(mode: CameraMode): void {
    this.mode = mode;
    if (mode === 'observer') {
      this.followEntityId = null;
      if (document.pointerLockElement) {
        document.exitPointerLock();
      }
    }
  }

  followEntity(entityId: string, mode: CameraMode = 'third_person'): void {
    this.followEntityId = entityId;
    this.mode = mode;
  }

  getMode(): CameraMode {
    return this.mode;
  }

  getFollowEntityId(): string | null {
    return this.followEntityId;
  }

  /**
   * Update camera position each frame.
   * Call with entity positions map for follow modes.
   */
  update(
    _delta: number,
    entityPositions?: Map<string, THREE.Vector3>,
  ): void {
    if (this.mode === 'observer') {
      this.updateObserver();
    } else if (this.followEntityId && entityPositions) {
      const targetPos = entityPositions.get(this.followEntityId);
      if (targetPos) {
        if (this.mode === 'third_person') {
          this.updateThirdPerson(targetPos);
        } else {
          this.updateFirstPerson(targetPos);
        }
      }
    }
  }

  private updateObserver(): void {
    const speed = this.keys.has('ShiftLeft') || this.keys.has('ShiftRight')
      ? MOVE_SPEED * SPRINT_MULTIPLIER
      : MOVE_SPEED;

    // Build direction from yaw
    const forward = new THREE.Vector3(
      -Math.sin(this.yaw),
      0,
      -Math.cos(this.yaw),
    );
    const right = new THREE.Vector3(
      Math.cos(this.yaw),
      0,
      -Math.sin(this.yaw),
    );

    this.velocity.set(0, 0, 0);

    if (this.keys.has('KeyW')) this.velocity.add(forward);
    if (this.keys.has('KeyS')) this.velocity.sub(forward);
    if (this.keys.has('KeyD')) this.velocity.add(right);
    if (this.keys.has('KeyA')) this.velocity.sub(right);
    if (this.keys.has('Space')) this.velocity.y += 1;
    if (this.keys.has('KeyC') || this.keys.has('ControlLeft')) this.velocity.y -= 1;

    if (this.velocity.lengthSq() > 0) {
      this.velocity.normalize().multiplyScalar(speed);
      this.targetPosition.add(this.velocity);
    }

    // Smooth camera movement
    this.camera.position.lerp(this.targetPosition, SMOOTH_FACTOR);

    // Apply rotation
    const euler = new THREE.Euler(this.pitch, this.yaw, 0, 'YXZ');
    this.camera.quaternion.setFromEuler(euler);
  }

  private updateThirdPerson(entityPos: THREE.Vector3): void {
    const offset = new THREE.Vector3(
      Math.sin(this.yaw) * THIRD_PERSON_DISTANCE,
      THIRD_PERSON_HEIGHT,
      Math.cos(this.yaw) * THIRD_PERSON_DISTANCE,
    );

    const desired = entityPos.clone().add(offset);
    this.camera.position.lerp(desired, SMOOTH_FACTOR);
    this.camera.lookAt(entityPos);
  }

  private updateFirstPerson(entityPos: THREE.Vector3): void {
    const eyeHeight = new THREE.Vector3(0, 1.6, 0);
    this.camera.position.lerp(entityPos.clone().add(eyeHeight), SMOOTH_FACTOR);

    const euler = new THREE.Euler(this.pitch, this.yaw, 0, 'YXZ');
    this.camera.quaternion.setFromEuler(euler);
  }

  // ---- Event Handlers ----

  private onCanvasClick = (): void => {
    if (this.mode !== 'observer' && this.canvas && !this.isPointerLocked) {
      this.canvas.requestPointerLock();
    }
  };

  private onPointerLockChange = (): void => {
    this.isPointerLocked = document.pointerLockElement === this.canvas;
  };

  private onMouseMove = (e: MouseEvent): void => {
    // In observer mode, always allow rotation with right-mouse or pointer lock
    if (this.mode === 'observer' || this.isPointerLocked) {
      if (this.isPointerLocked || (e.buttons & 2)) {
        this.yaw -= e.movementX * MOUSE_SENSITIVITY;
        this.pitch -= e.movementY * MOUSE_SENSITIVITY;
        this.pitch = Math.max(-Math.PI / 2 + 0.01, Math.min(Math.PI / 2 - 0.01, this.pitch));
      }
    }
  };

  private onKeyDown = (e: KeyboardEvent): void => {
    // Don't capture input when typing in text fields
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement
    ) return;
    this.keys.add(e.code);
  };

  private onKeyUp = (e: KeyboardEvent): void => {
    this.keys.delete(e.code);
  };

  private onWheel = (e: WheelEvent): void => {
    e.preventDefault();
    if (this.mode === 'observer') {
      const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
      this.targetPosition.addScaledVector(forward, -e.deltaY * ZOOM_SPEED * 0.01);
    }
  };

  dispose(): void {
    this.detach();
  }
}
