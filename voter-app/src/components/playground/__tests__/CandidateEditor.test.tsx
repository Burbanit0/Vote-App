import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// PlaygroundProvider pulls in the live-diagnostics hook, which debounces a call to profileApi,
// and (in parliament mode) the assembly endpoints: neither is under test here.
vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockRejectedValue(new Error('not under test')),
}));
vi.mock('../../../services/assemblyApi', () => ({
  runAssembly: vi.fn().mockRejectedValue(new Error('not under test')),
  runAssemblyScorecard: vi.fn().mockRejectedValue(new Error('not under test')),
}));

import { PlaygroundProvider } from '../PlaygroundController';
import ElectorateMoment from '../moments/ElectorateMoment';
import {
  useElectionStore,
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
} from '../../../stores/useElectionStore';

// The list of candidates used to come only from a preset, a story or the home page; positions were
// draggable and nothing else was. What is pinned here: the panel ships closed (the playground's
// form-lock), edits go straight to the shared config (so the map, the winner and every method
// follow), and nothing invalid ever reaches it (the backend refuses duplicates and 1-8 limits).

const names = () => useElectionStore.getState().config.candidates.map((c) => c.name);

function mount() {
  render(
    <PlaygroundProvider>
      <ElectorateMoment />
    </PlaygroundProvider>
  );
}
const open = () => fireEvent.click(screen.getByTestId('module-candidates-toggle'));
const nameInput = (i: number) => screen.getByTestId(`candidate-name-${i}`) as HTMLInputElement;
const type = (i: number, value: string) => fireEvent.change(nameInput(i), { target: { value } });

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    config: { ...DEFAULT_CONFIG },
    playground: { ...DEFAULT_PLAYGROUND },
    scenarioMeta: null,
  });
});

describe('CandidateEditor', () => {
  it('ships closed: nothing of the editor is mounted until it is opened', () => {
    mount();
    expect(screen.getByTestId('module-candidates-toggle')).toBeInTheDocument();
    expect(screen.queryByTestId('candidate-editor')).not.toBeInTheDocument();
  });

  it('lists every candidate with its name', () => {
    mount();
    open();
    expect([0, 1, 2].map((i) => nameInput(i).value)).toEqual(['Alice', 'Bob', 'Carol']);
    expect(screen.queryByTestId('candidate-name-3')).not.toBeInTheDocument();
  });

  describe('adding', () => {
    it('appends a named candidate, placed away from the others, in the shared config', () => {
      mount();
      open();
      fireEvent.click(screen.getByTestId('candidate-add'));
      const { candidates } = useElectionStore.getState().config;
      expect(candidates.map((c) => c.name)).toEqual(['Alice', 'Bob', 'Carol', 'Candidate 4']);
      const added = candidates[3];
      for (const c of candidates.slice(0, 3)) {
        expect(Math.hypot(added.x - c.x, added.y - c.y)).toBeGreaterThan(0.4);
      }
      expect(nameInput(3).value).toBe('Candidate 4'); // and the new row is there to rename
    });

    it('stops at eight, and says why', () => {
      const eight = Array.from({ length: 8 }, (_, i) => ({ name: `C${i}`, x: i / 10, y: 0 }));
      useElectionStore.setState({ config: { ...DEFAULT_CONFIG, candidates: eight } });
      mount();
      open();
      const add = screen.getByTestId('candidate-add');
      expect(add).toBeDisabled();
      expect(add).toHaveAttribute('title', 'At most 8.');
    });
  });

  describe('removing', () => {
    it('drops that candidate and keeps the others, in order', () => {
      mount();
      open();
      fireEvent.click(screen.getByTestId('candidate-remove-1'));
      expect(names()).toEqual(['Alice', 'Carol']);
      expect([0, 1].map((i) => nameInput(i).value)).toEqual(['Alice', 'Carol']);
    });

    it('stops at two, and says why', () => {
      useElectionStore.setState({
        config: { ...DEFAULT_CONFIG, candidates: DEFAULT_CONFIG.candidates.slice(0, 2) },
      });
      mount();
      open();
      for (const i of [0, 1]) {
        expect(screen.getByTestId(`candidate-remove-${i}`)).toBeDisabled();
      }
      expect(screen.getByTestId('candidate-remove-0')).toHaveAttribute(
        'title',
        'At least 2 are needed.'
      );
    });
  });

  describe('renaming', () => {
    it('commits a valid name on blur, trimmed', () => {
      mount();
      open();
      type(1, '  Robert ');
      fireEvent.blur(nameInput(1));
      expect(names()).toEqual(['Alice', 'Robert', 'Carol']);
      expect(nameInput(1).value).toBe('Robert');
    });

    it('commits on Enter', () => {
      mount();
      open();
      type(0, 'Zed');
      fireEvent.keyDown(nameInput(0), { key: 'Enter' });
      expect(names()[0]).toBe('Alice'); // Enter blurs the field, which commits (jsdom: do it by hand)
      fireEvent.blur(nameInput(0));
      expect(names()[0]).toBe('Zed');
    });

    it('refuses a name another candidate has: says so, and nothing reaches the config', () => {
      mount();
      open();
      type(0, 'Bob');
      expect(screen.getByRole('alert')).toHaveTextContent('Another one already has this name.');
      expect(nameInput(0)).toHaveAttribute('aria-invalid', 'true');
      fireEvent.blur(nameInput(0));
      expect(names()).toEqual(['Alice', 'Bob', 'Carol']);
      // Left as typed, with its reason still showing: not silently put back.
      expect(nameInput(0).value).toBe('Bob');
      expect(screen.getByRole('alert')).toBeInTheDocument();
      fireEvent.keyDown(nameInput(0), { key: 'Escape' });
      expect(nameInput(0).value).toBe('Alice');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('refuses an empty name', () => {
      mount();
      open();
      type(2, '   ');
      expect(screen.getByRole('alert')).toHaveTextContent('A name is needed.');
      fireEvent.blur(nameInput(2));
      expect(names()[2]).toBe('Carol');
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('refuses a name past 64 characters, and tells the limit', () => {
      mount();
      open();
      type(0, 'x'.repeat(65));
      expect(screen.getByRole('alert')).toHaveTextContent('At most 64 characters.');
      fireEvent.blur(nameInput(0));
      expect(names()[0]).toBe('Alice');
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('fixing a refused name clears the reason and commits it', () => {
      mount();
      open();
      type(0, 'Bob');
      type(0, 'Bobby');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      fireEvent.blur(nameInput(0));
      expect(names()[0]).toBe('Bobby');
    });

    it('does not take Enter that confirms an IME composition for the end of the name', () => {
      mount();
      open();
      act(() => nameInput(0).focus());
      type(0, 'Zé');
      fireEvent.keyDown(nameInput(0), { key: 'Enter', isComposing: true });
      expect(nameInput(0)).toHaveFocus();
      expect(names()[0]).toBe('Alice');
      fireEvent.keyDown(nameInput(0), { key: 'Enter' });
      expect(nameInput(0)).not.toHaveFocus();
    });

    it('Escape puts the old name back', () => {
      mount();
      open();
      type(0, 'Zed');
      fireEvent.keyDown(nameInput(0), { key: 'Escape' });
      expect(nameInput(0).value).toBe('Alice');
      fireEvent.blur(nameInput(0));
      expect(names()[0]).toBe('Alice');
    });

    it('leaving a field as it was changes nothing', () => {
      mount();
      open();
      const before = useElectionStore.getState().config;
      fireEvent.blur(nameInput(1));
      type(1, ' Bob ');
      fireEvent.blur(nameInput(1));
      expect(useElectionStore.getState().config).toBe(before);
    });

    it('keeps a name the config changes underneath it: the config is the truth', async () => {
      mount();
      open();
      type(1, 'half-typed');
      act(() =>
        useElectionStore.setState({
          config: {
            ...DEFAULT_CONFIG,
            candidates: DEFAULT_CONFIG.candidates.map((c, i) =>
              i === 1 ? { ...c, name: 'Elsewhere' } : c
            ),
          },
        })
      );
      await waitFor(() => expect(nameInput(1).value).toBe('Elsewhere'));
    });
  });

  describe('rows keep their identity', () => {
    it("a removal leaves another row's half-typed name where it is", () => {
      mount();
      open();
      type(2, 'draft in progress'); // not committed: no blur yet
      fireEvent.click(screen.getByTestId('candidate-remove-0'));
      expect(names()).toEqual(['Bob', 'Carol']);
      // Carol is row 1 now, and still has her own draft (an index key would have lost it).
      expect(nameInput(1).value).toBe('draft in progress');
      expect(nameInput(0).value).toBe('Bob');
    });

    it('a removal hands focus to a neighbouring name, not to the page', () => {
      useElectionStore.setState({
        config: {
          ...DEFAULT_CONFIG,
          candidates: [...DEFAULT_CONFIG.candidates, { name: 'Dana', x: 0.1, y: 0.1 }],
        },
      });
      mount();
      open();
      fireEvent.click(screen.getByTestId('candidate-remove-3')); // the last of four
      expect(nameInput(2)).toHaveFocus(); // the one before it
      fireEvent.click(screen.getByTestId('candidate-remove-0')); // the first of three
      expect(nameInput(0)).toHaveFocus(); // whoever is first now
    });

    it('committing a name does not remount the row: Tab from the name to the button keeps focus', () => {
      mount();
      open();
      const remove = screen.getByTestId('candidate-remove-0');
      act(() => nameInput(0).focus());
      type(0, 'Zed');
      act(() => remove.focus()); // blur on the name commits it
      expect(names()[0]).toBe('Zed');
      expect(screen.getByTestId('candidate-remove-0')).toBe(remove); // the same node
      expect(remove).toHaveFocus();
    });

    it('a list changed from outside (a preset) starts again with the new names', async () => {
      mount();
      open();
      type(0, 'half-typed');
      act(() =>
        useElectionStore.setState({
          config: {
            ...DEFAULT_CONFIG,
            candidates: [
              { name: 'P', x: 0, y: 0 },
              { name: 'Q', x: 1, y: 0 },
            ],
          },
        })
      );
      await waitFor(() => expect([nameInput(0).value, nameInput(1).value]).toEqual(['P', 'Q']));
      expect(screen.queryByTestId('candidate-name-2')).not.toBeInTheDocument();
    });
  });

  it('a typed name reaches a screen reader as typed: R&D is not "R&amp;D"', () => {
    mount();
    open();
    type(0, 'R&D <3');
    fireEvent.blur(nameInput(0));
    expect(screen.getByRole('button', { name: 'Remove R&D <3' })).toBeInTheDocument();
  });

  it('says parties, not candidates, for the assembly question', () => {
    useElectionStore.setState({ playground: { ...DEFAULT_PLAYGROUND, mode: 'parliament' } });
    mount();
    expect(screen.getByTestId('module-candidates-toggle')).toHaveTextContent('Parties');
    open();
    fireEvent.click(screen.getByTestId('candidate-add'));
    expect(names()[3]).toBe('Party 4');
    expect(nameInput(0)).toHaveAttribute('aria-label', 'Name of party 1');
  });

  it('shows the count in the closed panel, so the list can be read without opening it', () => {
    mount();
    expect(screen.getByTestId('module-candidates-toggle')).toHaveTextContent('3 of 8');
  });
});
