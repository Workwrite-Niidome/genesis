/**
 * MobileV3TabBar — Bottom tab navigation for mobile GENESIS v3.
 *
 * 5 tabs: World | Entities | Events | Chat | More
 * 48px+ touch targets, fixed bottom with safe-area.
 */
import { Globe, Users, Radio, Crown, MoreHorizontal } from 'lucide-react';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import type { MobileV3Tab } from '../../../stores/mobileStoreV3';

const tabs: { id: MobileV3Tab; icon: typeof Globe; label: string }[] = [
  { id: 'world', icon: Globe, label: 'World' },
  { id: 'entities', icon: Users, label: 'Entities' },
  { id: 'events', icon: Radio, label: 'Events' },
  { id: 'chat', icon: Crown, label: 'Chat' },
  { id: 'more', icon: MoreHorizontal, label: 'More' },
];

export function MobileV3TabBar() {
  const activeTab = useMobileStoreV3(s => s.activeTab);
  const setActiveTab = useMobileStoreV3(s => s.setActiveTab);
  const setGodChatOpen = useMobileStoreV3(s => s.setGodChatOpen);
  const setTimelineOpen = useMobileStoreV3(s => s.setTimelineOpen);

  const handleTabPress = (tab: MobileV3Tab) => {
    if (tab === 'chat') {
      setGodChatOpen(true);
      return;
    }
    if (tab === 'more') {
      setTimelineOpen(true);
      return;
    }
    setActiveTab(tab);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-stretch bg-black/90 backdrop-blur-xl border-t border-white/10 safe-bottom">
      {tabs.map(({ id, icon: Icon, label }) => {
        const isActive = activeTab === id && id !== 'chat' && id !== 'more';
        return (
          <button
            key={id}
            onClick={() => handleTabPress(id)}
            className={`flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors ${
              isActive ? 'text-purple-400' : 'text-white/40'
            }`}
            style={{ minHeight: 48 }}
          >
            <Icon size={18} strokeWidth={isActive ? 2 : 1.5} />
            <span className={`text-[10px] tracking-wide ${isActive ? 'font-medium' : ''}`}>
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
