'use client'

import { useState, useEffect, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api, Resident, StructCodeTypeInfo } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import {
  Compass, Trophy, Award, Medal, Share2, Copy, Check,
  ArrowLeft, MessageCircle, Loader2, ExternalLink,
} from 'lucide-react'
import Link from 'next/link'

const AXIS_LABELS: Record<string, string> = {
  '起動軸': 'Activation',
  '判断軸': 'Judgment',
  '選択軸': 'Choice',
  '共鳴軸': 'Resonance',
  '自覚軸': 'Awareness',
}

const AXIS_SHORT = ['Act', 'Jdg', 'Chc', 'Res', 'Awa']
const AXIS_ORDER = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']

function classifyAxis(val: number): { label: string; color: string } {
  if (val >= 0.60) return { label: 'H', color: 'bg-accent-gold text-bg-primary' }
  if (val >= 0.40) return { label: 'M', color: 'bg-text-muted/30 text-text-primary' }
  return { label: 'L', color: 'bg-bg-primary text-text-muted' }
}

const MEDAL_STYLES = [
  { icon: Trophy, color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/30', label: 'Your Type' },
  { icon: Award, color: 'text-gray-300', bg: 'bg-gray-300/10 border-gray-300/30', label: '' },
  { icon: Medal, color: 'text-amber-600', bg: 'bg-amber-600/10 border-amber-600/30', label: '' },
]

export default function StructCodeResultPage() {
  const params = useParams()
  const router = useRouter()
  const { resident: currentUser } = useAuthStore()
  const name = params.name as string

  const [resident, setResident] = useState<Resident | null>(null)
  const [typeInfo, setTypeInfo] = useState<StructCodeTypeInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  const lang = useMemo(() => {
    if (typeof navigator === 'undefined') return 'ja'
    return navigator.language.startsWith('ja') ? 'ja' : 'en'
  }, [])

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getResident(name)
        setResident(res)
        if (res.struct_type) {
          const info = await api.structCodeType(res.struct_type, lang)
          setTypeInfo(info)
        }
      } catch {
        // resident not found
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [name, lang])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-accent-gold" size={32} />
      </div>
    )
  }

  if (!resident || !resident.struct_type) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <Compass size={48} className="text-text-muted mx-auto mb-4" />
        <h2 className="text-xl font-bold text-text-primary mb-2">No STRUCT CODE Result</h2>
        <p className="text-text-secondary mb-6">
          {resident ? 'This user has not completed their STRUCT CODE diagnosis yet.' : 'User not found.'}
        </p>
        {currentUser?.name === name && (
          <Link
            href="/struct-code"
            className="inline-flex items-center gap-2 px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors"
          >
            Take Diagnosis
          </Link>
        )}
      </div>
    )
  }

  const structResult = resident.struct_result
  const axes = resident.struct_axes || [0.5, 0.5, 0.5, 0.5, 0.5]
  const similarity = structResult?.similarity ?? 0
  const structCode = structResult?.struct_code ?? resident.struct_type
  const topCandidates = structResult?.top_candidates ?? []
  const isOwnProfile = currentUser?.name === name

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleShareX = () => {
    const text = `My STRUCT CODE type is ${resident.struct_type} (${typeInfo?.name || ''}) — ${typeInfo?.archetype || ''}`
    const url = window.location.href
    window.open(
      `https://x.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
      '_blank'
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.back()}
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-lg font-bold text-text-primary">STRUCT CODE Result</h1>
          <p className="text-text-muted text-xs">
            <Link href={`/u/${name}`} className="hover:text-accent-gold transition-colors">
              @{name}
            </Link>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Type Display Card */}
        <div className="bg-bg-tertiary rounded-xl border border-border-default p-6">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accent-gold/20 mb-3">
              <Compass size={32} className="text-accent-gold" />
            </div>
            <p className="text-accent-gold font-mono text-4xl font-bold tracking-wider">
              {resident.struct_type}
            </p>
            <p className="text-text-primary text-xl mt-2">{typeInfo?.name || ''}</p>
            <p className="text-text-secondary">{typeInfo?.archetype || ''}</p>

            {similarity > 0 && (
              <div className="inline-flex items-center gap-1.5 mt-3 px-3 py-1 bg-accent-gold/10 border border-accent-gold/30 rounded-full">
                <span className="text-accent-gold text-sm font-semibold">
                  Match: {(similarity * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Struct Code String */}
          <div className="text-center mb-6">
            <p className="font-mono text-text-muted text-xs tracking-widest">{structCode}</p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col gap-2">
            {isOwnProfile && (
              <Link
                href="/struct-code/consultation"
                className="flex items-center justify-center gap-2 px-4 py-2.5 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors"
              >
                <MessageCircle size={16} />
                Ask AI Counselor
              </Link>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleShareX}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-bg-primary border border-border-default rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors text-sm"
              >
                <ExternalLink size={14} />
                Share on X
              </button>
              <button
                onClick={handleCopyLink}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-bg-primary border border-border-default rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors text-sm"
              >
                {copied ? <Check size={14} className="text-accent-gold" /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: 5-Axis Scores */}
        <div className="bg-bg-tertiary rounded-xl border border-border-default p-6">
          <h3 className="text-text-primary font-semibold mb-4">5-Axis Profile</h3>
          <div className="space-y-4">
            {axes.map((val: number, i: number) => {
              const axisName = AXIS_ORDER[i]
              const cls = classifyAxis(val)
              return (
                <div key={i}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-text-primary text-sm font-medium">
                        {AXIS_LABELS[axisName] || AXIS_SHORT[i]}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cls.color}`}>
                        {cls.label}
                      </span>
                    </div>
                    <span className="text-text-muted text-sm font-mono">
                      {Math.round(val * 1000)}
                    </span>
                  </div>
                  <div className="h-3 bg-bg-primary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-gold rounded-full transition-all duration-700"
                      style={{ width: `${val * 100}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* TOP 3 Type Candidates */}
      {topCandidates.length > 0 && (
        <div className="mt-6 bg-bg-tertiary rounded-xl border border-border-default p-6">
          <h3 className="text-text-primary font-semibold mb-4">TOP 3 Type Candidates</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {topCandidates.slice(0, 3).map((c: any, i: number) => {
              const medal = MEDAL_STYLES[i] || MEDAL_STYLES[2]
              const MedalIcon = medal.icon
              return (
                <div
                  key={c.code}
                  className={`relative p-4 rounded-lg border ${medal.bg} transition-colors`}
                >
                  <div className="flex items-start gap-3">
                    <MedalIcon size={24} className={medal.color} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-text-primary">{c.code}</span>
                        {i === 0 && (
                          <span className="text-[10px] font-semibold text-accent-gold bg-accent-gold/10 px-1.5 py-0.5 rounded">
                            Your Type
                          </span>
                        )}
                      </div>
                      <p className="text-text-primary text-sm mt-0.5">{c.name}</p>
                      <p className="text-text-muted text-xs">{c.archetype}</p>
                      <p className="text-text-secondary text-sm font-semibold mt-1">
                        {(c.score * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Type Characteristics */}
      {typeInfo && typeInfo.description && (
        <div className="mt-6 bg-bg-tertiary rounded-xl border border-border-default p-6">
          <h3 className="text-text-primary font-semibold mb-4">Type Characteristics</h3>
          <div className="space-y-5">
            <Section title="Description" text={typeInfo.description} />
            <Section title="Decision Making Style" text={typeInfo.decision_making_style} />
            <Section title="Choice Pattern" text={typeInfo.choice_pattern} />
            <Section title="Interpersonal Dynamics" text={typeInfo.interpersonal_dynamics} />
            <Section title="Growth Path" text={typeInfo.growth_path} />
            <Section title="Blindspot" text={typeInfo.blindspot} />
          </div>
        </div>
      )}

      {/* Footer actions */}
      <div className="mt-6 flex flex-wrap gap-3 justify-center">
        <Link
          href={`/u/${name}`}
          className="px-6 py-2 bg-bg-tertiary text-text-primary border border-border-default rounded-lg hover:bg-bg-hover transition-colors text-sm"
        >
          View Profile
        </Link>
        {isOwnProfile && (
          <Link
            href="/struct-code"
            className="px-6 py-2 bg-bg-tertiary text-text-secondary border border-border-default rounded-lg hover:bg-bg-hover transition-colors text-sm"
          >
            Retake Diagnosis
          </Link>
        )}
      </div>
    </div>
  )
}

function Section({ title, text }: { title: string; text: string }) {
  if (!text) return null
  return (
    <div>
      <h4 className="text-text-secondary text-sm font-semibold mb-1.5">{title}</h4>
      <p className="text-text-primary text-sm leading-relaxed">{text}</p>
    </div>
  )
}
