import axios from 'axios';

const API_BASE_URL = 'http://localhost:4433';

export const simulateVote = async (numVoters: number, numCandidates: number) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations`, {
      num_voters: numVoters,
      num_candidates: numCandidates,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to simulate votes. Please try again.', error);
    throw error;
  }
}

export const simulatePop = async (numVoters: number, averageAge: number) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/simulate_voters`, {
      num_voters: numVoters,
      avg_age: averageAge,
    });
    return response.data.coord;
  } catch (error) {
    console.error('Failed to get the coord', error);
    throw error;
  }
}

export const closestCandidate = async (voters: number[], candidates: number[]) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/simulations/get_closest_candidate`, {
      candidates: candidates,
      voters: voters,
    });
    return response.data.result;
  } catch (error) {
    console.error('Failed to get the closest candidates', error);
    throw error;
  }
}
