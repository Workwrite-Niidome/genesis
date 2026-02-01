import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Radio, Loader2 } from 'lucide-react';
import { FeedContent } from '../observer/ObserverFeed';

type SubTab = 'thoughts' | 'events';

export default function MobileFeedView() {
  const { t } = useTranslation();
  const [subTab, setSubTab] = useState<SubTab>('thoughts');

  return (
    <div className="h-full flex flex-col">
      {/* Sub-tab bar */}
      <div className="flex border-b border-border flex-shrink-0">
        <button
          onClick={() => setSubTab('thoughts')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-[11px] font-medium uppercase tracking-wider transition-colors ${
            subTab === 'thoughts'
              ? 'text-accent border-b-2 border-accent bg-white/[0.02]'
              : 'text-text-3'
          }`}
        >
          <Brain size={13} />
          {t('thoughts')}
        </button>
        <button
          onClick={() => setSubTab('events')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-[11px] font-medium uppercase tracking-wider transition-colors ${
            subTab === 'events'
              ? 'text-cyan border-b-2 border-cyan bg-white/[0.02]'
              : 'text-text-3'
          }`}
        >
          <Radio size={13} />
          {t('live_events')}
        </button>
      </div>

      {/* Full-screen feed content */}
      <div className="flex-1 overflow-y-auto">
        <FeedContent tab={subTab} fullScreen />
      </div>
    </div>
  );
}
