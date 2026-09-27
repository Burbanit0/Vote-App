# PLAN — Méthodes, histoires (dont vote blanc) & Atlas 3D

Plan d'exécution auto-suffisant. **Une branche `feat/*` + une PR par étape**,
contre `develop`, merge `--no-ff`. Écrit pour être exécuté étape par étape (par
moi ou un autre agent) sans contexte préalable. Fichier **local, hors repo**
(gitignoré, comme les autres plans).

## Mission

Quatre chantiers, demandés par l'utilisateur :

1. **Couvrir le plus de méthodes possibles** — que le maximum de règles soient
   jouables/comparables, pas seulement « expliquées ».
2. **Ajouter des histoires** — plus de phénomènes narrés dans l'instrument.
3. **Le vote blanc dans les histoires + simulable dans le playground** — pas un
   îlot séparé : un vrai levier de l'électorat, narré et manipulable en direct.
4. **Un Atlas 3D des régimes démocratiques** — globe monde qui tourne, coloré par
   méthode et par usage du vote blanc ; sert aussi de **démo d'animation**.

## Règles du jeu (CLAUDE.md fait foi)

- Une branche `feat/*` par étape **depuis `develop`**, une PR, merge `--no-ff`.
- Portes : `npx tsc --noEmit` · `npx vitest run` · `npm run lint` (0 erreur) ·
  `npx prettier --config .prettierrc --write <files>` · `npm run build`.
- i18n : `playground.fr.ts` source de vérité ET type ; `.en.ts` miroir
  clé-pour-clé (tsc l'impose). **Les tests tournent en anglais** — asserter EN.
- **Parité moteur** : toute règle a DEUX implémentations (client
  `playgroundVoting.ts` + backend `simulation_ranked_utils.py` /
  `simulation_score_utils.py`), verrouillées par `playgroundVoting.parity.test.ts`
  via `engineParity.json` (artefact **généré**, jamais édité à la main —
  régénérer par `python fast_api_voter/scripts/gen_engine_parity.py`).
- **Pas de nouvelle dépendance** : `d3` (donc `d3-geo`) est déjà là ; réutiliser.
- Logique = **lib pure + test unitaire + composant mince**.
- Auteur des commits = forme `noreply` ; `Co-Authored-By: Claude Opus 4.8`.

## À réutiliser (grep avant de construire)

| Besoin | Existe déjà |
|---|---|
| Registre méthodes (info + analogie) | `lib/methodInfo.ts` (`METHOD_INFO`, `METHOD_ANALOGY`, 29 entrées) |
| Listes de règles | `lib/scorecard.ts` (`LEADER_RULES` 17 = sélecteur/scorecard ; `EXTRA_RULES` 12 = galerie seule) |
| Moteur client | `lib/playgroundVoting.ts` (`ruleWinner`, `ruleWinnerFromRanks`) |
| Histoires (données + deep-link) | `lib/stories.ts` (`Story`/`StoryStep`, patch d'état) + `StoryPlayer.tsx` + `stories.test.ts` |
| Vote blanc — électorat | `useElectionStore` : `config.blank_vote { enabled, rule, contagion }` **déjà présent** ; scénarios `france2002` (symbolic) etc. le posent |
| Vote blanc — logique/verdict | `lib/blankVote.ts` (pur, 4 régimes) + `data/blankVoteRegimes.ts` (16 pays, **avec lat/lon**) |
| Vote blanc — divergence (back) | `BlankVoteDivergencePanel` + endpoint `/api/v2/.../divergence` (consomme `config.blank_vote`) |
| Famille Lab dédiée | `blank` (« Vote blanc & abstention ») déjà dans le rail |
| d3 / dataviz | `d3` (Heatmap, BarChart, MethodSimilarityGraph) → `d3-geo` dispo pour le globe |
| Orphelins à réanimer | `BlankVoteTimeSeries.tsx` (courbe historique), régimes lat/lon |

---

## Chantier A — Couverture des méthodes

### A.1 — Audit de couverture *(branch `feat/method-coverage-audit`)*
**But** : savoir exactement où en est chaque méthode avant d'en promouvoir/ajouter.
**Faire** : produire un tableau (script jetable ou test-doc) croisant, par règle :
présente dans le moteur **client** ? dans le moteur **backend** ? dans
`METHOD_INFO` ? dans le **harnais de parité** ? dans `LEADER_RULES` vs
`EXTRA_RULES` ? Sortir : (a) EXTRA_RULES sûres à promouvoir (parité OK), (b)
méthodes notables **absentes** (candidates : BTR-IRV / Condorcet-Hare, Tideman
Alternative, Smith//Score, Copeland variantes, Bucklin-ER, approval-runoff…).
**Fini quand** : liste priorisée écrite (dans ce plan, section « suivi »).

### A.2 — Promouvoir les EXTRA_RULES sûres *(branch `feat/promote-extra-rules`)*
**But** : rendre comparables (sélecteur + scorecard + tableau) les méthodes déjà
dans le moteur mais reléguées à la galerie.
**Faire** : déplacer les règles parité-sûres de `EXTRA_RULES` vers `LEADER_RULES` ;
vérifier scorecard/axes ; **régénérer `engineParity.json`** ; parité verte.
Ajouter analogie « Au quotidien » si honnête.
**Tests** : `playgroundVoting.parity.test.ts` vert ; galerie/gallery test à jour.
**Fini quand** : les méthodes promues apparaissent partout, parité verte.

### A.3 — Ajouter les méthodes manquantes *(une branche `feat/method-<nom>` PAR méthode)*
**But** : combler les trous du panthéon.
**Faire**, par méthode : règle **client** (`playgroundVoting.ts`) + règle
**backend** (`simulation_*_utils.py`) + entrée `METHOD_INFO` (fr+en) + analogie si
honnête + inscription liste + **régénérer parité**. Une méthode = une PR
(parité-gated : une divergence est un bug jusqu'à preuve du contraire).
**Fini quand** : chaque nouvelle méthode jouable, expliquée, en parité.

---

## Chantier B — Nouvelles histoires *(branch `feat/stories-batch`, découpable)*

**But** : narrer plus de phénomènes dans l'instrument, entrée par curiosité.
**Faire** : ajouter des `Story` (données pures) pour des phénomènes sous-narrés —
p. ex. **non-monotonie / no-show paradox**, **later-no-harm**, **indépendance aux
clones**, **majorité vs Condorcet**, **participation/abstention**, **reversal
symmetry**, **favorite betrayal**. Chaque histoire : positions choisies pour que
le beat tienne + `stories.<id>.*` (fr+en) + assertions dans `stories.test.ts` (le
test verrouille chaque résultat porteur). Se branche seule sur la grille
d'accueil (auto depuis `STORIES`) ; ajouter aux questions de curiosité si pertinent.
**Fini quand** : N histoires nouvelles, chaque beat verrouillé, portes vertes.

---

## Chantier C — Vote blanc dans le playground & les histoires *(le plus profond)*

Le socle existe (`config.blank_vote`, `lib/blankVote.ts`, endpoint divergence) mais
le vote blanc n'est PAS un levier vivant de l'instrument. Objectif : qu'on puisse
**ajouter des blancs à l'électorat** et voir l'issue changer à travers les 5 moments,
et qu'une **histoire** le narre.

### C.1 — Surfacer `config.blank_vote` dans le playground *(branch `feat/blank-in-electorate`)*
**Faire** : un contrôle dans le moment **Électorat** (activer + part de blancs +
règle symbolic/competitive/threshold) qui lit/écrit le champ **déjà présent** du
store. Pas de nouveau state.
**Tests** : le contrôle bascule le champ, persiste dans le patch d'état. EN.

### C.2 — Le moteur live reflète les blancs *(branch `feat/blank-engine-live`)*
**Faire** : brancher la logique de `lib/blankVote.ts` (régimes) sur le **résultat
réel** de l'électorat, pour que le vainqueur / la majorité / l'éventuel
« on recommence » apparaissent dans les dérivations des moments (pas seulement la
fiche `thy-blank`). Parité backend pour le traitement du blanc.
**Piège** : sémantique par règle — pour beaucoup de méthodes le blanc réduit juste
les exprimés ; pour les règles à seuil/majorité il change le dénominateur ; le
compétitif/seuil peut déclencher un re-scrutin. Documenter, tester par famille.
**Tests** : parité verte ; une assertion par régime sur l'électorat live. EN.
**Fini quand** : bouger la part de blancs change visiblement l'issue dans l'instrument.

### C.3 — Histoires « vote blanc » *(branch `feat/blank-stories`)*
**Faire** : 1–2 histoires qui font monter le blanc au fil des beats (« le blanc qui
annule » en régime seuil/compétitif), réutilisant les scénarios qui posent déjà
`blank_vote`. Données pures + i18n + `stories.test.ts`.
**Fini quand** : au moins une histoire narre le basculement, beats verrouillés.

### C.4 *(option)* — `thy-blank` sur l'électorat réel
Toggle « sur mon électorat » qui remplace les curseurs A/B/C de la fiche par les
parts réelles calculées sur l'électorat courant.

---

## Chantier D — Atlas 3D des régimes démocratiques *(branch `feat/atlas-globe`)*

**But** : un globe monde qui tourne, chaque pays coloré par sa méthode et son usage
du vote blanc ; **démo d'animation** en prime. Zéro nouvelle dépendance (d3-geo).

### D.1 — Données `lib/electoralAtlas.ts`
Étendre l'esprit de `blankVoteRegimes.ts` (qui a déjà lat/lon) → un enregistrement
par démocratie : `{ country, flag, lat, lon, method: <enum de Rule/‘two_round’/
‘stv’/‘mmp’/‘fptp’…>, blankStatus: BlankVoteStatus, note, source }`. Couvrir les
cas emblématiques : Australie (IRV), Irlande (STV), Allemagne (MMP), France (2
tours), USA (FPTP), Uruguay (blanc compétitif), Colombie (blanc seuil)… Labels de
méthode/statut par **enum + i18n** (le miroir EN reste propre), notes tolérées FR.
**Tests** : intégrité (chaque `method`/`blankStatus` est une valeur connue ;
lat/lon dans les bornes ; deux locales pour les labels).

### D.2 — Composant globe `components/lab/RegimeGlobe.tsx`
`d3-geo` `geoOrthographic` : sphère + graticule + un point par régime à sa lat/lon,
coloré par méthode (toggle : par statut de blanc). **Auto-rotation**
(`requestAnimationFrame`), **drag pour tourner**, `prefers-reduced-motion` →
statique. Clic sur un point → carte pays (méthode + usage du blanc + source).
SVG ou canvas, **aucun polygone pays requis** pour le MVP (points sur globe).
**Tests** : rend N points, le toggle change la coloration, clic ouvre la carte. EN.

### D.3 — Emplacement
Une fiche dans la famille **« Vote blanc & abstention »** (ou une fiche « Atlas »
en Systèmes). Sert de démo d'animation (le globe qui tourne). Entrée catalogue +
i18n + bump du test d'intégrité `labCatalog`.

### D.4 *(option, plus lourd)* — Pays pleins
Formes de pays coloriées via un TopoJSON world-atlas **embarqué comme asset
statique** (fichier de données, pas une dépendance runtime). Plus riche, à décider.

**Fini quand** : globe qui tourne, reduced-motion respecté, points colorés +
cliquables, données sourcées, portes vertes.

---

## Ordre conseillé

- **B** (histoires) et **D.1** (données atlas) sont peu risqués et parallélisables
  tout de suite (données pures, zéro moteur).
- **D.2/D.3** (globe) ensuite — autonome, effet « waouh » + démo animation.
- **A** (méthodes) est **parité-lourd** (backend + regen) → par petits pas.
- **C** (vote blanc live) est le **plus profond** (moteur + parité + UI + histoires)
  → en dernier, ou en parallèle de A puisque les deux touchent le moteur.

Définition de « fini » commune : portes vertes, FR+EN synchro, tests en EN, zéro
dépendance nouvelle, parité intacte-ou-régénérée, PR contre `develop`.

## Suivi (à remplir au fil de l'eau)

- Chantier A — audit : fait à la volée en A.2 (PR #100) plutôt qu'en étape séparée —
  Kemeny-Young était le seul EXTRA_RULES avec un jumeau backend déjà testé
  (`get_kemeny_young_winner`, exact ≤6 candidats) jamais branché au harnais de
  parité. Les 11 autres EXTRA_RULES (anti_plurality, dowdall, black, smith_irv,
  split_cycle, cumulative, maximin, benham, river, nash, raynaud) n'ont PAS de
  jumeau backend — leur promotion relèverait d'A.3 (ajouter la méthode manquante
  au backend), pas d'A.2. Note : Copeland existe côté backend
  (`get_copeland_winner`) mais n'est même pas dans EXTRA_RULES côté client — vérifier
  s'il correspond à l'alias `condorcet`→`copeland` déjà utilisé (methodInfo.ts) avant
  d'y toucher.
- Chantier A — promues : **kemeny** (PR #100, mergé 2026-07-29) — EXTRA_RULES → LEADER_RULES,
  parité 0 écart/60 scénarios, reclassé famille Condorcet (pas « Autres »), citation
  de dureté de manipulation réelle (Bartholdi–Tovey–Trick 1989), analogie ajoutée.
  Au passage : corrigé un texte METHOD_INFO obsolète (le playground bascule sur
  Borda au-delà de 8 candidats, pas KwikSort — ça c'est le backend).
- Chantier A — ajoutées : **black** (PR #103, mergé 2026-07-29) — première VRAIE
  méthode ajoutée des deux côtés (pas une promotion). `get_black_winner(votes) =
  get_condorcet_winner(votes) or get_borda_winner(votes)` — une ligne, composée
  de deux primitives backend déjà testées. Enregistrée dans `compare_all_methods`
  (`simulation_metrics.py`) → visible aussi dans ResultsMethodTable/
  BlankVoteDivergencePanel, pas seulement le harnais de parité. **Piège trouvé
  par la suite pytest COMPLÈTE** (pas juste le nouveau fichier de test) :
  `profile_engine.py`'s `_ORDINAL_METHODS` (liste blanche de compatibilité
  bulletin) ignorait "black" → `profile-simulate` le signalait "incompatible"
  même sur bulletin complet. Corrigé. Parité 0 écart/60 scénarios → promue
  EXTRA_RULES → LEADER_RULES (16 méthodes verrouillées désormais : 14 ordinales
  + score + STAR). Restent 10 EXTRA_RULES sans jumeau backend (anti_plurality,
  dowdall, smith_irv, split_cycle, cumulative, maximin, benham, river, nash,
  raynaud) — candidates pour de futures PRs A.3, une par PR, `black` sert de
  modèle pour repérer si une méthode client peut se composer d'utils backend
  déjà existants (near-zero-risk) avant d'écrire un VRAI nouvel algorithme.
- Chantier A — ajoutée : **anti_plurality/véto** (PR #104, mergé 2026-07-29) —
  méthode positionnelle simple (`get_anti_plurality_winner` : tally des dernières
  places, élit le moins souvent véto). Piège corrigé DÈS L'ÉCRITURE (pas après
  coup comme `black`) : un `Counter` naïf qui ignore les candidats jamais classés
  derniers aurait exclu le vrai gagnant (0 véto) du `min()` — corrigé en gardant
  la liste ordonnée des candidats rencontrés (même patron que Schulze) et en
  lisant `Counter.get(c, 0)`. Suite pytest COMPLÈTE lancée AVANT commit (leçon
  de `black` appliquée) : 385/385 verts du premier coup, `_ORDINAL_METHODS` mis à
  jour en même temps que le registre `compare_all_methods`. Promue EXTRA_RULES →
  LEADER_RULES, famille « majoritaire », vraie citation (stratégie de
  l'enterrement, même style que le « compromis » de la pluralité), analogie
  ajoutée. Au passage : nettoyé le commentaire « Tier B, pas de jumeau backend »
  resté périmé sur `black`/`kemeny` dans le type `Rule` et le switch de
  `playgroundVoting.ts` depuis leurs promotions respectives (PR #100/#103) —
  toujours vérifier ce commentaire à chaque promotion. Vérifié au navigateur :
  20/20 méthodes actives ; un faux « Mono. ✗ » suspecté sur la matrice de
  critères s'est avéré une erreur de lecture visuelle du tableau (colonne
  adjacente « Rev. » en réalité, échec attendu/connu de la symétrie de réversion
  pour une règle positionnelle miroir de la pluralité) — confirmé par un scan
  de 500 électorats aléatoires que la monotonie, elle, tient toujours. Parité =
  **17 méthodes verrouillées** (15 ordinales + score + STAR). Restent 9
  EXTRA_RULES sans jumeau backend (dowdall, smith_irv, split_cycle, cumulative,
  maximin, benham, river, nash, raynaud).
- **Chantier A — TERMINÉ** (2026-07-29, PRs #105-#111, 6 branches pour les 9 méthodes
  restantes — cumulative/maximin/nash regroupées dans une seule PR car même patron
  de câblage) :
  - **dowdall** (PR #105) : positionnelle harmonique (rang k → 1/(k+1)), même
    patron trivial qu'anti_plurality. Au passage, trouvé ET corrigé un DEUXIÈME
    commentaire « Tier B, pas de jumeau backend » périmé sur le cas `kemeny` du
    switch de dispatch (oublié depuis PR #100) — le genre d'oubli qui se répète
    tant qu'on ne grep pas « Tier B » à chaque promotion.
  - **cumulative + maximin + nash** (PR #106, un seul PR car même câblage) :
    trois agrégateurs cardinaux ajoutés à `simulation_score_utils.py`
    (`get_cumulative_winner`, `get_maximin_score_winner` — nommé ainsi pour ne
    PAS entrer en collision avec le `get_minimax_winner` ordinal déjà existant,
    ce sont deux méthodes différentes malgré le nom proche —, `get_nash_winner`)
    ; branchées sur le harnais `CARDINAL` déjà existant (score/STAR) sans
    nouveau câblage. 60/60 scénarios cardinaux résolus sans ambiguïté de
    tie-break.
  - **raynaud** (PR #107) : élimination itérative de la plus grosse défaite par
    paire, réutilise `_pairwise_wins` (déjà partagé avec Copeland). Tie-break
    alphabétique explicite (patron Nanson/Baldwin/Copeland), PAS l'ordre
    d'itération d'un `set` Python (non déterministe d'un process à l'autre).
  - **benham** (PR #108, Condorcet-IRV) : à chaque tour, on filtre les bulletins
    aux candidats encore actifs et on les passe TELS QUELS à `get_condorcet_winner`
    déjà existant — aucune nouvelle logique de comparaison par paires n'était
    nécessaire. Citation de manip empruntée à l'IRV (Bartholdi–Orlin 1991)
    plutôt qu'inventée, car Benham dégénère en IRV pur dès qu'aucun vainqueur de
    Condorcet n'apparaît.
  - **river** (PR #109, Heitzig) : copie quasi telle quelle la structure de
    `get_ranked_pairs_winner` (déjà en place) + UNE règle en plus (un seul
    verrou entrant par candidat → arbre, pas DAG général). Recherche aléatoire
    (même technique que pour les histoires) pour trouver un VRAI cas de
    divergence face à Ranked Pairs plutôt que d'en dériver un à la main (risque
    d'erreur arithmétique silencieuse) — trouvé en 240 tirages sur 20000.
  - **smith_irv** (PR #110, Tideman's Alternative) : nouveau helper `_smith_set`
    (préfixe croissant trié par score de Copeland, copie exacte du `smithSet`
    client) au-dessus de `_pairwise_wins`. Un vrai bug mypy trouvé et corrigé
    au passage (`next(iter(active))` avait besoin d'un `str()` explicite que
    `min(active)` juste à côté n'exigeait pas — subtilité d'inférence de type
    sur cette forme d'appel précise, corrigée à la source).
  - **split_cycle** (PR #111, Holliday–Pacuit 2021 — LA DERNIÈRE des 10
    `EXTRA_RULES` d'origine) : matrice de marges + passe Floyd–Warshall en
    chemin-le-plus-large (même technique générale que Schulze) sur les arêtes à
    marge positive ; un candidat gagne si aucune défaite contre lui ne dépasse
    strictement le meilleur chemin retour. Recherche aléatoire a trouvé un
    profil à 4 candidats où Split Cycle diverge à la fois de Schulze ET de
    Ranked Pairs — confirme que c'est un vrai algorithme distinct.
  - **`EXTRA_RULES` est maintenant VIDE** — toutes les méthodes du playground ont
    un jumeau backend testé. Nettoyé les commentaires « Tier B » devenus
    périmés dans `scorecard.ts` et `playgroundVoting.ts` (le marqueur de
    section n'avait plus aucun membre en dessous). Le tableau `EXTRA_RULES`
    lui-même et ses 3 consommateurs UI (`MethodDuel`, `MethodGallery`,
    `MethodReplayModal`) sont restés en place tels quels — ils dégradent
    proprement vers un no-op avec un tableau vide, et retirer tout le concept
    Tier B de l'UI est un chantier de nettoyage séparé, plus gros qu'« ajouter
    une méthode de plus ».
  - **Parité finale : 29 méthodes verrouillées** (21 ordinales + score + STAR +
    cumulative + maximin + nash), régénérée à chaque PR, 0 régression.
    CLAUDE.md à jour au fil des PRs.
  - **Leçon transversale confirmée sur toute la série** : suite pytest COMPLÈTE
    avant chaque commit backend (jamais seulement le nouveau fichier de test) ;
    grep « Tier B » sur `playgroundVoting.ts`/`scorecard.ts` à chaque promotion
    (trouvé périmé 2 fois sur 7 PRs malgré la vigilance) ; recherche aléatoire
    par script jetable plutôt que dérivation à la main dès qu'un test doit
    prouver une divergence entre deux algorithmes à 4+ candidats (fiable, rapide,
    zéro risque d'erreur arithmétique).
- Chantier B — histoires : **1 histoire ajoutée** (PR #99, mergé 2026-07-28 : `clones` —
  la stratégie du clone, faille d'indépendance aux clones de Borda, Condorcet/IRV
  résistent ; positions/poids trouvés par recherche numérique, verrouillés par
  4 assertions). Autres phénomènes de la liste (non-monotonie/no-show, later-no-harm,
  participation/abstention, reversal symmetry) : non tentés — ce sont des paradoxes
  qui naissent typiquement de profils de bulletins précis plutôt que d'un modèle
  spatial continu (électeur = distance au candidat), donc probablement plus longs à
  construire ; à reprendre si besoin avec le même harnais de recherche.
- Chantier B — **2 histoires ajoutées** (PR #112, mergé 2026-07-29/30, branche unique
  car même technique et découvertes ensemble) : `monotonie` et `renversement`. Demande
  explicite de l'utilisateur : diversifier au-delà du récit déjà raconté deux fois
  (« même électorat, méthode différente, vainqueur différent » — `paradox` et `five`) ;
  ces deux histoires montrent plutôt UNE règle qui se contredit elle-même.
  - **`monotonie`** (échec de monotonie sous IRV) : un bloc d'indécis fait passer Nora
    de 2ᵉ à 1er choix (son score de premiers choix monte de 38 % à 49 %) — et pourtant
    l'ordre d'élimination change et c'est Yanis qui gagne à la place. Gagner des voix
    a coûté l'élection.
  - **`renversement`** (échec de symétrie de réversion sous la pluralité) : Malik, aimé
    d'une base fidèle mais classé dernier par tout le reste, gagne le scrutin ET
    regagne quand on retourne CHAQUE bulletin (39 % → 61 %) — la pluralité ne regarde
    que qui arrive en tête, donc elle ne distingue pas « adoré » de « détesté ailleurs ».
  - **Technique clé (nouvelle, réutilisable)** : au lieu d'un champ spatial approximatif
    (blocs gaussiens vaguement centrés), un bloc-« ancre » par **classement complet
    exact** (`permAnchor(X,Y,Z)` = point pondéré 0.75X+0.2Y+0.05Z, étalement 0.02) donne
    un contrôle EXACT du nombre de bulletins par permutation — comme un profil de
    bulletins à la main, mais réalisé spatialement pour rester compatible avec le
    format `Story` (qui ne patch que candidats/électorat, pas de bulletins bruts). Les
    comptes ont d'abord été dérivés à la main (inégalités sur les poids des 3-4 blocs),
    puis vérifiés par un script jetable AVANT d'écrire les coordonnées finales — la
    dérivation à la main a suffi ici (contrairement à river/split_cycle en Chantier A)
    car le mécanisme (qui est éliminé, vers qui son report va) est algébrique et petit
    (3 candidats, 1 seule élimination par côté).
    Pour `renversement`, l'électorat « inverse » est construit en réutilisant
    `permAnchor` avec l'ordre de CHAQUE bloc littéralement inversé (mêmes poids) —
    pas besoin d'un nouveau levier « inverser les bulletins » dans l'instrument.
  - **Corrigé au passage** : l'icône `Ban` de l'histoire `blank` (PR #102) n'était
    jamais enregistrée dans `StoryPlayer.tsx`'s `ICONS` — elle retombait
    silencieusement sur `BookOpen` depuis sa création. Ajoutée avec les 2 nouvelles
    icônes (`TrendingUp`, `Repeat`).
  - Reste de la liste d'origine non tenté : later-no-harm, participation/abstention
    (no-show — proche math de `monotonie`, donc probablement redondant à faire tel
    quel), favorite betrayal (déjà esquissé par `utile`).
- **later-no-harm ajouté** (PR #113, mergé 2026-07-30) : `soutien` (« Le soutien de
  trop »). Vote par approbation : un bloc d'électeurs garde Léa comme favorite tout
  du long (première préférence inchangée aux deux temps de l'histoire), mais se met
  à approuver sincèrement Hugo EN PLUS — jamais à la place de Léa. Résultat : le
  score d'approbation d'Hugo grimpe de 39 % à 72 % (celui de Léa reste fixe à 61 %)
  et il la dépasse. Plus dur à câbler que `monotonie`/`renversement` : la
  normalisation min-max de l'approbation (score relatif au meilleur/pire candidat
  DE CETTE COURSE, pas un seuil d'utilité absolu) ne se prête pas à une dérivation à
  la main par blocs — une hypothèse initiale (« le bloc proche de Léa n'approuve pas
  Hugo ») s'est révélée fausse dès la première vérification par script (le bloc
  approuvait déjà Hugo à 100 % à la position testée, à cause de l'étirement de
  l'échelle par le 3ᵉ candidat rejeté). Corrigé par une recherche en grille sur la
  position du bloc oscillant plutôt qu'une nouvelle tentative de calcul à la main —
  même leçon que river/split_cycle en Chantier A : ne pas insister sur l'algèbre
  quand une normalisation relative est en jeu, chercher.
- **Chantier C — C.4 FAIT** (PR #114, mergé 2026-07-30, dernier point du chantier) :
  toggle « Sur mon électorat » sur la fiche `thy-blank` (Laboratoire). Remplace les
  3 curseurs abstraits A/B/C par les VRAIES parts de premier choix des candidats
  actuellement configurés dans le Playground (`usePlaygroundCtx` → `leaderCandidates`
  + `votingVoters`), plus une part de blanc calculée avec le même mécanisme de rayon
  d'aliénation que le curseur du moment Stratégie (`applyBlankVote`, à l'intensité
  actuelle, forcé actif pour cette vue même si le vrai curseur ne l'est pas — la
  fiche part du principe que le blanc existe). Les vrais noms de candidats
  remontent aussi dans les 4 cartes de verdict (le lookup du gagnant, câblé en dur
  sur `CAND_LETTERS`, généralisé à un tableau de noms actif selon le mode). Mode
  manuel (curseurs + presets) intact, le bascule ne change que la SOURCE des
  données, pas la mécanique des 4 destins en dessous. **Chantiers A, B (3 histoires),
  C et D sont maintenant tous complets** — restent seulement les options non
  prioritaires D.4 (pays pleins TopoJSON) et d'éventuelles histoires
  supplémentaires si on veut continuer à diversifier B.
  **Incident de workflow corrigé en direct** : le commit C.4 a d'abord atterri par
  erreur directement sur `develop` (pas de `git checkout -b` après le merge de la
  PR précédente) — repéré avant tout push, corrigé par `git branch <nom> && git
  reset --hard origin/develop` puis `git checkout <nom>` pour déplacer le commit
  sur une vraie branche `feat/*` sans jamais toucher `develop` à distance. Toujours
  vérifier `git branch --show-current` avant de committer, surtout juste après un
  merge.
- Chantier C — **C.1+C.2 FAITS ensemble** (PR #101, mergé 2026-07-29) : `playground.blank
  {enabled,intensity,lens}` (state client, calqué sur `turnout`, ne touche PAS
  `config.blank_vote`/le backend) + `applyBlankVote()` (même rayon d'aliénation que
  `applyTurnout`) + `blankVerdict()` étendu avec `knownWinner` (sinon il élit le
  leader en 1ère préférence, faux dès qu'IRV/Condorcet/Borda élit un autre gagnant)
  → contrôle vivant dans le moment Stratégie, vérifié en navigateur (bascule Carol
  élue ↔ le blanc gagne, mêmes électeurs, juste le régime change). Portée
  délibérément limitée : `leaderScorecard`/`manipulationProbe`/`shake` NE lisent PAS
  l'électorat post-blanc (seul le vainqueur affiché + le nouveau panneau verdict le
  font) — fil à tirer si besoin, pas un oubli. **C.3 FAIT** (PR #102, mergé
  2026-07-29) : histoire `blank` (« Le vote blanc, quatre destins ») — Camille
  gagne 67 %/33 % parmi ceux qui choisissent quelqu'un ; électorat composé (bloc
  proche + gros bloc « rejette tout le monde ») ; SEUL le régime change entre les
  beats (intensité fixe 70 %) : loi actuelle → élue quand même (96 % des rares
  exprimés) ; comptée dans les exprimés → plus de majorité ; régime compétitif
  (Uruguay) → le blanc gagne, on rouvre. Positions trouvées par recherche
  numérique (même méthode que `clones`) ; `stories.test.ts` a un nouvel harnais
  `blankVerdictAt()` qui rejoue exactement la dérivation de PlaygroundController.
  Vérifié en navigateur via `/playground?story=blank`, les 4 scènes rendent
  identiques au script. C.4 (option, thy-blank sur l'électorat réel) : non fait.
- Chantier D — **D.1/D.2/D.3 FAITS** (PR #97, mergé 2026-07-28 : `lib/electoralAtlas.ts`
  + `RegimeGlobe.tsx` + fiche `sys-atlas` en Systèmes, 26 pays, globe d3-geo qui
  tourne, toggle méthode/blanc). D.4 (pays pleins TopoJSON) : non fait, optionnel.
