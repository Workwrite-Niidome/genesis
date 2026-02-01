import { useTranslation } from 'react-i18next';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ja' : 'en';
    i18n.changeLanguage(newLang);
    localStorage.setItem('genesis_language', newLang);
  };

  return (
    <button
      onClick={toggleLanguage}
      className="glass rounded-xl px-3 py-2 border border-border text-[10px] text-text-2
                 hover:text-text hover:border-text-3 transition-all duration-200
                 font-medium tracking-wide"
      title="Switch language"
    >
      {i18n.language === 'en' ? 'JP' : 'EN'}
    </button>
  );
}
