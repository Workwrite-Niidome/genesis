import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Heart,
  Zap,
  Brain,
  Users,
  ScrollText,
  Activity,
  Shield,
  AlertTriangle,
  Trash2,
  Send,
  MapPin,
} from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import type {
  AgentDetail,
  PersonalityAxis,
  NeedBar,
  Relationship,
  MemoryEntry,
  EventEntry,
} from '../../stores/agentStore';

interface Props {
  agentId: string;
  onClose: () => void;
}

export default function AgentDetailPanel({ agentId, onClose }: Props) {
  const { t } = useTranslation();
  const {
    selectedAgentDetail: detail,
    isLoading,
    error,
    fetchAgentDetail,
    updatePolicy,
    recallAgent,
    clearError,
  } = useAgentStore();

  const [policyText, setPolicyText] = useState('');
  const [showRecallConfirm, setShowRecallConfirm] = useState(false);
  const [activeTab, setActiveTab] = useState<'personality' | 'memories' | 'events' | 'relationships'>('personality');

  useEffect(() => {
    fetchAgentDetail(agentId);
  }, [agentId, fetchAgentDetail]);

  useEffect(() => {
    if (detail?.policy) {
      setPolicyText(detail.policy);
    }
  }, [detail?.policy]);

  const handleUpdatePolicy = async () => {
    if (!detail || !policyText.trim()) return;
    await updatePolicy(detail.id, policyText.trim());
  };

  const handleRecall = async () => {
    if (!detail) return;
    const ok = await recallAgent(detail.id);
    if (ok) {
      onClose();
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'alive': return 'text-green';
      case 'dead': return 'text-rose';
      case 'recalled': return 'text-text-3';
      default: return 'text-text-3';
    }
  };

  const statusBadgeBg = (status: string) => {
    switch (status) {
      case 'alive': return 'bg-green/10 border-green/20';
      case 'dead': return 'bg-rose/10 border-rose/20';
      case 'recalled': return 'bg-white/[0.04] border-white/[0.08]';
      default: return 'bg-white/[0.04] border-white/[0.08]';
    }
  };

  const behaviorColor = (mode: string) => {
    switch (mode) {
      case 'normal': return 'text-green';
      case 'desperate': return 'text-orange';
      case 'rampage': return 'text-rose';
      default: return 'text-text-3';
    }
  };

  const behaviorKey = (mode: string) => {
    switch (mode) {
      case 'normal': return 'behavior_normal';
      case 'desperate': return 'behavior_desperate';
      case 'rampage': return 'behavior_rampage';
      default: return mode;
    }
  };

  const tabs = [
    { key: 'personality' as const, icon: Brain, label: t('personality') },
    { key: 'memories' as const, icon: ScrollText, label: t('recent_memories') },
    { key: 'events' as const, icon: Activity, label: t('recent_events') },
    { key: 'relationships' as const, icon: Users, label: t('relationships') },
  ];

  if (isLoading && !detail) {
    return (
      <div className="glass rounded-2xl border border-border p-6 fade-in">
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!detail) {
    return null;
  }

  const canEditPolicy = detail.autonomy_level !== 'autonomous' && detail.status === 'alive';

  return (
    <div className="glass rounded-2xl border border-border fade-in overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center">
            <span className="text-lg">{detail.name.charAt(0).toUpperCase()}</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text">{detail.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`badge text-[9px] border ${statusBadgeBg(detail.status)} ${statusColor(detail.status)}`}>
                {detail.status === 'alive' ? t('agent_alive') : detail.status === 'dead' ? t('agent_dead') : t('agent_recalled')}
              </span>
              <span className={`text-[10px] ${behaviorColor(detail.behavior_mode)}`}>
                {t(behaviorKey(detail.behavior_mode))}
              </span>
              {detail.position && (
                <span className="flex items-center gap-0.5 text-[10px] text-text-3">
                  <MapPin size={9} />
                  ({detail.position.x}, {detail.position.y})
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-text-3 hover:text-text transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/[0.06] px-3">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-[10px] font-medium border-b-2 transition-colors ${
                active
                  ? 'border-cyan text-cyan'
                  : 'border-transparent text-text-3 hover:text-text-2'
              }`}
            >
              <Icon size={11} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="p-5 max-h-[60vh] overflow-y-auto">
        {/* Personality Tab */}
        {activeTab === 'personality' && (
          <div className="space-y-5 fade-in">
            {/* Description */}
            {detail.description && (
              <div>
                <p className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 font-medium">
                  {t('agent_description')}
                </p>
                <p className="text-xs text-text-2 leading-relaxed">{detail.description}</p>
              </div>
            )}

            {/* Personality Axes */}
            {detail.personality_axes && detail.personality_axes.length > 0 && (
              <div>
                <p className="text-[10px] text-text-3 uppercase tracking-wider mb-2 font-medium">
                  {t('agent_personality_axes')}
                </p>
                <div className="space-y-2">
                  {detail.personality_axes.map((axis: PersonalityAxis) => (
                    <div key={axis.axis}>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-[10px] text-text-2">{axis.label || axis.axis}</span>
                        <span className="text-[10px] mono text-text-3">{axis.value}</span>
                      </div>
                      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-accent/60 to-accent rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, Math.max(0, axis.value))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Needs */}
            {detail.needs && detail.needs.length > 0 && (
              <div>
                <p className="text-[10px] text-text-3 uppercase tracking-wider mb-2 font-medium">
                  {t('agent_needs')}
                </p>
                <div className="space-y-2">
                  {detail.needs.map((need: NeedBar) => {
                    const color = need.value > 70 ? 'from-green/60 to-green' :
                                  need.value > 30 ? 'from-orange/60 to-orange' :
                                  'from-rose/60 to-rose';
                    return (
                      <div key={need.need}>
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-[10px] text-text-2">{need.label || need.need}</span>
                          <span className="text-[10px] mono text-text-3">{need.value}%</span>
                        </div>
                        <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className={`h-full bg-gradient-to-r ${color} rounded-full transition-all duration-500`}
                            style={{ width: `${Math.min(100, Math.max(0, need.value))}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Memories Tab */}
        {activeTab === 'memories' && (
          <div className="space-y-2 fade-in">
            {detail.recent_memories && detail.recent_memories.length > 0 ? (
              detail.recent_memories.map((mem: MemoryEntry) => (
                <div
                  key={mem.id}
                  className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-3 hover:border-white/[0.1] transition-colors"
                >
                  <p className="text-xs text-text-2 leading-relaxed">{mem.content}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-[9px] text-text-3 mono">Tick {mem.tick}</span>
                    <span className="flex items-center gap-0.5 text-[9px] text-accent">
                      <Zap size={8} />
                      {mem.importance}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-center py-8 text-text-3 text-xs">
                {t('agent_no_memories')}
              </div>
            )}
          </div>
        )}

        {/* Events Tab */}
        {activeTab === 'events' && (
          <div className="space-y-2 fade-in">
            {detail.recent_events && detail.recent_events.length > 0 ? (
              detail.recent_events.map((evt: EventEntry) => (
                <div
                  key={evt.id}
                  className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-3 hover:border-white/[0.1] transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge text-[9px] bg-cyan/10 border border-cyan/20 text-cyan">
                      {evt.action}
                    </span>
                    <span className="text-[9px] text-text-3 mono">Tick {evt.tick}</span>
                  </div>
                  <p className="text-xs text-text-2 leading-relaxed">{evt.description}</p>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-center py-8 text-text-3 text-xs">
                {t('agent_no_events')}
              </div>
            )}
          </div>
        )}

        {/* Relationships Tab */}
        {activeTab === 'relationships' && (
          <div className="space-y-3 fade-in">
            {detail.relationships && detail.relationships.length > 0 ? (
              detail.relationships.map((rel: Relationship) => (
                <div
                  key={rel.target_id}
                  className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-3 hover:border-white/[0.1] transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text font-medium">{rel.target_name}</span>
                    {rel.label && (
                      <span className="text-[9px] text-text-3">{rel.label}</span>
                    )}
                  </div>
                  <div className="space-y-1.5">
                    {/* Trust */}
                    <div className="flex items-center gap-2">
                      <Heart size={10} className="text-green shrink-0" />
                      <span className="text-[9px] text-text-3 w-10 shrink-0">Trust</span>
                      <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden relative">
                        {/* Center marker for -100 to 100 range */}
                        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/[0.15]" />
                        <div
                          className={`absolute top-0 h-full rounded-full transition-all duration-500 ${
                            rel.trust >= 0
                              ? 'bg-gradient-to-r from-green/40 to-green left-1/2'
                              : 'bg-gradient-to-l from-rose/40 to-rose right-1/2'
                          }`}
                          style={{
                            width: `${Math.abs(rel.trust) / 2}%`,
                            ...(rel.trust < 0 ? { right: '50%', left: 'auto' } : { left: '50%' }),
                          }}
                        />
                      </div>
                      <span className="text-[9px] mono text-text-3 w-8 text-right shrink-0">{rel.trust}</span>
                    </div>
                    {/* Anger */}
                    <div className="flex items-center gap-2">
                      <Zap size={10} className="text-orange shrink-0" />
                      <span className="text-[9px] text-text-3 w-10 shrink-0">Anger</span>
                      <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-orange/60 to-orange rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, Math.max(0, rel.anger))}%` }}
                        />
                      </div>
                      <span className="text-[9px] mono text-text-3 w-8 text-right shrink-0">{rel.anger}</span>
                    </div>
                    {/* Fear */}
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={10} className="text-accent shrink-0" />
                      <span className="text-[9px] text-text-3 w-10 shrink-0">Fear</span>
                      <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-accent/60 to-accent rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, Math.max(0, rel.fear))}%` }}
                        />
                      </div>
                      <span className="text-[9px] mono text-text-3 w-8 text-right shrink-0">{rel.fear}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-center py-8 text-text-3 text-xs">
                {t('agent_no_relationships')}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Policy section (for guided / semi-autonomous agents) */}
      {canEditPolicy && (
        <div className="px-5 pb-4 border-t border-white/[0.06] pt-4">
          <p className="text-[10px] text-text-3 uppercase tracking-wider mb-2 font-medium flex items-center gap-1.5">
            <Shield size={10} />
            {t('policy_directions')}
          </p>
          <div className="flex gap-2">
            <textarea
              value={policyText}
              onChange={(e) => setPolicyText(e.target.value)}
              maxLength={2000}
              rows={2}
              placeholder={t('agent_policy_placeholder')}
              className="flex-1 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors resize-none"
            />
            <button
              onClick={handleUpdatePolicy}
              disabled={isLoading || !policyText.trim()}
              className="self-end px-3 py-2 rounded-xl bg-accent/15 border border-accent/30 text-accent hover:bg-accent/25 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <Send size={12} />
            </button>
          </div>
        </div>
      )}

      {/* Recall button */}
      {detail.status === 'alive' && (
        <div className="px-5 pb-5 border-t border-white/[0.06] pt-4">
          {!showRecallConfirm ? (
            <button
              onClick={() => setShowRecallConfirm(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose/5 border border-rose/20 text-xs text-rose hover:bg-rose/10 hover:border-rose/30 transition-all"
            >
              <Trash2 size={12} />
              {t('recall_agent')}
            </button>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-rose">{t('confirm_recall')}</p>
              <div className="flex gap-2">
                <button
                  onClick={handleRecall}
                  disabled={isLoading}
                  className="px-4 py-2 rounded-xl bg-rose/20 border border-rose/40 text-xs text-rose font-medium hover:bg-rose/30 disabled:opacity-30 transition-all"
                >
                  {t('recall_agent')}
                </button>
                <button
                  onClick={() => setShowRecallConfirm(false)}
                  className="px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs text-text-2 hover:bg-white/[0.08] transition-colors"
                >
                  {t('admin_reset_cancel')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-5 pb-4">
          <div className="flex items-center gap-2 text-xs text-rose bg-rose/5 border border-rose/10 rounded-lg px-3 py-2">
            <AlertTriangle size={12} />
            <span>{error}</span>
            <button onClick={clearError} className="ml-auto text-rose/60 hover:text-rose">
              <X size={10} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
