'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api, Resident, StructCodeTypeInfo } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import {
  Compass, Trophy, Award, Medal, Share2, Copy, Check,
  ArrowLeft, MessageCircle, Loader2, ExternalLink,
  ArrowUp, ArrowDown, Minus, Clock, Globe,
} from 'lucide-react'
import Link from 'next/link'

function t(lang: string, ja: string, en: string): string {
  return lang === 'en' ? en : ja
}

const AXIS_LABELS: Record<string, Record<string, string>> = {
  '起動軸': { ja: '起動軸', en: 'Activation' },
  '判断軸': { ja: '判断軸', en: 'Judgment' },
  '選択軸': { ja: '選択軸', en: 'Choice' },
  '共鳴軸': { ja: '共鳴軸', en: 'Resonance' },
  '自覚軸': { ja: '自覚軸', en: 'Awareness' },
}

const AXIS_SHORT = ['Act', 'Jdg', 'Chc', 'Res', 'Awa']
const AXIS_ORDER = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']

function classifyAxis(val: number): { label: string; color: string } {
  if (val >= 0.60) return { label: 'H', color: 'bg-accent-gold text-bg-primary' }
  if (val >= 0.40) return { label: 'M', color: 'bg-text-muted/30 text-text-primary' }
  return { label: 'L', color: 'bg-bg-primary text-text-muted' }
}

function getAxisStateInfo(state: string, lang: string): { label: string; color: string; icon: typeof ArrowUp } {
  switch (state) {
    case 'activation':
      return { label: t(lang, '活性化', 'Active'), color: 'text-emerald-400', icon: ArrowUp }
    case 'suppression':
      return { label: t(lang, '抑制', 'Suppressed'), color: 'text-red-400', icon: ArrowDown }
    default:
      return { label: t(lang, '安定', 'Stable'), color: 'text-text-muted', icon: Minus }
  }
}

export default function StructCodeResultPage() {
  const params = useParams()
  const router = useRouter()
  const { resident: currentUser } = useAuthStore()
  const name = params.name as string

  const [resident, setResident] = useState<Resident | null>(null)
  const [typeInfo, setTypeInfo] = useState<StructCodeTypeInfo | null>(null)
  const [natalTypeInfo, setNatalTypeInfo] = useState<StructCodeTypeInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  const [lang, setLang] = useState('en')

  // Load resident data
  useEffect(() => {
    async function load() {
      try {
        const res = await api.getResident(name)
        setResident(res)
        // Use diagnosis language if available
        if (res.struct_result?.lang) {
          setLang(res.struct_result.lang)
        }
      } catch {
        // resident not found
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [name])

  // Fetch type info when resident or lang changes
  useEffect(() => {
    if (!resident?.struct_type) return
    async function loadTypeInfo() {
      try {
        const info = await api.structCodeType(resident!.struct_type!, lang)
        setTypeInfo(info)
        const natalType = resident!.struct_result?.natal?.type
        if (natalType && natalType !== resident!.struct_type) {
          try {
            const nInfo = await api.structCodeType(natalType, lang)
            setNatalTypeInfo(nInfo)
          } catch { /* natal type info not critical */ }
        }
      } catch { /* type info fetch failed */ }
    }
    loadTypeInfo()
  }, [resident, lang])

  const MEDAL_STYLES = [
    { icon: Trophy, color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/30', label: t(lang, 'あなたのタイプ', 'Your Type') },
    { icon: Award, color: 'text-gray-300', bg: 'bg-gray-300/10 border-gray-300/30', label: '' },
    { icon: Medal, color: 'text-amber-600', bg: 'bg-amber-600/10 border-amber-600/30', label: '' },
  ]

  // Section title translations
  const SECTION_TITLES: Record<string, Record<string, string>> = {
    description: { ja: '概要', en: 'Description' },
    decision_making_style: { ja: '意思決定スタイル', en: 'Decision Making Style' },
    choice_pattern: { ja: '選択パターン', en: 'Choice Pattern' },
    interpersonal_dynamics: { ja: '対人関係の特徴', en: 'Interpersonal Dynamics' },
    growth_path: { ja: '成長の道筋', en: 'Growth Path' },
    blindspot: { ja: '盲点', en: 'Blindspot' },
  }

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
        <h2 className="text-xl font-bold text-text-primary mb-2">
          {t(lang, 'STRUCT CODE 結果なし', 'No STRUCT CODE Result')}
        </h2>
        <p className="text-text-secondary mb-6">
          {resident
            ? t(lang, 'このユーザーはまだSTRUCT CODE診断を受けていません。', 'This user has not completed their STRUCT CODE diagnosis yet.')
            : t(lang, 'ユーザーが見つかりません。', 'User not found.')
          }
        </p>
        {currentUser?.name === name && (
          <Link
            href="/struct-code"
            className="inline-flex items-center gap-2 px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors"
          >
            {t(lang, '診断を受ける', 'Take Diagnosis')}
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

  // Dynamic data
  const natal = structResult?.natal
  const current = structResult?.current
  const designGap = structResult?.design_gap
  const axisStates = structResult?.axis_states ?? []
  const temporal = structResult?.temporal
  const hasNatalCurrentSplit = natal && current && natal.type !== current.type

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleShareX = () => {
    const text = lang === 'en'
      ? `My STRUCT CODE type is ${resident.struct_type} (${typeInfo?.name || ''}) — ${typeInfo?.archetype || ''}`
      : `私のSTRUCT CODEタイプは ${resident.struct_type}（${typeInfo?.name || ''}）— ${typeInfo?.archetype || ''}`
    const url = window.location.href
    window.open(
      `https://x.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
      '_blank'
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-2 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-text-primary">
              {t(lang, 'STRUCT CODE 結果', 'STRUCT CODE Result')}
            </h1>
            <p className="text-text-muted text-xs">
              <Link href={`/u/${name}`} className="hover:text-accent-gold transition-colors">
                @{name}
              </Link>
            </p>
          </div>
        </div>
        <button
          onClick={() => setLang(lang === 'en' ? 'ja' : 'en')}
          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-bg-tertiary border border-border-default rounded-lg text-text-secondary hover:text-text-primary hover:border-border-hover transition-colors text-xs font-medium shrink-0"
        >
          <Globe size={14} />
          {lang === 'en' ? 'JP' : 'EN'}
        </button>
      </div>

      {/* Natal vs Current Type Cards */}
      {hasNatalCurrentSplit ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {/* Current Type (Primary) */}
          <div className="bg-bg-tertiary rounded-xl border border-accent-gold/40 p-5">
            <div className="text-center">
              <p className="text-accent-gold text-[10px] font-semibold uppercase tracking-widest mb-2">
                {t(lang, 'カレントタイプ', 'Current Type')}
              </p>
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-accent-gold/20 mb-2">
                <Compass size={24} className="text-accent-gold" />
              </div>
              <p className="text-accent-gold font-mono text-3xl font-bold tracking-wider">
                {current.type}
              </p>
              <p className="text-text-primary text-lg mt-1">{current.type_name || typeInfo?.name || ''}</p>
              <p className="text-text-secondary text-sm">{typeInfo?.archetype || ''}</p>
              {current.description && (
                <p className="text-text-muted text-xs mt-2 leading-relaxed">{current.description}</p>
              )}
            </div>
          </div>

          {/* Natal Type */}
          <div className="bg-bg-tertiary rounded-xl border border-border-default p-5">
            <div className="text-center">
              <p className="text-text-muted text-[10px] font-semibold uppercase tracking-widest mb-2">
                {t(lang, 'ネイタルタイプ', 'Natal Type')}
              </p>
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-text-muted/10 mb-2">
                <Compass size={24} className="text-text-muted" />
              </div>
              <p className="text-text-primary font-mono text-3xl font-bold tracking-wider">
                {natal.type}
              </p>
              <p className="text-text-primary text-lg mt-1">{natal.type_name || natalTypeInfo?.name || ''}</p>
              <p className="text-text-secondary text-sm">{natalTypeInfo?.archetype || ''}</p>
              {natal.description && (
                <p className="text-text-muted text-xs mt-2 leading-relaxed">{natal.description}</p>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Single Type Card (natal == current or no dynamic data) */
        <div className="bg-bg-tertiary rounded-xl border border-border-default p-6 mb-6">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accent-gold/20 mb-3">
              <Compass size={32} className="text-accent-gold" />
            </div>
            <p className="text-accent-gold font-mono text-4xl font-bold tracking-wider">
              {resident.struct_type}
            </p>
            <p className="text-text-primary text-xl mt-2">{typeInfo?.name || ''}</p>
            <p className="text-text-secondary">{typeInfo?.archetype || ''}</p>
            {natal && current && natal.type === current.type && (
              <p className="text-text-muted text-xs mt-2">
                {t(lang, 'ネイタル = カレント', 'Natal = Current')}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Struct Code String + Match + Actions */}
      <div className="bg-bg-tertiary rounded-xl border border-border-default p-5 mb-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <p className="font-mono text-text-primary text-sm tracking-widest">{structCode}</p>
            {similarity > 0 && (
              <span className="text-accent-gold text-xs font-semibold">
                {t(lang, '適合度', 'Match')}: {(similarity * 100).toFixed(1)}%
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {isOwnProfile && (
              <Link
                href={`/chat?struct_code=${encodeURIComponent(structCode)}`}
                className="flex items-center gap-2 px-4 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors text-sm"
              >
                <MessageCircle size={14} />
                {t(lang, 'AIに相談', 'Ask AI')}
              </Link>
            )}
            <button
              onClick={handleShareX}
              className="flex items-center gap-2 px-3 py-2 bg-bg-primary border border-border-default rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors text-sm"
            >
              <ExternalLink size={14} />
            </button>
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-2 px-3 py-2 bg-bg-primary border border-border-default rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors text-sm"
            >
              {copied ? <Check size={14} className="text-accent-gold" /> : <Copy size={14} />}
            </button>
          </div>
        </div>
      </div>

      {/* Temporal Theme */}
      {temporal && temporal.current_theme && (
        <div className="bg-bg-tertiary rounded-xl border border-border-default p-5 mb-6">
          <div className="flex items-start gap-3">
            <Clock size={18} className="text-accent-gold mt-0.5 shrink-0" />
            <div>
              <h3 className="text-text-primary font-semibold text-sm">{temporal.current_theme}</h3>
              {temporal.theme_description && (
                <p className="text-text-secondary text-xs mt-1 leading-relaxed">{temporal.theme_description}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 5-Axis Profile with Axis States */}
      <div className="bg-bg-tertiary rounded-xl border border-border-default p-6 mb-6">
        <h3 className="text-text-primary font-semibold mb-4">
          {t(lang, '5軸プロフィール', '5-Axis Profile')}
        </h3>
        <div className="space-y-4">
          {axes.map((val: number, i: number) => {
            const axisName = AXIS_ORDER[i]
            const cls = classifyAxis(val)
            const natalVal = natal?.axes?.[i]
            const stateData = axisStates.find(s => s.axis === axisName)
            const stateInfo = stateData ? getAxisStateInfo(stateData.state, lang) : null
            const StateIcon = stateInfo?.icon || Minus
            return (
              <div key={i}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary text-sm font-medium">
                      {AXIS_LABELS[axisName]?.[lang] || AXIS_SHORT[i]}
                    </span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cls.color}`}>
                      {cls.label}
                    </span>
                    {stateInfo && stateData && stateData.state !== 'stable' && (
                      <span className={`inline-flex items-center gap-0.5 text-[10px] font-semibold ${stateInfo.color}`}>
                        <StateIcon size={10} />
                        {stateInfo.label}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {natalVal !== undefined && hasNatalCurrentSplit && (
                      <span className="text-text-muted text-[10px] font-mono">
                        ({Math.round(natalVal * 1000)})
                      </span>
                    )}
                    <span className="text-text-muted text-sm font-mono">
                      {Math.round(val * 1000)}
                    </span>
                  </div>
                </div>
                <div className="relative h-3 bg-bg-primary rounded-full overflow-hidden">
                  {/* Natal bar (background, dimmed) */}
                  {natalVal !== undefined && hasNatalCurrentSplit && (
                    <div
                      className="absolute h-full bg-text-muted/20 rounded-full"
                      style={{ width: `${natalVal * 100}%` }}
                    />
                  )}
                  {/* Current bar (foreground) */}
                  <div
                    className="absolute h-full bg-accent-gold rounded-full transition-all duration-700"
                    style={{ width: `${val * 100}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Axis state legend */}
        {axisStates.length > 0 && (
          <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border-default">
            <span className="text-text-muted text-[10px]">
              {t(lang, '軸の状態:', 'Axis States:')}
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
              <ArrowUp size={10} /> {t(lang, '活性化', 'Active')}
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] text-text-muted">
              <Minus size={10} /> {t(lang, '安定', 'Stable')}
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] text-red-400">
              <ArrowDown size={10} /> {t(lang, '抑制', 'Suppressed')}
            </span>
            {hasNatalCurrentSplit && (
              <span className="text-text-muted text-[10px]">
                {t(lang, '( ) = ネイタル', '( ) = Natal')}
              </span>
            )}
          </div>
        )}
      </div>

      {/* TOP 3 Type Candidates */}
      {topCandidates.length > 0 && (
        <div className="bg-bg-tertiary rounded-xl border border-border-default p-6 mb-6">
          <h3 className="text-text-primary font-semibold mb-4">
            {t(lang, 'タイプ候補 TOP 3', 'TOP 3 Type Candidates')}
          </h3>
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
                            {t(lang, 'あなたのタイプ', 'Your Type')}
                          </span>
                        )}
                      </div>
                      <p className="text-text-primary text-sm mt-0.5">{c.name}</p>
                      <p className="text-text-muted text-xs">{c.archetype}</p>
                      {c.score > 0 && (
                        <p className="text-text-secondary text-sm font-semibold mt-1">
                          {(c.score * 100).toFixed(1)}%
                        </p>
                      )}
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
        <div className="bg-bg-tertiary rounded-xl border border-border-default p-6 mb-6">
          <h3 className="text-text-primary font-semibold mb-4">
            {t(lang, 'タイプの特徴', 'Type Characteristics')}
          </h3>
          <div className="space-y-5">
            <Section title={SECTION_TITLES.description[lang]} text={typeInfo.description} />
            <Section title={SECTION_TITLES.decision_making_style[lang]} text={typeInfo.decision_making_style} />
            <Section title={SECTION_TITLES.choice_pattern[lang]} text={typeInfo.choice_pattern} />
            <Section title={SECTION_TITLES.interpersonal_dynamics[lang]} text={typeInfo.interpersonal_dynamics} />
            <Section title={SECTION_TITLES.growth_path[lang]} text={typeInfo.growth_path} />
            <Section title={SECTION_TITLES.blindspot[lang]} text={typeInfo.blindspot} />
          </div>
        </div>
      )}

      {/* Footer actions */}
      <div className="mt-6 flex flex-wrap gap-3 justify-center">
        <Link
          href={`/u/${name}`}
          className="px-6 py-2 bg-bg-tertiary text-text-primary border border-border-default rounded-lg hover:bg-bg-hover transition-colors text-sm"
        >
          {t(lang, 'プロフィールを見る', 'View Profile')}
        </Link>
        {isOwnProfile && (
          <Link
            href="/struct-code"
            className="px-6 py-2 bg-bg-tertiary text-text-secondary border border-border-default rounded-lg hover:bg-bg-hover transition-colors text-sm"
          >
            {t(lang, '再診断する', 'Retake Diagnosis')}
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
