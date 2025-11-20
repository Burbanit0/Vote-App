import { Election } from '../types';

export function getElectionStatus(election: Election): string {
  const now = new Date();
  const startDate = new Date(election.start_date);
  const endDate = new Date(election.end_date);

  if (now < startDate) {
    return 'upcoming';
  } else if (now >= startDate && now <= endDate) {
    return 'active';
  } else {
    return 'completed';
  }
}
