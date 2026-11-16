import { switchLanguage } from './index';

describe('language preference', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('remembers the language the visitor switches to', async () => {
    await switchLanguage('fr');
    expect(localStorage.getItem('votelab_lang')).toBe('fr');
    await switchLanguage('en');
    expect(localStorage.getItem('votelab_lang')).toBe('en');
  });

  it('sets <html lang> to the language, and "en" for the pseudo-locale', async () => {
    await switchLanguage('en');
    expect(document.documentElement.lang).toBe('en');
    await switchLanguage('fr');
    expect(document.documentElement.lang).toBe('fr');
    await switchLanguage('pseudo'); // not a valid language tag; English underneath
    expect(document.documentElement.lang).toBe('en');
  });

  // i18next is one instance across vi.resetModules(): the listener the setup file's import left
  // on it would write init's own "fr" into storage before the fresh module reads it. So storage is
  // stubbed: it holds `saved` for the key, and a write goes nowhere.
  async function startWithSaved(saved: string) {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation((k) =>
      k === 'votelab_lang' ? saved : null
    );
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.resetModules();
    const fresh = await import('./index');
    await fresh.i18nReady;
    return fresh.default;
  }

  it.each(['klingon', '', 'EN', 'english', '{"lng":"en"}', 'fr_FR'])(
    'ignores a saved language that is not one the app has (%j): the browser language decides',
    async (junk) => {
      // jsdom's navigator.languages is ['en-US', 'en'].
      expect((await startWithSaved(junk)).resolvedLanguage).toBe('en');
    }
  );

  it.each([
    ['fr', 'fr'],
    ['en-GB', 'en'],
    ['pseudo', 'pseudo'],
  ])('keeps a saved language the app has (%j, resolved to %j)', async (saved, resolved) => {
    expect((await startWithSaved(saved)).resolvedLanguage).toBe(resolved);
  });

  it('starts from the browser language when storage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage disabled');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage disabled');
    });
    vi.resetModules();
    const fresh = await import('./index');
    await fresh.i18nReady;
    // jsdom's navigator.languages is ['en-US', 'en'].
    expect(fresh.default.resolvedLanguage).toBe('en');
    await expect(fresh.switchLanguage('fr')).resolves.toBeUndefined();
  });
});
