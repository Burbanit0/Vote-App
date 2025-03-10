// src/types.ts
export interface Candidate {
    id: number;
    first_name: string;
    last_name: string;
    results?: Result[];
}
  
export interface Result {
    candidate_id: number;
    vote_type: string;
    vote_count: number;
}

export interface Vote {
    vote_id: number;
    voter_id: number;
    candidate_id: number;
    vote_type: string;
    rank: number;
    weight: number;
    rating: number;
}

export interface Voter {
    id: number;
    first_name: string;
    last_name: string;
}

export interface User {
    id: number;
    access_token: string;
    username: string;
    role: string;
    created_at: string;
    voter?: Voter;
}
  