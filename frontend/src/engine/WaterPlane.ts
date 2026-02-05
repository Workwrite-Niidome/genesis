/**
 * GENESIS v3 WaterPlane
 *
 * Ethereal reflective water surface inspired by 超かぐや姫 (Super Kaguya-hime).
 * A large, semi-transparent mirror-like plane at ground level with animated
 * ripple displacement via custom vertex/fragment shaders.
 *
 * The water plane is placed on layer 1 so it does not interfere with entity
 * click raycasting (which uses the default layer 0).
 */
import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Shader code
// ---------------------------------------------------------------------------

const waterVertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uWaveAmplitude;
  uniform float uWaveFrequency;

  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vNormal;

  void main() {
    vUv = uv;

    // Gentle multi-octave sine ripple displacement on Y
    vec3 pos = position;
    float wave1 = sin(pos.x * uWaveFrequency + uTime * 0.6) *
                  cos(pos.z * uWaveFrequency * 0.8 + uTime * 0.4) * uWaveAmplitude;
    float wave2 = sin(pos.x * uWaveFrequency * 1.7 - uTime * 0.35) *
                  cos(pos.z * uWaveFrequency * 1.3 + uTime * 0.55) * uWaveAmplitude * 0.5;
    float wave3 = sin(pos.x * uWaveFrequency * 3.1 + uTime * 0.8) *
                  sin(pos.z * uWaveFrequency * 2.7 - uTime * 0.65) * uWaveAmplitude * 0.2;
    pos.y += wave1 + wave2 + wave3;

    // Approximate normal perturbation for lighting
    float dx = cos(pos.x * uWaveFrequency + uTime * 0.6) * uWaveFrequency * uWaveAmplitude;
    float dz = -sin(pos.z * uWaveFrequency * 0.8 + uTime * 0.4) * uWaveFrequency * 0.8 * uWaveAmplitude;
    vNormal = normalize(vec3(-dx, 1.0, -dz));

    vec4 worldPos = modelMatrix * vec4(pos, 1.0);
    vWorldPosition = worldPos.xyz;

    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

const waterFragmentShader = /* glsl */ `
  uniform float uTime;
  uniform vec3 uDeepColor;
  uniform vec3 uShallowColor;
  uniform vec3 uSpecularColor;
  uniform float uOpacity;
  uniform vec3 uCameraPosition;

  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vNormal;

  void main() {
    // Fresnel-like view-dependent transparency
    vec3 viewDir = normalize(uCameraPosition - vWorldPosition);
    float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 3.0);

    // Mix deep and shallow colors based on fresnel
    vec3 baseColor = mix(uDeepColor, uShallowColor, fresnel * 0.6);

    // Simple specular highlight from a directional light (top-right)
    vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));
    vec3 halfDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(vNormal, halfDir), 0.0), 128.0);
    vec3 specular = uSpecularColor * spec * 0.8;

    // Subtle animated caustic pattern
    float caustic = sin(vWorldPosition.x * 2.0 + uTime * 0.5) *
                    sin(vWorldPosition.z * 2.0 - uTime * 0.3) * 0.5 + 0.5;
    caustic = pow(caustic, 3.0) * 0.15;

    vec3 finalColor = baseColor + specular + vec3(caustic * 0.3, caustic * 0.5, caustic * 0.7);

    // Opacity: stronger at grazing angles (fresnel), base opacity otherwise
    float alpha = mix(uOpacity, min(uOpacity + 0.25, 0.95), fresnel);

    gl_FragColor = vec4(finalColor, alpha);
  }
`;

// ---------------------------------------------------------------------------
// WaterPlane class
// ---------------------------------------------------------------------------

export class WaterPlane {
  private mesh: THREE.Mesh;
  private material: THREE.ShaderMaterial;
  private scene: THREE.Scene;

  constructor(scene: THREE.Scene) {
    this.scene = scene;

    // High-segment plane for smooth vertex displacement
    const geometry = new THREE.PlaneGeometry(400, 400, 200, 200);
    geometry.rotateX(-Math.PI / 2);

    this.material = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0.0 },
        uWaveAmplitude: { value: 0.12 },
        uWaveFrequency: { value: 0.08 },
        uDeepColor: { value: new THREE.Color(0x0a1e2e) },
        uShallowColor: { value: new THREE.Color(0x1a4a5a) },
        uSpecularColor: { value: new THREE.Color(0x8ec8ff) },
        uOpacity: { value: 0.65 },
        uCameraPosition: { value: new THREE.Vector3() },
      },
      vertexShader: waterVertexShader,
      fragmentShader: waterFragmentShader,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });

    this.mesh = new THREE.Mesh(geometry, this.material);
    this.mesh.position.y = -0.5;
    this.mesh.renderOrder = -1; // Render before other transparent objects

    // Put on layer 1 so default raycaster (layer 0) ignores it
    this.mesh.layers.set(1);

    this.scene.add(this.mesh);
  }

  /**
   * Update water animation each frame.
   * @param time - elapsed time in seconds (e.g. from THREE.Clock.getElapsedTime())
   */
  update(time: number): void {
    this.material.uniforms.uTime.value = time;
  }

  /**
   * Update the camera position uniform for fresnel calculations.
   * Call this if camera moves; the WorldScene passes it each frame.
   */
  setCameraPosition(pos: THREE.Vector3): void {
    this.material.uniforms.uCameraPosition.value.copy(pos);
  }

  dispose(): void {
    this.scene.remove(this.mesh);
    this.mesh.geometry.dispose();
    this.material.dispose();
  }
}
