// electoralAtlas.ts — a small, sourced atlas of how democracies actually elect,
// for the rotating 3D globe (RegimeGlobe). Each country carries its headline
// national method and, where documented, its blank-vote regime (reusing the
// taxonomy from data/blankVoteRegimes.ts). Coordinates drive the globe; the
// method is the primary colour lens, the blank regime the secondary one.
//
// Scope note: method assignments are the well-documented headline system for the
// main national election (lower house or president). blankStatus is only set
// where it is confidently known (the countries also in blankVoteRegimes); others
// are left undefined and shown muted under the blank lens — better a gap than a
// fabricated fact.

import type { BlankVoteStatus } from '../data/blankVoteRegimes';

export type AtlasMethod =
  | 'fptp' // first-past-the-post, single-member plurality
  | 'two_round' // two-round runoff (président / législatives FR)
  | 'irv' // instant-runoff / alternative vote
  | 'stv' // single transferable vote (proportional, ranked)
  | 'mmp' // mixed-member proportional
  | 'party_list_pr' // party-list proportional representation
  | 'mixed'; // parallel / mixed non-compensatory

export interface AtlasEntry {
  country: string; // French name (matches blankVoteRegimes)
  flag: string;
  lat: number;
  lon: number;
  method: AtlasMethod;
  blankStatus?: BlankVoteStatus;
  source: string;
}

const ATLAS: AtlasEntry[] = [
  // ── Two-round & the blank-vote stars ──────────────────────────────────────
  {
    country: 'France',
    flag: '🇫🇷',
    lat: 46,
    lon: 2,
    method: 'two_round',
    blankStatus: 'counted_separate',
    source: 'Code électoral ; loi du 21/02/2014',
  },
  {
    country: 'Uruguay',
    flag: '🇺🇾',
    lat: -33,
    lon: -56,
    method: 'two_round',
    blankStatus: 'competitive',
    source: 'Constitución de Uruguay, art. 77',
  },
  {
    country: 'Colombie',
    flag: '🇨🇴',
    lat: 4,
    lon: -72,
    method: 'two_round',
    blankStatus: 'threshold',
    source: 'Ley 134 de 1994, art. 26',
  },
  {
    country: 'Brésil',
    flag: '🇧🇷',
    lat: -10,
    lon: -55,
    method: 'two_round',
    blankStatus: 'symbolic',
    source: 'Código Eleitoral Brasileiro',
  },
  {
    country: 'Chili',
    flag: '🇨🇱',
    lat: -30,
    lon: -71,
    method: 'two_round',
    blankStatus: 'symbolic',
    source: 'Ley Orgánica sobre Votaciones — SERVEL',
  },
  {
    country: 'Indonésie',
    flag: '🇮🇩',
    lat: -2,
    lon: 118,
    method: 'two_round',
    source: 'General Elections Commission (KPU)',
  },
  // ── First-past-the-post ───────────────────────────────────────────────────
  {
    country: 'Royaume-Uni',
    flag: '🇬🇧',
    lat: 54,
    lon: -2,
    method: 'fptp',
    source: 'Representation of the People Act',
  },
  {
    country: 'États-Unis',
    flag: '🇺🇸',
    lat: 39,
    lon: -98,
    method: 'fptp',
    source: 'U.S. Constitution ; state law',
  },
  {
    country: 'Inde',
    flag: '🇮🇳',
    lat: 22,
    lon: 79,
    method: 'fptp',
    source: 'Representation of the People Act 1951',
  },
  {
    country: 'Canada',
    flag: '🇨🇦',
    lat: 56,
    lon: -106,
    method: 'fptp',
    source: 'Canada Elections Act',
  },
  // ── Instant-runoff / ranked ───────────────────────────────────────────────
  {
    country: 'Australie',
    flag: '🇦🇺',
    lat: -25,
    lon: 133,
    method: 'irv',
    blankStatus: 'merged_invalid',
    source: 'Commonwealth Electoral Act 1918 (House)',
  },
  {
    country: 'Irlande',
    flag: '🇮🇪',
    lat: 53,
    lon: -8,
    method: 'stv',
    source: 'Electoral Act ; Bunreacht na hÉireann',
  },
  {
    country: 'Malte',
    flag: '🇲🇹',
    lat: 35.9,
    lon: 14.4,
    method: 'stv',
    source: 'Constitution of Malta',
  },
  // ── Mixed-member proportional ─────────────────────────────────────────────
  {
    country: 'Allemagne',
    flag: '🇩🇪',
    lat: 51,
    lon: 10,
    method: 'mmp',
    blankStatus: 'merged_invalid',
    source: 'Bundeswahlgesetz',
  },
  {
    country: 'Nouvelle-Zélande',
    flag: '🇳🇿',
    lat: -41,
    lon: 174,
    method: 'mmp',
    source: 'Electoral Act 1993',
  },
  // ── Party-list proportional ───────────────────────────────────────────────
  {
    country: 'Pays-Bas',
    flag: '🇳🇱',
    lat: 52.4,
    lon: 5.3,
    method: 'party_list_pr',
    blankStatus: 'symbolic',
    source: 'Kieswet — Kiesraad',
  },
  {
    country: 'Belgique',
    flag: '🇧🇪',
    lat: 50.5,
    lon: 4.5,
    method: 'party_list_pr',
    blankStatus: 'symbolic',
    source: 'Code électoral belge',
  },
  {
    country: 'Espagne',
    flag: '🇪🇸',
    lat: 40,
    lon: -4,
    method: 'party_list_pr',
    blankStatus: 'counted_separate',
    source: 'LOREG — Junta Electoral Central',
  },
  {
    country: 'Portugal',
    flag: '🇵🇹',
    lat: 39.5,
    lon: -8,
    method: 'party_list_pr',
    blankStatus: 'symbolic',
    source: 'Código Eleitoral Português',
  },
  {
    country: 'Suède',
    flag: '🇸🇪',
    lat: 60,
    lon: 15,
    method: 'party_list_pr',
    blankStatus: 'symbolic',
    source: 'Vallagen (2005:837)',
  },
  {
    country: 'Suisse',
    flag: '🇨🇭',
    lat: 47,
    lon: 8,
    method: 'party_list_pr',
    blankStatus: 'symbolic',
    source: 'Loi fédérale sur les droits politiques',
  },
  {
    country: 'Afrique du Sud',
    flag: '🇿🇦',
    lat: -29,
    lon: 24,
    method: 'party_list_pr',
    source: 'Electoral Act 73 of 1998',
  },
  // ── Mixed / parallel ──────────────────────────────────────────────────────
  {
    country: 'Italie',
    flag: '🇮🇹',
    lat: 42,
    lon: 12,
    method: 'mixed',
    blankStatus: 'counted_separate',
    source: 'Rosatellum (l. 165/2017)',
  },
  {
    country: 'Japon',
    flag: '🇯🇵',
    lat: 36,
    lon: 138,
    method: 'mixed',
    source: 'Public Offices Election Act',
  },
  {
    country: 'Mexique',
    flag: '🇲🇽',
    lat: 23,
    lon: -102,
    method: 'mixed',
    source: 'LGIPE — INE',
  },
  {
    country: 'Corée du Sud',
    flag: '🇰🇷',
    lat: 36.5,
    lon: 127.8,
    method: 'mixed',
    source: 'Public Official Election Act',
  },
];

export default ATLAS;

export const ATLAS_METHODS: AtlasMethod[] = [
  'fptp',
  'two_round',
  'irv',
  'stv',
  'mmp',
  'party_list_pr',
  'mixed',
];

/** Categorical colour per method (the primary globe lens). */
export const METHOD_COLOR: Record<AtlasMethod, string> = {
  fptp: '#4e79a7',
  two_round: '#59a14f',
  irv: '#f28e2b',
  stv: '#e15759',
  mmp: '#b07aa1',
  party_list_pr: '#76b7b2',
  mixed: '#edc948',
};

/** Colour per blank-vote status (the secondary lens); undefined → muted. */
export const BLANK_COLOR: Record<BlankVoteStatus, string> = {
  competitive: '#e15759',
  threshold: '#f28e2b',
  counted_separate: '#59a14f',
  symbolic: '#76b7b2',
  merged_invalid: '#9aa0a6',
};
export const BLANK_UNKNOWN_COLOR = '#c9ccd1';
