/**
 * The types of the election config and the playground state. They live here, apart from the
 * store, so the modules that check or edit them (persistedState, candidateEditing) can import
 * them without importing the store, which imports them back.
 */
import type { BlankLens } from './blankVote';
import type { Community } from './playgroundElectorate';

/** A composable electorate: a mixture of communities + axis correlation. */
export interface ElectorateComposition {
  mode: 'simple' | 'composed';
  correlation: number;
  /** Global measurement/polling jitter in [0,1] (blurs observed positions). */
  noise: number;
  communities: Community[];
}

export interface ElectionCandidate {
  name: string;
  x: number;
  y: number;
  /** Optional 3rd ideological axis (playground dims=3). Defaults to 0. */
  z?: number;
  /** Stokes valence: non-spatial quality in [-1,1], applied only when
   *  space.valenceEnabled. Lifts utility for every voter (−distance + valence). */
  valence?: number;
}

export interface ElectionConfig {
  candidates: ElectionCandidate[];
  num_voters: number;
  ideology: string;
  seed: number;
  blank_vote: {
    enabled: boolean;
    rule: 'symbolic' | 'competitive' | 'threshold_30';
    contagion: {
      enabled: boolean;
      beta: number;
      gamma: number;
      network: 'random' | 'watts_strogatz' | 'block';
    };
  };
  information_model: {
    enabled: boolean;
    media_bias: Record<string, number>;
    voter_segments: { low_info: number; medium_info: number; high_info: number };
  };
  campaign: {
    enabled: boolean;
    num_days: number;
    polling_effect: number;
  };
  description?: string;
  phenomenon?: string;
}

export type PlaygroundMode = 'leader' | 'parliament';
export type PrefSource =
  | 'spatial'
  | 'single_peaked'
  | 'impartial'
  | 'iac'
  | 'mallows'
  | 'urn'
  | 'plackett_luce'
  | 'didi'
  | 'stratification'
  | 'handcrafted';

export type Behavior = 'sincere' | 'strategic' | 'mixed';
export type AssemblyStructure = 'pr' | 'fptp' | 'mmp';
export type Apportionment = 'dhondt' | 'sainte_lague';
export type BallotType =
  | 'full'
  | 'choose_one'
  | 'approve'
  | 'rank_full'
  | 'rank_truncated'
  | 'score'
  | 'grade'
  | 'cumulative';

export interface PlaygroundState {
  mode: PlaygroundMode;
  space: { dims: 1 | 2 | 3; axisLabels: string[]; valenceEnabled: boolean };
  behavior: Behavior;
  /** Which insincere ballot a tempted conviction bloc casts (leader map). */
  stratTactic: 'compromise' | 'burying';
  /** Size of the coordinating conviction bloc, as a share of the electorate. */
  stratShare: number;
  prefSource: PrefSource;
  prefParams: Record<string, number>;
  /** FA-1: how voters may EXPRESS preferences — separate from the counting rule. */
  ballot: { type: BallotType; truncate_at: number; score_levels: number };
  /** Electorate realism: differential turnout (Downsian abstention). */
  turnout: { model: 'full' | 'alienation' | 'indifference'; intensity: number };
  /** Live blank-vote lever (leader mode): voters too far from every candidate
   *  spoil their ballot instead of voting; `lens` picks the constitutional
   *  regime (lib/blankVote.ts) that decides what that does to the result. */
  blank: { enabled: boolean; intensity: number; lens: BlankLens };
  /** Composable electorate (community mixture); 'simple' = the ideology Gaussian. */
  electorate: ElectorateComposition;
  assembly: {
    structure: AssemblyStructure;
    seats: number;
    threshold: number;
    apportionment: Apportionment;
    num_districts: number;
    /** Duverger demo (P4): voters desert non-viable parties. */
    strategic_desertion: boolean;
  };
}
