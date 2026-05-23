/**
 * useScenarioPersistence — owns the Save / Load modal state for
 * SimulationComparePage.
 *
 * Replaces these 6 useState calls (which formerly lived inline at the top
 * of SimulationComparePage):
 *
 *   const [showSaveModal, setShowSaveModal] = useState(false);
 *   const [saveName,      setSaveName]      = useState('');
 *   const [saving,        setSaving]        = useState(false);
 *   const [showLoadModal, setShowLoadModal] = useState(false);
 *   const [scenarioList,  setScenarioList]  = useState<ScenarioSummary[]>([]);
 *   const [loadingList,   setLoadingList]   = useState(false);
 *
 * with a single useReducer + a few focused action creators. Net effect:
 *   - SimulationComparePage loses 6 useStates and 3 callbacks (~25 LOC)
 *   - related state transitions are co-located and named (open/close,
 *     setName, saveCurrent, refreshList, removeFromList)
 *   - persistence logic (axios calls in services/scenariosApi) lives in
 *     the hook, so the page only sees a Promise<void> contract.
 */
import { useCallback, useReducer } from 'react';
import { ScenarioSummary } from '../types';
import { saveScenario, listScenarios, deleteScenario } from '../services/scenariosApi';

// ── State + actions ─────────────────────────────────────────────────────────

interface State {
  showSave:    boolean;
  showLoad:    boolean;
  saveName:    string;
  saving:      boolean;
  list:        ScenarioSummary[];
  loadingList: boolean;
}

const INITIAL: State = {
  showSave:    false,
  showLoad:    false,
  saveName:    '',
  saving:      false,
  list:        [],
  loadingList: false,
};

type Action =
  | { type: 'OPEN_SAVE' }
  | { type: 'CLOSE_SAVE' }
  | { type: 'SET_NAME';        name: string }
  | { type: 'SAVE_START' }
  | { type: 'SAVE_END' }
  | { type: 'OPEN_LOAD' }
  | { type: 'CLOSE_LOAD' }
  | { type: 'LOAD_LIST_START' }
  | { type: 'LOAD_LIST_END';   list: ScenarioSummary[] }
  | { type: 'REMOVE_FROM_LIST'; id: number };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'OPEN_SAVE':         return { ...state, showSave: true,  saveName: '' };
    case 'CLOSE_SAVE':        return { ...state, showSave: false };
    case 'SET_NAME':          return { ...state, saveName: action.name };
    case 'SAVE_START':        return { ...state, saving:   true };
    case 'SAVE_END':          return { ...state, saving:   false, showSave: false, saveName: '' };
    case 'OPEN_LOAD':         return { ...state, showLoad: true,  loadingList: true };
    case 'CLOSE_LOAD':        return { ...state, showLoad: false };
    case 'LOAD_LIST_START':   return { ...state, loadingList: true };
    case 'LOAD_LIST_END':     return { ...state, loadingList: false, list: action.list };
    case 'REMOVE_FROM_LIST':  return { ...state, list: state.list.filter((s) => s.id !== action.id) };
  }
}

// ── Public API ──────────────────────────────────────────────────────────────

export interface UseScenarioPersistenceResult {
  showSave:        boolean;
  showLoad:        boolean;
  saveName:        string;
  saving:          boolean;
  list:            ScenarioSummary[];
  loadingList:     boolean;
  openSave:        () => void;
  closeSave:       () => void;
  setName:         (s: string) => void;
  /** Persist the snapshot; resolves once the request has completed (success or fail). */
  saveCurrent:     (config: Record<string, any>, results?: Record<string, any> | null) => Promise<void>;
  openLoad:        () => Promise<void>;
  closeLoad:       () => void;
  removeFromList:  (id: number) => Promise<void>;
}

export function useScenarioPersistence(): UseScenarioPersistenceResult {
  const [state, dispatch] = useReducer(reducer, INITIAL);

  const openSave   = useCallback(() => dispatch({ type: 'OPEN_SAVE' }),  []);
  const closeSave  = useCallback(() => dispatch({ type: 'CLOSE_SAVE' }), []);
  const setName    = useCallback((s: string) => dispatch({ type: 'SET_NAME', name: s }), []);
  const closeLoad  = useCallback(() => dispatch({ type: 'CLOSE_LOAD' }), []);

  const saveCurrent = useCallback(
    async (config: Record<string, any>, results?: Record<string, any> | null) => {
      dispatch({ type: 'SAVE_START' });
      try {
        await saveScenario(state.saveName.trim(), config, results);
      } finally {
        dispatch({ type: 'SAVE_END' });
      }
    },
    [state.saveName]
  );

  const openLoad = useCallback(async () => {
    dispatch({ type: 'OPEN_LOAD' });
    try {
      const list = await listScenarios();
      dispatch({ type: 'LOAD_LIST_END', list });
    } catch {
      dispatch({ type: 'LOAD_LIST_END', list: [] });
    }
  }, []);

  const removeFromList = useCallback(async (id: number) => {
    await deleteScenario(id);
    dispatch({ type: 'REMOVE_FROM_LIST', id });
  }, []);

  return {
    showSave:    state.showSave,
    showLoad:    state.showLoad,
    saveName:    state.saveName,
    saving:      state.saving,
    list:        state.list,
    loadingList: state.loadingList,
    openSave,
    closeSave,
    setName,
    saveCurrent,
    openLoad,
    closeLoad,
    removeFromList,
  };
}
