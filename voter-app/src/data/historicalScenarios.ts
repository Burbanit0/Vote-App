/**
 * Static data for historical election scenarios.
 * Used by HistoricalReferencePanel to show real results alongside simulated ones.
 */

export interface HistoricalScenario {
  id: string;
  name: string;
  year: number;
  country: string;
  flag: string;
  phenomenon: string;
  description: string; // 2-3 sentence pedagogical text
  real_result: {
    method: string; // constitutional voting method used
    winner: string; // actual winner
    context: string; // 1 sentence with key numbers
  };
  /** Approximate real vote shares (%) of main candidates, 1st round */
  vote_shares?: Record<string, number>;
  reference: string; // Wikipedia or official source URL
}

export const HISTORICAL_SCENARIOS: Record<string, HistoricalScenario> = {
  france2002: {
    id: 'france2002',
    name: 'France 2002 — 1er tour',
    year: 2002,
    country: 'France',
    flag: '🇫🇷',
    phenomenon: 'Paradoxe de Condorcet',
    description:
      'La gauche présente 6 candidats au 1er tour (Jospin, Chevènement, Taubira, Besancenot…), ' +
      'fragmentant le vote progressiste. Jospin, préféré par une majorité face à Le Pen ou Chirac ' +
      "en duel direct, est éliminé avec 16,18% — une démonstration emblématique de l'effet spoiler " +
      'et du paradoxe de Condorcet dans un scrutin uninominal.',
    real_result: {
      method: 'Scrutin uninominal à deux tours',
      winner: 'Chirac',
      context:
        'Chirac 19,9% · Jospin 16,2% · Le Pen 16,9% — Jospin éliminé au 1er tour, Chirac élu avec 82% au 2nd tour.',
    },
    vote_shares: {
      Chirac: 19.9,
      Jospin: 16.2,
      'Le Pen': 16.9,
      Bayrou: 6.8,
      Chevènement: 5.3,
      Mégret: 2.3,
      Taubira: 2.3,
      Besancenot: 4.3,
    },
    reference:
      'https://fr.wikipedia.org/wiki/%C3%89lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2002',
  },

  usa1992: {
    id: 'usa1992',
    name: 'USA 1992 — Élection présidentielle',
    year: 1992,
    country: 'États-Unis',
    flag: '🇺🇸',
    phenomenon: 'Effet spoiler',
    description:
      'Ross Perot se présente comme indépendant et capture 19,7% du vote populaire, ' +
      "un score historique pour un tiers candidat. Les analystes estiment qu'il a " +
      'siphonné des voix modérées des deux camps, mais plus significativement du camp républicain, ' +
      "permettant à Clinton de l'emporter avec seulement 43% — illustrant parfaitement " +
      'comment la pluralité peut élire un candidat rejeté par la majorité.',
    real_result: {
      method: 'Collège électoral (système "winner-take-all" par État)',
      winner: 'Clinton',
      context: 'Clinton 43,0% · Bush 37,5% · Perot 18,9% du vote populaire.',
    },
    vote_shares: {
      Clinton: 43.0,
      Bush: 37.5,
      Perot: 19.0,
    },
    reference: 'https://en.wikipedia.org/wiki/1992_United_States_presidential_election',
  },

  germany2021: {
    id: 'germany2021',
    name: 'Allemagne 2021 — Élection fédérale',
    year: 2021,
    country: 'Allemagne',
    flag: '🇩🇪',
    phenomenon: 'Fragmentation & coalition',
    description:
      "Six partis entrent au Bundestag, aucun ne dépasse 30% — un cas d'école de " +
      'fragmentation qui nécessite une coalition. Dans ce contexte, les méthodes ' +
      'consensuelles comme Borda ou Schulze avantagent les candidats capables de former ' +
      'des majorités, plutôt que les partis extrêmes qui obtiennent des scores élevés ' +
      'à la pluralité mais sont inacceptables pour une coalition.',
    real_result: {
      method: 'Scrutin proportionnel mixte (vote de liste + candidats directs)',
      winner: 'Scholz (SPD)',
      context: 'SPD 25,7% · CDU/CSU 24,1% · Verts 14,8% · FDP 11,5% · AfD 10,3% · Gauche 4,9%.',
    },
    vote_shares: {
      'Scholz (SPD)': 25.7,
      'Laschet (CDU)': 24.1,
      'Baerbock (Verts)': 14.8,
      'Lindner (FDP)': 11.5,
      'Weidel (AfD)': 10.3,
      'Bartsch (Gauche)': 4.9,
    },
    reference: 'https://en.wikipedia.org/wiki/2021_German_federal_election',
  },

  condorcet_cycle: {
    id: 'condorcet_cycle',
    name: 'Cycle de Condorcet — Cas théorique',
    year: 1785,
    country: 'Théorie du vote',
    flag: '📐',
    phenomenon: "Cycle d'Arrow (intransitivité)",
    description:
      "Le marquis de Condorcet a démontré en 1785 qu'avec des préférences cycliques " +
      '(A bat B, B bat C, C bat A en duels directs), aucune méthode de vote ne peut ' +
      'produire un résultat transitif. Ce cas synthétique illustre pourquoi les méthodes ' +
      'comme Schulze, Minimax ou Kemeny-Young produisent des résultats différents : ' +
      'elles "cassent" le cycle selon des critères différents.',
    real_result: {
      method: 'Démonstration théorique (Condorcet, 1785)',
      winner: '—',
      context:
        "Aucun vainqueur de Condorcet n'existe. Le résultat dépend entièrement de la méthode choisie.",
    },
    reference: 'https://fr.wikipedia.org/wiki/Paradoxe_de_Condorcet',
  },

  consensus: {
    id: 'consensus',
    name: 'Élection consensuelle — Cas théorique',
    year: 0,
    country: 'Théorie du vote',
    flag: '✅',
    phenomenon: 'Consensus parfait (Condorcet)',
    description:
      'Configuration idéale où un candidat du centre bat tous les autres en duel direct ' +
      "— il est le vainqueur de Condorcet. Toutes les méthodes consensuelles s'accordent " +
      'sur ce résultat. C\'est la référence "parfaite" qui permet de comprendre, par contraste, ' +
      'pourquoi les configurations fragmentées ou polarisées produisent des divergences.',
    real_result: {
      method: 'Toutes les méthodes consensuelles',
      winner: 'Centre',
      context:
        'Le candidat du centre est élu par toutes les méthodes (pluralité, Borda, IRV, Schulze, approbation).',
    },
    reference: 'https://fr.wikipedia.org/wiki/M%C3%A9thode_de_Condorcet',
  },
};

/** Ordered list for UI display */
export const HISTORICAL_SCENARIO_IDS = [
  'france2002',
  'usa1992',
  'germany2021',
  'condorcet_cycle',
  'consensus',
] as const;
