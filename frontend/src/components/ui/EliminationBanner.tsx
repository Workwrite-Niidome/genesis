'use client'

import { Skull } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'

export default function EliminationBanner() {
  const { resident } = useAuthStore()

  if (!resident?.is_eliminated) {
    return null
  }

  return (
    <div className="bg-red-950/80 border-b border-red-500/30">
      <div className="max-w-4xl mx-auto px-4 py-3">
        <div className="flex items-center gap-3">
          <Skull className="flex-shrink-0 text-red-400" size={20} />
          <p className="text-sm text-red-200">
            You have been eliminated. You can observe but not participate.
            You will return when the next God takes power.
          </p>
        </div>
      </div>
    </div>
  )
}
