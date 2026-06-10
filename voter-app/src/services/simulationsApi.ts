import { SimulationFormData } from '../components/Simulation/SimulationForm';
import { VoterSimu, CandidateSimu } from '../types';
import { apiPost } from '../api/client';

export const simulateVote = async (formData: SimulationFormData): Promise<any> => {
  try {
    return await apiPost('/api/v2/simulations', { formData });
  } catch (error) {
    console.error('Failed to simulate votes. Please try again.', error);
    throw error;
  }
};

export const simulateVoters = async (numVoters: number): Promise<{ voters: VoterSimu[] }> => {
  try {
    return await apiPost<{ voters: VoterSimu[] }>('/api/v2/simulations/simulate_voters', {
      num_voters: numVoters,
    });
  } catch (error) {
    console.error('Failed to create voters', error);
    throw error;
  }
};

export const simulateCandidates = async (
  numCandidates: number,
  issues: string[],
  parties: string[]
): Promise<{ candidates: CandidateSimu[] }> => {
  try {
    return await apiPost<{ candidates: CandidateSimu[] }>(
      '/api/v2/simulations/simulate_candidates',
      { num_candidates: numCandidates, issues, parties }
    );
  } catch (error) {
    console.error('Failed to create candidates', error);
    throw error;
  }
};

export const simulateUtility = async (
  issues: string[],
  voters: VoterSimu[],
  candidates: CandidateSimu[]
): Promise<any> => {
  try {
    return await apiPost('/api/v2/simulations/simulate_utility', { voters, candidates, issues });
  } catch (error) {
    console.error('Error simulating utility:', error);
    throw error;
  }
};

export const getUtilityMatrix = async (
  voters: VoterSimu[],
  candidates: CandidateSimu[],
  issues: string[]
): Promise<any> => {
  try {
    return await apiPost('/api/v2/simulations/get_utility_matrix', { voters, candidates, issues });
  } catch (error) {
    console.error('Error getting utility matrix:', error);
    throw error;
  }
};

export const getVoterSegments = async (
  voters: VoterSimu[],
  candidates: CandidateSimu[],
  issues: string[]
): Promise<any> => {
  try {
    return await apiPost('/api/v2/simulations/get_voter_segments', {
      voters,
      candidates,
      issues,
      segments: ['young_female', 'old_male', 'high_edu', 'urban'],
    });
  } catch (error) {
    console.error('Error getting voter segments:', error);
    throw error;
  }
};

export const closestCandidate = async (voters: number[], candidates: number[]): Promise<any> => {
  try {
    const data = await apiPost<{ result: any }>('/api/v2/simulations/get_closest_candidate', {
      candidates,
      voters,
    });
    return data.result;
  } catch (error) {
    console.error('Failed to get the closest candidates', error);
    throw error;
  }
};
