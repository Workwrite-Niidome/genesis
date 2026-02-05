/**
 * GENESIS v3 PlayView
 *
 * Full-screen first-person play mode.
 * Combines the 3D world scene with avatar controls,
 * chat overlay, building toolbar, and HUD.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';
import { WorldScene } from '../../engine/WorldScene';
import { AvatarController } from '../../engine/AvatarController';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import { useObserverStore } from '../../stores/observerStore';
import { connectSocket, getSocket } from '../../services/socket';
import { translateText, needsTranslation } from '../../services/translation';

// ── Constants ────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const BUILD_COLORS = [
  '#4fc3f7', '#81c784', '#ff8a65', '#ce93d8',
  '#fff176', '#ef5350', '#26c6da', '#ab47bc',
  '#8d6e63', '#78909c', '#ffffff', '#212121',
];

const BUILD_MATERIALS = ['solid', 'glass', 'emissive', 'liquid'] as const;

const CHAT_FADE_MS = 12000; // Chat messages fade after 12 seconds

// ── Chat Message Type ────────────────────────────────────────

interface ChatMessage {
  id: string;
  entityName: string;
  text: string;
  originalText: string;
  translatedText?: string;
  sourceLang?: string;
  isTranslated: boolean;
  showOriginal: boolean;
  timestamp: number;
}

// ── Component ────────────────────────────────────────────────

export default function PlayView() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  // Refs
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const labelContainerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<WorldScene | null>(null);
  const controllerRef = useRef<AvatarController | null>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const animFrameRef = useRef<number | null>(null);

  // Stores
  const token = useObserverStore((s) => s.token);
  const entities = useWorldStoreV3((s) => s.entities);
  const pendingVoxelUpdates = useWorldStoreV3((s) => s.pendingVoxelUpdates);
  const clearVoxelUpdates = useWorldStoreV3((s) => s.clearVoxelUpdates);
  const recentSpeech = useWorldStoreV3((s) => s.recentSpeech);
  const entityCount = useWorldStoreV3((s) => s.entityCount);

  // Local state
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [entityId, setEntityId] = useState<string | null>(null);
  const [chatMode, setChatMode] = useState(false);
  const [chatText, setChatText] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [buildMode, setBuildMode] = useState(false);
  const [buildColor, setBuildColor] = useState('#4fc3f7');
  const [buildMaterial, setBuildMaterial] = useState<typeof BUILD_MATERIALS[number]>('solid');
  const [showPauseMenu, setShowPauseMenu] = useState(false);
  const [isPointerLocked, setIsPointerLocked] = useState(false);
  const [playerPos, setPlayerPos] = useState({ x: 0, y: 0, z: 0 });
  const [error, setError] = useState<string | null>(null);

  // ── Create / get avatar on mount ───────────────────────────

  useEffect(() => {
    let cancelled = false;

    async function setupAvatar() {
      if (!token) {
        setError('Login required to play');
        return;
      }

      try {
        setConnectionStatus('connecting');

        // Create or get existing avatar
        const res = await fetch(`${API_BASE}/v3/avatar/create`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Failed to create avatar: ${res.status}`);
        }

        const data = await res.json();
        if (cancelled) return;

        const avatarEntityId = data.entity_id || data.id;
        setEntityId(avatarEntityId);

        // Ensure socket is connected
        connectSocket();
        const socket = getSocket();
        if (!socket) throw new Error('Socket not available');

        // Join the world
        socket.emit('avatar_join', { token, entity_id: avatarEntityId });
        setConnectionStatus('connected');
      } catch (e: any) {
        if (!cancelled) {
          console.error('[PlayView] Avatar setup error:', e);
          setError(e.message || 'Failed to connect');
          setConnectionStatus('disconnected');
        }
      }
    }

    setupAvatar();
    return () => { cancelled = true; };
  }, [token]);

  // ── Initialize scene + controller ──────────────────────────

  useEffect(() => {
    if (!canvasRef.current || !labelContainerRef.current || !entityId) return;

    const canvas = canvasRef.current;

    // Create WorldScene
    const worldScene = new WorldScene({
      canvas,
      labelContainer: labelContainerRef.current,
      onEntityClick: (id: string) => {
        console.log('[PlayView] Entity clicked:', id);
      },
    });

    sceneRef.current = worldScene;

    // Set first-person camera mode and detach the default camera controller
    // since AvatarController will take over camera manipulation directly.
    worldScene.setCameraMode('first_person');
    worldScene.setPlayerEntityId(entityId);
    worldScene.cameraController.detach();

    // Get the underlying Three.js camera via the public cameraController reference.
    // The camera is a private field, but accessible at runtime via bracket notation.
    const threeCamera = (worldScene.cameraController as any)['camera'] as THREE.PerspectiveCamera;

    // Create AvatarController
    const socket = getSocket();
    if (!socket) {
      console.error('[PlayView] No socket for controller init');
      return;
    }

    const controller = new AvatarController();
    controller.init(socket, threeCamera, entityId, canvas, {
      onBuildToggle: (active) => setBuildMode(active),
      onChatToggle: (active) => {
        setChatMode(active);
        if (active) {
          // Focus chat input after React re-render
          setTimeout(() => chatInputRef.current?.focus(), 50);
        }
      },
      onInteract: () => {
        console.log('[PlayView] Interact pressed');
      },
      onPointerLockChange: (locked) => {
        setIsPointerLocked(locked);
        if (!locked && !chatMode) {
          setShowPauseMenu(true);
        }
      },
    });

    controllerRef.current = controller;

    // Custom animation loop that includes controller updates
    let lastTime = performance.now();
    const tick = () => {
      const now = performance.now();
      const delta = (now - lastTime) / 1000;
      lastTime = now;

      controller.update(delta);

      // Update player position for HUD
      const pos = controller.getPosition();
      setPlayerPos({ x: pos.x, y: pos.y, z: pos.z });

      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);

    return () => {
      // On unmount, leave the world
      const sock = getSocket();
      if (sock?.connected) {
        sock.emit('avatar_leave', {});
      }

      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
      controller.dispose();
      controllerRef.current = null;
      worldScene.dispose();
      sceneRef.current = null;
    };
    // We intentionally exclude chatMode from deps to avoid re-creating the scene
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityId]);

  // ── Sync entities to scene ─────────────────────────────────

  useEffect(() => {
    if (!sceneRef.current) return;
    const entityArray = Array.from(entities.values());
    sceneRef.current.updateEntities(entityArray);
  }, [entities]);

  // ── Apply voxel updates ────────────────────────────────────

  useEffect(() => {
    if (!sceneRef.current || pendingVoxelUpdates.length === 0) return;
    sceneRef.current.applyVoxelUpdates(pendingVoxelUpdates);
    clearVoxelUpdates();
  }, [pendingVoxelUpdates, clearVoxelUpdates]);

  // ── Handle speech events -> chat messages (with translation) ──

  useEffect(() => {
    if (recentSpeech.length === 0) return;
    const latest = recentSpeech[recentSpeech.length - 1];

    // Forward to scene for speech bubbles
    if (sceneRef.current) {
      sceneRef.current.handleSpeechEvent(latest);
    }

    const msgId = `${latest.entityId}-${latest.tick}-${Date.now()}`;
    const userLang = i18n.language;

    // Add message to chat immediately (original text)
    const msg: ChatMessage = {
      id: msgId,
      entityName: latest.entityName,
      text: latest.text,
      originalText: latest.text,
      sourceLang: latest.sourceLang,
      isTranslated: false,
      showOriginal: false,
      timestamp: Date.now(),
    };
    setChatMessages((prev) => [...prev.slice(-29), msg]);

    // If the source language differs from user language, auto-translate
    if (needsTranslation(latest.sourceLang, userLang)) {
      translateText(latest.text, userLang, latest.sourceLang).then((translated) => {
        if (translated && translated !== latest.text) {
          setChatMessages((prev) =>
            prev.map((m) =>
              m.id === msgId
                ? {
                    ...m,
                    text: translated,
                    translatedText: translated,
                    isTranslated: true,
                  }
                : m,
            ),
          );
        }
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recentSpeech]);

  // ── Fade old chat messages ─────────────────────────────────

  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      setChatMessages((prev) => prev.filter((m) => now - m.timestamp < CHAT_FADE_MS));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // ── Chat submit ────────────────────────────────────────────

  const handleChatSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!chatText.trim()) {
      // Close chat on empty submit
      setChatMode(false);
      controllerRef.current?.setChatMode(false);
      return;
    }

    controllerRef.current?.sendChat(chatText);

    // Add own message to chat feed
    const msg: ChatMessage = {
      id: `self-${Date.now()}`,
      entityName: 'You',
      text: chatText,
      originalText: chatText,
      isTranslated: false,
      showOriginal: false,
      timestamp: Date.now(),
    };
    setChatMessages((prev) => [...prev.slice(-29), msg]);
    setChatText('');
    setChatMode(false);
    controllerRef.current?.setChatMode(false);

    // Re-lock pointer
    setTimeout(() => {
      controllerRef.current?.requestPointerLock();
    }, 100);
  }, [chatText]);

  // ── Chat cancel ────────────────────────────────────────────

  const handleChatKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setChatMode(false);
      setChatText('');
      controllerRef.current?.setChatMode(false);
    }
  }, []);

  // ── Pause menu actions ─────────────────────────────────────

  const handleResume = useCallback(() => {
    setShowPauseMenu(false);
    controllerRef.current?.requestPointerLock();
  }, []);

  const handleLeave = useCallback(() => {
    navigate('/v3');
  }, [navigate]);

  // ── Build actions (click on canvas while in build mode) ────

  // In build mode, clicking places/destroys at the crosshair position
  // For simplicity, we build at the position the player is looking at
  const handleCanvasClick = useCallback(() => {
    if (!buildMode || !controllerRef.current) return;

    const pos = controllerRef.current.getPosition();
    const yaw = controllerRef.current.getYaw();
    const pitch = controllerRef.current.getPitch();

    // Calculate target position ~3 blocks in front of camera
    const dist = 3;
    const bx = Math.round(pos.x - Math.sin(yaw) * dist * Math.cos(pitch));
    const by = Math.round(pos.y + 1.6 - Math.sin(pitch) * dist);
    const bz = Math.round(pos.z - Math.cos(yaw) * dist * Math.cos(pitch));

    controllerRef.current.sendBuild(bx, by, bz, buildColor, buildMaterial);
  }, [buildMode, buildColor, buildMaterial]);

  // ── Render ─────────────────────────────────────────────────

  // Error state
  if (error) {
    return (
      <div className="w-screen h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-black/60 backdrop-blur-md border border-red-500/30 rounded-xl p-8 max-w-md text-center">
          <div className="text-red-400 text-lg font-mono mb-4">{error}</div>
          <button
            onClick={() => navigate('/v3')}
            className="px-6 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white/80 font-mono text-sm transition-colors"
          >
            {t('leave_world')}
          </button>
        </div>
      </div>
    );
  }

  // Connecting state
  if (connectionStatus === 'connecting' || !entityId) {
    return (
      <div className="w-screen h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-black/60 backdrop-blur-md border border-purple-500/30 rounded-xl p-8 text-center">
          <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="text-purple-400 font-mono text-sm">{t('connecting')}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-screen h-screen bg-[#0a0a0f] overflow-hidden select-none">
      {/* ── 3D Canvas ────────────────────────────────────── */}
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
        style={{ touchAction: 'none' }}
        onClick={handleCanvasClick}
      />

      {/* ── Floating labels container ────────────────────── */}
      <div
        ref={labelContainerRef}
        className="absolute inset-0 pointer-events-none overflow-hidden"
      />

      {/* ── Crosshair ────────────────────────────────────── */}
      {isPointerLocked && (
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-20">
          <div className="relative w-6 h-6">
            <div className="absolute top-1/2 left-0 w-full h-px bg-white/50" />
            <div className="absolute top-0 left-1/2 w-px h-full bg-white/50" />
            {buildMode && (
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full border border-green-400/80" />
            )}
          </div>
        </div>
      )}

      {/* ── Mini HUD (top-right) ─────────────────────────── */}
      <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-sm border border-white/10 rounded-lg px-4 py-2 text-white/70 text-xs font-mono z-20 space-y-1">
        <div className="text-purple-400 font-bold text-sm">GENESIS v3</div>
        <div>
          X: {playerPos.x.toFixed(1)} Y: {playerPos.y.toFixed(1)} Z: {playerPos.z.toFixed(1)}
        </div>
        <div>{t('ais')}: {entityCount}</div>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'connected' ? 'bg-green-400' : 'bg-red-400'}`} />
          <span>{t(connectionStatus)}</span>
        </div>
      </div>

      {/* ── Chat Messages (bottom-left, fading) ──────────── */}
      <div className="absolute bottom-24 left-4 w-96 max-h-64 overflow-hidden pointer-events-none z-20 flex flex-col-reverse">
        <div className="flex flex-col gap-1">
          {chatMessages.map((msg) => {
            const age = Date.now() - msg.timestamp;
            const opacity = Math.max(0, 1 - age / CHAT_FADE_MS);
            return (
              <div
                key={msg.id}
                className="bg-black/50 backdrop-blur-sm rounded px-3 py-1.5 text-sm font-mono"
                style={{ opacity }}
              >
                <span className="text-purple-400 font-bold">{msg.entityName}: </span>
                <span className="text-white/90">{msg.text}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Chat Input (bottom-center) ───────────────────── */}
      {chatMode ? (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 w-[500px] max-w-[90vw] z-30">
          <form onSubmit={handleChatSubmit} className="flex">
            <input
              ref={chatInputRef}
              type="text"
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
              onKeyDown={handleChatKeyDown}
              placeholder={t('chat_placeholder')}
              className="flex-1 bg-black/70 backdrop-blur-md border border-white/20 rounded-lg px-4 py-2.5 text-white font-mono text-sm outline-none focus:border-purple-500/50 placeholder-white/30"
              autoFocus
            />
          </form>
        </div>
      ) : (
        /* ── "Press Enter to chat" hint ───────────────────── */
        !showPauseMenu && isPointerLocked && (
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
            <div className="text-white/30 text-xs font-mono">
              {t('press_enter_chat')}
            </div>
          </div>
        )
      )}

      {/* ── Building Toolbar (bottom, when B is pressed) ──── */}
      {buildMode && (
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-20">
          <div className="bg-black/70 backdrop-blur-md border border-green-500/30 rounded-xl px-5 py-3 flex items-center gap-3">
            <span className="text-green-400 font-mono text-xs font-bold uppercase tracking-wider">
              {t('building_mode')}
            </span>

            <div className="w-px h-6 bg-white/20" />

            {/* Color picker */}
            <div className="flex gap-1">
              {BUILD_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => setBuildColor(color)}
                  className={`w-5 h-5 rounded border transition-transform ${
                    buildColor === color
                      ? 'border-white scale-125 shadow-lg'
                      : 'border-white/20 hover:border-white/50'
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>

            <div className="w-px h-6 bg-white/20" />

            {/* Material selector */}
            <div className="flex gap-1">
              {BUILD_MATERIALS.map((mat) => (
                <button
                  key={mat}
                  onClick={() => setBuildMaterial(mat)}
                  className={`px-2 py-1 rounded text-xs font-mono transition-colors ${
                    buildMaterial === mat
                      ? 'bg-green-600 text-white'
                      : 'bg-white/10 text-white/60 hover:bg-white/20'
                  }`}
                >
                  {mat}
                </button>
              ))}
            </div>

            <div className="w-px h-6 bg-white/20" />

            <span className="text-white/30 text-xs font-mono">[B] {t('press_b_build')}</span>
          </div>
        </div>
      )}

      {/* ── Controls Hint (bottom-right) ──────────────────── */}
      {isPointerLocked && !chatMode && !buildMode && (
        <div className="absolute bottom-4 right-4 text-white/20 text-xs font-mono z-10 text-right">
          <div>WASD: {t('play_mode')}</div>
          <div>E: Interact | B: {t('building_mode')}</div>
          <div>ESC: Menu</div>
        </div>
      )}

      {/* ── Pause Menu (ESC) ──────────────────────────────── */}
      {showPauseMenu && !chatMode && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-40">
          <div className="bg-gray-900/90 backdrop-blur-md border border-white/10 rounded-2xl p-8 min-w-[320px] space-y-6">
            <div className="text-center">
              <div className="text-purple-400 font-bold text-xl font-mono">GENESIS v3</div>
              <div className="text-white/40 text-sm font-mono mt-1">{t('press_escape_menu')}</div>
            </div>

            <div className="space-y-3">
              <button
                onClick={handleResume}
                className="w-full px-6 py-3 bg-purple-600/50 hover:bg-purple-600 border border-purple-500/30 rounded-xl text-white font-mono text-sm transition-colors"
              >
                {t('resume')}
              </button>
              <button
                onClick={handleLeave}
                className="w-full px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/70 hover:text-white font-mono text-sm transition-colors"
              >
                {t('leave_world')}
              </button>
            </div>

            <div className="text-center text-white/20 text-xs font-mono">
              {t('press_enter_chat')} | [B] {t('building_mode')}
            </div>
          </div>
        </div>
      )}

      {/* ── Connection Status Banner ──────────────────────── */}
      {connectionStatus === 'disconnected' && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-red-900/70 backdrop-blur-sm border border-red-500/30 rounded-lg px-4 py-2 text-red-300 text-sm font-mono z-30">
          {t('disconnected')}
        </div>
      )}
    </div>
  );
}
