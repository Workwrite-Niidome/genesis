/**
 * GENESIS v3 AssetManager
 *
 * Manages the lifecycle of loaded assets in the world.
 * Coordinates with AssetLoader to discover, load, and integrate
 * HDRI skyboxes, GLTF models, and PBR textures into the scene.
 *
 * Behaviour:
 * 1. On applySkybox(), checks /assets/skybox/ for available skybox images.
 *    If found, loads the first one and applies it as skybox + environment map.
 *    If not found, the existing procedural sky dome remains (graceful fallback).
 *
 * 2. On loadAndPlaceModels(), checks /assets/models/ for GLB files.
 *    If model files are found (e.g., torii.glb), loads and places them,
 *    hiding the corresponding procedural structure.
 *    If no models are found, everything stays procedural (current behavior).
 */
import * as THREE from 'three';
import { AssetLoader } from './AssetLoader';
import type { ProceduralStructures } from './ProceduralStructures';

/** Maps a model filename (without extension) to its placement configuration. */
interface ModelPlacement {
  /** Position in world space */
  position: THREE.Vector3;
  /** Rotation in radians (Euler Y) */
  rotationY: number;
  /** Uniform scale factor */
  scale: number;
  /** Name of the procedural structure group to hide when this model loads */
  proceduralName?: string;
}

/** Known model placements keyed by filename stem (e.g., "torii") */
const MODEL_PLACEMENTS: Record<string, ModelPlacement> = {
  torii: {
    position: new THREE.Vector3(0, 0, 0),
    rotationY: 0,
    scale: 1,
    proceduralName: 'ToriiGate',
  },
  shrine: {
    position: new THREE.Vector3(25, 0, 25),
    rotationY: Math.PI,
    scale: 1,
    proceduralName: 'Shrine',
  },
  lantern: {
    position: new THREE.Vector3(10, 0, 2.5),
    rotationY: 0,
    scale: 1,
    proceduralName: 'StoneLantern',
  },
  tree: {
    position: new THREE.Vector3(22, 0, 20),
    rotationY: 0,
    scale: 1,
    proceduralName: 'CherryTree',
  },
};

export class AssetManager {
  private scene: THREE.Scene;
  private renderer: THREE.WebGLRenderer;
  private assetLoader: AssetLoader;

  /** Loaded model groups added to the scene (for disposal) */
  private loadedModels: THREE.Group[] = [];

  /** Skybox texture reference (for disposal) */
  private skyboxTexture: THREE.Texture | null = null;

  /** Whether the skybox was successfully applied */
  private skyboxApplied = false;

  constructor(
    scene: THREE.Scene,
    renderer: THREE.WebGLRenderer,
    assetLoader: AssetLoader,
  ) {
    this.scene = scene;
    this.renderer = renderer;
    this.assetLoader = assetLoader;
  }

  /**
   * Try to load and apply a skybox from /assets/skybox/.
   *
   * Checks for available skybox images, loads the first one found,
   * and applies it as both the scene background and environment map.
   *
   * Returns true if a skybox was successfully applied, false otherwise.
   * On failure the existing procedural sky dome is preserved.
   */
  async applySkybox(): Promise<boolean> {
    try {
      const assets = await this.assetLoader.checkAvailableAssets();

      if (assets.skyboxes.length === 0) {
        console.log('[AssetManager] No skybox assets found, keeping procedural sky dome');
        return false;
      }

      const skyboxFile = assets.skyboxes[0];
      const url = `/assets/skybox/${skyboxFile}`;

      console.log(`[AssetManager] Loading skybox: ${url}`);

      this.skyboxTexture = await this.assetLoader.loadSkybox(
        url,
        this.scene,
        this.renderer,
      );

      this.skyboxApplied = true;
      console.log('[AssetManager] Skybox applied successfully');
      return true;
    } catch (error) {
      console.warn('[AssetManager] Failed to apply skybox, keeping procedural sky dome:', error);
      return false;
    }
  }

  /**
   * Try to load and place 3D models from /assets/models/.
   *
   * For each found model file:
   * 1. Determines placement from MODEL_PLACEMENTS (or uses defaults)
   * 2. Loads the GLTF/GLB model
   * 3. Places it in the scene at the configured position
   * 4. Hides the corresponding procedural structure if one exists
   *
   * Returns true if any models were loaded, false otherwise.
   */
  async loadAndPlaceModels(
    proceduralStructures: ProceduralStructures | null = null,
  ): Promise<boolean> {
    try {
      const assets = await this.assetLoader.checkAvailableAssets();

      if (assets.models.length === 0) {
        console.log('[AssetManager] No model assets found, keeping procedural structures');
        return false;
      }

      let anyLoaded = false;

      for (const modelFile of assets.models) {
        try {
          const url = `/assets/models/${modelFile}`;
          const model = await this.assetLoader.loadModel(url);

          // Determine placement -- strip extension to get the stem
          const stem = modelFile.replace(/\.(glb|gltf)$/i, '').toLowerCase();
          const placement = MODEL_PLACEMENTS[stem];

          if (placement) {
            model.position.copy(placement.position);
            model.rotation.y = placement.rotationY;
            model.scale.setScalar(placement.scale);

            // Hide the corresponding procedural structure
            if (placement.proceduralName && proceduralStructures) {
              this.hideProceduralStructure(placement.proceduralName);
            }
          } else {
            // Default placement at origin if not in the known map
            console.log(
              `[AssetManager] No placement config for "${stem}", placing at origin`,
            );
            model.position.set(0, 0, 0);
          }

          this.scene.add(model);
          this.loadedModels.push(model);
          anyLoaded = true;

          console.log(`[AssetManager] Model placed: ${modelFile} at`, model.position);
        } catch (error) {
          console.warn(`[AssetManager] Failed to load model: ${modelFile}`, error);
          // Continue trying other models
        }
      }

      return anyLoaded;
    } catch (error) {
      console.warn('[AssetManager] Failed to load models:', error);
      return false;
    }
  }

  /**
   * Hide a procedural structure group by name.
   * Traverses the scene to find groups with a matching name and sets visible = false.
   */
  private hideProceduralStructure(name: string): void {
    this.scene.traverse((child) => {
      if (child instanceof THREE.Group && child.name === name) {
        child.visible = false;
        console.log(`[AssetManager] Hidden procedural structure: ${name}`);
      }
    });
  }

  /**
   * Whether the skybox has been successfully applied.
   */
  get hasSkybox(): boolean {
    return this.skyboxApplied;
  }

  /**
   * Get the number of loaded models.
   */
  get modelCount(): number {
    return this.loadedModels.length;
  }

  /**
   * Dispose all loaded assets and remove them from the scene.
   */
  dispose(): void {
    // Remove loaded models from scene and dispose their resources
    for (const model of this.loadedModels) {
      this.scene.remove(model);
      model.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) {
            for (const mat of mesh.material) {
              mat.dispose();
            }
          } else {
            mesh.material.dispose();
          }
        }
      });
    }
    this.loadedModels = [];

    // Clear skybox from scene if we applied it
    if (this.skyboxApplied) {
      this.scene.background = null;
      this.scene.environment = null;
    }

    this.skyboxTexture = null;
    this.skyboxApplied = false;

    console.log('[AssetManager] Disposed');
  }
}
