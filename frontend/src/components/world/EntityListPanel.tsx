/**
 * EntityListPanel — Toggleable scrollable entity list for GENESIS v3 observer view.
 *
 * Shows all alive entities with name, behavior mode indicator, current action,
 * and optional distance from camera.  Supports search/filter and sorting.
 * Uses glass-morphism styling consistent with the project theme.
 */
import { useState, useMemo, useCallback } from 'react';
import { Users, Search, ChevronLeft, ArrowUpDown } from 'lucide-react';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import type { EntityV3 } from '../../types/v3';

// ── Sort options ─────────────────────────────────────────────
type SortKey = 'name' | 'mode' | 'distance';

const SORT_LABELS: Record<SortKey, string> = {
  name: 'Name',
  mode: 'Mode',
  distance: 'Dist',
};

const MODE_ORDER: Record<string, number> = {
  rampage: 0,
  desperate: 1,
  normal: 2,
};

// ── Mode dot colors ──────────────────────────────────────────
function modeDotClass(mode: string): string {
  switch (mode) {
    case 'rampage':
      return 'bg-red-500';
    case 'desperate':
      return 'bg-amber-500';
    default:
      return 'bg-emerald-500';
  }
}

interface EntityListPanelProps {
  /** Current camera position for distance calculation (optional). */
  cameraPosition?: { x: number; y: number; z: number } | null;
}

export function EntityListPanel({ cameraPosition }: EntityListPanelProps) {
  const entities = useWorldStoreV3((s) => s.entities);
  const selectEntity = useWorldStoreV3((s) => s.selectEntity);
  const selectedEntityId = useWorldStoreV3((s) => s.selectedEntityId);

  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('name');

  // ── Distance helper ────────────────────────────────────────
  const distanceTo = useCallback(
    (e: EntityV3): number | null => {
      if (!cameraPosition) return null;
      const dx = e.position.x - cameraPosition.x;
      const dy = e.position.y - cameraPosition.y;
      const dz = e.position.z - cameraPosition.z;
      return Math.sqrt(dx * dx + dy * dy + dz * dz);
    },
    [cameraPosition],
  );

  // ── Filter + sort alive entities ───────────────────────────
  const sortedEntities = useMemo(() => {
    const alive: EntityV3[] = [];
    for (const e of entities.values()) {
      if (!e.isAlive) continue;
      if (query && !e.name.toLowerCase().includes(query.toLowerCase())) continue;
      alive.push(e);
    }

    alive.sort((a, b) => {
      if (sortKey === 'name') return a.name.localeCompare(b.name);
      if (sortKey === 'mode') {
        const ma = MODE_ORDER[a.state.behaviorMode] ?? 2;
        const mb = MODE_ORDER[b.state.behaviorMode] ?? 2;
        return ma - mb || a.name.localeCompare(b.name);
      }
      if (sortKey === 'distance') {
        const da = distanceTo(a) ?? Infinity;
        const db = distanceTo(b) ?? Infinity;
        return da - db;
      }
      return 0;
    });

    return alive;
  }, [entities, query, sortKey, distanceTo]);

  // ── Cycle sort key ─────────────────────────────────────────
  const cycleSort = useCallback(() => {
    setSortKey((prev) => {
      const keys: SortKey[] = ['name', 'mode', 'distance'];
      const idx = keys.indexOf(prev);
      return keys[(idx + 1) % keys.length];
    });
  }, []);

  const aliveCount = useMemo(() => {
    let count = 0;
    for (const e of entities.values()) {
      if (e.isAlive) count++;
    }
    return count;
  }, [entities]);

  // ── Collapsed: toggle button only ─────────────────────────
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="absolute top-14 left-[350px] z-10 flex items-center gap-1.5 px-2.5 py-1.5 bg-black/60 backdrop-blur-sm rounded-lg border border-white/10 text-white/70 text-xs font-mono hover:bg-white/10 transition-colors"
      >
        <Users size={12} className="text-purple-400" />
        <span>Entities ({aliveCount})</span>
      </button>
    );
  }

  // ── Expanded panel ─────────────────────────────────────────
  return (
    <div
      className="absolute top-14 left-[350px] z-10 flex flex-col bg-black/60 backdrop-blur-sm rounded-lg border border-white/10 overflow-hidden transition-all duration-200"
      style={{ width: 280, maxHeight: 'calc(100vh - 120px)' }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.06] shrink-0">
        <Users size={12} className="text-purple-400" />
        <span className="text-[10px] font-medium tracking-[0.12em] text-white/60 uppercase">
          Entities
        </span>
        <span className="text-[9px] font-mono text-white/30 ml-auto mr-2">
          {sortedEntities.length}/{aliveCount}
        </span>
        <button
          onClick={() => setIsOpen(false)}
          className="p-0.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors"
          title="Close entity list"
        >
          <ChevronLeft size={12} />
        </button>
      </div>

      {/* Search + sort row */}
      <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-white/[0.04] shrink-0">
        <div className="flex items-center gap-1.5 flex-1 bg-white/[0.04] rounded px-2 py-1">
          <Search size={10} className="text-white/30 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter..."
            className="bg-transparent text-[10px] text-white/80 placeholder-white/20 outline-none flex-1 min-w-0"
          />
        </div>
        <button
          onClick={cycleSort}
          className="flex items-center gap-1 px-1.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-white/40 text-[9px] font-mono transition-colors shrink-0"
          title={`Sort by: ${SORT_LABELS[sortKey]}`}
        >
          <ArrowUpDown size={9} />
          {SORT_LABELS[sortKey]}
        </button>
      </div>

      {/* Entity rows */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {sortedEntities.length === 0 ? (
          <div className="text-center py-6 text-white/25 text-[10px]">
            {query ? 'No matches' : 'No alive entities'}
          </div>
        ) : (
          sortedEntities.map((entity) => {
            const isSelected = entity.id === selectedEntityId;
            const dist = distanceTo(entity);
            const mode = entity.state.behaviorMode;

            return (
              <button
                key={entity.id}
                onClick={() => selectEntity(entity.id)}
                className={`w-full flex items-center gap-2 px-3 py-1.5 text-left transition-colors ${
                  isSelected
                    ? 'bg-purple-500/15 border-l-2 border-purple-400'
                    : 'hover:bg-white/[0.04] border-l-2 border-transparent'
                }`}
              >
                {/* Mode dot */}
                <div
                  className={`w-2 h-2 rounded-full shrink-0 ${modeDotClass(mode)} ${
                    mode === 'rampage' ? 'animate-pulse' : ''
                  }`}
                />

                {/* Name + action */}
                <div className="flex-1 min-w-0">
                  <div
                    className={`text-[11px] font-mono truncate ${
                      isSelected ? 'text-purple-300' : 'text-white/70'
                    }`}
                  >
                    {entity.name}
                  </div>
                  {entity.state.currentAction && (
                    <div className="text-[9px] text-white/30 truncate">
                      {entity.state.currentAction}
                    </div>
                  )}
                </div>

                {/* Distance */}
                {dist !== null && (
                  <span className="text-[8px] font-mono text-white/20 shrink-0">
                    {dist < 100 ? dist.toFixed(0) : '99+'}m
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
