import axios from 'axios';
import { SimulationFormData } from '../components/Simulation/SimulationForm';
import { VoterSimu, CandidateSimu } from '../types';

const API_BASE_URL = 'http://localhost:4433';

export const simulateVote = async (formData: SimulationFormData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations`, {
      formData: formData,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to simulate votes. Please try again.', error);
    throw error;
  }
};

export const simulateVoters = async (numVoters: number) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/simulate_voters`, {
      num_voters: numVoters,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to create voters', error);
    throw error;
  }
};

export const simulateCandidates = async (
  numCandidates: number,
  issues: string[],
  parties: string[]
) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/simulate_candidates`, {
      num_candidates: numCandidates,
      issues: issues,
      parties: parties,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to create candidates', error);
    throw error;
  }
};

// Pour simuler une analyse complète
export const simulateUtility = async (
  issues: string[],
  voters: VoterSimu[],
  candidates: CandidateSimu[]
) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/simulate_utility`, {
      voters: voters,
      candidates: candidates,
      issues: issues,
    });
    return response.data;
  } catch (error) {
    console.error('Error simulating utility:', error);
  }
};

// Pour obtenir une matrice d'utilité
export const getUtilityMatrix = async (
  voters: VoterSimu[],
  candidates: CandidateSimu[],
  issues: string[]
) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/get_utility_matrix`, {
      voters: voters,
      candidates: candidates,
      issues: issues,
    });
    return response.data;
  } catch (error) {
    console.error('Error getting utility matrix:', error);
  }
};

// Pour analyser par segments
export const getVoterSegments = async (
  voters: VoterSimu[],
  candidates: CandidateSimu[],
  issues: string[]
) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/get_voter_segments`, {
      voters: voters,
      candidates: candidates,
      issues: issues,
      segments: ['young_female', 'old_male', 'high_edu', 'urban'],
    });
    return response.data;
  } catch (error) {
    console.error('Error getting voter segments:', error);
  }
};

export const closestCandidate = async (voters: number[], candidates: number[]) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/get_closest_candidate`, {
      candidates: candidates,
      voters: voters,
    });
    return response.data.result;
  } catch (error) {
    console.error('Failed to get the closest candidates', error);
    throw error;
  }
};
