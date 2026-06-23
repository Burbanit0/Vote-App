import { apiPost } from '../api/client';
import { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';
import { electoratePayload } from './assemblyApi';

// Frontier FB-2 — issue voting & the bundling paradoxes (Ostrogorski /
// discursive dilemma): issue-by-issue majorities vs the bundled platform vote.

export interface IssueOutcome {
  label: string;
  yes_share: number;
  majority: number; // +1 | -1
  winner_plank: number; // +1 | -1
  divergent: boolean;
}

export interface IssuePartyResult {
  name: string;
  platform: number[];
  votes: number;
  vote_share: number;
}

export interface IssueVotingResult {
  mode: string;
  parties: IssuePartyResult[];
  bundled_winner: string;
  issues: IssueOutcome[];
  divergent_count: number;
  num_issues: number;
  ostrogorski_paradox: boolean;
}

/** Spatial mode: K issues derived as hyperplanes through the shared electorate.
 * When `pg` carries a composed electorate, the hyperplanes cut that mixture. */
export async function runIssueVoting(
  config: ElectionConfig,
  numIssues: number,
  pg?: PlaygroundState
): Promise<IssueVotingResult> {
  return apiPost<IssueVotingResult>('/api/v2/election/issue-voting', {
    mode: 'spatial',
    parties: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    num_issues: numIssues,
    electorate: pg ? electoratePayload(pg) : null,
  });
}

/** The canonical constructed Ostrogorski profile — the pedagogical anchor. */
export async function runOstrogorskiDemo(): Promise<IssueVotingResult> {
  return apiPost<IssueVotingResult>('/api/v2/election/issue-voting', {
    mode: 'handcrafted',
    party_names: ['A', 'B'],
    party_platforms: [
      [1, 1, 1],
      [-1, -1, -1],
    ],
    voter_stances: [
      [1, 1, -1],
      [1, -1, 1],
      [-1, 1, 1],
      [-1, -1, -1],
      [-1, -1, -1],
    ],
  });
}
