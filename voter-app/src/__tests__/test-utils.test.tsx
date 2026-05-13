import React from 'react';
import { render } from '../test-utils';

describe('test-utils', () => {
  it('customRender renders with AuthProvider wrapper', () => {
    const TestChild = () => <div>hello from custom render</div>;
    render(<TestChild />);
    expect(document.body.textContent).toContain('hello from custom render');
  });
});
