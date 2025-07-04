// useElectionParticipation.ts
import { useState, useEffect } from 'react';
import { ParticipationStatus } from '../types';
import { isParticipating } from '../services';

const useElectionParticipation = (electionId: number | null) => {
  const [status, setStatus] = useState<ParticipationStatus>({
    is_participant: false,
    role: null,
    isLoading: true,
    error: null
  });

  useEffect(() => {
    const checkParticipation = async () => {
      if (!electionId) {
        setStatus(prev => ({ ...prev, isLoading: false }));
        return;
      }

      try {
        const response = await isParticipating(electionId);

        setStatus({
          is_participant: response?.is_participant,
          role: response?.role,
          isLoading: false,
          error: null
        });
      } catch (error) {
        setStatus({
          is_participant: false,
          role: null,
          isLoading: false,
          error: 'Failed to check participation status'
        });
      }
    };

    checkParticipation();
  }, [electionId]);

  return status;
};

export default useElectionParticipation;