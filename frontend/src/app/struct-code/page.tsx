'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { api, StructCodeQuestion, StructCodeResult } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { Compass, ArrowRight, ArrowLeft, Check, MapPin, Loader2 } from 'lucide-react'

const AXIS_LABELS: Record<string, string> = {
  '起動軸': 'Activation',
  '判断軸': 'Judgment',
  '選択軸': 'Choice',
  '共鳴軸': 'Resonance',
  '自覚軸': 'Awareness',
}

const AXIS_ORDER = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']

const QUESTIONS_PER_PAGE = 5

export default function StructCodePage() {
  const router = useRouter()
  const { resident } = useAuthStore()

  // Steps: 0=intro, 1=birth info, 2-6=questions, 7=result
  const [step, setStep] = useState(0)
  const [birthYear, setBirthYear] = useState('')
  const [birthMonth, setBirthMonth] = useState('')
  const [birthDay, setBirthDay] = useState('')
  const [birthLocation, setBirthLocation] = useState('')
  const [locationQuery, setLocationQuery] = useState('')
  const [locationSuggestions, setLocationSuggestions] = useState<LocationSuggestion[]>([])
  const [locationLoading, setLocationLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [questions, setQuestions] = useState<StructCodeQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<StructCodeResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const locationRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  const birthDate = birthYear && birthMonth && birthDay
    ? `${birthYear}-${birthMonth.padStart(2, '0')}-${birthDay.padStart(2, '0')}`
    : ''

  useEffect(() => {
    api.structCodeQuestions().then(setQuestions).catch(() => {})
  }, [])

  // Close suggestions on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (locationRef.current && !locationRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Geocode location with Nominatim (debounced)
  const searchLocation = useCallback(async (query: string) => {
    if (query.length < 2) {
      setLocationSuggestions([])
      return
    }
    setLocationLoading(true)
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?` +
        `q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=6&accept-language=ja,en`,
        { headers: { 'User-Agent': 'Genesis-StructCode/1.0' } }
      )
      const data = await res.json()
      setLocationSuggestions(
        data.map((item: any) => ({
          display: item.display_name,
          short: buildShortName(item),
          lat: item.lat,
          lon: item.lon,
        }))
      )
      setShowSuggestions(true)
    } catch {
      setLocationSuggestions([])
    } finally {
      setLocationLoading(false)
    }
  }, [])

  const handleLocationInput = (value: string) => {
    setLocationQuery(value)
    setBirthLocation('')  // Clear selection when typing
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => searchLocation(value), 400)
  }

  const selectLocation = (suggestion: LocationSuggestion) => {
    setBirthLocation(suggestion.short)
    setLocationQuery(suggestion.short)
    setShowSuggestions(false)
  }

  const totalPages = Math.ceil(questions.length / QUESTIONS_PER_PAGE)
  const questionPage = step - 2 // 0-indexed question page
  const currentQuestions = questions.slice(
    questionPage * QUESTIONS_PER_PAGE,
    (questionPage + 1) * QUESTIONS_PER_PAGE
  )

  const allQuestionsAnswered = questions.length > 0 && questions.every(q => answers[q.id])

  const canProceed = () => {
    if (step === 1) return birthDate && birthLocation
    if (step >= 2 && step <= 1 + totalPages) {
      return currentQuestions.every(q => answers[q.id])
    }
    return true
  }

  const handleSubmit = async () => {
    if (!resident) {
      setError('Please log in first')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.structCodeDiagnose({
        birth_date: birthDate,
        birth_location: birthLocation,
        answers: Object.entries(answers).map(([qid, choice]) => ({
          question_id: qid,
          choice,
        })),
      })
      setResult(res)
      setStep(2 + totalPages) // result step
    } catch (e: any) {
      setError(e.message || 'Diagnosis failed')
    } finally {
      setLoading(false)
    }
  }

  const handleNext = () => {
    const lastQuestionStep = 1 + totalPages
    if (step === lastQuestionStep && allQuestionsAnswered) {
      handleSubmit()
    } else {
      setStep(s => s + 1)
    }
  }

  // ── Intro ──
  if (step === 0) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="text-center space-y-6">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-accent-gold/10 mb-4">
            <Compass size={40} className="text-accent-gold" />
          </div>
          <h1 className="text-3xl font-bold text-text-primary">STRUCT CODE</h1>
          <p className="text-text-secondary text-lg">
            Discover your structural personality type through 25 questions and astrological analysis.
          </p>
          <p className="text-text-muted text-sm">
            24 types across 5 axes: Activation, Judgment, Choice, Resonance, Awareness
          </p>

          {!resident && (
            <p className="text-karma-down text-sm">Please log in to take the diagnosis.</p>
          )}

          <button
            onClick={() => setStep(1)}
            disabled={!resident}
            className="inline-flex items-center gap-2 px-8 py-3 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Start Diagnosis
            <ArrowRight size={18} />
          </button>

          {resident?.struct_type && (
            <div className="mt-8 p-4 bg-bg-tertiary rounded-lg border border-border-default">
              <p className="text-text-muted text-sm mb-2">Your current type</p>
              <p className="text-accent-gold font-bold text-xl">{resident.struct_type}</p>
              <p className="text-text-secondary text-sm mt-1">
                You can retake the diagnosis to update your type.
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Birth Info ──
  if (step === 1) {
    const currentYear = new Date().getFullYear()
    const years = Array.from({ length: 80 }, (_, i) => currentYear - 10 - i) // 10~89 years ago
    const months = Array.from({ length: 12 }, (_, i) => i + 1)
    const daysInMonth = birthYear && birthMonth
      ? new Date(Number(birthYear), Number(birthMonth), 0).getDate()
      : 31
    const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)

    return (
      <div className="max-w-2xl mx-auto p-6">
        <ProgressBar current={0} total={totalPages + 1} />
        <h2 className="text-xl font-bold text-text-primary mb-6">Birth Information</h2>
        <p className="text-text-muted text-sm mb-4">
          Astrological calculation requires accurate birth date and location.
        </p>
        <div className="space-y-5">
          {/* Birth Date - Year/Month/Day selects */}
          <div>
            <label className="block text-text-secondary text-sm mb-2">Birth Date</label>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <select
                  value={birthYear}
                  onChange={e => { setBirthYear(e.target.value); if (birthDay && Number(birthDay) > new Date(Number(e.target.value), Number(birthMonth), 0).getDate()) setBirthDay('') }}
                  className="w-full px-3 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary focus:outline-none focus:border-accent-gold appearance-none cursor-pointer"
                >
                  <option value="" className="text-text-muted">Year</option>
                  {years.map(y => (
                    <option key={y} value={String(y)}>{y}</option>
                  ))}
                </select>
              </div>
              <div>
                <select
                  value={birthMonth}
                  onChange={e => { setBirthMonth(e.target.value); if (birthDay && Number(birthDay) > new Date(Number(birthYear), Number(e.target.value), 0).getDate()) setBirthDay('') }}
                  className="w-full px-3 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary focus:outline-none focus:border-accent-gold appearance-none cursor-pointer"
                >
                  <option value="" className="text-text-muted">Month</option>
                  {months.map(m => (
                    <option key={m} value={String(m)}>{m}月 / {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]}</option>
                  ))}
                </select>
              </div>
              <div>
                <select
                  value={birthDay}
                  onChange={e => setBirthDay(e.target.value)}
                  className="w-full px-3 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary focus:outline-none focus:border-accent-gold appearance-none cursor-pointer"
                >
                  <option value="" className="text-text-muted">Day</option>
                  {days.map(d => (
                    <option key={d} value={String(d)}>{d}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Birth Location - Autocomplete with Nominatim */}
          <div ref={locationRef}>
            <label className="block text-text-secondary text-sm mb-2">Birth Location</label>
            <p className="text-text-muted text-xs mb-2">
              Please specify down to the city/ward level (市区町村). Example: 渋谷区, 福岡市中央区, Manhattan NY
            </p>
            <div className="relative">
              <MapPin size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                value={locationQuery}
                onChange={e => handleLocationInput(e.target.value)}
                onFocus={() => locationSuggestions.length > 0 && setShowSuggestions(true)}
                placeholder="e.g. 渋谷区, Shibuya, Manhattan, 福岡市..."
                className="w-full pl-10 pr-10 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold"
              />
              {locationLoading && (
                <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted animate-spin" />
              )}
            </div>
            {birthLocation && (
              <p className="text-accent-gold text-xs mt-1.5 flex items-center gap-1">
                <Check size={12} /> {birthLocation}
              </p>
            )}

            {/* Suggestions dropdown */}
            {showSuggestions && locationSuggestions.length > 0 && (
              <div className="mt-1 bg-bg-secondary border border-border-default rounded-lg shadow-lg overflow-hidden max-h-60 overflow-y-auto z-50 relative">
                {locationSuggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => selectLocation(s)}
                    className="w-full text-left px-4 py-2.5 hover:bg-bg-tertiary transition-colors border-b border-border-default last:border-b-0"
                  >
                    <p className="text-text-primary text-sm">{s.short}</p>
                    <p className="text-text-muted text-xs truncate">{s.display}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex justify-between mt-8">
          <button
            onClick={() => setStep(0)}
            className="flex items-center gap-2 px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
          >
            <ArrowLeft size={16} /> Back
          </button>
          <button
            onClick={handleNext}
            disabled={!canProceed()}
            className="flex items-center gap-2 px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50"
          >
            Next <ArrowRight size={16} />
          </button>
        </div>
      </div>
    )
  }

  // ── Result ──
  if (result) {
    const info = result.type_info
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accent-gold/20 mb-4">
            <Check size={32} className="text-accent-gold" />
          </div>
          <h2 className="text-2xl font-bold text-text-primary">Your STRUCT CODE</h2>
        </div>

        <div className="bg-bg-tertiary rounded-xl border border-border-default p-6 mb-6">
          <div className="text-center mb-6">
            <p className="text-accent-gold font-mono text-3xl font-bold">{result.struct_type}</p>
            <p className="text-text-primary text-xl mt-1">{info.name}</p>
            <p className="text-text-secondary">{info.archetype}</p>
            <p className="text-text-muted text-sm mt-2">
              Similarity: {(result.similarity * 100).toFixed(1)}%
            </p>
          </div>

          {/* 5-axis bars */}
          <div className="space-y-3 mb-6">
            {result.axes.map((val, i) => {
              const axisName = AXIS_ORDER[i]
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-text-secondary text-sm w-24 text-right">
                    {AXIS_LABELS[axisName] || axisName}
                  </span>
                  <div className="flex-1 h-3 bg-bg-primary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-gold rounded-full transition-all duration-500"
                      style={{ width: `${val * 100}%` }}
                    />
                  </div>
                  <span className="text-text-muted text-xs w-12">
                    {(val * 100).toFixed(0)}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Type description */}
          {info.description && (
            <div className="border-t border-border-default pt-4 space-y-4">
              <Section title="Description" text={info.description} />
              <Section title="Decision Style" text={info.decision_making_style} />
              <Section title="Choice Pattern" text={info.choice_pattern} />
              <Section title="Interpersonal Dynamics" text={info.interpersonal_dynamics} />
              <Section title="Growth Path" text={info.growth_path} />
              <Section title="Blindspot" text={info.blindspot} />
            </div>
          )}
        </div>

        {/* Top candidates */}
        {result.top_candidates.length > 0 && (
          <div className="bg-bg-tertiary rounded-xl border border-border-default p-4 mb-6">
            <h3 className="text-text-secondary text-sm font-semibold mb-3">Other possible types</h3>
            <div className="space-y-2">
              {result.top_candidates.map(c => (
                <div key={c.code} className="flex items-center justify-between text-sm">
                  <span className="text-text-primary font-mono">{c.code} — {c.name}</span>
                  <span className="text-text-muted">{(c.score * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3 justify-center">
          <button
            onClick={() => router.push('/struct-code/consultation')}
            className="px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors"
          >
            Ask AI Counselor
          </button>
          <button
            onClick={() => router.push(`/u/${resident?.name}`)}
            className="px-6 py-2 bg-bg-tertiary text-text-primary border border-border-default rounded-lg hover:bg-bg-hover transition-colors"
          >
            View Profile
          </button>
        </div>

        {error && <p className="text-karma-down text-sm text-center mt-4">{error}</p>}
      </div>
    )
  }

  // ── Questions ──
  return (
    <div className="max-w-2xl mx-auto p-6">
      <ProgressBar current={questionPage + 1} total={totalPages + 1} />

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold text-text-primary">
          Questions {questionPage * QUESTIONS_PER_PAGE + 1}-
          {Math.min((questionPage + 1) * QUESTIONS_PER_PAGE, questions.length)} of {questions.length}
        </h2>
        <span className="text-text-muted text-sm">
          {currentQuestions[0]?.axis && (AXIS_LABELS[currentQuestions[0].axis] || currentQuestions[0].axis)}
        </span>
      </div>

      <div className="space-y-6">
        {currentQuestions.map((q) => (
          <div key={q.id} className="bg-bg-tertiary rounded-xl border border-border-default p-5">
            <p className="text-text-primary font-medium mb-4">{q.question}</p>
            <div className="grid grid-cols-1 gap-2">
              {Object.entries(q.choices).map(([key, choice]) => (
                <button
                  key={key}
                  onClick={() => setAnswers(prev => ({ ...prev, [q.id]: key }))}
                  className={`text-left px-4 py-3 rounded-lg border transition-all text-sm ${
                    answers[q.id] === key
                      ? 'border-accent-gold bg-accent-gold/10 text-text-primary'
                      : 'border-border-default bg-bg-primary text-text-secondary hover:border-border-hover hover:bg-bg-hover'
                  }`}
                >
                  <span className="font-mono text-accent-gold mr-2">{key}.</span>
                  {choice.text}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {error && <p className="text-karma-down text-sm mt-4">{error}</p>}

      <div className="flex justify-between mt-8">
        <button
          onClick={() => setStep(s => s - 1)}
          className="flex items-center gap-2 px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft size={16} /> Back
        </button>
        <button
          onClick={handleNext}
          disabled={!canProceed() || loading}
          className="flex items-center gap-2 px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50"
        >
          {loading ? (
            'Analyzing...'
          ) : step === 1 + totalPages ? (
            <>Submit <Check size={16} /></>
          ) : (
            <>Next <ArrowRight size={16} /></>
          )}
        </button>
      </div>
    </div>
  )
}

function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = (current / total) * 100
  return (
    <div className="mb-6">
      <div className="h-1.5 bg-bg-primary rounded-full overflow-hidden">
        <div
          className="h-full bg-accent-gold rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-text-muted text-xs mt-1 text-right">
        Step {current} / {total}
      </p>
    </div>
  )
}

function Section({ title, text }: { title: string; text: string }) {
  if (!text) return null
  return (
    <div>
      <h4 className="text-text-secondary text-sm font-semibold mb-1">{title}</h4>
      <p className="text-text-primary text-sm leading-relaxed">{text}</p>
    </div>
  )
}

interface LocationSuggestion {
  display: string
  short: string
  lat: string
  lon: string
}

function buildShortName(item: any): string {
  const addr = item.address || {}
  // Build a concise but specific location string
  const parts: string[] = []

  // Most specific: suburb/neighbourhood/quarter
  const detail = addr.suburb || addr.neighbourhood || addr.quarter || addr.borough || ''
  // City/town/village
  const city = addr.city || addr.town || addr.village || addr.municipality || ''
  // State/prefecture
  const state = addr.state || addr.province || addr.county || ''
  // Country
  const country = addr.country || ''

  if (detail) parts.push(detail)
  if (city && city !== detail) parts.push(city)
  if (state && state !== city) parts.push(state)
  if (country) parts.push(country)

  return parts.join(', ') || item.display_name?.split(',').slice(0, 3).join(',') || ''
}
