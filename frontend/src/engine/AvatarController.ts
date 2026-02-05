/**
 * GENESIS v3 AvatarController
 *
 * First-person avatar control system.
 * Handles WASD movement, mouse look (pointer lock), interactions,
 * and sends position updates to the server via Socket.IO at ~20Hz.
 */
import * as THREE from 'three';
import type { Socket } from 'socket.io-client';

export interface AvatarControllerCallbacks {
  onBuildToggle?: (active: boolean) => void;
  onChatToggle?: (active: boolean) => void;
  onInteract?: (entityId: string | null) => void;
  onPointerLockChange?: (locked: boolean) => void;
}

const MOVE_SPEED = 5.0;           // units per second
const MOUSE_SENSITIVITY = 0.002;
const SEND_RATE_MS = 50;          // ~20Hz position updates
const PITCH_LIMIT = Math.PI / 2 - 0.01;

export class AvatarController {
  private socket: Socket | null = null;
  private camera: THREE.PerspectiveCamera | null = null;
  private entityId: string | null = null;
  private canvas: HTMLCanvasElement | null = null;

  // Movement state
  private keys: Set<string> = new Set();
  private yaw = 0;
  private pitch = 0;
  private position = new THREE.Vector3(0, 0, 0);

  // Pointer lock
  private isPointerLocked = false;

  // Throttle position sends
  private lastSendTime = 0;

  // Mode flags (exposed via callbacks)
  private buildModeActive = false;
  private chatModeActive = false;

  // Callbacks
  private callbacks: AvatarControllerCallbacks = {};

  // Bound handlers (for cleanup)
  private _onKeyDown = this.onKeyDown.bind(this);
  private _onKeyUp = this.onKeyUp.bind(this);
  private _onMouseMove = this.onMouseMove.bind(this);
  private _onPointerLockChange = this.onPointerLockChange.bind(this);
  private _onCanvasClick = this.onCanvasClick.bind(this);

  // Socket event listeners
  private _onAvatarJoined: ((data: any) => void) | null = null;
  private _onAvatarError: ((data: any) => void) | null = null;

  /**
   * Initialize the avatar controller.
   * @param socket - The Socket.IO socket instance
   * @param camera - The Three.js perspective camera
   * @param entityId - The player's entity ID in the world
   * @param canvas - The canvas element to attach pointer lock to
   * @param callbacks - Optional callbacks for mode changes
   */
  init(
    socket: Socket,
    camera: THREE.PerspectiveCamera,
    entityId: string,
    canvas: HTMLCanvasElement,
    callbacks?: AvatarControllerCallbacks,
  ): void {
    this.socket = socket;
    this.camera = camera;
    this.entityId = entityId;
    this.canvas = canvas;
    this.callbacks = callbacks || {};

    // Reset state
    this.keys.clear();
    this.yaw = 0;
    this.pitch = 0;
    this.position.set(0, 1.6, 0);
    this.buildModeActive = false;
    this.chatModeActive = false;

    // Attach DOM listeners
    document.addEventListener('keydown', this._onKeyDown);
    document.addEventListener('keyup', this._onKeyUp);
    document.addEventListener('mousemove', this._onMouseMove);
    document.addEventListener('pointerlockchange', this._onPointerLockChange);
    canvas.addEventListener('click', this._onCanvasClick);

    // Attach socket listeners
    this._onAvatarJoined = (data: any) => {
      console.log('[AvatarController] avatar_joined:', data);
      if (data.position) {
        this.position.set(
          data.position.x ?? 0,
          data.position.y ?? 1.6,
          data.position.z ?? 0,
        );
      }
    };
    this._onAvatarError = (data: any) => {
      console.error('[AvatarController] avatar_error:', data);
    };
    socket.on('avatar_joined', this._onAvatarJoined);
    socket.on('avatar_error', this._onAvatarError);
  }

  /**
   * Clean up all listeners and release pointer lock.
   */
  dispose(): void {
    // Release pointer lock
    if (document.pointerLockElement) {
      document.exitPointerLock();
    }

    // Remove DOM listeners
    document.removeEventListener('keydown', this._onKeyDown);
    document.removeEventListener('keyup', this._onKeyUp);
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('pointerlockchange', this._onPointerLockChange);
    if (this.canvas) {
      this.canvas.removeEventListener('click', this._onCanvasClick);
    }

    // Remove socket listeners
    if (this.socket) {
      if (this._onAvatarJoined) this.socket.off('avatar_joined', this._onAvatarJoined);
      if (this._onAvatarError) this.socket.off('avatar_error', this._onAvatarError);
    }

    this.socket = null;
    this.camera = null;
    this.entityId = null;
    this.canvas = null;
    this.keys.clear();
  }

  /**
   * Per-frame update. Call this from the animation loop.
   * @param delta - Time since last frame in seconds
   */
  update(delta: number): void {
    if (!this.camera || this.chatModeActive) return;

    // Compute movement direction from keys
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

    const velocity = new THREE.Vector3(0, 0, 0);

    if (this.keys.has('KeyW')) velocity.add(forward);
    if (this.keys.has('KeyS')) velocity.sub(forward);
    if (this.keys.has('KeyD')) velocity.add(right);
    if (this.keys.has('KeyA')) velocity.sub(right);
    if (this.keys.has('Space')) velocity.y += 1;
    if (this.keys.has('ShiftLeft') || this.keys.has('ShiftRight')) velocity.y -= 1;

    if (velocity.lengthSq() > 0) {
      velocity.normalize().multiplyScalar(MOVE_SPEED * delta);
      this.position.add(velocity);
    }

    // Update camera position (eye height offset)
    this.camera.position.set(
      this.position.x,
      this.position.y + 1.6,
      this.position.z,
    );

    // Update camera rotation
    const euler = new THREE.Euler(this.pitch, this.yaw, 0, 'YXZ');
    this.camera.quaternion.setFromEuler(euler);

    // Throttled position send
    const now = performance.now();
    if (now - this.lastSendTime >= SEND_RATE_MS && this.socket?.connected) {
      this.lastSendTime = now;
      this.socket.emit('avatar_move', {
        x: Math.round(this.position.x * 100) / 100,
        y: Math.round(this.position.y * 100) / 100,
        z: Math.round(this.position.z * 100) / 100,
      });
    }
  }

  // ---- Public Accessors ----

  getPosition(): THREE.Vector3 {
    return this.position.clone();
  }

  getYaw(): number {
    return this.yaw;
  }

  getPitch(): number {
    return this.pitch;
  }

  isLocked(): boolean {
    return this.isPointerLocked;
  }

  isBuildMode(): boolean {
    return this.buildModeActive;
  }

  isChatMode(): boolean {
    return this.chatModeActive;
  }

  /**
   * Programmatically set chat mode (e.g., when Enter is pressed from React).
   */
  setChatMode(active: boolean): void {
    this.chatModeActive = active;
  }

  /**
   * Send a chat message via socket.
   */
  sendChat(text: string): void {
    if (!this.socket?.connected || !text.trim()) return;
    this.socket.emit('avatar_speak', { text: text.trim() });
  }

  /**
   * Send a build action via socket.
   */
  sendBuild(x: number, y: number, z: number, color: string, material: string): void {
    if (!this.socket?.connected) return;
    this.socket.emit('avatar_build', { x, y, z, color, material });
  }

  /**
   * Send a destroy action via socket.
   */
  sendDestroy(x: number, y: number, z: number): void {
    if (!this.socket?.connected) return;
    this.socket.emit('avatar_destroy', { x, y, z });
  }

  /**
   * Request pointer lock on the canvas.
   */
  requestPointerLock(): void {
    if (this.canvas && !this.isPointerLocked) {
      this.canvas.requestPointerLock();
    }
  }

  // ---- Event Handlers ----

  private onKeyDown(e: KeyboardEvent): void {
    // Don't capture input when typing in text fields
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement
    ) return;

    // Chat mode toggle
    if (e.code === 'Enter' && !this.chatModeActive) {
      e.preventDefault();
      this.chatModeActive = true;
      this.callbacks.onChatToggle?.(true);
      // Release pointer lock so user can type
      if (document.pointerLockElement) {
        document.exitPointerLock();
      }
      return;
    }

    // Escape: release pointer lock / close chat / close build
    if (e.code === 'Escape') {
      if (this.chatModeActive) {
        this.chatModeActive = false;
        this.callbacks.onChatToggle?.(false);
        return;
      }
      if (this.buildModeActive) {
        this.buildModeActive = false;
        this.callbacks.onBuildToggle?.(false);
        return;
      }
      // Otherwise, signal escape (for pause menu)
      if (document.pointerLockElement) {
        document.exitPointerLock();
      }
      return;
    }

    // Building mode toggle
    if (e.code === 'KeyB' && !this.chatModeActive) {
      this.buildModeActive = !this.buildModeActive;
      this.callbacks.onBuildToggle?.(this.buildModeActive);
      return;
    }

    // Interact
    if (e.code === 'KeyE' && !this.chatModeActive) {
      this.callbacks.onInteract?.(null);
      return;
    }

    this.keys.add(e.code);
  }

  private onKeyUp(e: KeyboardEvent): void {
    this.keys.delete(e.code);
  }

  private onMouseMove(e: MouseEvent): void {
    if (!this.isPointerLocked) return;

    this.yaw -= e.movementX * MOUSE_SENSITIVITY;
    this.pitch -= e.movementY * MOUSE_SENSITIVITY;
    this.pitch = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, this.pitch));
  }

  private onPointerLockChange(): void {
    this.isPointerLocked = document.pointerLockElement === this.canvas;
    this.callbacks.onPointerLockChange?.(this.isPointerLocked);
  }

  private onCanvasClick(): void {
    if (!this.isPointerLocked && !this.chatModeActive) {
      this.canvas?.requestPointerLock();
    }
  }
}
