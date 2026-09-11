# EXP-004 — Régression visuelle : Playwright screenshots, et pourquoi l'environnement compte plus que l'outil

- **Date** : 2026-09-11 · **Statut** : adopté (gate CI, job séparé — voir réserve sur le *required check* GitHub en fin de fiche) · **Coût réel** : ~5h (recherche outillage, trois pièges de stabilité trouvés et corrigés, vérification du détecteur contre une régression injectée, une mauvaise config de tolérance trouvée et corrigée)
- **Verdict en une phrase** : le mécanisme natif de Playwright (`toHaveScreenshot`) suffit largement — Lost Pixel a été écarté sans essai pour une raison qui ne laisse pas le choix (dépôt archivé, équipe partie chez Figma) — mais le faire tenir en CI a exigé de trouver et corriger trois pièges réels (un flash d'UI intermittent au montage, un faux négatif de tolérance qui laissait passer une régression visible, une carte qui rend un état d'erreur permanent sans le backend), pas seulement de brancher l'API.

## Hypothèse de départ

Le [Lot 7 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#lot-7--surfaces-perçues-par-lutilisateur)
pose un vrai angle mort : l'app est presque entièrement visuelle (cartes SVG
`LeaderCanvas`/`ParliamentCanvas`, Recharts, ~50+ panneaux pédagogiques) et
aucun signal existant (tests unitaires, audit a11y, e2e fonctionnel) ne
regarde un pixel — une carte qui s'affiche de travers, avec des couleurs
fausses ou des éléments superposés, passerait toute la suite actuelle sans
broncher.

Deux candidats nommés par le plan : le mécanisme natif de Playwright
(`toHaveScreenshot`/`toMatchSnapshot`, zéro dépendance externe) contre Lost
Pixel (un outil dédié, potentiellement plus d'infrastructure). Hypothèse
testée : lequel résout vraiment le problème, et le vrai risque connu de ce
genre de test — des baselines qui rendent différemment d'un environnement à
l'autre, ou d'une capture en pleine animation — peut-il être réellement
maîtrisé plutôt que contourné en réduisant la précision du test ?

## Protocole

### Choix de l'outil — pas d'essai nécessaire

Avant d'installer quoi que ce soit, vérification de la santé du projet Lost
Pixel (même réflexe que `license-checker-rseidelsohn` au Lot 6.7 : jamais
adopter un outil sans vérifier sa maintenance). Résultat, trouvé en une
recherche : **Lost Pixel a annoncé le 22 avril 2026 que l'équipe rejoignait
Figma et arrêtait le produit** — dépôt GitHub archivé (lecture seule) le jour
même, aucune date d'arrêt de la plateforme cloud ni plan de maintenance de la
partie open-source publiés depuis. Un outil mort à l'adoption est un
non-choix, indépendamment de ses mérites techniques — décision prise sans
avoir besoin d'un seul test. Playwright natif retenu par défaut : zéro
dépendance nouvelle, déjà utilisé par toute la suite e2e existante, et les
docs documentent explicitement le problème de stabilité cross-environnement
qui est le vrai sujet de cette expérience.

### Périmètre choisi

Les 5 surfaces de `src/routes.ts` (`SURFACES`) au chargement initial, plus
deux captures ciblées sur ce que l'item nomme explicitement (« cartes ») : le
`LeaderCanvas` (mode Dirigeant) et le `ParliamentCanvas` (mode Assemblée) —
les deux types de carte que le toggle Dirigeant/Assemblée fait basculer.
Nouveau fichier `tests/e2e/visual.spec.ts`, réutilisant `SURFACES`/`ANCHORS`
de `tests/e2e/routes.ts` (même table que `accessibility.spec.ts`, aucune
liste dupliquée). Volontairement **pas** les ~50+ composants visuels ni les
62 fiches du Laboratoire — hors budget de l'effort `M` annoncé par le plan.

### Le problème de stabilité cross-environnement

Nouveau fichier `playwright.visual.config.ts`, séparé de
`playwright.config.ts` (`testIgnore` réciproque) : un test de pixels n'a de
sens que si la baseline et la comparaison rendent avec des polices/anti-
aliasing/rasterization identiques au bit près — chose que « la CI tourne
aussi sur Ubuntu » ne garantit pas (l'image `ubuntu-latest` de GitHub Actions
elle-même change avec le temps, sans rapport avec le code testé). Solution :
générer les baselines et les comparer en CI **uniquement** dans l'image
Docker officielle Playwright, épinglée à la version exacte de
`@playwright/test` du projet (`mcr.microsoft.com/playwright:v1.62.1-noble`,
vérifiée disponible et testée en local avant d'y engager quoi que ce soit).
`scripts/test-visual-docker.sh` reproduit exactement ce que fait le nouveau
job CI (`visual-regression` dans `e2e.yml`) ; le tag d'image est dérivé du
`package.json` (pas recopié à la main) pour qu'un bump de version ne puisse
pas silencieusement désynchroniser les deux.

### Le timing des animations

Deux mécanismes combinés, aucun code d'app modifié pour ça :
`toHaveScreenshot`'s comportement par défaut (`animations: 'disabled'`) gèle
déjà les animations/transitions CSS avant la capture (vérifié dans la doc
Playwright, pas supposé) ; `reducedMotion: 'reduce'` (option de contexte)
déclenche le chemin `prefers-reduced-motion` que plusieurs composants
respectent déjà nativement (`DiscoverVoteAnimation`, `CampaignTimeline`,
`LeaderScene3D`, `RegimeGlobe` — grep fait avant d'écrire le test, pas
supposé). Un troisième cas, trouvé seulement en testant en vrai (section
suivante), a demandé un correctif dédié dans le test lui-même.

### Vérifier le détecteur contre une régression injectée

Même discipline que le détecteur de flaky tests ailleurs dans ce plan :
faire échouer le test avant de lui faire confiance. Couleur d'un marqueur de
candidat (`LeaderCanvas.tsx:582`, `fill={PALETTE[i % PALETTE.length]}`)
changée en dur vers `#ff00ff`, suite rejouée sans `--update-snapshots`,
couleur restaurée, suite rejouée une troisième fois pour confirmer le retour
au vert — deux fois (une fois avant, une fois après avoir corrigé le piège
de tolérance ci-dessous, pour prouver que le correctif changeait bien le
résultat).

## Ce que ça a trouvé

**Quatre pièges réels, chacun aurait rendu le gate soit flaky soit aveugle —
aucun n'était hypothétique, chacun observé en le faisant échouer en vrai.**

### Piège 1 — un flash de caption intermittent au montage (~1 échec / 3 runs complets)

`FlipReveal.tsx` (le composant qui anime la bascule Dirigeant/Assemblée)
flotte une légende pendant `CAPTION_MS=2600ms` sur un **vrai** changement de
mode — voulu — mais un `useRef` (`first.current`) censé la sauter au tout
premier montage s'est révélé ne pas le faire de façon fiable : sur la build
de production (`vite preview`), la légende est apparue une fois sur ~3 passes
complètes de la suite, jamais sur un sous-ensemble réduit à 2 tests (10/10
propre), jamais non plus sur 5 navigations répétées instrumentées avec un
`MutationObserver` (0/5) — un vrai race, rare, pas reproductible à la
demande. Contre le serveur de dev (`npm start`), en revanche, le même
`MutationObserver` l'a capturé **5 fois sur 5**, toujours ~700ms après le
montage (React Strict Mode double-invoque les effets en dev, jamais en
prod — cohérent avec l'écart de fréquence observé). Correctif appliqué
indépendamment de la cause exacte : `settleFlipCaption()` dans
`visual.spec.ts` attend `FLIP_CAPTION_LIFECYCLE_MS=3500ms` (le cycle de vie
complet de la légende, avec marge) avant toute capture touchant le
playground, puis affirme `toHaveCount(0)` — échec bruyant si ce budget
devient un jour faux, plutôt qu'une baseline silencieusement polluée.

### Piège 2 — le serveur de dev fait échouer un test par un timeout sans rapport avec le rendu

Premier essai avec `npm start` (serveur Vite dev, comme `playwright.config.ts`
existant) : `/laboratoire` a timeout sur `toBeVisible()` (>5s) — pas un bug de
rendu, juste la compilation à la demande du chunk lazy de cette route la
première fois qu'elle est visitée dans un run. Reproductible une fois,
disparu au retry (le chunk reste alors en cache du serveur dev). Corrigé à la
racine plutôt que par un timeout plus long : `playwright.visual.config.ts`
lance `vite build && vite preview` — le bundle réellement livré, sans
compilation à la demande, et arguably plus fidèle à ce qu'un vrai visiteur
voit (bundle dev non minifié, instrumenté HMR, n'est pas exactement le même
rendu).

### Piège 3 — sans le backend, `ParliamentCanvas` ne rend pas une carte légèrement différente, il rend un état d'erreur permanent

Attendu au départ : aucune des 5 captures ne devrait avoir besoin du backend
(`CLAUDE.md` documentait déjà que seules deux fiches du Laboratoire et le
mode Assemblée le sollicitent en e2e — et les 4 pages hors playground
n'ont aucun appel réseau au montage, vérifié par grep). Faux en partie :
lancé une première fois sans backend (dans le conteneur Docker, qui n'a pas
Python), `ParliamentCanvas` n'affiche **pas** un hémicycle légèrement décalé
— il affiche son propre message de repli, « ⚠ Hémicycle indisponible : le
calcul de l'assemblée n'a pas abouti… » et « 100 sièges — en attente de la
répartition », au lieu de sièges réels. Baseliner cet état aurait verrouillé
un état **structurellement cassé** qui ne peut plus jamais échouer — l'angle
mort exact que cet item existe pour fermer. Vérifié aussi dans l'autre sens :
`LeaderCanvas` en vue par défaut est, lui, identique avec ou sans backend (son
survol de zones colorées n'est pas calculé au montage) — donc pas une
supposition généralisée à tort, un cas vérifié composant par composant.
Corrigé en démarrant le vrai backend FastAPI dans le job CI (mêmes étapes que
le job `e2e` existant) et en documentant que `scripts/test-visual-docker.sh`
l'exige en local (`--network=host` pour atteindre le `:4434` de l'hôte).

### Piège 4 (trouvé en vérifiant le détecteur, pas en le construisant) — une tolérance de 1% masquait la régression qu'elle devait attraper

Premier réglage : `maxDiffPixelRatio: 0.01` (« marge pour le bruit
d'antialiasing sub-pixel », choisie avant même de mesurer si ce bruit
existait réellement). En testant le détecteur contre l'injection de
`#ff00ff` (section Protocole), **le test est passé** — un marqueur de
candidat mal coloré, visible à l'œil nu, ne représente qu'environ 0,07% des
pixels d'une capture de carte (un cercle de rayon 9px sur ~365 000 px), sous
le seuil de 1%. La tolérance que j'avais moi-même choisie « par prudence »
aurait rendu le gate aveugle exactement au genre de régression qu'il existe
pour attraper. Supprimée entièrement (retour au défaut de Playwright — zéro
pixel de tolérance au-delà du seuil de couleur par pixel) : 8 runs natifs
consécutifs et 6 runs Docker consécutifs, tous à zéro échec (voir chiffres
ci-dessous), puis la même injection **échoue bien**, proprement, avec un
diff de 303 pixels (ratio 0,01 — littéralement à la frontière de l'ancien
seuil, confirmant que ce n'était pas une marge de sécurité, mais un point
aveugle de la largeur exacte du bug testé) sur exactement les deux tests
affectés (`/playground` et `playground-leader-canvas`) — les 5 autres,
non affectés par ce composant, restent verts. Restauré au vert après retour
du code.

## Ce que ça a coûté

~5h : ~30 min de recherche/vérification d'outillage (statut Lost Pixel,
version Docker Playwright disponible) ; ~1h à construire le mécanisme de
base (config, spec, script Docker) ; ~1h30 à diagnostiquer et corriger les
pièges 1-3 (dont l'instrumentation `MutationObserver` pour capturer le flash
intermittent) ; ~1h à découvrir et corriger le piège de tolérance (deux
cycles complets d'injection/vérification, un avant et un après correctif) ;
~1h de vérification finale (8 runs natifs + 6 runs Docker, suite e2e
fonctionnelle complète rejouée pour confirmer l'absence de régression,
`tsc`/`vitest`/`lint`). Aucune nouvelle dépendance de production ni de dev
(`@playwright/test` déjà présent) ; une image Docker (`mcr.microsoft.com/
playwright`, ~1,5 Go, tirée une fois, réutilisée).

## Verdict et pourquoi

**Adopté, gate CI dans un job séparé (`visual-regression` dans `e2e.yml`),
avec une réserve honnête.** Stabilité mesurée, pas supposée : **8/8** runs
natifs consécutifs et **6/6** runs dans le conteneur Docker épinglé (celui
que la CI utilise réellement), tous à zéro échec, sous la config finale
(zéro tolérance de pixels). Le détecteur a été vérifié contre une régression
injectée deux fois (avant et après le correctif du piège 4), avec un échec
propre scopé exactement aux deux tests affectés dans les deux cas où il
échoue et un retour au vert après revert dans les deux cas. C'est le même
niveau de preuve que Lot 6.7 (license-compliance) avant d'être promu
bloquant.

La réserve : le job tourne dans un conteneur GitHub Actions (`container:`
sur le job) — un mécanisme standard, mais **jamais observé sur un vrai run
GitHub Actions** dans le cadre de cette expérience (cette session travaille
dans un worktree isolé, sans droit de push ni de PR — voir les notes de
process de la tâche). Tout le reste a été vérifié en local avec le même
outillage (Docker, la même image épinglée, les mêmes commandes) : c'est une
preuve forte de la stabilité du *mécanisme de comparaison de pixels*, mais
pas une preuve que `actions/setup-python`/`actions/setup-uv` se comportent
identiquement une fois exécutées à l'intérieur d'un `container:` GitHub
Actions plutôt que sur le runner nu (comme le fait déjà le job `e2e`
existant). Recommandation : le job est câblé pour échouer/réussir
normalement dès la première PR qui le déclenche (donc un vrai signal, pas un
faux vert) ; mais je recommande de **ne l'ajouter aux *required status
checks* GitHub qu'après avoir vu tourner sans accroc son premier vrai run**
— exactement le risque documenté par le commentaire existant d'`e2e.yml` sur
la PR #205 (« a required check that never reports can't be satisfied »),
appliqué ici par prudence à un mécanisme (`container:`) qui n'a pas encore
tourné une seule fois sur ce dépôt.

## Ce que j'en retiens (transférable à un autre projet)

1. **Une tolérance de pixels choisie « par prudence » sans être mesurée est
   un pari, pas une marge de sécurité — et elle peut annuler exactement ce
   que le test existe pour attraper.** Le seul moyen de savoir si une
   tolérance est trop large : y injecter une régression réaliste et
   vérifier qu'elle échoue encore. Un test de régression visuelle qui n'a
   jamais été mis en échec délibérément n'est pas vérifié, il est espéré.
2. **« Le composant ne dépend pas du backend » est une hypothèse par
   composant, pas une propriété de la page.** Deux cartes voisines dans le
   même écran (`LeaderCanvas`, `ParliamentCanvas`) se sont comportées
   différemment sans backend — l'une invisible à l'œil, l'autre un état
   d'erreur permanent. Vérifier chaque cible individuellement (couper le
   backend et regarder) coûte quelques minutes ; supposer coûte un gate qui
   verrouille un bug pour toujours sans jamais rougir.
3. **Un flash d'UI intermittent peut être bien plus fréquent en dev
   (Strict Mode double-invoque les effets) qu'en prod — tester contre
   l'environnement réellement utilisé (ici : le build de prod, celui que la
   CI compare) plutôt que le serveur de dev le plus pratique à itérer
   dessus change la fréquence observée d'un ordre de grandeur.** Le
   corollaire pratique : la baseline la plus robuste n'est pas « attendre
   que l'état semble stable », c'est attendre le budget de temps connu du
   pire cas (ici le cycle de vie fixe de 2600ms d'une légende), avec une
   assertion qui échoue fort si ce budget devient faux.
4. **Vérifier la maintenance d'un outil avant l'essai, pas après, évite un
   essai entier.** Lost Pixel a été écarté en une recherche (dépôt archivé,
   équipe partie chez Figma) sans qu'un seul test ait été nécessaire — le
   même réflexe que `license-checker-rseidelsohn` au Lot 6.7, appliqué ici
   à un choix d'outil plutôt qu'à une licence.
