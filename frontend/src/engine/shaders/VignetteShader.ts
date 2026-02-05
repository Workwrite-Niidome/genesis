/**
 * Vignette Post-Processing Shader
 *
 * Darkens the edges and corners of the frame to draw the viewer's eye
 * toward the center of the scene. The effect is gentle and cinematic,
 * adding depth and focus without being distracting.
 *
 * Parameters:
 *  - offset: Controls where the vignette starts (higher = more of the
 *    center is untouched). Default 1.0.
 *  - darkness: Intensity of the edge darkening. Default 1.2.
 */

export const VignetteShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    offset: { value: 1.0 },     // vignette offset (how far from center darkening begins)
    darkness: { value: 1.2 },    // vignette darkness intensity
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
    uniform float offset;
    uniform float darkness;

    varying vec2 vUv;

    void main() {
      // Remap UV from [0,1] to [-1,1] so center is (0,0)
      vec2 uv = (vUv - 0.5) * 2.0;

      // Radial falloff based on distance from center
      float vignette = 1.0 - dot(uv, uv) * darkness * 0.25;
      vignette = clamp(vignette, 0.0, 1.0);
      vignette = smoothstep(0.0, offset, vignette);

      vec3 color = texture2D(tDiffuse, vUv).rgb;
      gl_FragColor = vec4(color * vignette, 1.0);
    }
  `,
};

// Type import used only for the uniform typing above
import type * as THREE from 'three';
