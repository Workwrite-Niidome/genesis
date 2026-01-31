import { useTranslation } from 'react-i18next';
import { useAIStore } from '../../stores/aiStore';
import { useWorldStore } from '../../stores/worldStore';

export default function InfoPanel() {
  const { t } = useTranslation();
  const { selectedAI, selectedMemories, ais } = useAIStore();
  const { aiCount } = useWorldStore();

  if (selectedAI) {
    return (
      <div className="space-y-4 fade-in">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-glow-cyan">{t('ai_detail')}</h3>
          <button
            onClick={() => useAIStore.getState().selectAI(null)}
            className="text-xs text-text-dim hover:text-text-secondary"
          >
            ✕
          </button>
        </div>

        {/* AI visual */}
        <div className="flex items-center gap-3 p-3 rounded-lg bg-void-lighter">
          <div
            className="w-10 h-10 rounded-lg"
            style={{
              backgroundColor: selectedAI.appearance?.primaryColor || '#4fc3f7',
              boxShadow: `0 0 15px ${selectedAI.appearance?.primaryColor || '#4fc3f7'}40`,
            }}
          />
          <div>
            <div className="text-xs font-mono text-text-secondary">
              {selectedAI.id.slice(0, 8)}...
            </div>
            <div className="text-xs text-text-dim">
              {selectedAI.creator_type} · {selectedAI.is_alive ? t('alive') : t('dead')}
            </div>
          </div>
        </div>

        {/* Position */}
        <div className="text-xs space-y-1">
          <div className="text-text-dim">{t('position')}</div>
          <div className="font-mono text-text-secondary">
            ({selectedAI.position_x.toFixed(1)}, {selectedAI.position_y.toFixed(1)})
          </div>
        </div>

        {/* State */}
        <div className="text-xs space-y-1">
          <div className="text-text-dim">State</div>
          <pre className="text-text-secondary bg-void-lighter rounded p-2 overflow-x-auto text-[10px]">
            {JSON.stringify(selectedAI.state, null, 2)}
          </pre>
        </div>

        {/* Memories */}
        <div className="text-xs space-y-1">
          <div className="text-text-dim">{t('memories')} ({selectedMemories.length})</div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {selectedMemories.map((m) => (
              <div key={m.id} className="p-2 rounded bg-void-lighter">
                <div className="flex justify-between text-text-dim mb-0.5">
                  <span>{m.memory_type}</span>
                  <span>★ {m.importance.toFixed(1)}</span>
                </div>
                <div className="text-text-secondary">{m.content}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 fade-in">
      <h3 className="text-sm font-medium text-glow-cyan">{t('info_panel')}</h3>

      {aiCount === 0 ? (
        <div className="text-center py-8">
          <div className="text-3xl mb-3 pulse-slow">∅</div>
          <p className="text-text-secondary text-xs">{t('no_ais')}</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {ais.map((ai) => (
            <button
              key={ai.id}
              onClick={() => useAIStore.getState().selectAI(ai.id)}
              className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-panel-hover transition-colors text-left"
            >
              <div
                className="w-6 h-6 rounded"
                style={{
                  backgroundColor: ai.appearance?.primaryColor || '#4fc3f7',
                  boxShadow: `0 0 8px ${ai.appearance?.primaryColor || '#4fc3f7'}30`,
                }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-mono text-text-secondary truncate">
                  {ai.id.slice(0, 12)}...
                </div>
                <div className="text-[10px] text-text-dim">
                  ({ai.position_x.toFixed(0)}, {ai.position_y.toFixed(0)})
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
