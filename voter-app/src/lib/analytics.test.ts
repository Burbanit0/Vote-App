import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { initAnalytics, track } from './analytics';

const ENV = {
  PROD: true,
  VITE_UMAMI_SRC: 'https://a.example/script.js',
  VITE_UMAMI_WEBSITE_ID: 'site-1',
};
const injected = () => document.head.querySelector('script[data-website-id]');

beforeEach(() => {
  injected()?.remove();
  delete (window as { umami?: unknown }).umami;
});
afterEach(() => vi.unstubAllGlobals());

describe('initAnalytics — only fires when explicitly configured for production', () => {
  it('injects the tracker with the configured source and site id', () => {
    initAnalytics(ENV);
    const s = injected() as HTMLScriptElement;
    expect(s).toBeTruthy();
    expect(s.src).toBe(ENV.VITE_UMAMI_SRC);
    expect(s.getAttribute('data-website-id')).toBe('site-1');
    expect(s.defer).toBe(true);
  });

  it('is a no-op in non-production builds', () => {
    initAnalytics({ ...ENV, PROD: false });
    expect(injected()).toBeNull();
  });

  it('is a no-op when either env var is missing (dev, tests, repo forks)', () => {
    initAnalytics({ PROD: true, VITE_UMAMI_SRC: ENV.VITE_UMAMI_SRC });
    initAnalytics({ PROD: true, VITE_UMAMI_WEBSITE_ID: 'site-1' });
    expect(injected()).toBeNull();
  });

  it('respects Do-Not-Track', () => {
    vi.stubGlobal('navigator', { ...navigator, doNotTrack: '1' });
    initAnalytics(ENV);
    expect(injected()).toBeNull();
  });

  it('never injects twice', () => {
    initAnalytics(ENV);
    initAnalytics(ENV);
    expect(document.head.querySelectorAll('script[data-website-id]')).toHaveLength(1);
  });
});

describe('track — a safe no-op until the tracker is live', () => {
  it('does not throw when the tracker is absent (dev, tests, script blocked)', () => {
    expect(() => track('story_started', { story: 'spoiler' })).not.toThrow();
  });

  it('forwards event name and props once the tracker exists', () => {
    const spy = vi.fn();
    (window as { umami?: unknown }).umami = { track: spy };
    track('rule_changed', { rule: 'irv' });
    expect(spy).toHaveBeenCalledWith('rule_changed', { rule: 'irv' });
  });
});
