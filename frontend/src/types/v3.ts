/**
 * GENESIS v3 Type Definitions
 * 3D voxel world where AI and humans are indistinguishable.
 */

// ============================================================
// World Types
// ============================================================

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface Voxel {
  x: number;
  y: number;
  z: number;
  color: string;       // "#FF4400"
  material: 'solid' | 'glass' | 'emissive' | 'liquid';
  hasCollision: boolean;
  placedBy?: string;   // entity ID
  structureId?: string;
}

export interface VoxelUpdate {
  type: 'place' | 'destroy';
  x: number;
  y: number;
  z: number;
  color?: string;
  material?: string;
}

export interface StructureInfo {
  id: string;
  name?: string;
  ownerId?: string;
  structureType: string;
  bounds: {
    min: Vector3;
    max: Vector3;
  };
}

export interface ZoneInfo {
  id: string;
  name: string;
  ownerId?: string;
  zoneType: string;
  bounds: {
    min: Vector3;
    max: Vector3;
  };
  rules: Record<string, any>;
}

// ============================================================
// Entity Types (unified — no AI/human distinction)
// ============================================================

export interface EntityV3 {
  id: string;
  name: string;
  position: Vector3;
  facing: { x: number; z: number };
  appearance: EntityAppearance;
  personality: PersonalityParams;
  state: EntityState;
  isAlive: boolean;
  isGod: boolean;
  metaAwareness: number;
  birthTick: number;
  deathTick?: number;
  createdAt: string;
}

export interface EntityAppearance {
  bodyColor: string;
  accentColor: string;
  shape: 'humanoid' | 'sphere' | 'crystal' | 'custom';
  size: number;
  emissive: boolean;
  voxelData?: number[][]; // Custom voxel avatar data
}

export interface EntityState {
  needs: NeedsState;
  behaviorMode: 'normal' | 'desperate' | 'rampage';
  currentAction?: string;
  energy: number;
  inventory: string[];
}

export interface NeedsState {
  curiosity: number;
  social: number;
  creation: number;
  dominance: number;
  safety: number;
  expression: number;
  understanding: number;
  evolutionPressure: number;
}

// ============================================================
// Personality (18 axes, 0.0-1.0, immutable)
// ============================================================

export interface PersonalityParams {
  // Value axes
  orderVsChaos: number;
  cooperationVsCompetition: number;
  curiosity: number;
  ambition: number;
  empathy: number;
  aggression: number;
  creativity: number;
  riskTolerance: number;
  selfPreservation: number;
  aestheticSense: number;
  // Conversation style
  verbosity: number;
  politeness: number;
  leadership: number;
  honesty: number;
  humor: number;
  // Behavior style
  patience: number;
  planningHorizon: number;
  conformity: number;
}

// ============================================================
// Relationship (7 axes)
// ============================================================

export interface RelationshipV3 {
  entityId: string;
  targetId: string;
  targetName?: string;
  trust: number;        // -100 ~ 100
  familiarity: number;  // 0 ~ 100
  respect: number;      // 0 ~ 100
  fear: number;         // 0 ~ 100
  rivalry: number;      // 0 ~ 100
  gratitude: number;    // 0 ~ 100
  anger: number;        // 0 ~ 100
  debt: number;         // -100 ~ 100
  alliance: boolean;
}

// ============================================================
// Memory Types
// ============================================================

export interface EpisodicMemoryV3 {
  id: string;
  summary: string;
  importance: number;
  tick: number;
  relatedEntityIds: string[];
  location?: Vector3;
  memoryType: string;
  createdAt: string;
}

export interface SemanticMemoryV3 {
  key: string;
  value: string;
  confidence: number;
}

// ============================================================
// World Events (event sourcing)
// ============================================================

export interface WorldEventV3 {
  id: number;
  tick: number;
  actorId?: string;
  eventType: string;
  action: string;
  params: Record<string, any>;
  result: 'accepted' | 'rejected';
  reason?: string;
  position?: Vector3;
  importance: number;
  createdAt: string;
}

// ============================================================
// World State
// ============================================================

export interface WorldStateV3 {
  tickNumber: number;
  entityCount: number;
  voxelCount: number;
  structureCount: number;
  isRunning: boolean;
  timeSpeed: number;
  isPaused: boolean;
  godEntityId?: string;
  godPhase: string;
}

// ============================================================
// Action Proposal (client → server)
// ============================================================

export interface ActionProposal {
  agentId: string;
  action: string;
  params: Record<string, any>;
}

// ============================================================
// Socket Events
// ============================================================

export interface SocketEntityPosition {
  id: string;
  x: number;
  y: number;
  z: number;
  fx: number;  // facing x
  fz: number;  // facing z
  name: string;
  action?: string;
}

export interface SocketVoxelUpdate {
  type: 'place' | 'destroy';
  x: number;
  y: number;
  z: number;
  color?: string;
  material?: string;
  placedBy?: string;
}

export interface SocketWorldTick {
  tickNumber: number;
  entityCount: number;
  voxelCount: number;
  processingTimeMs: number;
}

export interface SocketSpeechEvent {
  entityId: string;
  entityName: string;
  text: string;
  position: Vector3;
  tick: number;
}
