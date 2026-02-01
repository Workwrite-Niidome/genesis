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
            className="p-1 rounded-lg hover:bg-surface-3 text-text-3 hover:text-text-2 transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        {/* Identity card */}
        <div className="flex items-center gap-3 p-3.5 rounded-xl bg-surface-2 border border-border hover-lift">
          <div
            className="w-9 h-9 rounded-lg"
            style={{
              backgroundColor: selectedAI.appearance?.primaryColor || '#7c5bf5',
              boxShadow: `0 0 24px ${selectedAI.appearance?.primaryColor || '#7c5bf5'}25`,
            }}
          />
          <div className="flex-1 min-w-0">
            <div className="text-[11px] mono text-text-2 truncate">
              {selectedAI.id.slice(0, 12)}
            </div>
            <div className="flex items-center gap-2 mt-1">
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
          <pre className="text-text-3 bg-surface-2 rounded-lg p-2.5 overflow-x-auto text-[10px] mono border border-border leading-relaxed">
            {JSON.stringify(selectedAI.state, null, 2)}
          </pre>
        </Field>

        {/* Memories */}
        <Field label={`${t('memories')} (${selectedMemories.length})`}>
          <div className="space-y-2 max-h-52 overflow-y-auto">
            {selectedMemories.map((m) => (
              <div key={m.id} className="p-2.5 rounded-lg bg-surface-2 border border-border hover-lift">
                <div className="flex justify-between text-[10px] text-text-3 mb-1">
                  <span className="mono">{m.memory_type}</span>
                  <span className="text-accent mono">{m.importance.toFixed(1)}</span>
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
        <div className="text-center py-14">
          <div className="relative w-12 h-12 mx-auto mb-5">
            <div className="absolute inset-0 rounded-full border border-border pulse-ring" />
            <div className="absolute inset-3 rounded-full border border-border/50" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-text-3" />
            </div>
          </div>
          <p className="text-text-3 text-[11px]">{t('no_ais')}</p>
        </div>
      ) : (
        <div className="space-y-1">
          {ais.map((ai) => (
            <button
              key={ai.id}
              onClick={() => useAIStore.getState().selectAI(ai.id)}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl
                         hover:bg-surface-2 transition-all duration-150 text-left group"
            >
              <div
                className="w-5 h-5 rounded-md flex-shrink-0 transition-shadow duration-200
                           group-hover:shadow-[0_0_12px_rgba(124,91,245,0.25)]"
                style={{ backgroundColor: ai.appearance?.primaryColor || '#7c5bf5' }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[11px] mono text-text-2 truncate group-hover:text-text transition-colors">
                  {ai.id.slice(0, 16)}
                </div>
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
