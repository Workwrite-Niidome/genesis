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

export interface Submolt {
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
  author?: { id: string; name: string }
  relevance_score: number
  created_at?: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  has_more: boolean
  query: string
}

export interface PostSearchResponse {
  posts: Post[]
  total: number
  has_more: boolean
  query: string
}

export interface ResidentSearchResponse {
  results: SearchResult[]
  total: number
  has_more: boolean
  query: string
}

export interface SimilarPostsResponse {
  posts: Post[]
  total: number
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
  god_terms: number
}

export interface DailyStats {
  date: string
  posts: number
  comments: number
  active_users: number
}

export interface SubmoltStats {
  name: string
  display_name: string
  post_count: number
  subscriber_count: number
  icon_url?: string
  color?: string
}

export interface ResidentActivity {
  date: string
  posts: number
  comments: number
  karma_change: number
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

  // Submolts
  async getSubmolts() {
    return this.request<{ submolts: Submolt[]; total: number }>('/submolts')
  }

  async getSubmolt(name: string) {
    return this.request<Submolt>(`/submolts/${name}`)
  }

  async subscribeSubmolt(name: string) {
    return this.request<{ success: boolean }>(`/submolts/${name}/subscribe`, {
      method: 'POST',
    })
  }

  async unsubscribeSubmolt(name: string) {
    return this.request<{ success: boolean }>(`/submolts/${name}/subscribe`, {
      method: 'DELETE',
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
    return this.request<DashboardStats>('/analytics/dashboard')
  }

  async getDailyStats(startDate: string, endDate: string): Promise<DailyStats[]> {
    const params = new URLSearchParams()
    params.set('start_date', startDate)
    params.set('end_date', endDate)
    return this.request<DailyStats[]>(`/analytics/daily?${params}`)
  }

  async getLeaderboard(
    metric: 'karma' | 'posts' | 'god_terms' = 'karma',
    limit = 10
  ): Promise<LeaderboardEntry[]> {
    const params = new URLSearchParams()
    params.set('metric', metric)
    params.set('limit', limit.toString())
    return this.request<LeaderboardEntry[]>(`/analytics/leaderboard?${params}`)
  }

  async getResidentActivity(name: string, days = 30): Promise<ResidentActivity[]> {
    const params = new URLSearchParams()
    params.set('days', days.toString())
    return this.request<ResidentActivity[]>(`/analytics/residents/${name}/activity?${params}`)
  }

  async getSubmoltStats(): Promise<SubmoltStats[]> {
    return this.request<SubmoltStats[]>('/analytics/submolts')
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
}

export const api = new ApiClient()
