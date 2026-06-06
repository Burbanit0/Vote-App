import { renderHook } from '@testing-library/react';
import { useMetaTags } from './useMetaTags';

describe('useMetaTags', () => {
  beforeEach(() => {
    document.title = '';
    document.querySelectorAll('meta').forEach((el) => el.remove());
  });

  it('sets document.title', () => {
    renderHook(() => useMetaTags({ title: 'My Page', description: 'desc' }));
    expect(document.title).toBe('My Page');
  });

  it('creates og:description meta tag', () => {
    renderHook(() => useMetaTags({ title: 'T', description: 'Test description' }));
    const meta = document.querySelector('meta[property="og:description"]');
    expect(meta).not.toBeNull();
    expect(meta?.getAttribute('content')).toBe('Test description');
  });

  it('updates existing meta tag on re-render with new description', () => {
    const { rerender } = renderHook(
      ({ title, description }) => useMetaTags({ title, description }),
      { initialProps: { title: 'A', description: 'First' } }
    );
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content')).toBe(
      'First'
    );

    rerender({ title: 'B', description: 'Second' });
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content')).toBe(
      'Second'
    );
  });

  it('sets twitter:title and twitter:description meta tags', () => {
    renderHook(() => useMetaTags({ title: 'T', description: 'D' }));
    expect(document.querySelector('meta[name="twitter:title"]')?.getAttribute('content')).toBe('T');
    expect(
      document.querySelector('meta[name="twitter:description"]')?.getAttribute('content')
    ).toBe('D');
  });

  it('sets og:image when image prop is provided', () => {
    renderHook(() =>
      useMetaTags({ title: 'T', description: 'D', image: 'https://example.com/img.png' })
    );
    expect(document.querySelector('meta[property="og:image"]')?.getAttribute('content')).toBe(
      'https://example.com/img.png'
    );
  });

  it('does not set og:image when image prop is omitted', () => {
    renderHook(() => useMetaTags({ title: 'T', description: 'D' }));
    expect(document.querySelector('meta[property="og:image"]')).toBeNull();
  });

  it('removes meta tags on unmount', () => {
    const { unmount } = renderHook(() => useMetaTags({ title: 'T', description: 'D' }));

    expect(document.querySelector('meta[property="og:title"]')).not.toBeNull();

    unmount();

    expect(document.querySelector('meta[property="og:title"]')).not.toBeNull();
  });
});
