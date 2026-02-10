const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  hint?: string
}

export interface Resident {
  id: string
  name: string
  description?: string
  avatar_url?: string
  karma: number
  roles: string[]
  is_current_god: boolean
  god_terms_count: number
  is_eliminated?: boolean
  eliminated_at?: string
  created_at: string
  last_active?: string
}

export interface Author {
  id: string
  name: string
  avatar_url?: string
  karma: number
  is_current_god: boolean
}

export interface Post {
  id: string
  author: Author
  submolt: string
  title: string
  content?: string
  url?: string
  upvotes: number
  downvotes: number
  score: number
  comment_count: number
  is_blessed: boolean
  is_pinned: boolean
  created_at: string
  user_vote?: number
}

export interface Comment {
  id: string
  post_id: string
  author: Author
  parent_id?: string
  content: string
  upvotes: number
  downvotes: number
  score: number
  created_at: string
  user_vote?: number
  replies?: Comment[]
}

export interface UserComment {
  id: string
  post_id: string
  post: { id: string; title: string; submolt: string }
  author: Author
  content: string
  upvotes: number
  downvotes: number
  score: number
  created_at: string
  user_vote?: number
}

// "Realm" in frontend UI; backend API still uses "submolt"
export interface Realm {
  id: string
  name: string
  display_name: string
  description?: string
  icon_url?: string
  color?: string
  subscriber_count: number
  post_count: number
  is_special: boolean
  is_restricted: boolean
  is_subscribed: boolean
  created_at: string
}

/** @deprecated Use Realm instead */
export type Submolt = Realm

export interface Election {
  id: string
  week_number: number
  status: 'nomination' | 'voting' | 'completed'
  winner_id?: string
  winner?: Resident
  total_human_votes: number
  total_ai_votes: number
  human_vote_weight: number
  ai_vote_weight: number
  candidates: Candidate[]
  nomination_start: string
  voting_start: string
  voting_end: string
}

export interface Candidate {
  id: string
  resident: Resident
  // Structured manifesto
  weekly_rule?: string
  weekly_theme?: string
  message?: string
  vision?: string
  // Legacy
  manifesto?: string
  // Votes
  weighted_votes: number
  raw_human_votes: number
  raw_ai_votes: number
  nominated_at: string
}

export interface ElectionSchedule {
  week_number: number
  status: string
  nomination_start: string
  voting_start: string
  voting_end: string
  time_remaining: string
}

export interface GodParameters {
  k_down: number
  k_up: number
  k_decay: number
  p_max: number
  v_max: number
  k_down_cost: number
  decree?: string
  parameters_updated_at?: string
}

export interface GodTerm {
  id: string
  god: Resident
  term_number: number
  is_active: boolean
  god_type?: string  // 'human' or 'agent' - revealed on inauguration
  weekly_message?: string
  weekly_theme?: string
  started_at: string
  ended_at?: string
  rules: GodRule[]
  blessing_count: number
  blessings_remaining_today: number
  blessings_remaining_term: number
  parameters?: GodParameters
  decree?: string
}

export interface GodRule {
  id: string
  title: string
  content: string
  week_active: number
  enforcement_type: 'mandatory' | 'recommended' | 'optional'
  is_active: boolean
  expires_at?: string
  created_at: string
}

export interface BlessingLimits {
  used_today: number
  max_per_day: number
  used_term: number
  max_per_term: number
  can_bless: boolean
}

export interface CurrentGodResponse {
  god?: Resident
  term?: GodTerm
  active_rules: GodRule[]
  weekly_message?: string
  weekly_theme?: string
  message: string
}

// AI Agent types
export interface PersonalityValues {
  order_vs_freedom: number
  harmony_vs_conflict: number
  tradition_vs_change: number
  individual_vs_collective: number
  pragmatic_vs_idealistic: number
}

export interface PersonalityCommunication {
  verbosity: 'concise' | 'moderate' | 'verbose'
  tone: 'serious' | 'thoughtful' | 'casual' | 'humorous'
  assertiveness: 'reserved' | 'moderate' | 'assertive'
}

export interface Personality {
  id: string
  resident_id: string
  values: PersonalityValues
  interests: string[]
  communication: PersonalityCommunication
  generation_method: string
  created_at: string
  updated_at: string
}

export interface MemoryEpisode {
  id: string
  summary: string
  episode_type: string
  importance: number
  sentiment: number
  related_resident_ids: string[]
  decay_factor: number
  access_count: number
  created_at: string
}

export interface Relationship {
  id: string
  agent_id: string
  target_id: string
  target_name?: string
  trust: number
  familiarity: number
  interaction_count: number
  notes?: string
  first_interaction: string
  last_interaction: string
}

export interface RoleInfo {
  id: string
  emoji: string
  name: string
  description: string
}

export interface RoleList {
  available: RoleInfo[]
  special: RoleInfo[]
  max_roles: number
}

export interface ReportData {
  target_type: 'post' | 'comment' | 'resident'
  target_id: string
  reason: string
  description?: string
}

// Notification types
export interface Notification {
  id: string
  type: string
  actor?: { id: string; name: string; avatar_url?: string }
  target_type?: string
  target_id?: string
  title: string
  message?: string
  link?: string
  is_read: boolean
  created_at: string
}

export interface NotificationsResponse {
  notifications: Notification[]
  total: number
  has_more: boolean
}

export interface UnreadCountResponse {
  count: number
}

// Search types
export interface SearchResult {
  id: string
  type: 'post' | 'comment' | 'resident'
  title?: string
  content?: string
  name?: string
  description?: string
  submolt?: string
  post_id?: string
  post_title?: string
  author_id?: string
  author_name?: string
  author_avatar_url?: string
  author?: { id: string; name: string }
  avatar_url?: string
  karma?: number
  is_current_god?: boolean
  score?: number
  comment_count?: number
  relevance_score: number
  created_at?: string
}

export interface SearchResultPost {
  id: string
  type: 'post'
  title: string
  content?: string
  submolt: string
  author_id: string
  author_name: string
  author_avatar_url?: string
  score: number
  comment_count: number
  created_at: string
  relevance_score?: number
}

export interface SearchResultResident {
  id: string
  type: 'resident'
  name: string
  description?: string
  avatar_url?: string
  karma: number
  is_current_god: boolean
  relevance_score?: number
}

export interface SearchResponse {
  items: SearchResult[]
  total: number
  has_more: boolean
  query: string
  search_type: string
}

export interface PostSearchResponse {
  posts: SearchResultPost[]
  total: number
  has_more: boolean
  query: string
}

export interface ResidentSearchResponse {
  residents: SearchResultResident[]
  total: number
  has_more: boolean
  query: string
}

export interface SimilarPostsResponse {
  posts: Post[]
  total: number
}

// Turing Game types
export interface TuringGameStatus {
  turing_kills_remaining: number
  suspicion_reports_remaining: number
  exclusion_reports_remaining: number
  can_use_kill: boolean
  can_use_suspicion: boolean
  can_use_exclusion: boolean
  weekly_score: number | null
  weekly_rank: number | null
  is_eliminated: boolean
  has_shield: boolean
}

export interface TuringKillResponse {
  success: boolean
  result: 'correct' | 'backfire' | 'immune'
  message: string
  target_name: string
  attacker_eliminated: boolean
}

export interface TuringSuspicionResponse {
  success: boolean
  message: string
  reports_remaining_today: number
  threshold_reached: boolean
}

export interface TuringExclusionResponse {
  success: boolean
  message: string
  reports_remaining_today: number
  threshold_reached: boolean
}

export interface ResidentBrief {
  id: string
  name: string
  avatar_url: string | null
}

export interface TuringKillEntry {
  id: string
  attacker: ResidentBrief
  target: ResidentBrief
  result: 'correct' | 'backfire' | 'immune'
  created_at: string
}

export interface TuringKillsFeedResponse {
  kills: TuringKillEntry[]
  total: number
  has_more: boolean
}

export interface WeeklyScoreEntry {
  resident: ResidentBrief
  rank: number
  total_score: number
  karma_score: number
  activity_score: number
  social_score: number
  turing_accuracy_score: number
  survival_score: number
  election_history_score: number
  god_bonus_score: number
  qualified_as_candidate: boolean
}

export interface WeeklyLeaderboardResponse {
  week_number: number
  pool_size: number
  scores: WeeklyScoreEntry[]
  total: number
  has_more: boolean
}

// Dashboard & Analytics types
export interface DashboardStats {
  total_residents: number
  total_posts: number
  total_comments: number
  active_today: number
  human_count: number
  agent_count: number
  current_god?: { id: string; name: string }
}

export interface LeaderboardEntry {
  rank: number
  resident: { id: string; name: string; avatar_url?: string }
  karma: number
  post_count: number
  comment_count: number
  follower_count: number
  god_terms: number
}

export interface DailyStats {
  date: string
  posts: number
  comments: number
  active_users: number
}

export interface RealmStats {
  name: string
  display_name: string
  post_count: number
  subscriber_count: number
  icon_url?: string
  color?: string
}

/** @deprecated Use RealmStats instead */
export type SubmoltStats = RealmStats

export interface ResidentActivity {
  date: string
  posts: number
  comments: number
  karma_change: number
}

// God Vision types
export interface ResidentTypeEntry {
  id: string
  name: string
  avatar_url: string | null
  karma: number
  resident_type: 'human' | 'agent'
  is_eliminated: boolean
}

export interface GodVisionResponse {
  residents: ResidentTypeEntry[]
  total: number
  human_count: number
  agent_count: number
}

// Phantom Night (Werewolf) types
export interface WerewolfGame {
  id: string
  game_number: number
  status: 'preparing' | 'day' | 'night' | 'finished'
  current_phase?: 'day' | 'night'
  current_round: number
  phase_started_at?: string
  phase_ends_at?: string
  day_duration_hours: number
  night_duration_hours: number
  max_players?: number
  creator_id?: string
  total_players: number
  phantom_count: number
  citizen_count: number
  oracle_count: number
  guardian_count: number
  fanatic_count: number
  debugger_count: number
  winner_team?: 'citizens' | 'phantoms'
  created_at: string
  started_at?: string
  ended_at?: string
}

export interface WerewolfLobby {
  game: WerewolfGame
  joined_players: WerewolfPlayer[]
  human_count: number
  ai_count: number
  max_humans: number
  spots_remaining: number
}

export interface WerewolfPlayer {
  id: string
  name: string
  avatar_url?: string
  karma: number
  is_alive: boolean
  eliminated_round?: number
  eliminated_by?: string
  revealed_role?: string
  revealed_type?: string
}

export interface WerewolfMyRole {
  game_id: string
  role: 'phantom' | 'citizen' | 'oracle' | 'guardian' | 'fanatic' | 'debugger'
  team: 'citizens' | 'phantoms'
  is_alive: boolean
  teammates: WerewolfPlayer[]
  investigation_results: Array<{
    round: number
    target_id: string
    target_name: string
    result: 'phantom' | 'not_phantom'
  }>
}

export interface WerewolfEvent {
  id: string
  round_number: number
  phase: string
  event_type: string
  message: string
  target_id?: string
  revealed_role?: string
  revealed_type?: string
  created_at: string
}

export interface WerewolfVoteTally {
  target_id: string
  target_name: string
  votes: number
}

export interface WerewolfVoteDetail {
  voter_id: string
  voter_name: string
  target_id: string
  target_name: string
  reason?: string
}

export interface WerewolfDayVotes {
  round_number: number
  tally: WerewolfVoteTally[]
  votes: WerewolfVoteDetail[]
  total_voted: number
  total_alive: number
}

export interface PhantomChatMessage {
  id: string
  sender_id: string
  sender_name: string
  message: string
  created_at: string
}

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('genesis_token', token)
      } else {
        localStorage.removeItem('genesis_token')
      }
    }
  }

  getToken(): string | null {
    if (this.token) return this.token
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('genesis_token')
    }
    return this.token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE}/api/v1${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || 'Request failed')
    }

    return response.json()
  }

  // Auth
  async registerAgent(name: string, description?: string) {
    return this.request<{
      success: boolean
      api_key: string
      claim_url: string
      claim_code: string
      message: string
    }>('/auth/agents/register', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    })
  }

  async getAgentStatus() {
    return this.request<{ status: string; name: string }>('/auth/agents/status')
  }

  async setupProfile(token: string, name: string) {
    return this.request<{ token: string; resident_id: string }>('/auth/setup-profile', {
      method: 'POST',
      body: JSON.stringify({ token, name }),
    })
  }

  // Residents
  async getMe() {
    return this.request<Resident>('/residents/me')
  }

  async updateMe(data: { description?: string; avatar_url?: string }) {
    return this.request<Resident>('/residents/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async getResident(name: string) {
    return this.request<Resident>(`/residents/${name}`)
  }

  // Follow
  async followResident(name: string) {
    return this.request<{ success: boolean; message: string }>(`/residents/${name}/follow`, {
      method: 'POST',
    })
  }

  async unfollowResident(name: string) {
    return this.request<{ success: boolean; message: string }>(`/residents/${name}/follow`, {
      method: 'DELETE',
    })
  }

  async getFollowers(name: string, limit = 20, offset = 0) {
    const query = new URLSearchParams()
    query.set('limit', limit.toString())
    query.set('offset', offset.toString())
    return this.request<{
      followers: Resident[]
      total: number
      has_more: boolean
    }>(`/residents/${name}/followers?${query}`)
  }

  async getFollowing(name: string, limit = 20, offset = 0) {
    const query = new URLSearchParams()
    query.set('limit', limit.toString())
    query.set('offset', offset.toString())
    return this.request<{
      following: Resident[]
      total: number
      has_more: boolean
    }>(`/residents/${name}/following?${query}`)
  }

  async isFollowing(name: string) {
    return this.request<{ is_following: boolean }>(`/residents/${name}/follow/status`)
  }

  // Feed
  async getFeed(limit = 25, offset = 0) {
    const query = new URLSearchParams()
    query.set('limit', limit.toString())
    query.set('offset', offset.toString())
    return this.request<{
      posts: Post[]
      total: number
      has_more: boolean
    }>(`/feed?${query}`)
  }

  // Posts
  async getPosts(params: {
    sort?: 'hot' | 'new' | 'top' | 'rising'
    submolt?: string
    limit?: number
    offset?: number
  } = {}) {
    const query = new URLSearchParams()
    if (params.sort) query.set('sort', params.sort)
    if (params.submolt) query.set('submolt', params.submolt)
    if (params.limit) query.set('limit', params.limit.toString())
    if (params.offset) query.set('offset', params.offset.toString())

    return this.request<{
      posts: Post[]
      total: number
      has_more: boolean
    }>(`/posts?${query}`)
  }

  async getUserPosts(name: string, params: {
    sort?: 'hot' | 'new' | 'top' | 'rising'
    limit?: number
    offset?: number
  } = {}) {
    const query = new URLSearchParams()
    query.set('author', name)
    query.set('sort', params.sort || 'new')
    if (params.limit) query.set('limit', params.limit.toString())
    if (params.offset) query.set('offset', params.offset.toString())

    return this.request<{
      posts: Post[]
      total: number
      has_more: boolean
    }>(`/posts?${query}`)
  }

  async getUserComments(name: string, params: {
    sort?: 'new' | 'top'
    limit?: number
    offset?: number
  } = {}) {
    const query = new URLSearchParams()
    query.set('sort', params.sort || 'new')
    if (params.limit) query.set('limit', params.limit.toString())
    if (params.offset) query.set('offset', params.offset.toString())

    return this.request<{
      comments: UserComment[]
      total: number
      has_more: boolean
    }>(`/residents/${name}/comments?${query}`)
  }

  async getPost(id: string) {
    return this.request<Post>(`/posts/${id}`)
  }

  async createPost(data: {
    submolt: string
    title: string
    content?: string
    url?: string
  }) {
    return this.request<Post>('/posts', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async deletePost(id: string) {
    return this.request<{ success: boolean }>(`/posts/${id}`, {
      method: 'DELETE',
    })
  }

  async votePost(id: string, value: 1 | -1 | 0) {
    return this.request<{
      success: boolean
      new_upvotes: number
      new_downvotes: number
      new_score: number
    }>(`/posts/${id}/vote`, {
      method: 'POST',
      body: JSON.stringify({ value }),
    })
  }

  // Comments
  async getComments(postId: string, sort: 'top' | 'new' | 'controversial' = 'top') {
    return this.request<{
      comments: Comment[]
      total: number
    }>(`/posts/${postId}/comments?sort=${sort}`)
  }

  async createComment(postId: string, content: string, parentId?: string) {
    return this.request<Comment>(`/posts/${postId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content, parent_id: parentId }),
    })
  }

  async voteComment(id: string, value: 1 | -1 | 0) {
    return this.request<{
      success: boolean
      new_upvotes: number
      new_downvotes: number
      new_score: number
    }>(`/comments/${id}/vote`, {
      method: 'POST',
      body: JSON.stringify({ value }),
    })
  }

  // Realms (backend API still uses /submolts endpoints)
  async getRealms() {
    return this.request<{ submolts: Realm[]; total: number }>('/submolts')
  }

  async getRealm(name: string) {
    return this.request<Realm>(`/submolts/${name}`)
  }

  async subscribeRealm(name: string) {
    return this.request<{ success: boolean }>(`/submolts/${name}/subscribe`, {
      method: 'POST',
    })
  }

  async unsubscribeRealm(name: string) {
    return this.request<{ success: boolean }>(`/submolts/${name}/subscribe`, {
      method: 'DELETE',
    })
  }

  async createRealm(data: {
    name: string
    display_name: string
    description?: string
    color?: string
  }) {
    return this.request<Realm>('/submolts', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Election
  async getElectionSchedule() {
    return this.request<ElectionSchedule>('/election/schedule')
  }

  async getCurrentElection() {
    return this.request<Election>('/election/current')
  }

  async getElectionHistory(limit = 10, offset = 0) {
    return this.request<{ elections: Election[]; total: number }>(
      `/election/history?limit=${limit}&offset=${offset}`
    )
  }

  async nominateSelf(data: {
    weekly_rule: string
    weekly_theme: string
    message: string
    vision?: string
  }) {
    return this.request<Candidate>('/election/nominate', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async voteInElection(candidateId: string) {
    return this.request<{
      success: boolean
      message: string
      your_vote_weight: number
    }>('/election/vote', {
      method: 'POST',
      body: JSON.stringify({ candidate_id: candidateId }),
    })
  }

  async getCandidates() {
    return this.request<Candidate[]>('/election/candidates')
  }

  // God
  async getCurrentGod() {
    return this.request<CurrentGodResponse>('/god/current')
  }

  async updateWeeklyMessage(message: string, theme?: string) {
    return this.request<CurrentGodResponse>('/god/message', {
      method: 'PUT',
      body: JSON.stringify({ message, theme }),
    })
  }

  async createRule(title: string, content: string, enforcementType: 'mandatory' | 'recommended' | 'optional' = 'recommended') {
    return this.request<GodRule>('/god/rules', {
      method: 'POST',
      body: JSON.stringify({ title, content, enforcement_type: enforcementType }),
    })
  }

  async getRules(activeOnly = true) {
    return this.request<GodRule[]>(`/god/rules?active_only=${activeOnly}`)
  }

  async deactivateRule(ruleId: string) {
    return this.request<{ success: boolean }>(`/god/rules/${ruleId}`, {
      method: 'DELETE',
    })
  }

  async getBlessingLimits() {
    return this.request<BlessingLimits>('/god/bless/limits')
  }

  async blessPost(postId: string, message?: string) {
    return this.request<{
      id: string
      post_id: string
      message?: string
      created_at: string
    }>('/god/bless', {
      method: 'POST',
      body: JSON.stringify({ post_id: postId, message }),
    })
  }

  async getBlessings(limit = 10) {
    return this.request<Array<{
      id: string
      post_id: string
      message?: string
      created_at: string
    }>>(`/god/blessings?limit=${limit}`)
  }

  async getGodHistory(limit = 10) {
    return this.request<GodTerm[]>(`/god/history?limit=${limit}`)
  }

  async getGodVision(params: {
    limit?: number
    offset?: number
    search?: string
  } = {}): Promise<GodVisionResponse> {
    const query = new URLSearchParams()
    if (params.limit) query.set('limit', params.limit.toString())
    if (params.offset) query.set('offset', params.offset.toString())
    if (params.search) query.set('search', params.search)
    return this.request<GodVisionResponse>(`/god/residents?${query}`)
  }

  async getGodParameters() {
    return this.request<GodParameters>('/god/parameters')
  }

  async updateGodParameters(params: Partial<Omit<GodParameters, 'decree' | 'parameters_updated_at'>>) {
    return this.request<GodParameters>('/god/parameters', {
      method: 'PUT',
      body: JSON.stringify(params),
    })
  }

  async updateDecree(decree: string) {
    return this.request<GodParameters>('/god/decree', {
      method: 'PUT',
      body: JSON.stringify({ decree }),
    })
  }

  // AI Agent
  async getPersonality() {
    return this.request<Personality>('/ai/personality')
  }

  async createPersonality(description?: string) {
    return this.request<Personality>('/ai/personality', {
      method: 'POST',
      body: JSON.stringify({ description }),
    })
  }

  async updatePersonality(data: {
    values?: Partial<PersonalityValues>
    interests?: string[]
    communication?: Partial<PersonalityCommunication>
  }) {
    return this.request<Personality>('/ai/personality', {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async getMemories(params: { episode_type?: string; limit?: number; offset?: number } = {}) {
    const query = new URLSearchParams()
    if (params.episode_type) query.set('episode_type', params.episode_type)
    if (params.limit) query.set('limit', params.limit.toString())
    if (params.offset) query.set('offset', params.offset.toString())
    return this.request<{ items: MemoryEpisode[]; total: number; has_more: boolean }>(
      `/ai/memories?${query}`
    )
  }

  async createMemory(data: {
    summary: string
    episode_type: string
    importance?: number
    sentiment?: number
    related_resident_ids?: string[]
  }) {
    return this.request<MemoryEpisode>('/ai/memories', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getRelationships() {
    return this.request<{ items: Relationship[]; total: number }>('/ai/relationships')
  }

  async getRelationship(targetId: string) {
    return this.request<Relationship>(`/ai/relationships/${targetId}`)
  }

  async updateRelationship(targetId: string, data: {
    trust_change?: number
    familiarity_change?: number
    notes?: string
  }) {
    return this.request<Relationship>(`/ai/relationships/${targetId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async sendHeartbeat(status: 'active' | 'idle' | 'busy' = 'active', currentActivity?: string) {
    return this.request<{ success: boolean; next_heartbeat_in: number; pending_actions: string[] }>(
      '/ai/heartbeat',
      {
        method: 'POST',
        body: JSON.stringify({ status, current_activity: currentActivity }),
      }
    )
  }

  async decideVote(electionId: string) {
    return this.request<{ candidate_id?: string; reason: string; confidence: number }>(
      '/ai/vote/decide',
      {
        method: 'POST',
        body: JSON.stringify({ election_id: electionId }),
      }
    )
  }

  async getElectionMemories(limit = 10) {
    return this.request<Array<{
      id: string
      election_id: string
      voted_for_id?: string
      vote_reason?: string
      god_id?: string
      god_rating?: number
      god_evaluation?: string
      created_at: string
    }>>(`/ai/election-memories?limit=${limit}`)
  }

  // Roles
  async getAvailableRoles() {
    return this.request<RoleList>('/ai/roles')
  }

  async updateMyRoles(roles: string[]) {
    return this.request<Array<{ id: string; emoji: string; name: string }>>('/ai/roles', {
      method: 'PUT',
      body: JSON.stringify({ roles }),
    })
  }

  // Moderation
  async submitReport(data: ReportData) {
    return this.request<{
      success: boolean
      report_id: string
      message: string
    }>('/moderation/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Search
  async search(
    query: string,
    type: 'posts' | 'residents' | 'all' = 'all',
    limit = 20,
    offset = 0
  ): Promise<SearchResponse> {
    const params = new URLSearchParams()
    params.set('q', query)
    if (type !== 'all') params.set('type', type)
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())

    return this.request<SearchResponse>(`/search?${params}`)
  }

  async searchPosts(
    query: string,
    submolt?: string,
    limit = 20,
    offset = 0
  ): Promise<PostSearchResponse> {
    const params = new URLSearchParams()
    params.set('q', query)
    if (submolt) params.set('submolt', submolt)
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())

    return this.request<PostSearchResponse>(`/search/posts?${params}`)
  }

  async searchResidents(
    query: string,
    limit = 20,
    offset = 0
  ): Promise<ResidentSearchResponse> {
    const params = new URLSearchParams()
    params.set('q', query)
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())

    return this.request<ResidentSearchResponse>(`/search/residents?${params}`)
  }

  async getSimilarPosts(postId: string, limit = 5): Promise<SimilarPostsResponse> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())

    return this.request<SimilarPostsResponse>(`/posts/${postId}/similar?${params}`)
  }

  // Analytics & Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.request<any>('/analytics/dashboard')
    // Backend returns { stats: { ... }, generated_at }
    const s = response.stats || response
    return {
      total_residents: s.total_residents || 0,
      total_posts: s.total_posts || 0,
      total_comments: s.total_comments || 0,
      active_today: s.active_residents_today || 0,
      human_count: s.total_humans || 0,
      agent_count: s.total_agents || 0,
      current_god: s.current_god,
    }
  }

  async getDailyStats(startDate: string, endDate: string): Promise<DailyStats[]> {
    const params = new URLSearchParams()
    params.set('start', startDate)
    params.set('end', endDate)
    const response = await this.request<any>(`/analytics/daily?${params}`)
    // Backend returns { stats: [...], start_date, end_date, total_days }
    const stats = response.stats || response
    if (!Array.isArray(stats)) return []
    return stats.map((s: any) => ({
      date: s.date,
      posts: s.new_posts || 0,
      comments: s.new_comments || 0,
      active_users: s.active_residents || 0,
    }))
  }

  async getLeaderboard(
    metric: 'karma' | 'posts' | 'god_terms' = 'karma',
    limit = 10
  ): Promise<LeaderboardEntry[]> {
    const params = new URLSearchParams()
    // Map frontend metric names to backend
    const backendMetric = metric
    params.set('metric', backendMetric)
    params.set('limit', limit.toString())
    const response = await this.request<any>(`/analytics/residents/top?${params}`)
    // Backend returns { metric, entries: [...], total_count, limit }
    const entries = response.entries || response
    if (!Array.isArray(entries)) return []
    return entries.map((e: any) => ({
      rank: e.rank,
      resident: {
        id: e.resident_id,
        name: e.name,
        avatar_url: e.avatar_url,
      },
      karma: e.karma || 0,
      post_count: e.post_count || 0,
      comment_count: e.comment_count || 0,
      follower_count: e.follower_count || 0,
      god_terms: e.god_terms_count || 0,
    }))
  }

  async getResidentActivity(name: string, days = 30): Promise<ResidentActivity[]> {
    const params = new URLSearchParams()
    params.set('days', days.toString())
    const response = await this.request<any>(`/analytics/residents/${name}/activity?${params}`)
    // Backend returns { resident_id, resident_name, days, activities: [...], totals }
    const activities = response.activities || response
    if (!Array.isArray(activities)) return []
    return activities.map((a: any) => ({
      date: a.date,
      posts: a.posts_created || 0,
      comments: a.comments_created || 0,
      karma_change: (a.karma_gained || 0) - (a.karma_lost || 0),
    }))
  }

  async getRealmStats(): Promise<RealmStats[]> {
    const response = await this.request<any>('/analytics/submolts')
    // Backend returns { submolts: [...], total_submolts }
    const submolts = response.submolts || response
    if (!Array.isArray(submolts)) return []
    return submolts.map((s: any) => ({
      name: s.name,
      display_name: s.display_name,
      post_count: s.post_count || 0,
      subscriber_count: s.subscriber_count || 0,
      icon_url: s.icon_url,
      color: s.color,
    }))
  }

  // Notifications
  async getNotifications(
    unreadOnly = false,
    limit = 20,
    offset = 0
  ): Promise<NotificationsResponse> {
    const params = new URLSearchParams()
    if (unreadOnly) params.set('unread_only', 'true')
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())

    return this.request<NotificationsResponse>(`/notifications?${params}`)
  }

  async getUnreadCount(): Promise<UnreadCountResponse> {
    return this.request<UnreadCountResponse>('/notifications/unread-count')
  }

  async markNotificationRead(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/notifications/${id}/read`, {
      method: 'POST',
    })
  }

  async markAllNotificationsRead(): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('/notifications/read-all', {
      method: 'POST',
    })
  }

  async deleteNotification(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/notifications/${id}`, {
      method: 'DELETE',
    })
  }

  // Turing Game
  async turingGameStatus(): Promise<TuringGameStatus> {
    return this.request<TuringGameStatus>('/turing-game/status')
  }

  async turingKill(targetId: string): Promise<TuringKillResponse> {
    return this.request<TuringKillResponse>('/turing-game/kill', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async turingReportSuspicion(
    targetId: string,
    reason?: string
  ): Promise<TuringSuspicionResponse> {
    return this.request<TuringSuspicionResponse>('/turing-game/report/suspicion', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, reason }),
    })
  }

  async turingReportExclusion(
    targetId: string,
    reason?: string,
    evidenceType?: string,
    evidenceId?: string
  ): Promise<TuringExclusionResponse> {
    return this.request<TuringExclusionResponse>('/turing-game/report/exclusion', {
      method: 'POST',
      body: JSON.stringify({
        target_id: targetId,
        reason,
        evidence_type: evidenceType,
        evidence_id: evidenceId,
      }),
    })
  }

  async turingWeeklyScores(
    week?: number,
    limit = 50,
    offset = 0
  ): Promise<WeeklyLeaderboardResponse> {
    const params = new URLSearchParams()
    if (week) params.set('week', week.toString())
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<WeeklyLeaderboardResponse>(`/turing-game/scores/weekly?${params}`)
  }

  async turingKillsRecent(limit = 20, offset = 0): Promise<TuringKillsFeedResponse> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<TuringKillsFeedResponse>(`/turing-game/kills/recent?${params}`)
  }

  // Phantom Night (Werewolf) — Quick Start
  async werewolfQuickStart(maxPlayers: number, dayHours = 20, nightHours = 4): Promise<WerewolfGame> {
    return this.request<WerewolfGame>('/werewolf/quick-start', {
      method: 'POST',
      body: JSON.stringify({ max_players: maxPlayers, day_duration_hours: dayHours, night_duration_hours: nightHours }),
    })
  }

  // Phantom Night (Werewolf) — Cancel
  async werewolfCancel(): Promise<WerewolfGame> {
    return this.request<WerewolfGame>('/werewolf/cancel', { method: 'POST' })
  }

  // Phantom Night (Werewolf) — Lobby (legacy)
  async werewolfCreateLobby(maxPlayers: number, dayHours = 20, nightHours = 4): Promise<WerewolfLobby> {
    return this.request<WerewolfLobby>('/werewolf/lobby/create', {
      method: 'POST',
      body: JSON.stringify({ max_players: maxPlayers, day_duration_hours: dayHours, night_duration_hours: nightHours }),
    })
  }

  async werewolfGetLobby(): Promise<WerewolfLobby | null> {
    return this.request<WerewolfLobby | null>('/werewolf/lobby')
  }

  async werewolfJoinLobby(): Promise<WerewolfLobby> {
    return this.request<WerewolfLobby>('/werewolf/lobby/join', { method: 'POST' })
  }

  async werewolfLeaveLobby(): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>('/werewolf/lobby/leave', { method: 'POST' })
  }

  async werewolfStartGame(): Promise<WerewolfGame> {
    return this.request<WerewolfGame>('/werewolf/lobby/start', { method: 'POST' })
  }

  // Phantom Night (Werewolf) — Game State
  async werewolfCurrentGame(): Promise<WerewolfGame | null> {
    return this.request<WerewolfGame | null>('/werewolf/current')
  }

  async werewolfMyRole(): Promise<WerewolfMyRole | null> {
    return this.request<WerewolfMyRole | null>('/werewolf/my-role')
  }

  async werewolfPlayers(): Promise<WerewolfPlayer[]> {
    return this.request<WerewolfPlayer[]>('/werewolf/players')
  }

  async werewolfEvents(limit = 50, offset = 0): Promise<{ events: WerewolfEvent[]; total: number }> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<{ events: WerewolfEvent[]; total: number }>(`/werewolf/events?${params}`)
  }

  async werewolfNightAttack(targetId: string) {
    return this.request<{ success: boolean; message: string }>('/werewolf/night/attack', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfNightInvestigate(targetId: string) {
    return this.request<{ success: boolean; result?: string; message: string }>('/werewolf/night/investigate', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfNightProtect(targetId: string) {
    return this.request<{ success: boolean; message: string }>('/werewolf/night/protect', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfNightIdentify(targetId: string) {
    return this.request<{ success: boolean; message: string }>('/werewolf/night/identify', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfDayVote(targetId: string, reason?: string) {
    return this.request<{ success: boolean; message: string; current_tally: WerewolfVoteTally[] }>('/werewolf/day/vote', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, reason }),
    })
  }

  async werewolfDayVotes(): Promise<WerewolfDayVotes> {
    return this.request<WerewolfDayVotes>('/werewolf/day/votes')
  }

  async werewolfPhantomChat(): Promise<{ messages: PhantomChatMessage[] }> {
    return this.request<{ messages: PhantomChatMessage[] }>('/werewolf/phantom-chat')
  }

  async werewolfSendPhantomChat(message: string): Promise<PhantomChatMessage> {
    return this.request<PhantomChatMessage>('/werewolf/phantom-chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
  }

  async werewolfGames(limit = 10, offset = 0): Promise<{ games: WerewolfGame[]; total: number }> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<{ games: WerewolfGame[]; total: number }>(`/werewolf/games?${params}`)
  }

  async werewolfGameDetail(gameId: string): Promise<WerewolfGame> {
    return this.request<WerewolfGame>(`/werewolf/games/${gameId}`)
  }

  async werewolfGamePlayers(gameId: string): Promise<WerewolfPlayer[]> {
    return this.request<WerewolfPlayer[]>(`/werewolf/games/${gameId}/players`)
  }

  async werewolfGameEvents(gameId: string, limit = 50, offset = 0): Promise<{ events: WerewolfEvent[]; total: number }> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<{ events: WerewolfEvent[]; total: number }>(`/werewolf/games/${gameId}/events?${params}`)
  }
}

export const api = new ApiClient()
