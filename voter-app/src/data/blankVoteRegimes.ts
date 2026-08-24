/**
 * blankVoteRegimes.ts — International blank-vote legal frameworks.
 *
 * Data sourced from electoral legislation, official statistics, and
 * academic literature on comparative election law (May 2026).
 *
 * legal_status taxonomy:
 *   counted_separate — officially counted & published separately (no effect on result)
 *   symbolic         — counted but only political/moral weight, no legal mechanism
 *   competitive      — blank can win like a regular candidate
 *   threshold        — if blank exceeds a threshold, special procedure is triggered
 *   merged_invalid   — not distinguished from spoiled/invalid ballots
 */

export type BlankVoteStatus =
  | 'counted_separate'
  | 'symbolic'
  | 'competitive'
  | 'threshold'
  | 'merged_invalid';

export interface BlankVoteRegime {
  country: string;
  flag: string; // emoji drapeau
  legal_status: BlankVoteStatus;
  description: string; // explication en français
  blank_rate_typical: number; // % moyen aux dernières élections
  impact_on_result: boolean; // le vote blanc peut-il invalider/modifier une élection ?
  since_year?: number;
  source: string;
  lat: number; // latitude approximative (pour la carte SVG)
  lon: number; // longitude approximative
}

const regimes: BlankVoteRegime[] = [
  {
    country: 'France',
    flag: '🇫🇷',
    legal_status: 'counted_separate',
    description:
      'Depuis la loi du 21 février 2014, les bulletins blancs sont comptés séparément ' +
      'des bulletins nuls et apparaissent dans les résultats officiels. Ils ne sont pas ' +
      "comptabilisés dans les suffrages exprimés et n'affectent pas la majorité requise.",
    blank_rate_typical: 2.6,
    impact_on_result: false,
    since_year: 2014,
    source: "Loi n°2014-172 du 21/02/2014 — Ministère de l'Intérieur",
    lat: 46,
    lon: 2,
  },
  {
    country: 'Belgique',
    flag: '🇧🇪',
    legal_status: 'symbolic',
    description:
      'Le vote est obligatoire en Belgique. Les bulletins blancs sont comptés mais ne ' +
      'modifient pas le résultat — le vote blanc est une protestation légale reconnue. ' +
      "L'abstention forcée pousse certains électeurs à voter blanc plutôt que nul.",
    blank_rate_typical: 5.1,
    impact_on_result: false,
    source: 'Code électoral belge — SPF Intérieur',
    lat: 50.5,
    lon: 4.5,
  },
  {
    country: 'Suisse',
    flag: '🇨🇭',
    legal_status: 'symbolic',
    description:
      'Les bulletins blancs ("bulletins blancs") sont comptés séparément dans les ' +
      'statistiques officielles. Ils ont une valeur de signal politique sans effet ' +
      "constitutionnel direct sur le résultat de l'élection.",
    blank_rate_typical: 1.8,
    impact_on_result: false,
    source: 'Loi fédérale sur les droits politiques — Chancellerie fédérale suisse',
    lat: 47,
    lon: 8,
  },
  {
    country: 'Portugal',
    flag: '🇵🇹',
    legal_status: 'symbolic',
    description:
      'Les "votos em branco" sont officiellement comptés et publiés dans les résultats. ' +
      "Ils sont soustraits du total pour calculer la majorité requise, mais n'ont " +
      'aucun effet procédural spécifique.',
    blank_rate_typical: 2.3,
    impact_on_result: false,
    source: 'Código Eleitoral Português — Comissão Nacional de Eleições',
    lat: 39.5,
    lon: -8,
  },
  {
    country: 'Espagne',
    flag: '🇪🇸',
    legal_status: 'counted_separate',
    description:
      'Les "votos en blanco" sont officiellement comptabilisés et publiés. Ils entrent ' +
      'dans le dénominateur pour le calcul du seuil de 3% nécessaire pour participer ' +
      'à la répartition des sièges — le vote blanc peut donc priver un petit parti de sièges.',
    blank_rate_typical: 0.7,
    impact_on_result: false,
    source: 'Ley Orgánica del Régimen Electoral General (LOREG) — Junta Electoral Central',
    lat: 40,
    lon: -4,
  },
  {
    country: 'Suède',
    flag: '🇸🇪',
    legal_status: 'symbolic',
    description:
      'Les bulletins blancs ("blankröster") sont comptés séparément des bulletins nuls. ' +
      "Ils n'influencent pas le résultat mais sont publiés comme indicateur de " +
      "mécontentement ou d'indécision.",
    blank_rate_typical: 0.4,
    impact_on_result: false,
    source: 'Vallagen (2005:837) — Valmyndigheten',
    lat: 60,
    lon: 15,
  },
  {
    country: 'Pays-Bas',
    flag: '🇳🇱',
    legal_status: 'symbolic',
    description:
      'Les "blanco stemmen" sont comptés officiellement. Aux Pays-Bas le vote blanc ' +
      "est parfois utilisé lors de référendums comme protestation. Il n'affecte pas " +
      'la répartition des sièges à la proportionnelle.',
    blank_rate_typical: 0.6,
    impact_on_result: false,
    source: 'Kieswet — Kiesraad (Conseil électoral néerlandais)',
    lat: 52.4,
    lon: 5.3,
  },
  {
    country: 'Allemagne',
    flag: '🇩🇪',
    legal_status: 'merged_invalid',
    description:
      'Les bulletins blancs ("leere Stimmzettel") sont inclus dans les "Ungültige Stimmen" ' +
      '(suffrages invalides) et ne sont pas distingués dans les statistiques officielles. ' +
      "Ils n'ont aucun effet sur les résultats.",
    blank_rate_typical: 0.8,
    impact_on_result: false,
    source: 'Bundeswahlgesetz — Bundeswahlleiter',
    lat: 51,
    lon: 10,
  },
  {
    country: 'Italie',
    flag: '🇮🇹',
    legal_status: 'counted_separate',
    description:
      'Les "schede bianche" (bulletins blancs) sont comptées séparément des bulletins ' +
      'nuls ("schede nulle"). Elles sont publiées dans les résultats officiels mais ' +
      "n'influencent pas la majorité requise.",
    blank_rate_typical: 0.9,
    impact_on_result: false,
    source: "Testo Unico Leggi Elettorali — Ministero dell'Interno",
    lat: 42,
    lon: 12,
  },
  {
    country: 'Australie',
    flag: '🇦🇺',
    legal_status: 'merged_invalid',
    description:
      'L\'Australie compte les "informal votes" (comprenant bulletins blancs, mal remplis ' +
      "ou délibérément gâtés). Le vote est obligatoire. Le taux élevé d'informels reflète " +
      'une protestation délibérée. Ils ne sont pas séparés des autres invalides.',
    blank_rate_typical: 5.2,
    impact_on_result: false,
    source: 'Commonwealth Electoral Act 1918 — Australian Electoral Commission',
    lat: -25,
    lon: 133,
  },
  {
    country: 'Brésil',
    flag: '🇧🇷',
    legal_status: 'symbolic',
    description:
      'Le "voto em branco" est officiellement comptabilisé séparément. Le vote est ' +
      'obligatoire. Les bulletins blancs ne sont pas considérés comme des suffrages ' +
      "exprimés et n'affectent pas la majorité absolue requise pour être élu au 1er tour.",
    blank_rate_typical: 3.1,
    impact_on_result: false,
    source: 'Código Eleitoral Brasileiro — Tribunal Superior Eleitoral',
    lat: -10,
    lon: -55,
  },
  {
    country: 'Uruguay',
    flag: '🇺🇾',
    legal_status: 'competitive',
    description:
      'Si le vote blanc obtient plus de voix que tout autre candidat, de nouvelles ' +
      'candidatures sont ouvertes et une nouvelle élection est organisée. Le vote blanc ' +
      "agit comme un candidat à part entière — c'est l'un des régimes les plus avancés au monde.",
    blank_rate_typical: 1.4,
    impact_on_result: true,
    source: 'Constitución de Uruguay 1966, Art. 77 — Corte Electoral',
    lat: -33,
    lon: -56,
  },
  {
    country: 'Colombie',
    flag: '🇨🇴',
    legal_status: 'threshold',
    description:
      "Si le vote blanc dépasse 50% des votes valides, l'élection est annulée et de " +
      'nouvelles élections sont organisées avec de nouveaux candidats. Ce mécanisme a ' +
      'été utilisé en 2013 dans la commune de Bello, Antioquia.',
    blank_rate_typical: 6.8,
    impact_on_result: true,
    since_year: 1994,
    source: 'Ley 134 de 1994, Art. 26 — Registraduría Nacional del Estado Civil',
    lat: 4,
    lon: -72,
  },
  {
    country: 'Chili',
    flag: '🇨🇱',
    legal_status: 'symbolic',
    description:
      'Depuis la réforme de 2012, le vote est volontaire. Les bulletins blancs sont ' +
      "comptés séparément des nuls. Ils n'influencent pas la majorité requise et " +
      "servent d'indicateur de protestation électorale.",
    blank_rate_typical: 3.4,
    impact_on_result: false,
    since_year: 2012,
    source: 'Ley Orgánica Constitucional sobre Votaciones Populares — SERVEL',
    lat: -30,
    lon: -71,
  },
  {
    country: 'Pérou',
    flag: '🇵🇪',
    legal_status: 'merged_invalid',
    description:
      'Les bulletins blancs et nuls sont parfois agrégés dans les statistiques. Le vote ' +
      'est obligatoire. Un taux élevé de voix blanches/nulles est souvent interprété ' +
      "comme un rejet de l'offre politique sans valeur constitutionnelle.",
    blank_rate_typical: 4.1,
    impact_on_result: false,
    source: 'Ley Orgánica de Elecciones N°26859 — Jurado Nacional de Elecciones',
    lat: -10,
    lon: -76,
  },
];

export default regimes;
