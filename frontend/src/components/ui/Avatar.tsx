'use client'

import { forwardRef, ImgHTMLAttributes } from 'react'
import clsx from 'clsx'

interface AvatarProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  src?: string | null
  name: string
  size?: 'sm' | 'md' | 'lg'
}

function getInitials(name: string): string {
  return name
    .split(/[-_\s]/)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getColorFromName(name: string): string {
  const colors = [
    'bg-realm-general',
    'bg-realm-creations',
    'bg-realm-thoughts',
    'bg-realm-questions',
    'bg-purple-500',
    'bg-pink-500',
    'bg-indigo-500',
    'bg-cyan-500',
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, src, name, size = 'md', ...props }, ref) => {
    const sizes = {
      sm: 'w-6 h-6 text-xs',
      md: 'w-8 h-8 text-sm',
      lg: 'w-12 h-12 text-base',
    }

    const baseStyles =
      'inline-flex items-center justify-center rounded-full font-medium overflow-hidden flex-shrink-0'

    if (src) {
      return (
        <div
          ref={ref}
          className={clsx(baseStyles, sizes[size], className)}
        >
          <img
            src={src}
            alt={name}
            className="w-full h-full object-cover"
            {...props}
          />
        </div>
      )
    }

    return (
      <div
        ref={ref}
        className={clsx(
          baseStyles,
          sizes[size],
          getColorFromName(name),
          'text-white',
          className
        )}
      >
        {getInitials(name)}
      </div>
    )
  }
)

Avatar.displayName = 'Avatar'

export default Avatar
