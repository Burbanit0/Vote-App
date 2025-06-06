import axios from 'axios';
import { Election, Election_ } from '../types';

const API_BASE_URL = 'http://localhost:4433';

export const createElection = async (name: string, description: string, voters: number[], candidates: number[]) => {
  try {
    const storedUserJSON = localStorage.getItem('user');
    let token = "";
    let storedUser: { access_token: string; role: string } | null = null;

    if (storedUserJSON !== null) {
      storedUser = JSON.parse(storedUserJSON);
    }

    if (storedUser !== null) {
      token = storedUser.access_token;
    } else {
      console.error('User data not found in localStorage.');
    }
    const response = await axios.post(`${API_BASE_URL}/elections`, {
      name: name,
      description: description,
      voters: voters,
      candidates: candidates,
    }, {
      headers: {
        Authorization: `Bearer ${token}`,
      }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to create a new election', error);
    throw error;
  }
}

export const fetchElections = async (): Promise<Election[]> => {
  try {
    const response = await axios.get<Election[]>(`${API_BASE_URL}/elections`);
    return response.data;
  } catch (error) {
    console.error('Error fetching all elections:', error);
    throw error;
  }
}

export const fetchElectionById = async (id: number): Promise<Election_> => {
  try {
    const response = await axios.get<Election_>(`${API_BASE_URL}/elections/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching the election:', error);
    throw error;
  }
}

export const addVoterToElection = async (id: number) => {
  const storedUserJSON = localStorage.getItem('user');
  let token = "";
  let storedUser: { access_token: string; role: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }
  try {
    const response = await axios.post(`${API_BASE_URL}/elections/${id}/add_voter`, {}, {
      headers: {
        Authorization: `Bearer ${token}`,
      }
    })
    return response.data;
  } catch (error) {
    console.error('Error adding the voter to the election', error);
    throw error;
  }
}

export const fetchUserElectionList = async (id: number): Promise<Election[]> => {
  const storedUserJSON = localStorage.getItem('user');
  let token = "";
  let storedUser: { access_token: string; role: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }
  try {
    const response = await axios.get<Election[]>(`${API_BASE_URL}/elections/users/${id}/elections`, {
      headers: {
        Authorization: `Bearer ${token}`,
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching the elections for the user:', error);
    throw (error);
  }
}
