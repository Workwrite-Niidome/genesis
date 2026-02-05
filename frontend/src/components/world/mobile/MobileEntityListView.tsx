/**
 * MobileEntityListView — Full-height entity list for mobile (Entities tab).
 *
 * Full-width search input (44px height, 14px text).
 * Entity rows: 48px+ height, 14px name, 12px action.
 * Tap entity → selectEntity + switch to World tab + open entity sheet.
 */
import { useState, useMemo, useCallback } from 'react';
import { Search, ArrowUpDown, Skull } from 'lucide-react';
import { useWorldStoreV3 } from '../../../stores/worldStoreV3';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import type { EntityV3 } from '../../../types/v3';

type SortKey = 'name' | 'mode';

const MODE_ORDER: Record<string, number> = {
  rampage: 0,
  desperate: 1,
  normal: 2,
};

function modeDotClass(mode: string): string {
  switch (mode) {
    case 'rampage': return 'bg-red-500';
    case 'desperate': return 'bg-amber-500';
    default: return 'bg-emerald-500';
  }
}

export function MobileEntityListView() {
  const entities = useWorldStoreV3(s => s.entities);
  const selectEntity = useWorldStoreV3(s => s.selectEntity);
  const selectedEntityId = useWorldStoreV3(s => s.selectedEntityId);
  const setActiveTab = useMobileStoreV3(s => s.setActiveTab);

  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('name');

  const aliveCount = useMemo(() => {
    let count = 0;
    for (const e of entities.values()) {
      if (e.isAlive) count++;
    }
    return count;
  }, [entities]);

  const sortedEntities = useMemo(() => {
    const list: EntityV3[] = [];
    for (const e of entities.values()) {
      if (query && !e.name.toLowerCase().includes(query.toLowerCase())) continue;
      list.push(e);
    }

    list.sort((a, b) => {
      // Alive entities first
      if (a.isAlive !== b.isAlive) return a.isAlive ? -1 : 1;
      if (sortKey === 'name') return a.name.localeCompare(b.name);
      if (sortKey === 'mode') {
        const ma = MODE_ORDER[a.state.behaviorMode] ?? 2;
        const mb = MODE_ORDER[b.state.behaviorMode] ?? 2;
        return ma - mb || a.name.localeCompare(b.name);
      }
      return 0;
    });

    return list;
  }, [entities, query, sortKey]);

  const cycleSort = useCallback(() => {
    setSortKey(prev => prev === 'name' ? 'mode' : 'name');
  }, []);

  const handleEntityTap = useCallback((entityId: string) => {
    selectEntity(entityId);
    setActiveTab('world');
  }, [selectEntity, setActiveTab]);

  return (
    <div className="flex flex-col h-full">
      {/* Search + sort */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.06] flex-shrink-0">
        <div className="flex items-center gap-2 flex-1 bg-white/[0.06] rounded-lg px-3" style={{ height: 44 }}>
          <Search size={14} className="text-white/30 flex-shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search entities..."
            className="bg-transparent text-[14px] text-white/80 placeholder-white/25 outline-none flex-1 min-w-0"
          />
        </div>
        <button
          onClick={cycleSort}
          className="flex items-center gap-1.5 px-3 rounded-lg bg-white/[0.06] text-white/40 text-[12px] font-mono flex-shrink-0"
          style={{ height: 44 }}
        >
          <ArrowUpDown size={12} />
          {sortKey === 'name' ? 'Name' : 'Mode'}
        </button>
      </div>

      {/* Count */}
      <div className="px-4 py-1.5 text-[12px] font-mono text-white/30 flex-shrink-0">
        {sortedEntities.length} entities ({aliveCount} alive)
      </div>

      {/* Entity rows */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {sortedEntities.length === 0 ? (
          <div className="text-center py-12 text-white/25 text-[13px]">
            {query ? 'No matches' : 'No entities found'}
          </div>
        ) : (
          sortedEntities.map((entity) => {
            const isSelected = entity.id === selectedEntityId;
            const mode = entity.state.behaviorMode;
            const dead = !entity.isAlive;

            return (
              <button
                key={entity.id}
                onClick={() => handleEntityTap(entity.id)}
                className={`w-full flex items-center gap-3 px-4 text-left transition-colors ${
                  isSelected
                    ? 'bg-purple-500/15 border-l-2 border-purple-400'
                    : 'hover:bg-white/[0.04] border-l-2 border-transparent'
                } ${dead ? 'opacity-50' : ''}`}
                style={{ minHeight: 48 }}
              >
                {/* Mode dot / skull */}
                {dead ? (
                  <Skull size={12} className="text-gray-500 flex-shrink-0" />
                ) : (
                  <div
                    className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${modeDotClass(mode)} ${
                      mode === 'rampage' ? 'animate-pulse' : ''
                    }`}
                  />
                )}

                {/* Name + action */}
                <div className="flex-1 min-w-0">
                  <div
                    className={`text-[14px] font-mono truncate ${
                      isSelected ? 'text-purple-300' : 'text-white/70'
                    }`}
                  >
                    {entity.name}
                  </div>
                  {dead ? (
                    <div className="text-[12px] text-gray-500 truncate">
                      deceased
                    </div>
                  ) : entity.state.currentAction ? (
                    <div className="text-[12px] text-white/30 truncate">
                      {entity.state.currentAction}
                    </div>
                  ) : null}
                </div>

                {/* Energy indicator */}
                <span className="text-[12px] font-mono text-white/25 flex-shrink-0">
                  {dead ? 'DEAD' : `${Math.round(entity.state.energy * 100)}%`}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
