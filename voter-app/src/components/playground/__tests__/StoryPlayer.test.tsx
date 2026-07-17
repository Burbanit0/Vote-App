import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../../stores/useElectionStore';
import { storyById } from '../../../lib/stories';

// Mock the controller context: StoryPlayer must drive the live setters, so we spy
// on them and hand it a known "current sandbox" to snapshot + restore.
const setConfig = vi.fn();
const setPlayground = vi.fn();
const setMode = vi.fn();
const setLeaderRule = vi.fn();
const setActiveMoment = vi.fn();
const SNAP_CONFIG = { ...DEFAULT_CONFIG, seed: 999 };
const SNAP_PLAYGROUND = { ...DEFAULT_PLAYGROUND, behavior: 'strategic' as const };

vi.mock('../PlaygroundController', () => ({
  usePlaygroundCtx: () => ({
    config: SNAP_CONFIG,
    playground: SNAP_PLAYGROUND,
    leaderRule: 'borda',
    activeMoment: 'campaign',
    setConfig,
    setPlayground,
    setMode,
    setLeaderRule,
    setActiveMoment,
  }),
}));

import StoryPlayer from '../StoryPlayer';

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState({}, '', '/playground');
});

const spoiler = storyById('spoiler')!;

describe('StoryPlayer', () => {
  it('opens the picker and starts a story, applying its first beat', () => {
    render(<StoryPlayer />);
    fireEvent.click(screen.getByTestId('story-launch'));
    fireEvent.click(screen.getByTestId('story-pick-spoiler'));

    // First beat patches applied through the live setters.
    expect(setMode).toHaveBeenCalledWith('leader');
    expect(setLeaderRule).toHaveBeenCalledWith('plurality');
    expect(setActiveMoment).toHaveBeenCalledWith('method');
    expect(setConfig).toHaveBeenCalledWith(spoiler.steps[0].config);
    // The beat sentence renders (English, per the test locale).
    expect(screen.getByTestId('story-beat')).toHaveTextContent('under plurality, Gore beats Bush');
    expect(screen.getByTestId('story-bar')).toHaveTextContent('Scene 1 / 4');
  });

  it('next applies the following beat', () => {
    render(<StoryPlayer />);
    fireEvent.click(screen.getByTestId('story-launch'));
    fireEvent.click(screen.getByTestId('story-pick-spoiler'));
    setLeaderRule.mockClear();
    setConfig.mockClear();

    fireEvent.click(screen.getByTestId('story-next'));
    expect(setLeaderRule).toHaveBeenCalledWith('plurality'); // step 2 keeps plurality
    expect(setConfig).toHaveBeenCalledWith(spoiler.steps[1].config);
    expect(screen.getByTestId('story-bar')).toHaveTextContent('Scene 2 / 4');
    expect(screen.getByTestId('story-beat')).toHaveTextContent('That is the spoiler');
  });

  it('quit restores the pre-story sandbox verbatim', () => {
    render(<StoryPlayer />);
    fireEvent.click(screen.getByTestId('story-launch'));
    fireEvent.click(screen.getByTestId('story-pick-spoiler'));
    setConfig.mockClear();

    fireEvent.click(screen.getByTestId('story-quit'));
    expect(setConfig).toHaveBeenCalledWith(SNAP_CONFIG);
    expect(setPlayground).toHaveBeenCalledWith(SNAP_PLAYGROUND);
    expect(setLeaderRule).toHaveBeenCalledWith('borda');
    expect(setActiveMoment).toHaveBeenCalledWith('campaign');
    // Back to the idle launcher.
    expect(screen.getByTestId('story-launch')).toBeInTheDocument();
    expect(screen.queryByTestId('story-bar')).not.toBeInTheDocument();
  });

  it('auto-starts from the ?story= query param', () => {
    window.history.replaceState({}, '', '/playground?story=squeeze');
    render(<StoryPlayer />);
    expect(screen.getByTestId('story-bar')).toBeInTheDocument();
    expect(setActiveMoment).toHaveBeenCalledWith('method');
    expect(screen.getByTestId('story-beat')).toHaveTextContent('Left, Centre, Right');
  });
});
