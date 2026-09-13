# RETROSPECTIVE — Le plan de solidité technique a-t-il survécu au contact ?

> Rédigé le 2026-09-11, pour l'item « Rétrospective du plan » du Lot 13 du
> [plan de solidité technique](PLAN_SOLIDITE_TECHNIQUE.md). Question posée par
> le plan lui-même : *« Ce plan a-t-il survécu au contact ? Quels items
> abandonnés, lesquels ajoutés en route, lesquels ont déçu. »*
>
> Document séparé plutôt qu'une simple case cochée dans le tableau du Lot 13,
> pour la même raison que `docs/exploration/` existe séparément du code : une
> rétrospective qui ne cite que des impressions ne vaut rien, une qui cite des
> commits, des dates et des chiffres se vérifie. Vit à la racine, à côté de
> `PLAN_SOLIDITE_TECHNIQUE.md` et `CODE_AUDIT.md` — c'est le document qu'elle
> retrospecte, pas une expérience d'outillage isolée (`docs/exploration/`) ni
> une entrée de session (`docs/journal/`).

---

## En chiffres, avant tout récit

- **Ouverture** : 2026-09-07 (commit `617807a`, `develop` à `a5cb7ce`, tous
  les gates verts — 1789 tests backend, 91 % de couverture).
- **Fenêtre réelle d'exécution** : du 2026-09-07 au 2026-09-12, soit **6 jours
  calendaires** — pas les semaines que la somme des efforts `S`/`M`/`L`
  annoncés lot par lot aurait pu laisser supposer.
- **203 commits, 86 pull requests mergées** dans cette fenêtre
  (`git log --oneline 617807a^..2e2f6aa`).
- **14 carnets d'expérience** clos (`docs/exploration/EXP-001` à `EXP-014`,
  vérifié en comptant les fichiers réels, pas repris de mémoire) — le Lot 13
  lui-même corrige au passage l'ambition initiale du Lot 0.3 (« ~25 outils
  essayés ») en un chiffre honnête : ~25 outils essayés au total, 14 verdicts
  formels, le reste tranché en paragraphe « détail » quand l'essai était trop
  court pour justifier le rituel complet.
- **Lots 0 à 13 : tous livrés.** Lot 13 lui-même est le seul encore
  partiellement ouvert (voir plus bas). **Lot 14 : entièrement en attente**,
  zéro ligne de code produite sur ses cinq items depuis sa création
  (voir plus bas — c'est vérifié, pas supposé).
- Un seul jour, le **2026-09-11**, porte à lui seul les Lots 7 (fin), 8, 9,
  10, 11, une bonne partie du 12 et le début du 13 — voir « Le rythme réel »
  ci-dessous. Une session de cette seule journée a coûté, mesuré après coup
  par `ccusage` (Lot 12.1) : **10 936 requêtes API, l'équivalent de 628,47 $**
  de consommation modèle. Le plan entier, étalé sur six jours à un rythme
  loin d'être constant, n'a jamais été chiffré dans son ensemble — un angle
  mort assumé de ce document même, faute d'un point de mesure avant le
  2026-09-11 (Lot 12.1 : « on n'optimise pas ce qu'on ne mesure pas », vrai
  aussi pour ce document rétrospectif lui-même).

## Le séquencement a-t-il tenu ?

Dans l'ensemble, oui, dans sa forme — pas dans son rythme.

L'ordre prescrit par la section « Séquencement recommandé » du plan
(Lot 0 → Lot 1 → {2, 3, 5, 6} en parallèle → Lot 4 → {7, 8, 9, 10} → Lot 11 →
Lot 13, avec le Lot 12 transversal et le Lot 14 hors flux) a été respecté à la
lettre dans sa **structure de dépendances** : rien n'indique que Lot 4 ait
démarré avant que Lots 2/3/5/6 ne soient bien avancés, et Lot 11
(`axiom-checker`) a bien attendu la matrice du Lot 4.1 comme la dépendance
dure l'exigeait.

Ce que le séquencement ne prédisait pas, c'est le **rythme**, mesuré ici pour
la première fois en recoupant les dates de commit plutôt que supposé :

| Fenêtre | Ce qui a été livré |
|---|---|
| 09-07 → 09-08 | Lot 0 (dispositif de documentation) puis Lot 1 (quick wins) |
| 09-08 → 09-09 | Lots 2/3/5/6 démarrent en parallèle, comme prévu |
| **09-10** | **Lot 4 en entier** — les 6 items (4.1 à 4.6), du fuzzing exploratoire à Z3, en une seule journée calendaire |
| 09-10 → 09-11 | Fin du Lot 6, Lot 3 (timeouts & résilience) |
| **09-11** | Fin du Lot 7 (webkit), **Lots 8, 9, 10, 11 en entier**, début du 12 et du 13 |
| 09-11 → 09-12 | Fin du Lot 12, `CODE_AUDIT.md` rejoué (Lot 13) |

Le Lot 4 est présenté dans le plan comme « le lot à plus forte valeur… et le
plus spécifique à ce projet », composé de six items cotés jusqu'à `L`
(preuves formelles Z3, oracle tiers, vérification exhaustive) — l'estimation
d'effort la plus lourde du document. Il a été livré en une journée. Le
2026-09-11 est plus extrême encore : quatre lots entiers (8, 9, 10, 11),
chacun avec plusieurs items `M` et `L`, en 24h. Ce n'est pas que les
estimations `S`/`M`/`L` étaient fausses en soi — le "à faire, en temps humain
posé, une tâche à la fois" qu'elles supposaient implicitement ne correspond
simplement pas au régime réel d'exécution (agent + parallélisation de
sous-agents, cf. Lot 12.4). La bonne lecture des efforts `S`/`M`/`L` de ce
plan n'est donc pas « en jours humains », mais **relative entre items** — ce
qui reste vrai, et pour quoi ils ont réellement servi tout du long (prioriser
Lot 4.3 avant Lot 4.6, par exemple).

## Ce qui a été ajouté en cours de route

Rien de tout ceci n'existait dans la version du plan écrite le 2026-09-07.

**Le Lot 14 lui-même.** Ajouté le **2026-09-11** (commit `7902052`, PR #372,
`docs(plan): add Lot 14 — pay down the debt Lot 6's tools measured`), soit
quatre jours après l'ouverture du plan — mais à peine 17 minutes après le
dernier item réel du Lot 6 (`996769b`, gate de licences, mergé 12:50 UTC ce
même jour ; Lot 14 créé 13:07 UTC) : pas une réflexion après coup distante,
une clôture de boucle immédiate, dans la même session. Sa raison d'être,
dans les mots du commit : le Lot 6 avait délibérément *mesuré* la dette
(basedpyright, refurb/perflint, sonarjs, type-coverage, les deux zones
mortes du 6.5) sans la rembourser en masse, pour rester dans le budget
`S`/`M` annoncé de chaque item. Le Lot 14 existe pour fermer cette boucle —
mais volontairement **hors flux**, sans échéance, « ne bloque rien d'autre,
y compris Lot 13 ».

**Deux vagues de règles `ignore:` Dependabot**, pas une. Le Lot 1 avait
résolu la cascade du 06/09 en groupant les PR par écosystème (`groups:`, PR
#321, 2026-09-08). Mais deux nouveaux blocages amont sont apparus *après*
coup et ont chacun demandé leur propre correctif dédié, tous deux le
2026-09-11 : `fix(ci): stop Dependabot proposing pylint 4.x bumps`
(`2764bc6`) et `fix(ci): stop Dependabot proposing Node-22-blocked frontend
majors` (`fffed4a`, PR #390) — ce dernier retrouve exactement la même classe
de contrainte (« Node 20 vs `^22`») déjà rencontrée et documentée trois fois
séparément ailleurs dans ce plan (`dependency-cruiser` 18.x au Lot 2,
`size-limit` 13.x au Lot 8, `i18next-cli` récent au Lot 7) sans qu'un
mécanisme générique n'ait émergé pour l'anticiper une quatrième fois.

**Un correctif de corpus de fuzzing oublié au premier merge.** L'item atheris
du Lot 9 (PR #383, `db92840`) a d'abord mergé sans committer de fichier de
seed pour le corpus du moteur — corrigé deux commits plus tard,
`dd19dd8`/`dcd1bc8` (PR #387, `fix(ci): commit a seed file for the atheris
engine fuzz corpus`) : un oubli de CI trouvé après coup, pas anticipé par le
plan.

**Au moins deux collisions de numérotation `EXP-*` entre agents parallèles**,
exactement le genre d'accident qu'un dispositif conçu pour capturer
l'expérience honnêtement peut lui-même produire :

1. **`f8d2bcc`** (2026-09-11, « collision EXP corrigée, 6 en-têtes périmés
   marqués ») : un carnet écrit le même matin depuis le worktree **polity**
   a pris le numéro « 002 » — déjà pris sur `develop` par Z3
   (`EXP-002-z3-formal-voting-proofs.md`). `docs/exploration/` numérote
   globalement, pas par branche ; l'agent polity ne le savait pas. Renuméroté
   en EXP-008 côté polity, et la règle (`git ls-tree --name-only
   origin/develop docs/exploration/` avant d'écrire un nouveau numéro) a été
   ajoutée à l'index *a posteriori*, en réaction à l'incident, pas en
   anticipation.
2. **`15a9777`** (« fix stale EXP-012 references, should be EXP-013 ») :
   deux PR du Lot 10 (Prometheus #393, GlitchTip #394) rédigées en parallèle
   ont toutes deux visé le numéro 012 ; celle qui a mergé en second
   (GlitchTip) est devenue EXP-013, laissant deux commentaires de code
   pointant vers le mauvais numéro jusqu'à ce correctif dédié.

Aucun des deux n'est un problème de méthode — les deux carnets sont corrects
sur le fond — mais les deux confirment que numéroter globalement un dossier
partagé entre agents/branches concurrents est un point de friction réel,
observé deux fois indépendamment, pas une fois.

## Ce qui a été reporté ou abandonné, et pourquoi — un rejet argumenté est un succès

Le plan le dit lui-même en toutes lettres dans ses « Règles d'exécution » :
*« Un verdict "rejeté" est un succès du plan, pas un échec. »* Vérifié à
l'usage — les cas suivants le confirment, chacun avec une raison précise
plutôt qu'un simple abandon silencieux.

**WebKit e2e (Lot 7) — reporté deux fois, pour deux raisons différentes, puis
livré.** Premier blocage : `npx playwright install-deps webkit` exige
`sudo`, indisponible pour l'agent dans ce sandbox (cf. la contrainte
« No passwordless sudo » de cet environnement). Décision explicite prise à
ce moment : reporter et enchaîner sur le Lot 8 plutôt que d'attendre —
documentée dans le plan comme un choix, pas un blocage muet. Repris une fois
l'utilisateur lui-même ayant levé le blocage (`sudo env "PATH=$PATH" npx
playwright install-deps webkit`, la forme nue ayant échoué faute d'hériter du
`PATH` géré par `nvm`). Second blocage, complètement différent et non prévu :
une fois les dépendances installées, WebKit plantait à 100 % sur toute
navigation HTTP réelle — diagnostiqué (`DEBUG=pw:browser`) jusqu'à
`WPENetworkProcess: symbol lookup error`, causé par le confinement snap de
VS Code qui court-circuite la résolution de `libpthread` pour tout binaire
GTK/WPE lancé depuis son terminal intégré. Contourné, pas réparé, en testant
dans un conteneur Docker Playwright non confiné (`--network host` vers les
serveurs déjà démarrés sur l'hôte) : 114/114 tests, 59,6 s — preuve que ni
l'app ni la config webkit n'ont de défaut réel, seulement l'environnement de
développement précis de cette machine. Deux causes racines sans rapport
l'une avec l'autre, sur le même item, documentées dans le même paragraphe
daté « 2026-09-11/12 » du plan — le report initial n'a donc pas traîné des
jours, mais l'item a quand même fallu deux diagnostics indépendants avant de
livrer, pas un seul.

**Lot 4.1 (matrice axiomatique) — 2 critères sur 8 explicitement non
tranchés.** Participation et symétrie par renversement ont été **reportés
par leur nom**, pas devinés ni classés par défaut : le plan documente que le
signal réel s'y mélange à du bruit de tie-break qui demande une passe dédiée
par cellule, une discipline directement issue d'une erreur déjà commise et
corrigée *dans ce même item* (une classification sous-échantillonnée, 100-240
profils/cellule, avait classé à tort `ranked_pairs`/`river`/`smith_irv` comme
satisfaisant l'indépendance aux clones — corrigée seulement par le fuzzing
`@given` complet). Le report des deux derniers critères applique la même
prudence à l'avance plutôt que de répéter l'erreur une troisième fois.
L'agent `axiom-checker` du Lot 11, dont l'instruction explicite est de ne
**jamais** proposer un côté satisfait/viole lui-même mais seulement de
signaler « pas encore classé », institutionnalise directement cette leçon.

**Le Lot 6 a fabriqué sa propre dette différée — et cette dette est restée
différée.** Le Lot 6 a délibérément mesuré cinq angles morts de l'analyse
statique (basedpyright : 34 faux positifs restants ; refurb+perflint : 145+85
findings ; type-coverage : 280 `any` réels ; sonarjs : 304 findings restants ;
deux zones mortes trouvées par la couverture runtime) sans les corriger en
masse, dans le budget `S`/`M` annoncé de chaque item — un choix cohérent,
documenté à chaque fois. Le Lot 14 a été créé dans la foulée immédiate
(voir plus haut, ~17 minutes après le dernier item du Lot 6) explicitement
pour rembourser cette dette. Vérifié dans ce document, pas supposé depuis le
cadrage du Lot 14 lui-même : **aucun commit, aucune branche, aucune PR ne
touche à l'un des cinq items du Lot 14** depuis sa création (recherche
exhaustive sur `basedpyright`, `refurb`, `perflint`, `sonarjs`,
`type-coverage` dans l'historique complet des messages de commit — rien
après `7902052`, qui est la création du Lot lui-même, pas un item de travail
dessus). Le Lot 14 est donc, à la date de ce document — le jour même de sa
création —, **entièrement à l'état de plan** — ce qui est cohérent avec son
propre cadrage (« hors flux, aucune échéance ») et n'est donc pas un échec
du plan, mais mérite d'être dit clairement plutôt que supposé réglé du seul
fait qu'il existe, et vaudra la peine d'être revérifié dans quelques
semaines pour voir si « pas d'échéance » a fini par vouloir dire « jamais ».

**`.claudeignore` (Lot 12.2) — confirmé ne pas être un mécanisme réel, écarté
sans hésitation.** Le plan proposait ce fichier comme premier levier contre
la lecture accidentelle d'artefacts générés. Vérifié avant d'écrire quoi que
ce soit : absent de la documentation des permissions de Claude Code, objet
d'une demande upstream toujours ouverte (issue #579), et un fichier
`.claudeignore` posé dans un repo est simplement ignoré sans avertissement.
Écart assumé du plan, remplacé par un hook `PreToolUse` réel — le genre de
correction que seule une vérification directe (pas une confiance dans le nom
du fichier) pouvait produire.

## Quand un rejet a été le bon résultat — la méthodologie du plan, testée sur elle-même

Le principe directeur du plan (« un outil essayé et rejeté avec une raison
précise vaut autant qu'un outil adopté ») ne s'est pas contenté d'être écrit
en préambule : il s'est vérifié en pratique, à répétition, sur des rejets
dont chacun a économisé un vrai coût d'adoption raté :

- **`hypofuzz`** (Lot 9) écarté pour sa licence non-OSI (`LicenseRef-
  HypoFuzz`, usage gratuit restreint au non-commercial) malgré le meilleur
  fit technique sur le papier (réutilisation directe des stratégies
  Hypothesis existantes) — `atheris` (Apache-2.0) adopté à la place, et a
  trouvé 4 bugs réels quand même.
- **`slsa-framework/slsa-github-generator`** (Lot 9) écarté après lecture
  directe de son propre README annonçant ne plus être activement maintenu,
  au profit de `actions/attest-build-provenance`.
- **Lost Pixel** (Lot 7, régression visuelle) écarté sans même être essayé :
  équipe partie chez Figma, dépôt archivé le jour de l'annonce (22/04/2026).
  Playwright natif (`toHaveScreenshot`) adopté, avec un Docker épinglé pour
  la stabilité.
- **`bundlesize`** (Lot 8) écarté pour abandon (dernier publié 2024-03, plus
  de deux ans) ; `size-limit` adopté à sa place.
- **`license-checker`** (Lot 6.7) remplacé par son fork maintenu
  `license-checker-rseidelsohn`, même schéma que `i18next-parser` (Lot 7,
  déprécié officiellement au profit d'`i18next-cli`) et
  `jaegertracing/all-in-one` (Lot 10, image gelée depuis ~9 mois, remplacée
  par `jaegertracing/jaeger:2.20.0`).
- **`zap-api-scan.py`** (Lot 9, DAST) écarté après lecture de sa propre doc :
  il « attempts exploitation » — actif, pas passif — alors que l'item exige
  explicitement zéro payload d'attaque. `zap-baseline.py` (spider
  traditionnel + scan passif) adopté à la place.

Six rejets, six raisons vérifiées de première main (licence lue, dépôt
vérifié `gh api`, doc officielle lue avant d'écrire une ligne de config),
zéro rejeté « par réputation ». C'est exactement la discipline que le plan
prescrit — et elle a produit un résultat mesurable : aucun de ces six outils
n'a eu besoin d'être défait après coup, contrairement à un outil adopté trop
vite qui aurait dû être retiré plus tard.

## Trouvailles non planifiées, plus précieuses que l'item lui-même

Plusieurs items ont trouvé, en cours de route, davantage que ce pour quoi ils
avaient été inscrits au plan :

- **Schemathesis (Lot 3)** : censé combler « le chaînon manquant le plus
  évident du projet » (le contrat OpenAPI jamais vérifié contre
  l'implémentation) — a trouvé et corrigé **6 bugs réels de production**
  avant même d'être mergé (crashs `IndexError`/`TypeError`/`AttributeError`
  sur 5 endpoints distincts, plus des codes d'erreur non documentés sur 7
  routers).
- **`atheris` (Lot 9)** : **4 bugs réels**, dont 3 trouvés par la campagne de
  fuzzing elle-même (bulletin vide faisant planter `calculate_bayesian_
  regret` pour tous les candidats ; `get_nanson_winner`/`get_baldwin_winner`
  plantant sur des bulletins tous vides ; `get_majority_judgment_winner`
  dérivant l'ensemble des candidats du seul premier votant) et un quatrième
  trouvé **en lisant le code avant même d'écrire le harnais** (un JSON à
  ~10⁵ crochets imbriqués fait déborder la pile C du parseur, avant que
  `json.JSONDecodeError` n'ait sa chance) — le carnet documente honnêtement
  qu'une campagne de fuzzing par mutation de bytes n'aurait probablement
  jamais trouvé ce dernier cas seule.
- **L'oracle tiers `pref_voting` (Lot 4.2)** : sur les 21 méthodes ordinales
  comparées à une bibliothèque académique indépendante, **18 sans le moindre
  écart** ; les autres examinées une par une plutôt que comptées en bloc —
  `baldwin` et `raynaud` (bugs réels, corrigés), `smith_irv` (deux bugs
  indépendants dans le même fichier, corrigés), et `dowdall` (le seul écart
  qui n'était **pas** un bug côté Vote-App : imprécision flottante dans
  l'oracle lui-même). La parité à deux implémentations internes ne pouvait
  structurellement pas trouver ces trois bugs-là, puisqu'elle compare deux
  moteurs qui peuvent être faux **ensemble**.
- **Des découvertes « déjà satisfait, rien à construire »**, où vérifier
  avant d'agir a évité du travail redondant : l'a11y sur toutes les routes
  (Lot 7) existait déjà depuis le 2026-08-22, avant même ce plan
  (`assertEverySurfaceAnchored()`, 10/10 tests déjà verts) ; `/code-review
  ultra` (Lot 11) existait déjà, seul un rappel dans `CLAUDE.md` manquait ;
  `minimumReleaseAge` (Lot 9) était déjà dépassé par le `cooldown:
  default-days: 7` de Dependabot, ajouté six semaines plus tôt pour une
  raison sans rapport (un finding Semgrep) ; et le Lot 11 lui-même a corrigé,
  au premier vrai run de son propre agent `doc-drift`, une affirmation fausse
  **dans son propre paragraphe d'ouverture** (« 0 hook » alors que les
  garde-fous graphify existaient déjà à la date du commit qui l'affirmait).

## Leçons de méthode qui reviennent — pas des incidents isolés

Certains schémas se répètent assez souvent dans ce plan pour ne plus être
anecdotiques :

**Vérifier une affirmation de sous-agent avant de la publier a changé un
résultat, pas juste sa formulation, à plusieurs reprises** :

- Le commentaire du Lot 8 affirmait que `pytest-benchmark` « se désactive
  silencieusement » sous `pytest-xdist`. Revérifié en direct (`9e7ffe3`) :
  chaque test **plante** (`AttributeError`), il ne passe pas silencieusement
  sans rien mesurer — la conclusion opérationnelle (exclure le fichier de la
  run `-n auto`) ne changeait pas, mais la raison invoquée était fausse.
- La première version d'EXP-001 (heuristique git-blame) attribuait un défaut
  de l'outil à « le dépôt est trop jeune » — un artefact d'historique
  tronqué. Corrigé (`51ca490`) en rejouant contre le bon PR et en ajoutant
  une seconde leçon transférable : vérifier la profondeur de l'historique
  avant de faire confiance à un outil basé sur `git blame` (mémoire
  utilisateur : « verify git history depth before trusting blame tools » —
  directement née de cet incident).
- `.size-limit.json` étiquetait son budget « (gzip) » alors que l'outil
  mesure en brotli par défaut — corrigé (`be3680c`) après relecture, sans
  changer le chiffre du budget lui-même, seulement son étiquette.
- Un bug de pseudo-locale (padding en un seul bloc plutôt que mot par mot,
  faisant déborder `/decouvrir` de 62px sous Firefox) n'a été trouvé qu'en
  CI, pas en local — fonts différentes.

**Un venv de développement partagé entre agents concurrents sur la même
machine est un vecteur de collision réel, pas hypothétique** : documenté en
détail dans EXP-014 (Lot 10, tracing OpenTelemetry) — installer les versions
demandées par l'item dans le venv `fast_api_voter/.venv` partagé a
immédiatement cassé les épingles `opentelemetry-*` que `semgrep` y avait
posées comme dépendances transitives sans rapport avec ce dépôt. Corrigé en
restaurant les versions d'origine et en construisant un venv jetable dédié à
la vérification — le même réflexe d'isolation que le Lot 4.2 avait déjà
appliqué par précaution (`pref_voting` dans son propre venv Python 3.11, sans
attendre d'incident).

**La numérotation globale d'un dossier partagé entre branches/agents
concurrents est un point de friction réel** — les deux collisions `EXP-*`
détaillées plus haut (`f8d2bcc`, `15a9777`) ne sont pas un hasard isolé mais
la même classe de problème rencontrée deux fois indépendamment, chaque fois
entre deux PR rédigées en parallèle plutôt qu'en séquence stricte.

## Ce que les chiffres disent vraiment

Pas d'adjectifs, les mesures citées par le plan et par `CODE_AUDIT.md`
lui-même :

| Mesure | Avant (2026-09-06/07) | Après (2026-09-11/12) |
|---|---|---|
| Tests backend | 1789 | ≥ 2014 (`2014 passed, 41 skipped`, run complet cité par le Lot 11 le 09-11) |
| Couverture backend (unitaire) | 91 % | 91,56 % (chiffre stable cité par le Lot 6.5) |
| Couverture backend **en usage e2e réel** | jamais mesurée | **34,4 %** (nouveau, Lot 6.5/EXP-003) |
| Couverture frontend en usage e2e réel | jamais mesurée | **63,15 %** (nouveau, Lot 6.5/EXP-003) |
| `vulture` (code mort backend) | 0 | 0 — inchangé malgré le volume de Lots 7-12 |
| `radon` (fonctions complexité C+) | 137 | 137 — inchangé |
| `jscpd` (clones cross-langage) | 33 | 33 — après une régression 33→34 trouvée et corrigée en cours de route (Lot 4.2), puis une seconde vérification identique au 09-12 |
| Bugs réels trouvés par Schemathesis | — | 6 |
| Bugs réels trouvés par `atheris` | — | 4 |
| Bugs réels trouvés par l'oracle tiers (Lot 4.2) | — | 3 méthodes (`baldwin`, `raynaud`, `smith_irv`) — + 5 méthodes en écart réel par la vérification exhaustive du Lot 4.3, + 6 corrections par `fast-check` au Lot 4.4 ; plusieurs méthodes (`smith_irv`, `baldwin`, `raynaud`, `benham`, `condorcet`/Copeland) reviennent d'un item à l'autre, chaque passe trouvant un angle différent sur le même bug ou un bug distinct au même endroit |
| Type-coverage TS | jamais mesuré | 99,58 % (608 `any` implicites, 280 dans du code source réel) |
| Carnets d'expérience clos | 0 | 14 |

La ligne la plus révélatrice est probablement `vulture`/`radon`/`jscpd` :
**strictement stables** malgré six lots entiers de changement (7 à 12) entre
les deux mesures — la discipline "vérifier avant de committer, jamais laisser
la dette dériver silencieusement" a authentiquement tenu sur la durée, ce
n'est pas qu'une formule répétée dans chaque paragraphe "détail". Les deux
seules régressions réelles trouvées en rejouant `CODE_AUDIT.md` (`deptry` et
`knip`, toutes deux issues du Lot 10) ont été corrigées **dans la même passe**
plutôt que laissées pour le Lot 14 — cohérent avec la règle du plan
(« rien de mécanique commité sans vérifier que ça reste vert »), incohérent
avec le sort réservé au reste de la dette du Lot 6 elle-même.

## Ce qui a déçu

Peu de choses, en réalité — la plupart des items notés « adopté partiel » ou
« périmètre réduit » l'ont été par décision assumée, pas par échec :

- **`refurb`/`perflint` (Lot 6.3)** est l'item le plus proche d'une vraie
  déception : 145 + 85 findings mesurés, câblés, documentés — et c'est tout.
  Le plan lui-même le note dès l'écriture : « zéro urgence » pour un item
  déjà coté ⭐ (le plus bas du plan). Ce n'est pas un échec, c'est un item qui
  a rempli exactement le contrat de son étoile unique, ni plus ni moins — et
  qui reste, à la date de ce document, la première ligne non traitée du
  Lot 14.
- **`guarddog` côté npm (Lot 9)** reste, de l'aveu même du carnet,
  « vérifié sur l'interface CLI et le format de sortie uniquement, pas sur un
  run complet réussi dans cette session » — un piège réseau (DNS asynchrone
  résolu hors de `socket.getaddrinfo`) jamais contourné faute de temps,
  documenté honnêtement comme tel plutôt que masqué.
- **Le Lot 12.6** annonçait l'angle de récit « le plus original » du plan
  (chiffrer ce que l'outillage qualité économise en tokens/conversation) —
  jamais chiffré concrètement, resté au milieu d'une phrase d'intention. La
  télémétrie et `ccusage` (Lot 12.1) donnent un coût, jamais un *gain net*
  comparé à un scénario sans le même outillage.
- **La séparation journal/git n'a pas tenu pendant l'exécution la plus
  dense.** `docs/journal/JOURNAL_DE_BORD.md` n'a **aucune entrée** entre le
  2026-09-06 et la date de ce document (vérifié : `grep "^## 2026-09"` ne
  retourne que le 09-06 et le 09-04) — alors que le plan lui-même s'est
  exécuté du 09-07 au 09-12. Le Lot 0 avait prévu `/log-session` comme le
  « récit par session/lot » (étage 2 de son propre dispositif à trois
  étages) ; dans les faits, ce sont les messages de commit et les paragraphes
  « détail » du plan lui-même qui ont porté ce rôle pendant les six jours les
  plus actifs — pas un échec du dispositif (l'information existe, elle est
  même mieux sourcée commit par commit que ne l'aurait été un résumé de
  session), mais un écart réel entre l'intention du Lot 0 et l'usage constaté.

## Bilan

Le plan a survécu au contact, dans un sens précis et vérifiable : sa
**structure de dépendances** a tenu, sa **méthodologie** (vérifier avant
d'adopter, vérifier avant de rejeter, chiffrer avant/après, ne jamais faire
confiance à un détecteur sans l'avoir vu échouer puis réussir) s'est
appliquée avec une régularité mesurable jusqu'au bout — les deux dernières
lignes du tableau du Lot 6 le confirment aussi bien que la première. Ce qui
n'a pas tenu, c'est tout ce qui supposait un rythme régulier ou une exécution
non concurrente : les estimations d'effort en temps humain, la granularité
« une entrée de journal par session », et la numérotation d'un dossier partagé
entre branches. Le plan a aussi produit sa propre dette — le Lot 14 — sans
jamais la rembourser dans la fenêtre de ce document, ce qui n'est ni caché ni
grave (c'est son cadrage explicite), mais mérite d'être dit sans mise en
scène : **rembourser une dette qu'on a soi-même mesurée est visiblement plus
facile à écrire qu'à faire.**

Il reste, à la date de ce document, deux items ouverts dans le Lot 13
lui-même : « Les 3-4 histoires les plus partageables » et « README qui
raconte » — tous deux notés `L`/`M`, tous deux plus proches d'un travail de
mise en récit public que de vérification technique, et donc délibérément
laissés à une session dédiée plutôt que compressés dans celle-ci.
