import axios from 'axios';
import { Candidate } from '../types';

const API_BASE_URL = 'http://localhost:4433';

// Function to fetch all candidates
export const fetchCandidates = async (): Promise<Candidate[]> => {
  try {
    const response = await axios.get<Candidate[]>(`${API_BASE_URL}/candidates`);
    return response.data;
  } catch (error) {
    console.error('Error fetching candidates:', error);
    throw error;
  }
};

// Function to fetch a specific candidate by ID
export const fetchCandidateById = async (candidateId: number): Promise<Candidate> => {
  try {
    const response = await axios.get<Candidate>(`${API_BASE_URL}/candidates/${candidateId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching candidate with ID ${candidateId}:`, error);
    throw error;
  }
};

// Function to create a new candidate
export const createCandidate = async (candidateData: Omit<Candidate, 'id'>): Promise<Candidate> => {
  try {
    const response = await axios.post<Candidate>(`${API_BASE_URL}/candidates`, candidateData, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error creating candidate:', error);
    throw error;
  }
};

// Function to update a candidate
export const updateCandidate = async (candidateId: number, candidateData: Partial<Candidate>) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/candidates/${candidateId}`, candidateData);
    return response.data;
  } catch (error) {
    console.error('Error updating candidate:', error);
    throw error;
  }
};

// Function to delete a candidate
export const deleteCandidate = async (candidateId: number) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/candidates/${candidateId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting candidate:', error);
    throw error;
  }
};
