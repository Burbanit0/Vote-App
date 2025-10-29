import axios from 'axios';
import { Election, Election_, PaginatedResponse, Participant, ParticipationStatus, UpdateElectionData } from '../types';

const API_BASE_URL = 'http://localhost:4433';

export const createElection = async (name: string, description: string, startDate: string, endDate: string) => {
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
    const response = await axios.post(`${API_BASE_URL}/elections`, {
      name: name,
      description: description,
      create_at: Date.now(),
      start_date: startDate,
      end_date: endDate,
      created_by: storedUser?.user_id,
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

export const fetchAllElections = async (currentPage: number, searchTerm:string, sortBy:string, sortDir:string, status:string): Promise<PaginatedResponse> => {
  try {
    const response = await axios.get<PaginatedResponse>(`${API_BASE_URL}/elections`, {
      params:{
        page: currentPage,
        search: searchTerm,
        sort_by: sortBy,
        sort_dir: sortDir,
        status: status,
      }
    });
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

export const fetchParticipants = async (id: number): Promise<Participant[]> => {
  const token = localStorage.getItem('access_token');

  try {
    const response = await axios.get<Participant[]>(
      `${API_BASE_URL}/elections/${id}/participants`,
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
    const response = await axios.post(`${API_BASE_URL}/elections/${id}/participate`, {}, {
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

export const addCandidateToElection = async (id: number) => {
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
    const response = await axios.post(`${API_BASE_URL}/elections/${id}/register-candidate`, {}, {
      headers: {
        Authorization: `Bearer ${token}`,
      }
    })
    return response.data;
  } catch (error) {
    console.error('Error adding the candidate to the election', error);
    throw error;
  }
}

export const fetchUserElectionList = async (id: number): Promise<Election[]> => {
  const storedUserJSON = localStorage.getItem('user');
  let token = "";
  let storedUser: { access_token: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }
  
  try {
    const response = await axios.get<Election[]>(
      `${API_BASE_URL}/elections/users/${id}/elections`,
      {
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

export const isParticipating = async (election_id: number): Promise<ParticipationStatus> => {
  const storedUserJSON = localStorage.getItem('user');
  let token = "";
  let storedUser: { access_token: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }
  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }
  
  try {
      const response = await axios.get(
          `${API_BASE_URL}/elections/${election_id}/participation`,
          {
            headers: {
              Authorization: `Bearer ${token}`
            }
          });
          return response.data;
      } catch(error) {
        console.error('Error getting the participation info:', error);
        throw(error);
      }
}

export const cancelElectionParticipation = async (election_id:number) => {
    const storedUserJSON = localStorage.getItem('user');
    let token = "";
    let storedUser: { access_token: string } | null = null;

    if (storedUserJSON !== null) {
      storedUser = JSON.parse(storedUserJSON);
    }
    if (storedUser !== null) {
      token = storedUser.access_token;
    } else {
      console.error('User data not found in localStorage.');
    }
    try {
      const response = await axios.post(`${API_BASE_URL}/elections/${election_id}/cancel-participation`,
      {},
      { headers:
        {
          Authorization: `Bearer ${token}`
        }
      });
      return response.data;
    } catch(error) {
      console.error('Error canceling the participation :', error);
      throw(error);
    }
}

export const fetchElectionResults = async (election_id:number) => {
      const storedUserJSON = localStorage.getItem('user');
      let token = "";
      let storedUser: { access_token: string } | null = null;

      if (storedUserJSON !== null) {
        storedUser = JSON.parse(storedUserJSON);
      }
      if (storedUser !== null) {
        token = storedUser.access_token;
      } else {
        console.error('User data not found in localStorage.');
      }
      try {
        const response = await axios.get(
          `${API_BASE_URL}/elections/${election_id}/results`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        return response.data;
      } catch(error) {
        console.error('Failed to fetch the result for the election :', error)
        throw(error);
      }
}

export const updateElection = async (electionId: number, electionData: UpdateElectionData): Promise<Election> => {
      const storedUserJSON = localStorage.getItem('user');
      let token = "";
      let storedUser: { access_token: string } | null = null;

      if (storedUserJSON !== null) {
        storedUser = JSON.parse(storedUserJSON);
      }
      if (storedUser !== null) {
        token = storedUser.access_token;
      } else {
        console.error('User data not found in localStorage.');
      }
      try {
        const response = await axios.put(`${API_BASE_URL}/elections/${electionId}`, electionData, 
          { headers: { Authorization: `Bearer ${token}` } }
        );
        return response.data.election;
      } catch(error) {
        console.error('Failed to update the election:', error)
        throw(error);
      }
}

export const deleteElection = async (electionId: number) => {
      const storedUserJSON = localStorage.getItem('user');
      let token = "";
      let storedUser: { access_token: string } | null = null;

      if (storedUserJSON !== null) {
        storedUser = JSON.parse(storedUserJSON);
      }
      if (storedUser !== null) {
        token = storedUser.access_token;
      } else {
        console.error('User data not found in localStorage.');
      }
      try {
        const response = await axios.delete(`${API_BASE_URL}/elections/${electionId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        return response.data;
      } catch(error) {
        console.error('Failed to delete the election:', error)
        throw(error);
      }
}