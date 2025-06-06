import axios from 'axios';
import { Result, Candidate } from '../types';

const API_BASE_URL = 'http://localhost:4433';

// Function to fetch voting results for a specific candidate
export const fetchCandidateResults = async (candidateId: number): Promise<Result[]> => {
  try {
    const response = await axios.get<Result[]>(`${API_BASE_URL}/candidates/${candidateId}/results`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching results for candidate with ID ${candidateId}:`, error);
    throw error;
  }
};

// Function to fetch all voting results
export const fetchAllResults = async (): Promise<Result[]> => {
  try {
    const response = await axios.get<Result[]>(`${API_BASE_URL}/results`);
    return response.data;
  } catch (error) {
    console.error('Error fetching all results:', error);
    throw error;
  }
};

export const fetchCondorcetWinner = async (): Promise<Candidate> => {
  try {
    const response = await axios.get<Candidate>(`${API_BASE_URL}/results/condorcet`);
    return response.data;
  } catch (error) {
    console.error('Error fetching all results:', error);
    throw error;
  }
};

export const fetchTwoRoundWinner = async (): Promise<Candidate> => {
  try {
    const response = await axios.get<Candidate>(`${API_BASE_URL}/results/two-round`);
    return response.data;
  } catch (error) {
    console.error('Error fetching all results:', error);
    throw error;
  }
};
