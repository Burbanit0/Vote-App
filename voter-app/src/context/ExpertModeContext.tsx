/**
 * ExpertModeContext — compatibility shim over useUIStore (Phase 5.4).
 */
import React, { useEffect } from 'react';
import { useUIStore } from '../stores/useUIStore';

interface ExpertModeContextValue {
  expertMode: boolean;
  setExpertMode: (value: boolean) => void;
}

export function useExpertMode(): ExpertModeContextValue {
  const expertMode = useUIStore((s) => s.expertMode);
  const setExpertMode = useUIStore((s) => s.setExpertMode);
  return { expertMode, setExpertMode };
}

export const ExpertModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hydrate = useUIStore((s) => s.hydrate);
  useEffect(() => { hydrate(); }, [hydrate]);
  return <>{children}</>;
};
