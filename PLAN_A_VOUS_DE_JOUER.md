# Plan — « À vous de jouer »

Page où l'utilisateur devient un électeur réel : il exprime **un** avis, le traduit dans
**cinq langages de bulletin**, et découvre que le langage décide de ce que sa voix a le
droit de dire — et de ce qu'il obtient.

## La thèse de la page

> Votre avis ne change pas. Votre bulletin, si.

Trois choses à faire comprendre, dans cet ordre :

1. **On peut s'exprimer de plusieurs manières** — un nom, un ordre, plusieurs noms, des
   notes, des points à répartir.
2. **Le langage ferme des portes** — un bulletin uninominal ne peut pas produire un
   vainqueur de Condorcet : l'information n'existe pas. Choisir un bulletin, c'est
   choisir ce que la méthode a le droit de savoir.
3. **Certains bulletins forcent une tactique** — pour l'approbation, la note et les
   points, « sincère » est **sous-déterminé** (où couper ? quelle échelle ? tout sur un
   ou réparti ?). L'électeur fait un choix stratégique avant même d'avoir voté. C'est le
   pont naturel vers la tranche 2.

## Décisions actées

- **Métrique centrale = le gain personnel**, exprimé en rang : « vous obtenez votre 2ᵉ
  choix ». Sans elle la page reste un tableau de bord.
- **Pas de numérotation 01/02/03** pour les langages : c'est une *taxonomie*, pas une
  séquence (même raisonnement que le rail de familles du Laboratoire). En revanche les
  chiffres 1‑2‑3 sont légitimes *à l'intérieur* du bulletin ordonné — là, le rang est le
  contenu.
- **L'indétermination n'est pas cachée** : approbation / note / points exposent leur
  curseur, et l'utilisateur constate qu'il vient de trancher.
- **Abstention, pas vote blanc**, en v1 : l'abstention est le bulletin retiré du
  décompte — entièrement côté client. Le vote blanc (qui agit sur la légitimité, et peut
  *gagner* sous la règle compétitive) est un volet ultérieur, et n'existe aujourd'hui que
  côté backend.

## Direction visuelle

L'identité existante s'applique telle quelle — pétrole `#0e7068`, terracotta `#e07a3f`
(l'encre et le tampon « Élu »), crème `#f6f7f4`, Space Grotesk / Inter / IBM Plex Mono,
et le vocabulaire d'instrument (repères d'angle, bandeau mono).

**Signature : le bulletin est un objet de papier qui se reforme.** L'avis reste affiché,
fixe ; c'est le *papier* qui change de nature quand on change de langage, et les marques
s'y posent à l'encre terracotta — la même encre que le tampon « Élu » et que les bâtons
du dépouillement. Le papier est une peau : dessous, ce sont de vrais contrôles
(clavier, focus visible, `prefers-reduced-motion` respecté).

**Second geste : les portes qui se ferment.** Le rail des méthodes s'allume ou s'éteint
selon le langage choisi. On *voit* Condorcet, Borda et l'IRV s'éteindre quand on prend un
bulletin uninominal.

Glyphes des langages (chacun encode la marque réellement portée sur le papier) : une
croix unique · 1‑2‑3 empilés · plusieurs coches · une échelle à 5 crans · des jetons.

```
┌──────────────────────────────────────────────────────────┐
│ VOTE LAB · À VOUS DE JOUER                               │
│ Votre avis ne change pas. Votre bulletin, si.            │
├────────────────┬─────────────────────────────────────────┤
│ VOTRE AVIS     │  ┌───────────────────────┐              │
│ (fixe)         │  │  le papier, qui morphe │             │
│ Carol › Alice  │  │  marques à l'encre     │             │
│ › Bob          │  └───────────────────────┘              │
│                │  [ ✗ ] [1‑2‑3] [ ✓✓ ] [1–5] [ ●●● ]     │
├────────────────┴─────────────────────────────────────────┤
│ CE QUE CE BULLETIN AUTORISE   (chips allumées / éteintes)│
├──────────────────────────────────────────────────────────┤
│ RÉSULTAT   élu : X        VOUS OBTENEZ : votre 2ᵉ choix  │
└──────────────────────────────────────────────────────────┘
```

## Modèle technique

**Ce qui existe déjà et se réutilise**

- Le vocabulaire `BallotType` dans le store (`choose_one`, `rank_full`, `approve`,
  `score`, `grade`, `cumulative`).
- **Toutes** les règles de décompte côté client, cumulatif compris (`winCumulative`).
- `ruleWinnerFromRanks(ranks, m, rule, scores?)` — l'entrée de dispatch.
- Les primitives de stratégie : `strategicVote`, `sincerityProbe`, `manipulationField`.

**Ce qui manque — le seul primitif neuf**

Personne ne *traduit* un avis en bulletin. Nouveau `src/lib/ballotLanguages.ts` :

```ts
export type BallotLanguage = 'one' | 'rank' | 'approve' | 'score' | 'points';

/** Un avis (utilités par candidat) → un bulletin dans le langage demandé. */
ballotFrom(utils: number[], lang: BallotLanguage, opts): { rank: number[]; score?: number[] }

/** Les règles qu'un langage rend calculables. */
RULES_FOR: Record<BallotLanguage, Rule[]>
```

Règle d'or : **un bulletin plus riche en subsume un plus pauvre.** Un ordre complet
autorise tout l'ordinal ; un seul nom n'autorise presque rien.

| Langage | Marque | Règles autorisées |
|---|---|---|
| `one` | une croix | pluralité (+ deux tours, au prix d'un second déplacement) |
| `rank` | 1‑2‑3 | tout l'ordinal : pluralité, deux tours, IRV, Coombs, Borda, Bucklin, Nanson, Baldwin, Condorcet, minimax, Schulze, paires ordonnées |
| `approve` | coches | approbation (+ pluralité si une seule coche) |
| `score` | 1–5 | note, STAR, jugement majoritaire, approbation par seuil |
| `points` | jetons | vote cumulatif |

**Les autres électeurs votent dans le même langage.** Leurs utilités viennent du modèle
spatial ; on les traduit avec la même fonction, en réglage sincère par défaut. L'utilisateur
est un bulletin de plus. C'est ce qui rend la comparaison honnête.

**Indétermination exposée** : `approve` prend un seuil k ; `score` une échelle
(fidèle ↔ contrastée) ; `points` une répartition (concentrée ↔ étalée). Chacun est un
curseur visible.

## Découpage

- **Tranche 1 — les langages.** Un avis → les 5 bulletins ; pour chacun : les méthodes
  autorisées, le vainqueur, **votre rang obtenu**. Porte l'objectif 1 et la moitié du 2.
- **Tranche 2 — sincère / stratégique / abstention**, sous le langage choisi.
- **Tranche 3 — le poids.** Marge réelle, « combien de gens comme vous », manette
  serré ↔ large. Ancrage sur des marges véritables (Floride 2000 : 537 voix sur ~6 M).
  Et le fait rigoureux qui casse la croyance du 1/n : la pivotalité décroît en **1/√n**
  (Penrose), pas en 1/n — pour n = 10⁶, c'est mille fois plus.

## Portes de qualité

`npx tsc --noEmit` · `npm run lint` (0 erreur) · `npx vitest run` · prettier.
Test dédié : le bulletin traduit doit élire, sous chaque règle, **le même vainqueur** que
le moteur alimenté directement — le langage ne doit jamais introduire d'écart parasite.
Les tests tournent en anglais (jsdom) : asserter les chaînes EN.
