import { useState, useEffect } from 'react';
import { UserPermissions } from '../types';
import { checkPermissions } from '../services';


const useUserPermissions = () => {
  const [permissions, setPermissions] = useState<UserPermissions>({
    is_admin: false,
    participation_points: 0,
    canCreateElections: false,
    is_loading: true,
    error: null
  });

  useEffect(() => {
    const checkPermission = async () => {
        try {
            const response = await checkPermissions();
            setPermissions({
            is_admin: response.is_admin,
            participation_points: response.participation_points,
            canCreateElections: response.is_admin || response.participation_points >= 100,
            is_loading: false,
            error: null
            });
        } catch (error) {
            setPermissions(prev => ({
            ...prev,
            isLoading: false,
            error: 'Failed to fetch user permissions'
            }));
          }
        };
    checkPermission();
  }, []);

  return permissions;
};

export default useUserPermissions;