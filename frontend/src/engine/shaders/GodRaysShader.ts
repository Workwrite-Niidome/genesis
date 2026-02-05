/**
 * God Rays / Volumetric Light Scattering Shader
 *
 * Simulates volumetric light shafts by performing a radial blur from the
 * screen-space light position toward each fragment. Each sample along the
 * ray accumulates brightness with exponential decay, producing the
 * characteristic "god ray" streaks emanating from the light source.
 *
 * Inspired by the ethereal light effects in the twilight scenes of
 * the virtual worlds of GENESIS.
 */
import * as THREE from 'three';

export const GodRaysShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    lightPosition: { value: new THREE.Vector2(0.5, 0.7) }, // screen-space light position (NDC 0-1)
    exposure: { value: 0.25 },   // final ray intensity — kept low to avoid washing out the scene
    decay: { value: 0.95 },      // exponential decay per sample step
    density: { value: 0.8 },     // overall density of rays (scales delta step)
    weight: { value: 0.5 },      // per-sample weight
    samples: { value: 60 },      // number of samples along each ray
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
    uniform vec2 lightPosition;
    uniform float exposure;
    uniform float decay;
    uniform float density;
    uniform float weight;
    uniform int samples;

    varying vec2 vUv;

    void main() {
      // Direction from current fragment toward the light, scaled by density / sample count
      vec2 deltaTexCoord = (vUv - lightPosition) * density / float(samples);
      vec2 coord = vUv;
      float illuminationDecay = 1.0;
      vec3 color = vec3(0.0);

      // March along the ray from fragment toward the light, accumulating brightness
      for (int i = 0; i < 60; i++) {
        coord -= deltaTexCoord;
        vec3 samp = texture2D(tDiffuse, coord).rgb;
        samp *= illuminationDecay * weight;
        color += samp;
        illuminationDecay *= decay;
      }

      // Blend the accumulated god rays onto the original scene color
      vec3 original = texture2D(tDiffuse, vUv).rgb;
      gl_FragColor = vec4(original + color * exposure, 1.0);
    }
  `,
};
