'use client'

import { forwardRef, HTMLAttributes } from 'react'
import clsx from 'clsx'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'blessed' | 'god'
  hoverable?: boolean
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', hoverable = false, children, ...props }, ref) => {
    const baseStyles = 'rounded-lg border transition-all duration-200'

    const variants = {
      default: 'bg-bg-secondary border-border-default',
      blessed:
        'bg-bg-secondary border-god-glow blessed shadow-god-glow',
      god: 'bg-gradient-to-br from-bg-secondary to-bg-tertiary border-god-glow god-glow',
    }

    const hoverStyles = hoverable
      ? 'hover:bg-bg-tertiary hover:border-border-hover hover:shadow-card-hover cursor-pointer'
      : ''

    return (
      <div
        ref={ref}
        className={clsx(baseStyles, variants[variant], hoverStyles, className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export default Card
