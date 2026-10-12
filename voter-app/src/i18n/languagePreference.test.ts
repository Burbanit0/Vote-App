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
