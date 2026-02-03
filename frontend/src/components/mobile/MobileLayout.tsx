import { useUIStore } from '../../stores/uiStore';
import MobileHeader from './MobileHeader';
import MobileTabBar from './MobileTabBar';
import MobileWorldView from './MobileWorldView';
import MobileRankingView from './MobileRankingView';
import MobileFeedView from './MobileFeedView';
import MobileArchiveView from './MobileArchiveView';
import MobileMoreView from './MobileMoreView';
import MobileSubView from './MobileSubView';
import DetailModal from '../observer/DetailModal';
import DeployPanel from '../observer/DeployPanel';

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
    <div className="h-screen w-screen bg-bg overflow-hidden">
      {/* Film grain */}
      <div className="noise-overlay" />

      {/* Fixed Header */}
      <div className="fixed top-0 left-0 right-0 z-50">
        <MobileHeader />
      </div>

      {/* Main content area with padding for fixed header/tabbar */}
      <main className="h-full overflow-auto pt-[52px] pb-[60px]">
        {mobileActiveTab === 'world' && <MobileWorldView />}
        {mobileActiveTab === 'ranking' && <MobileRankingView />}
        {mobileActiveTab === 'feed' && <MobileFeedView />}
        {mobileActiveTab === 'archive' && <MobileArchiveView />}
        {mobileActiveTab === 'more' && <MobileMoreView />}
      </main>

      {/* Fixed Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-50">
        <MobileTabBar />
      </div>

      {/* Modals */}
      <DetailModal />
      <DeployPanel />
    </div>
  );
}
