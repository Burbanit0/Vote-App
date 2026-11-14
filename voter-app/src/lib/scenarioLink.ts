/**
 * A scenario as a link: the election config, the playground slice, the rule under examination,
 * the moment and the map lens, in the URL hash (`#s=<token>`), so that the person who opens it
 * sees what the sender saw.
 *
 * The hash, not the query string: it is never sent to a server, and it leaves `?story=` alone.
 * The token is base64url of a small JSON object. To keep a link short, a group of settings
 * (`candidates`, `blank_vote`, `space`, ...) that equals the default is left out, and the reader
 * falls back to the default for it.
 *
 * A link is typed by whoever wrote it, so reading it never trusts the shape: the two slices go
 * through the same checks as what comes back from localStorage (`persistedState`), and the rule,
 * moment and lens are checked against what exists. A token that is not ours, or from a newer
 * format, is not a scenario: `readScenarioLink` returns null and nothing is applied.
 */
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from './electionTypes';
import { LENSES, MOMENT_IDS, type Lens, type MomentId } from './journeyTypes';
import { sanitizeConfig, sanitizePlayground } from './persistedState';
import { RULE_LABELS, type Rule } from './playgroundVoting';

/** The format of the token. Bump it when a field changes meaning; a newer token is refused. */
export const LINK_VERSION = 1;

/** The hash parameter that carries the token. */
const PARAM = 's';

const RULES: ReadonlySet<string> = new Set(Object.keys(RULE_LABELS));

/** What a link carries. */
export interface ScenarioLink {
  config: ElectionConfig;
  playground: PlaygroundState;
  rule: Rule;
  moment: MomentId;
  lens: Lens;
}

type Json = Record<string, unknown>;

const isObject = (v: unknown): v is Json =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

const oneOf = <T extends string>(v: unknown, allowed: readonly T[], fallback: T): T =>
  allowed.find((a) => a === v) ?? fallback;

/** The settings of `value` that differ from `base`: whole groups, never a part of one. */
function changed(value: object, base: object): Json {
  const out: Json = {};
  const b = base as Json;
  for (const [key, v] of Object.entries(value)) {
    if (JSON.stringify(v) !== JSON.stringify(b[key])) out[key] = v;
  }
  return out;
}

function toBase64Url(text: string): string {
  let binary = '';
  for (const byte of new TextEncoder().encode(text)) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function fromBase64Url(token: string): string {
  const binary = atob(token.replace(/-/g, '+').replace(/_/g, '/'));
  return new TextDecoder('utf-8', { fatal: true }).decode(
    Uint8Array.from(binary, (c) => c.charCodeAt(0))
  );
}

/** The hash (`#s=...`) that carries `link`. */
export function scenarioHash(link: ScenarioLink): string {
  const payload = {
    v: LINK_VERSION,
    c: changed(link.config, DEFAULT_CONFIG),
    p: changed(link.playground, DEFAULT_PLAYGROUND),
    r: link.rule,
    m: link.moment,
    l: link.lens,
  };
  return `#${PARAM}=${toBase64Url(JSON.stringify(payload))}`;
}

/**
 * The scenario a hash carries, or null when it carries none: no token, not decodable, not JSON,
 * not an object, or a format this build does not know.
 */
export function readScenarioLink(hash: string): ScenarioLink | null {
  const token = new URLSearchParams(hash.replace(/^#/, '')).get(PARAM);
  if (!token) return null;
  let payload: unknown;
  try {
    payload = JSON.parse(fromBase64Url(token));
  } catch {
    return null;
  }
  if (!isObject(payload) || payload.v !== LINK_VERSION) return null;
  const { r: rule, m: moment, l: lens } = payload;
  return {
    config: sanitizeConfig(isObject(payload.c) ? payload.c : {}, DEFAULT_CONFIG),
    playground: sanitizePlayground(isObject(payload.p) ? payload.p : {}, DEFAULT_PLAYGROUND),
    rule: RULES.has(rule as string) ? (rule as Rule) : 'plurality',
    moment: oneOf(moment, MOMENT_IDS, 'electorate'),
    lens: oneOf(lens, LENSES, 'winner'),
  };
}

/** The full address of a link: this page, without its query or hash, then the hash. */
export function scenarioUrl(link: ScenarioLink, location: Pick<Location, 'origin' | 'pathname'>) {
  return `${location.origin}${location.pathname}${scenarioHash(link)}`;
}
