'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import Button from './Button'

interface FollowButtonProps {
  targetId: string
  targetName: string
  initialFollowing: boolean
  onFollowChange?: (isFollowing: boolean) => void
}

export default function FollowButton({
  targetId,
  targetName,
  initialFollowing,
  onFollowChange,
}: FollowButtonProps) {
  const [isFollowing, setIsFollowing] = useState(initialFollowing)
  const [isLoading, setIsLoading] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  const handleClick = async () => {
    try {
      setIsLoading(true)
      if (isFollowing) {
        await api.unfollowResident(targetName)
        setIsFollowing(false)
        onFollowChange?.(false)
      } else {
        await api.followResident(targetName)
        setIsFollowing(true)
        onFollowChange?.(true)
      }
    } catch (err) {
      console.error('Follow action failed:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getButtonText = () => {
    if (isLoading) return 'Loading...'
    if (isFollowing && isHovered) return 'Unfollow'
    if (isFollowing) return 'Following'
    return 'Follow'
  }

  const getVariant = () => {
    if (isFollowing && isHovered) return 'secondary'
    if (isFollowing) return 'secondary'
    return 'primary'
  }

  return (
    <Button
      variant={getVariant()}
      size="sm"
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      isLoading={isLoading}
      className={
        isFollowing && isHovered
          ? 'border-red-500 text-red-500 hover:bg-red-500/10'
          : isFollowing
          ? 'border-accent-gold text-accent-gold'
          : ''
      }
    >
      {getButtonText()}
    </Button>
  )
}
