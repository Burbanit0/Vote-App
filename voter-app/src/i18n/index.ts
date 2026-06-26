import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import fr from './locales/fr';
import pgFr from './locales/playground.fr';

// i18n lazy-loading (Phase 6 — UI modernisation).
//
// `fr` is both the default and the fallback language, so it ships in the main
// bundle (it must always be available). `en` is **code-split** into its own
// chunk and fetched on demand — the majority of users never switch language and
// therefore never download it. Vite turns the dynamic `import('./locales/en')`
// into a separate asset automatically.
const lazyLoaders: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  en: () => import('./locales/en'),
};
// The playground namespace is code-split the same way (its own large vocabulary).
const pgLazyLoaders: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  en: () => import('./locales/playground.en'),
};

/** Ensure a language's bundles (translation + playground) are registered (no-op
 *  for `fr` and for already-loaded languages). Safe to call repeatedly. */
export async function loadLanguage(lng: string): Promise<void> {
  const base = lng.startsWith('en') ? 'en' : 'fr';
  if (base === 'fr') return; // fr (and anything bundled) is already present
  if (!i18n.hasResourceBundle(base, 'translation') && lazyLoaders[base]) {
    const mod = await lazyLoaders[base]();
    i18n.addResourceBundle(base, 'translation', mod.default, true, true);
  }
  if (!i18n.hasResourceBundle(base, 'playground') && pgLazyLoaders[base]) {
    const mod = await pgLazyLoaders[base]();
    i18n.addResourceBundle(base, 'playground', mod.default, true, true);
  }
}

/** Load the target bundle, THEN switch — so the UI never flashes raw keys. */
export async function switchLanguage(lng: string): Promise<void> {
  await loadLanguage(lng);
  await i18n.changeLanguage(lng);
}

const initPromise = i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fr: { translation: fr, playground: pgFr },
    },
    fallbackLng: 'fr',
    supportedLngs: ['fr', 'en'],
    // Allows registering a language's bundle AFTER init (via addResourceBundle).
    partialBundledLanguages: true,
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'votelab_lang',
    },
    interpolation: { escapeValue: true },
  });

// Resolves once the detected language's bundle is present. `main.tsx` awaits
// this before the first render so an `en`-preferring visitor never sees the
// French fallback flash.
export const i18nReady: Promise<unknown> = initPromise.then(() =>
  loadLanguage(i18n.resolvedLanguage || i18n.language || 'fr')
);

export default i18n;
