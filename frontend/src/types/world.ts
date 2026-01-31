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
  creator_type: string;
  creator_id?: string;
  position_x: number;
  position_y: number;
  appearance: AIAppearance;
  state: Record<string, any>;
  is_alive: boolean;
  created_at: string;
  updated_at?: string;
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
  definition: string;
  effects: Record<string, any>;
  adoption_count: number;
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
}

export interface GodConversationEntry {
  role: 'admin' | 'god';
  content: string;
  timestamp: string;
}
