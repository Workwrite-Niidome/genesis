/**
 * GENESIS v3 AssetLoader
 *
 * Centralized asset loading system for HDRI skyboxes, GLTF 3D models,
 * and PBR textures. Integrates loaded assets into the Three.js scene
 * with environment mapping for realistic reflections.
 *
 * Key feature: Setting scene.environment with an equirectangular map
 * makes ALL MeshStandardMaterial objects reflect the surroundings,
 * dramatically improving visual quality with a single assignment.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';

/** Result of checking available assets at /assets/ */
export interface AvailableAssets {
  skyboxes: string[];
  models: string[];
  textures: string[];
}

/** A PBR texture set with optional normal/roughness maps */
export interface PBRTextureSet {
  diffuse: THREE.Texture;
  normal?: THREE.Texture;
  roughness?: THREE.Texture;
}

export class AssetLoader {
  private textureLoader: THREE.TextureLoader;
  private gltfLoader: GLTFLoader;
  private dracoLoader: DRACOLoader;
  private loadedTextures: THREE.Texture[] = [];
  private disposed = false;

  constructor() {
    this.textureLoader = new THREE.TextureLoader();

    // DRACO decoder for compressed GLTF models (using CDN-hosted decoder)
    this.dracoLoader = new DRACOLoader();
    this.dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/');
    this.dracoLoader.setDecoderConfig({ type: 'js' });

    this.gltfLoader = new GLTFLoader();
    this.gltfLoader.setDRACOLoader(this.dracoLoader);
  }

  /**
   * Load an equirectangular JPG/PNG image as skybox + environment map.
   *
   * - Sets texture.mapping = EquirectangularReflectionMapping
   * - Sets scene.background = texture (replaces the shader sky dome visually)
   * - Sets scene.environment = texture (enables PBR reflections on ALL materials)
   *
   * If loading fails, the existing sky dome is preserved (graceful fallback).
   */
  async loadSkybox(
    url: string,
    scene: THREE.Scene,
    renderer: THREE.WebGLRenderer,
  ): Promise<THREE.Texture> {
    // Suppress unused parameter lint -- renderer is kept in the signature
    // for future HDR/EXR loading with PMREMGenerator
    void renderer;

    return new Promise<THREE.Texture>((resolve, reject) => {
      this.textureLoader.load(
        url,
        (texture) => {
          if (this.disposed) {
            texture.dispose();
            reject(new Error('AssetLoader disposed during load'));
            return;
          }

          // Configure as equirectangular environment map
          texture.mapping = THREE.EquirectangularReflectionMapping;
          texture.colorSpace = THREE.SRGBColorSpace;

          // Apply as scene background and environment (PBR reflections)
          scene.background = texture;
          scene.environment = texture;

          this.loadedTextures.push(texture);

          console.log(`[AssetLoader] Skybox loaded and applied: ${url}`);
          resolve(texture);
        },
        undefined, // onProgress
        (error) => {
          console.warn(`[AssetLoader] Failed to load skybox: ${url}`, error);
          reject(error);
        },
      );
    });
  }

  /**
   * Load a GLTF/GLB model.
   *
   * - Uses GLTFLoader with optional DRACO decompression
   * - Enables castShadow and receiveShadow on all meshes
   * - Returns the loaded scene as THREE.Group
   */
  async loadModel(url: string): Promise<THREE.Group> {
    return new Promise<THREE.Group>((resolve, reject) => {
      this.gltfLoader.load(
        url,
        (gltf) => {
          if (this.disposed) {
            reject(new Error('AssetLoader disposed during load'));
            return;
          }

          const model = gltf.scene;

          // Enable shadows on all meshes in the loaded model
          model.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
              const mesh = child as THREE.Mesh;
              mesh.castShadow = true;
              mesh.receiveShadow = true;
            }
          });

          console.log(`[AssetLoader] Model loaded: ${url}`);
          resolve(model);
        },
        undefined, // onProgress
        (error) => {
          console.warn(`[AssetLoader] Failed to load model: ${url}`, error);
          reject(error);
        },
      );
    });
  }

  /**
   * Load a single texture (for ground, walls, etc.).
   *
   * - Uses THREE.TextureLoader
   * - Configures wrapping to RepeatWrapping and sets a default repeat
   * - Returns the configured texture
   */
  async loadTexture(url: string): Promise<THREE.Texture> {
    return new Promise<THREE.Texture>((resolve, reject) => {
      this.textureLoader.load(
        url,
        (texture) => {
          if (this.disposed) {
            texture.dispose();
            reject(new Error('AssetLoader disposed during load'));
            return;
          }

          texture.wrapS = THREE.RepeatWrapping;
          texture.wrapT = THREE.RepeatWrapping;
          texture.repeat.set(1, 1);
          texture.colorSpace = THREE.SRGBColorSpace;

          this.loadedTextures.push(texture);

          console.log(`[AssetLoader] Texture loaded: ${url}`);
          resolve(texture);
        },
        undefined, // onProgress
        (error) => {
          console.warn(`[AssetLoader] Failed to load texture: ${url}`, error);
          reject(error);
        },
      );
    });
  }

  /**
   * Load a PBR texture set (diffuse + optional normal + optional roughness).
   *
   * Expects files following a naming convention:
   *   baseName_diffuse.jpg, baseName_normal.jpg, baseName_roughness.jpg
   *
   * Only the diffuse map is required; normal and roughness are optional.
   */
  async loadTextureSet(basePath: string, baseName: string): Promise<PBRTextureSet> {
    const extensions = ['jpg', 'png'];

    const tryLoad = async (suffix: string): Promise<THREE.Texture | undefined> => {
      for (const ext of extensions) {
        const url = `${basePath}/${baseName}_${suffix}.${ext}`;
        try {
          const tex = await this.loadTexture(url);
          if (suffix === 'normal' || suffix === 'roughness') {
            // Normal and roughness maps should use linear color space
            tex.colorSpace = THREE.LinearSRGBColorSpace;
          }
          return tex;
        } catch {
          // Try next extension
        }
      }
      return undefined;
    };

    const diffuse = await tryLoad('diffuse');
    if (!diffuse) {
      throw new Error(`[AssetLoader] Could not load diffuse texture for ${baseName}`);
    }

    const normal = await tryLoad('normal');
    const roughness = await tryLoad('roughness');

    return { diffuse, normal, roughness };
  }

  /**
   * Check what assets are available at /assets/ by attempting to fetch
   * a manifest file or probing known subdirectories.
   *
   * Tries to fetch /assets/manifest.json first. If unavailable, returns
   * empty lists (the caller should handle the empty case gracefully).
   */
  async checkAvailableAssets(): Promise<AvailableAssets> {
    const empty: AvailableAssets = { skyboxes: [], models: [], textures: [] };

    try {
      // Try manifest file first (generated by build/deploy tools)
      const response = await fetch('/assets/manifest.json');
      if (response.ok) {
        const manifest = await response.json() as AvailableAssets;
        console.log('[AssetLoader] Asset manifest loaded:', manifest);
        return manifest;
      }
    } catch {
      // manifest.json not available, that's fine
    }

    // Fallback: probe for common asset files
    const probeResults: AvailableAssets = { skyboxes: [], models: [], textures: [] };

    // Probe common skybox filenames
    const skyboxProbes = [
      'skybox.jpg', 'skybox.png', 'sky.jpg', 'sky.png',
      'environment.jpg', 'environment.png', 'hdri.jpg', 'hdri.png',
    ];
    for (const name of skyboxProbes) {
      try {
        const res = await fetch(`/assets/skybox/${name}`, { method: 'HEAD' });
        if (res.ok) {
          probeResults.skyboxes.push(name);
        }
      } catch {
        // Not found, continue
      }
    }

    // Probe common model filenames
    const modelProbes = [
      'torii.glb', 'torii.gltf',
      'shrine.glb', 'shrine.gltf',
      'lantern.glb', 'lantern.gltf',
      'tree.glb', 'tree.gltf',
    ];
    for (const name of modelProbes) {
      try {
        const res = await fetch(`/assets/models/${name}`, { method: 'HEAD' });
        if (res.ok) {
          probeResults.models.push(name);
        }
      } catch {
        // Not found, continue
      }
    }

    // Probe common texture filenames
    const textureProbes = [
      'ground_diffuse.jpg', 'ground_diffuse.png',
      'stone_diffuse.jpg', 'stone_diffuse.png',
    ];
    for (const name of textureProbes) {
      try {
        const res = await fetch(`/assets/textures/${name}`, { method: 'HEAD' });
        if (res.ok) {
          probeResults.textures.push(name);
        }
      } catch {
        // Not found, continue
      }
    }

    if (
      probeResults.skyboxes.length > 0 ||
      probeResults.models.length > 0 ||
      probeResults.textures.length > 0
    ) {
      console.log('[AssetLoader] Probed assets found:', probeResults);
    }

    return probeResults.skyboxes.length === 0 &&
           probeResults.models.length === 0 &&
           probeResults.textures.length === 0
      ? empty
      : probeResults;
  }

  /**
   * Dispose all loaded assets and release GPU memory.
   */
  dispose(): void {
    this.disposed = true;

    for (const tex of this.loadedTextures) {
      tex.dispose();
    }
    this.loadedTextures = [];

    this.dracoLoader.dispose();

    console.log('[AssetLoader] Disposed');
  }
}
