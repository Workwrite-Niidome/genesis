/**
 * GENESIS v3 - Translation Service (Frontend)
 *
 * Calls the backend /api/v3/translate endpoint for on-demand text translation.
 * Includes a local in-memory cache to avoid redundant network calls.
 */

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TranslateResult {
  translated_text: string;
  source_lang: string;
  target_lang: string;
}

// ---------------------------------------------------------------------------
// In-memory cache  (key = `${text}:${target}`)
// ---------------------------------------------------------------------------

const _cache = new Map<string, string>();
const CACHE_MAX = 500;

function cacheKey(text: string, targetLang: string): string {
  return `${text}::${targetLang}`;
}

function cacheGet(text: string, targetLang: string): string | undefined {
  return _cache.get(cacheKey(text, targetLang));
}

function cacheSet(text: string, targetLang: string, translated: string): void {
  // Evict oldest entries when cache grows too large
  if (_cache.size >= CACHE_MAX) {
    const firstKey = _cache.keys().next().value;
    if (firstKey !== undefined) {
      _cache.delete(firstKey);
    }
  }
  _cache.set(cacheKey(text, targetLang), translated);
}

// ---------------------------------------------------------------------------
// Map i18next language codes to DeepL-style codes
// ---------------------------------------------------------------------------

const LANG_MAP: Record<string, string> = {
  en: 'EN',
  ja: 'JA',
  zh: 'ZH',
  ko: 'KO',
  es: 'ES',
  fr: 'FR',
  de: 'DE',
};

export function normalizeToDeepL(code: string): string {
  return LANG_MAP[code.toLowerCase()] ?? code.toUpperCase();
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Translate text to the user's preferred language.
 * Returns the original text if translation fails or is unnecessary.
 */
export async function translateText(
  text: string,
  targetLang: string,
  sourceLang?: string,
): Promise<string> {
  const target = normalizeToDeepL(targetLang);
  const source = sourceLang ? normalizeToDeepL(sourceLang) : undefined;

  // Same language? No translation needed.
  if (source && source === target) {
    return text;
  }

  // Check local cache
  const cached = cacheGet(text, target);
  if (cached !== undefined) {
    return cached;
  }

  try {
    const res = await fetch(`${API_BASE}/v3/translate/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        target_lang: target,
        source_lang: source ?? undefined,
      }),
    });

    if (!res.ok) {
      console.warn('[Translation] API error:', res.status);
      return text;
    }

    const data: TranslateResult = await res.json();
    const translated = data.translated_text;

    // Cache the result
    cacheSet(text, target, translated);

    return translated;
  } catch (err) {
    console.warn('[Translation] Network error:', err);
    return text;
  }
}

/**
 * Returns true if the source language differs from the user's language,
 * meaning translation is recommended.
 */
export function needsTranslation(
  sourceLang: string | undefined,
  userLang: string,
): boolean {
  if (!sourceLang) return false;
  return normalizeToDeepL(sourceLang) !== normalizeToDeepL(userLang);
}
