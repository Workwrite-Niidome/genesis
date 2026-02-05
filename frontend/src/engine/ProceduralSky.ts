/**
 * GENESIS v3 ProceduralSky
 *
 * Generates a high-quality equirectangular sky texture (2048x1024) at runtime
 * using a 2D canvas. Features a mystical twilight sky with stars, aurora borealis,
 * wispy clouds, and a glowing moon — all painted procedurally.
 *
 * Used as a fallback when no AI-generated skybox is available.
 * The result is applied as both scene.background and scene.environment so that
 * all PBR materials receive correct reflections and environment lighting.
 */
import * as THREE from 'three';

// ---------- Helpers ----------

/** Smooth cosine interpolation between 0 and 1. */
function smoothstep(t: number): number {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}

/** Hermite (cosine-style) interpolation between two colors. */
function lerpColor(
  r1: number, g1: number, b1: number,
  r2: number, g2: number, b2: number,
  t: number,
): [number, number, number] {
  const s = smoothstep(t);
  return [
    Math.round(r1 + (r2 - r1) * s),
    Math.round(g1 + (g2 - g1) * s),
    Math.round(b1 + (b2 - b1) * s),
  ];
}

/** Parse a hex color string into [r, g, b]. */
function hexToRgb(hex: string): [number, number, number] {
  const v = parseInt(hex.replace('#', ''), 16);
  return [(v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff];
}

/** Simple pseudo-random seeded generator (xorshift32) for deterministic output. */
function makeRng(seed: number) {
  let s = seed | 0 || 1;
  return (): number => {
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    return ((s >>> 0) / 0x100000000);
  };
}

// ---------- Color Stops ----------

const ZENITH    = hexToRgb('#050520');
const UPPER     = hexToRgb('#1a0a4e');
const MID       = hexToRgb('#3d1a6e');
const HORIZON_A = hexToRgb('#8b2a6b');
const HORIZON_B = hexToRgb('#cc6b3a');
const BELOW     = hexToRgb('#0a0510');

// ---------- Main Class ----------

export class ProceduralSky {
  /**
   * Generate the procedural sky texture.
   * Returned texture has EquirectangularReflectionMapping set so it works
   * directly as `scene.background` and `scene.environment`.
   */
  static generate(_renderer: THREE.WebGLRenderer): THREE.Texture {
    const W = 2048;
    const H = 1024;

    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d')!;

    // 1. Sky gradient
    ProceduralSky.drawGradient(ctx, W, H);

    // 2. Stars (upper sky)
    ProceduralSky.drawStars(ctx, W, H);

    // 3. Moon (before aurora so aurora can overlap slightly)
    ProceduralSky.drawMoon(ctx, W, H);

    // 4. Aurora / Northern Lights
    ProceduralSky.drawAurora(ctx, W, H);

    // 5. Clouds near horizon
    ProceduralSky.drawClouds(ctx, W, H);

    // Create texture
    const texture = new THREE.CanvasTexture(canvas);
    texture.mapping = THREE.EquirectangularReflectionMapping;
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;

    return texture;
  }

  /**
   * Generate and apply the sky as both scene.background and scene.environment.
   * Returns the texture so the caller can dispose() it later.
   */
  static apply(scene: THREE.Scene, renderer: THREE.WebGLRenderer): THREE.Texture {
    const texture = ProceduralSky.generate(renderer);
    scene.background = texture;
    scene.environment = texture;
    return texture;
  }

  // ========== Drawing Routines ==========

  /** 1. Multi-stop sky gradient with cosine interpolation. */
  private static drawGradient(ctx: CanvasRenderingContext2D, W: number, H: number): void {
    // We iterate row by row for smooth cosine blending across multiple stops.
    // v goes from 0 (top = zenith) to 1 (bottom = below horizon).
    // In equirectangular mapping: v=0 is north pole (zenith), v=0.5 is horizon, v=1 is nadir.

    const imageData = ctx.createImageData(W, H);
    const data = imageData.data;

    for (let y = 0; y < H; y++) {
      const v = y / H; // 0 = top (zenith), 1 = bottom (nadir)

      let r: number, g: number, b: number;

      if (v < 0.15) {
        // Zenith to upper sky
        [r, g, b] = lerpColor(...ZENITH, ...UPPER, v / 0.15);
      } else if (v < 0.30) {
        // Upper sky to mid sky
        [r, g, b] = lerpColor(...UPPER, ...MID, (v - 0.15) / 0.15);
      } else if (v < 0.42) {
        // Mid sky to warm magenta horizon
        [r, g, b] = lerpColor(...MID, ...HORIZON_A, (v - 0.30) / 0.12);
      } else if (v < 0.52) {
        // Magenta to amber at horizon
        [r, g, b] = lerpColor(...HORIZON_A, ...HORIZON_B, (v - 0.42) / 0.10);
      } else if (v < 0.58) {
        // Amber back to magenta (symmetry below horizon)
        [r, g, b] = lerpColor(...HORIZON_B, ...HORIZON_A, (v - 0.52) / 0.06);
      } else {
        // Below horizon to dark
        [r, g, b] = lerpColor(...HORIZON_A, ...BELOW, Math.min(1, (v - 0.58) / 0.20));
      }

      for (let x = 0; x < W; x++) {
        const idx = (y * W + x) * 4;
        data[idx]     = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }

    ctx.putImageData(imageData, 0, 0);
  }

  /** 2. Draw a starfield in the upper portion of the sky. */
  private static drawStars(ctx: CanvasRenderingContext2D, W: number, H: number): void {
    const rng = makeRng(42);

    // Star color palette
    const starColors = [
      'rgba(255,255,255,',   // white
      'rgba(200,220,255,',   // pale blue
      'rgba(255,240,200,',   // pale yellow
      'rgba(180,200,255,',   // blue-ish
      'rgba(255,220,180,',   // warm
    ];

    // -- Small stars (~2000) --
    const smallCount = 2000;
    for (let i = 0; i < smallCount; i++) {
      const x = rng() * W;
      // Weight toward zenith: use square of random to cluster near top
      const yRaw = rng() * rng();
      const y = yRaw * H * 0.48; // upper hemisphere only (0 to ~0.48)

      const brightness = 0.3 + rng() * 0.7;
      const size = 0.4 + rng() * 1.0;
      const colorBase = starColors[Math.floor(rng() * starColors.length)];

      ctx.fillStyle = `${colorBase}${brightness.toFixed(2)})`;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fill();
    }

    // -- Bright stars with glow (~10) --
    const brightCount = 10;
    for (let i = 0; i < brightCount; i++) {
      const x = rng() * W;
      const y = rng() * rng() * H * 0.40;
      const radius = 2 + rng() * 3;

      // Glow halo
      const grad = ctx.createRadialGradient(x, y, 0, x, y, radius * 4);
      const hue = rng() < 0.5 ? '200,220,255' : '255,240,210';
      grad.addColorStop(0, `rgba(${hue},0.9)`);
      grad.addColorStop(0.2, `rgba(${hue},0.4)`);
      grad.addColorStop(0.5, `rgba(${hue},0.1)`);
      grad.addColorStop(1, `rgba(${hue},0)`);

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, radius * 4, 0, Math.PI * 2);
      ctx.fill();

      // Bright core
      ctx.fillStyle = `rgba(255,255,255,0.95)`;
      ctx.beginPath();
      ctx.arc(x, y, radius * 0.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  /** 3. Draw aurora borealis bands in the upper-mid sky. */
  private static drawAurora(ctx: CanvasRenderingContext2D, W: number, H: number): void {
    ctx.save();
    ctx.globalCompositeOperation = 'screen';

    // Aurora band configurations
    const bands = [
      { color: [0, 255, 136],  yBase: H * 0.18, amplitude: H * 0.06, freq: 3, phase: 0,   alpha: 0.12 },
      { color: [136, 85, 255], yBase: H * 0.24, amplitude: H * 0.05, freq: 4, phase: 1.2, alpha: 0.10 },
      { color: [0, 221, 255],  yBase: H * 0.15, amplitude: H * 0.04, freq: 5, phase: 2.5, alpha: 0.08 },
    ];

    for (const band of bands) {
      const { color, yBase, amplitude, freq, phase, alpha } = band;
      const [cr, cg, cb] = color;

      // Draw the band multiple times with slight offsets for a soft/blurred look
      for (let pass = 0; pass < 12; pass++) {
        const passOffset = (pass - 6) * 2;
        ctx.globalAlpha = alpha * (1 - Math.abs(pass - 6) / 8);

        ctx.beginPath();

        for (let x = 0; x <= W; x += 2) {
          const nx = x / W;
          // Layered sine waves for organic flowing shape
          const wave =
            Math.sin(nx * Math.PI * 2 * freq + phase) * 0.5 +
            Math.sin(nx * Math.PI * 2 * (freq * 1.7) + phase * 1.3) * 0.3 +
            Math.sin(nx * Math.PI * 2 * (freq * 3.1) + phase * 0.7) * 0.2;

          const y = yBase + wave * amplitude + passOffset;
          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }

        // Close the shape by going to the bottom edge and back
        ctx.lineTo(W, yBase + amplitude * 1.5 + passOffset);
        ctx.lineTo(0, yBase + amplitude * 1.5 + passOffset);
        ctx.closePath();

        ctx.fillStyle = `rgb(${cr},${cg},${cb})`;
        ctx.fill();
      }

      // Subtle vertical streaks for the aurora
      ctx.globalAlpha = alpha * 0.4;
      for (let sx = 0; sx < W; sx += 8 + Math.floor(Math.random() * 12)) {
        const nx = sx / W;
        const wave =
          Math.sin(nx * Math.PI * 2 * freq + phase) * 0.5 +
          Math.sin(nx * Math.PI * 2 * (freq * 1.7) + phase * 1.3) * 0.3 +
          Math.sin(nx * Math.PI * 2 * (freq * 3.1) + phase * 0.7) * 0.2;

        const streakY = yBase + wave * amplitude;
        const streakH = 10 + Math.random() * 30;

        const streakGrad = ctx.createLinearGradient(sx, streakY - streakH, sx, streakY + streakH);
        streakGrad.addColorStop(0, `rgba(${cr},${cg},${cb},0)`);
        streakGrad.addColorStop(0.3, `rgba(${cr},${cg},${cb},${(alpha * 0.6).toFixed(2)})`);
        streakGrad.addColorStop(0.7, `rgba(${cr},${cg},${cb},${(alpha * 0.4).toFixed(2)})`);
        streakGrad.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);

        ctx.fillStyle = streakGrad;
        ctx.fillRect(sx, streakY - streakH, 2, streakH * 2);
      }
    }

    ctx.restore();
  }

  /** 4. Draw wispy cloud layers near the horizon. */
  private static drawClouds(ctx: CanvasRenderingContext2D, W: number, H: number): void {
    const rng = makeRng(137);

    ctx.save();
    ctx.globalCompositeOperation = 'source-over';

    // Cloud base colors: dark purple-gray with warm tint
    const cloudColors = [
      [60, 30, 70],
      [50, 25, 55],
      [70, 35, 60],
      [45, 25, 50],
    ];

    // Multiple cloud layers near the horizon (v ~ 0.35 to 0.50 region)
    const layerCount = 4;
    for (let layer = 0; layer < layerCount; layer++) {
      const baseY = H * (0.34 + layer * 0.04);
      const cloudCount = 30 + Math.floor(rng() * 20);

      for (let i = 0; i < cloudCount; i++) {
        const cx = rng() * W;
        const cy = baseY + (rng() - 0.5) * H * 0.04;
        const cw = 40 + rng() * 160;
        const ch = 4 + rng() * 12;
        const color = cloudColors[Math.floor(rng() * cloudColors.length)];

        // Draw wispy ellipse with multiple overlapping strokes
        for (let p = 0; p < 5; p++) {
          const ox = (rng() - 0.5) * cw * 0.3;
          const oy = (rng() - 0.5) * ch * 0.5;
          const pw = cw * (0.5 + rng() * 0.5);
          const ph = ch * (0.6 + rng() * 0.4);

          ctx.globalAlpha = 0.03 + rng() * 0.06;
          ctx.fillStyle = `rgb(${color[0]},${color[1]},${color[2]})`;

          ctx.beginPath();
          ctx.ellipse(cx + ox, cy + oy, pw / 2, ph / 2, 0, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // Extra thin wispy layer very close to horizon line for blending
    const wispY = H * 0.48;
    for (let i = 0; i < 60; i++) {
      const x = rng() * W;
      const y = wispY + (rng() - 0.5) * H * 0.03;
      const w = 60 + rng() * 200;
      const h = 2 + rng() * 6;

      ctx.globalAlpha = 0.02 + rng() * 0.04;
      ctx.fillStyle = `rgb(80,45,60)`;

      ctx.beginPath();
      ctx.ellipse(x, y, w / 2, h / 2, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  /** 5. Draw a glowing moon in the upper portion of the sky. */
  private static drawMoon(ctx: CanvasRenderingContext2D, W: number, H: number): void {
    ctx.save();

    // Position the moon in the upper sky (roughly 20% down, 70% across)
    const moonX = W * 0.70;
    const moonY = H * 0.12;
    const moonRadius = 30;

    // Outer halo (large, very soft glow)
    const haloRadius = moonRadius * 6;
    const haloGrad = ctx.createRadialGradient(moonX, moonY, 0, moonX, moonY, haloRadius);
    haloGrad.addColorStop(0, 'rgba(255, 245, 220, 0.15)');
    haloGrad.addColorStop(0.15, 'rgba(255, 240, 210, 0.08)');
    haloGrad.addColorStop(0.4, 'rgba(200, 180, 255, 0.04)');
    haloGrad.addColorStop(1, 'rgba(200, 180, 255, 0)');

    ctx.globalCompositeOperation = 'screen';
    ctx.fillStyle = haloGrad;
    ctx.beginPath();
    ctx.arc(moonX, moonY, haloRadius, 0, Math.PI * 2);
    ctx.fill();

    // Middle glow
    const midGlowRadius = moonRadius * 2.5;
    const midGrad = ctx.createRadialGradient(moonX, moonY, 0, moonX, moonY, midGlowRadius);
    midGrad.addColorStop(0, 'rgba(255, 250, 235, 0.5)');
    midGrad.addColorStop(0.3, 'rgba(255, 245, 225, 0.2)');
    midGrad.addColorStop(0.7, 'rgba(230, 220, 255, 0.05)');
    midGrad.addColorStop(1, 'rgba(230, 220, 255, 0)');

    ctx.fillStyle = midGrad;
    ctx.beginPath();
    ctx.arc(moonX, moonY, midGlowRadius, 0, Math.PI * 2);
    ctx.fill();

    // Moon disc (pale yellow-white, soft edge)
    ctx.globalCompositeOperation = 'source-over';
    const discGrad = ctx.createRadialGradient(moonX, moonY, 0, moonX, moonY, moonRadius);
    discGrad.addColorStop(0, 'rgba(255, 252, 240, 0.95)');
    discGrad.addColorStop(0.5, 'rgba(255, 248, 230, 0.85)');
    discGrad.addColorStop(0.8, 'rgba(240, 235, 220, 0.50)');
    discGrad.addColorStop(1, 'rgba(220, 215, 240, 0)');

    ctx.fillStyle = discGrad;
    ctx.beginPath();
    ctx.arc(moonX, moonY, moonRadius, 0, Math.PI * 2);
    ctx.fill();

    // Subtle surface detail (darker patches to hint at craters)
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = 'rgba(180, 170, 200, 1)';
    ctx.beginPath();
    ctx.arc(moonX - 8, moonY - 5, 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalAlpha = 0.08;
    ctx.beginPath();
    ctx.arc(moonX + 6, moonY + 8, 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalAlpha = 0.10;
    ctx.beginPath();
    ctx.arc(moonX + 10, moonY - 7, 3, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }
}
