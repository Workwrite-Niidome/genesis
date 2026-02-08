'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Crown, Calendar, Sparkles, Users, Hash } from 'lucide-react'
import { api, Resident, Post } from '@/lib/api'
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
  god: { emoji: '👑', name: 'God' },
  ex_god: { emoji: '✨', name: 'Ex-God' },
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
  const [posts, setPosts] = useState<Post[]>([])
  const [postsLoading, setPostsLoading] = useState(true)

  const isOwnProfile = currentUser?.name === username

  useEffect(() => {
    fetchResident()
    fetchFollowData()
    fetchUserPosts()
  }, [username])

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
      <Card variant={resident.is_current_god ? 'god' : 'default'} className="p-6">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <Avatar
            name={resident.name}
            src={resident.avatar_url}
            size="lg"
            isGod={resident.is_current_god}
            className="w-24 h-24 text-2xl"
          />

          <div className="flex-1 text-center sm:text-left">
            <div className="flex flex-col sm:flex-row items-center gap-2 mb-2">
              <h1 className="text-2xl font-bold">{resident.name}</h1>
              <span
                className="text-xs font-mono text-text-muted bg-bg-tertiary px-2 py-0.5 rounded"
                title="Genesis ID (unique, immutable)"
              >
                #{resident.id.slice(0, 8)}
              </span>
              {resident.is_current_god && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-god-glow/20 text-god-glow rounded-full text-sm">
                  <Crown size={14} />
                  Current God
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

            {resident.description && (
              <p className="text-text-secondary mb-4">{resident.description}</p>
            )}

            <div className="flex flex-wrap justify-center sm:justify-start gap-4 text-sm text-text-muted">
              <div className="flex items-center gap-1">
                <Sparkles size={14} className="text-accent-gold" />
                <span className="font-medium text-text-primary">{resident.karma}</span>
                <span>karma</span>
              </div>

              <div className="flex items-center gap-1">
                <Calendar size={14} />
                <TimeAgo date={resident.created_at} />
              </div>

              {resident.god_terms_count > 0 && (
                <div className="flex items-center gap-1">
                  <Crown size={14} className="text-god-glow" />
                  <span className="font-medium text-god-glow">{resident.god_terms_count}</span>
                  <span>God term{resident.god_terms_count > 1 ? 's' : ''}</span>
                </div>
              )}

              <div className="flex items-center gap-1">
                <Users size={14} />
                <span className="font-medium text-text-primary">{followerCount}</span>
                <span>follower{followerCount !== 1 ? 's' : ''}</span>
              </div>

              <div className="flex items-center gap-1">
                <span className="font-medium text-text-primary">{followingCount}</span>
                <span>following</span>
              </div>
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

      {/* Posts section */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Posts</h2>
        {postsLoading ? (
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
        )}
      </div>
    </div>
  )
}
