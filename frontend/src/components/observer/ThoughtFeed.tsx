import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Eye, Lightbulb, MessageCircle, Compass } from 'lucide-react';
import { useThoughtStore } from '../../stores/thoughtStore';
import { useAIStore } from '../../stores/aiStore';
import type { AIThought } from '../../types/world';

const thoughtIcons: Record<string, typeof Brain> = {
  reflection: Brain,
  reaction: MessageCircle,
  intention: Lightbulb,
  observation: Eye,
};

const thoughtColors: Record<string, string> = {
  reflection: 'text-accent',
  reaction: 'text-rose',
  intention: 'text-cyan',
  observation: 'text-green',
};

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 10) return 'now';
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h`;
}

function ThoughtEntry({ thought }: { thought: AIThought }) {
  const selectAI = useAIStore((s) => s.selectAI);
  const Icon = thoughtIcons[thought.thought_type] || Compass;
  const colorClass = thoughtColors[thought.thought_type] || 'text-text-3';

  return (
    <button
      onClick={() => selectAI(thought.ai_id)}
      className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200 group"
    >
      <div className="flex items-start gap-2">
        <div className={`mt-0.5 flex-shrink-0 ${colorClass}`}>
          <Icon size={12} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[11px] font-medium text-accent group-hover:text-text transition-colors truncate">
              {thought.ai_name || 'Unknown'}
            </span>
            <span className="text-[8px] text-text-3 flex-shrink-0">
              {formatRelativeTime(thought.created_at)}
            </span>
          </div>
          <p className="text-[10px] text-text-2 leading-relaxed line-clamp-2">
            {thought.content}
          </p>
        </div>
      </div>
    </button>
  );
}

export default function ThoughtFeed() {
  const { t } = useTranslation();
  const { thoughts, startPolling, stopPolling } = useThoughtStore();

  useEffect(() => {
    startPolling();
    return () => stopPolling();
  }, [startPolling, stopPolling]);

  if (thoughts.length === 0) return null;

  return (
    <div className="absolute top-20 right-4 z-40 w-72 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden">
        {/* Header */}
        <div className="px-4 py-2.5 border-b border-white/[0.04]">
          <div className="flex items-center gap-2">
            <Brain size={12} className="text-accent" />
            <span className="text-[11px] font-medium text-text uppercase tracking-wider">
              {t('thoughts')}
            </span>
            <span className="text-[9px] text-text-3 ml-auto">
              {thoughts.length}
            </span>
          </div>
        </div>

        {/* Thought list */}
        <div className="p-2 space-y-1.5 max-h-[400px] overflow-y-auto">
          {thoughts.map((thought) => (
            <ThoughtEntry key={thought.id} thought={thought} />
          ))}
        </div>
      </div>
    </div>
  );
}
