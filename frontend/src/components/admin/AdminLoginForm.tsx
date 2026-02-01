import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Lock, User, LogIn, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

export default function AdminLoginForm() {
  const { t } = useTranslation();
  const { login, error, loading } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-bg relative overflow-hidden">
      {/* Background noise */}
      <div className="noise-overlay" />

      {/* Login card */}
      <div className="glass rounded-3xl border border-border shadow-[0_8px_60px_rgba(0,0,0,0.6)] p-8 w-full max-w-sm relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 mb-4">
            <Lock size={24} className="text-accent" />
          </div>
          <h1 className="text-xl font-semibold text-text tracking-wide">
            {t('admin')}
          </h1>
          <p className="text-xs text-text-3 mt-1">{t('admin_login_subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username */}
          <div className="relative">
            <User
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-3"
            />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t('admin_username')}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors"
              autoFocus
            />
          </div>

          {/* Password */}
          <div className="relative">
            <Lock
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-3"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('admin_password')}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text placeholder:text-text-3 focus:outline-none focus:border-accent/40 transition-colors"
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-center gap-2 text-rose text-xs px-1">
              <AlertCircle size={12} />
              <span>{error}</span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full py-2.5 rounded-xl bg-accent/20 border border-accent/30 text-sm text-accent font-medium hover:bg-accent/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="animate-pulse">{t('admin_logging_in')}</span>
            ) : (
              <>
                <LogIn size={14} />
                {t('admin_login')}
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
