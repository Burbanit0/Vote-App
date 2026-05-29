import axios from 'axios';
import { SimulationFormData } from '../components/Simulation/SimulationForm';
import { VoterSimu, CandidateSimu } from '../types';
import { apiPath } from '../api/apiVersion';

const API_BASE_URL = (process.env.VITE_API_URL) || 'http://localhost:4433';

function getAuthHeader(): Record<string, string> {
  const userString = localStorage.getItem('user');
  if (!userString) return {};
  try {
    const token = JSON.parse(userString).access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

export const simulateVote = async (formData: SimulationFormData): Promise<any> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}${apiPath('simulations')}`,
      { formData },
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to simulate votes. Please try again.', error);
    throw error;
  }
};

export const simulateVoters = async (numVoters: number): Promise<{ voters: VoterSimu[] }> => {
  try {
    const response = await axios.post<{ voters: VoterSimu[] }>(
      `${API_BASE_URL}${apiPath('simulations/simulate_voters')}`,
      { num_voters: numVoters },
      { headers: getAuthHeader() }
    );
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
): Promise<{ candidates: CandidateSimu[] }> => {
  try {
    const response = await axios.post<{ candidates: CandidateSimu[] }>(
      `${API_BASE_URL}${apiPath('simulations/simulate_candidates')}`,
      { num_candidates: numCandidates, issues, parties },
      { headers: getAuthHeader() }
    );
    return response.data;
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
    const response = await axios.post(
      `${API_BASE_URL}${apiPath('simulations/simulate_utility')}`,
      { voters, candidates, issues },
      { headers: getAuthHeader() }
    );
    return response.data;
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
    const response = await axios.post(
      `${API_BASE_URL}${apiPath('simulations/get_utility_matrix')}`,
      { voters, candidates, issues },
      { headers: getAuthHeader() }
    );
    return response.data;
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
    const response = await axios.post(
      `${API_BASE_URL}${apiPath('simulations/get_voter_segments')}`,
      { voters, candidates, issues, segments: ['young_female', 'old_male', 'high_edu', 'urban'] },
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Error getting voter segments:', error);
    throw error;
  }
};

export const closestCandidate = async (
  voters: number[],
  candidates: number[]
): Promise<any> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}${apiPath('simulations/get_closest_candidate')}`,
      { candidates, voters },
      { headers: getAuthHeader() }
    );
    return response.data.result;
  } catch (error) {
    console.error('Failed to get the closest candidates', error);
    throw error;
  }
};
