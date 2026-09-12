# Journal de bord — Vote-App / La Fourmilière

> Une entrée par session de travail significative, la plus récente en
> haut. Objectif : raconter l'histoire du projet au jour le jour — ce qui
> avance, ce qui bloque, les décisions prises — pour soi-même en
> relecture, et pour pouvoir reprendre le contexte facilement dans une
> autre conversation. Rédigé via le sub-agent `journal-writer` (commande
> `/log-session`), toujours en proposition avant application.
>
> **Historique archivé** (Lot 12.2, `PLAN_SOLIDITE_TECHNIQUE.md`) : ce
> fichier ne garde que les entrées écrites en temps réel, pour rester petit
> d'une session à l'autre. L'historique reconstruit rétroactivement (genèse
> du projet en mars 2025 jusqu'à la mise en place de ce journal le
> 2026-08-19) vit dans [`docs/journal/archive/`](./archive/) :
> [`JOURNAL_2026.md`](./archive/JOURNAL_2026.md) (2026-05-03 → 2026-08-19)
> et [`JOURNAL_2025.md`](./archive/JOURNAL_2025.md) (2025-03-01 →
> 2026-01-13).
>
> **Règle de rotation** : quand ce fichier dépasse à nouveau ~100 Ko,
> déplacer ses entrées les plus anciennes vers `archive/JOURNAL_<année>.md`
> (créer le fichier de l'année si besoin) et mettre à jour les liens
> ci-dessus.

---

## 2026-09-06 — Revue de code full-stack en 14 PR, cascade de 13 PR Dependabot, et passe de correction de la documentation

**Contexte du jour.** Suite de la consolidation du 04/09 (worktree Polity prêt,
mais rien avancé dessus depuis). Objectif du jour : une revue de code complète
de `develop` hors périmètre Polity (Polity ne se repère pas par le chemin des
fichiers mais par leur contenu — plusieurs fichiers comme
`fast_api_voter/scripts/*.md` ou `docs/adr/*` vivent sur `develop` sans que
« polity » apparaisse dans leur chemin, et ont donc été exclus de cette passe).
Un préalable, distinct de cette revue : `#272` avait basculé le backend de
Python 3.11 à 3.14 le 05/09 au matin, débloquant une PR Dependabot scipy
bloquée — ce changement s'avérera pertinent plus tard dans la journée.

**Ce qui a avancé**
- **Revue full-stack → 14 PR `feat/*`, toutes mergées sur `develop`** (#279,
  #281, #282, #284, #286, #287, #288, #290, #291, #293, #294, #297, #311,
  #312), couvrant frontend, backend, CI/CD et sécurité :
  - Bornage des schémas `BandwagonRequest`/`MonteCarloRequest`/
    `RealElectionRequest`, jusque-là sans limite sur `num_voters`/`num_rounds`/
    `num_runs` — un risque de DoS sur des endpoints non authentifiés partageant
    un pool de threads (#279).
  - Logging structuré ajouté aux 21 sites de `except Exception` du moteur de
    simulation (zéro appel `log.*` sous `api/domain/` avant), plus un handler
    d'exception global en filet (#281).
  - Rate-limiting de `/api/v2/simulations` et `/api/v2/election` — jusque-là
    sans aucune limite alors que `/api/v1` en avait une. Valeur initiale
    30/min, corrigée à 120/min **dans la même PR** après 2 échecs sur 3 runs
    CI de `playground-strategy.spec.ts` : `profile-simulate` est un appel
    debouncé déclenché à chaque changement de config dans le Playground, pas
    une action explicite, et deux navigateurs Playwright × 25 tests e2e
    dépassaient largement 30/min en usage normal (#284, commits `614238f` puis
    `b30286f`).
  - Bug de thread-safety sur `get_kemeny_young_winner` : le flag
    `was_approx` était stocké sur l'objet fonction sous un commentaire le
    disant thread-local, alors que chaque appel passe par
    `asyncio.to_thread` — extrait en helper pur `kemeny_used_approximation`.
    CORS Socket.IO câblé sur le même `CORS_ORIGINS` que le middleware HTTP, à
    la place d'un `"*"` en dur laissé par un commentaire « à resserrer plus
    tard » jamais suivi d'effet (#282).
  - Suppression de l'arbre mort `voter-app/src/components/Simulation/` :
    16 758 lignes supprimées (confirmé via un script de graphe d'imports
    tracé depuis `src/index.tsx`, pas un simple grep — deux erreurs évitées de
    justesse : trois composants réellement importés par le Laboratoire, et un
    mock global câblé par alias Vitest, invisible pour `tsc`) (#286).
  - Dépendance `react-router-dom` supprimée — le seul import restant
    (`MemoryRouter` dans `Navbar.test.tsx`) est aussi exporté par
    `react-router` v8, déjà le routeur réel de l'app (#287).
  - Erreurs API typées (`ApiError` avec statut + corps préservés sur
    `apiPost`/`apiGet`/`apiDelete`) (#288). Mémoïsation du contexte
    `PlaygroundController` (#290).
  - Navigation clavier ajoutée aux cartes SVG (`LeaderCanvas`,
    `ParliamentCanvas`) — a fait remonter un vrai bug a11y au passage : les
    deux `<svg>` portaient `role="img"` (contenu déclaré non interactif) tout
    en devenant focusables, détecté par la règle `nested-interactive`
    d'axe-core ; corrigé en `role="group"` (#291).
  - Backfill de tests sur `services/{assembly,issues,profile,structural}Api.ts`
    (0 % de couverture avant — exactement la frontière client/serveur que la
    garantie de parité moteur du `CLAUDE.md` suppose surveillée) et sur les
    panneaux Playground les plus faibles (`ReplayStage.tsx` 15→100 %,
    `NonSpatialProfileMap.tsx` 29→100 %, `MethodsMatrix.tsx` 25→100 %) (#293).
  - Côté CI/CD : suppression du workflow redondant `merge-to-main.yml`
    (doublon de `branch-policy.yml`, vérifié non requis et `main` sans
    protection de branche configurée), re-pin de `trivy-action` sur un tag de
    release plutôt qu'un SHA de branche mouvante, ajout de l'écosystème
    `docker` à Dependabot pour les 3 Dockerfiles du repo (#294) ;
    `permissions: contents: read` et `timeout-minutes` ajoutés partout où ils
    manquaient sur les 10 workflows (#297) ; job `image-scan` + génération de
    SBOM (SPDX, via `anchore/sbom-action`) ajouté sur les images Docker
    construites, jusque-là jamais scannées en tant qu'images (#312).
- **Découverte en construisant réellement les images Docker (#312)** : les
  deux Dockerfiles backend (`fast_api_voter/Dockerfile.prod`, `ci-local/` non
  concerné) étaient restés silencieusement sur `python:3.11-slim` depuis la
  migration `#272` — cassés parce que `scipy==1.18.1` (bumpé le même jour)
  exige Python ≥ 3.12. `docker build` échouait net. Corrigé vers
  `python:3.14-slim-bookworm`, build + `curl /api/v2/health` vérifiés
  réellement, pas seulement en lisant le Dockerfile.
- **Cascade de 13 PR Dependabot mergées** (#295, #296, #299–#309), apparues
  automatiquement une fois l'écosystème `docker` ajouté à Dependabot dans
  #294. La protection de branche (« doit être à jour avec `develop` »)
  invalidait chaque PR restante à chaque merge, imposant une boucle
  update-branch → attente CI → merge répétée plutôt qu'un lot en une passe.
  Contrairement à la session du 04/09, l'agent a exécuté directement tous ces
  merges (`gh pr merge`) sans blocage — le classifieur de sécurité qui avait
  forcé l'utilisateur à fusionner lui-même `#255`/`#252`/`#254` ce jour-là ne
  s'est pas manifesté ici.
- **Vérification de clôture** : `ci-local/run-ci.sh all` exécuté contre
  `develop` à jour avant la passe documentation, tous les gates verts —
  Backend CI, Frontend CI, Playwright E2E, Security Audit (1789 tests
  backend, 91 % de couverture, 0 vulnérabilité Trivy, 0 secret Gitleaks),
  documenté directement dans le corps de PR #313.
- **Passe de correction de la documentation, PR #313, mergée** (16 fichiers,
  523 insertions / 335 suppressions) — 4 sous-agents en parallèle, chacun
  vérifiant contre le code réel plutôt que contre les affirmations existantes
  des docs. Corrections notables : `voter-app/README.md` était resté
  intégralement le boilerplate Create-React-App par défaut sur un projet migré
  vers Vite de longue date ; `SECURITY.md` décrivait une authentification JWT
  et des identifiants Postgres qui n'existent pas dans l'app ; `CLAUDE.md`
  annonçait 17 méthodes en parité moteur au lieu des 26 réelles ;
  `docs/research/traceability.md` marquait 8 méthodes comme « prévues » alors
  qu'elles sont déjà implémentées (démocratie liquide, tirage au sort, sondage
  délibératif, chaos de Plott, etc.) ; `ci-local/README.md` décrivait des
  étapes de CI comme non-bloquantes alors qu'elles bloquent réellement.
  `CODE_AUDIT.md` et le plan d'amélioration CI/CD ont été re-datés avec les
  chiffres du jour (recalcul vulture/knip/jscpd/radon) plutôt que réécrits,
  pour rester une trace historique utile de ce qui a été corrigé depuis.

**Points bloquants**
- Le classifieur de sécurité qui bloquait `gh pr merge` pour l'agent le 04/09
  ne s'est pas déclenché aujourd'hui — tous les merges de la session (14 PR de
  revue, 13 PR Dependabot, PR doc) ont été exécutés directement par l'agent.
  À confirmer si c'est un changement durable de configuration ou une
  variation ponctuelle.
- Deux échecs CI apparents pendant la cascade Dependabot (Dependency Review
  « fetch failed », Playwright E2E) se sont révélés être des faux positifs sur
  des commits déjà rendus obsolètes par le cycle d'update-branch suivant — pas
  un vrai problème, mais un bruit qui a ralenti la boucle de merge et qu'il a
  fallu diagnostiquer à chaque occurrence plutôt que réflexivement ignorer.
- Deux vrais bugs (rate-limit à 30/min cassant l'usage normal du Playground,
  Dockerfiles muets sur Python 3.11) n'ont été découverts qu'en exécutant
  réellement le code concerné (CI e2e, `docker build`) — aucun des deux
  n'était visible à la seule lecture du diff. Reste un signal à prendre au
  sérieux : la revue statique seule ne suffit pas sur ce genre de changement.

**Décisions prises**
- Exécuter la revue de code en 14 PR séquentielles plutôt qu'un gros commit —
  *pourquoi* : chaque correction est indépendamment vérifiable (tests, mypy,
  lint) et review-able, cohérent avec le workflow `feat/*` déjà mandaté par
  `CLAUDE.md`.
- Corriger le rate-limit `/api/v2/*` à 120/min plutôt que garder 30/min ou
  désactiver la limite — *pourquoi* : 120/min borne toujours un abus réel
  (un attaquant envoyant des centaines de requêtes/s ne voit pas la
  différence entre 30 et 120) tout en laissant l'usage interactif normal du
  Playground respirer.
- Rendre le job `image-scan` non-bloquant pour l'instant et scopé à
  `schedule` + `push: develop` (jamais sur PR) — *pourquoi* : un premier run
  ferait remonter des CVE de base d'image essentiellement à la charge de
  l'amont, pas quelque chose qu'une seule PR peut corriger, et bloquer
  immédiatement gèlerait `develop` indéfiniment (même logique déjà appliquée
  au job `trivy` sur système de fichiers).
- Re-dater `CODE_AUDIT.md` et le plan d'amélioration CI/CD plutôt que les
  réécrire — *pourquoi* : ce sont des documents d'audit ponctuels, les garder
  comme trace historique de ce qui a été corrigé depuis leur reste plus utile
  qu'un lissage qui effacerait l'historique du diagnostic initial.
- Exclure les fichiers Polity de la passe documentation par leur contenu et
  non leur chemin — *pourquoi* : plusieurs fichiers Polity (`fast_api_voter/
  scripts/*.md`, `docs/adr/*`) vivent sur `develop` sans que « polity »
  apparaisse dans leur chemin ; un filtrage par chemin les aurait traités par
  erreur.

**Prochaines étapes**
- [ ] Pas de tâche précise en attente à ce stade — la session s'est terminée
      sur la passe de documentation (PR #313), en attente de la prochaine
      demande de l'utilisateur.
- [ ] Reprendre le projet Polity depuis le worktree `~/Vote-App-polity` reste
      ouvert depuis le 04/09 — toujours rien avancé dessus.
- [ ] Surveiller le premier run réel du job `image-scan` (#312) sur `push:
      develop` — non gating pour l'instant, mais à regarder pour d'éventuelles
      CVE de base d'image à traiter.

**Pour aller plus loin** : PR #279, #281, #282, #284, #286, #287, #288, #290,
#291, #293, #294, #297, #311, #312 (revue de code), #295–#309 (cascade
Dependabot), #313 (documentation) ; commits `614238f`/`b30286f` (rate-limit) ;
`CODE_AUDIT.md` (re-daté 2026-09-06) ; `CLAUDE.md` (parité moteur corrigée à
26 méthodes) ; `docs/research/traceability.md`.

---

## 2026-09-04 — Consolidation post-migration Ubuntu : trois PR de docs/outillage triées et fusionnées, projet Polity prêt à être repris (mais rien avancé dessus)

**Contexte du jour.** Reprise du projet après la migration Windows/WSL2 → Ubuntu
native. Trois PR ouvertes contenaient des documents qui n'existaient jusque-là
que sur la machine Windows : `#252` (`chore/track-local-docs`, base `develop`),
`#254` (`chore/portable-workspace-ubuntu`, base `polity`) et `#253`
(`chore/ci-dependabot-metadata`, base `develop`, sans rapport avec la
migration). Objectif du jour : trancher le chevauchement entre `#252` et `#254`
et fusionner ce qui doit l'être pour pouvoir reprendre le travail sur Polity.

**Ce qui a avancé**
- Règle de répartition tranchée avec l'utilisateur : l'outillage journal
  (agent `journal-writer` + commande `/log-session`) est générique et doit
  vivre sur `develop` ; tout ce qui est spécifique à Polity reste sur la
  branche `polity`.
- Extraction de cet outillage en une PR dédiée, `#255`
  (`chore/claude-journal-tooling`, base `develop`), avec les règles
  `.gitignore` correspondantes — mergée dans `develop`.
- `#252` élaguée : les 5 docs polity-spécifiques
  (`DEMARRAGE-polity-v0.md`, `polity-simulation-design-v2.md`,
  `dev-plan-v0-worktree.md`, `audit-precision-plan.md`,
  `prompt-liquid-democracy-conviction-voting.md`) retirés, lignes `.gitignore`
  correspondantes restaurées — force-push, puis mergée dans `develop`
  (commit `eb26deb`).
- `develop` fusionné dans `polity` (sync de routine, cohérent avec
  l'historique de la branche qui l'a déjà fait des dizaines de fois).
- `#254` rebasée sur le nouveau tip de `polity` : conflit sur `.gitignore`
  résolu à la main (règles `.claude/agents`/`.claude/commands` devenues
  redondantes retirées, lignes d'ignore des 5 docs polity transformées en
  commentaires pour qu'ils restent versionnés sur cette branche) —
  force-push, puis mergée dans `polity` (commit `d7ecc51`) : `docs/claude-memory/`
  (24 fichiers), `polity-simulation-design-v2.md`, l'enquête `pressure_action`
  et un commit `wip` de travail non commité sur Windows sont maintenant
  disponibles côté Linux.
- Worktree `~/Vote-App-polity` créé (`git worktree add -b polity
  ../Vote-App-polity origin/polity`), conforme à la convention déjà
  documentée dans `dev-plan-v0-worktree.md`.
- Instantané `docs/claude-memory/` restauré dans son propre espace mémoire
  Claude Code (`~/.claude/projects/-home-burbanit0-Vote-App-polity/memory/`,
  distinct de celui du repo principal), suivant la procédure de
  `docs/claude-memory/README.md`.
- Mémoire Claude Code du repo principal mise à jour (deux nouveaux souvenirs :
  consolidation du jour, règle de répartition develop/polity).

**Points bloquants**
- Le classifieur de sécurité de l'environnement bloque l'action `gh pr merge`
  pour l'agent : chaque fusion de PR (`#255`, `#252`, `#254`) a dû être
  exécutée par l'utilisateur lui-même, pas par l'agent.
- Obsidian : le vault était enraciné sur le repo principal `Vote-App` ; le
  nouveau worktree `Vote-App-polity` est un répertoire séparé sans config
  `.obsidian/` propre. Pas automatisable depuis l'agent — l'utilisateur doit
  l'ouvrir lui-même comme vault (ou vault lié) dans l'interface Obsidian.
- `#253` (labels Dependabot + `pip-audit` bloquant en CI) reste ouverte,
  intacte, non traitée : son propre corps de PR prévient que le flip
  `pip-audit` fera passer la CI backend au rouge tant que `fastapi` n'est pas
  mis à jour. Décision à prendre séparément (accepter le rouge, scinder le
  commit, ou l'accompagner du bump `fastapi`).

**Décisions prises**
- Partager l'outillage journal sur `develop` plutôt que de le laisser
  dépendre de `polity` — *pourquoi* : il n'est pas spécifique à Polity et
  alimente `docs/journal/`, déjà versionné sur `develop`.
- Garder tout le reste (docs de conception, enquêtes, checklists) spécifique
  à `polity` plutôt que de le dupliquer sur `develop` — *pourquoi* : consigne
  explicite de l'utilisateur pour éviter la redondance entre les deux
  branches à mesure que le projet Polity avance.
- Laisser `#253` de côté pour cette session — *pourquoi* : sans rapport avec
  la migration, et son impact (CI rouge) mérite une décision séparée plutôt
  qu'un arbitrage rapide en fin de session.

**Prochaines étapes**
- [ ] Ouvrir `~/Vote-App-polity` comme vault Obsidian (ou vault lié) pour
      retrouver l'accès au journal et aux docs depuis l'interface.
- [ ] Trancher le sort de `#253` (accepter la CI rouge, scinder le commit
      pip-audit, ou l'accompagner du bump `fastapi`).
- [ ] Reprendre effectivement le contenu du projet Polity depuis le worktree
      `~/Vote-App-polity` — rien n'a avancé sur ce plan aujourd'hui, la
      session était uniquement de la consolidation d'infrastructure.

**Pour aller plus loin** : PR `#255`, `#252` (élaguée), `#254` (rebasée) ;
commits `eb26deb`, `d7ecc51` ; `docs/claude-memory/README.md` ;
`dev-plan-v0-worktree.md`.

---

## 2026-08-29 (après-midi) — La calibration d'ambition tranchée à 0,30, deux erreurs de vérification corrigées en route, et un flake E2E qui bloque désormais le merge

**Contexte du jour.** Suite directe du matin même (commit `218d1d6`, moitié
visibilité d'ADR-002 livrée) : exécution de `plan-calibration-ambition.md`,
la moitié restante — trancher pourquoi la configuration livrée
(`ambition_threshold=0.7`, `ambition_dist=beta(2,8)`,
`rupture_path_enabled=false`) ne produit jamais de candidat, et quoi
corriger.

**Ce qui a avancé**
- **Phase 1 — la piste « `rupture_path_enabled` était l'accident » testée et écartée.** Sonde déterministe, 40 graines, pipeline réel, durée livrée (320 élections), 3 bras. Bras livré : 312/320 élections à champ candidat vide (reproduit exactement ADR-002). Bras rupture activée seule : 212 élections avec vainqueur mais **86 (26,9 %) toujours sans aucun candidat**. Écartée sur trois motifs : elle remplace le chemin dominant plutôt que le restaurer (476 déclarations de rupture contre 8 dominantes, nomination de parti inerte sur 312/320 élections) ; 58,8 % des élections ont zéro ou un candidat ; et l'hypothèse de coût du plan était **fausse, vérifiée pas supposée** — la piste casse les **mêmes 7 tests** que les options de calibration, parce que la preuve de byte-identité dépend de `nominees == []`, pas d'`ambition_threshold`.
- Le critère pré-enregistré du §2.2 comptait en « runs » ; le bras rupture atteint 100 % des runs tout en laissant 26,9 % des élections vides. **Unité corrigée en « élection » avant tout sweep.**
- **Découverte latérale → ADR-003.** `rupture_signature_ratio: 0.005` ne rejette structurellement personne à n=100 : `sympathizer_ratio` compte le citoyen lui-même, donc le ratio plancher à `1/n = 0,01`. Mesuré : 477 495 tirages, 476 succès au pile-ou-face, 476 passages du seuil, **zéro rejet**. L'inertie s'inverse au-dessus de n=200 — à l'échelle v3 (1000 citoyens, déjà sur la feuille de route) le filtre deviendrait vivant sans prévenir. `independent_signature_ratio` est par ailleurs parsé, validé, et lu par aucun code de domaine.
- **Coût de migration mesuré avant d'implémenter** : 7 tests dépendaient du défaut, pas les 4 annoncés par ADR-002 — dont une **seconde** preuve de byte-identité non identifiée (`test_events_enabled_but_structurally_inert_...`), qui cassait à 64 lignes contre 1485 parce que son bras « off » n'activait pas `awakening` comme son bras « on » : elle ne passait que grâce à la présidence perpétuellement vacante.
- **Une quatrième option, absente d'ADR-002.** §2.4 définit le chemin dominant comme `ambition_score` **et** le soutien social perçu franchissant un seuil combiné ; `decide_candidacy` ne teste que le premier terme. Le code le dit lui-même ailleurs : `decide_candidacies` (LLM) se décrit comme le remplacement du « bare ambition_score threshold » et alimente le modèle avec les deux signaux.
- **Erreur de méthode corrigée en cours de route.** La première vérification RNG de l'option 4 comparait `bare @0.7` à `combiné @0.7` et concluait « coût RNG nul » — vérification vide : aux deux règles le pool est vide, les deux runs sont le même run, même classe d'erreur que le postulat de coût de la Phase 1. Refaite sur des bras à pools réellement différents, en comparant option 4 à option 2 plutôt qu'au statu quo cassé, sur l'état final du bit generator plutôt que le nombre d'appels. Conclusion solide : flux `population`/`parties` identiques dans tous les bras ; seul `rupture_rng` bouge, identiquement pour options 2, 4 et le contournement 0.0 ; option 4 contre option 2 au même seuil : aucun flux ne diffère.
- **Sweep contre le critère pré-enregistré** : trois bras passent (`bare @0,25`, `bare @0,30`, `combiné @0,45`), tous reproduits sur le bloc de graines indépendant 41..80. L'option 4 seule ne suffit pas : au seuil livré 0,7 elle laisse encore 304/320 élections vides (contre 312), une moyenne comprimant au lieu de translater. Le critère ne départage pas les deux règles.
- **Mesure discriminante ajoutée pour ne pas décider à l'aveugle** : la règle combinée ne déplace le soutien moyen des nominees que de +0,018 (~3 %), parce que `select_party_nominee` prend l'argmax sur `ambition_score` et lave l'effet. La revendication de fond de §2.4 est bloquée en aval par le critère de nomination (§10.10), pas par `decide_candidacy`.
- **Décision (utilisateur) : option 2, `ambition_threshold` 0.7 → 0.30**, valeur dérivée non ajustée (§2.3 exige ≥ 2 éligibles/parti → plancher 10 %, plafond ~40 %). Mesuré à 0.30 : 20,0 % d'éligibles, 4,0 prétendants/parti, 0/320 élection vide, 100 % avec ≥ 4 partis. Option 4 reportée et explicitement groupée avec §10.10.
- **Implémenté** : les deux preuves de byte-identité reconstruites sur `institutions.president_term_limit: 0` (champ candidat vide par construction, à chaque tick, pour chaque graine, indépendamment de tout tirage) ; bras « off » du test events corrigé ; 2 nouveaux garde-fous. Suite verte à 1776 tests (1774 avant). ADR-002 fermé, `THEORY.md` corrigé, ADR-003 ouvert. Commit `8470bf3`.
- **Recadrage de l'utilisateur** : la checklist v3 avait été écrite dans `polity-simulation-design-v2.md` §11.1 — fichier gitignoré ; refus explicite qu'elle reste locale. En la déplaçant, découverte que `docs/v3-readiness-checklist.md` est **aussi** ignoré (`.gitignore` exclut `/docs/*`, ne réinclut que `/docs/adr/` et `/docs/journal/`) — premier commit échoué là-dessus. Atterrie dans `docs/adr/v3-readiness-checklist.md`, avec audit des 27 paramètres en ratio (exactement 2 concernés) et trois autres classes de sensibilité à l'échelle — dont la dérivation de l'`ambition_threshold` qui venait d'être posée (à n=1000, ~40 prétendants/parti au lieu de 4, l'arbitrage de nomination change de nature). Commit `c72c4e5`.
- **Deux flakes documentés en issues plutôt que laissés sans trace** : #217 (backend, `TestShyVoter::test_rejects_num_polls_above_30`, échec unique non reproductible en 3 relances complètes, hypothèse rate-limiting vérifiée et fausse, diagnostic non établi) et #218 (E2E, `playground-method.spec.ts`, garde-fou anti-flaky ; run précédent sur la même branche vert et commit fautif ne touchant que deux fichiers Markdown — donc non causé par la branche).

**Points bloquants**
- #218 laisse la PR #216 en `MERGEABLE / UNSTABLE` — tous les autres checks sont verts, seul le garde-fou anti-flaky E2E échoue, sans lien apparent avec cette branche. Pas un blocage dur (`MERGEABLE`), laissé volontairement pour une session dédiée plutôt que d'ouvrir un chantier E2E frontend au milieu de la calibration polity.
- #217 reste non diagnostiqué et non reproductible — faible urgence, mais sans explication.
- ADR-003 reste ouvert : trois correctifs candidats nommés, aucun choisi.
- Le re-baseline des scripts d'acceptance (qui gardent tous `ambition_threshold=0.0` par continuité) n'a pas démarré ; aucun critère écrit pour distinguer un changement de conclusion qualitative d'un simple changement de chiffre avant d'engager le run LLM (~6500s).
- Option 4 (§2.4) et le critère de nomination §10.10 restent groupés mais non traités ensemble.

**Décisions prises**
- Écarter la piste `rupture_path_enabled` malgré son coût apparemment nul — *pourquoi* : elle remplace le chemin dominant au lieu de le restaurer et casse le même nombre de tests que les options de calibration, donc n'offre aucun avantage réel.
- Corriger l'unité du critère pré-enregistré de « run » à « élection » avant tout sweep — *pourquoi* : un critère en runs aurait laissé passer le bras rupture à 100 % alors que 26,9 % de ses élections étaient vides, il était aveugle au problème qu'il devait mesurer.
- Refaire la vérification RNG de l'option 4 sur des bras à pools réellement différents plutôt que garder la première mesure — *pourquoi* : la première comparaison ne testait rien (pool vide des deux côtés), même classe d'erreur que le postulat de coût de la Phase 1.
- Retenir l'option 2 (`ambition_threshold` 0.30) et reporter l'option 4 — *pourquoi* : le critère empirique ne départage pas les deux règles, et la mesure discriminante montre que l'option 4 seule ne change presque rien (+0,018 de soutien) tant que le critère de nomination (§10.10) n'est pas rouvert.
- Reconstruire les preuves de byte-identité sur `institutions.president_term_limit: 0` plutôt que sur un autre contournement — *pourquoi* : mécanisme exact (champ vide par construction) plutôt que distributionnel, plus robuste à toute future recalibration.
- Déplacer la checklist v3 dans `docs/adr/` plutôt que la laisser dans le fichier gitignoré — *pourquoi* : consigne explicite de l'utilisateur, un document que personne ne peut lire ne remplit pas sa fonction, même logique déjà appliquée aux ADR et au journal.
- Documenter les deux flakes en issues séparées plutôt que relancer silencieusement le CI — *pourquoi* : consigne du garde-fou anti-flaky lui-même (« a flaky test is a broken test »), et convention déjà établie sur ce projet de ne rien laisser sans trace.
- Laisser #218 (flake E2E) pour une session dédiée plutôt que le traiter dans la foulée — *pourquoi* : déjà bien caractérisé comme non lié à cette branche (run précédent vert, commit fautif ne touchant que du Markdown), la PR reste `MERGEABLE`, et mélanger un chantier E2E frontend avec la fin de la calibration polity romprait le périmètre maintenu tout du long.

**Prochaines étapes**
- [ ] Merger la PR #216 (pas de blocage dur ; #218 peut être traité séparément).
- [ ] Corriger ADR-003, en vérifiant que le correctif ne change **rien** à n=100 — pas seulement qu'il retire le basculement à n=1000.
- [ ] Re-baseline déterministe des résultats publiés : écrire avant le sweep le critère distinguant « change une conclusion qualitative » de « change juste un chiffre », pour trancher d'avance la décision d'engager le run LLM (~6500s).
- [ ] Restent ouverts sans urgence : §10.10 + option 4 ensemble (critère de nomination), et le flake #217, et le flake E2E #218 (session dédiée).

**Pour aller plus loin** : `plan-calibration-ambition.md` (protocole complet, §1.1 piste rupture, §2.1bis-2.4 option 4 et sweep, §3.1 coût de migration), `docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md` (calibration tranchée), `docs/adr/ADR-003-ballot-access-filter-is-inert.md` (filtre inerte, décision reportée), `docs/adr/v3-readiness-checklist.md` (audit des 27 paramètres en ratio, 4 classes de sensibilité à l'échelle), `THEORY.md` §10.10, PR #216, issues #217 et #218, commits `8470bf3` et `c72c4e5`.

---

## 2026-08-29 — Le chantier distribution se referme, et découvre en sortant que la configuration livrée ne peut pas tenir d'élection

**Contexte du jour.** Suite directe de l'entrée du 24/08 : la chaîne causale seed=42 était fermée (positions `uniform` + priorités individualisées favorisent structurellement le Blanc au second tour), mais la décision de corriger restait entièrement ouverte, et la réécriture de `THEORY.md` §10.10 non commitée. Objectif de la période : trancher et implémenter le correctif, le faire vivre sous charge LLM réelle, et fermer le chantier distribution proprement.

**Ce qui a avancé**
- **Phases 1 à 4 du plan (`plan-distribution-positions-seeds.md`), exécutées dans l'ordre prescrit.** Phase 1 : décision théorique écrite *avant* tout chiffre de sweep — structure factorielle à bas rang à 2 facteurs (`factor_structure`) retenue contre une gaussienne simple (ne corrèle pas les 20 dimensions) et contre un mélange gaussien (présupposerait la polarisation que la vue méso existe pour observer) ; `n_factors=2` reprend les axes économique/sociétal déjà nommés au §14.2 du plan de conception. Phase 2 (`918377e`) : implémentée en opt-in, sweep 40 graines contre le vrai `generate_population` — 0/40 victoires du Blanc, corrélation inter-dimensions réaliste (0,539), variance seed-à-seed préservée. Phase 3 (`a3ebfa9`) : bascule du défaut livré ; découverte non anticipée que plusieurs tests dépendaient implicitement de `uniform` (séquence RNG de v4 Lot 2, seuils calibrés empiriquement pour la porte d'éveil/mobilisation/pétition) — épinglés explicitement sur `uniform` plutôt que corrigés en masse. Phase 4 (`98dbdd3`) : quatre sondes déterministes bon marché rejouant les configurations déjà publiées (both, mobilization_only, electoral_only, v6b) → décision de ne pas relancer les bras LLM au complet, le signal déterministe restant suggestif mais pas conclusif.
- **Le run d'acceptance v6b sous le nouveau défaut a échoué deux fois avant d'aboutir**, sur `cast_votes` (dt=1), troncature `finish_reason='length'` au budget exact (13 596 tokens = 1596 + allowance 12000). Diagnostiqué au niveau de la réponse brute, pas par inférence : la règle du prompt (« classe les positions des candidats acceptables du plus proche au plus éloigné ») est ambiguë entre « classer tous les acceptables » et « classer, c'est-à-dire choisir, le plus proche » — le modèle trouve la bonne réponse en ~1500 caractères puis boucle ~62 000 caractères à re-citer la règle sans jamais émettre de JSON (Mode A, pas Mode B : le budget avait déjà grimpé 4000→8000→12000, une cinquième valeur n'aurait fait que déplacer le plafond). `factor_structure` ne crée pas l'ambiguïté, elle augmente la fréquence de la condition qui la déclenche : la part d'électeurs à ≥2 candidats acceptables passe de 62 % à 88 %.
- **Correctif implémenté et vérifié en direct** (`13e4a14`) : une phrase explicite imposant que `ranking` porte *chaque* candidat acceptable, jamais le seul plus proche. Testé en stress sur les 4 électeurs les plus difficiles identifiés (25 appels, 0 boucle) avant de relancer le run complet.
- **Piège d'outillage réel découvert et documenté à part** (README `llm_test_harness`) : l'endpoint `/v1` d'Ollama renvoie le contenu `<think>` dans `message.reasoning`, un champ séparé de `message.content`, que ni `_extract_content` ni `_extract_native_content` ne lisent — les deux lèvent sur `finish_reason` avant même de regarder le message. Une exception de troncature ne porte donc aucun raisonnement ; toute future investigation de ce type doit dumper le corps JSON entier.
- **Le run complet a confirmé, honnêtement, que le fix n'est pas la cause unique** : sur ~1822 appels, 11 troncatures (0,6 %, contre 6-7 % estimé au diagnostic), toutes absorbées au premier retry — mais 2 sur 11 tombent sur `chamber_deliberation` (dt=11), un prompt jamais touché par ce fix et sans notion de `ranking`. Le plancher de troncature résiduel reste donc réel, non diagnostiqué (Mode A ou B inconnu). Le fallback `build_ranking` (§2.3 du plan) a été scopé par écrit — déclenchement uniquement sur épuisement des retries, périmètre limité au seul électeur en échec, marqueur de source obligatoire — mais délibérément non implémenté : à 0,6 % totalement absorbé, mélanger deux sources de bulletin dans un même run coûte plus qu'il ne rapporte.
- **Run `both` sous `factor_structure` : invalide selon son propre critère pré-enregistré** — `office_occupancy=0,333` contre un seuil de 0,70. Résultat scientifique conservé quand même (§4.2 du plan) : première comparaison like-for-like sonde/LLM — la sonde déterministe annonçait 63,6 %, le bras LLM en produit 33,3 %, surestimation d'un facteur ~2 sur une quantité continue, alors qu'elle était juste sur le compte de rappels (2 dans les deux cas).
- **Run `electoral_only` relancé et franchit le critère** (`efffdca`) : `office_occupancy=1,0`, zéro rappel, `L` plate à `m` par mandat. Comparaison v6b enfin calculable : président élu 0,0479 moyenne / 0,1702 max (écrêté) contre chambre strictement immobile (0,000000 sur 990 délibérations) — troisième confirmation indépendante de la cécité de `top_k_priorities`, et première fois que le chiffre corrigé est journalisé en bande par du code de production (`clamped_at_bound`, 8 événements, 4 tombant exactement dans le plateau de la série).
- Mais réserve explicite posée avant même de citer les chiffres : n=2 présidents au comportement opposé (l'un concède 13/16, l'autre 16/16 silencieux) et pas des positions de départ comparables. Vérifié contre la population régénérée : le second président est un quasi-centriste (7e plus proche du centre de masse sur 100, 15 mécontents contre 29 pour le premier) — sa dérive nulle est un cas de « rien à concéder », pas une résistance démontrée. Résultat le plus inattendu du run : `inaction_rate` vaut exactement 1,0 sur tous les ticks 0-15, et le président concède quand même 13 fois — la dérive n'est pas une réponse à la pression, il n'y en avait aucune.
- Bug réel corrigé au passage dans `run_v6b_acceptance.py` : l'en-tête de `summarize()` codait en dur « full pressure menu », contredisant la ligne suivante sur un répertoire `electoral_only` — rendu conditionnel au menu, les cinq répertoires de runs existants re-rendus sans erreur.
- **Chantier distribution fermé** (`dc91f5f`) : les caveats déjà posés sur §10.7/§10.8 ne couvraient que la chronologie de fiabilité GPU (bug 4), pas le fait que ces runs tiraient leur population sous `uniform`/seed=42 — corrigé aux trois endroits où la promesse de non-rétroactivité avait été faite (§10.10, le YAML, `traceability.md`) sans jamais être honorée à l'usage. Écart trouvé au passage : la ligne `uniform` du tableau §2.1 (11/40, 27,5 %) n'est pas reproductible contre le critère de nominee réellement livré — trois blocs de 40 graines donnent 70,0/75,0/67,5 %, c'est la variante centroïde qui était mesurée, mal étiquetée. La décision de Phase 2 n'est pas affectée (la marge réelle est ~2,5× plus large), annoté à trois endroits plutôt que corrigé en douce.
- **En vérifiant le §3 du plan resté ouvert (« `ambition_threshold=0.0` : à vérifier empiriquement »), découverte que l'hypothèse est fausse dans l'autre sens.** Sonde déterministe, 40 graines, 4 cellules : au seuil livré `ambition_threshold=0.7` avec `ambition_dist: beta(2,8)`, seuls 0,03 citoyen sur 100 est éligible — 39 graines sur 40 ne produisent **aucun** candidat, identique sous `uniform` et `factor_structure`. Le blocage est le couple (ambition_dist, ambition_threshold), orthogonal aux positions, et `rupture_path_enabled: false` fait de `decide_candidacy` le seul chemin de candidature — pas de voie de secours. Conséquence : aucun résultat publié (§10.4 à §10.9) n'a jamais exercé la valeur livrée ; les cinq scripts d'acceptance la contournent tous silencieusement via `dataclasses.replace`.
- Sorti en **ADR-002** (`docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md`, `dc91f5f` puis affiné `c2d68d7`), statut « Open — problem named and measured, decision deliberately deferred », sur demande explicite de ne pas noyer ce constat dans les limites de fin de section.
- Rebase de la branche sur `develop` (qui avait avancé de 57 commits — CI, dépendances, refactors et tests) sans conflit, PR précédente #188 déjà mergée entretemps → nouvelle branche `fix/polity-cast-votes-ranking-ambiguity`, **PR #216 ouverte contre `develop`**. Suite complète verte après rebase : 1767 passés, 41 ignorés, couverture 91,17 % ; `flake8`/`mypy --strict` propres.

**Points bloquants**
- Le plancher de troncature de `chamber_deliberation` (2 puis 3 occurrences sur deux runs indépendants) n'a jamais été diagnostiqué — Mode A ou Mode B inconnu, seul défaut connu encore actif.
- Le run `both` sous `factor_structure` reste invalide selon son propre critère et n'est délibérément pas rejoué.
- **La configuration livrée ne peut pas tenir d'élection dans l'écrasante majorité des cas, et rien ne le signale.** Un run aux défauts livrés produit zéro candidat, zéro élection, aucune erreur, aucun avertissement — il se termine « avec succès » sans contenir la moindre démocratie. C'est le constat central d'ADR-002, laissé volontairement sans décision de correctif (calibrer `ambition_dist`, baisser `ambition_threshold`, les deux, ou vérifier si `rupture_path_enabled: false` était l'accident réel) — choisir un correctif est un jugement de modélisation et une décision de re-baseline, pas un effet de bord de fermeture de ce chantier.
- Tout reste à n=1 graine sur les bras LLM ; le multi-graines coûterait ~4h par run. La comparaison v6b n=2 présidents reste une réserve non levée, plutôt durcie par la vérification faite.
- L'hypothèse « sonde fiable sur les quantités mécaniques, optimiste sur celles qui dépendent de l'arbitrage citoyen » reste une hypothèse de travail consolidée par un seul cas favorable (presque tautologique par sa propre clause), pas une règle établie — à ne pas citer ailleurs comme acquise.
- `traceability.md` (autre worktree, gitignoré) mis à jour localement, non commitable depuis ce dépôt.
- La justification théorique de `factor_structure` vit dans le bullet §10.10 « Limites connues » plutôt que dans une section méthodologique dédiée — rangement volontairement laissé de côté.

**Décisions prises**
- Retenir `factor_structure` (structure factorielle unimodale à 2 facteurs) plutôt qu'un mélange gaussien — *pourquoi* : un mélange présupposerait la polarisation que la vue méso du projet existe justement pour observer, contrairement à une structure unimodale qui corrèle les dimensions sans imposer de modes.
- Ne pas relancer les bras LLM complets en Phase 4 — *pourquoi* : les quatre sondes déterministes montrent une hausse cohérente de l'acceptabilité partout, avec rappels et propriété de contrôle `electoral_only` inchangés ; le coût (heures de calcul par bras) n'était pas justifié pour confirmer un résultat déjà probable, la réouverture reste possible mais différée.
- Corriger l'ambiguïté du prompt `cast_votes` plutôt que d'augmenter encore le budget de tokens — *pourquoi* : la troncature n'était pas un problème de budget insuffisant (déjà escaladé trois fois) mais un problème de convergence, une règle ambiguë que le modèle ne pouvait pas résoudre seul.
- Scoper par écrit le fallback `build_ranking` sans l'implémenter — *pourquoi* : consigne explicite de ne pas conclure trop vite que le fallback n'a pas de raison d'être (2 troncatures sur `chamber_deliberation` restent hors du périmètre du fix) ; mais à 0,6 % totalement absorbé, l'implémenter tout de suite coûterait plus (deux sources de bulletin à distinguer) qu'il ne rapporte.
- Documenter le run `both` comme invalide plutôt que de le présenter avec des réserves — *pourquoi* : il manque son propre critère pré-enregistré (0,333 contre 0,70), la seule position honnête est l'invalidité, pas une nuance.
- Sortir ADR-002 en document séparé plutôt qu'en bullet de fin de section — *pourquoi* : le problème (aucune élection possible aux valeurs livrées, silencieusement) est structurellement plus grave que les limites habituellement listées en §10.10 et mérite sa propre traçabilité de décision.
- Prioriser explicitement le garde-fou contre l'échec silencieux avant la question de calibration `ambition_dist`/`ambition_threshold` — *pourquoi* : une valeur mal calibrée reste détectable en observant les résultats, alors qu'un mécanisme qui dégénère silencieusement rend un run d'apparence propre sans le moindre indice qu'il manque quelque chose ; c'est aussi l'option la moins coûteuse des deux, sans décision de re-baseline ni changement d'ordre RNG.
- Ne pas corriger silencieusement l'étiquette erronée du tableau §2.1 (ligne `uniform` mesurée avec la variante centroïde) — *pourquoi* : annoter l'écart à trois endroits préserve la trace de ce qui a réellement été mesuré, même quand la décision finale n'en est pas affectée.

**Prochaines étapes**
- [ ] **Priorité 1 sur ADR-002 : implémenter le garde-fou contre l'échec silencieux** — `PolityConfigError` au chargement quand `(ambition_dist, ambition_threshold)` ne peut produire aucun pool de candidats, et/ou garde-fou à l'exécution quand un tick d'élection trouve zéro nominee, et/ou événement de journal explicite. À traiter **avant** la question de calibration ci-dessous.
- [ ] Trancher ensuite la calibration `ambition_dist`/`ambition_threshold` (relever le seuil d'ambition, baisser le seuil de candidature, les deux, ou vérifier d'abord si `rupture_path_enabled: false` était l'accident réel) — non commencé, aucune option évaluée à ce stade.
- [ ] Diagnostiquer le plancher de troncature résiduel de `chamber_deliberation` (Mode A ou B, prompt distinct de `cast_votes`) — non commencé.
- [ ] Faire suivre la PR #216 (contre `develop`) en revue/merge.

**Pour aller plus loin** : `plan-distribution-positions-seeds.md` (protocole complet Phases 1-4 et §3.1 pour la sonde ambition_threshold), `THEORY.md` §10.9-§10.10, `docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md`, `fast_api_voter/scripts/acceptance_v6b_fs_electoral_only_results.md`, `fast_api_voter/scripts/llm_test_harness/README.md` (piège `message.reasoning`), PR #216, entrée du 2026-08-24 pour la fermeture de la chaîne causale seed=42 qui a ouvert ce chantier.

---

## 2026-08-24 — Le run cascade à trois ingrédients ne franchit pas la barre de go/no-go, et révèle un problème plus grave que celui qu'il cherchait à tester

**Contexte du jour.** La PR #184 (v6b Lot 4 acceptance + investigation fiabilité LLM + déterminisme GPU + métrique de déviation unifiée), qui rassemble le travail déjà raconté dans les entrées du 19 au 23 août, a été mergée sur `develop` ce matin (squash `c40b1bb`) — non re-racontée ici. Nouvelle branche `feat/polity-cascade-acceptance` ouverte pour le chantier suivant, identifié depuis plusieurs sessions comme le point qui referme la revendication à trois ingrédients du §7bis.9e (« un basculement de type Gilets jaunes n'est pas atteignable avant v6… il requiert simultanément le graphe social, les chocs exogènes et les leviers de pression ») : un run d'acceptation qui active pour la première fois `events` (v5) et `social_graph`/`neighbors_acting` (v6a) *ensemble*, sous `mobilization_only`, alors que chaque run précédent n'en avait isolé qu'un seul à la fois.

**Ce qui a avancé**
- Script `fast_api_voter/scripts/run_cascade_acceptance.py` écrit, avec critère de décision pré-enregistré dans le docstring avant tout lancement : escalader vers le bras LLM (~2,5-5h prévues) seulement si le dry-run déterministe atteint `office_occupancy >= 0.5` et au moins 2 ticks de tir de scandale + 1 de choc ; sinon diviser par deux `scandal_rate`/`economy_sigma` et relancer le dry-run (quasi gratuit) — jamais relâcher `legitimacy.recall_floor`, option explicitement exclue en citant la conclusion déjà actée du v6b Lot 4 (« scientifiquement peu élégant… désactive la responsabilité plutôt que de la tester »).
- Dry-run déterministe exécuté (`scripts/acceptance_cascade_runs/cascade-deterministic-8y-r0.08-s0.12/`, seed=42, `scandal_rate=0.08`/`economy_sigma=0.12`, point de départ délibérément prudent — environ moitié moins que le calibrage v5 déjà retenu, ce dernier n'ayant jamais été validé pour cette combinaison précise). Résultat : `office_occupancy=0.152`, largement sous la barre `>=0.5`.
- Escalade prescrite par le script tentée (division par deux du taux à `r0.04/s0.06`) : résultat byte-identique au run précédent (`office_occupancy=0.152`, mêmes 2 rappels, zéro scandale, zéro choc déclenché) — preuve directe que les événements ne se déclenchent jamais avant l'effondrement, donc qu'aucun recalibrage de ce type ne peut réparer quoi que ce soit.
- Racine tracée dans le journal du run lui-même : élection au tick 0, rappel au tick 1 (`L` chute de 0,345 à 0,026, sous le plancher 0,2), poste vacant jusqu'au tick 16, nouvelle élection, nouveau rappel au tick 17, vacant jusqu'au tick 32. Au tick 0, la porte d'éveil est maximalement permissive (aucun terme de modulation contextuel n'a encore eu la chance d'être non nul), ce qui consulte 67/100 citoyens et en mobilise 33/100 — exactement le chiffre déjà documenté par v4 Lot 4 (« mobilize max ≈0.33 juste après élection »), déjà à l'intérieur du mur d'amplification x33,3 que le docstring de v4 Lot 4 nommait déjà. Ce résultat (`legitimacy_floor=2`, `mean L (last)=0.345`) est byte-identique à la ligne `mobilization_only` déjà committée de v4 Lot 8 et à la ligne contagion déjà committée de v6a Lot 4 — preuve qu'il s'agit d'une propriété préexistante de la ligne de base déterministe `mobilization_only`, présente depuis v4 Lot 8, jamais repérée jusqu'ici faute d'une métrique `office_occupancy` explicite dans les scripts d'acceptation précédents.
- Décision prise en conséquence, sans consommer le budget GPU du bras LLM : le bras LLM (~2,5-5h) n'a délibérément pas été lancé — la barre de go/no-go n'étant franchissable par aucun des leviers autorisés par le plan, le résultat déterministe est documenté tel quel comme un résultat honnête (limite structurelle, pas un bug ni un résultat nul) dans `fast_api_voter/scripts/acceptance_cascade_results.md`.
- **Découverte plus large en cours de route, faite en balayant 11 graines alternatives (1, 2, 3, 5, 7, 10, 13, 21, 99, 100, 123) pour vérifier si un autre tirage de population évitait l'effondrement** : 9 sur 11 n'élisent aucun président du tout — le Blanc l'emporte au second tour (`election_no_winner`) dès qu'assez d'électeurs jugent les 5 plateformes de parti inacceptables — et les 2 restantes (10, 99) qui élisent quelqu'un s'effondrent quand même par le même mécanisme de rappel. `seed=42` — la seule graine jamais utilisée par un run d'acceptation de ce projet, de v4 Lot 8 jusqu'aux runs v6b les plus récents — se situe juste sous ce seuil de basculement (~32-34 % de bulletins classant Blanc en tête) par coïncidence de tirage, pas par une propriété distinctive de la population générée : son `blank_threshold` moyen et sa distance moyenne au nominee le plus proche ne sont pas systématiquement plus favorables que plusieurs graines qui échouent. Vérifié directement que ce phénomène est indépendant de `pressure_menu`/`social_graph`/`events` (les élections se résolvent avant que ces mécanismes n'interviennent) : `electoral_only` aux seeds 1 et 7 produit le même `election_no_winner`.
- Deux notes de documentation ajoutées, pure documentation sans changement de code/comportement : un nouveau paragraphe en tête de §10.10 « Limites connues » de `THEORY.md` ; une troisième clause datée (2026-08-24) ajoutée à la cellule Statut de la ligne Polity de `traceability.md` (autre worktree `C:\Users\burba\Vote-App`, gitignoré donc invisible au `git diff` de ce dépôt — vérifié directement dans le fichier).
- Travail du jour committé (`87d319b`) et poussé, PR #188 ouverte contre `develop` — non mergée à la demande explicite de l'utilisateur (« no need to merge »).
- **Revirement plus tard dans la même session : l'investigation de fond sur la représentativité des graines, explicitement écartée plus haut dans cette même entrée, a finalement été autorisée et menée à terme le jour même** (« lets start the investigation », après la mise en attente initiale). Menée intégralement en lecture/mesure contre le pipeline réel (`generate_population`, `initialize_parties`, `select_party_nominee`, `build_ranking`, `get_two_round_winner`), via des scripts éphémères dans le scratchpad de session — jamais commités, jamais destinés à l'être. Chaîne causale fermée, pas seulement corrélée :
  - Élargi le sweep à 60 graines : le Blanc l'emporte sur **41/60 (68 %)** à la configuration livrée — un taux bien plus élevé que les 9/11 du premier sweep ne le laissait supposer, et le taux de bulletins « Blanc forcé » (aucun des 5 nominee dans la tolérance de l'électeur) reste étonnamment resserré d'une graine à l'autre (0,29 à 0,52, écart-type 0,054) — signe que ce n'est pas un tirage de population particulier qui échoue, mais une propriété quasi systématique du modèle.
  - **Mécanisme du second tour identifié comme déterministe, pas probabiliste** : une fois le Blanc qualifié, `build_ranking` classe tout candidat dans la tolérance d'un électeur au-dessus du Blanc et tout candidat hors tolérance en dessous — le second tour se réduit donc, par électeur, à une seule question binaire (« ce finaliste m'est-il acceptable ? »), indépendante des trois autres candidats. Vérifié : le Blanc gagne si et seulement si l'acceptabilité du finaliste dans toute la population est `≤ 50 %` — frontière exacte sur 40 graines (max 50,0 % quand le Blanc gagne, min 51,0 % quand un candidat réel gagne, zéro chevauchement).
  - Cause racine isolée : `citizens.position_dist: uniform` disperse 100 citoyens sur 20 dimensions sans centre de gravité ; combiné à une pondération de priorités individualisée par électeur (`priority_dist: dirichlet`), quasiment aucun point n'est proche, selon la métrique propre à chaque électeur, de plus de la moitié de la population.
  - Deux leviers testés isolément contre le même pipeline : la méthode de sélection du nominee (le membre au score d'ambition le plus élevé, artefact de `ambition_threshold=0.0` forcé par tout script d'acceptance, vs le membre le plus proche du centroïde k-means du parti) fait passer le taux d'échec de 70 % à 27,5 % (5 partis, 40 graines) — un effet réel mais secondaire, qui n'élimine pas le problème. Augmenter le nombre de partis n'aide pas de façon monotone (55 % à 10 partis, remonte à 67,5 % à 15-20 partis) — la couverture s'améliore mais la fragmentation du vote s'aggrave en proportion.
  - **Le levier qui referme la chaîne** : remplacer uniquement le tirage des positions par une distribution concentrée (`position_dist: gaussian_mixture`, déjà légale dans le schéma de config mais jamais implémentée — `generate_population` la rejette avec `NotImplementedError`), tout le reste du pipeline inchangé, fait chuter l'échec à 2,5 % (gaussienne large, `std=0,30`) puis 0 % (`std≤0,20`, ou mélange à 2-3 modes) sur les 40 graines testées.
  - `THEORY.md` §10.10 et `traceability.md` réécrits pour porter cette chaîne complète, en remplacement des notes préliminaires du matin.

**Points bloquants**
- La revendication à trois ingrédients du §7bis.9e reste non testable à l'échelle actuelle (`population_size=100`, seed=42, `mobilization_only`) — pas parce que la contagion ou les événements échouent à interagir, mais parce que le poste est vacant avant qu'ils n'aient la moindre chance d'agir. Ligne du v6a Lot 4 déjà committée montrant le même `legitimacy_floor=2` sous le même menu (sans événements) suggère, sans le prouver (`office_occupancy` jamais calculée sur ce run-là), que le bras LLM ne s'en tirerait probablement pas mieux.
- La décision de corriger reste entièrement ouverte : le mécanisme est complet et fermé, mais implémenter `gaussian_mixture` dans `generate_population`, et/ou revoir le tiebreak de `select_party_nominee`, et/ou reconsidérer l'override `ambition_threshold=0.0` que tout script d'acceptance impose — touchent un mécanisme central du v0, utilisé par tous les runs du projet depuis le début. Aucune de ces pistes n'a été décidée ni commencée.
- La réécriture complète de `THEORY.md` §10.10 (chaîne causale fermée, décrite ci-dessus) n'a jamais été committée : elle existe uniquement comme diff dans l'arbre de travail au moment de la clôture de cette session (`git status` : `M THEORY.md`, 60 insertions/14 suppressions), et remplace localement la note préliminaire déjà committée dans `87d319b`/PR #188 — mais la PR elle-même porte encore cette note préliminaire, pas la version finale. La question de committer/pousser cette mise à jour vers PR #188 a été posée explicitement à l'utilisateur en fin de session ; la réponse reste en attente au moment de la rédaction de cette entrée.

**Décisions prises**
- Ne pas lancer le bras LLM une fois la barre de go/no-go pré-enregistrée manquée et l'escalade prescrite épuisée — *pourquoi* : le plan pré-enregistré ne prévoyait pas d'autre levier autorisé (le relâchement de `recall_floor` étant explicitement exclu), et le coût du bras LLM (~2,5-5h) n'aurait rien pu changer à une cause déjà tracée comme indépendante des événements.
- Documenter `office_occupancy=0.152` comme un résultat honnête de limite structurelle plutôt que de le présenter comme un échec de calibration — *pourquoi* : la cause est tracée avec preuve (byte-identité entre deux taux d'événements différents, byte-identité avec des lignes déjà committées de v4 Lot 8 et v6a Lot 4) à une propriété préexistante de la ligne de base `mobilization_only`, pas à un mauvais réglage de ce run.
- Committer et ouvrir la PR #188 sans la merger — *pourquoi* : consigne explicite de l'utilisateur (« no need to merge »), le travail est prêt pour revue mais l'intégration reste une décision séparée.
- **Revirement explicite et assumé** : l'investigation de fond, mise en attente plus tôt dans la journée (« mérite une vraie session »), a finalement été autorisée et menée le jour même sur consigne directe de l'utilisateur (« lets start the investigation ») — la décision antérieure de ne pas l'engager n'a pas été reconduite silencieusement, elle a été explicitement remplacée.
- Approfondir jusqu'à fermer la chaîne causale complète (pas s'arrêter à la première corrélation trouvée) — *pourquoi* : deux points de contrôle explicites de l'utilisateur en cours de route (« creuser le résiduel », puis « tester gaussian_mixture ») plutôt que de documenter une explication partielle après le premier résultat frappant.
- S'arrêter une fois la chaîne fermée par le test `gaussian_mixture`, sans passer à la conception d'un correctif — *pourquoi* : consigne explicite de l'utilisateur à la dernière étape de contrôle ; le mécanisme est maintenant complet et déterministe (pas une hypothèse), mais corriger touche `select_party_nominee`/`generate_population`, du code central utilisé par tout le projet, et mérite sa propre planification séparée plutôt qu'être décidé en bout d'investigation.

**Prochaines étapes**
- [x] Committer le travail du jour (`.gitignore`, `THEORY.md`, `run_cascade_acceptance.py`, `acceptance_cascade_results.md`) — fait (`87d319b`), PR #188 ouverte, non mergée.
- [x] Investigation de fond sur la représentativité des graines — faite le jour même, chaîne causale complète fermée (voir ci-dessus).
- [ ] Décider si/quand committer et pousser vers PR #188 la réécriture complète de `THEORY.md` §10.10 — actuellement diff non commité dans l'arbre de travail, décision utilisateur en attente.
- [ ] Décider si/comment corriger : implémenter `gaussian_mixture` dans `generate_population`, et/ou revoir le tiebreak de `select_party_nominee` (centroïde plutôt qu'ambition), et/ou reconsidérer l'override `ambition_threshold=0.0` de chaque script d'acceptance — non commencé, non planifié, décision et priorité restent à prendre.
- [ ] Statuer, une fois un correctif éventuel tranché, sur si/comment retenter le run cascade à trois ingrédients (§7bis.9e) avec un tirage de population plus robuste.

**Pour aller plus loin** : `fast_api_voter/scripts/run_cascade_acceptance.py` (script, docstring pré-enregistré), `fast_api_voter/scripts/acceptance_cascade_results.md` (résultat détaillé, premier sweep de graines), `THEORY.md` §10.10 (chaîne causale complète, réécrite en fin de journée — diff non commité au moment de la rédaction de cette entrée, voir Points bloquants), `docs/research/traceability.md` (autre worktree, troisième clause réécrite), PR #188 (committée, non mergée, porte encore la note préliminaire de §10.10), entrées du 19 au 23 août pour le contexte complet de la PR #184. Les scripts de l'investigation de fond (sweep à 60 graines, test `gaussian_mixture`) étaient dans le scratchpad de session, non commités — à reproduire depuis THEORY.md §10.10 si nécessaire, pas depuis un fichier existant.

---

## 2026-08-23 — Troisième run d'acceptance (electoral_only) : même maximum au bit près, et un pré-enregistrement vérifié à trois horodatages indépendants

**Contexte du jour.** Suite directe de la session de la veille (commit `ab91fa2`) : le second run d'acceptance v6b Lot 4 (`legitimacy.recall_floor=0.0`) avait éliminé le confond de vacance en gardant le président en poste sans interruption, mais via un levier qui désactive la responsabilité plutôt que de la tester — recall_floor à zéro. Objectif du jour : planifier deux chantiers de suivi, puis exécuter le plus rigoureux des deux — un troisième run résolvant le même confond via `pressure_menu.electoral_only`, un levier qui teste la responsabilité électorale sans l'éteindre.

**Ce qui a avancé**
- Deux chantiers planifiés en profondeur (mode plan, approbation utilisateur explicite) : (A) câblage en production d'une métrique de déviation "unifiée" (sans configuration, même pondération que `chamber_deviation`) dans `representative_response`/`mandate_deviation_recorded` et l'extraction `indexer.py` correspondante ; (B) un troisième run d'acceptance via `pressure_menu.electoral_only` au lieu d'un `recall_floor` mis à zéro.
- Chantier B seul autorisé et exécuté ce jour. Pré-enregistré avant lancement : hypothèse et trois branches de résultat nommées à l'avance (comparable au run 2, matériellement plus bas mais non nul, ou quasi nul) — critère de décision explicite pour éviter toute survente a posteriori.
- Run LLM lancé (~4,4h prévues, bande 3,9-5,9h), terminé proprement en ~4h38 (16670,7s, 28 replays, sain).
- Falsifiables structurels pré-enregistrés tous vérifiés : zéro rappel, occupation du poste à 1,0, mêmes élections byte-identiques entre run 2 et run 3 — même titulaire, même plateforme promise, confirmant que candidature/nomination/vote ne dépendent pas du menu de pression.
- Résultat dans la branche intermédiaire pré-enregistrée : déviation unifiée moyenne du président à 0,1017 (contre 0,1496 sur le run 2, environ un tiers de baisse), mais maximum identique au bit près entre les deux runs (0,2312481349581757).
- Ce maximum identique investigué à la demande explicite de l'utilisateur avant toute synthèse : reconstruction complète depuis les deux journaux bruts (régénération de la population, rejeu des shifts) montrant que les deux présidents (même personne dans les deux runs) saturent indépendamment les trois mêmes dimensions au plafond du clamp [0,1] — atteint au tick 27 sous pression complète, seulement au tick 30 sous `electoral_only`. Même plafond, atteint plus tard sans la pression de rue : explique la baisse de moyenne sans toucher au maximum, corrobore la découverte du plafonnement de la veille une seconde fois plutôt que de la contredire.
- Preuve matérielle du pré-enregistrement également demandée avant synthèse (pas une reconstruction a posteriori) : retrouvée dans la transcription de session avec horodatages UTC réels — édition du plan à 13:31:13Z, approbation à 13:39:09Z, édition du docstring du script à 13:45:49Z, message utilisateur de lancement à 14:04:58Z, lancement effectif vers 14:05Z — 19 à 34 minutes d'écart, vérifié à trois points indépendants, pas un simple mtime de fichier.
- `THEORY.md` §10.9/§10.10 et `fast_api_voter/scripts/acceptance_v6b_results.md` mis à jour pour raconter l'histoire à trois runs comme un seul récit continu (pas deux documents séparés) : tableau de résultats du troisième run, vérification élections/identité du maximum, synthèse de la question de départ à travers les trois runs. `traceability.md` (autre worktree) ne nécessitait aucun changement ce coup-ci — déjà à jour depuis le commit de la veille.
- Commit unique sur `feat/polity-v6b-lot4-acceptance` (`922a070`), portant exactement `THEORY.md` et `acceptance_v6b_results.md` — séparé du reste de l'arbre de travail, comme la veille.

**Points bloquants**
- Le câblage en production de la métrique unifiée (chantier A) n'a pas démarré ce jour — resté au stade plan. Le code déjà modifié lors de la session précédente pour ce chantier (`accountability.py`, `run_polity_simulation.py`, `indexer.py`, tests, `run_v6b_acceptance.py`) est présent dans l'arbre de travail mais non commité, et mélangé dans `run_v6b_acceptance.py` avec un diff préexistant sans rapport qu'il faudra démêler avant de committer proprement.
- Le clamp silencieux d'`apply_shifts`, documenté mais non corrigé, reste un défaut d'observabilité en suspens — confirmé une seconde fois ce jour comme mécanisme actif, pas résolu pour autant.

**Décisions prises**
- Traiter uniquement le chantier B (troisième run via `electoral_only`) ce jour, laisser le chantier A (câblage production) au stade plan — *pourquoi* : consigne explicite de l'utilisateur de ne pas enchaîner les deux chantiers sans autorisation séparée, l'un est une exécution d'expérience bornée dans le temps, l'autre un chantier de code à part entière.
- Préférer `pressure_menu.electoral_only` à un `recall_floor` relâché pour ce troisième run — *pourquoi* : teste la responsabilité électorale en retirant la pression de rue plutôt que de désactiver le mécanisme de rappel lui-même, un levier plus proche de la question scientifique posée par le §6bis.3.
- Investiguer le maximum identique au bit près avant toute rédaction de synthèse, plutôt que de le mentionner en passant comme curiosité — *pourquoi* : consigne explicite de l'utilisateur ; une coïncidence numérique de cette précision méritait une explication mécanique vérifiée, pas une hypothèse non testée.
- Vérifier matériellement l'antériorité du pré-enregistrement au lancement avant de synthétiser le résultat — *pourquoi* : consigne explicite de l'utilisateur ; un pré-enregistrement n'a de valeur que si son antériorité au résultat est démontrable, pas seulement affirmée.
- Committer la mise à jour documentaire (`THEORY.md`, `acceptance_v6b_results.md`) isolément du reste de l'arbre de travail — *pourquoi* : cohérent avec la discipline déjà établie sur ce projet d'un commit par préoccupation.

**Prochaines étapes**
- [ ] Démêler le diff préexistant sans rapport dans `run_v6b_acceptance.py` du code du chantier A (câblage métrique unifiée), puis committer séparément — non autorisé à démarrer.
- [ ] Câbler la métrique de déviation unifiée en production (`accountability.py`, `run_polity_simulation.py`, `indexer.py`, tests déjà modifiés dans l'arbre de travail) — non autorisé à démarrer.
- [ ] Statuer, à terme, sur une correction du clamp silencieux d'`apply_shifts` (retour/journalisation), au-delà de la documentation actuelle du défaut.

**Pour aller plus loin** : `THEORY.md` §10.9-§10.10 (récit à trois runs, commit `922a070`), `fast_api_voter/scripts/acceptance_v6b_results.md` (régénéré), `fast_api_voter/scripts/acceptance_v6b_runs_electoral_only/` (troisième run), `fast_api_voter/scripts/acceptance_v6b_electoral_only_results.md`, entrée du 2026-08-22 précédente pour le contexte des deux premiers runs et du plafonnement du clamp.

---

## 2026-08-22 — Le confond de vacance était un demi-diagnostic : bug de métrique, plafonnement du clamp, et une §10.9 réécrite en entier

**Contexte du jour.** Suite directe de la session précédente du même jour : le premier run d'acceptance v6b Lot 4 (menu `both`) s'était révélé confondu par un rappel quasi immédiat du président élu après chacune des deux élections, laissant le poste vacant l'essentiel du run et `mandate_deviation` à 0,0 par absence d'exposition plutôt que par fidélité réelle. Un second run avait été lancé avant cette session avec `legitimacy.recall_floor=0.0` pour éliminer ce confond par construction. Objectif du jour : comprendre pourquoi `mandate_deviation` restait *encore* à 0,0 dans ce second run malgré une occupation du poste à 100 %, et trancher enfin la question du §6bis.3 — la chambre de sortition est-elle sincère ou erratique, comparée au président élu ?

**Ce qui a avancé**
- Diagnostic du second run (`scripts/acceptance_v6b_runs_recallfloor0/`, `office_occupancy=1.0`, zéro rappel, 15874,6s, 28 rejeux) : `mandate_deviation` à 0,0 malgré une exposition complète n'était pas un artefact de run mais un vrai bug de conception de métrique.
- Recalcul post-hoc de `mandate_deviation` avec la même méthode déjà en service pour `chamber_deviation` (`weighted_euclidean` sur le vecteur de priorités complet, sans troncature) pour obtenir une comparaison sur la même base. Résultat mesuré : président (métrique unifiée) moyenne 0,1496 / max 0,2312, contre chambre quasi inerte moyenne 0,000036 / max 0,0353 — l'écart que le run devait révéler apparaît enfin.
- Second phénomène repéré en examinant la série recalculée : elle plafonne exactement à deux reprises (0,194070 du tick 10 à 15 ; 0,231248 du tick 27 à 31). Vérifié directement contre le journal d'événements : à chaque tick du plateau, `representative_response` continue d'émettre des `shifts` non vides (motif `302 STREET_PRESSURE_RESPONSE`, concession) sur les mêmes trois dimensions — la pression ne s'arrête jamais. Ce qui plafonne réellement, c'est le clamp `[0,1]` d'`apply_shifts` : les trois dimensions ont déjà atteint 1,0, chaque delta suivant vise une cible hors bornes absorbée silencieusement.
- Reconstruction diagnostique bâtie pour quantifier l'ampleur masquée par le clamp : mêmes shifts journalisés, rejoués sans jamais appliquer le clamp. La déviation "fantôme" non bornée atteint 0,701 en fin de premier mandat (contre 0,194 côté clampé — x3,6) et 0,642 en fin de second mandat (contre 0,231 — x2,8). Le chiffre officiellement rapporté est donc une borne inférieure de la dérive réelle, pas une mesure de son plafond — ce qui renforce la conclusion scientifique (chambre sincère, président erratique sous pression) plutôt que de la nuancer.
- Défaut d'observabilité repéré et signalé séparément, hors résultat scientifique : `apply_shifts` clampe silencieusement (aucun retour, aucun journal, aucun log) — un défaut partagé par les trois décisions qui l'utilisent (dt=5, dt=6, dt=11), pas spécifique à `mandate_deviation`. Documenté dans la docstring d'`apply_shifts` (`llm_behavior_engine.py`) et dans `traceability.md`, non corrigé à ce stade.
- `THEORY.md` §10.9 réécrite en entier (et la puce §10.10 qui la référençait, restée rédigée pour le premier run confondu, donc obsolète) pour raconter l'histoire complète en deux runs : bug de métrique, mesure corrigée, plafonnement diagnostiqué comme borne inférieure. Relecture de cohérence demandée explicitement par l'utilisateur avant commit : deux problèmes réels trouvés et corrigés — (a) l'ordre de deux paragraphes était inversé, la reconstruction non clampée citait les valeurs du plateau avant que le plateau lui-même soit expliqué, référence en avant héritée d'une version antérieure du raisonnement ; (b) un chiffre figé d'un brouillon antérieur ("99,3 % de décisions `SINCERE_POSITION`") appartenait en réalité aux statistiques du premier run, pas du second — revérifié directement contre `chamber.json` et corrigé à 99,70 %.
- `fast_api_voter/scripts/acceptance_v6b_results.md` régénéré pour raconter exactement la même histoire que `THEORY.md`, avec les chiffres relus directement dans les `metrics.json`/`chamber.json` des deux runs, pas recopiés d'un brouillon.
- Vérifications avant commit : `flake8`/`mypy` propres sur `accountability.py` et `llm_behavior_engine.py` — changements docstring-only, aucun changement de comportement.
- Commit unique sur `feat/polity-v6b-lot4-acceptance` (`ab91fa2`), portant exactement `THEORY.md`, `accountability.py`, `llm_behavior_engine.py`, `acceptance_v6b_results.md` — délibérément séparé du reste de l'arbre de travail (diff non lié dans `run_v6b_acceptance.py`, `llm_batching_determinism_results_gpu.md`, scripts supprimés, répertoires de runs non suivis), non lié à ce chantier précis.

**Points bloquants**
- Aucun nouveau, mais deux fils explicitement laissés en l'état par choix, pas par oubli : la métrique de déviation unifiée n'est câblée que dans cette analyse post-hoc, pas dans les métriques de production (`metrics.json`/`indexer.py`) ; et la question de vacance du tout premier run (menu `both`) n'a pas de run de suivi dédié.
- Le clamp silencieux d'`apply_shifts` reste un défaut d'observabilité non corrigé, documenté mais pas résolu — toute mesure future de déviation basée sur cette fonction sous-estimera potentiellement la dérive réelle sans avertissement.

**Décisions prises**
- Recalculer `mandate_deviation` post-hoc avec la méthode `weighted_euclidean` déjà en service pour `chamber_deviation`, plutôt que de retoucher le mode `top_k_priorities` en production — *pourquoi* : répondre à la question scientifique du jour sans engager un nouveau chantier de correction de métrique de production, non prévu dans ce lot.
- Quantifier explicitement l'effet du clamp via une reconstruction "fantôme" non bornée plutôt que de se contenter de signaler sa présence — *pourquoi* : donner un ordre de grandeur (x2,8 à x3,6) permet de qualifier le chiffre rapporté comme borne inférieure fiable, au lieu de laisser planer un doute non chiffré sur sa validité.
- Différer explicitement le câblage en production de la métrique unifiée et la conception d'un run de suivi pour le premier run confondu — *pourquoi* : ce sont deux nouveaux chantiers distincts, pas la suite mécanique de la correction documentaire du jour ; consigne explicite de l'utilisateur de ne pas les enchaîner sans autorisation séparée.
- Commiter la correction documentaire (`THEORY.md`, docstrings, résultats) isolément du reste de l'arbre de travail non lié — *pourquoi* : cohérent avec la discipline déjà établie sur ce projet d'un commit par préoccupation.

**Prochaines étapes**
- [ ] Câbler la métrique de déviation unifiée (pondération pleine, méthode `chamber_deviation`) dans les métriques de production (`metrics.json`/`indexer.py`) — non autorisé à démarrer.
- [ ] Concevoir et lancer un run de suivi pour trancher la question de vacance du premier run (menu `electoral_only`, ou plancher de rappel relâché, pour laisser le mandat élu survivre assez longtemps pour être comparable) — non autorisé à démarrer.
- [ ] Statuer, à terme, sur une correction du clamp silencieux d'`apply_shifts` (retour/journalisation), au-delà de la documentation actuelle du défaut.

**Pour aller plus loin** : `THEORY.md` §10.9-§10.10 (réécrites, commit `ab91fa2`), `fast_api_voter/scripts/acceptance_v6b_results.md` (régénéré), `scripts/acceptance_v6b_runs_recallfloor0/` (second run, `legitimacy.recall_floor=0.0`), docstrings `KNOWN METRIC DESIGN BUG`/`KNOWN OBSERVABILITY GAP` dans `accountability.py` et `llm_behavior_engine.py`, `docs/research/traceability.md` (autre worktree, note `apply_shifts`), entrée du 2026-08-22 précédente pour le contexte du premier run confondu.

---

## 2026-08-22 — chamber_deliberation tronqué, chunk_size réduit à 1, run d'acceptance terminé — mais la question du §6bis.3 reste ouverte

**Contexte du jour.** Prolongation directe de l'investigation bug 4 (troncature `finish_reason='length'` sur Ollama), entamée le 2026-08-19 et poursuivie le 2026-08-20/21 : après le déploiement de la mitigation cache-recycling (`49e3631`), un nouveau run d'acceptance v6b Lot 4 relancé avait planté sur `chamber_deliberation` (dt=11) au tick 18, après 1258 événements journalisés — signe que la mitigation bug 4 ne suffisait pas seule à sécuriser cette décision LLM particulière. Objectif du run : trancher, via le v6b Lot 4, si la chambre tirée au sort se comporte de façon sincère ou erratique, en la comparant au président élu sur la même durée.

**Ce qui a avancé**
- Diagnostic mené selon la méthode "Mode A vs Mode B" déjà établie sur ce projet : sur les 3 tentatives du run planté (originale + 2 replays), `n_decoded` tombait exactement et systématiquement à `10136 = compute_max_tokens(10) + _CHAMBER_THINK_TOKEN_ALLOWANCE(8000)` — signature Mode B (plafond de budget trop juste, pas une dérive sans convergence), avec 11630 tokens de marge de contexte disponible par ailleurs. Chunk_size de `chamber_deliberation` confirmé à 10 dans le code.
- Fix testé par escalade contrôlée, chaque palier validé avant le suivant plutôt qu'un saut direct à la valeur la plus prudente :
  - `_CHAMBER_MAX_CHUNK_SIZE = 5` essayé en premier (par analogie avec l'historique déjà documenté de `_VOTE_CAST_MAX_CHUNK_SIZE`) — **rejeté après validation live** : rejoué contre l'état exact du run planté (replay du journal, seed=42, sans re-run complet), un sous-groupe différent de 5 citoyens (cids [59,61,65,75,90]) a reproduit la même signature de troncature, `n_decoded=9836` = plafond exact, marge nulle.
  - `_CHAMBER_MAX_CHUNK_SIZE = 1` essayé ensuite (l'aboutissement déjà connu pour `_VOTE_CAST_MAX_CHUNK_SIZE`), revalidé sur le même groupe de 5 citoyens en individuel : 5/5 réussites, 4.3–11.7s chacune — un ordre de grandeur plus rapide que les 99–108s des tentatives échouées, marge réelle cette fois.
- Documentation (docstrings, commentaires de code, 3 fichiers de tests, `fast_api_voter/scripts/lot3_chamber_reliability_results.md`) réécrite pour refléter la chaîne complète de preuves (10 → 5 essayé et invalidé → 1 validé), pas seulement la valeur finale retenue.
- Vérifications complètes après le fix : `pytest -k "chamber"` (23 passed), mypy clean, flake8 clean, suite complète `pytest api/` (1548 passed, 41 skipped).
- **Run d'acceptance relancé, terminé avec succès (exit code 0).** Journal complet jusqu'au tick 32, 2012 événements journalisés. 38 replays au total sur tout le run — tous récupérés dès leur première tentative de retry, aucun n'a épuisé son budget de 3 tentatives. Temps réel 16384.8s (~4.55h), proche de la prévision du plan (~3.95h). La chambre de sortition est restée pleine (30 sièges) sur les 9 rotations du run — le mécanisme de bassin assoupli (v6b Lot 2) a tenu comme prévu.
- Nettoyage découvert en cours de route : `fast_api_voter/scripts/acceptance_v6b_runs/` avait accumulé 18 dossiers de runs ratés/obsolètes de sessions précédentes (déjà nommés `-failed-*`/`-stale-*`), que le script `--summarize` (glob non récursif à un niveau) ramassait quand même et mélangeait dans le rapport final. Archivés (déplacés, pas supprimés) dans `_archived_failed_runs/` pour que le résumé ne porte que sur les deux runs réels du jour (déterministe + LLM).
- Synchronisation documentaire faite : `THEORY.md` gagne une nouvelle §10.9 "La chambre de sortition — sincère ou erratique ?" (renumérote les sections suivantes : 10.9→10.10 limites, 10.10→10.11 références), avec la découverte de vacance rapportée honnêtement dans le corps du texte. `traceability.md` (autre worktree, `c:/Users/burba/Vote-App/docs/research/`) mis à jour : statut `implémenté (v4, v5, v6a, v6b)`.
- **Étape 3.1 du prompt séquencé post-harnais reprise (nettoyage de dette technique jamais fait jusqu'ici) : ajout du champ `inference_backend`/version driver-CUDA.** Nouvelle fonction `_capture_gpu_driver_info()` dans `run_polity_simulation.py` : capture best-effort (jamais fatale, dégrade à `(None, None)` sur tout échec) de la version du driver GPU et de la version CUDA via un appel `nvidia-smi` en subprocess — inspirée du même principe déjà utilisé par `llm_test_harness/environment.py`, sans adopter le harnais lui-même. Deux nouveaux champs dans `run_metadata.json` (`gpu_driver_version`, `gpu_cuda_version`), capturés **uniquement** quand `config.llm.enabled` est vrai — le GPU n'a de sens à identifier que quand un appel LLM peut réellement avoir lieu, et ça évite tout coût subprocess sur les >100 invocations déterministes de `run_simulation` dans la suite de tests. 4 nouveaux tests, mypy clean, flake8 clean, suite complète passée à 1552 passed / 41 skipped (+4).
- **Étape 3.2 reprise (audit des runs antérieurs aux correctifs), avec une découverte notable.** Aucun dossier `runs/` par défaut trouvé — tous les vrais runs du projet utilisent des `--output-dir` explicites vers `scripts/acceptance_v*_runs/`. En examinant ces dossiers, découverte que **deux résultats déjà publiés dans `THEORY.md` reposent sur des runs antérieurs à tous les correctifs de fiabilité de cette investigation** : `scripts/acceptance_v5_runs/electoral_only-llm-8y-events-r0.15-s0.25/` (2026-08-15, cité en §10.7 "l'étincelle", palier v5 Lot 5) et `scripts/acceptance_v6a_runs/contagion-llm-8y/` (2026-08-16, cité en §10.8 "la contagion", palier v6a Lot 4) — tous deux antérieurs au fix warm-up GPU (18/08), à la mitigation cache-recycling bug 4 (20/08), et au fix `vote_cast`/`chamber_deliberation` d'aujourd'hui. Constat présenté à l'utilisateur avant toute modification de `THEORY.md` (voir décisions ci-dessous).
- **Audit ciblé exécuté selon le protocole défini par l'utilisateur** : relecture directe des deux journaux existants (300 événements `vote_cast` chacun, ticks d'élection 0/16/32) contre la règle §3.6.1 exacte (`blank=1` doit avoir un `ranking` vide) — **zéro violation trouvée dans les deux cas**, cohérent avec le `replays.log` vide de chacun des deux runs.
- Conclusion appliquée selon la règle de décision de l'utilisateur (caveat suffit si audit négatif ou isolé) : deux caveats ajoutés dans `THEORY.md` (§10.7 et §10.8), datés (2026-08-22), factuels — citant l'antériorité aux correctifs, le taux d'incohérence connu (~6,7% des appels `cast_votes`, mesuré dans `cache_recycle_chunk_size_tension_findings.md`), et le résultat de l'audit, avec conclusion explicite : "le résultat n'est pas invalidé, il reste non re-vérifié sous le code corrigé." Deux marqueurs `INVALID_PRE_GPU_FIXES.md` ajoutés (non destructifs, rien supprimé) à côté des deux runs concernés, pour qu'une future analyse de sensibilité (§11) ne les utilise pas comme référence propre sans vérifier d'abord si un re-run change le résultat.
- Travail commité en quatre commits séparés au total sur la journée, comme d'habitude sur ce projet — un commit par préoccupation :
  - `ca02344` — fix(polity): LLM batch reliability, bundle le fix `chamber_deliberation` chunk_size (10→5 rejeté→1) avec les correctifs `vote_cast` de la même investigation (chunk_size 3→1, retry à température variable 0.3, `_CHAMBER_THINK_TOKEN_ALLOWANCE` 4000→8000) — regroupés parce que les deux fils partagent le même mécanisme sous-jacent (`_complete_and_decode_with_replay`) et le même fichier.
  - `44abc75` — docs(polity): v6b Lot 4 acceptance run, sync `THEORY.md` §10.9 + `scripts/acceptance_v6b_results.md`.
  - `7e13894` — feat(polity): étape 3.1 post-harnais, capture best-effort du driver GPU/version CUDA dans `run_metadata.json` (`gpu_driver_version`, `gpu_cuda_version`), déclenchée seulement quand `config.llm.enabled`.
  - `6380f05` — docs(polity): étape 3.2 post-harnais, caveats `THEORY.md` §10.7/§10.8 sur les deux runs antérieurs aux correctifs de fiabilité, + marqueurs `INVALID_PRE_GPU_FIXES.md`.
  - Vérifié avant chaque commit : mypy clean, flake8 clean, suite complète (1548 → 1552 passed après les 4 nouveaux tests de l'étape 3.1, 41 skipped).

**Points bloquants**
- **Le run a réussi techniquement mais n'a pas tranché la question scientifique du §6bis.3 — le point le plus important de la journée, à ne pas édulcorer.** Sous le menu de pression complet (`both` — pétition + mobilisation), le président élu est rappelé par le plancher de légitimité en l'espace d'un seul tick après CHACUNE des deux élections du run (`L` chute de 0,43 à 0,12, puis de 0,44 à 0,11). Le poste reste vacant l'essentiel des 33 ticks du run. Résultat : `mandate_deviation` reste exactement à 0,0 sur toute la durée — pas parce que le président serait resté fidèle à son mandat, mais parce qu'il n'a presque jamais eu l'occasion de dériver (`representative_response`/dt=6 n'a presque jamais eu de titulaire à qui s'adresser). En parallèle, `chamber_deviation` (la chambre tirée au sort) reste authentiquement quasi nulle (moyenne 0,0001, maximum 0,035, 99,3% des décisions étiquetées `SINCERE_POSITION` par le modèle lui-même). La comparaison "sincère contre erratique" que ce run devait trancher est donc confondue par un phénomène distinct et lui-même intéressant : le menu de pression complet, combiné à l'apparat de responsabilité, produit un rappel quasi immédiat plutôt qu'une dérive mesurable à comparer.
- Un second run ciblé reste à concevoir pour trancher effectivement le §6bis.3, avec un paramétrage qui permette au mandat électif de survivre suffisamment longtemps pour être réellement comparable (ex : `electoral_only`, ou un plancher de rappel relâché) — pas encore autorisé à démarrer.

**Décisions prises**
- Valider chaque palier de réduction de chunk_size (10 → 5 → 1) contre l'état réel du run planté avant d'escalader au suivant, plutôt que de sauter directement à la valeur la plus prudente connue — *pourquoi* : consigne explicite de l'utilisateur de ne pas escalader à l'aveugle ; le palier 5 semblait un choix raisonnable par analogie mais s'est révélé insuffisant à la vérification, ce qui aurait été manqué sans ce test intermédiaire.
- Regrouper le fix `chamber_deliberation` et les correctifs `vote_cast` dans un seul commit plutôt que de les séparer artificiellement — *pourquoi* : les deux fils partagent le même mécanisme sous-jacent et le même fichier ; les séparer aurait cassé la cohérence de la revue sans bénéfice réel.
- Rapporter le résultat du run tel quel (vacance dominante, comparaison confondue) plutôt que de le reformuler pour qu'il ressemble à une conclusion propre — *pourquoi* : la valeur du run est dans ce qu'il révèle sur l'interaction pression/responsabilité, pas dans une réponse artificiellement nette à la question initiale.
- Archiver (pas supprimer) les 18 runs ratés/obsolètes qui polluaient le résumé — *pourquoi* : cohérent avec la discipline déjà établie sur ce projet de préserver la trace des runs plantés plutôt que de les effacer.
- Présenter la découverte des deux runs pré-fix (§10.7/§10.8) à l'utilisateur avant de toucher aux sections `THEORY.md` elles-mêmes — *pourquoi* : la décision de comment traiter des résultats déjà publiés mais potentiellement affectés par des bugs corrigés depuis appartient à l'utilisateur, pas à un choix unilatéral pris en cours de nettoyage.
- Suivre scrupuleusement le protocole en quatre temps fixé par l'utilisateur (caveat factuel d'abord, puis audit ciblé des journaux existants contre la règle §3.6.1, re-run seulement en cas de signal de concentration autour des moments clés) plutôt que d'improviser un re-run immédiat par excès de prudence — *pourquoi* : un re-run coûte plusieurs heures de calcul GPU (cf. le run du jour, ~4,55h) ; l'audit low-cost sur les journaux déjà produits permet de vérifier s'il y a un signal réel avant d'engager cette dépense — et le résultat (zéro violation) a confirmé que le caveat suffisait sans re-run, sans que cette conclusion soit décidée à l'avance.

**Prochaines étapes**
- [ ] Concevoir un second run ciblé v6b Lot 4 permettant au mandat électif de survivre assez longtemps pour être comparable à la chambre de sortition (ex : `electoral_only`, ou plancher de rappel relâché) — non autorisé à démarrer.
- [ ] Revoir si la découverte "rappel quasi immédiat sous menu de pression complet" mérite sa propre section théorique distincte de §10.9, ou reste une note dans cette dernière.

**Pour aller plus loin** : `fast_api_voter/scripts/lot3_chamber_reliability_results.md` (historique complet 10 → 5 → 1), `fast_api_voter/scripts/acceptance_v6b_results.md` (résultats détaillés du run), `THEORY.md` §10.7/§10.8 (caveats datés 2026-08-22) et §10.9, `docs/research/traceability.md`, `fast_api_voter/scripts/cache_recycle_chunk_size_tension_findings.md` (taux d'incohérence ~6,7% cité dans les caveats), run préservé `fast_api_voter/scripts/acceptance_v6b_runs/sortition-llm-8y-failed-chamber-deliberation-truncation-20260821/`, runs archivés dans `_archived_failed_runs/`, marqueurs `INVALID_PRE_GPU_FIXES.md` dans `acceptance_v5_runs/electoral_only-llm-8y-events-r0.15-s0.25/` et `acceptance_v6a_runs/contagion-llm-8y/`, entrée du 2026-08-19 pour le contexte complet de l'investigation bug 4.

---

## 2026-08-19 — Harnais de test lancé : la piste du volume de cache se confirme en partie, et révèle un mécanisme composite à trois étages

**Contexte du jour.** Reprise du chantier bug 4 (troncature `finish_reason='length'` sur Ollama) là où la session précédente l'avait laissé : un banc d'essai de reproduction fiable restait à construire, une mitigation "nonce inerte" restait à tester sans preuve. Avant de plonger dans le bug 4, vérification de deux morceaux de travail en attente de commit — wiring `chamber_deviation` (v6b Lot 4) et le nouveau harnais de test `llm_test_harness/` construit lors d'une session antérieure — avec la suite de tests complète.

**Ce qui a avancé**
- Suite de tests complète revérifiée avant de reprendre le chantier bug 4 : 1531 passed / 41 skipped sur `api/`, mypy et flake8 clean — couvre à la fois le wiring `chamber_deviation` (v6b Lot 4) et le package `llm_test_harness/` (jamais commité), tous deux encore en attente de commit.
- Exécution du prompt séquencé `prompt-sequencement-post-harnais.md`, étape 0 : diagnostic du run d'acceptance `sortition-llm-8y` laissé en cours d'une session précédente — trouvé interrompu au tick 0 pendant une resoumission de batch `vote_cast`, cohérent avec le risque déjà documenté (pas un échec inattendu).
- Confirmation indirecte (logs Windows Defender Operational, event 5007, faute de droits admin pour `Get-MpPreference`) que l'exclusion antivirus configurée pour le conteneur Ollama et les chemins Docker est bien active — trois exclusions retrouvées (deux chemins Docker + `ollama.exe`).
- Reconstruction déterministe du prompt réel ayant déclenché le bug (via `generate_population`/`initialize_parties` au seed=42, cid des nominés vérifiés contre les événements `candidacy_declared` du run interrompu), et calcul par le harnais de la taille d'échantillon nécessaire (n=97) pour le critère de décision pré-enregistré sur le taux de succès des resoumissions avec nonce.
- Caractérisation du taux d'échec de base (hors resoumission), décidée après un échec inattendu de l'appel d'amorçage lui-même : sur 10 appels frais et distincts, 5 échecs (IC de Wilson 95% [24%, 76%]) — nettement au-dessus du seuil de 20-30% attendu, ce qui invalide en l'état le plan de test du nonce tel que conçu.
- **Découverte inattendue, faite en croisant gratuitement les timestamps des essais avec les lignes `cache state: N prompts` des logs Docker du conteneur `ollama-polity`** : le cache de prompts de llama.cpp sur ce conteneur a une capacité mesurée de 8 prompts, et les échecs par troncature corrèlent avec sa saturation (remplissage 0→8 : succès ; une fois saturé/en éviction : échecs dominants). Reformule l'hypothèse du bug — peut-être pas "resoumission d'octets identiques" comme déclencheur, mais "volume de prompts distincts accumulés dans le cache" — une piste déjà évoquée dans `llm_batching_determinism_results_gpu.md` (section cross-request prompt-cache reuse) mais jamais testée jusqu'ici.
- **Résultat de l'expérience de volume de cache (4 sessions × 15 appels, terminée).** Critère pré-enregistré satisfait : ratio taux d'échec (cache saturé ≥8 prompts) / taux d'échec (cache<8) = 2.00 exactement (seuil ≥2x). Résultat plus frappant que le critère lui-même : le pattern exact d'échecs (rangs 1, 4, 8, 10, 11 sur 15) se reproduit à l'identique sur les 4 sessions indépendantes, malgré un redémarrage à froid complet entre chacune et un contenu/ordre strictement identiques — déterministe, pas du bruit stochastique, ce qui contredit directement la "variance énorme entre essais" observée avec le protocole nonce d'une session précédente (lequel, lui, variait le contenu à chaque tentative — possible que le nonce ait lui-même été la source du bruit observé alors). Répartition par niveau de cache réel (reconstruit depuis les logs Docker horodatés, après correction d'un bug dans le script d'analyse qui incluait des entrées résiduelles d'une session précédente) : cache={0,2,4,5,6} → 0 échec sur 24 essais ; cache=7 → 8 échecs sur 20 (40%) ; cache=8 (capacité max observée) → 4 échecs sur 8 (50%) — 80% de tous les échecs par troncature concentrés aux deux derniers niveaux avant/à saturation. Réserve importante : le design confond contenu, rang et niveau de cache (même séquence à chaque session) — corrélation nette, pas une preuve causale isolée.
- **Pivot demandé par l'utilisateur : investigation d'un second bug distinct trouvé en cours de route.** Le tout premier appel de chaque session échouait systématiquement (5/5 sur les expériences précédentes) selon un mode d'échec jamais vu jusque-là : `cid` renvoyés strictement égaux aux valeurs de `motif` (`CampaignMotif` 601-604) au lieu des vrais `citizen_id` attendus — une confusion de champs par le modèle, pas une troncature. Relecture de `llm_batching_determinism_results_gpu.md` : ce phénomène est déjà documenté sous le nom "Cold start vs. warm: a second, distinct determinism gap" — le tout premier passage d'inférence après un chargement de modèle à froid emprunte un chemin d'exécution GPU différent (heuristiques de sélection de kernel) — et une fonction `_warm_up_llm_client` existe déjà en production (`run_polity_simulation.py`) pour absorber cet effet via un appel jetable avant toute vraie décision, que les scripts de diagnostic de cette investigation n'appelaient jamais, contrairement au pipeline de production. Test direct (6 redémarrages à froid, avec `_warm_up_llm_client` appelé cette fois) : corruption cid=motif disparue (0/6) — confirme un bug déjà connu et déjà corrigé en production, pas un nouveau bug.
- **Un troisième problème révélé par ce même test, non résolu.** Avec le warm-up appliqué, l'appel réel qui suit immédiatement échoue maintenant 6/6, systématiquement par troncature (`finish_reason='length'`) — un échec différent, déplacé plutôt qu'éliminé. Hypothèse testée : le warm-up de production (budget de 32 tokens seulement, garanti de tronquer lui-même sous `think=True`) laisserait une entrée de cache corrompue contaminant l'appel suivant — réfutée en donnant au warm-up un budget généreux (1500 tokens, se termine proprement 6/6) : l'appel suivant échoue quand même 6/6, à l'identique. Nouvelle hypothèse, non testée : la forme du prompt de warm-up lui-même (un stub trivial `"{}"`, structurellement sans rapport avec un vrai prompt métier de plusieurs milliers de tokens) produirait une correspondance partielle de mauvaise qualité contre le cache — mécanisme déjà évoqué ("cross-request prompt-cache reuse") mais jamais testé avec une paire de prompts aussi dissemblable en taille. Confirmé sur données réelles, pas seulement synthétiques : dans le run interrompu `sortition-llm-8y`, `candidacy_considered` et `party_nomination_choice` utilisent tous deux `think=False` (vérifié dans le code), donc `campaign_positioning` était bien le tout premier appel `think=True` réel de ce run, juste après le warm-up de démarrage — et `replays.log` montre qu'il a échoué à sa première tentative avant de réussir au retry, exactement le pattern trouvé sur le banc synthétique.

**Points bloquants**
- **Bug 4, toujours non résolu formellement — mais le dossier est maintenant beaucoup plus riche.** Un mécanisme composite se dessine : comportement de cold-start du tout premier appel, déjà connu et déjà corrigé en production ; contamination structurelle probable liée à la forme du warm-up pour le second appel (hypothèse non testée) ; corrélation nette avec la saturation du cache au-delà (causalité non isolée). Aucune mitigation nouvelle déployée en code de production à ce stade.
- Le ratio 2.00 et la répartition par niveau de cache restent des résultats intermédiaires qui affinent le dossier, pas une résolution — le design de l'expérience confond contenu, rang et niveau de cache, donc rien de tout cela n'isole encore la cause exacte.
- L'hypothèse "forme du prompt de warm-up" n'est pas testée — reste à vérifier si un warm-up avec un prompt structurellement plus proche d'un vrai prompt métier change le résultat du second appel.
- Comment clore formellement l'étape 2 du prompt séquencé (décision sur le bug 4) reste en discussion au moment de la rédaction — pas encore tranché.
- Rien commité pendant cette session : `llm_test_harness/`, le wiring `chamber_deviation` + tests, et les mises à jour de `llm_batching_determinism_results_gpu.md` / ADR-001 restent en attente — ces deux derniers documents reflètent encore l'état d'avant cette session, pas les découvertes ci-dessus.

**Décisions prises**
- Mesurer d'abord le taux d'échec de base (hors resoumission) avant de continuer le test du nonce — *pourquoi* : l'appel d'amorçage, censé toujours réussir, a échoué deux fois de suite avec un nouveau mode d'échec (cid corrompus) au lancement du test ; poursuivre sans recalibrer aurait consommé le budget d'appels GPU sur un protocole déjà suspect.
- Pivoter vers une investigation du volume de cache comme variable continue plutôt que de forcer le protocole nonce/resoumission — *pourquoi* : la corrélation cache observée, gratuite (aucun appel GPU supplémentaire, croisement de logs déjà produits), rouvre une piste plus ancienne et mieux étayée mécaniquement que l'hypothèse resoumission-à-l'identique, elle-même déjà affaiblie par un cas de contrôle qui n'avait pas reproduit le bug la session précédente.
- Pivoter vers l'investigation du bug cid=motif avant de poursuivre l'analyse fine du volume de cache, à la demande de l'utilisateur — *pourquoi* : un second mode d'échec jamais vu, découvert en cours de route sur l'appel d'amorçage lui-même, méritait d'être élucidé avant de construire davantage sur une expérience potentiellement polluée par ce bug distinct.
- Tester l'hypothèse "budget de warm-up" avant l'hypothèse "forme du prompt" — *pourquoi* : ordre du moins coûteux/plus simple à écarter vers le plus coûteux à vérifier ; le budget de tokens se règle en une ligne, la forme du prompt demande une modification plus structurelle du warm-up de production.
- Ne pas committer le travail en attente (`llm_test_harness/`, `chamber_deviation`) tant que le fil bug 4 est ouvert — *pourquoi* : éviter de mélanger un commit de fonctionnalité stable avec une investigation encore mouvante, cohérent avec la discipline déjà établie sur ce projet de garder les scripts d'investigation jetables hors dépôt.

**Prochaines étapes**
- [ ] Tester l'hypothèse "forme du prompt de warm-up" (remplacer le stub `"{}"` par un prompt structurellement plus proche d'un vrai prompt métier) et vérifier si cela change le taux d'échec du second appel.
- [ ] Trancher comment clore l'étape 2 du prompt séquencé (décision sur le bug 4) — discussion en cours au moment de la rédaction.
- [ ] Reprendre les étapes 3-4 du prompt séquencé : nettoyage des dettes techniques (champ `inference_backend`, audit des runs pré-fix), retour au travail v6/v6b.
- [ ] Committer le travail stable en attente (`llm_test_harness/`, wiring `chamber_deviation` + tests) une fois découplé de l'investigation en cours.

**Pour aller plus loin** : `fast_api_voter/scripts/llm_batching_determinism_results_gpu.md` (sections cross-request prompt-cache reuse et "Cold start vs. warm: a second, distinct determinism gap", pas encore mises à jour avec les découvertes de cette session), `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`, rapport généré `fast_api_voter/scripts/bug4_baseline_rate_20260819T235545Z-89a6b3f4.md`, scripts de diagnostic ad hoc de session (`bug4_baseline_rate.py`, `bug4_cache_volume.py`, `bug4_first_call_warmup_check.py`, `bug4_warmup_budget_check.py` — hors dépôt, scratchpad).

---

## 2026-08-17 → 2026-08-18 — Bascule GPU d'Ollama : quatre bugs, une remise en question de la reproductibilité, et une décision d'architecture

**Contexte du jour.** Passage du conteneur `ollama-polity` de CPU à GPU
(RTX 5070 Ti, 16 Go VRAM) pour accélérer l'inférence locale. Attendu : un
simple gain de vitesse. Obtenu : quatre bugs distincts, une remise en
cause sérieuse (puis partiellement rassurante) de la reproductibilité du
pipeline, et une première décision d'architecture documentée en ADR.

**Ce qui a avancé**
- Conteneur Ollama recréé avec `--gpus=all` : confirmé à 100% GPU via
  `ollama ps` (au lieu de 100% CPU).
- **Bug 1 résolu — context-shift silencieux.** Au-delà de ~1800 tokens de
  raisonnement, `num_ctx` jamais fixé par `llm_client.py` (et de toute
  façon ignoré sur l'endpoint OpenAI-compat) laissait le contexte par
  défaut à 4096, provoquant un écrasement silencieux du system prompt en
  cours de génération. Fix : `OLLAMA_CONTEXT_LENGTH=16384` au niveau du
  conteneur. Documenté dans `scripts/ollama_context_window_results.md`.
- **Bug 2 résolu — budget de tokens `decide_campaign_positioning`.**
  `_POSITIONING_THINK_TOKEN_ALLOWANCE` sous-calibré (4000 tokens,
  insuffisant pour un prompt à 5 nominees). Doublé à 8000, vérifié 5/5
  propre avec marge. Suite complète (1526 tests), mypy, flake8 passés.
- **Bug 3 (`cast_votes`) — diagnostic réorienté, pas résolu par un simple
  ajustement de budget.** Signature identique au bug 2 en apparence, mais
  170 tentatives de réplique sur d'anciens chunks dumpés ont toutes échoué
  à reproduire l'erreur — parce que ces chunks dataient d'avant le fix du
  bug 2, et que `vote_cast` dépend en entrée des sorties de
  `decide_campaign_positioning` (dépendance de pipeline jusque-là non
  versionnée dans les dumps de debug).
- **Découverte n°1 — non-reproductibilité au niveau d'un appel isolé,
  confirmée puis largement expliquée.** Un run identique rejoué deux fois
  (même seed, température=0) a divergé dès le tout premier appel LLM du
  pipeline (prompt byte-identique, réponse brute différente), avec effet
  de cascade sur le nombre de candidats retenus. D'abord attribué à un
  non-déterminisme structurel du modèle sur `think=True` (hypothèse
  sérieuse un temps), puis **largement expliqué par un phénomène de
  cold-start GPU** : le modèle est déterministe à 16/16 une fois "chaud",
  et diverge seulement sur le tout premier appel après (re)chargement.
  Confirmé par un test de causalité propre (cycles forcés à froid,
  convergence identique aux reps 2-8 du test précédent).
- **Mitigation cold-start appliquée et vérifiée.** Warm-up (appel factice
  avant la première décision réelle du run) + `OLLAMA_KEEP_ALIVE=60m` au
  niveau conteneur (contre une expiration en cours de run), les deux
  documentés comme complémentaires (fenêtres de risque différentes — l'un
  couvre le tout premier appel, l'autre les suivants). Commit isolé
  proprement du travail Lot 4 en cours (conflit de stash résolu à la
  main, suite complète revérifiée à 1531 tests après réintégration).
- **Spike `llama-server` mené à son terme (16 min, dans le budget de 3h
  alloué).** N'a jamais reproduit le bug de cache-reuse (bug 4,
  ci-dessous), ni à charge légère ni à charge lourde réaliste, avec les
  mêmes poids et le même prompt que la production. Résultat honnêtement
  qualifié d'inconclusif sur la preuve d'immunité, mais cohérent avec
  l'hypothèse que les bugs 1 et 4 sont spécifiques à la couche
  d'orchestration d'Ollama, pas au modèle ni à `llama.cpp` en général.
- **Décision d'architecture actée en ADR** (`docs/adr/ADR-001-serving-
  layer-ollama-vs-llama-server.md`) : rester sur Ollama pour l'instant, ni
  bascule `llama-server`, ni accélération du calendrier vLLM — le
  bénéfice du spike reste non confirmé face au coût d'un nouveau chemin de
  déploiement non vérifié (même calcul déjà fait pour `VllmJsonClient`).

**Points bloquants**
- **Bug 4 — cache-reuse cross-requête d'Ollama (non résolu, le plus
  sérieux actuellement).** Logs montrant un `f_keep` bas juste avant des
  générations qui partent en dérive (`finish_reason='length'` après
  9700+ tokens). Cause probable : le cache de prompt cross-requête
  interne d'Ollama, sur une correspondance partielle de faible confiance,
  semble corrompre la génération — mécanisme distinct du bug 1, non
  couvert ni par `num_ctx` ni par le warm-up. Un test de causalité a
  écarté `f_keep` bas comme cause suffisante isolée (aucun effet sur un
  prompt court `think=False`) — l'interaction avec un raisonnement long
  `think=True` reste nécessaire, mécanisme exact non isolé.
- **La mitigation `--max-batch-replays` ne protège pas contre le bug 4 —
  découverte a posteriori, après un relaunch qui a échoué 6/6.** Le
  motif observé (OK à la 1ère soumission d'un prompt donné, FAIL
  systématique aux resoumissions identiques suivantes) montre que rejouer
  des octets identiques aggrave la situation plutôt que de l'absorber par
  hasard — l'inverse de l'hypothèse sur laquelle la mitigation reposait.
- **Tentative de fiabiliser un banc d'essai de reproduction du bug 4 —
  en cours.** Un premier test de mitigation par variation (nonce inerte
  dans le payload) s'est révélé inconclusif : le cas de contrôle
  (répétition à l'identique) n'a pas reproduit le bug ce jour-là,
  contrairement à un test antérieur qui l'avait montré 2/2. Hypothèse
  actuelle, non confirmée : effet lié au volume de prompts déjà en cache
  (conteneur "chaud avec historique varié" vs conteneur frais) plutôt
  qu'à la seule identité octet-pour-octet du prompt rejoué.
- Aucun champ `inference_backend` dans les métadonnées de run — toujours
  absent.
- Runs journalisés (v6, v6b) produits avant l'ensemble de ces fixes —
  toujours pas audités/marqués comme potentiellement invalides.

**Décisions prises**
- Traiter la non-reproductibilité comme priorité bloquante avant toute
  reprise de la chasse aux bugs de budget de tokens au cas par cas —
  *pourquoi* : patcher un symptôme (bug 3) sans comprendre la cause de
  fond (reproductibilité) risquait de produire un fix qui ne tient pas
  au run suivant — confirmé a posteriori par l'échec de la mitigation
  `--max-batch-replays`.
- Ne pas basculer vers `llama-server` ni accélérer vLLM sur la seule foi
  d'un spike inconclusif — *pourquoi* : un problème partiellement
  caractérisé (Ollama) ne doit pas être échangé contre un problème pas
  caractérisé du tout, même si deux bugs sur quatre pointent vers la
  couche wrapper d'Ollama plutôt que le modèle.
- Fiabiliser un banc d'essai de reproduction du bug 4 avant d'appliquer
  une mitigation (nonce ou autre) sans preuve — *pourquoi* : éviter de
  répéter l'erreur qui vient de coûter un relaunch complet raté (mitiger
  sans avoir vérifié que la mitigation fonctionne dans les conditions
  réelles de déclenchement).

**Prochaines étapes**
- [ ] Rejouer la recette « conteneur chaud + ~9 appels d'historique varié
      + resoumission identique » 2-3 fois pour confirmer qu'elle
      déclenche le bug 4 de façon fiable.
- [ ] Si confirmée : tester le nonce inerte (ou une autre variation
      sémantiquement neutre) contre ce banc avant tout déploiement.
- [ ] Si la reproduction fiable échoue : décider explicitement entre
      repli documenté (nonce non vérifié, jugé sur le run réel) et
      creuser davantage — pas de décision par défaut.
- [ ] Ajouter le champ `inference_backend` aux métadonnées de run.
- [ ] Auditer les runs déjà journalisés (v6, v6b) produits avant ces
      fixes, et les marquer comme non valides pour une future analyse de
      sensibilité.
- [ ] Une fois le bug 4 traité : relancer l'acceptance run v6b.

**Pour aller plus loin** : `scripts/ollama_context_window_results.md`,
`llm_batching_determinism_results_gpu.md` (avec ses notes de correction
datées), `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`,
`audit-precision-plan.md` (§4 du plan de conception, prérequis de
reproductibilité).

---

