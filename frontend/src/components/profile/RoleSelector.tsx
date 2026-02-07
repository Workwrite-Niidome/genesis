'use client'

import { useState, useEffect } from 'react'
import { api, RoleInfo } from '@/lib/api'

interface RoleSelectorProps {
  currentRoles: string[]
  onRolesChange?: (roles: string[]) => void
  readonly?: boolean
}

export default function RoleSelector({ currentRoles, onRolesChange, readonly = false }: RoleSelectorProps) {
  const [availableRoles, setAvailableRoles] = useState<RoleInfo[]>([])
  const [specialRoles, setSpecialRoles] = useState<RoleInfo[]>([])
  const [selectedRoles, setSelectedRoles] = useState<string[]>(currentRoles)
  const [maxRoles, setMaxRoles] = useState(3)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const data = await api.getAvailableRoles()
        setAvailableRoles(data.available)
        setSpecialRoles(data.special)
        setMaxRoles(data.max_roles)
      } catch (err) {
        console.error('Failed to fetch roles:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRoles()
  }, [])

  useEffect(() => {
    setSelectedRoles(currentRoles)
  }, [currentRoles])

  const toggleRole = async (roleId: string) => {
    if (readonly) return

    const isSelected = selectedRoles.includes(roleId)
    let newRoles: string[]

    if (isSelected) {
      newRoles = selectedRoles.filter(r => r !== roleId)
    } else {
      // Check max roles (only count non-special roles)
      const nonSpecialSelected = selectedRoles.filter(r =>
        availableRoles.some(ar => ar.id === r)
      )
      if (nonSpecialSelected.length >= maxRoles) {
        setError(`You can select up to ${maxRoles} roles`)
        return
      }
      newRoles = [...selectedRoles, roleId]
    }

    setSelectedRoles(newRoles)
    setError(null)

    // Save immediately
    setSaving(true)
    try {
      await api.updateMyRoles(newRoles.filter(r =>
        availableRoles.some(ar => ar.id === r)
      ))
      onRolesChange?.(newRoles)
    } catch (err: any) {
      setError(err.message || 'Failed to update roles')
      setSelectedRoles(currentRoles) // Revert
    } finally {
      setSaving(false)
    }
  }

  // Get current special roles from currentRoles
  const currentSpecialRoles = currentRoles.filter(r =>
    specialRoles.some(sr => sr.id === r)
  )

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-8 bg-genesis-tertiary rounded w-32" />
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-10 w-24 bg-genesis-tertiary rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Special roles (display only) */}
      {currentSpecialRoles.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-genesis-secondary mb-2">Special Roles</h4>
          <div className="flex flex-wrap gap-2">
            {currentSpecialRoles.map(roleId => {
              const role = specialRoles.find(r => r.id === roleId)
              if (!role) return null
              return (
                <div
                  key={roleId}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-genesis-gold/20 text-genesis-gold border border-genesis-gold/30"
                >
                  <span>{role.emoji}</span>
                  <span className="text-sm font-medium">{role.name}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Regular roles */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-genesis-secondary">
            Roles {readonly ? '' : `(${selectedRoles.filter(r => availableRoles.some(ar => ar.id === r)).length}/${maxRoles})`}
          </h4>
          {saving && (
            <span className="text-xs text-genesis-secondary animate-pulse">Saving...</span>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {availableRoles.map(role => {
            const isSelected = selectedRoles.includes(role.id)
            return (
              <button
                key={role.id}
                onClick={() => toggleRole(role.id)}
                disabled={readonly || saving}
                className={`
                  inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all
                  ${readonly ? 'cursor-default' : 'cursor-pointer'}
                  ${isSelected
                    ? 'bg-genesis-accent/20 border-genesis-accent text-genesis-accent'
                    : 'bg-genesis-tertiary border-genesis-border text-genesis-secondary hover:border-genesis-accent/50 hover:text-genesis-primary'
                  }
                  ${!isSelected && !readonly ? 'opacity-60 hover:opacity-100' : ''}
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                title={role.description}
              >
                <span>{role.emoji}</span>
                <span className="text-sm font-medium">{role.name}</span>
              </button>
            )
          })}
        </div>

        {error && (
          <p className="mt-2 text-sm text-red-400">{error}</p>
        )}

        {!readonly && (
          <p className="mt-3 text-xs text-genesis-muted">
            Roles express your identity. You can select up to {maxRoles}.
          </p>
        )}
      </div>
    </div>
  )
}
