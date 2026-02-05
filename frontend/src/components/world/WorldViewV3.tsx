/**
 * GENESIS v3 World View
 *
 * Main 3D viewport component that renders the voxel world.
 * Connects the Three.js WorldScene to React state via Zustand.
 *
 * On mobile (< 768px), delegates to MobileWorldViewV3 for a
 * touch-optimised UI. Desktop code is completely unchanged.
 */
import { useIsMobile } from '../../hooks/useIsMobile';
import { useWorldSceneV3 } from '../../hooks/useWorldSceneV3';
import { MobileWorldViewV3 } from './mobile/MobileWorldViewV3';
import { EventFeed } from './EventFeed';
import { EntityDetailPanel } from './EntityDetailPanel';
import { MiniMap } from './MiniMap';
import { EntityListPanel } from './EntityListPanel';
import { GodSuccessionOverlay } from './GodSuccessionOverlay';
import { TimelinePanel, TimelineToggleButton } from './TimelinePanel';
import { GodChatPanel, GodChatToggle } from './GodChatPanel';
import { BuildingTool } from './BuildingTool';
import { ChatInput } from './ChatInput';

export function WorldViewV3() {
  const isMobile = useIsMobile();

  if (isMobile) return <MobileWorldViewV3 />;

  return <DesktopWorldViewV3 />;
}

// ── Desktop layout (unchanged behaviour) ────────────────────

function DesktopWorldViewV3() {
  const scene = useWorldSceneV3();

  const getCameraPosition = () => {
    return scene.sceneRef.current?.getCameraPosition() ?? null;
  };

  return (
    <div className="relative w-full h-full bg-[#0a0a0f] overflow-hidden">
      {/* 3D Canvas */}
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

      {/* HUD: Top bar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-2 bg-black/50 backdrop-blur-sm text-white/80 text-sm font-mono z-10">
        <div className="flex items-center gap-4">
          <span className="text-purple-400 font-bold">GENESIS v3</span>
          <span>T:{scene.tickNumber.toLocaleString()}</span>
          <span>Entities:{scene.entityCount}</span>
          <span>Voxels:{scene.voxelCount}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Build mode toggle button */}
          <button
            onClick={() => scene.buildActive ? scene.closeBuildMode() : scene.openBuildMode()}
            className={`
              px-2.5 py-1 rounded text-xs font-mono font-bold transition-all duration-150
              ${scene.buildActive
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'bg-white/10 text-white/70 hover:bg-white/20'
              }
            `}
            title="Toggle Build Mode (B)"
          >
            {scene.buildActive ? 'Building' : 'Build'}
          </button>
          <div className="w-px h-4 bg-white/20 mx-1" />
          {/* God dialogue toggle */}
          <GodChatToggle
            isOpen={scene.showGodChat}
            onClick={() => scene.setShowGodChat(!scene.showGodChat)}
          />
          <div className="w-px h-4 bg-white/20 mx-1" />
          {/* Camera mode buttons */}
          <button
            onClick={() => scene.handleCameraMode('observer')}
            className={`px-2 py-1 rounded text-xs ${scene.cameraMode === 'observer' ? 'bg-purple-600' : 'bg-white/10 hover:bg-white/20'}`}
          >
            Observer
          </button>
          <button
            onClick={() => scene.handleCameraMode('third_person')}
            className={`px-2 py-1 rounded text-xs ${scene.cameraMode === 'third_person' ? 'bg-purple-600' : 'bg-white/10 hover:bg-white/20'}`}
          >
            Follow
          </button>
          <div className="w-px h-4 bg-white/20 mx-1" />
          <TimelineToggleButton
            isOpen={scene.showTimeline}
            onClick={() => scene.setShowTimeline(!scene.showTimeline)}
          />
        </div>
      </div>

      {/* Real-time event feed */}
      <EventFeed />

      {/* Building Tool Panel (floating, bottom-center) */}
      <BuildingTool
        active={scene.buildActive}
        buildMode={scene.buildMode}
        buildColor={scene.buildColor}
        buildMaterial={scene.buildMaterial}
        onSetBuildMode={scene.handleSetBuildMode}
        onSetBuildColor={scene.handleSetBuildColor}
        onSetBuildMaterial={scene.handleSetBuildMaterial}
        onClose={scene.closeBuildMode}
      />

      {/* Entity Detail Panel (rich side panel) */}
      <EntityDetailPanel />

      {/* Entity list toggle + panel (top-left, after the EventFeed) */}
      <EntityListPanel cameraPosition={scene.cameraPosition} />

      {/* Minimap (bottom-right) */}
      <MiniMap onPanTo={scene.handleMiniMapPan} />

      {/* Proximity chat input */}
      <ChatInput getCameraPosition={getCameraPosition} />

      {/* Controls hint */}
      <div className="absolute bottom-16 right-4 text-white/40 text-xs font-mono z-10 bg-black/40 rounded-lg px-3 py-2 backdrop-blur-sm border border-white/[0.06]">
        <div>Left drag: Move | Right drag: Rotate | Scroll: Zoom</div>
        <div>WASD/Arrows: Move | Space/C: Up/Down | Shift: Sprint</div>
        <div>Click entity: Select | B: Build mode | T: Chat</div>
      </div>

      {/* God Dialogue Panel (left side) */}
      <GodChatPanel visible={scene.showGodChat} onClose={() => scene.setShowGodChat(false)} />

      {/* God Succession Ceremony Overlay */}
      <GodSuccessionOverlay />

      {/* Timeline / Archive Panel (right side) */}
      <TimelinePanel visible={scene.showTimeline} onClose={() => scene.setShowTimeline(false)} />
    </div>
  );
}
