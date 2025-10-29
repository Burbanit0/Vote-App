import axios from 'axios';
import { User, Party } from '../types';

const API_BASE_URL = 'http://localhost:4433';

export const createParty = async (name: string, description: string) => {
    try {
        const storedUserJSON = localStorage.getItem('user');
            let token = "";
            let storedUser: { access_token: string; user_id: number } | null = null;

            if (storedUserJSON !== null) {
            storedUser = JSON.parse(storedUserJSON);
            }

            if (storedUser !== null) {
            token = storedUser.access_token;
            } else {
            console.error('User data not found in localStorage.');
            }
            const response = await axios.post(`${API_BASE_URL}/parties`, {
            name: name,
            description: description,
            }, {
            headers: {
                Authorization: `Bearer ${token}`,
            }
            });
            return response.data;
        } catch (error) {
            console.error('Failed to create a new party', error);
            throw error;
        }
    }

export const fetchMembers = async (id: number): Promise<User[]> => {
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
    const response = await axios.get<User[]>(
      `${API_BASE_URL}/parties/${id}/users`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        }
      }
    );
    return response.data;
    } catch (error) {
        console.error('Error fetching the elections participants:', error);
        throw error;
    }
}

export const removeUserFromParty = async (id: number, party_id: number) => {
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
        const response = await axios.post(
            `${API_BASE_URL}/parties/${id}/remove-party`, 
            {},
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                }
            })
        return response.data; 
    } catch (error) {
        console.error('Error removing the user from the party:', error);
        throw error;
    }
}

export const addUserFromParty = async (id: number, party_id: number) => {
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
        const response = await axios.post(
            `${API_BASE_URL}/parties/${id}/assign-party`, 
            {
                party_id: party_id,
            },
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                }
            })
        return response.data; 
    } catch (error) {
        console.error('Error adding the user to the party:', error);
        throw error;
    }
}

export const fetchAllParties = async (): Promise<Party[]> => {
  try {
    const response = await axios.get<Party[]>(`${API_BASE_URL}/parties`);
    return response.data;
  } catch (error) {
    console.error('Error fetching all parties:', error);
    throw error;
  }
}

export const fetchPartyById = async (id: number): Promise<Party> => {
  try {
    const response = await axios.get<Party>(`${API_BASE_URL}/parties/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching the election:', error);
    throw error;
  }
}

export const fetchUserParty = async (): Promise<Party> => {
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
        const response = await axios.get<Party>(
            `${API_BASE_URL}/api/auth/users/me/party`, 
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                }
            }
        );
        return response.data;
    } catch (error) {
        console.error('Error fetching the party:', error);
        throw error;
    }
}
