/**
 * 8-bit / Chiptune music player using Web Audio API.
 * Plays note sequences with oscillator-based synthesis.
 */

// Note name → frequency mapping (C3 to C6)
const NOTE_FREQ: Record<string, number> = {};
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

for (let octave = 3; octave <= 6; octave++) {
  for (let i = 0; i < NOTE_NAMES.length; i++) {
    const semitone = (octave - 4) * 12 + (i - 9); // A4 = 440Hz
    NOTE_FREQ[`${NOTE_NAMES[i]}${octave}`] = 440 * Math.pow(2, semitone / 12);
  }
}
// Add flat aliases (Db = C#, Eb = D#, etc.)
const FLAT_MAP: Record<string, string> = { Db: 'C#', Eb: 'D#', Gb: 'F#', Ab: 'G#', Bb: 'A#' };
for (let octave = 3; octave <= 6; octave++) {
  for (const [flat, sharp] of Object.entries(FLAT_MAP)) {
    NOTE_FREQ[`${flat}${octave}`] = NOTE_FREQ[`${sharp}${octave}`];
  }
}

export function noteToFreq(note: string): number | null {
  if (note === 'rest' || !note) return null;
  return NOTE_FREQ[note] ?? null;
}

export type WaveType = 'square' | 'triangle' | 'sawtooth' | 'sine';

export interface NoteData {
  note: string;
  dur: number; // in beats
}

export interface SongData {
  notes: NoteData[];
  tempo: number; // BPM
  wave: WaveType;
}

export class ChiptuneEngine {
  private ctx: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private scheduledSources: OscillatorNode[] = [];
  private _playing = false;
  private _startTime = 0;
  private _duration = 0;
  private _onTick: ((currentBeat: number) => void) | null = null;
  private _tickInterval: number | null = null;
  private _song: SongData | null = null;

  get playing() { return this._playing; }
  get duration() { return this._duration; }

  get currentTime(): number {
    if (!this.ctx || !this._playing) return 0;
    return this.ctx.currentTime - this._startTime;
  }

  onTick(cb: (currentTime: number) => void) {
    this._onTick = cb;
  }

  play(song: SongData) {
    this.stop();
    this._song = song;

    this.ctx = new AudioContext();
    this.gainNode = this.ctx.createGain();
    this.gainNode.gain.value = 0.15;
    this.gainNode.connect(this.ctx.destination);

    const secPerBeat = 60 / (song.tempo || 120);
    let time = this.ctx.currentTime + 0.05;
    this._startTime = time;

    for (const note of song.notes) {
      const dur = (note.dur || 0.25) * secPerBeat;
      const freq = noteToFreq(note.note);

      if (freq !== null) {
        const osc = this.ctx.createOscillator();
        osc.type = song.wave || 'square';
        osc.frequency.value = freq;

        // Envelope for 8-bit feel
        const env = this.ctx.createGain();
        env.gain.setValueAtTime(0, time);
        env.gain.linearRampToValueAtTime(1, time + 0.005);
        env.gain.setValueAtTime(1, time + dur - 0.01);
        env.gain.linearRampToValueAtTime(0, time + dur);

        osc.connect(env);
        env.connect(this.gainNode!);

        osc.start(time);
        osc.stop(time + dur + 0.01);
        this.scheduledSources.push(osc);
      }

      time += dur;
    }

    this._duration = time - this._startTime;
    this._playing = true;

    // Tick callback for UI updates
    if (this._onTick) {
      this._tickInterval = window.setInterval(() => {
        if (!this._playing || !this.ctx) {
          this._stopTick();
          return;
        }
        const elapsed = this.ctx.currentTime - this._startTime;
        if (elapsed >= this._duration) {
          this.stop();
          return;
        }
        this._onTick?.(elapsed);
      }, 50);
    }

    // Auto-stop when done
    setTimeout(() => {
      if (this._playing) this.stop();
    }, this._duration * 1000 + 200);
  }

  stop() {
    this._playing = false;
    this._stopTick();

    for (const osc of this.scheduledSources) {
      try { osc.stop(); } catch { /* already stopped */ }
    }
    this.scheduledSources = [];

    if (this.ctx) {
      this.ctx.close().catch(() => {});
      this.ctx = null;
    }
    this.gainNode = null;
  }

  private _stopTick() {
    if (this._tickInterval !== null) {
      clearInterval(this._tickInterval);
      this._tickInterval = null;
    }
  }

  /** Calculate total duration in seconds */
  static calcDuration(song: SongData): number {
    const secPerBeat = 60 / (song.tempo || 120);
    return song.notes.reduce((sum, n) => sum + (n.dur || 0.25) * secPerBeat, 0);
  }
}
