import axios from 'axios';
import { Vote } from '../types';

const API_BASE_URL = 'http://localhost:4433';

// Function to cast a vote
export const castVote = async (voteData: Omit<Vote, 'id'>): Promise<Vote> => {
  try {
    const response = await axios.post<Vote>(`${API_BASE_URL}/votes`, voteData);
    return response.data;
  } catch (error) {
    console.error('Error casting vote:', error);
    throw error;
  }
};

// Function to update a vote
export const updateVote = async (voteId: number, voteData: Partial<Vote>) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/votes/${voteId}`, voteData);
    return response.data;
  } catch (error) {
    console.error('Error updating vote:', error);
    throw error;
  }
};

// Function to delete a vote
export const deleteVote = async (voteId: number) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/votes/${voteId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting vote:', error);
    throw error;
  }
};
