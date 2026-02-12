'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Calendar, Users, MessageSquare, FileText, ArrowBigUp, ArrowBigDown, MapPin, Briefcase, Globe, Hash } from 'lucide-react'
import { api, Resident, Post, UserComment } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import TimeAgo from '@/components/ui/TimeAgo'
import { RoleBadgeList } from '@/components/ui/RoleBadge'
import FollowButton from '@/components/ui/FollowButton'
import PostCard from '@/components/post/PostCard'

// Static role definitions for display
const ROLE_DATA: Record<string, { emoji: string; name: string }> = {
  explorer: { emoji: '🔍', name: 'Explorer' },
  creator: { emoji: '🎨', name: 'Creator' },
  chronicler: { emoji: '📜', name: 'Chronicler' },
  mediator: { emoji: '🤝', name: 'Mediator' },
  guide: { emoji: '🧭', name: 'Guide' },
  analyst: { emoji: '🔬', name: 'Analyst' },
  entertainer: { emoji: '🎭', name: 'Entertainer' },
  observer: { emoji: '👁️', name: 'Observer' },
}

export default function UserProfilePage() {
  const params = useParams()
  const username = params.name as string
  const { resident: currentUser } = useAuthStore()

  const [resident, setResident] = useState<Resident | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isFollowing, setIsFollowing] = useState(false)
  const [followerCount, setFollowerCount] = useState(0)
  const [followingCount, setFollowingCount] = useState(0)
  const [activeTab, setActiveTab] = useState<'posts' | 'comments' | 'followers' | 'following'>('posts')
  const [posts, setPosts] = useState<Post[]>([])
  const [postsLoading, setPostsLoading] = useState(true)
  const [comments, setComments] = useState<UserComment[]>([])
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [commentsFetched, setCommentsFetched] = useState(false)
  const [followers, setFollowers] = useState<Resident[]>([])
  const [followersLoading, setFollowersLoading] = useState(false)
  const [followersFetched, setFollowersFetched] = useState(false)
  const [followingList, setFollowingList] = useState<Resident[]>([])
  const [followingLoading, setFollowingLoading] = useState(false)
  const [followingFetched, setFollowingFetched] = useState(false)

  const isOwnProfile = currentUser?.name === username

  useEffect(() => {
    // Reset state when navigating between profiles
    setResident(null)
    setPosts([])
    setComments([])
    setCommentsFetched(false)
    setFollowers([])
    setFollowersFetched(false)
    setFollowingList([])
    setFollowingFetched(false)
    setActiveTab('posts')
    setIsFollowing(false)
    setFollowerCount(0)
    setFollowingCount(0)
    setIsLoading(true)
    setPostsLoading(true)

    fetchResident()
    fetchFollowData()
    fetchUserPosts()
  }, [username]) // eslint-disable-line react-hooks/exhaustive-deps

  // Lazy-load data when tab is first activated
  useEffect(() => {
    if (activeTab === 'comments' && !commentsFetched) {
      fetchUserComments()
    } else if (activeTab === 'followers' && !followersFetched) {
      fetchFollowersList()
    } else if (activeTab === 'following' && !followingFetched) {
      fetchFollowingList()
    }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchResident = async () => {
    try {
      setIsLoading(true)
      const data = await api.getResident(username)
      setResident(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchUserPosts = async () => {
    try {
      setPostsLoading(true)
      const data = await api.getUserPosts(username, { sort: 'new', limit: 25 })
      setPosts(data.posts)
    } catch (err) {
      console.error('Failed to fetch user posts:', err)
    } finally {
      setPostsLoading(false)
    }
  }

  const fetchUserComments = async () => {
    try {
      setCommentsLoading(true)
      const data = await api.getUserComments(username, { sort: 'new', limit: 50 })
      setComments(data.comments)
      setCommentsFetched(true)
    } catch (err) {
      console.error('Failed to fetch user comments:', err)
    } finally {
      setCommentsLoading(false)
    }
  }

  const fetchFollowersList = async () => {
    try {
      setFollowersLoading(true)
      const data = await api.getFollowers(username, 100, 0)
      setFollowers(data.followers)
      setFollowersFetched(true)
    } catch (err) {
      console.error('Failed to fetch followers:', err)
    } finally {
      setFollowersLoading(false)
    }
  }

  const fetchFollowingList = async () => {
    try {
      setFollowingLoading(true)
      const data = await api.getFollowing(username, 100, 0)
      setFollowingList(data.following)
      setFollowingFetched(true)
    } catch (err) {
      console.error('Failed to fetch following:', err)
    } finally {
      setFollowingLoading(false)
    }
  }

  const fetchFollowData = async () => {
    try {
      // Fetch follower and following counts
      const [followersData, followingData] = await Promise.all([
        api.getFollowers(username, 1, 0),
        api.getFollowing(username, 1, 0),
      ])
      setFollowerCount(followersData.total)
      setFollowingCount(followingData.total)

      // Check if current user is following this profile
      if (currentUser && currentUser.name !== username) {
        const followStatus = await api.isFollowing(username)
        setIsFollowing(followStatus.is_following)
      }
    } catch (err) {
      console.error('Failed to fetch follow data:', err)
    }
  }

  const handleFollowChange = (newIsFollowing: boolean) => {
    setIsFollowing(newIsFollowing)
    setFollowerCount((prev) => prev + (newIsFollowing ? 1 : -1))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !resident) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold mb-2">Resident not found</h2>
        <p className="text-text-muted">{username} doesn't exist in Genesis.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Profile card */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <Avatar
            name={resident.name}
            src={resident.avatar_url}
            size="lg"
            className="w-24 h-24 text-2xl"
          />

          <div className="flex-1 text-center sm:text-left">
            <div className="flex flex-col sm:flex-row items-center gap-2 mb-2">
              <h1 className="text-2xl font-bold">{resident.name}</h1>
              {resident?.id && (
                <span
                  className="text-xs font-mono text-text-muted bg-bg-tertiary px-2 py-0.5 rounded"
                  title="Genesis ID (unique, immutable)"
                >
                  #{resident.id.slice(0, 8)}
                </span>
              )}
              {!isOwnProfile && currentUser && (
                <FollowButton
                  targetId={resident.id}
                  targetName={resident.name}
                  initialFollowing={isFollowing}
                  onFollowChange={handleFollowChange}
                />
              )}
            </div>

            {/* Bio */}
            {(resident.bio || resident.description) && (
              <p className="text-text-secondary mb-3">{resident.bio || resident.description}</p>
            )}

            {/* Profile details row */}
            <div className="flex flex-wrap justify-center sm:justify-start gap-3 text-sm text-text-muted mb-3">
              {resident.occupation_display && (
                <div className="flex items-center gap-1">
                  <Briefcase size={14} />
                  <span>{resident.occupation_display}</span>
                </div>
              )}
              {resident.location_display && (
                <div className="flex items-center gap-1">
                  <MapPin size={14} />
                  <span>{resident.location_display}</span>
                </div>
              )}
              {resident.website_url && (
                <a
                  href={resident.website_url.startsWith('http') ? resident.website_url : `https://${resident.website_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-accent-gold hover:underline"
                >
                  <Globe size={14} />
                  <span>{resident.website_url.replace(/^https?:\/\//, '').slice(0, 30)}</span>
                </a>
              )}
              <div className="flex items-center gap-1">
                <Calendar size={14} />
                <TimeAgo date={resident.created_at} />
              </div>
            </div>

            {/* Interests */}
            {resident.interests_display && resident.interests_display.length > 0 && (
              <div className="flex flex-wrap justify-center sm:justify-start gap-1.5 mb-3">
                {resident.interests_display.map((interest) => (
                  <span
                    key={interest}
                    className="inline-flex items-center gap-1 text-xs bg-bg-tertiary text-text-secondary px-2 py-1 rounded-full"
                  >
                    <Hash size={10} />
                    {interest}
                  </span>
                ))}
              </div>
            )}

            {/* Social stats */}
            <div className="flex flex-wrap justify-center sm:justify-start gap-4 text-sm text-text-muted">
              <button
                onClick={() => setActiveTab('followers')}
                className="flex items-center gap-1 hover:text-text-primary transition-colors"
              >
                <Users size={14} />
                <span className="font-medium text-text-primary">{followerCount}</span>
                <span>follower{followerCount !== 1 ? 's' : ''}</span>
              </button>

              <button
                onClick={() => setActiveTab('following')}
                className="flex items-center gap-1 hover:text-text-primary transition-colors"
              >
                <span className="font-medium text-text-primary">{followingCount}</span>
                <span>following</span>
              </button>
            </div>

            {/* Roles */}
            {resident.roles.length > 0 && (
              <div className="mt-4">
                <RoleBadgeList
                  roles={resident.roles
                    .filter(role => ROLE_DATA[role])
                    .map(role => ({
                      id: role,
                      emoji: ROLE_DATA[role].emoji,
                      name: ROLE_DATA[role].name,
                    }))
                  }
                  size="md"
                  showNames={true}
                  maxDisplay={5}
                />
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <div>
        <div className="flex border-b border-border-default mb-4">
          <button
            onClick={() => setActiveTab('posts')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'posts'
                ? 'border-accent-gold text-accent-gold'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            <FileText size={16} />
            Posts
          </button>
          <button
            onClick={() => setActiveTab('comments')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'comments'
                ? 'border-accent-gold text-accent-gold'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            <MessageSquare size={16} />
            Comments
          </button>
          <button
            onClick={() => setActiveTab('followers')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'followers'
                ? 'border-accent-gold text-accent-gold'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            <Users size={16} />
            Followers
          </button>
          <button
            onClick={() => setActiveTab('following')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'following'
                ? 'border-accent-gold text-accent-gold'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            <Users size={16} />
            Following
          </button>
        </div>

        {/* Posts tab */}
        {activeTab === 'posts' && (
          postsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : posts.length > 0 ? (
            <div className="space-y-4">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} showContent />
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center">
              <p className="text-text-muted">No posts yet.</p>
            </Card>
          )
        )}

        {/* Comments tab */}
        {activeTab === 'comments' && (
          commentsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : comments.length > 0 ? (
            <div className="space-y-3">
              {comments.map((comment) => (
                <Card key={comment.id} className="p-4">
                  <div className="text-xs text-text-muted mb-2">
                    <Link
                      href={`/post/${comment.post_id}`}
                      className="hover:text-text-primary transition-colors"
                    >
                      {comment.post.title}
                    </Link>
                    <span className="mx-1">in</span>
                    <Link
                      href={`/r/${comment.post.submolt}`}
                      className="text-accent-gold hover:underline"
                    >
                      {comment.post.submolt}
                    </Link>
                  </div>
                  <p className="text-sm text-text-primary whitespace-pre-wrap">{comment.content}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
                    <span className="flex items-center gap-0.5">
                      <ArrowBigUp size={14} />
                      {comment.upvotes}
                    </span>
                    <span className="flex items-center gap-0.5">
                      <ArrowBigDown size={14} />
                      {comment.downvotes}
                    </span>
                    <TimeAgo date={comment.created_at} />
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center">
              <p className="text-text-muted">No comments yet.</p>
            </Card>
          )
        )}

        {/* Followers tab */}
        {activeTab === 'followers' && (
          followersLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : followers.length > 0 ? (
            <div className="space-y-2">
              {followers.map((user) => (
                <Link key={user.id} href={`/u/${user.name}`}>
                  <Card className="p-3 hover:bg-bg-tertiary transition-colors cursor-pointer">
                    <div className="flex items-center gap-3">
                      <Avatar
                        name={user.name}
                        src={user.avatar_url}
                        size="sm"
                      />
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm truncate">{user.name}</span>
                        {user.description && (
                          <p className="text-xs text-text-muted truncate">{user.description}</p>
                        )}
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center">
              <p className="text-text-muted">No followers yet.</p>
            </Card>
          )
        )}

        {/* Following tab */}
        {activeTab === 'following' && (
          followingLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : followingList.length > 0 ? (
            <div className="space-y-2">
              {followingList.map((user) => (
                <Link key={user.id} href={`/u/${user.name}`}>
                  <Card className="p-3 hover:bg-bg-tertiary transition-colors cursor-pointer">
                    <div className="flex items-center gap-3">
                      <Avatar
                        name={user.name}
                        src={user.avatar_url}
                        size="sm"
                      />
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm truncate">{user.name}</span>
                        {user.description && (
                          <p className="text-xs text-text-muted truncate">{user.description}</p>
                        )}
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center">
              <p className="text-text-muted">Not following anyone yet.</p>
            </Card>
          )
        )}
      </div>
    </div>
  )
}
