import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Eye } from 'lucide-react';
import DraggablePanel from '../ui/DraggablePanel';

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

  return (
    <DraggablePanel
      title={t('god_observation')}
      icon={<Eye size={12} className="text-accent" />}
      visible={visible}
      onClose={onClose}
      defaultX={Math.round(window.innerWidth / 2 - 150)}
      defaultY={100}
      defaultWidth={320}
      defaultHeight={380}
      minWidth={260}
      minHeight={200}
    >
      <div className="p-2 space-y-1.5">
        {feed.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-text-3 text-[11px]">God has not yet spoken...</p>
          </div>
        ) : (
          feed.map((entry, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-xl bg-white/[0.02] border border-accent/10"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-medium text-accent uppercase tracking-wider">
                  {entry.role === 'god_observation'
                    ? 'Observation'
                    : entry.role === 'god_succession_trial'
                    ? 'Succession Trial'
                    : 'God'}
                </span>
                {entry.tick_number && (
                  <span className="text-[9px] mono text-text-3">T:{entry.tick_number}</span>
                )}
              </div>
              <p className="text-[11px] text-text-2 leading-relaxed line-clamp-4">
                {entry.content}
              </p>
            </div>
          ))
        )}
      </div>
    </DraggablePanel>
  );
}
