import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Eye, X } from 'lucide-react';
import { api } from '../../services/api';

interface GodFeedEntry {
  role: string;
  content: string;
  timestamp: string;
  tick_number?: number;
}

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function GodFeed({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [feed, setFeed] = useState<GodFeedEntry[]>([]);

  useEffect(() => {
    if (!visible) return;
    const load = () => {
      fetch('/api/history/god-feed?limit=20')
        .then((res) => res.json())
        .then((data) => {
          setFeed((data.feed || []).reverse());
        })
        .catch(() => setFeed([]));
    };
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="absolute top-20 left-[calc(50%-140px)] z-40 w-72 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04]">
          <div className="flex items-center gap-2">
            <Eye size={12} className="text-accent" />
            <span className="text-[10px] font-medium text-text uppercase tracking-wider">
              {t('god_observation')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/[0.08] text-text-3 hover:text-text transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        <div className="p-2 space-y-1.5 max-h-64 overflow-y-auto">
          {feed.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-text-3 text-[10px]">God has not yet spoken...</p>
            </div>
          ) : (
            feed.map((entry, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-xl bg-white/[0.02] border border-accent/10"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] font-medium text-accent uppercase tracking-wider">
                    {entry.role === 'god_observation'
                      ? 'Observation'
                      : entry.role === 'god_succession_trial'
                      ? 'Succession Trial'
                      : 'God'}
                  </span>
                  {entry.tick_number && (
                    <span className="text-[8px] mono text-text-3">T:{entry.tick_number}</span>
                  )}
                </div>
                <p className="text-[10px] text-text-2 leading-relaxed line-clamp-4">
                  {entry.content}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
