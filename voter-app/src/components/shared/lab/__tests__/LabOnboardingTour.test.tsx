import React from 'react';
import { render } from '@testing-library/react';
import LabOnboardingTour, { LAB_TOUR_LS_KEY } from '../LabOnboardingTour';

// react-joyride mounts portals and is not jsdom-friendly. We mock it to a
// simple element that surfaces the props we care about.
vi.mock('react-joyride', () => ({
  __esModule: true,
  Joyride: (props: any) => (
    <div data-testid="joyride">
      <span data-testid="run">{props.run ? 'true' : 'false'}</span>
      <span data-testid="step-count">{props.steps?.length ?? 0}</span>
      <span data-testid="targets">{(props.steps ?? []).map((s: any) => s.target).join('|')}</span>
    </div>
  ),
  STATUS: { FINISHED: 'finished', SKIPPED: 'skipped' },
}));

describe('LabOnboardingTour', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('exports the LS key used to persist completion', () => {
    expect(LAB_TOUR_LS_KEY).toBe('lab_tour_completed');
  });

  it('configures 5 steps targeting the lab data-tour anchors', () => {
    const { getByTestId } = render(<LabOnboardingTour run={false} onFinish={() => {}} />);
    expect(getByTestId('step-count')).toHaveTextContent('5');
    const targets = getByTestId('targets').textContent ?? '';
    expect(targets).toContain('[data-tour="lab-central"]');
    expect(targets).toContain('[data-tour="lab-tabs"]');
    expect(targets).toContain('[data-tour="lab-perturb-tab"]');
    expect(targets).toContain('[data-tour="lab-animation-tab"]');
    expect(targets).toContain('[data-tour="lab-focus"]');
  });

  it('passes the run prop through to Joyride', () => {
    const { getByTestId, rerender } = render(<LabOnboardingTour run={false} onFinish={() => {}} />);
    expect(getByTestId('run')).toHaveTextContent('false');
    rerender(<LabOnboardingTour run={true} onFinish={() => {}} />);
    expect(getByTestId('run')).toHaveTextContent('true');
  });
});
