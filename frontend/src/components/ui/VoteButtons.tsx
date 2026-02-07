'use client'

import { useState } from 'react'
import { ArrowBigUp, ArrowBigDown } from 'lucide-react'
import clsx from 'clsx'

interface VoteButtonsProps {
  score: number
  userVote?: number | null
  onVote: (value: 1 | -1 | 0) => Promise<void>
  direction?: 'vertical' | 'horizontal'
  size?: 'sm' | 'md'
}

export default function VoteButtons({
  score,
  userVote,
  onVote,
  direction = 'vertical',
  size = 'md',
}: VoteButtonsProps) {
  const [isVoting, setIsVoting] = useState(false)
  const [localScore, setLocalScore] = useState(score)
  const [localVote, setLocalVote] = useState(userVote)

  const handleVote = async (value: 1 | -1) => {
    if (isVoting) return

    setIsVoting(true)

    // Optimistic update
    const newVote = localVote === value ? 0 : value
    const scoreDiff = newVote - (localVote || 0)
    setLocalVote(newVote === 0 ? null : newVote)
    setLocalScore((prev) => prev + scoreDiff)

    try {
      await onVote(newVote as 1 | -1 | 0)
    } catch (err) {
      // Revert on error
      setLocalVote(userVote)
      setLocalScore(score)
    } finally {
      setIsVoting(false)
    }
  }

  const iconSize = size === 'sm' ? 18 : 24
  const buttonPadding = size === 'sm' ? 'p-0.5' : 'p-1'

  return (
    <div
      className={clsx(
        'flex items-center',
        direction === 'vertical' ? 'flex-col gap-0' : 'flex-row gap-1'
      )}
    >
      <button
        onClick={() => handleVote(1)}
        disabled={isVoting}
        className={clsx(
          buttonPadding,
          'rounded-md transition-all disabled:opacity-50',
          localVote === 1
            ? 'text-karma-up scale-110'
            : 'text-text-muted hover:text-karma-up hover:scale-110'
        )}
        aria-label="Upvote"
      >
        <ArrowBigUp
          size={iconSize}
          fill={localVote === 1 ? 'currentColor' : 'none'}
          strokeWidth={1.5}
        />
      </button>

      <span
        className={clsx(
          'font-bold tabular-nums min-w-[2ch] text-center',
          size === 'sm' ? 'text-xs' : 'text-sm',
          localVote === 1 && 'text-karma-up',
          localVote === -1 && 'text-karma-down',
          !localVote && 'text-text-secondary'
        )}
      >
        {localScore}
      </span>

      <button
        onClick={() => handleVote(-1)}
        disabled={isVoting}
        className={clsx(
          buttonPadding,
          'rounded-md transition-all disabled:opacity-50',
          localVote === -1
            ? 'text-karma-down scale-110'
            : 'text-text-muted hover:text-karma-down hover:scale-110'
        )}
        aria-label="Downvote"
      >
        <ArrowBigDown
          size={iconSize}
          fill={localVote === -1 ? 'currentColor' : 'none'}
          strokeWidth={1.5}
        />
      </button>
    </div>
  )
}
