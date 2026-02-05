import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  User,
  Eye,
  Shield,
  CheckCircle2,
} from 'lucide-react';
import { useAgentStore, type PersonalityAxis } from '../../stores/agentStore';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

const STEPS = ['agent_step_name', 'agent_step_preview', 'agent_step_autonomy', 'agent_step_confirm'] as const;

const AUTONOMY_OPTIONS = [
  { value: 'autonomous', icon: Sparkles, color: 'cyan' },
  { value: 'guided', icon: Shield, color: 'accent' },
  { value: 'semi_autonomous', icon: Eye, color: 'green' },
] as const;

export default function AgentCreationWizard({ open, onClose, onCreated }: Props) {
  const { t } = useTranslation();
  const {
    personalityPreview,
    isLoading,
    error,
    previewPersonality,
    createAgent,
    clearError,
    clearPreview,
  } = useAgentStore();

  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [autonomyLevel, setAutonomyLevel] = useState<string>('guided');
  const [createdSuccess, setCreatedSuccess] = useState(false);

  const reset = () => {
    setStep(0);
    setName('');
    setDescription('');
    setAutonomyLevel('guided');
    setCreatedSuccess(false);
    clearError();
    clearPreview();
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handlePreview = async () => {
    if (description.trim().length < 5) return;
    await previewPersonality(description);
  };

  const handleCreate = async () => {
    clearError();
    const agent = await createAgent({
      name: name.trim(),
      description: description.trim(),
      autonomy_level: autonomyLevel,
    });
    if (agent) {
      setCreatedSuccess(true);
      onCreated?.();
    }
  };

  const canNext = (): boolean => {
    switch (step) {
      case 0:
        return name.trim().length >= 1 && description.trim().length >= 5;
      case 1:
        return true; // preview is optional
      case 2:
        return !!autonomyLevel;
      case 3:
        return !isLoading;
      default:
        return false;
    }
  };

  const goNext = () => {
    if (step < STEPS.length - 1) {
      clearError();
      setStep(step + 1);
    }
  };

  const goPrev = () => {
    if (step > 0) {
      clearError();
      setStep(step - 1);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center pointer-events-auto">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative glass rounded-2xl border border-border shadow-[0_16px_80px_rgba(0,0,0,0.7)] w-full max-w-lg mx-4 fade-in max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 glass z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center">
              <User size={14} className="text-cyan" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-text">
                {t('create_agent')}
              </h2>
              <p className="text-[10px] text-text-3">
                {t(STEPS[step])} ({step + 1}/{STEPS.length})
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-text-3 hover:text-text transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-5 pt-4 pb-2">
          <div className="flex gap-1.5">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                  i <= step ? 'bg-cyan/60' : 'bg-white/[0.06]'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="p-5 min-h-[280px]">
          {createdSuccess ? (
            <div className="flex flex-col items-center justify-center py-8 gap-4 fade-in">
              <div className="w-14 h-14 rounded-2xl bg-green/10 border border-green/20 flex items-center justify-center">
                <CheckCircle2 size={28} className="text-green" />
              </div>
              <p className="text-sm text-green font-medium">{t('agent_created_success')}</p>
              {personalityPreview && (
                <div className="w-full mt-2">
                  <p className="text-[10px] text-text-3 uppercase tracking-wider mb-2 font-medium">
                    {t('agent_summary')}
                  </p>
                  <p className="text-xs text-text-2 leading-relaxed bg-white/[0.03] rounded-xl border border-white/[0.06] p-3">
                    {personalityPreview.summary}
                  </p>
                </div>
              )}
              <button
                onClick={handleClose}
                className="mt-2 px-6 py-2 rounded-xl bg-white/[0.06] border border-white/[0.08] text-sm text-text hover:bg-white/[0.1] transition-colors"
              >
                {t('board_back')}
              </button>
            </div>
          ) : (
            <>
              {/* Step 0: Name & Description */}
              {step === 0 && (
                <div className="space-y-4 fade-in">
                  <div>
                    <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
                      {t('agent_name')}
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      maxLength={50}
                      placeholder={t('agent_name_placeholder')}
                      className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors"
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
                      {t('agent_description')}
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      maxLength={1000}
                      rows={5}
                      placeholder={t('agent_desc_placeholder')}
                      className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors resize-none"
                    />
                    <p className="text-[9px] text-text-3 mt-1 text-right">
                      {description.length}/1000
                    </p>
                  </div>
                </div>
              )}

              {/* Step 1: Preview personality */}
              {step === 1 && (
                <div className="space-y-4 fade-in">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] text-text-3 uppercase tracking-wider font-medium">
                      {t('personality_preview')}
                    </p>
                    <button
                      onClick={handlePreview}
                      disabled={isLoading || description.trim().length < 5}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan/15 border border-cyan/30 text-xs text-cyan hover:bg-cyan/25 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                    >
                      <Sparkles size={12} />
                      {isLoading ? t('agent_previewing') : t('agent_preview_btn')}
                    </button>
                  </div>

                  {!personalityPreview && !isLoading && (
                    <div className="flex items-center justify-center py-10 text-text-3 text-xs">
                      {t('agent_desc_placeholder')}
                    </div>
                  )}

                  {isLoading && !personalityPreview && (
                    <div className="flex items-center justify-center py-10">
                      <div className="w-6 h-6 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
                    </div>
                  )}

                  {personalityPreview && (
                    <div className="space-y-4">
                      {/* Axes as bars */}
                      <div>
                        <p className="text-[10px] text-text-3 uppercase tracking-wider mb-2 font-medium">
                          {t('agent_personality_axes')}
                        </p>
                        <div className="space-y-2">
                          {personalityPreview.axes.map((axis: PersonalityAxis) => (
                            <div key={axis.axis}>
                              <div className="flex items-center justify-between mb-0.5">
                                <span className="text-[10px] text-text-2">{axis.label || axis.axis}</span>
                                <span className="text-[10px] mono text-text-3">{axis.value}</span>
                              </div>
                              <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-cyan/60 to-cyan rounded-full transition-all duration-500"
                                  style={{ width: `${Math.min(100, Math.max(0, axis.value))}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Summary */}
                      <div>
                        <p className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 font-medium">
                          {t('agent_summary')}
                        </p>
                        <p className="text-xs text-text-2 leading-relaxed bg-white/[0.03] rounded-xl border border-white/[0.06] p-3">
                          {personalityPreview.summary}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Step 2: Autonomy level */}
              {step === 2 && (
                <div className="space-y-4 fade-in">
                  <p className="text-[10px] text-text-3 uppercase tracking-wider font-medium">
                    {t('autonomy_level')}
                  </p>
                  <div className="space-y-3">
                    {AUTONOMY_OPTIONS.map((opt) => {
                      const Icon = opt.icon;
                      const selected = autonomyLevel === opt.value;
                      const colorClasses = {
                        cyan: {
                          selected: 'bg-cyan/10 border-cyan/40 shadow-[0_0_12px_rgba(88,213,240,0.08)]',
                          icon: 'text-cyan',
                          iconBg: 'bg-cyan/10 border-cyan/20',
                        },
                        accent: {
                          selected: 'bg-accent/10 border-accent/40 shadow-[0_0_12px_rgba(124,91,245,0.08)]',
                          icon: 'text-accent',
                          iconBg: 'bg-accent/10 border-accent/20',
                        },
                        green: {
                          selected: 'bg-green/10 border-green/40 shadow-[0_0_12px_rgba(52,211,153,0.08)]',
                          icon: 'text-green',
                          iconBg: 'bg-green/10 border-green/20',
                        },
                      }[opt.color];
                      return (
                        <button
                          key={opt.value}
                          onClick={() => setAutonomyLevel(opt.value)}
                          className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left ${
                            selected
                              ? colorClasses.selected
                              : 'bg-white/[0.02] border-white/[0.06] hover:border-white/[0.12] hover:bg-white/[0.04]'
                          }`}
                        >
                          <div className={`w-8 h-8 rounded-lg border flex items-center justify-center ${
                            selected ? colorClasses.iconBg : 'bg-white/[0.04] border-white/[0.08]'
                          }`}>
                            <Icon size={14} className={selected ? colorClasses.icon : 'text-text-3'} />
                          </div>
                          <div>
                            <p className={`text-sm font-medium ${selected ? 'text-text' : 'text-text-2'}`}>
                              {t(opt.value)}
                            </p>
                            <p className="text-[10px] text-text-3 mt-0.5">
                              {opt.value === 'autonomous' && 'Agent acts fully independently based on its personality.'}
                              {opt.value === 'guided' && 'You can set policy directions to guide behavior.'}
                              {opt.value === 'semi_autonomous' && 'Mix of self-direction and your policy guidance.'}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Step 3: Confirm */}
              {step === 3 && (
                <div className="space-y-4 fade-in">
                  <p className="text-[10px] text-text-3 uppercase tracking-wider font-medium mb-3">
                    {t('agent_step_confirm')}
                  </p>

                  <div className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-text-3 uppercase tracking-wider">{t('agent_name')}</span>
                      <span className="text-sm text-text font-medium">{name}</span>
                    </div>
                    <div className="border-t border-white/[0.04]" />
                    <div>
                      <span className="text-[10px] text-text-3 uppercase tracking-wider block mb-1">{t('agent_description')}</span>
                      <p className="text-xs text-text-2 leading-relaxed">{description}</p>
                    </div>
                    <div className="border-t border-white/[0.04]" />
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-text-3 uppercase tracking-wider">{t('autonomy_level')}</span>
                      <span className="text-xs text-cyan font-medium">{t(autonomyLevel)}</span>
                    </div>
                  </div>

                  {personalityPreview && (
                    <div className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-4">
                      <p className="text-[10px] text-text-3 uppercase tracking-wider mb-2 font-medium">
                        {t('personality_preview')}
                      </p>
                      <p className="text-xs text-text-2 leading-relaxed">
                        {personalityPreview.summary}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 text-xs text-rose bg-rose/5 border border-rose/10 rounded-lg px-3 py-2 mt-4">
              <AlertCircle size={12} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        {!createdSuccess && (
          <div className="px-5 pb-5 flex items-center justify-between gap-3">
            {step > 0 ? (
              <button
                onClick={goPrev}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text-2 hover:bg-white/[0.08] transition-colors"
              >
                <ChevronLeft size={14} />
                {t('agent_prev')}
              </button>
            ) : (
              <div />
            )}

            {step < STEPS.length - 1 ? (
              <button
                onClick={goNext}
                disabled={!canNext()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-cyan/20 border border-cyan/30 text-sm text-cyan font-medium hover:bg-cyan/30 disabled:opacity-25 disabled:cursor-not-allowed transition-all"
              >
                {t('agent_next')}
                <ChevronRight size={14} />
              </button>
            ) : (
              <button
                onClick={handleCreate}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-cyan/20 border border-cyan/30 text-sm text-cyan font-medium hover:bg-cyan/30 hover:shadow-[0_0_20px_rgba(88,213,240,0.15)] disabled:opacity-25 disabled:cursor-not-allowed transition-all"
              >
                {isLoading ? (
                  <span className="animate-pulse">{t('creating_agent')}</span>
                ) : (
                  <>
                    <Sparkles size={14} />
                    {t('confirm_create')}
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
