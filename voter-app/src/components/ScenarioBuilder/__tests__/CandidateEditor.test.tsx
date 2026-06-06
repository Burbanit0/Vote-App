import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import CandidateEditor, { newCandidate, newBlankCandidate } from '../CandidateEditor';

describe('newCandidate', () => {
  it('creates a candidate with default values', () => {
    const c = newCandidate('Alice', 0);
    expect(c.name).toBe('Alice');
    expect(c.ideology).toBe(0);
    expect(c.economy).toBe(0.5);
    expect(c.isBlank).toBe(false);
  });

  it('creates left-leaning candidate', () => {
    const c = newCandidate('Bob', -0.5);
    expect(c.ideology).toBe(-0.5);
    expect(c.economy).toBeLessThan(0.5);
    expect(c.environment).toBeGreaterThan(0.5);
  });
});

describe('newBlankCandidate', () => {
  it('creates a blank candidate', () => {
    const c = newBlankCandidate();
    expect(c.name).toBe('Vote Blanc');
    expect(c.isBlank).toBe(true);
    expect(c.ideology).toBe(0);
  });
});

describe('CandidateEditor', () => {
  const defaultCandidates = [newCandidate('Alice', 0.5), newCandidate('Bob', -0.3)];

  it('renders candidate cards', () => {
    render(<CandidateEditor candidates={defaultCandidates} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue('Alice')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Bob')).toBeInTheDocument();
  });

  it('renders blank candidate card', () => {
    const withBlank = [...defaultCandidates, newBlankCandidate()];
    render(<CandidateEditor candidates={withBlank} onChange={vi.fn()} />);
    expect(screen.getByText(/Blank Vote/)).toBeInTheDocument();
  });

  it('shows add candidate button', () => {
    render(<CandidateEditor candidates={defaultCandidates} onChange={vi.fn()} />);
    expect(screen.getByText('+ Add a candidate')).toBeInTheDocument();
  });

  it('shows blank vote add button when no blank candidate', () => {
    render(<CandidateEditor candidates={defaultCandidates} onChange={vi.fn()} />);
    expect(screen.getByText(/Blank Vote/)).toBeInTheDocument();
  });

  it('does not show blank vote add button when blank candidate exists', () => {
    const withBlank = [...defaultCandidates, newBlankCandidate()];
    render(<CandidateEditor candidates={withBlank} onChange={vi.fn()} />);
    const blankButtons = screen.getAllByText(/Blank Vote/);
    expect(blankButtons.length).toBe(1);
  });

  it('calls onChange when adding a candidate', () => {
    const onChange = vi.fn();
    render(<CandidateEditor candidates={defaultCandidates} onChange={onChange} />);
    fireEvent.click(screen.getByText('+ Add a candidate'));
    expect(onChange).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ name: '' })])
    );
  });

  it('removes candidate on X click', () => {
    const onChange = vi.fn();
    render(<CandidateEditor candidates={defaultCandidates} onChange={onChange} />);
    const removeButtons = screen.getAllByText('✕');
    fireEvent.click(removeButtons[0]);
    expect(onChange).toHaveBeenCalledWith(
      expect.not.arrayContaining([expect.objectContaining({ name: 'Alice' })])
    );
  });
});
