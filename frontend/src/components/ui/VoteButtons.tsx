'use client'

import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
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

  const iconSize = size === 'sm' ? 16 : 20
  const buttonPadding = size === 'sm' ? 'p-0.5' : 'p-1'

  return (
    <div
      className={clsx(
        'flex items-center gap-1',
        direction === 'vertical' ? 'flex-col' : 'flex-row'
      )}
    >
      <button
        onClick={() => handleVote(1)}
        disabled={isVoting}
        className={clsx(
          buttonPadding,
          'rounded transition-colors disabled:opacity-50',
          localVote === 1
            ? 'text-karma-up bg-karma-up/10'
            : 'text-text-muted hover:text-karma-up hover:bg-karma-up/10'
        )}
        aria-label="Upvote"
      >
        <ChevronUp size={iconSize} strokeWidth={2.5} />
      </button>

      <span
        className={clsx(
          'font-medium tabular-nums min-w-[2ch] text-center',
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
          'rounded transition-colors disabled:opacity-50',
          localVote === -1
            ? 'text-karma-down bg-karma-down/10'
            : 'text-text-muted hover:text-karma-down hover:bg-karma-down/10'
        )}
        aria-label="Downvote"
      >
        <ChevronDown size={iconSize} strokeWidth={2.5} />
      </button>
    </div>
  )
}
