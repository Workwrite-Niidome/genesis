import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'ja', label: '日本語' },
  { code: 'zh', label: '简体中文' },
  { code: 'ko', label: '한국어' },
  { code: 'es', label: 'Español' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
];

const SHORT_LABELS: Record<string, string> = {
  en: 'EN',
  ja: 'JP',
  zh: 'ZH',
  ko: 'KO',
  es: 'ES',
  fr: 'FR',
  de: 'DE',
};

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selectLanguage = (code: string) => {
    i18n.changeLanguage(code);
    localStorage.setItem('genesis_language', code);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="glass rounded-xl px-3 py-2 border border-border text-[10px] text-text-2
                   hover:text-text hover:border-text-3 transition-all duration-200
                   font-medium tracking-wide"
        title="Switch language"
      >
        {SHORT_LABELS[i18n.language] ?? 'EN'}
      </button>

      {open && (
        <div
          className="absolute right-0 mt-1 z-50 min-w-[140px] glass rounded-xl border border-border
                     shadow-lg py-1 flex flex-col"
        >
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => selectLanguage(lang.code)}
              className={`px-3 py-1.5 text-left text-[11px] transition-colors duration-150
                         hover:bg-white/10
                         ${i18n.language === lang.code ? 'text-text font-semibold' : 'text-text-2'}`}
            >
              <span className="inline-block w-6 font-mono text-[10px] opacity-60">
                {SHORT_LABELS[lang.code]}
              </span>
              {lang.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
