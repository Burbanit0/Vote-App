import { getElectionStatus } from './electionStatus';
import { Election } from '../types';

describe('getElectionStatus', () => {
  it('should return "upcoming" if current date is before start date', () => {
    const election: Election = {
      start_date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
      end_date: new Date(Date.now() + 172800000).toISOString(), // Day after tomorrow
    } as Election;
    expect(getElectionStatus(election)).toBe('upcoming');
  });

  it('should return "active" if current date is between start and end date', () => {
    const election: Election = {
      start_date: new Date(Date.now() - 86400000).toISOString(), // Yesterday
      end_date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
    } as Election;
    expect(getElectionStatus(election)).toBe('active');
  });

  it('should return "completed" if current date is after end date', () => {
    const election: Election = {
      start_date: new Date(Date.now() - 172800000).toISOString(), // Two days ago
      end_date: new Date(Date.now() - 86400000).toISOString(), // Yesterday
    } as Election;
    expect(getElectionStatus(election)).toBe('completed');
  });
});
