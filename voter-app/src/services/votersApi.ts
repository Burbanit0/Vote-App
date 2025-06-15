import axios from 'axios';
import { Voter } from '../types';

const API_BASE_URL = 'http://localhost:4433';

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

// Function to fetch a voter by id
export const fetchVoterById = async (voterId: number): Promise<Voter> => {
  try {
    const response = await axios.get<Voter>(`${API_BASE_URL}/voters/${voterId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching voter with ID ${voterId}:`, error);
    throw error;
  }
}

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

// Function to update a voter
export const updateVoter = async (voterId: number, voterData: Partial<Voter>) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/voters/${voterId}`, voterData);
    return response.data;
  } catch (error) {
    console.error('Error updating voter:', error);
    throw error;
  }
};

// Function to delete a voter
export const deleteVoter = async (voterId: number) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/voters/${voterId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting voter:', error);
    throw error;
  }
};
