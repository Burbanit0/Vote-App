// src/types.ts

export interface Party {
  id: number;
  name: string;
  description: string;
}

export interface PartyMembersProps {
  partyId: number;
}

export interface Result {
  candidate_id: number;
  vote_type: string;
  vote_count: number;
}

export interface Vote {
  candidate_id: number;
  // vote_type: string;
  // rank: number;
  // weight: number;
  // rating: number;
}

export interface Voter {
  id: number;
  user_id?: number;
  first_name: string;
  last_name: string;
}

export interface User {
  id: number;
  access_token: string;
  username: string;
  role: string;
  created_at: string;
  user_id: number;
  first_name: string;
  last_name: string;
}

export interface Election {
  id: number;
  name: string;
  description: string;
  voters: number[];
  candidates: number[];
  created_at: string;
  created_by: Voter;
  start_date: string;
  end_date: string;
  status: string;
}

export interface Election_ {
  id: number;
  name: string;
  description: string;
  voters: User[];
  candidates: Candidate[];
  created_at: string;
  created_by: Voter;
  start_date: string;
  end_date: string;
}

export interface Participant {
  id: number;
  user_id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
}

export interface Profile_ {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
  is_admin: boolean;
  elections_participated: number;
  elections_voted_in: number;
  participation_details: ParticipationDetails;
  voted_in_elections: number;
}

export interface ParticipationDetails {
  candidate: number[];
  organizer: number[];
  voter: number[];
}

export interface PaginatedResponse {
  elections: Election[];
  total: number;
  pages: number;
  current_page: number;
  per_page: number;
}

export interface ParticipationStatus {
  is_participant: boolean;
  role: string | null;
  isLoading: boolean;
  error: string | null;
}

export interface UserPermissions {
  is_admin: boolean;
  participation_points: number;
  canCreateElections: boolean;
  is_loading: boolean;
  error: string | null;
}

export interface ParticipationData {
  points: number;
  nextLevel: number;
  level: string;
}

export interface UpdateElectionData {
  name?: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  voting_method?: string;
}

export type Candidate = string;

export interface ScoreVote {
  voter_id: number;
  scores: Record<Candidate, number>;
}

export interface ScoreVotingResult {
  method: string;
  winner?: Candidate;
  details: any;
}

export interface ScoreVotingResults {
  simple_score: ScoreVotingResult;
  star_voting: ScoreVotingResult;
  median_voting: ScoreVotingResult;
  mean_median_hybrid: ScoreVotingResult;
  variance_based: ScoreVotingResult;
  score_distribution: ScoreVotingResult;
  bayesian_regret: ScoreVotingResult;
}

export interface ScoreVotingComparisonProps {
  scores: ScoreVote[];
  candidates: Candidate[];
  results: ScoreVotingResults;
}

export interface CandidateSimu {
  id: number;
  name: string;
  party: string;
  party_lean: number;
  policies: Record<string, number>;
  charisma: number;
  scandals: number;
  campaign_funds: number;
  experience: number;
  popularity: number;
}

export type Gender = 'male' | 'female';
export type Region = 'urban' | 'suburban' | 'rural';
export type Income = 'low' | 'middle' | 'high';
export type PartySimu = 'Green' | 'Conservative' | 'Liberal' | 'Independent';
export type Education = 'none' | 'high_school' | 'bachelor' | 'master' | 'phd';
export type Employement = 'employed' | 'unemployed' | 'self_employed' | 'retired';
export type Family = 'single' | 'with_children' | 'retired';
export type Ethnicity = 'native' | 'immigrant';
export type Religion = 'religious' | 'non_religious';

export interface VoterSimu {
  id: number;
  age: number;
  region: Region;
  income: Income;
  gender: Gender;
  education: Education;
  employment_status: Employement;
  religion: Religion;
  family_status: Family;
  ethnicity_immigration: Ethnicity;
  political_lean: number;
  issue_priorities: Record<string, number>;
  party_loyalty: number;
  preferred_party: PartySimu;
  likelihood_to_vote: number;
  mood: number;
}
