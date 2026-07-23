// analytics.ts — anonymous, cookie-less usage measurement (Umami, self-hosted).
//
// Why frontend events at all: the entire voting engine runs CLIENT-SIDE (rule
// changes, stories, lab fiches, the campaign scrubber never hit the backend),
// so server logs are blind to real usage. These events are the only way to
// learn which methods, stories and fiches people actually explore.
//
// Privacy posture (deliberate, matches the app's anonymous+stateless stance):
//  · Umami is cookie-less and stores no identifier — no consent banner needed
//    (CNIL audience-measurement exemption), no PII anywhere in our props.
//  · Respects Do-Not-Track.
//  · Enabled ONLY when both VITE_UMAMI_* vars are set at build time AND the
//    build is production — dev, tests and forks of this public repo send nothing.
//
// The provider is one <script> injection behind `initAnalytics()`; `track()` is
// a safe no-op until (and unless) the script is live, so call sites never guard.

declare global {
  interface Window {
    umami?: { track: (event: string, data?: Record<string, unknown>) => void };
  }
}

interface AnalyticsEnv {
  PROD: boolean;
  VITE_UMAMI_SRC?: string;
  VITE_UMAMI_WEBSITE_ID?: string;
}

/**
 * Inject the Umami tracker once, when configured. Umami auto-tracks pageviews
 * including SPA route changes (it hooks pushState), so no router wiring needed.
 * The `env` seam exists for tests; production callers pass nothing.
 */
export function initAnalytics(
  env: AnalyticsEnv = import.meta.env as unknown as AnalyticsEnv
): void {
  if (typeof document === 'undefined') return;
  if (!env.PROD || !env.VITE_UMAMI_SRC || !env.VITE_UMAMI_WEBSITE_ID) return;
  if (navigator.doNotTrack === '1') return;
  if (document.querySelector('script[data-website-id]')) return; // already injected

  const s = document.createElement('script');
  s.defer = true;
  s.src = env.VITE_UMAMI_SRC;
  s.setAttribute('data-website-id', env.VITE_UMAMI_WEBSITE_ID);
  document.head.appendChild(s);
}

/**
 * Record one product event. Event names are a small fixed vocabulary
 * (story_started, rule_changed, lab_fiche_opened, …); props carry only ids and
 * enum-like values — never free text, never anything user-identifying.
 * ponytail: events fired before the deferred script finishes loading are
 * dropped, not queued — the first paint-to-load gap loses at most a click.
 */
export function track(event: string, data?: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  window.umami?.track(event, data);
}
