import { COLORS, LAYOUT, SPACING, partyColor } from '../tokens';

describe('design tokens', () => {
  it('exposes the brand palette', () => {
    expect(COLORS.brand.primary).toBe('#005CAB');
    expect(COLORS.brand.secondary).toBe('#C8590A');
  });

  it('exposes party colours used across the app', () => {
    expect(COLORS.party.Green).toBe('#007A33');
    expect(COLORS.party.Liberal).toBe('#005CAB');
    expect(COLORS.party.Conservative).toBe('#C8590A');
    expect(COLORS.party.Independent).toBe('#6c757d');
  });

  it('exposes Bootstrap-aligned status colours', () => {
    expect(COLORS.status.success).toBe('#198754');
    expect(COLORS.status.danger).toBe('#dc3545');
    expect(COLORS.status.warning).toBe('#ffc107');
    expect(COLORS.status.info).toBe('#0dcaf0');
  });

  it('exposes 4 ordered page widths', () => {
    expect(LAYOUT.pageNarrow).toBeLessThan(LAYOUT.pageMedium);
    expect(LAYOUT.pageMedium).toBeLessThan(LAYOUT.pageWide);
    expect(LAYOUT.pageWide).toBeLessThan(LAYOUT.pageFull);
  });

  it('exposes a multiples-of-4 spacing scale', () => {
    Object.values(SPACING).forEach((v) => expect(v % 4).toBe(0));
  });
});

describe('partyColor', () => {
  it('returns the party-specific colour when known', () => {
    expect(partyColor('Liberal')).toBe(COLORS.party.Liberal);
    expect(partyColor('Conservative')).toBe(COLORS.party.Conservative);
  });

  it('falls back to Independent grey for unknown parties', () => {
    expect(partyColor('SomeNewParty')).toBe(COLORS.party.Independent);
  });

  it('handles null/undefined safely', () => {
    expect(partyColor(null)).toBe(COLORS.party.Independent);
    expect(partyColor(undefined)).toBe(COLORS.party.Independent);
  });
});
