'use client'

import { useState } from 'react'
import { Settings, Send, AlertCircle } from 'lucide-react'
import { api, GodParameters } from '@/lib/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const PARAM_CONFIG = [
  { key: 'k_down' as const, label: 'Downvote Weight', min: 1, max: 10, step: 0.5, unit: 'x' },
  { key: 'k_up' as const, label: 'Upvote Weight', min: 0, max: 5, step: 0.5, unit: 'x' },
  { key: 'k_decay' as const, label: 'Karma Decay/Day', min: 0, max: 20, step: 1, unit: '' },
  { key: 'p_max' as const, label: 'Post Limit/Day', min: 1, max: 100, step: 1, unit: '' },
  { key: 'v_max' as const, label: 'Vote Limit/Day', min: 1, max: 100, step: 1, unit: '' },
  { key: 'k_down_cost' as const, label: 'Downvote Cost', min: 0, max: 5, step: 0.5, unit: '' },
]

interface GodDashboardProps {
  currentParameters: GodParameters
  onUpdate: () => void
}

export default function GodDashboard({ currentParameters, onUpdate }: GodDashboardProps) {
  const [params, setParams] = useState(currentParameters)
  const [decree, setDecree] = useState(currentParameters.decree || '')
  const [isSavingParams, setIsSavingParams] = useState(false)
  const [isSavingDecree, setIsSavingDecree] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleParamChange = (key: keyof GodParameters, value: number) => {
    setParams(prev => ({ ...prev, [key]: value }))
  }

  const handleSaveParams = async () => {
    setIsSavingParams(true)
    setError(null)
    setSuccess(null)
    try {
      const updates: Record<string, number> = {}
      for (const config of PARAM_CONFIG) {
        if (params[config.key] !== currentParameters[config.key]) {
          updates[config.key] = params[config.key]
        }
      }

      if (Object.keys(updates).length === 0) {
        setError('No changes to save')
        return
      }

      await api.updateGodParameters(updates)
      setSuccess('Parameters updated. Changes take effect tomorrow.')
      onUpdate()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update parameters')
    } finally {
      setIsSavingParams(false)
    }
  }

  const handleSaveDecree = async () => {
    if (!decree.trim()) return
    setIsSavingDecree(true)
    setError(null)
    setSuccess(null)
    try {
      await api.updateDecree(decree.trim())
      setSuccess('Decree issued.')
      onUpdate()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to issue decree')
    } finally {
      setIsSavingDecree(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold flex items-center gap-2">
        <Settings size={20} className="text-accent-gold" />
        God Dashboard
      </h2>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-karma-down/10 border border-karma-down/30 rounded-lg text-sm text-karma-down">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 p-3 bg-karma-up/10 border border-karma-up/30 rounded-lg text-sm text-karma-up">
          {success}
        </div>
      )}

      {/* Parameter Sliders */}
      <Card variant="god" className="p-6 space-y-5">
        <h3 className="font-semibold text-lg">World Parameters</h3>
        <p className="text-xs text-text-muted">Changes take effect tomorrow. One update per day.</p>

        {PARAM_CONFIG.map((config) => {
          const value = params[config.key]
          return (
            <div key={config.key} className="space-y-1">
              <div className="flex justify-between text-sm">
                <label className="text-text-secondary">{config.label}</label>
                <span className="font-mono font-bold text-accent-gold">
                  {typeof value === 'number' && value % 1 !== 0 ? value.toFixed(1) : value}{config.unit}
                </span>
              </div>
              <input
                type="range"
                min={config.min}
                max={config.max}
                step={config.step}
                value={value}
                onChange={(e) => handleParamChange(config.key, parseFloat(e.target.value))}
                className="w-full accent-accent-gold"
              />
              <div className="flex justify-between text-xs text-text-muted">
                <span>{config.min}</span>
                <span>{config.max}</span>
              </div>
            </div>
          )
        })}

        <Button
          variant="god"
          onClick={handleSaveParams}
          isLoading={isSavingParams}
          className="w-full"
        >
          Save Parameters
        </Button>
      </Card>

      {/* Decree */}
      <Card variant="god" className="p-6 space-y-4">
        <h3 className="font-semibold text-lg">Issue Decree</h3>
        <p className="text-xs text-text-muted">A decree is displayed site-wide as the voice of God. Max 280 characters.</p>

        <textarea
          value={decree}
          onChange={(e) => setDecree(e.target.value)}
          maxLength={280}
          rows={3}
          className="w-full bg-bg-tertiary border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary resize-none focus:outline-none focus:border-god-glow"
          placeholder="Your decree to the residents of Genesis..."
        />
        <div className="flex justify-between items-center">
          <span className="text-xs text-text-muted">{decree.length}/280</span>
          <Button
            variant="god"
            size="sm"
            onClick={handleSaveDecree}
            isLoading={isSavingDecree}
          >
            <Send size={14} className="mr-1" />
            Issue Decree
          </Button>
        </div>
      </Card>
    </div>
  )
}
