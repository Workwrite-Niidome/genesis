import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Rocket,
  ArrowLeft,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Key,
  Copy,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useDeployStore } from '../../stores/deployStore';

export default function MobileDeploySheet() {
  const { t } = useTranslation();
  const {
    availableTraits,
    providers,
    deployPanelOpen,
    loading,
    error,
    successMessage,
    agentToken,
    togglePanel,
    fetchTraits,
    fetchProviders,
    registerAgent,
    clearMessages,
  } = useDeployStore();

  const [name, setName] = useState('');
  const [selectedTraits, setSelectedTraits] = useState<string[]>([]);
  const [philosophy, setPhilosophy] = useState('');
  const [llmProvider, setLlmProvider] = useState('anthropic');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [tokenCopied, setTokenCopied] = useState(false);

  useEffect(() => {
    if (deployPanelOpen) {
      fetchTraits();
      fetchProviders();
    }
  }, [deployPanelOpen, fetchTraits, fetchProviders]);

  const toggleTrait = (trait: string) => {
    setSelectedTraits((prev) => {
      if (prev.includes(trait)) return prev.filter((t) => t !== trait);
      if (prev.length >= 3) return prev;
      return [...prev, trait];
    });
  };

  const selectedProvider = providers.find((p) => p.id === llmProvider);

  const handleDeploy = async () => {
    clearMessages();
    const ok = await registerAgent(name, selectedTraits, philosophy, llmProvider, llmApiKey, llmModel);
    if (ok) {
      setName('');
      setSelectedTraits([]);
      setPhilosophy('');
      setLlmApiKey('');
      setLlmModel('');
    }
  };

  const handleCopyToken = () => {
    if (agentToken) {
      navigator.clipboard.writeText(agentToken);
      setTokenCopied(true);
      setTimeout(() => setTokenCopied(false), 2000);
    }
  };

  const canDeploy =
    name.trim().length > 0 &&
    selectedTraits.length >= 2 &&
    selectedTraits.length <= 3 &&
    llmApiKey.trim().length >= 10 &&
    !loading;

  if (!deployPanelOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex flex-col bg-bg">
      {/* Film grain */}
      <div className="noise-overlay" />

      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 bg-surface/95 backdrop-blur-xl border-b border-border safe-top flex-shrink-0">
        <button
          onClick={togglePanel}
          className="p-2 -ml-2 rounded-lg active:bg-white/[0.08] text-text-3 touch-target"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex items-center gap-2">
          <Rocket size={16} className="text-cyan" />
          <span className="text-[14px] font-semibold text-text tracking-wide">
            {t('deploy_title')}
          </span>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* Name */}
          <div>
            <label className="text-[11px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
              {t('deploy_name')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={50}
              placeholder={t('deploy_name_placeholder')}
              className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[14px] text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors"
            />
          </div>

          {/* Traits */}
          <div>
            <label className="text-[11px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
              {t('deploy_traits')}
              <span className="ml-2 text-text-3/60">
                {selectedTraits.length}/3
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              {availableTraits.map((trait) => {
                const selected = selectedTraits.includes(trait);
                const disabled = !selected && selectedTraits.length >= 3;
                return (
                  <button
                    key={trait}
                    onClick={() => toggleTrait(trait)}
                    disabled={disabled}
                    className={`px-3 py-2 rounded-lg text-[12px] border transition-all touch-target ${
                      selected
                        ? 'bg-cyan/15 border-cyan/40 text-cyan'
                        : disabled
                          ? 'bg-white/[0.02] border-white/[0.04] text-text-3 opacity-30'
                          : 'bg-white/[0.03] border-white/[0.06] text-text-2 active:bg-white/[0.06]'
                    }`}
                  >
                    {t(`trait_${trait}`)}
                  </button>
                );
              })}
            </div>
            {selectedTraits.length < 2 && (
              <p className="text-[10px] text-text-3 mt-2">{t('deploy_traits_hint')}</p>
            )}
          </div>

          {/* Philosophy */}
          <div>
            <label className="text-[11px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
              {t('deploy_philosophy')}
              <span className="ml-1 text-text-3/40 normal-case tracking-normal">({t('deploy_optional')})</span>
            </label>
            <textarea
              value={philosophy}
              onChange={(e) => setPhilosophy(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder={t('deploy_philosophy_placeholder')}
              className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[14px] text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors resize-none"
            />
          </div>

          {/* LLM Config */}
          <div className="border-t border-white/[0.06] pt-4">
            <div className="flex items-center gap-2 mb-4">
              <Key size={14} className="text-accent" />
              <span className="text-[11px] font-medium text-text uppercase tracking-wider">
                {t('deploy_llm_config')}
              </span>
            </div>

            {/* Provider */}
            <div className="mb-4">
              <label className="text-[11px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
                {t('deploy_provider')}
              </label>
              <div className="flex gap-2">
                {providers.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setLlmProvider(p.id);
                      setLlmModel('');
                    }}
                    className={`flex-1 px-3 py-3 rounded-xl text-[12px] border transition-all touch-target ${
                      llmProvider === p.id
                        ? 'bg-accent/15 border-accent/40 text-accent'
                        : 'bg-white/[0.03] border-white/[0.06] text-text-2 active:bg-white/[0.06]'
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <div className="mb-4">
              <label className="text-[11px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
                {t('deploy_api_key')}
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={llmApiKey}
                  onChange={(e) => setLlmApiKey(e.target.value)}
                  maxLength={256}
                  placeholder={selectedProvider ? `${selectedProvider.key_prefix}...` : 'sk-...'}
                  className="w-full px-4 py-3 pr-12 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[14px] text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-3 active:text-text transition-colors touch-target"
                >
                  {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <p className="text-[10px] text-text-3 mt-2">{t('deploy_api_key_hint')}</p>
            </div>

            {/* Model */}
            <div>
              <label className="text-[11px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
                {t('deploy_model')}
                <span className="ml-1 text-text-3/40 normal-case tracking-normal">({t('deploy_optional')})</span>
              </label>
              <input
                type="text"
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                maxLength={100}
                placeholder={selectedProvider?.default_model || 'Default model'}
                className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[14px] text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors font-mono"
              />
            </div>
          </div>

          {/* Messages */}
          {error && (
            <div className="flex items-start gap-2 text-[12px] text-rose bg-rose/5 border border-rose/10 rounded-xl px-4 py-3">
              <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          {successMessage && (
            <div className="space-y-3">
              <div className="flex items-start gap-2 text-[12px] text-green bg-green/5 border border-green/10 rounded-xl px-4 py-3">
                <CheckCircle2 size={14} className="flex-shrink-0 mt-0.5" />
                <span>{successMessage}</span>
              </div>
              {agentToken && (
                <div className="bg-white/[0.03] border border-accent/20 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-medium text-accent uppercase tracking-wider">
                      {t('deploy_agent_token')}
                    </span>
                    <button
                      onClick={handleCopyToken}
                      className="flex items-center gap-1.5 text-[11px] text-text-3 active:text-text transition-colors touch-target"
                    >
                      <Copy size={12} />
                      {tokenCopied ? t('deploy_copied') : t('deploy_copy')}
                    </button>
                  </div>
                  <code className="text-[11px] text-text-2 font-mono break-all leading-relaxed block">
                    {agentToken}
                  </code>
                  <p className="text-[10px] text-text-3 mt-3">{t('deploy_token_warning')}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="px-4 pb-4 pt-2 safe-bottom flex-shrink-0">
        <button
          onClick={handleDeploy}
          disabled={!canDeploy}
          className="w-full py-3.5 rounded-xl bg-cyan/20 border border-cyan/30 text-[14px] text-cyan font-medium active:bg-cyan/30 disabled:opacity-25 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 touch-target"
        >
          {loading ? (
            <span className="animate-pulse">{t('deploy_deploying')}</span>
          ) : (
            <>
              <Sparkles size={16} />
              {t('deploy_button')}
            </>
          )}
        </button>
      </footer>
    </div>
  );
}
