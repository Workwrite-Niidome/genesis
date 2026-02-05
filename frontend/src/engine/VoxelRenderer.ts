/**
 * GENESIS v3 VoxelRenderer
 *
 * High-performance voxel rendering using Three.js InstancedMesh.
 * Uses MeshLambertMaterial to avoid texture unit limits.
 */
import * as THREE from 'three';
import type { Voxel, VoxelUpdate } from '../types/v3';

const VOXEL_SIZE = 1.0;
const MAX_INSTANCES_PER_BATCH = 65536;

interface VoxelBatch {
  key: string;
  mesh: THREE.InstancedMesh;
  material: THREE.MeshLambertMaterial;
  positions: Map<string, number>;  // "x,y,z" → instance index
  count: number;
  dirty: boolean;
}

export class VoxelRenderer {
  private scene: THREE.Scene;
  private batches: Map<string, VoxelBatch> = new Map();
  private geometry: THREE.BoxGeometry;
  private voxelData: Map<string, Voxel> = new Map();  // "x,y,z" → Voxel
  private wireframeGroup: THREE.Group;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.geometry = new THREE.BoxGeometry(VOXEL_SIZE, VOXEL_SIZE, VOXEL_SIZE);
    this.wireframeGroup = new THREE.Group();
    this.wireframeGroup.name = 'voxel_wireframes';
    this.scene.add(this.wireframeGroup);
  }

  private getBatchKey(color: string, material: string): string {
    return `${color}:${material}`;
  }

  private getOrCreateBatch(color: string, materialType: string): VoxelBatch {
    const key = this.getBatchKey(color, materialType);
    let batch = this.batches.get(key);
    if (batch) return batch;

    const colorObj = new THREE.Color(color);

    // MeshLambertMaterial - シンプルで軽量、テクスチャユニットを消費しない
    const material = new THREE.MeshLambertMaterial({
      color: colorObj,
      transparent: materialType === 'glass' || materialType === 'liquid',
      opacity: materialType === 'glass' ? 0.5 : materialType === 'liquid' ? 0.7 : 1.0,
      emissive: materialType === 'emissive' ? colorObj : new THREE.Color(0x000000),
      emissiveIntensity: materialType === 'emissive' ? 0.8 : 0.1,
    });

    const mesh = new THREE.InstancedMesh(this.geometry, material, MAX_INSTANCES_PER_BATCH);
    mesh.count = 0;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = true;
    mesh.name = `voxels_${key}`;

    this.scene.add(mesh);

    batch = {
      key,
      mesh,
      material,
      positions: new Map(),
      count: 0,
      dirty: false,
    };
    this.batches.set(key, batch);
    return batch;
  }

  /**
   * Place a single voxel in the world.
   */
  placeVoxel(voxel: Voxel): void {
    const posKey = `${voxel.x},${voxel.y},${voxel.z}`;

    // Remove existing voxel at this position if any
    if (this.voxelData.has(posKey)) {
      this.destroyVoxelAt(voxel.x, voxel.y, voxel.z);
    }

    this.voxelData.set(posKey, voxel);

    const batch = this.getOrCreateBatch(voxel.color, voxel.material);
    const index = batch.count;

    if (index >= MAX_INSTANCES_PER_BATCH) {
      console.warn(`VoxelRenderer: batch ${batch.key} at capacity`);
      return;
    }

    const matrix = new THREE.Matrix4();
    matrix.setPosition(voxel.x, voxel.y, voxel.z);
    batch.mesh.setMatrixAt(index, matrix);
    batch.positions.set(posKey, index);
    batch.count++;
    batch.mesh.count = batch.count;
    batch.mesh.instanceMatrix.needsUpdate = true;
    batch.dirty = true;
  }

  /**
   * Destroy a voxel at the given position.
   */
  destroyVoxelAt(x: number, y: number, z: number): boolean {
    const posKey = `${x},${y},${z}`;
    const voxel = this.voxelData.get(posKey);
    if (!voxel) return false;

    const batchKey = this.getBatchKey(voxel.color, voxel.material);
    const batch = this.batches.get(batchKey);
    if (!batch) return false;

    const index = batch.positions.get(posKey);
    if (index === undefined) return false;

    // Swap with last instance to maintain contiguous array
    const lastIndex = batch.count - 1;
    if (index !== lastIndex) {
      const lastMatrix = new THREE.Matrix4();
      batch.mesh.getMatrixAt(lastIndex, lastMatrix);
      batch.mesh.setMatrixAt(index, lastMatrix);

      // Find and update the position key for the swapped instance
      for (const [key, idx] of batch.positions) {
        if (idx === lastIndex) {
          batch.positions.set(key, index);
          break;
        }
      }
    }

    batch.positions.delete(posKey);
    batch.count--;
    batch.mesh.count = batch.count;
    batch.mesh.instanceMatrix.needsUpdate = true;
    batch.dirty = true;

    this.voxelData.delete(posKey);
    return true;
  }

  /**
   * Apply a batch of voxel updates from the server.
   */
  applyUpdates(updates: VoxelUpdate[]): void {
    for (const update of updates) {
      if (update.type === 'place') {
        this.placeVoxel({
          x: update.x,
          y: update.y,
          z: update.z,
          color: update.color || '#888888',
          material: (update.material as Voxel['material']) || 'solid',
          hasCollision: true,
        });
      } else if (update.type === 'destroy') {
        this.destroyVoxelAt(update.x, update.y, update.z);
      }
    }
  }

  /**
   * Load initial world state — bulk voxel placement.
   */
  loadWorld(voxels: Voxel[]): void {
    this.clear();
    for (const voxel of voxels) {
      this.placeVoxel(voxel);
    }
    console.log(`[VoxelRenderer] Loaded ${voxels.length} voxels in ${this.batches.size} batches`);
  }

  /**
   * Clear all voxels.
   */
  clear(): void {
    for (const batch of this.batches.values()) {
      this.scene.remove(batch.mesh);
      batch.mesh.dispose();
      batch.material.dispose();
    }
    this.batches.clear();
    this.voxelData.clear();
  }

  /**
   * Get voxel at position (for client-side queries).
   */
  getVoxelAt(x: number, y: number, z: number): Voxel | undefined {
    return this.voxelData.get(`${x},${y},${z}`);
  }

  /**
   * Check if a position has a solid voxel.
   */
  isBlocked(x: number, y: number, z: number): boolean {
    const voxel = this.voxelData.get(`${x},${y},${z}`);
    return voxel !== undefined && voxel.hasCollision;
  }

  /**
   * Get total voxel count.
   */
  getVoxelCount(): number {
    return this.voxelData.size;
  }

  /**
   * Raycast to find which voxel the cursor is pointing at.
   * Returns the voxel position and the face normal for adjacent placement.
   */
  raycast(
    raycaster: THREE.Raycaster,
  ): { position: THREE.Vector3; normal: THREE.Vector3; voxel: Voxel } | null {
    const meshes = Array.from(this.batches.values()).map(b => b.mesh);
    const intersects = raycaster.intersectObjects(meshes, false);

    if (intersects.length === 0) return null;

    const hit = intersects[0];
    if (!hit.face || hit.instanceId === undefined) return null;

    const mesh = hit.object as THREE.InstancedMesh;
    const matrix = new THREE.Matrix4();
    mesh.getMatrixAt(hit.instanceId, matrix);
    const position = new THREE.Vector3();
    position.setFromMatrixPosition(matrix);

    // Round to grid
    position.x = Math.round(position.x);
    position.y = Math.round(position.y);
    position.z = Math.round(position.z);

    const voxel = this.voxelData.get(`${position.x},${position.y},${position.z}`);
    if (!voxel) return null;

    return {
      position,
      normal: hit.face.normal.clone(),
      voxel,
    };
  }

  /**
   * Dispose of all GPU resources.
   */
  dispose(): void {
    this.clear();
    this.geometry.dispose();
    this.scene.remove(this.wireframeGroup);
  }
}
