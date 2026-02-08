'use client'

import Link from 'next/link'
import { Fragment } from 'react'

const MENTION_RE = /(?<!\w)@([A-Za-z0-9_-]{1,30})(?!\w)/g

interface MentionTextProps {
  text: string
  className?: string
}

/**
 * Renders text with @username mentions as clickable links to user profiles.
 */
export default function MentionText({ text, className }: MentionTextProps) {
  const parts: (string | { username: string; key: number })[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  // Reset regex state
  MENTION_RE.lastIndex = 0

  while ((match = MENTION_RE.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    parts.push({ username: match[1], key: key++ })
    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  // If no mentions found, return plain text
  if (parts.length === 1 && typeof parts[0] === 'string') {
    return <span className={className}>{text}</span>
  }

  return (
    <span className={className}>
      {parts.map((part, i) =>
        typeof part === 'string' ? (
          <Fragment key={i}>{part}</Fragment>
        ) : (
          <Link
            key={`mention-${part.key}`}
            href={`/u/${part.username}`}
            className="text-accent-gold hover:underline font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            @{part.username}
          </Link>
        )
      )}
    </span>
  )
}
