import { useState, useRef, useCallback, useMemo } from 'react';
import { Play, Square, Music } from 'lucide-react';
import { ChiptuneEngine, type SongData } from '../../lib/musicPlayer';
import { generateFallbackNotes } from '../../lib/seedRandom';

interface ChiptunePlayerProps {
  artifact: { id: string; content?: any };
}

export default function ChiptunePlayer({ artifact }: ChiptunePlayerProps) {
  const engineRef = useRef<ChiptuneEngine | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [currentNoteIdx, setCurrentNoteIdx] = useState(-1);

  const song: SongData = useMemo(() => {
    const content = artifact.content || {};
    let notes = content.notes;
    if (!notes || !Array.isArray(notes) || notes.length === 0) {
      notes = generateFallbackNotes(artifact.id);
    }
    return {
      notes,
      tempo: content.tempo || 72,
      wave: content.wave || 'sine',
    };
  }, [artifact.id, artifact.content]);

  const totalDuration = useMemo(
    () => ChiptuneEngine.calcDuration(song),
    [song]
  );

  const handlePlay = useCallback(() => {
    if (playing) {
      engineRef.current?.stop();
      setPlaying(false);
      setCurrentTime(0);
      setCurrentNoteIdx(-1);
      return;
    }

    const engine = new ChiptuneEngine();
    engineRef.current = engine;

    const secPerBeat = 60 / (song.tempo || 120);

    engine.onTick((elapsed) => {
      setCurrentTime(elapsed);
      // Find which note is currently playing
      let t = 0;
      for (let i = 0; i < song.notes.length; i++) {
        const dur = (song.notes[i].dur || 0.25) * secPerBeat;
        if (elapsed >= t && elapsed < t + dur) {
          setCurrentNoteIdx(i);
          break;
        }
        t += dur;
      }
    });

    engine.play(song);
    setPlaying(true);

    // Reset when done
    setTimeout(() => {
      setPlaying(false);
      setCurrentTime(0);
      setCurrentNoteIdx(-1);
    }, totalDuration * 1000 + 300);
  }, [playing, song, totalDuration]);

  const progress = totalDuration > 0 ? Math.min(1, currentTime / totalDuration) : 0;

  return (
    <div className="rounded-xl bg-black/30 border border-white/[0.06] overflow-hidden">
      {/* Controls */}
      <div className="flex items-center gap-3 p-3">
        <button
          onClick={handlePlay}
          className="w-8 h-8 rounded-full bg-accent/20 text-accent flex items-center justify-center hover:bg-accent/30 transition-colors flex-shrink-0"
        >
          {playing ? <Square size={12} /> : <Play size={12} className="ml-0.5" />}
        </button>

        {/* Progress bar */}
        <div className="flex-1 min-w-0">
          <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-[width] duration-100"
              style={{
                width: `${progress * 100}%`,
                background: 'linear-gradient(90deg, #7c5bf5, #58d5f0)',
              }}
            />
          </div>
        </div>

        {/* Time */}
        <span className="text-[10px] mono text-text-3 flex-shrink-0 w-10 text-right">
          {formatTime(currentTime)}
        </span>
      </div>

      {/* Note display */}
      <div className="px-3 pb-3">
        <div className="flex items-center gap-1 flex-wrap">
          <Music size={10} className="text-text-3 mr-1 flex-shrink-0" />
          {song.notes.slice(0, 24).map((n, i) => (
            <span
              key={i}
              className={`text-[10px] mono px-1 py-0.5 rounded transition-colors ${
                i === currentNoteIdx
                  ? 'bg-accent/20 text-accent'
                  : n.note === 'rest'
                  ? 'text-text-3 opacity-40'
                  : 'text-text-2'
              }`}
            >
              {n.note === 'rest' ? '\u00b7' : n.note}
            </span>
          ))}
          {song.notes.length > 24 && (
            <span className="text-[9px] text-text-3">+{song.notes.length - 24}</span>
          )}
        </div>

        {/* Meta */}
        <div className="flex items-center gap-3 mt-2 text-[10px] text-text-3">
          <span className="capitalize">{song.wave}</span>
          <span>{song.tempo} BPM</span>
          <span>{song.notes.length} notes</span>
        </div>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
