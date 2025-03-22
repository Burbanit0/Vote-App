import axios from 'axios';
import { Candidate, Voter, Vote, Result,  } from '../types';

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

// Update Candidate
export const updateCandidate = async (candidateId: number, candidateData: Partial<Candidate>) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/candidates/${candidateId}`, candidateData);
      return response.data;
    } catch (error) {
      console.error('Error updating candidate:', error);
      throw error;
    }
  };
  
  // Delete Candidate
  export const deleteCandidate = async (candidateId: number) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/candidates/${candidateId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting candidate:', error);
      throw error;
    }
  };

// Function to fetch all voters
export const fetchVoters = async (): Promise<Voter[]> => {
  try {
    const response = await axios.get<Voter[]>(`${API_BASE_URL}/voters`);
    return response.data;
  } catch (error) {
    console.error('Error fetching voters:', error);
    throw error;
  }
};

// Function to create a new voter
export const createVoter = async (voterData: Omit<Voter, 'id'>): Promise<Voter> => {
  try {
    const response = await axios.post<Voter>(`${API_BASE_URL}/voters`, voterData);
    return response.data;
  } catch (error) {
    console.error('Error creating voter:', error);
    throw error;
  }
};

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

  
  // Update Voter
  export const updateVoter = async (voterId: number, voterData: Partial<Voter>) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/voters/${voterId}`, voterData);
      return response.data;
    } catch (error) {
      console.error('Error updating voter:', error);
      throw error;
    }
  };
  
  // Delete Voter
  export const deleteVoter = async (voterId: number) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/voters/${voterId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting voter:', error);
      throw error;
    }
  };
  
  // Update Vote
  export const updateVote = async (voteId: number, voteData: Partial<Vote>) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/votes/${voteId}`, voteData);
      return response.data;
    } catch (error) {
      console.error('Error updating vote:', error);
      throw error;
    }
  };
  
  // Delete Vote
  export const deleteVote = async (voteId: number) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/votes/${voteId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting vote:', error);
      throw error;
    }
  };


// Function to register a new user
export const registerUser = async (username: string, password: string, role: 'Voter' | 'Admin', first_name:string, last_name:string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
      username,
      password,
      role,
      first_name,
      last_name
    });
    return response.data;
  } catch (error) {
    console.error('Error registering user:', error);
    throw error;
  }
};

// Function to log in a user
export const loginUser = async (username: string, password: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
      username,
      password,
    });
    // Extract the token and role from the response
    const user = response.data;
    return user;
  } catch (error) {
    console.error('Error logging in user:', error);
    throw error;
  }
};


export const fetchProfileData = async () => {
  try {
    // Retrieve the JWT token from local storage
    const token = localStorage.getItem('token');

    if (!token) {
      throw new Error('No token found');
    }

    // Make a GET request to the /api/auth/profile endpoint with the JWT token
    const response = await axios.get(`${API_BASE_URL}/api/auth/profile`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch profile data. Please check your login status.');
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