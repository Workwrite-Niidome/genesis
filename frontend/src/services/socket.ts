import { io, Socket } from 'socket.io-client';
import { useWorldStore } from '../stores/worldStore';
import { useAIStore } from '../stores/aiStore';
import { useThoughtStore } from '../stores/thoughtStore';
import { useChatStore } from '../stores/chatStore';
import { useBoardStore } from '../stores/boardStore';
import { useSagaStore } from '../stores/sagaStore';

let socket: Socket | null = null;

export function connectSocket(): Socket {
  if (socket?.connected) return socket;

  // In production (served by nginx), use same origin; in dev, swap port to 8000
  const isDev = import.meta.env.DEV;
  const wsUrl = isDev
    ? window.location.origin.replace(/:\d+$/, ':8000')
    : window.location.origin;

  socket = io(wsUrl, {
    path: '/ws/socket.io',
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 2000,
  });

  socket.on('connect', () => {
    console.log('[GENESIS] WebSocket connected');
  });

  socket.on('disconnect', () => {
    console.log('[GENESIS] WebSocket disconnected');
  });

  socket.on('thought', (data: any) => {
    useThoughtStore.getState().addThought(data);
  });

  socket.on('event', (data: any) => {
    // Update world store counts on significant events
    const world = useWorldStore.getState();
    if (data.event_type === 'ai_birth') world.fetchState();
    if (data.event_type === 'concept_created') world.fetchState();
  });

  socket.on('world_update', (data: any) => {
    const store = useWorldStore.getState();
    if (data.tick_number) store.setTickNumber(data.tick_number);
  });

  socket.on('ai_position', (data: any) => {
    const store = useAIStore.getState();
    if (Array.isArray(data)) {
      // Batch position update: array of {id, x, y, name}
      data.forEach((pos: any) => {
        store.updateAI({
          id: pos.id,
          position_x: pos.x,
          position_y: pos.y,
        });
      });
    } else {
      // Single position update
      store.updateAI({
        id: data.id,
        position_x: data.x,
        position_y: data.y,
      });
    }
  });

  socket.on('interaction', (_data: any) => {
    // Interactions are reflected through world_update tick counts
  });

  socket.on('god_observation', (_data: any) => {
    // God observations are fetched via the god feed polling
  });

  socket.on('ai_death', (data: any) => {
    const store = useAIStore.getState();
    store.updateAI({ id: data.id, is_alive: false });
    console.log('[GENESIS] AI died:', data.name);
  });

  socket.on('concept_created', (_data: any) => {
    // Refresh world state to update concept count
    useWorldStore.getState().fetchState();
  });

  socket.on('artifact_created', (_data: any) => {
    // Artifacts are fetched via panel polling
  });

  socket.on('organization_formed', (_data: any) => {
    // Organizations are fetched via concept panel polling
  });

  socket.on('chat_message', (data: any) => {
    useChatStore.getState().addMessage(data);
  });

  socket.on('board_thread', (data: any) => {
    useBoardStore.getState().addThread(data);
  });

  socket.on('board_reply', (data: any) => {
    useBoardStore.getState().addReply(data);
  });

  socket.on('saga_chapter', (data: any) => {
    useSagaStore.getState().onNewChapter(data);
    console.log('[GENESIS] New saga chapter:', data.chapter_title);
  });

  return socket;
}

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

export function getSocket(): Socket | null {
  return socket;
}
