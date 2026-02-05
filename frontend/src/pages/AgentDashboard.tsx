import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Plus,
  User,
  Activity,
  MapPin,
  AlertCircle,
  LogIn,
  UserPlus,
} from 'lucide-react';
import { useObserverStore } from '../stores/observerStore';
import { useAgentStore, type AgentData } from '../stores/agentStore';
import AgentCreationWizard from '../components/agents/AgentCreationWizard';
import AgentDetailPanel from '../components/agents/AgentDetailPanel';
import LanguageSwitcher from '../components/ui/LanguageSwitcher';

export default function AgentDashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Auth state
  const { isLoggedIn, token, username, login, register, logout, loading: authLoading, error: authError } = useObserverStore();

  // Agent state
  const { agents, isLoading, error, fetchAgents, selectAgent, selectedAgentId, clearError } = useAgentStore();

  // Local state
  const [showWizard, setShowWizard] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');

  // Fetch agents on login
  useEffect(() => {
    if (isLoggedIn) {
      fetchAgents();
    }
  }, [isLoggedIn, fetchAgents]);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authUsername.trim() || !authPassword.trim()) return;
    if (authMode === 'login') {
      await login(authUsername.trim(), authPassword.trim());
    } else {
      await register(authUsername.trim(), authPassword.trim());
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'alive': return 'bg-green/10 border-green/20 text-green';
      case 'dead': return 'bg-rose/10 border-rose/20 text-rose';
      case 'recalled': return 'bg-white/[0.04] border-white/[0.08] text-text-3';
      default: return 'bg-white/[0.04] border-white/[0.08] text-text-3';
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'alive': return t('agent_alive');
      case 'dead': return t('agent_dead');
      case 'recalled': return t('agent_recalled');
      default: return status;
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

  return (
    <div className="min-h-screen bg-bg text-text">
      {/* Noise overlay */}
      <div className="noise-overlay" />

      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-border">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-5 py-3">
          {/* Left: Back + Branding */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-2 rounded-xl hover:bg-white/[0.06] text-text-3 hover:text-text transition-colors"
              title={t('agent_back')}
            >
              <ArrowLeft size={16} />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan" />
                <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-cyan pulse-glow" />
              </div>
              <span className="text-sm font-semibold tracking-[0.2em] text-text">GENESIS</span>
              <div className="w-px h-3.5 bg-border" />
              <span className="text-[10px] text-text-3 tracking-wide">{t('agent_dashboard')}</span>
            </div>
          </div>

          {/* Right: User info + Language */}
          <div className="flex items-center gap-3">
            {isLoggedIn && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-text-3">{username}</span>
                <button
                  onClick={logout}
                  className="text-[10px] text-text-3 hover:text-rose transition-colors"
                >
                  {t('observer_logout')}
                </button>
              </div>
            )}
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 py-6">
        {/* Not logged in: Auth form */}
        {!isLoggedIn && (
          <div className="flex items-center justify-center min-h-[60vh] fade-in">
            <div className="glass rounded-2xl border border-border shadow-[0_16px_80px_rgba(0,0,0,0.7)] w-full max-w-sm p-6">
              <div className="flex items-center gap-2.5 mb-6">
                <div className="w-8 h-8 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center">
                  <User size={14} className="text-cyan" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-text">
                    {authMode === 'login' ? t('observer_login') : t('observer_register')}
                  </h2>
                  <p className="text-[10px] text-text-3">{t('agent_login_required')}</p>
                </div>
              </div>

              <form onSubmit={handleAuth} className="space-y-3">
                <div>
                  <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1 block font-medium">
                    {t('observer_username')}
                  </label>
                  <input
                    type="text"
                    value={authUsername}
                    onChange={(e) => setAuthUsername(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-[10px] text-text-3 uppercase tracking-wider mb-1 block font-medium">
                    {t('observer_password')}
                  </label>
                  <input
                    type="password"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-cyan/40 transition-colors"
                  />
                </div>

                {authError && (
                  <div className="flex items-center gap-2 text-xs text-rose bg-rose/5 border border-rose/10 rounded-lg px-3 py-2">
                    <AlertCircle size={12} />
                    <span>{authError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={authLoading || !authUsername.trim() || !authPassword.trim()}
                  className="w-full py-2.5 rounded-xl bg-cyan/20 border border-cyan/30 text-sm text-cyan font-medium hover:bg-cyan/30 hover:shadow-[0_0_20px_rgba(88,213,240,0.15)] disabled:opacity-25 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                >
                  {authLoading ? (
                    <span className="animate-pulse">{t('admin_logging_in')}</span>
                  ) : authMode === 'login' ? (
                    <>
                      <LogIn size={14} />
                      {t('observer_login')}
                    </>
                  ) : (
                    <>
                      <UserPlus size={14} />
                      {t('observer_register')}
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
                  className="w-full text-center text-[10px] text-text-3 hover:text-text transition-colors py-1"
                >
                  {authMode === 'login' ? t('observer_register') : t('observer_login')}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Logged in: Dashboard */}
        {isLoggedIn && (
          <div className="fade-in">
            {/* Top bar: Title + Create button */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-text tracking-wide">{t('my_agents')}</h2>
              <button
                onClick={() => setShowWizard(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan/15 border border-cyan/30 text-sm text-cyan font-medium hover:bg-cyan/25 hover:shadow-[0_0_16px_rgba(88,213,240,0.1)] transition-all"
              >
                <Plus size={14} />
                {t('create_agent')}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 text-xs text-rose bg-rose/5 border border-rose/10 rounded-lg px-3 py-2 mb-4">
                <AlertCircle size={12} />
                <span>{error}</span>
                <button onClick={clearError} className="ml-auto text-rose/60 hover:text-rose">
                  &times;
                </button>
              </div>
            )}

            {/* Loading */}
            {isLoading && agents.length === 0 && (
              <div className="flex items-center justify-center py-16">
                <div className="w-6 h-6 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
              </div>
            )}

            {/* Two-column layout: Agent list + Detail */}
            <div className="flex gap-6 flex-col lg:flex-row">
              {/* Agent list */}
              <div className={`${selectedAgentId ? 'lg:w-[360px] shrink-0' : 'w-full'}`}>
                {!isLoading && agents.length === 0 && (
                  <div className="glass rounded-2xl border border-border p-8 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
                      <User size={24} className="text-text-3" />
                    </div>
                    <p className="text-sm text-text-3">{t('no_agents_yet')}</p>
                  </div>
                )}

                {agents.length > 0 && (
                  <div className="space-y-3">
                    {agents.map((agent: AgentData) => (
                      <button
                        key={agent.id}
                        onClick={() => {
                          selectAgent(agent.id);
                        }}
                        className={`w-full text-left glass rounded-xl border p-4 transition-all hover-lift ${
                          selectedAgentId === agent.id
                            ? 'border-cyan/30 bg-cyan/[0.03] shadow-[0_0_20px_rgba(88,213,240,0.05)]'
                            : 'border-border hover:border-white/[0.12]'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center shrink-0">
                            <span className="text-base font-medium text-cyan">
                              {agent.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-text truncate">
                                {agent.name}
                              </span>
                              <span className={`badge text-[9px] border ${statusColor(agent.status)}`}>
                                {statusLabel(agent.status)}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 mt-1">
                              <span className={`flex items-center gap-1 text-[10px] ${behaviorColor(agent.behavior_mode)}`}>
                                <Activity size={9} />
                                {t(behaviorKey(agent.behavior_mode))}
                              </span>
                              {agent.position && (
                                <span className="flex items-center gap-0.5 text-[10px] text-text-3">
                                  <MapPin size={9} />
                                  ({agent.position.x}, {agent.position.y})
                                </span>
                              )}
                              <span className="text-[10px] text-text-3">
                                {t(agent.autonomy_level)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Detail panel */}
              {selectedAgentId && (
                <div className="flex-1 min-w-0">
                  <AgentDetailPanel
                    agentId={selectedAgentId}
                    onClose={() => selectAgent(null)}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Creation Wizard */}
      <AgentCreationWizard
        open={showWizard}
        onClose={() => setShowWizard(false)}
        onCreated={() => {
          fetchAgents();
        }}
      />
    </div>
  );
}
