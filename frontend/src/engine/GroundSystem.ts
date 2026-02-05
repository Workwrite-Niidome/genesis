/**
 * GENESIS v3 GroundSystem
 *
 * Procedural textured ground plane with a Japanese temple/shrine aesthetic.
 * Replaces the flat wire GridHelper with a rich, shader-driven surface that
 * blends dark earth and stone tones, marks main paths along the x and z axes,
 * and adds a subtle moss tint in distant areas.
 *
 * The ground plane sits at y=0 and is placed on layer 1 so it does not
 * interfere with entity click raycasting (which uses the default layer 0).
 */
import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Shader code
// ---------------------------------------------------------------------------

const groundVertexShader = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorldPosition;

  void main() {
    vUv = uv;
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPos.xyz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const groundFragmentShader = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorldPosition;

  // ---- Hash-based pseudo-random noise ----

  // Simple 2D hash -> float in [0, 1)
  float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
  }

  // Value noise: smooth interpolation of hash values on a grid
  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    // Hermite interpolation for smooth transitions
    vec2 u = f * f * (3.0 - 2.0 * f);

    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));

    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
  }

  // Fractal Brownian Motion — layered noise for natural-looking variation
  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    for (int i = 0; i < 4; i++) {
      value += amplitude * noise(p * frequency);
      amplitude *= 0.5;
      frequency *= 2.0;
    }
    return value;
  }

  void main() {
    vec2 pos = vWorldPosition.xz;

    // ---- Base colors ----
    vec3 darkEarth = vec3(0.165, 0.145, 0.125);   // #2a2520
    vec3 darkStone = vec3(0.188, 0.157, 0.157);    // #302828

    // ---- Large-scale terrain color variation ----
    float largeMix = fbm(pos * 0.04);
    vec3 baseColor = mix(darkEarth, darkStone, largeMix);

    // ---- Small-scale surface grain ----
    float grain = noise(pos * 3.0) * 0.06 - 0.03;
    baseColor += vec3(grain);

    // ---- Extra fine detail ----
    float fine = noise(pos * 12.0) * 0.03 - 0.015;
    baseColor += vec3(fine);

    // ---- Stone path along x-axis and z-axis ----
    float pathHalfWidth = 2.0;
    float pathEdgeSoftness = 1.0;

    // Distance to the x-axis path (z near 0) and z-axis path (x near 0)
    float distToXPath = abs(pos.y);  // pos.y is actually world z
    float distToZPath = abs(pos.x);

    // Smooth path masks
    float xPathMask = 1.0 - smoothstep(pathHalfWidth - pathEdgeSoftness, pathHalfWidth + pathEdgeSoftness, distToXPath);
    float zPathMask = 1.0 - smoothstep(pathHalfWidth - pathEdgeSoftness, pathHalfWidth + pathEdgeSoftness, distToZPath);
    float pathMask = max(xPathMask, zPathMask);

    // Stone path color with slight noise variation
    vec3 stonePathColor = vec3(0.333, 0.333, 0.333);  // #555555
    float stoneVariation = noise(pos * 1.5) * 0.06 - 0.03;
    stonePathColor += vec3(stoneVariation);

    // Blend path onto base
    baseColor = mix(baseColor, stonePathColor, pathMask * 0.85);

    // ---- Grid lines on paths (suggesting stone blocks) ----
    // Only visible where pathMask is significant
    if (pathMask > 0.05) {
      // Thin lines at integer positions
      vec2 gridFrac = abs(fract(pos - 0.5) - 0.5);
      float lineThickness = 0.03;
      float lineX = 1.0 - smoothstep(0.0, lineThickness, gridFrac.x);
      float lineZ = 1.0 - smoothstep(0.0, lineThickness, gridFrac.y);
      float gridLine = max(lineX, lineZ);

      // Darken for grid lines
      vec3 gridColor = baseColor * 0.7;
      baseColor = mix(baseColor, gridColor, gridLine * pathMask * 0.5);
    }

    // ---- Subtle moss/grass tint far from paths ----
    float minPathDist = min(distToXPath, distToZPath);
    float mossMask = smoothstep(8.0, 20.0, minPathDist);
    vec3 mossColor = vec3(0.165, 0.188, 0.125);  // #2a3020
    float mossNoise = fbm(pos * 0.15) * 0.7 + 0.3;
    baseColor = mix(baseColor, mossColor, mossMask * mossNoise * 0.35);

    // ---- Distance-based darkening (complement the fog) ----
    float distFromCenter = length(pos) / 200.0;
    baseColor *= mix(1.0, 0.6, clamp(distFromCenter, 0.0, 1.0));

    gl_FragColor = vec4(baseColor, 1.0);
  }
`;

// ---------------------------------------------------------------------------
// GroundSystem class
// ---------------------------------------------------------------------------

export class GroundSystem {
  private mesh: THREE.Mesh;
  private material: THREE.ShaderMaterial;
  private scene: THREE.Scene;

  constructor(scene: THREE.Scene) {
    this.scene = scene;

    // Large ground plane at y=0
    const geometry = new THREE.PlaneGeometry(400, 400, 1, 1);
    geometry.rotateX(-Math.PI / 2);

    this.material = new THREE.ShaderMaterial({
      vertexShader: groundVertexShader,
      fragmentShader: groundFragmentShader,
      side: THREE.FrontSide,
      depthWrite: true,
    });

    this.mesh = new THREE.Mesh(geometry, this.material);
    this.mesh.position.y = 0;
    this.mesh.receiveShadow = true;

    // Place on layer 1 so default raycaster (layer 0) ignores it,
    // matching the pattern used by WaterPlane.
    this.mesh.layers.set(1);

    this.scene.add(this.mesh);
  }

  dispose(): void {
    this.scene.remove(this.mesh);
    this.mesh.geometry.dispose();
    this.material.dispose();
  }
}
