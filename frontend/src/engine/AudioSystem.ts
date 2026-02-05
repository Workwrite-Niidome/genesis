/**
 * GENESIS v3 Spatial Audio System
 *
 * Manages positional 3D audio using the Web Audio API:
 * - Entity speech cues (synthesized tones shaped by personality)
 * - Building sounds (place / destroy)
 * - Ambient drone scaled by entity density
 * - Placeholder for future entity-created music
 *
 * Uses inverse-distance attenuation (maxDistance 200, rolloff 1.0).
 * All operations fail gracefully when AudioContext is unavailable.
 */
import type { PersonalityParams } from '../types/v3';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Minimal 3D position vector (matches Vector3 from v3 types). */
export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

/** Forward direction for the listener (xz-plane). */
export interface Forward2 {
  x: number;
  z: number;
}

/** Categories of sounds the system can manage. */
export type SoundCategory = 'speech' | 'ambient' | 'building' | 'music';

/** An active audio source tracked by the system. */
export interface AudioSource {
  id: string;
  category: SoundCategory;
  panner: PannerNode;
  gain: GainNode;
  /** The oscillator / buffer-source currently playing (may be null for ended one-shots). */
  sourceNode: AudioScheduledSourceNode | null;
  /** If true, the source loops continuously and must be stopped explicitly. */
  continuous: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_DISTANCE = 200;
const ROLLOFF_FACTOR = 1.0;
const REF_DISTANCE = 1;

/** Base frequency range for speech cues (Hz). */
const SPEECH_FREQ_MIN = 180;
const SPEECH_FREQ_MAX = 600;

/** Duration of a single speech cue in seconds. */
const SPEECH_DURATION = 0.25;

/** Duration of a build sound in seconds. */
const BUILD_DURATION = 0.12;

// ---------------------------------------------------------------------------
// AudioSystem
// ---------------------------------------------------------------------------

export class AudioSystem {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private sources: Map<string, AudioSource> = new Map();

  // Track ambient state so we can update rather than re-create.
  private ambientId = '__ambient__';

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  /**
   * Create the AudioContext. Must be called inside a user-gesture handler
   * (click, keydown, etc.) to satisfy browser autoplay policies.
   */
  init(): void {
    if (this.ctx) return;

    try {
      this.ctx = new AudioContext();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0.6;
      this.masterGain.connect(this.ctx.destination);
    } catch {
      // Web Audio not available — all subsequent calls will be no-ops.
      this.ctx = null;
      this.masterGain = null;
    }
  }

  /** Whether the AudioContext has been successfully initialised. */
  get ready(): boolean {
    return this.ctx !== null && this.ctx.state !== 'closed';
  }

  // -----------------------------------------------------------------------
  // Listener
  // -----------------------------------------------------------------------

  /**
   * Synchronise the Web Audio listener with the camera position and
   * orientation every frame.
   *
   * @param pos    Camera world position.
   * @param forward Camera forward direction on the xz-plane (normalised).
   */
  updateListenerPosition(pos: Vec3, forward: Forward2): void {
    if (!this.ctx) return;
    const listener = this.ctx.listener;

    // Position
    if (listener.positionX) {
      listener.positionX.value = pos.x;
      listener.positionY.value = pos.y;
      listener.positionZ.value = pos.z;
    } else {
      listener.setPosition(pos.x, pos.y, pos.z);
    }

    // Orientation — forward + up
    if (listener.forwardX) {
      listener.forwardX.value = forward.x;
      listener.forwardY.value = 0;
      listener.forwardZ.value = forward.z;
      listener.upX.value = 0;
      listener.upY.value = 1;
      listener.upZ.value = 0;
    } else {
      listener.setOrientation(forward.x, 0, forward.z, 0, 1, 0);
    }
  }

  // -----------------------------------------------------------------------
  // Speech Cues
  // -----------------------------------------------------------------------

  /**
   * Play a short synthesised tone when an entity speaks.
   *
   * Tone characteristics are derived from the entity's personality:
   * - **Pitch**: Higher verbosity pushes the fundamental frequency up.
   * - **Harshness**: Lower politeness uses a sawtooth wave; higher uses sine.
   * - **Attack**: High aggression shortens the attack; high patience lengthens it.
   *
   * @param entityId   Unique entity identifier (used to prevent overlapping cues).
   * @param position   World position of the speaking entity.
   * @param personality  The entity's personality parameters.
   */
  playSpeechCue(
    entityId: string,
    position: Vec3,
    personality: Partial<PersonalityParams>,
  ): void {
    if (!this.ctx || !this.masterGain) return;

    // If this entity already has a speech cue playing, let it finish
    // naturally rather than stacking sounds.
    const existingKey = `speech_${entityId}`;
    if (this.sources.has(existingKey)) return;

    const now = this.ctx.currentTime;

    // Derive parameters from personality (default to mid-range 0.5).
    const verbosity = personality.verbosity ?? 0.5;
    const politeness = personality.politeness ?? 0.5;
    const aggression = personality.aggression ?? 0.5;
    const humor = personality.humor ?? 0.5;
    const patience = personality.patience ?? 0.5;

    // Frequency: verbosity maps linearly within the speech range.
    const baseFreq =
      SPEECH_FREQ_MIN + verbosity * (SPEECH_FREQ_MAX - SPEECH_FREQ_MIN);

    // Add a slight warble for humorous entities.
    const warble = humor * 30; // up to +30 Hz deviation

    // Wave type: polite entities get a gentle sine; rude ones get sawtooth.
    const waveType: OscillatorType =
      politeness >= 0.5 ? 'sine' : 'sawtooth';

    // Attack time: aggressive entities have a snappy onset.
    const attack = 0.01 + (1 - aggression) * 0.04; // 10-50 ms
    // Release time: patient entities have longer tails.
    const release = 0.05 + patience * 0.15; // 50-200 ms

    // Create nodes.
    const osc = this.ctx.createOscillator();
    osc.type = waveType;
    osc.frequency.setValueAtTime(baseFreq, now);
    // Apply warble as a quick vibrato.
    if (warble > 1) {
      osc.frequency.linearRampToValueAtTime(baseFreq + warble, now + SPEECH_DURATION * 0.5);
      osc.frequency.linearRampToValueAtTime(baseFreq, now + SPEECH_DURATION);
    }

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.25, now + attack);
    gain.gain.linearRampToValueAtTime(0, now + SPEECH_DURATION + release);

    const panner = this.createPanner(position);

    // Connect: osc -> gain -> panner -> master
    osc.connect(gain);
    gain.connect(panner);
    panner.connect(this.masterGain);

    osc.start(now);
    osc.stop(now + SPEECH_DURATION + release + 0.01);

    const source: AudioSource = {
      id: existingKey,
      category: 'speech',
      panner,
      gain,
      sourceNode: osc,
      continuous: false,
    };
    this.sources.set(existingKey, source);

    osc.onended = () => {
      this.cleanupSource(existingKey);
    };
  }

  // -----------------------------------------------------------------------
  // Building Sounds
  // -----------------------------------------------------------------------

  /**
   * Play a short percussive sound for block placement or destruction.
   *
   * - **place**: Higher-pitched click.
   * - **destroy**: Lower thud with more noise character.
   *
   * @param position World position of the voxel event.
   * @param type     Whether a block was placed or destroyed.
   */
  playBuildSound(position: Vec3, type: 'place' | 'destroy'): void {
    if (!this.ctx || !this.masterGain) return;

    const now = this.ctx.currentTime;
    const id = `build_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

    const freq = type === 'place' ? 800 : 200;
    const duration = BUILD_DURATION;
    const attackTime = 0.005;

    const osc = this.ctx.createOscillator();
    osc.type = type === 'place' ? 'square' : 'triangle';
    osc.frequency.setValueAtTime(freq, now);
    // Pitch drop for destroy gives a "thud" feeling.
    if (type === 'destroy') {
      osc.frequency.exponentialRampToValueAtTime(60, now + duration);
    }

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.2, now + attackTime);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    const panner = this.createPanner(position);

    osc.connect(gain);
    gain.connect(panner);
    panner.connect(this.masterGain);

    osc.start(now);
    osc.stop(now + duration + 0.01);

    const source: AudioSource = {
      id,
      category: 'building',
      panner,
      gain,
      sourceNode: osc,
      continuous: false,
    };
    this.sources.set(id, source);

    osc.onended = () => {
      this.cleanupSource(id);
    };
  }

  // -----------------------------------------------------------------------
  // Ambient Drone
  // -----------------------------------------------------------------------

  /**
   * Start or update a continuous ambient drone whose volume and complexity
   * scale with the number of active entities in the world.
   *
   * When called repeatedly (e.g. every tick), it smoothly adjusts the
   * existing drone rather than creating a new one.
   *
   * @param entityCount Current number of living entities.
   */
  playAmbient(entityCount: number): void {
    if (!this.ctx || !this.masterGain) return;

    // Target volume: quiet base hum + logarithmic growth with density.
    const targetGain = Math.min(
      0.15,
      0.02 + Math.log2(Math.max(entityCount, 1) + 1) * 0.015,
    );

    const existing = this.sources.get(this.ambientId);

    if (existing && existing.sourceNode) {
      // Smoothly ramp gain to new target.
      const now = this.ctx.currentTime;
      existing.gain.gain.cancelScheduledValues(now);
      existing.gain.gain.setValueAtTime(existing.gain.gain.value, now);
      existing.gain.gain.linearRampToValueAtTime(targetGain, now + 1.0);
      return;
    }

    // First time — create the ambient graph.
    const now = this.ctx.currentTime;

    // Low drone: a deep sine oscillator.
    const droneOsc = this.ctx.createOscillator();
    droneOsc.type = 'sine';
    droneOsc.frequency.setValueAtTime(55, now); // A1

    // Slow LFO modulating the drone amplitude for a "breathing" effect.
    const lfoOsc = this.ctx.createOscillator();
    lfoOsc.type = 'sine';
    lfoOsc.frequency.setValueAtTime(0.15, now); // very slow

    const lfoGain = this.ctx.createGain();
    lfoGain.gain.setValueAtTime(0.03, now);
    lfoOsc.connect(lfoGain);

    const droneGain = this.ctx.createGain();
    droneGain.gain.setValueAtTime(0, now);
    droneGain.gain.linearRampToValueAtTime(targetGain, now + 2.0);

    // Connect LFO to modulate drone gain.
    lfoGain.connect(droneGain.gain);

    // Ambient is non-positional — connect directly to master.
    droneOsc.connect(droneGain);
    droneGain.connect(this.masterGain);

    droneOsc.start(now);
    lfoOsc.start(now);

    // We only store the drone oscillator; the LFO is connected and will be
    // garbage-collected when the drone stops.
    const source: AudioSource = {
      id: this.ambientId,
      category: 'ambient',
      panner: null as unknown as PannerNode, // non-positional
      gain: droneGain,
      sourceNode: droneOsc,
      continuous: true,
    };

    // Keep a reference to the LFO so we can stop it during cleanup.
    (source as any)._lfo = lfoOsc;
    (source as any)._lfoGain = lfoGain;

    this.sources.set(this.ambientId, source);
  }

  // -----------------------------------------------------------------------
  // Music (placeholder)
  // -----------------------------------------------------------------------

  /**
   * Placeholder for future entity-created music playback.
   * Returns false to indicate that music is not yet implemented.
   */
  playMusic(_entityId: string, _position: Vec3): boolean {
    // TODO: Implement when entities can compose music.
    return false;
  }

  // -----------------------------------------------------------------------
  // Cleanup
  // -----------------------------------------------------------------------

  /**
   * Stop all currently playing sounds and remove all tracked sources.
   */
  stopAll(): void {
    for (const [id] of this.sources) {
      this.cleanupSource(id);
    }
    this.sources.clear();
  }

  /**
   * Tear down the AudioContext entirely. Call when the WorldScene is
   * being unmounted.
   */
  dispose(): void {
    this.stopAll();

    if (this.ctx && this.ctx.state !== 'closed') {
      this.ctx.close().catch(() => {
        // Ignore errors during close — context may already be gone.
      });
    }

    this.ctx = null;
    this.masterGain = null;
  }

  // -----------------------------------------------------------------------
  // Accessors (for testing / debugging)
  // -----------------------------------------------------------------------

  /** Number of active audio sources. */
  get activeSourceCount(): number {
    return this.sources.size;
  }

  /** Return the set of active source IDs (read-only snapshot). */
  getActiveSourceIds(): string[] {
    return Array.from(this.sources.keys());
  }

  // -----------------------------------------------------------------------
  // Private Helpers
  // -----------------------------------------------------------------------

  /**
   * Create a PannerNode configured for inverse-distance attenuation.
   */
  private createPanner(position: Vec3): PannerNode {
    const panner = this.ctx!.createPanner();
    panner.panningModel = 'HRTF';
    panner.distanceModel = 'inverse';
    panner.refDistance = REF_DISTANCE;
    panner.maxDistance = MAX_DISTANCE;
    panner.rolloffFactor = ROLLOFF_FACTOR;
    panner.coneInnerAngle = 360;
    panner.coneOuterAngle = 360;
    panner.coneOuterGain = 1;

    if (panner.positionX) {
      panner.positionX.value = position.x;
      panner.positionY.value = position.y;
      panner.positionZ.value = position.z;
    } else {
      panner.setPosition(position.x, position.y, position.z);
    }

    return panner;
  }

  /**
   * Disconnect and remove a tracked source by ID.
   */
  private cleanupSource(id: string): void {
    const source = this.sources.get(id);
    if (!source) return;

    try {
      if (source.sourceNode) {
        source.sourceNode.stop();
      }
    } catch {
      // Already stopped — this is fine.
    }

    try {
      // Stop any auxiliary nodes (e.g. LFO for ambient).
      const lfo = (source as any)._lfo as OscillatorNode | undefined;
      if (lfo) {
        lfo.stop();
        lfo.disconnect();
      }
      const lfoGain = (source as any)._lfoGain as GainNode | undefined;
      if (lfoGain) {
        lfoGain.disconnect();
      }

      if (source.sourceNode) {
        source.sourceNode.disconnect();
      }
      source.gain.disconnect();
      if (source.panner) {
        source.panner.disconnect();
      }
    } catch {
      // Disconnecting already-disconnected nodes throws — ignore.
    }

    this.sources.delete(id);
  }
}
