/**
 * Film Grain Post-Processing Shader
 *
 * Adds a very subtle, animated noise grain over the final image.
 * This breaks up banding in dark gradient regions (sky dome, fog)
 * and imparts a cinematic film-like quality to the rendering.
 *
 * The grain is pseudo-random based on UV coordinates and a time
 * uniform, so it animates every frame — mimicking real film grain.
 *
 * Parameters:
 *  - time: Elapsed time in seconds (updated each frame).
 *  - intensity: Strength of the grain. Keep very low (0.03-0.05)
 *    for a subtle effect that is felt rather than seen.
 */

export const FilmGrainShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    time: { value: 0.0 },
    intensity: { value: 0.04 },  // very subtle — barely noticeable
  },

  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,

  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform float intensity;

    varying vec2 vUv;

    void main() {
      // Pseudo-random noise derived from UV + time
      float noise = fract(
        sin(dot(vUv + vec2(time * 0.1, time * 0.2), vec2(12.9898, 78.233))) * 43758.5453
      );

      vec3 color = texture2D(tDiffuse, vUv).rgb;

      // Center noise around 0 (-0.5 to +0.5) and scale by intensity
      color += (noise - 0.5) * intensity;

      gl_FragColor = vec4(color, 1.0);
    }
  `,
};

// Type import used only for the uniform typing above
import type * as THREE from 'three';
