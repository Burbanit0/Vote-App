import React, { createContext, useCallback, useContext, useState } from 'react';

interface ExpertModeContextValue {
  expertMode: boolean;
  setExpertMode: (value: boolean) => void;
}

const ExpertModeContext = createContext<ExpertModeContextValue>({
  expertMode: false,
  setExpertMode: () => {},
});

export function useExpertMode(): ExpertModeContextValue {
  return useContext(ExpertModeContext);
}

export const ExpertModeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [expertMode, setExpertModeState] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('votelab_expert') === 'true';
  });

  const setExpertMode = useCallback((value: boolean) => {
    localStorage.setItem('votelab_expert', String(value));
    setExpertModeState(value);
  }, []);

  return (
    <ExpertModeContext.Provider value={{ expertMode, setExpertMode }}>
      {children}
    </ExpertModeContext.Provider>
  );
};
