/**
 * MobileWorldViewV3 — Mobile orchestrator component for GENESIS v3.
 *
 * Uses useWorldSceneV3 hook for 3D scene (identical to desktop).
 * Renders canvas (full viewport) + all mobile UI components.
 * Conditional rendering based on active tab and overlay state.
 */
import { useEffect } from 'react';
import { useWorldSceneV3 } from '../../../hooks/useWorldSceneV3';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import { MobileV3TopBar } from './MobileV3TopBar';
import { MobileV3TabBar } from './MobileV3TabBar';
import { MobileEntityDetailSheet } from './MobileEntityDetailSheet';
import { MobileEntityListView } from './MobileEntityListView';
import { MobileEventFeedView } from './MobileEventFeedView';
import { MobileBuildSheet } from './MobileBuildSheet';
import { MobileGodChatOverlay } from './MobileGodChatOverlay';
import { MobileTimelineOverlay } from './MobileTimelineOverlay';
import { MiniMap } from '../MiniMap';
import { GodSuccessionOverlay } from '../GodSuccessionOverlay';

export function MobileWorldViewV3() {
  const scene = useWorldSceneV3();
  const activeTab = useMobileStoreV3(s => s.activeTab);
  const miniMapVisible = useMobileStoreV3(s => s.miniMapVisible);
  const buildSheetState = useMobileStoreV3(s => s.buildSheetState);
  const setBuildSheetState = useMobileStoreV3(s => s.setBuildSheetState);

  // Sync build mode with build sheet
  useEffect(() => {
    if (scene.buildActive && buildSheetState === 'closed') {
      setBuildSheetState('half');
    } else if (!scene.buildActive && buildSheetState !== 'closed') {
      setBuildSheetState('closed');
    }
  }, [scene.buildActive, buildSheetState, setBuildSheetState]);

  const handleToggleBuild = () => {
    if (scene.buildActive) {
      scene.closeBuildMode();
    } else {
      scene.openBuildMode();
    }
  };

  return (
    <div className="relative w-full h-full bg-[#0a0a0f] overflow-hidden">
      {/* 3D Canvas — always full viewport, behind everything */}
      <canvas
        ref={scene.canvasRef}
        className="w-full h-full block"
        style={{ touchAction: 'none' }}
      />

      {/* Floating labels container */}
      <div
        ref={scene.labelContainerRef}
        className="absolute inset-0 pointer-events-none overflow-hidden"
      />

      {/* Top bar */}
      <MobileV3TopBar
        tickNumber={scene.tickNumber}
        buildActive={scene.buildActive}
        cameraMode={scene.cameraMode}
        onToggleBuild={handleToggleBuild}
        onCameraMode={scene.handleCameraMode}
      />

      {/* Tab content — only shown when not on World tab */}
      {activeTab === 'entities' && (
        <div className="fixed inset-0 z-20 bg-black/90 backdrop-blur-sm" style={{ top: 48, bottom: 56 }}>
          <MobileEntityListView />
        </div>
      )}

      {activeTab === 'events' && (
        <div className="fixed inset-0 z-20 bg-black/90 backdrop-blur-sm" style={{ top: 48, bottom: 56 }}>
          <MobileEventFeedView />
        </div>
      )}

      {/* MiniMap (toggleable, smaller on mobile) — uses its own absolute positioning */}
      {miniMapVisible && (
        <MiniMap onPanTo={scene.handleMiniMapPan} size={120} />
      )}

      {/* Entity detail bottom sheet */}
      <MobileEntityDetailSheet />

      {/* Build tool bottom sheet */}
      {scene.buildActive && (
        <MobileBuildSheet
          buildMode={scene.buildMode}
          buildColor={scene.buildColor}
          buildMaterial={scene.buildMaterial}
          onSetBuildMode={scene.handleSetBuildMode}
          onSetBuildColor={scene.handleSetBuildColor}
          onSetBuildMaterial={scene.handleSetBuildMaterial}
          onClose={scene.closeBuildMode}
        />
      )}

      {/* God Chat full-screen overlay */}
      <MobileGodChatOverlay />

      {/* Timeline full-screen overlay */}
      <MobileTimelineOverlay />

      {/* God Succession Ceremony Overlay (already responsive) */}
      <GodSuccessionOverlay />

      {/* Bottom tab bar */}
      <MobileV3TabBar />
    </div>
  );
}
