import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BookOpen,
  ArrowLeft,
  Users,
  Sparkles,
  X as XIcon,
  Loader2,
  MessageCircle,
  Lightbulb,
} from 'lucide-react';
import { useSagaStore } from '../../stores/sagaStore';
import type { SagaChapter } from '../../types/world';

// Mood color mapping
const moodColors: Record<string, { text: string; bg: string; border: string; hex: string }> = {
  hopeful:     { text: 'text-green',  bg: 'bg-green/10',    border: 'border-green/20',  hex: '#34d399' },
  tragic:      { text: 'text-orange', bg: 'bg-orange/10',   border: 'border-orange/20', hex: '#fb923c' },
  triumphant:  { text: 'text-gold',   bg: 'bg-gold/10',     border: 'border-gold/20',   hex: '#d4a574' },
  mysterious:  { text: 'text-accent', bg: 'bg-accent/10',   border: 'border-accent/20', hex: '#7c5bf5' },
  peaceful:    { text: 'text-cyan',   bg: 'bg-cyan/10',     border: 'border-cyan/20',   hex: '#58d5f0' },
  turbulent:   { text: 'text-rose',   bg: 'bg-rose/10',     border: 'border-rose/20',   hex: '#f472b6' },
};

function getMoodColor(mood: string | null | undefined) {
  if (!mood) return { text: 'text-text-3', bg: 'bg-white/5', border: 'border-white/10', hex: '#8a8694' };
  return moodColors[mood] || { text: 'text-text-3', bg: 'bg-white/5', border: 'border-white/10', hex: '#8a8694' };
}

export default function SagaView() {
  const { t } = useTranslation();
  const { chapters, selectedChapter, loading, fetchChapters, selectChapter } = useSagaStore();

  useEffect(() => {
    fetchChapters();
  }, [fetchChapters]);

  if (loading && chapters.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-gold animate-spin" />
        <span className="ml-2 text-[13px] text-text-2">{t('saga_loading')}</span>
      </div>
    );
  }

  if (selectedChapter) {
    return <ChapterDetail chapter={selectedChapter} onBack={() => selectChapter(null)} t={t} />;
  }

  if (chapters.length === 0) {
    return <EmptyState message={t('saga_no_chapters')} />;
  }

  return (
    <div className="p-3 space-y-2">
      {chapters.map((chapter, idx) => (
        <ChapterCard
          key={chapter.id}
          chapter={chapter}
          onClick={() => selectChapter(chapter)}
          style={{ animationDelay: `${idx * 40}ms` }}
          t={t}
        />
      ))}
    </div>
  );
}

// ---- Chapter card (list view) ----

function ChapterCard({
  chapter,
  onClick,
  style,
  t,
}: {
  chapter: SagaChapter;
  onClick: () => void;
  style?: React.CSSProperties;
  t: (key: string) => string;
}) {
  const mood = getMoodColor(chapter.mood);
  const stats = chapter.era_statistics;

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-gold/20 transition-all duration-200 fade-in group"
      style={style}
    >
      {/* Era + mood badge */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#d4a574' }}>
          {t('saga_era')} {chapter.era_number}
        </span>
        {chapter.mood && (
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${mood.bg} ${mood.border} border`}
            style={{ color: mood.hex }}
          >
            {t(`saga_mood_${chapter.mood}`) || chapter.mood}
          </span>
        )}
        <span className="ml-auto text-[10px] mono text-text-3">
          T:{chapter.start_tick}–{chapter.end_tick}
        </span>
      </div>

      {/* Title */}
      <h3 className="saga-text text-[16px] font-medium leading-snug mb-1.5 group-hover:text-gold transition-colors" style={{ color: '#e4e2e8' }}>
        {chapter.chapter_title}
      </h3>

      {/* Summary */}
      <p className="text-[12px] text-text-2 leading-relaxed line-clamp-2 mb-2.5">
        {chapter.summary}
      </p>

      {/* Mini stats */}
      <div className="flex items-center gap-3 text-[10px] text-text-3">
        {stats.births > 0 && (
          <span className="flex items-center gap-1">
            <Sparkles size={10} className="text-green" />
            {stats.births}
          </span>
        )}
        {stats.deaths > 0 && (
          <span className="flex items-center gap-1">
            <XIcon size={10} className="text-orange" />
            {stats.deaths}
          </span>
        )}
        {stats.interactions > 0 && (
          <span className="flex items-center gap-1">
            <MessageCircle size={10} className="text-rose" />
            {stats.interactions}
          </span>
        )}
        {stats.concepts > 0 && (
          <span className="flex items-center gap-1">
            <Lightbulb size={10} className="text-cyan" />
            {stats.concepts}
          </span>
        )}
        {chapter.key_characters.length > 0 && (
          <span className="flex items-center gap-1 ml-auto">
            <Users size={10} />
            {chapter.key_characters.length}
          </span>
        )}
      </div>
    </button>
  );
}

// ---- Chapter detail view ----

function ChapterDetail({
  chapter,
  onBack,
  t,
}: {
  chapter: SagaChapter;
  onBack: () => void;
  t: (key: string) => string;
}) {
  const mood = getMoodColor(chapter.mood);
  const stats = chapter.era_statistics;

  return (
    <div className="p-4 fade-in">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-[12px] text-text-3 hover:text-gold transition-colors mb-4"
      >
        <ArrowLeft size={13} />
        {t('saga_back')}
      </button>

      {/* Decorative header */}
      <div className="text-center mb-5">
        <div className="saga-divider mb-3">✿</div>

        <span
          className="text-[11px] font-semibold uppercase tracking-[0.2em]"
          style={{ color: '#d4a574' }}
        >
          {t('saga_era')} {chapter.era_number}
        </span>
        <span className="block text-[10px] mono text-text-3 mt-0.5">
          {t('saga_ticks')} {chapter.start_tick}–{chapter.end_tick}
        </span>

        <h2 className="saga-text text-[22px] font-medium leading-snug mt-2" style={{ color: '#e4e2e8' }}>
          {chapter.chapter_title}
        </h2>

        {chapter.mood && (
          <span
            className={`inline-block text-[11px] px-3 py-1 rounded-full font-medium mt-2 ${mood.bg} ${mood.border} border`}
            style={{ color: mood.hex }}
          >
            {t(`saga_mood_${chapter.mood}`) || chapter.mood}
          </span>
        )}
      </div>

      {/* Narrative body */}
      <div className="saga-text text-[16px] leading-[1.85] text-text tracking-[0.01em] mb-5 whitespace-pre-line">
        {chapter.narrative}
      </div>

      {/* Decorative divider */}
      <div className="saga-divider my-5">✿</div>

      {/* Key characters */}
      {chapter.key_characters.length > 0 && (
        <div className="mb-5">
          <h4 className="text-[12px] font-semibold uppercase tracking-wider mb-2" style={{ color: '#d4a574' }}>
            <Users size={12} className="inline mr-1.5" style={{ verticalAlign: '-2px' }} />
            {t('saga_key_characters')}
          </h4>
          <div className="space-y-1.5">
            {chapter.key_characters.map((char, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]"
              >
                <span className="saga-text text-[14px] font-medium text-text">{char.name}</span>
                <span className="text-[11px] text-text-2 italic">{char.role}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Statistics */}
      <div className="mb-4">
        <h4 className="text-[12px] font-semibold uppercase tracking-wider mb-2" style={{ color: '#d4a574' }}>
          {t('saga_statistics')}
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <StatItem icon={<Sparkles size={12} className="text-green" />} label={t('saga_births')} value={stats.births} />
          <StatItem icon={<XIcon size={12} className="text-orange" />} label={t('saga_deaths')} value={stats.deaths} />
          <StatItem icon={<MessageCircle size={12} className="text-rose" />} label={t('saga_interactions')} value={stats.interactions} />
          <StatItem icon={<Lightbulb size={12} className="text-cyan" />} label={t('saga_concepts')} value={stats.concepts} />
        </div>
        <div className="flex items-center justify-between mt-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
          <span className="text-[11px] text-text-2">AI Population</span>
          <span className="text-[12px] mono text-text">
            {stats.ai_count_start} → {stats.ai_count_end}
          </span>
        </div>
      </div>

      {/* Generation info */}
      {chapter.generation_time_ms && (
        <div className="text-center text-[10px] text-text-3 mono mt-4 opacity-50">
          Generated in {chapter.generation_time_ms}ms
        </div>
      )}
    </div>
  );
}

function StatItem({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
      {icon}
      <span className="text-[11px] text-text-2">{label}</span>
      <span className="ml-auto text-[13px] mono font-medium text-text">{value}</span>
    </div>
  );
}

// ---- Empty state ----

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16">
      <div className="relative w-12 h-12 mx-auto mb-4">
        <div
          className="absolute inset-0 rounded-full border pulse-ring"
          style={{ borderColor: 'rgba(212, 165, 116, 0.3)' }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <BookOpen size={16} style={{ color: '#d4a574' }} />
        </div>
      </div>
      <p className="text-text-3 text-[12px] max-w-[220px] mx-auto leading-relaxed">{message}</p>
    </div>
  );
}
