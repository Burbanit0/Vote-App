import axios from 'axios';
import { Vote } from '../types';

const API_BASE_URL = 'http://localhost:4433';

// Function to cast a vote
export const castVote = async (candidate_id: number, electionId: number): Promise<Vote> => {
  try {
    const storedUserJSON = localStorage.getItem('user');
    let token = '';
    let storedUser: { access_token: string; user_id: number } | null = null;

    if (storedUserJSON !== null) {
      storedUser = JSON.parse(storedUserJSON);
    }

    if (storedUser !== null) {
      token = storedUser.access_token;
    } else {
      console.error('User data not found in localStorage.');
    }
    const response = await axios.post<Vote>(
      `${API_BASE_URL}/votes/elections/${electionId}`,
      { candidate_id: candidate_id },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
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
