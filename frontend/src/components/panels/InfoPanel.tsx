import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
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
          <h3 className="text-xs font-medium text-text">{t('ai_detail')}</h3>
          <button
            onClick={() => useAIStore.getState().selectAI(null)}
            className="p-0.5 rounded hover:bg-surface-3 text-text-3 hover:text-text-2 transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        {/* Identity card */}
        <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-2 border border-border">
          <div
            className="w-8 h-8 rounded-lg"
            style={{
              backgroundColor: selectedAI.appearance?.primaryColor || '#7c5bf5',
              boxShadow: `0 0 20px ${selectedAI.appearance?.primaryColor || '#7c5bf5'}20`,
            }}
          />
          <div className="flex-1 min-w-0">
            <div className="text-[11px] mono text-text-2 truncate">
              {selectedAI.id.slice(0, 12)}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-text-3">{selectedAI.creator_type}</span>
              <span className={`badge text-[9px] ${selectedAI.is_alive ? 'bg-green-dim text-green' : 'bg-orange-dim text-orange'}`}>
                {selectedAI.is_alive ? t('alive') : t('dead')}
              </span>
            </div>
          </div>
        </div>

        {/* Position */}
        <Field label={t('position')}>
          <span className="mono text-[11px] text-text-2">
            ({selectedAI.position_x.toFixed(1)}, {selectedAI.position_y.toFixed(1)})
          </span>
        </Field>

        {/* State */}
        <Field label="State">
          <pre className="text-text-3 bg-surface-2 rounded-md p-2 overflow-x-auto text-[10px] mono border border-border">
            {JSON.stringify(selectedAI.state, null, 2)}
          </pre>
        </Field>

        {/* Memories */}
        <Field label={`${t('memories')} (${selectedMemories.length})`}>
          <div className="space-y-1.5 max-h-52 overflow-y-auto">
            {selectedMemories.map((m) => (
              <div key={m.id} className="p-2 rounded-md bg-surface-2 border border-border">
                <div className="flex justify-between text-[10px] text-text-3 mb-1">
                  <span className="mono">{m.memory_type}</span>
                  <span className="text-accent">{m.importance.toFixed(1)}</span>
                </div>
                <div className="text-[11px] text-text-2 leading-relaxed">{m.content}</div>
              </div>
            ))}
          </div>
        </Field>
      </div>
    );
  }

  return (
    <div className="space-y-3 fade-in">
      <h3 className="text-xs font-medium text-text">{t('info_panel')}</h3>

      {aiCount === 0 ? (
        <div className="text-center py-12">
          <div className="w-10 h-10 rounded-full border border-border mx-auto mb-4 flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-text-3" />
          </div>
          <p className="text-text-3 text-[11px]">{t('no_ais')}</p>
        </div>
      ) : (
        <div className="space-y-1">
          {ais.map((ai) => (
            <button
              key={ai.id}
              onClick={() => useAIStore.getState().selectAI(ai.id)}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-surface-2 transition-colors duration-150 text-left group"
            >
              <div
                className="w-5 h-5 rounded-md flex-shrink-0 transition-shadow group-hover:shadow-[0_0_12px_rgba(124,91,245,0.2)]"
                style={{ backgroundColor: ai.appearance?.primaryColor || '#7c5bf5' }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[11px] mono text-text-2 truncate">{ai.id.slice(0, 16)}</div>
              </div>
              <div className="text-[10px] mono text-text-3">
                {ai.position_x.toFixed(0)},{ai.position_y.toFixed(0)}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="text-[10px] font-medium text-text-3 uppercase tracking-wider">{label}</div>
      {children}
    </div>
  );
}
