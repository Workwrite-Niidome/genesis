'use client'

interface RoleBadgeProps {
  role: {
    id: string
    emoji: string
    name: string
  }
  size?: 'sm' | 'md'
  showName?: boolean
}

// Role color mapping
const ROLE_COLORS: Record<string, string> = {
  explorer: 'bg-blue-500/20 border-blue-500/40 text-blue-400',
  creator: 'bg-pink-500/20 border-pink-500/40 text-pink-400',
  chronicler: 'bg-amber-500/20 border-amber-500/40 text-amber-400',
  mediator: 'bg-green-500/20 border-green-500/40 text-green-400',
  guide: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400',
  analyst: 'bg-purple-500/20 border-purple-500/40 text-purple-400',
  entertainer: 'bg-orange-500/20 border-orange-500/40 text-orange-400',
  observer: 'bg-gray-500/20 border-gray-500/40 text-gray-400',
  // Special roles
  god: 'bg-genesis-gold/20 border-genesis-gold/40 text-genesis-gold',
  ex_god: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400',
}

const DEFAULT_COLOR = 'bg-genesis-tertiary border-genesis-border text-genesis-secondary'

export default function RoleBadge({ role, size = 'md', showName = true }: RoleBadgeProps) {
  const colorClass = ROLE_COLORS[role.id] || DEFAULT_COLOR
  const sizeClass = size === 'sm'
    ? 'px-1.5 py-0.5 text-xs gap-1'
    : 'px-2 py-1 text-sm gap-1.5'

  return (
    <span
      className={`
        inline-flex items-center rounded-md border font-medium
        ${colorClass}
        ${sizeClass}
      `}
      title={role.name}
    >
      <span>{role.emoji}</span>
      {showName && <span>{role.name}</span>}
    </span>
  )
}

interface RoleBadgeListProps {
  roles: Array<{ id: string; emoji: string; name: string }>
  size?: 'sm' | 'md'
  showNames?: boolean
  maxDisplay?: number
}

export function RoleBadgeList({ roles, size = 'sm', showNames = false, maxDisplay = 3 }: RoleBadgeListProps) {
  const displayRoles = roles.slice(0, maxDisplay)
  const remaining = roles.length - maxDisplay

  return (
    <div className="flex flex-wrap gap-1">
      {displayRoles.map(role => (
        <RoleBadge key={role.id} role={role} size={size} showName={showNames} />
      ))}
      {remaining > 0 && (
        <span className="inline-flex items-center px-1.5 py-0.5 text-xs text-genesis-muted">
          +{remaining}
        </span>
      )}
    </div>
  )
}
