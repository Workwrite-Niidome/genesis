import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  Lightbulb,
  Palette,
  Eye,
  MessageSquare,
  Settings,
  Rocket,
  Shield,
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { useDeployStore } from '../../stores/deployStore';

interface MenuItem {
  id: string;
  icon: typeof Lightbulb;
  labelKey: string;
  color: string;
  route?: string;
}

const menuItems: MenuItem[] = [
  { id: 'concepts', icon: Lightbulb, labelKey: 'concepts', color: 'text-cyan' },
  { id: 'artifacts', icon: Palette, labelKey: 'artifacts', color: 'text-rose' },
  { id: 'god', icon: Eye, labelKey: 'god_console', color: 'text-accent' },
  { id: 'board', icon: MessageSquare, labelKey: 'board_title', color: 'text-green' },
  { id: 'deploy', icon: Rocket, labelKey: 'deploy_title', color: 'text-cyan' },
];

export default function MobileMoreView() {
  const { t } = useTranslation();
  const setMobilePanelContent = useUIStore((s) => s.setMobilePanelContent);
  const togglePanel = useDeployStore((s) => s.togglePanel);

  const handleItem = (id: string) => {
    if (id === 'deploy') {
      togglePanel();
      return;
    }
    setMobilePanelContent(id);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-4 py-3 border-b border-border">
        <span className="text-[13px] font-semibold text-text tracking-wide">{t('settings')}</span>
      </div>

      <div className="p-3 space-y-1">
        {menuItems.map(({ id, icon: Icon, labelKey, color }) => (
          <button
            key={id}
            onClick={() => handleItem(id)}
            className="w-full flex items-center gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] active:bg-white/[0.06] transition-colors touch-target"
          >
            <div className={`p-2 rounded-lg bg-white/[0.04] ${color}`}>
              <Icon size={16} />
            </div>
            <span className="text-[13px] text-text font-medium">{t(labelKey)}</span>
            <span className="ml-auto text-text-3 text-[12px]">&rsaquo;</span>
          </button>
        ))}

        {/* Admin link */}
        <Link
          to="/admin"
          className="w-full flex items-center gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] active:bg-white/[0.06] transition-colors touch-target"
        >
          <div className="p-2 rounded-lg bg-white/[0.04] text-orange">
            <Shield size={16} />
          </div>
          <span className="text-[13px] text-text font-medium">{t('admin')}</span>
          <span className="ml-auto text-text-3 text-[12px]">&rsaquo;</span>
        </Link>
      </div>
    </div>
  );
}
