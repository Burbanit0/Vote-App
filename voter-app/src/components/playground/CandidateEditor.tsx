import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { useStoreCtx } from './PlaygroundController';
import type { ElectionCandidate, ElectionConfig } from '../../stores/useElectionStore';
import { candidateColor } from '../../lib/palette';
import {
  MAX_CANDIDATES,
  MAX_NAME_LENGTH,
  MIN_CANDIDATES,
  addCandidate,
  canAdd,
  canRemove,
  nameProblem,
  nextName,
  placeNewcomer,
  removeCandidate,
  renameCandidate,
} from '../../lib/candidateEditing';

// CandidateEditor — rename, add and remove the candidates (or parties). The list used to come
// only from a preset, a story or the home page; positions were draggable, nothing else was.
// Everything downstream reads `config.candidates`, so the map, the winner and every method
// follow an edit with nothing to wire.

/** A name field that commits on Enter or blur, and only when the name is valid: a half-typed
 *  duplicate never reaches the config (and so never reaches a request the backend would refuse). */
const NameInput: React.FC<{
  name: string;
  others: string[];
  label: string;
  onCommit: (name: string) => void;
  testId: string;
}> = ({ name, others, label, onCommit, testId }) => {
  const { t } = useTranslation('playground');
  const [draft, setDraft] = React.useState(name);
  // The config is the truth: a rename elsewhere, or a row removed above this one, shows here.
  React.useEffect(() => setDraft(name), [name]);

  const problem = draft.trim() === name ? null : nameProblem(draft, others);
  // A valid name is committed; an unchanged one is tidied (spaces); an invalid one is LEFT as typed
  // with its reason showing, not silently put back: Escape (or a fix) is the way out.
  const commit = () => {
    if (draft.trim() === name) setDraft(name);
    else if (problem === null) onCommit(draft);
  };
  const errorId = `${testId}-error`;

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
      <input
        data-testid={testId}
        type="text"
        aria-label={label}
        aria-invalid={problem !== null}
        aria-describedby={problem ? errorId : undefined}
        maxLength={MAX_NAME_LENGTH + 20} // room to type a too-long name and be told why
        className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          // Enter also confirms an IME composition: that one is not the end of the name.
          if (e.key === 'Enter' && !e.nativeEvent.isComposing) e.currentTarget.blur();
          if (e.key === 'Escape') setDraft(name);
        }}
      />
      {problem && (
        <span id={errorId} role="alert" className="text-[0.7rem] text-destructive">
          {t(`candidates.err_${problem}`, { max: MAX_NAME_LENGTH })}
        </span>
      )}
    </div>
  );
};

const CandidateEditor: React.FC = () => {
  const { t } = useTranslation('playground');
  const { config, setConfig, dims, mode } = useStoreCtx();
  const leader = mode === 'leader';
  const names = config.candidates.map((c) => c.name);
  const count = names.length;
  const editor = React.useRef<HTMLDivElement>(null);

  // A stable id per row, so a row keeps its own half-typed name and its focus when another row is
  // removed or this one is renamed (an index key pairs a row with the wrong draft; a name key
  // remounts the row mid-Tab). The editor's own edits say which ids the new list carries; a list
  // that changed any other way (a preset, a story) gets fresh ones.
  const lastId = React.useRef(0);
  const planned = React.useRef<{ list: ElectionCandidate[]; ids: number[] } | null>(null);
  const ids = React.useMemo(
    () =>
      planned.current?.list === config.candidates
        ? planned.current.ids
        : config.candidates.map(() => lastId.current++),
    [config.candidates]
  );
  const edit = (patch: Pick<ElectionConfig, 'candidates'>, nextIds: number[]) => {
    planned.current = { list: patch.candidates, ids: nextIds };
    setConfig(patch);
  };

  // After a removal the focused button is gone: hand focus to a neighbouring row's name.
  const refocus = React.useRef<number | null>(null);
  React.useEffect(() => {
    if (refocus.current === null) return;
    const row = refocus.current;
    refocus.current = null;
    editor.current
      ?.querySelector<HTMLInputElement>(`[data-testid="candidate-name-${row}"]`)
      ?.focus();
  }, [config.candidates]);

  const add = () => {
    const base = leader ? t('candidates.defaultName') : t('candidates.defaultParty');
    const newcomer = { name: nextName(base, names), ...placeNewcomer(config.candidates, dims) };
    edit(addCandidate(config, newcomer), [...ids, lastId.current++]);
  };
  const remove = (i: number) => {
    refocus.current = Math.min(i, count - 2);
    edit(
      removeCandidate(config, i),
      ids.filter((_, j) => j !== i)
    );
  };

  return (
    <div ref={editor} data-testid="candidate-editor" className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground">
        {t('candidates.hint', { min: MIN_CANDIDATES, max: MAX_CANDIDATES })}
      </p>
      <ul className="flex flex-col gap-1.5">
        {config.candidates.map((c, i) => (
          <li key={ids[i]} data-testid={`candidate-row-${i}`} className="flex items-start gap-2">
            <span
              aria-hidden="true"
              className="mt-2 h-3 w-3 shrink-0 rounded-full"
              style={{ background: candidateColor(i) }}
            />
            <NameInput
              testId={`candidate-name-${i}`}
              name={c.name}
              others={names.filter((_, j) => j !== i)}
              label={t(leader ? 'candidates.nameLabel' : 'candidates.nameLabelParty', { n: i + 1 })}
              onCommit={(next) => edit(renameCandidate(config, i, next), ids)}
            />
            <button
              type="button"
              data-testid={`candidate-remove-${i}`}
              disabled={!canRemove(count)}
              // A typed name: no HTML escaping ("R&D" must not read "R&amp;D" to a screen reader).
              aria-label={t('candidates.remove', {
                name: c.name,
                interpolation: { escapeValue: false },
              })}
              title={
                canRemove(count) ? undefined : t('candidates.removeMin', { min: MIN_CANDIDATES })
              }
              className="mt-0.5 rounded-md border border-input px-2 py-0.5 text-sm text-muted-foreground hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
              onClick={() => remove(i)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        variant="outline"
        size="sm"
        data-testid="candidate-add"
        className="self-start"
        disabled={!canAdd(count)}
        title={canAdd(count) ? undefined : t('candidates.addMax', { max: MAX_CANDIDATES })}
        onClick={add}
      >
        {t(leader ? 'candidates.add' : 'candidates.addParty')}
      </Button>
    </div>
  );
};

export default CandidateEditor;
