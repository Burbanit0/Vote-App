import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
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
  // Pseudo-locale (Lot 7, PLAN_SOLIDITE_TECHNIQUE.md): every string accented
  // and ~35% longer, to catch layout overflow/truncation before a real
  // second language does. Never surfaced in the UI's own language switcher —
  // only reachable via `localStorage.votelab_lang`, e2e's
  // `tests/e2e/pseudo-locale.spec.ts` uses the latter.
  pseudo: () => import('./locales/pseudo'),
};
// The playground namespace is code-split the same way (its own large vocabulary).
const pgLazyLoaders: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  en: () => import('./locales/playground.en'),
  pseudo: () => import('./locales/playground.pseudo'),
};

/** Ensure a language's bundles (translation + playground) are registered (no-op
 *  for `fr` and for already-loaded languages). Safe to call repeatedly. */
export async function loadLanguage(lng: string): Promise<void> {
  const base = lng.startsWith('en') ? 'en' : lng.startsWith('pseudo') ? 'pseudo' : 'fr';
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

const LANG_KEY = 'votelab_lang';

function savedLanguage(): string | null {
  try {
    return localStorage.getItem(LANG_KEY);
  } catch {
    return null; // storage disabled
  }
}

const initPromise = i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr, playground: pgFr },
  },
  fallbackLng: 'fr',
  supportedLngs: ['fr', 'en', 'pseudo'],
  // Allows registering a language's bundle AFTER init (via addResourceBundle).
  partialBundledLanguages: true,
  interpolation: { escapeValue: true },
});

// Resolves once the preferred language's bundle is present AND active. `main.tsx`
// awaits this before the first render so an `en`-preferring visitor never sees
// the French fallback flash. Preference: the saved choice, else the browser's
// first supported language, else French. The choice is persisted only from here
// on, so init's own switch to the `fr` fallback never overwrites a saved one.
export const i18nReady: Promise<unknown> = initPromise
  .then(() =>
    switchLanguage(savedLanguage() ?? navigator.languages.find((l) => /^(fr|en)\b/.test(l)) ?? 'fr')
  )
  .then(() =>
    i18n.on('languageChanged', (lng) => {
      try {
        localStorage.setItem(LANG_KEY, lng);
      } catch {
        // storage disabled — the choice just won't survive a reload
      }
    })
  );

export default i18n;
