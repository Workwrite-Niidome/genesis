/**
 * GENESIS v3 Building Tool
 *
 * Allows both AI and human players to place/destroy voxels.
 * For humans: mouse-based placement with color/material selection.
 * AI uses the same system via ActionProposal.
 */
import * as THREE from 'three';
import type { VoxelRenderer } from './VoxelRenderer';
import type { ActionProposal } from '../types/v3';

export type BuildMode = 'place' | 'destroy' | 'paint' | 'none';

const GRID_HELPER_SIZE = 16;

export class BuildingTool {
  private renderer: VoxelRenderer;
  private camera: THREE.Camera;
  private raycaster: THREE.Raycaster;

  // Build state
  private mode: BuildMode = 'none';
  private selectedColor: string = '#4fc3f7';
  private selectedMaterial: 'solid' | 'glass' | 'emissive' | 'liquid' = 'solid';

  // Visual aids
  private ghostBlock: THREE.Mesh | null = null;
  private scene: THREE.Scene;
  private gridHelper: THREE.GridHelper | null = null;

  // Callback for sending proposals to server
  private onProposal: ((proposal: ActionProposal) => void) | null = null;
  private entityId: string | null = null;

  constructor(scene: THREE.Scene, camera: THREE.Camera, renderer: VoxelRenderer) {
    this.scene = scene;
    this.camera = camera;
    this.renderer = renderer;
    this.raycaster = new THREE.Raycaster();

    this.createGhostBlock();
  }

  /**
   * Set the entity ID for this builder (human avatar's entity ID).
   */
  setEntityId(entityId: string): void {
    this.entityId = entityId;
  }

  /**
   * Set callback for when a build action should be sent to server.
   */
  setProposalCallback(cb: (proposal: ActionProposal) => void): void {
    this.onProposal = cb;
  }

  setMode(mode: BuildMode): void {
    this.mode = mode;
    if (this.ghostBlock) {
      this.ghostBlock.visible = mode === 'place' || mode === 'paint';
    }
    if (mode !== 'none') {
      this.showGrid();
    } else {
      this.hideGrid();
    }
  }

  getMode(): BuildMode {
    return this.mode;
  }

  setColor(color: string): void {
    this.selectedColor = color;
    if (this.ghostBlock) {
      (this.ghostBlock.material as THREE.MeshStandardMaterial).color.set(color);
    }
  }

  setMaterial(material: 'solid' | 'glass' | 'emissive' | 'liquid'): void {
    this.selectedMaterial = material;
  }

  /**
   * Update ghost block position based on mouse position.
   * Call each frame when build mode is active.
   */
  updateGhost(mouseNDC: THREE.Vector2): void {
    if (this.mode === 'none' || !this.ghostBlock) return;

    this.raycaster.setFromCamera(mouseNDC, this.camera);
    const hit = this.renderer.raycast(this.raycaster);

    if (hit) {
      if (this.mode === 'place') {
        // Place adjacent to the hit face
        const placePos = hit.position.clone().add(hit.normal);
        this.ghostBlock.position.copy(placePos);
        this.ghostBlock.visible = true;
      } else if (this.mode === 'destroy') {
        this.ghostBlock.position.copy(hit.position);
        this.ghostBlock.visible = true;
        (this.ghostBlock.material as THREE.MeshStandardMaterial).color.set(0xff0000);
      } else if (this.mode === 'paint') {
        // Paint targets the existing block
        this.ghostBlock.position.copy(hit.position);
        this.ghostBlock.visible = true;
        (this.ghostBlock.material as THREE.MeshStandardMaterial).color.set(this.selectedColor);
      }
    } else {
      // Raycast against ground plane (y=0)
      const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
      const intersection = new THREE.Vector3();
      this.raycaster.ray.intersectPlane(groundPlane, intersection);

      if (intersection) {
        this.ghostBlock.position.set(
          Math.round(intersection.x),
          0,
          Math.round(intersection.z),
        );
        this.ghostBlock.visible = true;
      } else {
        this.ghostBlock.visible = false;
      }
    }
  }

  /**
   * Execute a build action (place or destroy).
   */
  execute(): void {
    if (this.mode === 'none' || !this.ghostBlock || !this.ghostBlock.visible) return;
    if (!this.entityId || !this.onProposal) return;

    const pos = this.ghostBlock.position;
    const x = Math.round(pos.x);
    const y = Math.round(pos.y);
    const z = Math.round(pos.z);

    if (this.mode === 'place') {
      this.onProposal({
        agentId: this.entityId,
        action: 'place_voxel',
        params: {
          x, y, z,
          color: this.selectedColor,
          material: this.selectedMaterial,
          collision: true,
        },
      });
    } else if (this.mode === 'destroy') {
      this.onProposal({
        agentId: this.entityId,
        action: 'destroy_voxel',
        params: { x, y, z },
      });
    } else if (this.mode === 'paint') {
      // Paint = destroy existing block then place with new color/material
      this.onProposal({
        agentId: this.entityId,
        action: 'paint_voxel',
        params: {
          x, y, z,
          color: this.selectedColor,
          material: this.selectedMaterial,
        },
      });
    }
  }

  private createGhostBlock(): void {
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mat = new THREE.MeshStandardMaterial({
      color: this.selectedColor,
      transparent: true,
      opacity: 0.5,
      wireframe: false,
    });
    this.ghostBlock = new THREE.Mesh(geo, mat);
    this.ghostBlock.visible = false;
    this.ghostBlock.name = 'ghost_block';

    // Add wireframe overlay
    const wire = new THREE.LineSegments(
      new THREE.EdgesGeometry(geo),
      new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 }),
    );
    this.ghostBlock.add(wire);

    this.scene.add(this.ghostBlock);
  }

  private showGrid(): void {
    if (!this.gridHelper) {
      this.gridHelper = new THREE.GridHelper(GRID_HELPER_SIZE * 2, GRID_HELPER_SIZE * 2, 0x444444, 0x222222);
      this.gridHelper.position.y = -0.5;
      this.scene.add(this.gridHelper);
    }
    this.gridHelper.visible = true;
  }

  private hideGrid(): void {
    if (this.gridHelper) {
      this.gridHelper.visible = false;
    }
  }

  dispose(): void {
    if (this.ghostBlock) {
      this.scene.remove(this.ghostBlock);
      this.ghostBlock.geometry.dispose();
      (this.ghostBlock.material as THREE.Material).dispose();
    }
    if (this.gridHelper) {
      this.scene.remove(this.gridHelper);
      this.gridHelper.dispose();
    }
  }
}
