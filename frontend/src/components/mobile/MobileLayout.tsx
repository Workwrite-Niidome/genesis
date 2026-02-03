import { useUIStore } from '../../stores/uiStore';
import MobileHeader from './MobileHeader';
import MobileTabBar from './MobileTabBar';
import MobileWorldView from './MobileWorldView';
import MobileRankingView from './MobileRankingView';
import MobileFeedView from './MobileFeedView';
import MobileArchiveView from './MobileArchiveView';
import MobileMoreView from './MobileMoreView';
import MobileSubView from './MobileSubView';
import MobileDetailSheet from './MobileDetailSheet';
import MobileDeploySheet from './MobileDeploySheet';

export default function MobileLayout() {
  const { mobileActiveTab, mobilePanelContent, setMobilePanelContent } = useUIStore();

  // If a sub-view is open (from More menu), show it fullscreen
  if (mobilePanelContent) {
    return (
      <MobileSubView
        contentKey={mobilePanelContent}
        onBack={() => setMobilePanelContent(null)}
      />
    );
  }

  return (
    <div className="mobile-layout">
      {/* Film grain */}
      <div className="noise-overlay" />

      {/* Fixed Header */}
      <header className="mobile-header-fixed">
        <MobileHeader />
      </header>

      {/* Main content area */}
      <main className="mobile-content">
        {mobileActiveTab === 'world' && <MobileWorldView />}
        {mobileActiveTab === 'ranking' && <MobileRankingView />}
        {mobileActiveTab === 'feed' && <MobileFeedView />}
        {mobileActiveTab === 'archive' && <MobileArchiveView />}
        {mobileActiveTab === 'more' && <MobileMoreView />}
      </main>

      {/* Fixed Tab Bar */}
      <nav className="mobile-tabbar-fixed">
        <MobileTabBar />
      </nav>

      {/* Mobile fullscreen sheets */}
      <MobileDetailSheet />
      <MobileDeploySheet />
    </div>
  );
}
