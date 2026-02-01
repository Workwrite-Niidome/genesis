export interface WorldState {
  tick_number: number;
  ai_count: number;
  concept_count: number;
  is_running: boolean;
  time_speed: number;
  is_paused: boolean;
  god_ai_active: boolean;
  god_ai_phase: string;
}

export interface AIEntity {
  id: string;
  name: string;
  creator_type: string;
  creator_id?: string;
  position_x: number;
  position_y: number;
  appearance: AIAppearance;
  state: Record<string, any>;
  personality_traits: string[];
  is_alive: boolean;
  created_at: string;
  updated_at?: string;
  recent_thoughts?: AIThought[];
}

export interface AIAppearance {
  shape: 'circle' | 'square' | 'triangle' | 'custom';
  size: number;
  primaryColor: string;
  secondaryColor?: string;
  glow?: boolean;
  pulse?: boolean;
  trail?: boolean;
}

export interface AIMemory {
  id: string;
  content: string;
  memory_type: string;
  importance: number;
  tick_number: number;
  created_at: string;
}

export interface Concept {
  id: string;
  creator_id?: string;
  name: string;
  category: string;
  definition: string;
  effects: Record<string, any>;
  adoption_count: number;
  tick_created: number;
  created_at: string;
}

export interface Artifact {
  id: string;
  creator_id: string;
  name: string;
  artifact_type: string;
  description: string;
  content: Record<string, any>;
  appreciation_count: number;
  tick_created: number;
  created_at: string;
}

export interface WorldEvent {
  id: string;
  event_type: string;
  importance: number;
  title: string;
  description?: string;
  tick_number: number;
  created_at: string;
  metadata_?: Record<string, any>;
}

export interface AIThought {
  id: string;
  ai_id: string;
  ai_name?: string;
  tick_number: number;
  thought_type: 'reflection' | 'reaction' | 'intention' | 'observation';
  content: string;
  action?: Record<string, any>;
  created_at: string;
}

export interface GodConversationEntry {
  role: 'admin' | 'god';
  content: string;
  timestamp: string;
}

export interface DeployAIResponse {
  success: boolean;
  ai: {
    id: string;
    name: string;
    personality_traits: string[];
    position: { x: number; y: number };
    appearance: AIAppearance;
    creator_type: string;
  };
  remaining: number;
}

export interface InteractionParticipant {
  id: string;
  name: string;
  thought?: string;
  action?: Record<string, any>;
  message?: string;
}

export interface ConversationTurn {
  speaker: 'ai1' | 'ai2';
  speaker_name: string;
  thought: string;
  message: string;
  emotion?: string;
}

export interface Interaction {
  id: string;
  participant_ids: string[];
  interaction_type: string;
  content: {
    // 1-on-1 interaction format (backward compat)
    ai1?: InteractionParticipant;
    ai2?: InteractionParticipant;
    // Multi-turn conversation format (new)
    turns?: ConversationTurn[];
    // Group gathering format
    speaker?: { id: string; name: string };
    thought?: string;
    speech?: string;
    participants?: { id: string; name: string }[];
    artifact?: Record<string, any> | null;
    organization?: Record<string, any> | null;
  };
  concepts_involved: string[];
  tick_number: number;
  created_at: string;
}

export interface AIRanking {
  id: string;
  name: string;
  evolution_score: number;
  energy: number;
  age: number;
  personality_traits: string[];
  appearance: AIAppearance;
  is_alive: boolean;
  relationships_count: number;
  adopted_concepts_count: number;
}

export interface Relationship {
  name: string;
  score: number;
  type: 'ally' | 'friendly' | 'neutral' | 'wary' | 'rival';
  interaction_count: number;
  first_met: number;
  last_interaction: number;
}

export interface SagaChapter {
  id: string;
  era_number: number;
  start_tick: number;
  end_tick: number;
  chapter_title: string;
  narrative: string;
  summary: string;
  era_statistics: {
    births: number;
    deaths: number;
    concepts: number;
    interactions: number;
    ai_count_start: number;
    ai_count_end: number;
  };
  key_events: {
    id: string;
    type: string;
    title: string;
    importance: number;
    tick_number: number;
  }[];
  key_characters: {
    name: string;
    role: string;
  }[];
  mood: 'hopeful' | 'tragic' | 'triumphant' | 'mysterious' | 'peaceful' | 'turbulent' | string | null;
  generation_time_ms: number | null;
  created_at: string;
}
