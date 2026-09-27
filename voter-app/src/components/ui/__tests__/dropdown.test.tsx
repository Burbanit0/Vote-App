import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Dropdown } from '../dropdown';

describe('Dropdown', () => {
  it('opens the menu on toggle click and closes it on an outside click', () => {
    render(
      <Dropdown>
        <Dropdown.Toggle>Menu</Dropdown.Toggle>
        <Dropdown.Menu>
          <a href="/quiz">Quiz</a>
        </Dropdown.Menu>
      </Dropdown>
    );
    expect(screen.queryByText('Quiz')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Menu'));
    expect(screen.getByText('Quiz')).toBeInTheDocument();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByText('Quiz')).not.toBeInTheDocument();
  });
});
