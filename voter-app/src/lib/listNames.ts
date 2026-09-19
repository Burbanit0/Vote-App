/** Up to `shown` names, then a count — a tie at the top can span 30 methods. */
export function listNames(names: string[], shown = 3): string {
  const rest = names.length - shown;
  return names.slice(0, shown).join(', ') + (rest > 0 ? ` +${rest}` : '');
}
