import { encodeShareConfig, decodeShareConfig, buildShareURL, copyShareURL, readShareParam } from '../shareUtils';

const mockConfig = { numVoters: 100, ideology: 'centrist' };

describe('encodeShareConfig / decodeShareConfig', () => {
  it('round-trips a config object', () => {
    const encoded = encodeShareConfig(mockConfig);
    const decoded = decodeShareConfig<typeof mockConfig>(encoded);
    expect(decoded).toEqual(mockConfig);
  });

  it('returns empty string on encode failure', () => {
    const circular: any = { self: null };
    circular.self = circular;
    expect(encodeShareConfig(circular)).toBe('');
  });

  it('returns null on decode failure', () => {
    expect(decodeShareConfig('invalid!')).toBeNull();
  });
});

describe('buildShareURL', () => {
  const origHref = window.location.href;

  afterEach(() => {
    window.history.replaceState({}, '', origHref);
  });

  it('appends ?cfg= with encoded config', () => {
    window.history.replaceState({}, '', '/app');
    const url = buildShareURL(mockConfig);
    expect(url).toContain('/app?cfg=');
    expect(url).toContain(encodeShareConfig(mockConfig));
  });
});

describe('copyShareURL', () => {
  const origHref = window.location.href;

  beforeEach(() => {
    window.history.replaceState({}, '', '/app');
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  afterEach(() => {
    window.history.replaceState({}, '', origHref);
  });

  it('copies the share URL to clipboard', async () => {
    await copyShareURL(mockConfig);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining(`/app?cfg=${encodeShareConfig(mockConfig)}`)
    );
  });
});

describe('readShareParam', () => {
  const origHref = window.location.href;

  afterEach(() => {
    window.history.replaceState({}, '', origHref);
  });

  it('returns cfg param value when present', () => {
    const encoded = encodeShareConfig(mockConfig);
    window.history.replaceState({}, '', `http://localhost/app?cfg=${encoded}`);
    expect(readShareParam()).toBe(encoded);
  });

  it('returns null when no cfg param', () => {
    window.history.replaceState({}, '', 'http://localhost/app');
    expect(readShareParam()).toBeNull();
  });
});
