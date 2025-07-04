// src/types.ts
export interface Candidate {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    results?: Result[];
}

export interface Party {
  id: number;
  name: string;
  description: string;
}

export interface PartyMembersProps {
    partyId: number
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
    id : number;
    name : string;
    description : string;
    voters: number[];
    candidates: number[];
    created_at: string;
    created_by: Voter;
    start_date: number;
    status: 'active' | 'completed' | 'upcoming';
}

export interface Election_ {
    id : number;
    name : string;
    description : string;
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