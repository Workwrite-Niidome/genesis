import { useTranslation } from 'react-i18next';
import { Globe, TrendingUp, Radio, BookOpen, MoreHorizontal } from 'lucide-react';
import { useUIStore, type MobileTab } from '../../stores/uiStore';
import { useSagaStore } from '../../stores/sagaStore';

const tabs: { id: MobileTab; icon: typeof Globe; labelKey: string }[] = [
  { id: 'world', icon: Globe, labelKey: 'mobile_tab_world' },
  { id: 'ranking', icon: TrendingUp, labelKey: 'mobile_tab_ranking' },
  { id: 'feed', icon: Radio, labelKey: 'mobile_tab_feed' },
  { id: 'archive', icon: BookOpen, labelKey: 'mobile_tab_archive' },
  { id: 'more', icon: MoreHorizontal, labelKey: 'mobile_tab_more' },
];

export default function MobileTabBar() {
  const { t } = useTranslation();
  const { mobileActiveTab, setMobileTab } = useUIStore();
  const { hasNewChapter } = useSagaStore();

  return (
    <nav className="flex items-stretch bg-surface/95 backdrop-blur-xl border-t border-border safe-bottom">
      {tabs.map(({ id, icon: Icon, labelKey }) => {
        const active = mobileActiveTab === id;
        return (
          <button
            key={id}
            onClick={() => setMobileTab(id)}
            className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[48px] transition-colors touch-target ${
              active ? 'text-accent' : 'text-text-3'
            }`}
          >
            <div className="relative">
              <Icon size={18} strokeWidth={active ? 2 : 1.5} />
              {id === 'archive' && hasNewChapter && (
                <span
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full animate-pulse"
                  style={{ backgroundColor: '#d4a574' }}
                />
              )}
            </div>
            <span className={`text-[9px] tracking-wide ${active ? 'font-medium' : ''}`}>
              {t(labelKey)}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
