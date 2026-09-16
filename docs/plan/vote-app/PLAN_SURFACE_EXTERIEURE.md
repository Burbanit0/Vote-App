# Plan — La surface extérieure

> **Origine** : audit demandé le 2026-09-16, après la clôture de
> `PLAN_CI_STRUCTURAL_GAPS.md` (7 catégories à 5/5). La question posée était
> « la CI est solide, quoi d'autre ? ». État vérifié **en direct** : six
> agents d'audit en parallèle (frontend, backend, qualité des tests,
> produit/ops, surface d'abus, pédagogie), puis **chaque trouvaille
> structurante re-vérifiée à la main** avant d'entrer dans ce plan — les
> mesures citées ici sont les miennes, pas celles des agents.
>
> Légende de statut : 🔴 pas fait / ouvert · 🟡 dette documentée, non
> bloquant · 🟢 fait/résolu.
>
> **Portée** : ce plan ne couvre que ce qui touche au **monde extérieur** —
> déploiement, utilisateurs réels, lecteurs d'écran, charge hostile, et la
> frontière entre deux implémentations. Il ne double **aucun** des quatre
> plans existants :
> - `PLAN_SOLIDITE_TECHNIQUE.md` (Lots 0-14) — outillage qualité interne.
> - `PLAN_CI_STRUCTURAL_GAPS.md` — clos, 7/7 catégories.
> - `PLAN_UX_ACCESSIBILITE.md` — **les 7 phases sont construites** (vérifié :
>   `feat/play-analytics` … `feat/analogies-motion`, toutes présentes dans
>   `git log --all`). Ce plan reprend là où celui-là s'arrête.
> - `PLAN_METHODES_HISTOIRES_ATLAS.md` — **à moitié fait** (3 chantiers sur
>   6 : `promote-extra-rules`, `stories-batch`, `blank-in-electorate`
>   construits ; `method-coverage-audit`, `blank-engine-live`,
>   `blank-stories` non). Les items restants sont repris en §2.L, pas
>   réécrits.

---

## 1. Constat général

Le constat tient en une phrase : **tout ce qui est excellent ici est mesuré
de l'intérieur, et tout ce qui est faible est à la frontière avec
l'extérieur.**

La discipline d'ingénierie est réelle et mesurable : 1 963 commits sur 563
jours, ~163 k lignes source+tests, 15 workflows, 15 347 lignes de
documentation, un harnais de parité de 601 scénarios dont 481 exhaustifs, 96
endpoints tous de rang A, une i18n bilingue sur 79 namespaces. Rien de tout
cela n'est du décor.

Mais : **0 tag git, 0 release GitHub, `version: 0.1.0`, et aucune étape de
déploiement dans aucun workflow** (`grep -rlE "fly deploy|flyctl|kubectl|docker push"
.github/workflows/` → vide ; `release.yml` s'arrête à `Create GitHub
Release`). `fly.toml` est un gabarit dont le nom d'app n'a jamais été
réservé. La boucle de rétroaction se referme sur « la CI est verte », jamais
sur « quelqu'un s'en est servi ».

C'est cohérent avec ce qu'on observe partout ailleurs : la CI est devenue
excellente parce que c'est la seule partie de la boucle qui **se referme**.
Les quatre faiblesses les plus graves de ce plan sont toutes à la frontière —
une entrée non bornée venue d'un inconnu (§2.A), deux affirmations fausses
lues par un apprenant (§2.B), des graphiques muets pour un lecteur d'écran
(§2.H), et deux règles de vote jamais confrontées à l'implémentation de
référence (§2.F).

**Prémisses corrigées en cours d'audit** (elles circulaient dans mes propres
notes et dans certains docs) :

| Prémisse | Réalité vérifiée |
|---|---|
| « ~280 `any` non typés » | **~15 réels**, 14 justifiés. Le Lot 6.4 a déjà fait le travail (238 → 27, tracé dans `PLAN_SOLIDITE_TECHNIQUE.md`). Le 280 était un grep sur le mot anglais « any » en prose. |
| « `api/domain/polity/` est du code mort sur develop » | **Faux.** 24 modules de test sur develop l'importent — c'est du code exercé qui gagne sa couverture. Le déplacer coûterait plus qu'il ne rapporte (voir §4). |
| « 9 fonctions de rang F » | **2** (`radon cc api/ -n E -s` : 15 fonctions ≥ E, dont 2 F). |
| « Alembic / base de données » | **Il n'y en a pas.** Zéro hit sur `sqlalchemy|alembic|create_engine`. L'app est réellement sans état ; Redis est optionnel et se dégrade en silence. |
| « 4 namespaces i18n morts » | **1 seul** (`auth`, 0 référence). `simulation` (65), `scenario` (40), `electionLab` (5) sont toujours utilisés par des composants. |
| « v8 de polity bloqué sur un bug vLLM » | **Périmé.** Confirmé auprès de la session qui possède ce chantier : vLLM tourne, un bake-off complet a été mené. Ce plan ne cite plus l'état d'avancement de polity. |

---

## 2. Items à traiter, par priorité

### 2.A 🔴 Une requête de 30 octets peut tuer la machine

**Constat** (vérifié à la main, ligne par ligne) :
`api/schemas/simulations.py:52` déclare `num_voters: int = 1000` — **sans
`ge`/`le`**. Le worker `api/domain/simulations/base.py:201-205` ne borne
rien, pas même un `int()` :

```python
num_voters = data.get("num_voters", 1000)
voters = [create_voter(issues, i) for i in range(num_voters)]
```

Donc `POST /api/v2/simulations/simulate_voters {"num_voters": 50000000}`
alloue jusqu'à épuisement. `fly.toml` donne **512 Mo** à la VM et le
`Dockerfile` lance **`--workers 1`** : l'OOM-kill emporte l'API *et* le SPA
(même conteneur). Le timeout de 180 s ne sauve rien —
`api/core/worker_dispatch.py:70-78` documente lui-même que le thread
orphelin continue de tourner et d'allouer après expiration.

**L'ironie utile** : le fichier **définit déjà** les types bornés, avec un
commentaire expliquant qu'ils reprennent la convention de
`api/schemas/election.py` :

```python
NumVoters = Annotated[int, Field(ge=10, le=1000)]   # simulations.py:36
NumRounds = Annotated[int, Field(ge=1, le=10)]
NumRuns   = Annotated[int, Field(ge=1, le=500)]
```

…et ne les applique pas. **23 champs** de ce fichier sont non bornés
(recensés : lignes 52, 59, 69, 122-124, 141, 143, 153, 155, 163, 165, 174,
181, 183, 201-202, 211, 230, 240, 248, 275, 279).

Le pire ratio requête-bon-marché / réponse-coûteuse est
`SensitivityRequest.values` (`simulations.py:174`) : la liste est parcourue
entièrement (`api/domain/simulations/compare.py:250-283`), **sans le cap
`[:10]`** que son jumeau what-if applique pourtant (`whatif.py:96`). 500
valeurs = 500 `compare_all_methods`.

**Pourquoi ça compte** : c'est le seul item du plan qui est un **bloqueur
dur** au déploiement. Tant qu'il n'est pas fait, §2.C ne peut pas basculer
côté « on publie ».

**Action** : appliquer `NumVoters`/`NumRounds`/`NumRuns` aux 23 champs ;
`max_length=10` sur `SensitivityRequest.values` ; `max_length=8` sur chaque
`candidates: List[Any]`. Puis router la boucle Monte-Carlo Socket.IO
(`api/sockets/__init__.py:313`, un `asyncio.to_thread` brut) à travers
`run_bounded` — elle contourne aujourd'hui le sémaphore, le timeout **et**
le rate limiter (slowapi ne voit jamais ce chemin : `socketio.ASGIApp`
intercepte avant FastAPI).

**Effort** : S (≈ 20 lignes pour les schémas, ≈ 15 pour le socket) ·
**Priorité** : **la plus haute du plan**.

**Déjà sain, ne pas y toucher** : la surface publique `/api/v1` est
correctement bornée (10/min sur `/simulate`, 5/min sur `/compare`,
50-2000 électeurs clampés dans le worker) ; `schemas/election.py` compte 81
`ge=`/`le=` ; Kemeny-Young n'est pas NP-dur ici (`_KY_EXACT_CAP = 6`) ; CORS
est en liste blanche, pas `*`.

### 2.B 🔴 Deux affirmations fausses dans le contenu pédagogique

Pour une app qui **enseigne** la théorie du vote, c'est la classe de bug la
plus grave — et les deux sont contredites par le `THEORY.md` du projet
lui-même.

**1. Le critère de participation de Copeland.**
`voter-app/src/data/methodCriteria.ts:85` : `condorcet: { …
participation: 'yes' }` (le commentaire juste au-dessus précise « Copeland's
method »). Or `THEORY.md:675` (§4.6) écrit : « Moulin (1988) a démontré
qu'**aucune méthode Condorcet-cohérente n'y échappe entièrement** ».
Incohérence interne en prime : le même fichier marque correctement
`minimax: participation: 'no'` (ligne 101) et `schulze: 'no'` (ligne 111) —
deux méthodes Condorcet. Copeland est la seule à porter une coche verte
imméritée, sur une matrice de critères publique.

**2. L'histoire « clones » sur-généralise.**
`voter-app/src/i18n/locales/playground.fr.ts:123` : « Avec Condorcet, le
clonage ne sert à rien : B bat toujours A ET A2 en duel… **La faille était
propre à Borda.** » Or `THEORY.md:291` dit de Copeland, en gras : « **Pas
indépendant des clones** » (Tideman, 1987), en précisant que Ranked Pairs a
été *conçu précisément pour corriger ce défaut*, avec un test à l'appui
(`test_tideman_ranked_pairs_motivation`). Dans le scénario particulier de
l'histoire, B est vainqueur de Condorcet, donc le clonage échoue — mais la
phrase généralise de ce cas à la méthode, et enseigne exactement le
contresens qu'un cours de théorie du vote existe pour empêcher.

**Action** : corriger les deux (`'yes'` → `'no'` ; reformuler la conclusion
de l'histoire pour rester sur son cas particulier), puis **ajouter un garde-
fou CI** : un test qui compare `methodCriteria.ts` aux affirmations de
`THEORY.md` et échoue sur une divergence. Sans ce garde-fou, la même dérive
reviendra — c'est la classe de problème que cette session a déjà vue trois
fois ailleurs.

**Effort** : S (les deux corrections) → M (le garde-fou) · **Priorité** :
haute — c'est du contenu faux, publié, sur le cœur de métier.

### 2.C 🟢 Décision structurante : publier, ou dire qu'on ne publie pas

Ce n'est pas une tâche, c'est **une décision à prendre** (voir §3), et
plusieurs items en dépendent.

**Constat** : 0 tag, 0 release, `0.1.0`, aucune étape de déploiement, un
`fly.toml` gabarit, et un README qui documente `fly deploy` comme une
commande que **le lecteur** exécute, avec « Public URL:
`https://<app>.fly.dev` » en espace réservé — pas un lien. Un visiteur du
dépôt public MIT attend raisonnablement une démo et n'en trouve aucune.

**Pourquoi ça compte** : l'état intermédiaire actuel — machinerie de release
complète, zéro release — est le pire des deux mondes. Il coûte l'entretien
d'un pipeline de publication sans rien publier, et il laisse le
`PLAN_UX_ACCESSIBILITE.md` dans une impasse : sa **Phase 0 est
« instrumenter le tunnel pour savoir où les vrais visiteurs décrochent »**,
construite et mergée (PR #83) — mais il n'y a pas de visiteurs. On mesure un
entonnoir vide.

**Action** : trancher §3. Les deux branches sont légitimes ; l'état actuel
ne l'est pas.

**Tranché (2026-09-16) : Branche B — c'est un labo personnel public, pas un
produit.** `README.md` porte désormais une ligne explicite en tête de
fichier (« No hosted instance ») et le placeholder « Public URL:
`https://<app>.fly.dev` » a été retiré de la section Deploy — elle documente
maintenant comment se déployer *soi-même*, pas une instance qui existerait
déjà. Conséquence sur le reste du plan (§5) : §2.A reste fait (bloqueur dur
même en labo), §2.D/§2.G/§2.I retombent à « quand ça arrangera » plutôt que
d'être séquencés maintenant ; §2.H/§2.J/§2.L reprennent leur place.

**Effort** : S (décision) → M (si publication : §2.A d'abord, puis CORS,
`--forwarded-allow-ips`, et le plafond de concurrence ci-dessous) ·
**Priorité** : haute.

### 2.D 🟡 Le plafond de concurrence est bas et invisible

**Constat** : `docs/exploration/EXP-007` a mesuré un pool partagé de 4
workers (`MAX_CONCURRENT_WORKERS = 4`, `asyncio.Semaphore(4)`) saturant
vers 1,0-1,3 req/s. À 8 utilisateurs simultanés, la latence passe de 3 s à
**25-30 s, avec zéro 429/503**. Sous charge, l'app ne renvoie pas d'erreur :
elle **paraît figée**.

**Pourquoi ça compte** : c'est le comportement le plus déroutant possible
pour un visiteur, et il n'existe aucun signal côté client pour le
distinguer d'un bug. Gated sur §2.C : sans déploiement, c'est théorique.

**Action** (si publication) : soit une file avec progression visible, soit —
beaucoup moins cher — un timeout côté client avec un état « système
occupé » explicite. Vérifier aussi que slowapi ne compte pas sur l'IP du
proxy Fly (`get_remote_address` → `request.client.host`, et le `Dockerfile`
ne passe pas `--forwarded-allow-ips`) : si c'est le cas, tous les visiteurs
partagent un seul seau et le limiteur devient un auto-DoS.

**Effort** : S (état client) → L (file réelle) · **Priorité** : moyenne,
conditionnée à §2.C.

### 2.E 🟡 Deux règles de vote ne sont jamais confrontées au backend

**Constat** (trouvé en poursuivant l'écart « 29 vs 26 méthodes » entre
`README.md:17` et `EXP-006`, qui n'est pas une coquille) : l'union `Rule` de
`voter-app/src/lib/playgroundVoting.ts` compte **29** règles ; le harnais de
parité en verrouille **26**. Les trois non couvertes, vérifiées par
diff ensembliste contre `engineParity.json` :

- `random_ballot` — **exclusion légitime**, c'est une loterie
  (`gen_engine_parity.py:75` le dit).
- `approval` — déterministe, implémentée côté backend
  (`simulation_ranked_utils.py`, `simulation_voting_utils.py`).
- `majority_judgment` — déterministe, implémentée côté backend
  (`simulation_score_utils.py`).

**Pourquoi ça compte** : le harnais a attrapé **au moins 8 divergences
réelles** (archéologie git sur `engineParity.json` : Bucklin cumulatif,
élimination IRV/Coombs, beatpath Schulze, égalité de barrage STAR, « 13
règles élisaient un vainqueur différent quand on mélangeait les bulletins »,
plus trois commits « N vrais bugs »). Les règles **hors** du harnais sont
exactement là où une divergence non détectée peut vivre. Et le Jugement
majoritaire (Balinski-Laraki) est une méthode française, sur une app
francophone d'éducation au vote : si les deux implémentations divergent,
l'app enseigne faux.

**Action** : étendre `gen_engine_parity.py` pour émettre des bulletins
cardinaux pour `approval` et `majority_judgment`, régénérer, lancer le test
de parité. Si elles concordent, un trou réel dans la garantie la plus forte
du dépôt est fermé ; sinon, on vient de trouver un bug dans une méthode que
l'app enseigne.

**Effort** : S (une après-midi) · **Priorité** : haute — meilleur rapport
valeur/effort du plan.

### 2.F 🟡 La suite E2E n'a aucun oracle de résultat

**Constat** : 14 specs, 79 tests, 235 assertions, 4 navigateurs — et
**aucun test ne vérifie quel candidat gagne**. Le motif partout est
`expect(winner).not.toBeEmpty()` plus `expect(seen.size).toBeGreaterThan(1)`
(`playground-campaign.spec.ts:38,86`, `surfaces.spec.ts`,
`playground-method.spec.ts:89`). Recherche d'un vainqueur attendu en dur :
aucune. Un moteur qui renverrait des **noms au hasard, différents par
règle**, passerait la suite entière.

**Pourquoi ça compte** : c'est la seule couche qui teste le système assemblé
(front + back + réseau). Le harnais de parité prouve que les deux moteurs
sont d'accord ; rien ne prouve que ce que l'**écran** affiche vient bien de
ce moteur.

**Action** : un électorat fixe, des vainqueurs connus par règle, une
assertion par règle. Les fixtures existent déjà côté unitaire.

**Effort** : S · **Priorité** : haute.

### 2.G 🟡 Les graphiques sont muets, et les graphiques *sont* le produit

**Constat** : c'est une app de visualisation de données. Or **un seul
`sr-only` dans tout le frontend** (`components/ui/modal.tsx`), zéro
`sr-only` et zéro `aria-live` dans `components/playground/`. Six des neuf
composants graphiques de `components/Simulation/` n'ont **ni `aria-label`,
ni `role="img"`, ni `<desc>`, ni `<caption>`** : `IdeologyHeatmap`,
`ManipulabilityChart`, `MonteCarloConvergencePanel`, `MonteCarloLiveChart`,
`MonteCarloResults`, `VoteStepAnimator`. Et `ParliamentCanvas.tsx:346`
porte bien un `role="img"`, mais son libellé
(`playground.en.ts:605`) est « Hemicycle — seats per party » : **aucune
donnée**. Un utilisateur de lecteur d'écran déplace un parti, l'hémicycle se
redessine, et rien ne le lui dit.

L'audit a1y existant est plus large qu'attendu (les 5 surfaces, le mode
sombre, la navigation clavier réelle) — mais il n'audite que le **rendu
initial** de chaque surface : aucune des 62 fiches en chargement paresseux,
aucun des 4 moments du playground au-delà du défaut, n'est jamais dans le
DOM quand axe s'exécute.

**Le correctif existe déjà dans le dépôt** : `ResultsMethodTable.tsx` est
exactement le motif de repli tabulaire à câbler.

**Action** : `aria-label` porteur de données (« B en tête avec 34 % ») +
repli `ResultsMethodTable` sur les graphiques porteurs de résultat ;
`aria-live` sur l'hémicycle ; étendre l'audit axe à un moment non-défaut et
à une fiche.

**Effort** : M · **Priorité** : haute si §2.C bascule côté publication,
moyenne sinon.

### 2.H 🟡 Le théorème d'Arrow est écrit mais inatteignable

**Constat** : `fr.ts:2563-2625` contient 63 lignes d'excellente prose sur
Arrow, y compris une prémisse interactive (« cochez les axiomes que vous
souhaitez garantir » → « Aucune méthode ne satisfait tous les critères —
c'est le théorème d'Arrow »). **Aucun composant ne consomme une seule clé
`arrow.*`.** Il n'y a pas de fiche `thy-arrow` dans `labCatalog.tsx`, et
`/theory` redirige vers `/laboratoire`. Le résultat d'impossibilité central
du domaine est absent du produit. Même schéma pour ~11 autres namespaces
orphelins (~360 lignes), dont `mj` (jugement majoritaire) et `plott`.

**Action** : une fiche + un panneau. La copie est déjà écrite et relue.

**Effort** : S-M · **Priorité** : moyenne — meilleur retour sur contenu déjà
payé.

### 2.I 🟡 Le premier contact est cassé, et le « pourquoi » est sur la mauvaise page

Trois défauts qui se tiennent, tous dans le parcours d'un nouveau venu :

1. **La visite guidée décrit une app qui n'existe plus.**
   `OnboardingTour.tsx:51-80` cible `[data-tour="blank-vote-card"]`,
   `[data-tour="compare-card"]`, `[data-tour="elections-section"]` —
   **aucun n'existe** (seuls `navbar` et `hero` existent). Sa copie promet
   « 3 outils : Simulateur de scénario, Comparaison des méthodes,
   Simulateur de crise » (routes retirées) et « comparez sous **5**
   méthodes » alors qu'il y en a 29. Le bouton « ? » de la navbar mène un
   primo-visiteur dans une visite fausse et cassée. **Une visite cassée est
   pire que pas de visite.**
2. **`WinnerExplanation` n'est pas dans le Bilan.** Le composant qui dit
   *pourquoi* cette méthode a élu ce candidat (« gagne aux reports »,
   « gagne tous ses duels ») n'est monté que dans `AVousDeJouerPage.tsx`.
   L'instrument phare montre donc *que* Borda et Condorcet divergent, et
   jamais *pourquoi*.
3. **Le Bilan par défaut est un tableau de 29 lignes.**
   `PlaygroundController.tsx:71` initialise `enabledRules` avec **toutes**
   les `LEADER_RULES`.

**Action** : supprimer ou réécrire la visite (supprimer est acceptable) ;
monter `WinnerExplanation` par ligne de méthode dans le Bilan ; réduire le
défaut à ~5 méthodes (une par famille) avec « afficher les 29 » en option.

**Effort** : S (visite, défaut) → M (WinnerExplanation) · **Priorité** :
moyenne-haute.

### 2.J 🟢 Le tableau de dépendances à 62 entrées de `PlaygroundController`

**Constat** : `PlaygroundController.tsx` fait 658 lignes (14 `useState`, 14
`useMemo`, 5 `useCallback`, 6 `useEffect`). Le vrai défaut est le mémo
`main`, lignes **494-626** : un objet de **67 champs** suivi d'un tableau de
dépendances de **62 entrées maintenu à la main**. jscpd le signale comme un
clone de 44 lignes. Ajouter un champ suppose d'éditer deux listes
parallèles ; oublier la seconde donne un contexte **silencieusement périmé,
sans erreur de type**.

**À porter au crédit de l'auteur** : le compromis est documenté honnêtement
sur place (lignes 454-479), et le test dit lui-même que le split
`useMethodSelection` ne réduit pas les rendus
(`PlaygroundController.render.test.tsx:42-45`). C'est de la dette connue,
pas un angle mort.

**Action** : 3-4 contextes par préoccupation, ou le motif de sélecteurs
Zustand **déjà utilisé dans ce dépôt** (`stores/useElectionStore.tsx`).

**Effort** : M (≈ 1 jour, surface bien testée) · **Priorité** : moyenne.

### 2.K 🟢 Complexité : 15 fonctions ≥ E, les 2 F sont dans polity

**Constat** (mesuré **sur `develop`** : `uvx radon cc api/ -e "api/tests/*"
-n E -s`) — 15 fonctions de rang E ou pire. Les deux F :

| Fonction | Rang | Emplacement |
|---|---|---|
| `index_events` | **F (81)** | `api/domain/polity/indexer.py:266` |
| `_run_accountability_phase` | **F (44)** | `api/domain/polity/run_polity_simulation.py:1500` |
| `_intergenerational_worker` | E (40) | `api/domain/theory/workers.py:1787` |
| `_hold_presidential_election` | E (39) | `api/domain/polity/run_polity_simulation.py:835` |
| `_check_sen` | E (39) | `api/domain/theory/workers.py:898` |

**Distinction qui compte** : les offenseurs de la couche *engine*
(`get_condorcet_matrix` E(32), `get_schulze_winner` D(29), `get_stv_result`
D(29)) sont des algorithmes de choix social irréductibles — **les laisser**.
Les offenseurs de la couche *domain worker* sont longs par accumulation
(construire l'électorat → N tours → agréger → formater), pas par
algorithme : ceux-là sont extractibles.

**Coordination requise** : les deux F sont dans des fichiers activement
possédés par la session polity. Elle a elle-même désigné cette réduction de
complexité comme l'amélioration honnête côté develop. **Le séquencement lui
revient**, ce plan ne l'impose pas.

**Effort** : S par fonction, L en agrégat (135 fonctions ≥ C) — à traiter
par cliquet, pas par campagne · **Priorité** : basse-moyenne.

### 2.L 🟢 Petites exactitudes et reliquats

Chacun est de l'ordre de la minute à l'heure :

- **`README.md:17` annonce 29 méthodes**, `EXP-006` en mesure 26 — les deux
  sont vrais (29 côté client, 26 verrouillées en parité). Le formuler ainsi
  plutôt que de « corriger » un des deux. Lié à §2.E.
- **Le namespace i18n `auth` est mort** (0 référence, vérifié en Python —
  `simulation`/`scenario`/`electionLab` sont **toujours utilisés**, ne pas
  les toucher).
- **La pseudo-locale compte dans le budget de bundle.**
  `.size-limit.json` globe `build/assets/*.js` ; `pseudo` (44,9 ko) +
  `playground.pseudo` (24,9 ko) ne sont atteignables que par `?lng=pseudo`
  pour les tests e2e — **aucun utilisateur ne les télécharge**. Les exclure
  rend ~9 points de marge (77 % → ~70 %).
- **`data/quizQuestions.ts` est orphelin** (0 référence). Le
  `PLAN_UX_ACCESSIBILITE.md` le listait déjà comme « quiz orphelin à
  ranimer » — il l'est toujours. Ranimer ou supprimer.
- **Le score de mutation ne juge que < 4 % du code.** Backend : 3 fichiers
  (~4 700 de 40 559 lignes) ; frontend : **un seul fichier**
  (`playgroundVoting.ts`, 1 215 de ~88 000). Le score réel est 66,57 %
  (`.github/mutation-baseline.json`). **Le snooze n'est pas de la
  négligence** — le nombre de mutants a triplé (1 906 → 6 322) quand mutmut
  3.8.0 a corrigé sa détection de couverture, et les trous sont fermés un à
  un plutôt qu'en écrivant des tests contre le plancher ; c'est du bon
  jugement, documenté. La seule action : **cesser de citer ce chiffre comme
  s'il couvrait le dépôt**, ou élargir le périmètre à
  `api/domain/election/` (8 822 lignes testées mais non jugées).
- **Reliquats `PLAN_METHODES_HISTOIRES_ATLAS.md`** : `method-coverage-audit`,
  `blank-engine-live`, `blank-stories` jamais construits. Ne pas réécrire ce
  plan — le reprendre.
- **`lazyWithPreload.ts` et `rechartsFormatters.ts`** sont les deux seuls
  fichiers de `src/lib/` qui importent React : ils appartiennent à `hooks/`
  ou `components/`, pas à une « lib pure ».

---

## 3. Décision structurante — à trancher avant de séquencer

> **Tranché (2026-09-16) : Branche B.** Voir §2.C pour ce qui a été fait.

**La question** : Vote Lab est-il un produit destiné à des visiteurs, ou un
laboratoire personnel public en lecture seule ?

Les deux réponses sont légitimes. C'est l'**absence** de réponse qui coûte.

**Branche A — on publie.** Alors, dans l'ordre : §2.A (bloqueur dur,
non négociable), puis `CORS_ORIGINS`, `--forwarded-allow-ips`, §2.D (état
« occupé »), §2.G (accessibilité des graphiques), §2.I (premier contact).
§2.B devient urgent : du contenu faux lu par de vrais apprenants. Et la
Phase 0 déjà construite du `PLAN_UX_ACCESSIBILITE.md` commence enfin à
mesurer quelque chose.

**Branche B — c'est un labo.** Alors une ligne dans le README suffit (« pas
d'instance hébergée — voir *Local setup* »), et §2.A, §2.D, §2.G, §2.I
retombent à « quand ça arrangera ». Mais §2.B et §2.E restent : le contenu
faux et la parité manquante sont faux et manquants même sans un seul
visiteur, et ce dépôt est public — quelqu'un peut cloner et apprendre faux.

**Ce qui n'est pas une option** : garder la machinerie de release complète,
le `fly.toml`, la Phase 0 d'analytics et le « Public URL » en espace réservé,
sans publier ni le dire.

---

## 4. Ce qu'il ne faut **pas** faire

Aussi important que la liste des actions — ces pistes paraissent être de la
dette et n'en sont pas :

- **Ne pas fusionner le double moteur.** 1,2 k lignes miroir semblent
  gaspillées, mais le harnais a attrapé ≥ 8 bugs réels et sa fixture est de
  601 scénarios dont **481 exhaustifs** (le domaine complet pour n ≤ 3
  candidats, m ≤ 5 électeurs). C'est une preuve sur domaine borné, pas un
  échantillon. C'est le meilleur actif du dépôt.
- **Ne pas déplacer `api/domain/polity/` hors de develop.** 24 modules de
  test l'importent ; le déplacer transformerait chaque sync develop→polity
  en vraie fusion, retirerait le moteur des portes de develop, et
  décalerait d'un coup les baselines vulture/radon/jscpd — or le cliquet
  qualité échoue aussi **à la baisse**, donc il faudrait un `--update`
  mesuré dans la même PR. Analyse fournie par la session qui possède ce
  chantier ; elle est décisive.
- **Ne pas rouvrir le calendrier de fusion polity → develop.** Décision
  prise et consignée (`project_polity_branch_workflow.md`) : question
  répondue, pas ouverte. Le seul levier sans toucher à la décision est de
  synchroniser develop→polity plus souvent qu'hebdomadairement.
- **Ne pas chasser les `any`.** ~15 réels, 14 justifiés. Le Lot 6.4 l'a
  fait.
- **Ne pas chasser knip/jscpd.** Les 92 findings knip sont **tous** des
  types exportés inutilisés ; zéro fichier mort, zéro dépendance morte.
  jscpd : 0,58 % des lignes.
- **Ne pas toucher la couche routes.** 96 endpoints, tous rang A, dispatch
  centralisé. C'est la meilleure partie du backend.
- **Ne pas « ajouter une base de données ».** L'app est sans état par
  conception et correctement ainsi.
- **Ne pas laisser les algorithmes de choix social « se simplifier ».**
  Schulze, STV, Condorcet sont complexes parce que le domaine l'est.

---

## 5. Séquencement proposé

Pas de dépendance stricte, sauf §2.A avant toute publication. Ordre par
rapport valeur/risque :

1. **§2.A** — bornes d'entrée. Bloqueur dur, ≈ 20 lignes, à faire même en
   branche B (le dépôt est public, quelqu'un lancera ce conteneur).
2. **§2.B** — les deux erreurs de contenu + le garde-fou CI. Du faux publié
   sur le cœur de métier.
3. **§2.E** — parité `approval` + `majority_judgment`. Une après-midi,
   meilleur rapport valeur/effort.
4. **§2.C** — trancher la décision. Elle ordonne tout le reste.
5. **§2.F** — un oracle de résultat e2e.
6. Puis, selon la branche retenue : §2.G, §2.I, §2.D (branche A) ou §2.H,
   §2.J, §2.L (branche B).

---

## 6. Vérification — commandes de référence

```bash
# 2.A — les champs non bornés (attendu avant correction : 23)
grep -nE '^\s+(num_\w+|values|candidates)\s*:\s*(int|List)' \
  fast_api_voter/api/schemas/simulations.py | grep -v 'Num\(Voters\|Rounds\|Runs\)'

# 2.B — l'incohérence interne de la matrice de critères
grep -n "participation" voter-app/src/data/methodCriteria.ts
grep -n "Condorcet-cohérente" THEORY.md

# 2.E — les règles hors parité (attendu : approval, majority_judgment, random_ballot)
#   union Rule côté client vs clés présentes dans engineParity.json

# 2.F — un vainqueur attendu en dur dans la suite e2e (attendu : aucun)
grep -rnE "toHaveText\(['\"][A-Z]" voter-app/tests/e2e/*.spec.ts

# 2.G — sr-only dans tout le frontend (attendu : 1)
grep -rc "sr-only" voter-app/src --include="*.tsx" | grep -v ":0"

# 2.K — complexité (attendu : 15 fonctions ≥ E, 2 F)
cd fast_api_voter && uvx radon cc api/ -e "api/tests/*" -n E -s

# état de publication (attendu aujourd'hui : 0, 0)
git tag | wc -l ; gh release list | wc -l
```
