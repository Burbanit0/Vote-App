import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import WinnerExplanation from '../WinnerExplanation';
import type { NamedPt, Rule } from '../../../lib/playgroundVoting';
import type { VoteTrace } from '../../../lib/voteTrace';

// Tests run in English (jsdom) → assert EN copy, and confirm the explain.* keys
// resolve (a missing key would render the raw key string).

const CANDS: NamedPt[] = [
  { name: 'Alice', x: 0, y: 0 },
  { name: 'Bruno', x: 1, y: 0 },
];

const countTrace: VoteTrace = {
  family: 'count',
  rule: 'plurality' as Rule,
  frames: [{ caption: { key: 'x' }, bars: [16, 15] }],
  winner: 0,
  unitKey: 'votes',
  sampleSize: 31,
};

describe('WinnerExplanation', () => {
  it('renders a plain why-sentence naming the winner and mechanism', () => {
    render(<WinnerExplanation trace={countTrace} candidates={CANDS} />);
    const el = screen.getByTestId('winner-explanation');
    expect(el).toHaveTextContent('Why this winner?');
    expect(el).toHaveTextContent('Alice wins on the highest total: 16 to Bruno’s 15.');
  });
});
