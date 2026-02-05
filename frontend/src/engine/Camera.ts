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

const MOVE_SPEED = 1.5;
const SPRINT_MULTIPLIER = 3.0;
const MOUSE_SENSITIVITY = 0.003;
const TOUCH_SENSITIVITY = 0.004;
const ZOOM_SPEED = 3.0;
const PINCH_ZOOM_SPEED = 0.04;
const THIRD_PERSON_DISTANCE = 8;
const THIRD_PERSON_HEIGHT = 5;
const SMOOTH_FACTOR = 0.15;

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

  // Mouse drag state (for left-click drag rotation in observer mode)
  private isLeftDragging = false;

  // Touch state
  private touchPrevPos: { x: number; y: number } | null = null;
  private lastPinchDist: number | null = null;
  private activeTouchCount = 0;

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
    canvas.addEventListener('mousedown', this.onMouseDown);
    document.addEventListener('mouseup', this.onMouseUp);
    document.addEventListener('pointerlockchange', this.onPointerLockChange);
    document.addEventListener('mousemove', this.onMouseMove);
    document.addEventListener('keydown', this.onKeyDown);
    document.addEventListener('keyup', this.onKeyUp);
    canvas.addEventListener('wheel', this.onWheel, { passive: false });

    // Touch controls for mobile
    canvas.addEventListener('touchstart', this.onTouchStart, { passive: false });
    canvas.addEventListener('touchmove', this.onTouchMove, { passive: false });
    canvas.addEventListener('touchend', this.onTouchEnd, { passive: false });
  }

  /**
   * Detach input listeners.
   */
  detach(): void {
    if (this.canvas) {
      this.canvas.removeEventListener('click', this.onCanvasClick);
      this.canvas.removeEventListener('mousedown', this.onMouseDown);
      this.canvas.removeEventListener('wheel', this.onWheel);
      this.canvas.removeEventListener('touchstart', this.onTouchStart);
      this.canvas.removeEventListener('touchmove', this.onTouchMove);
      this.canvas.removeEventListener('touchend', this.onTouchEnd);
    }
    document.removeEventListener('mouseup', this.onMouseUp);
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

    if (this.keys.has('KeyW') || this.keys.has('ArrowUp')) this.velocity.add(forward);
    if (this.keys.has('KeyS') || this.keys.has('ArrowDown')) this.velocity.sub(forward);
    if (this.keys.has('KeyD') || this.keys.has('ArrowRight')) this.velocity.add(right);
    if (this.keys.has('KeyA') || this.keys.has('ArrowLeft')) this.velocity.sub(right);
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

  private onMouseDown = (e: MouseEvent): void => {
    if (e.button === 0) this.isLeftDragging = true; // left button
  };

  private onMouseUp = (e: MouseEvent): void => {
    if (e.button === 0) this.isLeftDragging = false;
  };

  private onMouseMove = (e: MouseEvent): void => {
    // Allow rotation with: left-drag, right-drag, or pointer lock
    const canRotate =
      this.isPointerLocked ||
      (this.mode === 'observer' && (this.isLeftDragging || !!(e.buttons & 2)));

    if (canRotate) {
      this.yaw -= e.movementX * MOUSE_SENSITIVITY;
      this.pitch -= e.movementY * MOUSE_SENSITIVITY;
      this.pitch = Math.max(-Math.PI / 2 + 0.01, Math.min(Math.PI / 2 - 0.01, this.pitch));
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

  // ---- Touch Handlers (mobile) ----

  private onTouchStart = (e: TouchEvent): void => {
    this.activeTouchCount = e.touches.length;

    if (e.touches.length === 1) {
      this.touchPrevPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      this.lastPinchDist = null;
    } else if (e.touches.length === 2) {
      e.preventDefault();
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      this.lastPinchDist = Math.sqrt(dx * dx + dy * dy);
      this.touchPrevPos = null;
    }
  };

  private onTouchMove = (e: TouchEvent): void => {
    e.preventDefault();

    if (e.touches.length === 1 && this.touchPrevPos && this.activeTouchCount === 1) {
      // Single-finger drag → rotate camera
      const dx = e.touches[0].clientX - this.touchPrevPos.x;
      const dy = e.touches[0].clientY - this.touchPrevPos.y;

      this.yaw -= dx * TOUCH_SENSITIVITY;
      this.pitch -= dy * TOUCH_SENSITIVITY;
      this.pitch = Math.max(-Math.PI / 2 + 0.01, Math.min(Math.PI / 2 - 0.01, this.pitch));

      this.touchPrevPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    } else if (e.touches.length === 2 && this.lastPinchDist !== null) {
      // Two-finger pinch → zoom
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const delta = dist - this.lastPinchDist;

      if (this.mode === 'observer') {
        const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
        this.targetPosition.addScaledVector(forward, delta * PINCH_ZOOM_SPEED);
      }

      this.lastPinchDist = dist;
    }
  };

  private onTouchEnd = (e: TouchEvent): void => {
    this.activeTouchCount = e.touches.length;
    if (e.touches.length === 0) {
      this.touchPrevPos = null;
      this.lastPinchDist = null;
    } else if (e.touches.length === 1) {
      this.touchPrevPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      this.lastPinchDist = null;
    }
  };

  /**
   * Pan the camera to look at a world position (x, z) while keeping current height.
   */
  panTo(x: number, z: number): void {
    if (this.mode !== 'observer') return;
    this.targetPosition.x = x;
    this.targetPosition.z = z;
  }

  /**
   * Get the current camera world position.
   */
  getPosition(): THREE.Vector3 {
    return this.camera.position.clone();
  }

  dispose(): void {
    this.detach();
  }
}
