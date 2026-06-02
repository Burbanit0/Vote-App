import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { useScenarioPersistence } from './useScenarioPersistence';

vi.mock('../services/scenariosApi', () => ({
  saveScenario:   vi.fn(),
  listScenarios:  vi.fn(),
  deleteScenario: vi.fn(),
}));

const mocked = (await import('../services/scenariosApi')) as unknown as {
  saveScenario:   jest.Mock;
  listScenarios:  jest.Mock;
  deleteScenario: jest.Mock;
};

function Harness() {
  const p = useScenarioPersistence();
  return (
    <div>
      <span data-testid="show-save">{p.showSave ? 'yes' : 'no'}</span>
      <span data-testid="show-load">{p.showLoad ? 'yes' : 'no'}</span>
      <span data-testid="save-name">{p.saveName}</span>
      <span data-testid="saving">{p.saving ? 'yes' : 'no'}</span>
      <span data-testid="list">{p.list.map((s) => s.id).join(',')}</span>
      <span data-testid="loading">{p.loadingList ? 'yes' : 'no'}</span>
      <button data-testid="open-save" onClick={p.openSave}>open save</button>
      <button data-testid="close-save" onClick={p.closeSave}>close save</button>
      <button data-testid="set-name" onClick={() => p.setName('My scenario')}>set name</button>
      <button data-testid="save" onClick={() => { p.saveCurrent({ a: 1 }, { b: 2 }).catch(() => {}); }}>save</button>
      <button data-testid="open-load" onClick={() => p.openLoad()}>open load</button>
      <button data-testid="close-load" onClick={p.closeLoad}>close load</button>
      <button data-testid="remove" onClick={() => p.removeFromList(7)}>remove 7</button>
    </div>
  );
}

describe('useScenarioPersistence', () => {
  beforeEach(() => {
    mocked.saveScenario.mockReset();
    mocked.listScenarios.mockReset();
    mocked.deleteScenario.mockReset();
  });

  it('starts in a clean state', () => {
    render(<Harness />);
    expect(screen.getByTestId('show-save')).toHaveTextContent('no');
    expect(screen.getByTestId('show-load')).toHaveTextContent('no');
    expect(screen.getByTestId('save-name')).toHaveTextContent('');
    expect(screen.getByTestId('list')).toHaveTextContent('');
  });

  it('openSave shows the modal and clears the previous name', () => {
    render(<Harness />);
    act(() => { screen.getByTestId('set-name').click(); });
    expect(screen.getByTestId('save-name')).toHaveTextContent('My scenario');
    act(() => { screen.getByTestId('open-save').click(); });
    expect(screen.getByTestId('show-save')).toHaveTextContent('yes');
    expect(screen.getByTestId('save-name')).toHaveTextContent('');
  });

  it('setName updates the input', () => {
    render(<Harness />);
    act(() => { screen.getByTestId('set-name').click(); });
    expect(screen.getByTestId('save-name')).toHaveTextContent('My scenario');
  });

  it('saveCurrent toggles saving and closes the modal on success', async () => {
    mocked.saveScenario.mockResolvedValue({ id: 1 });
    render(<Harness />);
    act(() => { screen.getByTestId('open-save').click(); });
    act(() => { screen.getByTestId('set-name').click(); });
    await act(async () => { screen.getByTestId('save').click(); });
    expect(mocked.saveScenario).toHaveBeenCalledWith('My scenario', { a: 1 }, { b: 2 });
    expect(screen.getByTestId('show-save')).toHaveTextContent('no');
    expect(screen.getByTestId('save-name')).toHaveTextContent('');
    expect(screen.getByTestId('saving')).toHaveTextContent('no');
  });

  it('saveCurrent still flips saving back to false on failure', async () => {
    mocked.saveScenario.mockRejectedValue(new Error('boom'));
    // Swallow the unhandled rejection that the hook re-throws (by design:
    // the page handler is responsible for showing the toast).
    const originalError = console.error;
    console.error = vi.fn();
    render(<Harness />);
    act(() => { screen.getByTestId('set-name').click(); });
    await act(async () => {
      try {
        screen.getByTestId('save').click();
        // Give the rejection a microtask to surface
        await new Promise((r) => setTimeout(r, 10));
      } catch { /* expected */ }
    });
    await waitFor(() => expect(screen.getByTestId('saving')).toHaveTextContent('no'));
    console.error = originalError;
  });

  it('openLoad fetches the list and stores it', async () => {
    mocked.listScenarios.mockResolvedValue([{ id: 1, name: 'A' }, { id: 2, name: 'B' }]);
    render(<Harness />);
    await act(async () => { screen.getByTestId('open-load').click(); });
    expect(screen.getByTestId('show-load')).toHaveTextContent('yes');
    expect(screen.getByTestId('list')).toHaveTextContent('1,2');
    expect(screen.getByTestId('loading')).toHaveTextContent('no');
  });

  it('openLoad gracefully handles a fetch failure', async () => {
    mocked.listScenarios.mockRejectedValue(new Error('boom'));
    render(<Harness />);
    await act(async () => { screen.getByTestId('open-load').click(); });
    expect(screen.getByTestId('show-load')).toHaveTextContent('yes');
    expect(screen.getByTestId('list')).toHaveTextContent('');
    expect(screen.getByTestId('loading')).toHaveTextContent('no');
  });

  it('closeLoad just hides the modal (does not touch the list)', async () => {
    mocked.listScenarios.mockResolvedValue([{ id: 1, name: 'A' }]);
    render(<Harness />);
    await act(async () => { screen.getByTestId('open-load').click(); });
    expect(screen.getByTestId('list')).toHaveTextContent('1');
    act(() => { screen.getByTestId('close-load').click(); });
    expect(screen.getByTestId('show-load')).toHaveTextContent('no');
    expect(screen.getByTestId('list')).toHaveTextContent('1');
  });

  it('removeFromList calls the service then prunes locally', async () => {
    mocked.listScenarios.mockResolvedValue([
      { id: 7, name: 'A' }, { id: 8, name: 'B' },
    ]);
    mocked.deleteScenario.mockResolvedValue(undefined);
    render(<Harness />);
    await act(async () => { screen.getByTestId('open-load').click(); });
    expect(screen.getByTestId('list')).toHaveTextContent('7,8');
    await act(async () => { screen.getByTestId('remove').click(); });
    expect(mocked.deleteScenario).toHaveBeenCalledWith(7);
    expect(screen.getByTestId('list')).toHaveTextContent('8');
  });
});
