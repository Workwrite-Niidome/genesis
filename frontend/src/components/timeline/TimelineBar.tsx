import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Pause, FastForward, Rewind, Radio, Search } from 'lucide-react';
import { useWorldStore } from '../../stores/worldStore';
import { useUIStore } from '../../stores/uiStore';
import { api } from '../../services/api';
import { getEventConfig } from './EventCard';

const SPEEDS = [0.1, 0.5, 1, 2, 10, 100];

interface Marker {
  id: number;
  tick: number;
  event_type: string;
  action: string;
  importance: number;
}

export default function TimelineBar() {
  const { t } = useTranslation();
  const {
    tickNumber, maxTick, seekTick, isPaused, timeSpeed,
    setPaused, setTimeSpeed, seekToTick,
  } = useWorldStore();
  const { toggleArchive } = useUIStore();

  const [markers, setMarkers] = useState<Marker[]>([]);
  const [hoveredMarker, setHoveredMarker] = useState<Marker | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragTick, setDragTick] = useState<number | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  const speedIndex = SPEEDS.indexOf(timeSpeed);
  const isLive = seekTick === null;
  const displayTick = seekTick ?? tickNumber;
  const effectiveMax = Math.max(maxTick, tickNumber, 1);

  const slower = () => {
    const idx = Math.max(0, speedIndex - 1);
    setTimeSpeed(SPEEDS[idx]);
  };

  const faster = () => {
    const idx = Math.min(SPEEDS.length - 1, speedIndex + 1);
    setTimeSpeed(SPEEDS[idx]);
  };

  // Fetch markers for the timeline
  useEffect(() => {
    if (effectiveMax <= 0) return;
    const fetchMarkers = async () => {
      try {
        const data = await api.historyV3.getMarkers(0, effectiveMax, 0.5);
        setMarkers(data.markers || []);
      } catch {
        // Silently fail - markers are non-critical
      }
    };
    fetchMarkers();
    const interval = setInterval(fetchMarkers, 15000);
    return () => clearInterval(interval);
  }, [effectiveMax]);

  // Calculate position from tick
  const tickToPercent = useCallback(
    (tick: number) => Math.min(100, Math.max(0, (tick / effectiveMax) * 100)),
    [effectiveMax],
  );

  // Calculate tick from mouse position
  const posToTick = useCallback(
    (clientX: number) => {
      if (!trackRef.current) return 0;
      const rect = trackRef.current.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      return Math.round(ratio * effectiveMax);
    },
    [effectiveMax],
  );

  // Handle seek slider interaction
  const handleTrackMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const tick = posToTick(e.clientX);
      setIsDragging(true);
      setDragTick(tick);
      seekToTick(tick);
      // Pause when seeking
      if (!isPaused) setPaused(true);
    },
    [posToTick, seekToTick, isPaused, setPaused],
  );

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => {
      const tick = posToTick(e.clientX);
      setDragTick(tick);
      seekToTick(tick);
    };
    const onUp = () => {
      setIsDragging(false);
      setDragTick(null);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isDragging, posToTick, seekToTick]);

  const goLive = () => {
    seekToTick(null);
  };

  // Limit markers to avoid rendering too many
  const visibleMarkers = useMemo(() => {
    if (markers.length <= 100) return markers;
    // Sample down to ~100 markers for performance
    const step = Math.ceil(markers.length / 100);
    return markers.filter((_, i) => i % step === 0);
  }, [markers]);

  const progress = tickToPercent(dragTick ?? displayTick);

  return (
    <div className="h-10 flex items-center gap-3 px-4 bg-surface/90 backdrop-blur-xl border-t border-border z-50 relative">
      {/* Subtle top glow line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/15 to-transparent" />

      {/* Playback controls */}
      <div className="flex items-center gap-0.5">
        <button
          onClick={slower}
          className="p-1 rounded-md hover:bg-surface-3 text-text-3 hover:text-text-2 transition-colors"
          title="Slower"
        >
          <Rewind size={12} />
        </button>

        <button
          onClick={() => setPaused(!isPaused)}
          className="p-1.5 rounded-lg hover:bg-surface-3 text-text transition-colors"
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
        </button>

        <button
          onClick={faster}
          className="p-1 rounded-md hover:bg-surface-3 text-text-3 hover:text-text-2 transition-colors"
          title="Faster"
        >
          <FastForward size={12} />
        </button>
      </div>

      {/* Speed indicator */}
      <div className="text-[11px] mono text-text-3 min-w-[60px]">
        <span className="text-cyan">x{timeSpeed}</span>
        {isPaused && <span className="ml-1.5 text-orange">{t('paused')}</span>}
      </div>

      {/* Timeline track with seek + markers */}
      <div
        ref={trackRef}
        className="flex-1 h-5 relative mx-2 group cursor-pointer"
        onMouseDown={handleTrackMouseDown}
      >
        {/* Track background */}
        <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-[3px] bg-surface-3 rounded-full overflow-visible">
          {/* Progress fill */}
          <div
            className="h-full bg-gradient-to-r from-accent/40 to-cyan/40 rounded-full transition-all"
            style={{
              width: `${progress}%`,
              transitionDuration: isDragging ? '0ms' : '500ms',
            }}
          />
        </div>

        {/* Event markers */}
        {visibleMarkers.map((marker) => {
          const pos = tickToPercent(marker.tick);
          const config = getEventConfig(marker.event_type);
          return (
            <div
              key={marker.id}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-1.5 h-3 rounded-sm opacity-50 hover:opacity-100 hover:scale-y-150 transition-all cursor-pointer z-10"
              style={{
                left: `${pos}%`,
                backgroundColor: config.hex,
              }}
              onMouseEnter={(e) => {
                setHoveredMarker(marker);
                setTooltipPos({ x: e.clientX, y: e.clientY });
              }}
              onMouseLeave={() => setHoveredMarker(null)}
              onClick={(e) => {
                e.stopPropagation();
                seekToTick(marker.tick);
                if (!isPaused) setPaused(true);
              }}
            />
          );
        })}

        {/* Seek head */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-cyan transition-all
                     shadow-[0_0_6px_rgba(88,213,240,0.4)] group-hover:shadow-[0_0_12px_rgba(88,213,240,0.6)]
                     group-hover:scale-150 z-20"
          style={{
            left: `${progress}%`,
            transitionDuration: isDragging ? '0ms' : '500ms',
          }}
        />

        {/* Marker tooltip */}
        {hoveredMarker && (
          <div
            className="fixed z-[200] px-3 py-2 rounded-lg bg-surface border border-border shadow-xl pointer-events-none"
            style={{
              left: tooltipPos.x + 12,
              top: tooltipPos.y - 50,
              maxWidth: 240,
            }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: getEventConfig(hoveredMarker.event_type).hex }}
              />
              <span className={`text-[10px] font-semibold uppercase tracking-wider ${getEventConfig(hoveredMarker.event_type).color}`}>
                {hoveredMarker.event_type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-[11px] text-text truncate">{hoveredMarker.action}</p>
            <p className="text-[10px] mono text-text-3 mt-0.5">Tick {hoveredMarker.tick}</p>
          </div>
        )}
      </div>

      {/* Tick counter / seek display */}
      <div className="flex items-center gap-2 min-w-[120px] justify-end">
        {!isLive && (
          <button
            onClick={goLive}
            className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold
              bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
          >
            <Radio size={10} />
            LIVE
          </button>
        )}
        <div className="text-[11px] mono text-text-3 whitespace-nowrap">
          {isLive ? (
            <>
              {t('tick')} <span className="text-cyan">{tickNumber.toLocaleString()}</span>
            </>
          ) : (
            <>
              <span className="text-amber-400">{displayTick.toLocaleString()}</span>
              <span className="text-text-3 opacity-50"> / {effectiveMax.toLocaleString()}</span>
            </>
          )}
        </div>
        {/* Archive / search shortcut */}
        <button
          onClick={toggleArchive}
          className="p-1 rounded-md hover:bg-surface-3 text-text-3 hover:text-text transition-colors"
          title="Open Archive"
        >
          <Search size={12} />
        </button>
      </div>
    </div>
  );
}
