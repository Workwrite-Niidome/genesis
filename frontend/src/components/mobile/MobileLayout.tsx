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
    <div className="h-screen w-screen flex flex-col bg-bg overflow-hidden">
      {/* Film grain */}
      <div className="noise-overlay" />

      <MobileHeader />

      {/* Main content area */}
      <main className="flex-1 overflow-hidden relative">
        {mobileActiveTab === 'world' && <MobileWorldView />}
        {mobileActiveTab === 'ranking' && <MobileRankingView />}
        {mobileActiveTab === 'feed' && <MobileFeedView />}
        {mobileActiveTab === 'archive' && <MobileArchiveView />}
        {mobileActiveTab === 'more' && <MobileMoreView />}
      </main>

      <MobileTabBar />

      {/* Modals */}
      <DetailModal />
      <DeployPanel />
    </div>
  );
}
