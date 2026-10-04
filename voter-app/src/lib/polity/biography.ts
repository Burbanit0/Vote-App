/**
 * lib/polity/biography.ts — a citizen's story, compacted for reading, pure.
 *
 * Over a long run most of a citizen's record repeats: thirty censuses as the same
 * elector of the same party, a dozen chamber debates on the same motive. Each repeat
 * is told once, with every year or tick it holds for.
 */

export interface CensusYear {
  year: number;
  role: string;
  office: string;
  party?: number | null;
}

/** Consecutive census years that read the same, as one span from `year` to `to`. */
export function censusSpans<T extends CensusYear>(years: readonly T[]): (T & { to: number })[] {
  const spans: (T & { to: number })[] = [];
  for (const year of years) {
    const last = spans.at(-1);
    const same =
      last !== undefined &&
      last.to === year.year - 1 &&
      last.role === year.role &&
      last.office === year.office &&
      (last.party ?? null) === (year.party ?? null);
    if (same) last.to = year.year;
    else spans.push({ ...year, to: year.year });
  }
  return spans;
}

interface Entry {
  tick: number;
  event_type: string;
  role: string;
  motif?: number | null;
  rationale?: string | null;
}

/**
 * Entries that say the same thing (the same event, role and motive, with no rationale of
 * their own) as one, with every tick it happened at, in order of first occurrence. A
 * turn or forum post says something new each time, so it stays apart.
 */
export function groupEntries<T extends Entry>(
  entries: readonly T[]
): { entry: T; ticks: number[] }[] {
  const groups: { entry: T; ticks: number[] }[] = [];
  const byKey = new Map<string, { entry: T; ticks: number[] }>();
  for (const entry of entries) {
    const own =
      Boolean(entry.rationale) ||
      entry.event_type === 'agent_turn' ||
      entry.event_type === 'forum_post';
    const key = `${entry.event_type}|${entry.role}|${entry.motif ?? ''}`;
    const group = own ? undefined : byKey.get(key);
    if (group) {
      group.ticks.push(entry.tick);
      continue;
    }
    const fresh = { entry, ticks: [entry.tick] };
    groups.push(fresh);
    if (!own) byKey.set(key, fresh);
  }
  return groups;
}
