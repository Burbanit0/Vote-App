# EXP-005 — Lot 8 perf gates : invariant Profiler du form-lock + budget de bundle

- **Date** : 2026-09-11 · **Statut** : adopté (les deux) · **Coût réel** : ~4h (dont ~2h30 d'expérimentation Profiler avant de trouver une assertion non-fragile, ~1h30 outillage + vérification du budget de bundle)
- **Verdict en une phrase** : un plafond en millisecondes absolues sur le premier rendu React est un piège de CI documenté par ce projet mais jamais vécu côté frontend avant aujourd'hui (×4,5 de bruit JIT à froid/chaud sur le MÊME code) — un compte de commits (déterministe) + une comparaison relative de coût (×5-12 mesurée) le remplacent avec de vraies dents, vérifiées contre 3 régressions injectées ; côté bundle, `size-limit` (actif, ~6 semaines) gate 1 MB brotli sur une baseline réelle de 810,88 kB (~23 % de marge), câblé dans `npm run build` sans toucher la CI.

## Hypothèse de départ

Le [Lot 8 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#lot-8--performance) porte
deux items indépendants mais nés de la même question : une convention **déjà
écrite** (le form-lock documenté dans le skill `voter-ui`, un budget de
bundle jamais chiffré) peut-elle être rendue **exécutable**, dans l'esprit du
Lot 2 de ce même plan (« combien de mes conventions documentées étaient déjà
violées sans que je le sache ? ») ?

- **Form-lock** : `PlaygroundPage.test.tsx` vérifie déjà que rien de lourd
  n'est monté au premier rendu — mais uniquement la *forme* (des testids
  absents). React expose une vraie API de mesure (`<Profiler onRender>`) :
  peut-elle donner une assertion de *performance* qui tienne réellement, sans
  tomber dans le piège classique du seuil en millisecondes absolu (déjà vécu
  côté CI backend, Lot 3) ?
- **Budget de bundle** : `vite.config.ts` a déjà un `manualChunks` et Vite
  avertit déjà (sans jamais échouer) quand un chunk dépasse 500 kB. Quel est
  le vrai poids aujourd'hui, et quel seuil serait à la fois mordant et non
  disruptif ?

## Protocole

### Form-lock — trois hypothèses testées contre le vrai environnement (Vitest + jsdom)

Toutes les mesures ci-dessous viennent de `<Profiler id="playground"
onRender>` enveloppant `<PlaygroundPage>` sous `MemoryRouter`, avec les mêmes
mocks (`assemblyApi`, `profileApi`) que `PlaygroundPage.test.tsx`. Fichier de
travail jetable, jamais committé (`PlaygroundPage.perfExperiment.test.tsx`,
supprimé une fois le protocole final fixé).

1. **Plafond en millisecondes absolues** — 8 rendus indépendants
   (`unmount()` entre chaque) du même code inchangé :

   | Run | 1 (froid) | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
   |---|---|---|---|---|---|---|---|---|
   | `actualDuration` du 1er commit (ms) | 58,10 | 23,25 | 21,63 | 16,30 | 14,39 | 13,42 | 13,50 | 12,46 |

   Facteur ×4,5 entre le run à froid et les runs stabilisés, **sur du code
   strictement identique**. N'importe quel seuil absolu assez serré pour
   attraper une vraie régression modeste se serait déclenché au run 1 pour de
   mauvaises raisons.

2. **Comptage de commits** — mêmes 8 runs : **exactement 2 commits à chaque
   fois**, y compris au run 1 malgré la durée gonflée. Stable indépendamment
   du bruit temporel — bon candidat.

3. **Régression injectée n°1 (structurelle)** : `ElectorateMoment.tsx` modifié
   temporairement pour monter `<ElectorateComposer />` deux fois (une fois
   sans son `Collapsible`, en plus de la version gardée) — simule un panneau
   qui échapperait au gating. Résultat : toujours **2 commits** (une
   inclusion structurelle dans l'arbre ne change pas le nombre de commits,
   elle alourdit juste celui qui existe déjà), et la fenêtre de durée
   (13,5-20,7 ms) **chevauche entièrement** la fenêtre baseline
   (12,4-23,2 ms) — indétectable par un seuil de durée à cette échelle.
   Revert confirmé, retour à la baseline.

4. **Régression injectée n°2 (calcul invisible dans un effet)** : une boucle
   de 20 millions d'itérations (`Math.sqrt`) glissée dans un `useEffect` de
   montage, avec un `setState` factice à la fin. Résultat, contre-intuitif
   mais net : **toujours 2 commits**, et la durée `actualDuration` du 2ᵉ
   commit **ne bouge pas** (le temps mur du test, lui, augmente nettement —
   confirmant que le calcul a bien coûté du CPU réel, juste pas mesuré par le
   Profiler). Conclusion vérifiée en relisant le comportement documenté de
   React : `<Profiler onRender>` chronomètre la phase de rendu/commit, jamais
   le corps d'un effet passif. Limite réelle, pas un bug de la mesure.

5. **Régression injectée n°3 (chaîne d'effets eager non gardée)** : deux
   `useEffect` chaînés au montage (`setStage(1)` puis, dépendant de `stage`,
   `setStage(2)`) — simule un futur contributeur qui ajouterait un
   chargement en plusieurs étapes non lié à une interaction. Résultat :
   **3 commits** au lieu de 2, détecté immédiatement. Revert confirmé, retour
   à 2.

6. **Comparaison relative** — 6 rendus indépendants, chacun mesurant (a) le
   coût d'ouvrir un `Collapsible` trivial (`module-electorate-toggle`, un
   formulaire, aucun calcul) et (b) le coût, sur un rendu séparé, de
   sélectionner la lentille de probabilité (`lens-probability`, un vrai
   calcul client attendu via `waitFor` comme le fait déjà
   `PlaygroundPage.test.tsx`) :

   | Run | 1 | 2 | 3 | 4 | 5 | 6 |
   |---|---|---|---|---|---|---|
   | coût "cheap" (ms) | 3,14 | 1,09 | 0,98 | 0,80 | 0,87 | 0,72 |
   | coût "heavy" (ms) | 16,82 | 12,76 | 8,06 | 8,84 | 8,04 | 7,52 |
   | ratio | ×5,36 | ×11,68 | ×8,19 | ×11,04 | ×9,20 | ×10,42 |

   Signal net et stable : ×5,4 à ×11,7 sur 6 mesures indépendantes, aucun
   chevauchement avec 1.

### Test final retenu

`voter-app/src/pages/__tests__/PlaygroundPage.perf.test.tsx` — deux
assertions :

1. `commits.length <= 2` au premier rendu (documenté : 2 aujourd'hui, mount +
   le passage `loading: true` du hook de diagnostics live).
2. `heavyCost > cheapCost * 3` (seuil ×3, sous la pire valeur observée ×5,36 —
   marge délibérée) + `heavyCommits.length > cheapCommits.length` (signal de
   comptage, indépendant du minutage).

Rejoué 5 fois d'affilée après finalisation : 5/5 vert, aucune variance de
résultat (seule la durée mesurée varie, jamais le verdict pass/fail).

### Budget de bundle — mesure puis choix d'outil

`npm run build` réel (pas de nombre inventé) : 121 chunks JS, 3 004 492 octets
bruts, 938 786 octets gzip (`gzip -c … | wc -c`), 68 622 octets CSS bruts.
Deux chunks dépassent déjà le `chunkSizeWarningLimit` par défaut de Vite
(500 kB) : `recharts` (590 kB) et le chunk vendor principal `index` (580 kB) —
attendus, pas du code applicatif ballonné.

Outils candidats vérifiés (date de dernière publication, `npm view <pkg>
time.modified`) avant d'installer quoi que ce soit — même réflexe que le rejet
de Lost Pixel (EXP-004) et le remplacement `license-checker` (Lot 6.7) :

| Outil | Dernière publication | Verdict |
|---|---|---|
| `bundlesize` | 2024-03-15 (**>2 ans**) | Rejeté — abandonné |
| `vite-plugin-bundlesize` | 2025-08-29 (~1 an) | Rejeté — mainteneur seul, signal modeste |
| `rollup-plugin-visualizer` | 2026-08-14 (~4 sem.) | Rejeté — visualisation, pas de gate à seuil |
| `vite-bundle-analyzer` | 2026-07-13 (~6 sem.) | Rejeté — idem |
| `size-limit` + `@size-limit/file` | 2026-07-30 (~6 sem.) | **Adopté** |

`size-limit` (Andrey Sitnik, mainteneur connu de l'écosystème
PostCSS/Autoprefixer) mesure par glob sur des fichiers déjà construits —
indépendant du bundler, donc utilisable directement sur `build/` sans
plugin Vite.

## Ce que ça a trouvé

**Form-lock** : le Profiler React ne voit **que** la phase de rendu — un
calcul lourd dans un effet est un angle mort total, quel que soit son coût
CPU réel (prouvé par l'injection n°2). Ce que le compte de commits détecte
réellement n'est donc pas « du travail lourd » en général, mais une classe
précise : une chaîne d'effets qui se déclenchent sans interaction utilisateur
(injection n°3). La comparaison relative de coût, elle, prouve autre chose
d'utile : que le fait de garder le calcul réel (lentille de probabilité)
derrière une interaction explicite a un effet mesurable et large (×5-12), pas
seulement une bonne intention documentée.

**Budget de bundle** : un vrai piège de version, trouvé en installant plutôt
qu'en lisant la doc. `npm install -D size-limit @size-limit/file` sans
épingler résout `size-limit@12.1.0`, alors que la dernière version publiée du
plugin (`@size-limit/file@13.0.3`) déclare une peer-dependency **exacte** sur
`size-limit@13.0.3` — `npm ls` confirme l'arbre invalide (`ELSPROBLEMS`)
après coup. Cause : `size-limit@13.0.3` a relevé son exigence Node à
`^22.18.0 || ^24.0.0 || >=26.0.0`, abandonnant le Node 20 sur lequel ce dépôt
tourne encore — exactement la même contrainte que celle déjà documentée pour
`dependency-cruiser` au Lot 2 (« 18.x exige Node ≥22 »). `size-limit@12.1.0`
(publication précédente) déclare encore `^20.0.0 || ^22.0.0 || >=24.0.0` et
reste compatible. Résolu en épinglant la paire exacte `size-limit@12.1.0` +
`@size-limit/file@12.1.0` (peer-dependency exacte re-vérifiée), pas la
dernière publiée.

## Ce que ça a coûté

**Form-lock** (~2h30) : la majeure partie du temps est allée dans les
expérimentations 1-6 ci-dessus — trois hypothèses fausses ou incomplètes
avant la bonne combinaison, chacune vérifiée avec de vrais chiffres plutôt
qu'écartée par intuition. Zéro nouvelle dépendance (React Profiler est natif).

**Budget de bundle** (~1h30) : ~30 min de recherche/vérification de mainteneurs
avant d'installer ; ~30 min à diagnostiquer le conflit de peer-dependency
Node 20 et trouver la paire de versions compatible ; ~30 min à câbler et
vérifier (build réel, régression injectée, revert). Deux nouvelles
dépendances de dev, épinglées en version exacte (`size-limit`,
`@size-limit/file`, 12.1.0 chacune) — aucune dépendance de production
ajoutée.

## Verdict et pourquoi

**Les deux adoptés, tels quels, aucun rejet cette fois.**

- Form-lock : `PlaygroundPage.perf.test.tsx` gate désormais deux invariants
  réels (compte de commits, coût relatif), tous deux vérifiés contre des
  régressions injectées puis retirées. Le test de forme existant
  (`PlaygroundPage.test.tsx`) reste nécessaire et complémentaire — ni l'un ni
  l'autre ne couvre tout seul ce que l'invariant de perf est censé garantir.
- Budget de bundle : `size-limit` câblé dans `npm run build` lui-même (le
  build échoue si le budget est dépassé, comme demandé par l'item), sans
  toucher `frontend-ci-cd-pipeline.yml` — ce workflow appelle déjà
  `npm run build`.

## Ce que j'en retiens (transférable à un autre projet)

1. **Un seuil de perf en millisecondes absolues dans un test unitaire est un
   piège même sans y avoir jamais été confronté sur ce sous-système précis** —
   le facteur ×4,5 entre un run froid et un run chaud, sur du code strictement
   identique, n'a rien à voir avec la machine CI : c'est un artefact du
   JIT/du chargement de modules dans le worker de test lui-même. Mesurer
   plusieurs runs consécutifs AVANT de choisir un style d'assertion, jamais
   après, est ce qui a rendu ce piège visible avant qu'il ne morde en CI.
2. **Le Profiler de React ne mesure que le rendu, jamais un effet** — une
   limite non documentée de façon évidente, trouvée seulement en injectant un
   calcul délibérément coûteux dans un effet et en constatant qu'il
   n'apparaît nulle part dans `actualDuration`. Toute assertion de perf basée
   sur le Profiler doit donc cibler du travail qui a lieu PENDANT le rendu
   (mount d'un composant lourd, calcul dans le corps d'un composant), pas du
   travail différé dans un effet.
3. **Une peer-dependency exacte (`"size-limit": "13.0.3"`, sans caret) peut
   se retrouver silencieusement non satisfaite par un simple `npm install`** —
   npm n'a pas fait échouer l'installation, juste résolu une version plus
   ancienne compatible avec d'autres contraintes du projet, laissant un arbre
   objectivement invalide (`npm ls` le révèle, `npm install` seul ne le dit
   pas). `npm ls <pkg>` après toute installation d'un outil avec plugins
   séparés est un réflexe de vérification à bas coût, pas une paranoïa
   excessive.
4. **Un pipeline shell qui se termine par `| tail` (ou tout autre filtre)
   masque le code de sortie de la commande qu'on voulait vérifier** — `$?`
   après un pipe donne le code de sortie du DERNIER élément du pipe, pas de la
   commande qu'on croit tester. Découvert en croyant, à tort, qu'une
   régression injectée n'avait pas fait échouer le gate — elle avait, le
   pipeline mentait. Toujours vérifier `$?` immédiatement après la commande
   dont on veut le code de sortie, sans rien derrière.
