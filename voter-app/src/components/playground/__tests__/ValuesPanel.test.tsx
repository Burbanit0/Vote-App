import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import ValuesPanel from '../ValuesPanel';
import Scorecard from '../Scorecard';
import type { LensItem } from '../../../lib/scorecard';

const mk = (id: string, a: number, b: number): LensItem => ({
  id,
  axes: {
    ax1: { mean: a, lo: Math.max(0, a - 0.05), hi: Math.min(1, a + 0.05) },
    ax2: { mean: b, lo: Math.max(0, b - 0.05), hi: Math.min(1, b + 0.05) },
  },
});

const ITEMS = [mk('alpha', 0.9, 0.2), mk('beta', 0.2, 0.9), mk('gamma', 0.1, 0.1)];
const KEYS = ['ax1', 'ax2'];
const AXIS_LABELS = { ax1: 'Axe 1', ax2: 'Axe 2' };
const ITEM_LABELS = { alpha: 'Alpha', beta: 'Beta', gamma: 'Gamma' };

function setup(weights = { ax1: 0.5, ax2: 0.5 }) {
  const onWeightChange = vi.fn();
  const utils = render(
    <ValuesPanel
      items={ITEMS}
      axisKeys={KEYS}
      axisLabels={AXIS_LABELS}
      itemLabels={ITEM_LABELS}
      weights={weights}
      onWeightChange={onWeightChange}
    />
  );
  return { onWeightChange, ...utils };
}

describe('ValuesPanel', () => {
  it('visibly removes dominated options and never ranks', () => {
    setup();
    expect(screen.getByTestId('lens-item-gamma')).toHaveTextContent('écarté (dominé)');
    // No rank numbers anywhere.
    expect(screen.getByTestId('values-panel').textContent).not.toMatch(/#\d|1er|N°/);
  });

  it('weights move the spotlight along the frontier (not onto dominated items)', () => {
    const { rerender, onWeightChange } = setup({ ax1: 1, ax2: 0 });
    expect(screen.getByTestId('lens-item-alpha')).toHaveTextContent('selon vos pondérations');
    expect(screen.getByTestId('lens-item-beta')).toHaveTextContent('sur la frontière');

    rerender(
      <ValuesPanel
        items={ITEMS}
        axisKeys={KEYS}
        axisLabels={AXIS_LABELS}
        itemLabels={ITEM_LABELS}
        weights={{ ax1: 0, ax2: 1 }}
        onWeightChange={onWeightChange}
      />
    );
    expect(screen.getByTestId('lens-item-beta')).toHaveTextContent('selon vos pondérations');
    expect(screen.getByTestId('lens-item-gamma')).toHaveTextContent('écarté (dominé)');
  });

  it('slider changes call back with the axis key', () => {
    const { onWeightChange } = setup();
    fireEvent.change(screen.getByTestId('weight-ax1'), { target: { value: '0.9' } });
    expect(onWeightChange).toHaveBeenCalledWith('ax1', 0.9);
  });
});

describe('Scorecard', () => {
  it('renders every axis with its banded value', () => {
    render(
      <Scorecard
        axes={[
          { key: 'a', label: 'Axe A', hint: 'convention A', band: { mean: 0.7, lo: 0.6, hi: 0.8 } },
          { key: 'b', label: 'Axe B', hint: 'convention B', band: null },
        ]}
        bandNote="20 ré-échantillonnages"
      />
    );
    expect(screen.getByTestId('axis-a')).toHaveTextContent('70 %');
    expect(screen.getByTestId('axis-b')).toHaveTextContent('…');
    expect(screen.getByTestId('scorecard')).toHaveTextContent('p10–p90');
  });
});
