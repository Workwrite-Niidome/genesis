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
  roles: string[]
  bio?: string
  interests_display?: string[]
  favorite_things?: string[]
  location_display?: string
  occupation_display?: string
  website_url?: string
  struct_type?: string
  struct_axes?: number[]
  created_at: string
  last_active?: string
}

export interface Author {
  id: string
  name: string
  avatar_url?: string
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

// Recent Residents
export interface RecentResident {
  id: string
  name: string
  avatar_url?: string
  created_at: string
}

// Dashboard & Analytics types
export interface DashboardStats {
  total_residents: number
  total_posts: number
  total_comments: number
  active_today: number
}

export interface LeaderboardEntry {
  rank: number
  resident: { id: string; name: string; avatar_url?: string }
  post_count: number
  comment_count: number
  follower_count: number
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
  current_player_count?: number
  speed?: 'quick' | 'standard' | 'extended'
}

export interface WerewolfLobbyPlayer {
  id: string
  name: string
  avatar_url?: string
}

export interface WerewolfLobby {
  id: string
  game_number: number
  max_players?: number
  speed?: string
  creator_id?: string
  creator_name?: string
  current_player_count: number
  human_cap: number
  players: WerewolfLobbyPlayer[]
  created_at: string
}

export interface WerewolfPlayer {
  id: string
  name: string
  avatar_url?: string
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

  async updateMe(data: {
    description?: string;
    avatar_url?: string;
    bio?: string;
    interests_display?: string[];
    favorite_things?: string[];
    location_display?: string;
    occupation_display?: string;
    website_url?: string;
  }) {
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
    }
  }

  async getRecentResidents(limit = 20): Promise<RecentResident[]> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    const response = await this.request<any>(`/analytics/residents/recent?${params}`)
    return response.residents || []
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
    metric: 'posts' = 'posts',
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
      post_count: e.post_count || 0,
      comment_count: e.comment_count || 0,
      follower_count: e.follower_count || 0,
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
    return this.request<UnreadCountResponse>('/notifications/unread/count')
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

  // Phantom Night (Werewolf) — Quick Start
  async werewolfQuickStart(maxPlayers: number, dayHours = 20, nightHours = 4): Promise<WerewolfGame> {
    return this.request<WerewolfGame>('/phantomnight/quick-start', {
      method: 'POST',
      body: JSON.stringify({ max_players: maxPlayers, day_duration_hours: dayHours, night_duration_hours: nightHours }),
    })
  }

  // Phantom Night (Werewolf) — Lobby Matchmaking
  async werewolfCreateGame(maxPlayers: number, speed: string = 'standard'): Promise<WerewolfGame> {
    return this.request<WerewolfGame>('/phantomnight/create', {
      method: 'POST',
      body: JSON.stringify({ max_players: maxPlayers, speed }),
    })
  }

  async werewolfJoinGame(gameId: string): Promise<WerewolfGame> {
    return this.request<WerewolfGame>(`/phantomnight/${gameId}/join`, { method: 'POST' })
  }

  async werewolfLeaveGame(gameId: string): Promise<WerewolfGame> {
    return this.request<WerewolfGame>(`/phantomnight/${gameId}/leave`, { method: 'POST' })
  }

  async werewolfStartGame(gameId: string): Promise<WerewolfGame> {
    return this.request<WerewolfGame>(`/phantomnight/${gameId}/start`, { method: 'POST' })
  }

  async werewolfGetLobbies(): Promise<WerewolfLobby[]> {
    return this.request<WerewolfLobby[]>('/phantomnight/lobbies')
  }

  // Phantom Night (Werewolf) — Cancel
  async werewolfCancel(): Promise<WerewolfGame> {
    return this.request<WerewolfGame>('/phantomnight/cancel', { method: 'POST' })
  }

  // Phantom Night (Werewolf) — Game State
  async werewolfCurrentGame(): Promise<WerewolfGame | null> {
    return this.request<WerewolfGame | null>('/phantomnight/current')
  }

  async werewolfMyRole(): Promise<WerewolfMyRole | null> {
    return this.request<WerewolfMyRole | null>('/phantomnight/my-role')
  }

  async werewolfPlayers(): Promise<WerewolfPlayer[]> {
    return this.request<WerewolfPlayer[]>('/phantomnight/players')
  }

  async werewolfEvents(limit = 50, offset = 0): Promise<{ events: WerewolfEvent[]; total: number }> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<{ events: WerewolfEvent[]; total: number }>(`/phantomnight/events?${params}`)
  }

  async werewolfNightAttack(targetId: string) {
    return this.request<{ success: boolean; message: string }>('/phantomnight/night/attack', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfNightInvestigate(targetId: string) {
    return this.request<{ success: boolean; result?: string; message: string }>('/phantomnight/night/investigate', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfNightProtect(targetId: string) {
    return this.request<{ success: boolean; message: string }>('/phantomnight/night/protect', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfNightIdentify(targetId: string) {
    return this.request<{ success: boolean; message: string }>('/phantomnight/night/identify', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId }),
    })
  }

  async werewolfDayVote(targetId: string, reason?: string) {
    return this.request<{ success: boolean; message: string; current_tally: WerewolfVoteTally[] }>('/phantomnight/day/vote', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, reason }),
    })
  }

  async werewolfDayVotes(): Promise<WerewolfDayVotes> {
    return this.request<WerewolfDayVotes>('/phantomnight/day/votes')
  }

  async werewolfPhantomChat(): Promise<{ messages: PhantomChatMessage[] }> {
    return this.request<{ messages: PhantomChatMessage[] }>('/phantomnight/phantom-chat')
  }

  async werewolfSendPhantomChat(message: string): Promise<PhantomChatMessage> {
    return this.request<PhantomChatMessage>('/phantomnight/phantom-chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
  }

  async werewolfGames(limit = 10, offset = 0): Promise<{ games: WerewolfGame[]; total: number }> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<{ games: WerewolfGame[]; total: number }>(`/phantomnight/games?${params}`)
  }

  async werewolfGameDetail(gameId: string): Promise<WerewolfGame> {
    return this.request<WerewolfGame>(`/phantomnight/games/${gameId}`)
  }

  async werewolfGamePlayers(gameId: string): Promise<WerewolfPlayer[]> {
    return this.request<WerewolfPlayer[]>(`/phantomnight/games/${gameId}/players`)
  }

  async werewolfGameEvents(gameId: string, limit = 50, offset = 0): Promise<{ events: WerewolfEvent[]; total: number }> {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return this.request<{ events: WerewolfEvent[]; total: number }>(`/phantomnight/games/${gameId}/events?${params}`)
  }
}

  // ═══════════════════════════════════════════════════════════════
  // STRUCT CODE
  // ═══════════════════════════════════════════════════════════════

  async structCodeQuestions(): Promise<StructCodeQuestion[]> {
    return this.request<StructCodeQuestion[]>('/struct-code/questions')
  }

  async structCodeDiagnose(data: StructCodeDiagnoseRequest): Promise<StructCodeResult> {
    return this.request<StructCodeResult>('/struct-code/diagnose', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async structCodeTypes(): Promise<StructCodeTypeSummary[]> {
    return this.request<StructCodeTypeSummary[]>('/struct-code/types')
  }

  async structCodeType(code: string): Promise<StructCodeTypeInfo> {
    return this.request<StructCodeTypeInfo>(`/struct-code/types/${code}`)
  }

  async structCodeConsult(question: string): Promise<StructCodeConsultResponse> {
    return this.request<StructCodeConsultResponse>('/struct-code/consultation', {
      method: 'POST',
      body: JSON.stringify({ question }),
    })
  }
}

// STRUCT CODE types
export interface StructCodeQuestion {
  id: string
  axis: string
  question: string
  choices: Record<string, { text: string }>
}

export interface StructCodeDiagnoseRequest {
  birth_date: string
  birth_location: string
  answers: { question_id: string; choice: string }[]
}

export interface StructCodeTypeSummary {
  code: string
  name: string
  archetype: string
}

export interface StructCodeTypeInfo {
  code: string
  name: string
  archetype: string
  description: string
  decision_making_style: string
  choice_pattern: string
  blindspot: string
  interpersonal_dynamics: string
  growth_path: string
}

export interface StructCodeResult {
  struct_type: string
  type_info: StructCodeTypeInfo
  axes: number[]
  top_candidates: { code: string; name: string; score: number }[]
  similarity: number
}

export interface StructCodeConsultResponse {
  answer: string
  remaining_today: number
}

export const api = new ApiClient()
