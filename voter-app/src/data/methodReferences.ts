/**
 * methodReferences.ts — Academic references for voting methods.
 *
 * Each key matches a METHOD_KEY in simulationConstants.ts.
 * Used to generate BibTeX bibliographies in LaTeX exports.
 */

export interface MethodReference {
  bibtexKey: string;
  entryType: 'article' | 'book' | 'misc' | 'inproceedings';
  author: string;
  year: number;
  title: string;
  journal?: string;
  publisher?: string;
  volume?: string;
  pages?: string;
  note?: string;
  doi?: string;
}

const references: Record<string, MethodReference> = {
  plurality: {
    bibtexKey: 'plurality_fptp',
    entryType: 'book',
    author: 'Duverger, Maurice',
    year: 1954,
    title: 'Political Parties: Their Organization and Activity in the Modern State',
    publisher: 'Wiley',
    note: 'Introduces Duverger\'s law on the relationship between plurality voting and two-party systems.',
  },

  two_round: {
    bibtexKey: 'tworound_blais2004',
    entryType: 'article',
    author: 'Blais, André and Loewen, Peter John',
    year: 2009,
    title: 'The French electoral system and its effects',
    journal: 'West European Politics',
    volume: '32(2)',
    pages: '345--359',
    doi: '10.1080/01402380802670495',
  },

  borda: {
    bibtexKey: 'borda1781',
    entryType: 'misc',
    author: 'Borda, Jean-Charles de',
    year: 1781,
    title: 'M\\\'emoire sur les \\\'elections au scrutin',
    journal: 'Histoire de l\'Acad\\\'emie Royale des Sciences',
    note: 'First formal analysis of ranked voting with positional scoring.',
  },

  approval: {
    bibtexKey: 'brams_fishburn1983',
    entryType: 'book',
    author: 'Brams, Steven J. and Fishburn, Peter C.',
    year: 1983,
    title: 'Approval Voting',
    publisher: 'Birkh{\\"{a}}user',
    note: 'Seminal work formalising approval voting.',
  },

  irv: {
    bibtexKey: 'tideman1987',
    entryType: 'article',
    author: 'Tideman, T. Nicolaus',
    year: 1987,
    title: 'Independence of clones as a criterion for voting rules',
    journal: 'Social Choice and Welfare',
    volume: '4(3)',
    pages: '185--206',
    doi: '10.1007/BF00433944',
  },

  coombs: {
    bibtexKey: 'coombs1964',
    entryType: 'book',
    author: 'Coombs, Clyde H.',
    year: 1964,
    title: 'A Theory of Data',
    publisher: 'Wiley',
    note: 'Introduces the Coombs elimination rule (remove most last-ranked candidate).',
  },

  bucklin: {
    bibtexKey: 'hoag_hallett1926',
    entryType: 'book',
    author: 'Hoag, Clarence G. and Hallett, George H.',
    year: 1926,
    title: 'Proportional Representation',
    publisher: 'Macmillan',
    note: 'Historical description of the Bucklin voting method used in US Progressive Era.',
  },

  minimax: {
    bibtexKey: 'young_levenglick1978',
    entryType: 'article',
    author: 'Young, H. P. and Levenglick, A.',
    year: 1978,
    title: 'A consistent extension of Condorcet\'s election principle',
    journal: 'SIAM Journal on Applied Mathematics',
    volume: '35(2)',
    pages: '285--300',
    doi: '10.1137/0135023',
  },

  schulze: {
    bibtexKey: 'schulze2011',
    entryType: 'article',
    author: 'Schulze, Markus',
    year: 2011,
    title: 'A new monotonic, clone-independent, reversal symmetric, and Condorcet-consistent single-winner election method',
    journal: 'Social Choice and Welfare',
    volume: '36(2)',
    pages: '267--303',
    doi: '10.1007/s00355-010-0475-4',
  },

  kemeny_young: {
    bibtexKey: 'kemeny1959',
    entryType: 'article',
    author: 'Kemeny, John G.',
    year: 1959,
    title: 'Mathematics without numbers',
    journal: 'Daedalus',
    volume: '88(4)',
    pages: '577--591',
    note: 'See also Young (1988) for axiomatic characterisation.',
  },

  condorcet: {
    bibtexKey: 'condorcet1785',
    entryType: 'misc',
    author: 'Condorcet, Marie Jean Antoine Nicolas Caritat de',
    year: 1785,
    title: 'Essai sur l\'application de l\'analyse {\\`{a}} la probabilit\\\'e des d\\\'ecisions rendues {\\`{a}} la pluralit\\\'e des voix',
    publisher: 'Imprimerie Royale',
    note: 'Introduces the pairwise majority rule and the Condorcet paradox.',
  },

  positional_score: {
    bibtexKey: 'saari1995',
    entryType: 'book',
    author: 'Saari, Donald G.',
    year: 1995,
    title: 'Basic Geometry of Voting',
    publisher: 'Springer',
    doi: '10.1007/978-3-642-57748-2',
  },

  simple_score: {
    bibtexKey: 'smith2000',
    entryType: 'misc',
    author: 'Smith, Warren D.',
    year: 2000,
    title: 'Range voting',
    note: 'Available at: rangevoting.org. Formal analysis of score (range) voting.',
  },

  star_voting: {
    bibtexKey: 'equal_vote2014',
    entryType: 'misc',
    author: '{Equal Vote Coalition}',
    year: 2014,
    title: '{STAR Voting}: Score Then Automatic Runoff',
    note: 'Proposal by the Equal Vote Coalition combining score expressivity with a runoff.',
  },

  median_voting: {
    bibtexKey: 'balinski_laraki2010',
    entryType: 'book',
    author: 'Balinski, Michel and Laraki, Rida',
    year: 2010,
    title: 'Majority Judgment: Measuring, Ranking, and Electing',
    publisher: 'MIT Press',
    doi: '10.7551/mitpress/9780262015134.001.0001',
  },

  mean_median_hybrid: {
    bibtexKey: 'merrill1999',
    entryType: 'article',
    author: 'Merrill, Samuel and Grofman, Bernard',
    year: 1999,
    title: 'A Unified Theory of Voting: Directional and Proximity Spatial Models',
    publisher: 'Cambridge University Press',
    note: 'Theoretical basis for hybrid scoring approaches.',
  },

  variance_based: {
    bibtexKey: 'laslier2006',
    entryType: 'article',
    author: 'Laslier, Jean-Fran{\\c{c}}ois',
    year: 2006,
    title: 'Spatial approval voting',
    journal: 'Political Analysis',
    volume: '14(2)',
    pages: '160--185',
    doi: '10.1093/pan/mpj004',
  },

  quadratic: {
    bibtexKey: 'posner_weyl2018',
    entryType: 'book',
    author: 'Posner, Eric A. and Weyl, E. Glen',
    year: 2018,
    title: 'Radical Markets: Uprooting Capitalism and Democracy for a Just Society',
    publisher: 'Princeton University Press',
    note: 'Popularised Quadratic Voting (QV) as a mechanism for expressing preference intensity.',
  },

  // ── General references used in the full report ───────────────────────────
  arrow1951: {
    bibtexKey: 'arrow1951',
    entryType: 'book',
    author: 'Arrow, Kenneth J.',
    year: 1951,
    title: 'Social Choice and Individual Values',
    publisher: 'Wiley',
    note: 'Proves the impossibility theorem: no ranked voting rule satisfies all fairness criteria simultaneously.',
  },

  gibbard1973: {
    bibtexKey: 'gibbard1973',
    entryType: 'article',
    author: 'Gibbard, Allan',
    year: 1973,
    title: 'Manipulation of voting schemes: a general result',
    journal: 'Econometrica',
    volume: '41(4)',
    pages: '587--601',
    doi: '10.2307/1914083',
  },
};

export default references;

/**
 * Render a MethodReference as a BibTeX entry string.
 */
export function toBibtex(ref: MethodReference): string {
  const fields: string[] = [];
  const add = (k: string, v?: string) => { if (v) fields.push(`  ${k} = {${v}}`); };

  add('author',    ref.author);
  add('year',      String(ref.year));
  add('title',     ref.title);
  add('journal',   ref.journal);
  add('publisher', ref.publisher);
  add('volume',    ref.volume);
  add('pages',     ref.pages);
  add('note',      ref.note);
  add('doi',       ref.doi);

  return `@${ref.entryType}{${ref.bibtexKey},\n${fields.join(',\n')}\n}`;
}
