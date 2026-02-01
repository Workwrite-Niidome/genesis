import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Rocket,
  X,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Key,
  Copy,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useDeployStore } from '../../stores/deployStore';

export default function DeployPanel() {
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
    fetchTraits();
    fetchProviders();
  }, [fetchTraits, fetchProviders]);

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
    <div className="absolute inset-0 z-50 pointer-events-auto flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={togglePanel}
      />

      {/* Modal */}
      <div className="relative glass rounded-2xl border border-border shadow-[0_16px_80px_rgba(0,0,0,0.7)] w-full max-w-md mx-4 fade-in max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 glass z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center">
              <Rocket size={14} className="text-cyan" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-text">
                {t('deploy_title')}
              </h2>
              <p className="text-[10px] text-text-3">
                {t('deploy_byok_subtitle')}
              </p>
            </div>
          </div>
          <button
            onClick={togglePanel}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-text-3 hover:text-text transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Name */}
          <div>
            <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
              {t('deploy_name')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={50}
              placeholder={t('deploy_name_placeholder')}
              className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors"
              autoFocus
            />
          </div>

          {/* Traits */}
          <div>
            <label className="text-[10px] text-text-3 uppercase tracking-wider mb-2 block font-medium">
              {t('deploy_traits')}
              <span className="ml-1.5 text-text-3/60">
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
                    className={`px-3 py-1 rounded-lg text-xs border transition-all ${
                      selected
                        ? 'bg-cyan/15 border-cyan/40 text-cyan shadow-[0_0_8px_rgba(88,213,240,0.1)]'
                        : disabled
                          ? 'bg-white/[0.02] border-white/[0.04] text-text-3 opacity-30 cursor-not-allowed'
                          : 'bg-white/[0.03] border-white/[0.06] text-text-2 hover:border-white/[0.15] hover:bg-white/[0.05]'
                    }`}
                  >
                    {t(`trait_${trait}`)}
                  </button>
                );
              })}
            </div>
            {selectedTraits.length < 2 && (
              <p className="text-[9px] text-text-3 mt-1.5">{t('deploy_traits_hint')}</p>
            )}
          </div>

          {/* Philosophy */}
          <div>
            <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
              {t('deploy_philosophy')}
              <span className="ml-1 text-text-3/40 normal-case tracking-normal">({t('deploy_optional')})</span>
            </label>
            <textarea
              value={philosophy}
              onChange={(e) => setPhilosophy(e.target.value)}
              maxLength={500}
              rows={2}
              placeholder={t('deploy_philosophy_placeholder')}
              className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors resize-none"
            />
          </div>

          {/* Divider */}
          <div className="border-t border-white/[0.06] pt-4">
            <div className="flex items-center gap-2 mb-3">
              <Key size={12} className="text-accent" />
              <span className="text-[10px] font-medium text-text uppercase tracking-wider">
                {t('deploy_llm_config')}
              </span>
            </div>

            {/* Provider */}
            <div className="mb-3">
              <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
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
                    className={`flex-1 px-3 py-2 rounded-xl text-xs border transition-all text-center ${
                      llmProvider === p.id
                        ? 'bg-accent/15 border-accent/40 text-accent'
                        : 'bg-white/[0.03] border-white/[0.06] text-text-2 hover:border-white/[0.15]'
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <div className="mb-3">
              <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
                {t('deploy_api_key')}
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={llmApiKey}
                  onChange={(e) => setLlmApiKey(e.target.value)}
                  maxLength={256}
                  placeholder={selectedProvider ? `${selectedProvider.key_prefix}...` : 'sk-...'}
                  className="w-full px-3.5 py-2 pr-10 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-3 hover:text-text transition-colors"
                >
                  {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="text-[9px] text-text-3 mt-1">{t('deploy_api_key_hint')}</p>
            </div>

            {/* Model override */}
            <div>
              <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1.5 block font-medium">
                {t('deploy_model')}
                <span className="ml-1 text-text-3/40 normal-case tracking-normal">({t('deploy_optional')})</span>
              </label>
              <input
                type="text"
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                maxLength={100}
                placeholder={selectedProvider?.default_model || 'Default model'}
                className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors font-mono"
              />
            </div>
          </div>

          {/* Messages */}
          {error && (
            <div className="flex items-center gap-2 text-xs text-rose bg-rose/5 border border-rose/10 rounded-lg px-3 py-2">
              <AlertCircle size={12} />
              <span>{error}</span>
            </div>
          )}
          {successMessage && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-green bg-green/5 border border-green/10 rounded-lg px-3 py-2">
                <CheckCircle2 size={12} />
                <span>{successMessage}</span>
              </div>
              {agentToken && (
                <div className="bg-white/[0.03] border border-accent/20 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[9px] font-medium text-accent uppercase tracking-wider">
                      {t('deploy_agent_token')}
                    </span>
                    <button
                      onClick={handleCopyToken}
                      className="flex items-center gap-1 text-[9px] text-text-3 hover:text-text transition-colors"
                    >
                      <Copy size={10} />
                      {tokenCopied ? t('deploy_copied') : t('deploy_copy')}
                    </button>
                  </div>
                  <code className="text-[10px] text-text-2 font-mono break-all leading-relaxed">
                    {agentToken}
                  </code>
                  <p className="text-[9px] text-text-3 mt-2">{t('deploy_token_warning')}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 pb-5">
          <button
            onClick={handleDeploy}
            disabled={!canDeploy}
            className="w-full py-2.5 rounded-xl bg-cyan/20 border border-cyan/30 text-sm text-cyan font-medium hover:bg-cyan/30 hover:shadow-[0_0_20px_rgba(88,213,240,0.15)] disabled:opacity-25 disabled:cursor-not-allowed disabled:hover:shadow-none transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="animate-pulse">{t('deploy_deploying')}</span>
            ) : (
              <>
                <Sparkles size={14} />
                {t('deploy_button')}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
