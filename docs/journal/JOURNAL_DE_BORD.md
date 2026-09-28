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
> 2026-01-13). Depuis la rotation du 2026-09-27, `JOURNAL_2026.md` garde
> aussi les entrées écrites en temps réel du 2026-08-17 au 2026-08-30.
>
> **Règle de rotation** : quand ce fichier dépasse à nouveau ~100 Ko,
> déplacer ses entrées les plus anciennes vers `archive/JOURNAL_<année>.md`
> (créer le fichier de l'année si besoin) et mettre à jour les liens
> ci-dessus.

---

## 2026-09-24 → 2026-09-27 — Audit des égalités par ordre de listing, première release v0.2.0, polity devient la seule branche de travail

**Contexte du jour.** Plan d'audit approuvé en amont : finir `develop`, sortir la première release `develop→main`, fusionner `develop↔polity` dans les deux sens, puis continuer sur `polity` seule. L'invariant visé sur tout `develop` : réordonner les candidats d'une requête ne doit jamais changer le résultat — une égalité exacte se tire au sort avec la graine de l'endpoint, jamais par ordre de listing ou par plus petit id.

**Ce qui a avancé**
- **Phase A (develop) — fin de la série « égalités par ordre de listing »** : #640 (Hamilton compare les restes exacts, une égalité de reste va au nom), #643 (multi-gagnants : lignes FPTP, complétion Equal Shares, ancre de coalition), #657 (cause racine trouvée : les utilités étaient arrondies à 4 décimales avant classement, ce qui inventait des égalités — arrondi retiré), #659 (playground : assemblée, équité structurelle, no-show), #661 (la transformation stratégique du profile engine inventait une égalité en tête de classement — remplacée par un échange de valeurs), #660 (cache Redis : `GIT_SHA` n'était jamais défini au déploiement, chaque déploiement réutilisait l'espace de cache « dev » — espace de cache par processus désormais).
- **CI** : #641 (watchdog ci-health sur une branche fixe, `pipefail`, groupes Dependabot), #649 (e2e servi sur un build de production `vite build`+`vite preview` plutôt que le serveur de dev — tue les flakes WebKit de modules perdus, proxy `ws: true`), #651 (un corps de réponse d'erreur vide déclenche une alerte), #650 (`quota_type` STV validé — `droop`/`hare`, pas n'importe quel nom renvoyé), #644 (plafonds sur `profile-simulate`, l'électorat capé à 500). Dependabot : #632, #636, #637, #645 (size-limit 14, groupé), #646.
- **Release** : #669 fusionne `develop→main` (470 PR, première release depuis juillet). Titre « Release: … » rejeté par la politique de branche (Conventional Commits requis) ; `diff-cover` rouge par construction (`main` très en retard, 55 lignes déjà passées au gate sur `develop`) ; `main` sans protection → fusion manuelle. Premier vrai dispatch de `release.yml` (run `36292989132`) : **échec** — le job backend n'installait que `requirements.txt` + pytest, jamais `hypothesis`/`schemathesis`/`z3`, un chemin jamais exercé avant. #672 corrige (lockfile dev, plafonds de perf, `test:coverage`+`build` côté front) ; un `/code-review max` sur la branche trouve surtout que la garde de `release.yml` acceptait n'importe quel ancêtre de `main` (un double dispatch aurait pu re-publier une release) → garde « commit exact » + `push --atomic`. #673 porte le correctif sur `main` (Mergify ne file pas les PR vers `main`, fusion manuelle) ; nouveau dispatch → **v0.2.0 taguée et publiée le 2026-09-27** (`git tag` le confirme), premier tag du dépôt.
- **Phase C** : #671 fusionne `develop→polity`, 10 conflits (`main.py`, i18n, un EXP-015 en double → hook renuméroté EXP-017) et plusieurs casses silencieuses corrigées après coup (imports `lazyWithPreload`, `d3-delaunay`→`d3`, `scipy` réajouté, lockfiles régénérés, un ternaire imbriqué sonarjs dans `RunFacts` pour tenir la barre à 264). OBS-026 enregistre que Kemeny-Young et le jugement majoritaire changent de comportement via ce merge (fixes venus de `develop`, pas une anomalie). Le snapshot visuel du Laboratoire a été remplacé par le rendu du job CI (seul diff réel : le lien Polity de la navbar). `polity` avait bougé entre-temps (#670 avait pris OBS-024/025) → renumérotation nécessaire.
- **Phase D** : #674 fusionne `polity→develop` ; `diff-cover` y trouve 5 branches d'erreur polity jamais testées → 5 petits tests ajoutés. #675 est la dernière convergence : `develop` et `polity` identiques. #676 met à jour `CLAUDE.md` et le skill `voter-ci` — **`polity` devient la branche de travail**.
- **E1** : #677 — une égalité de sièges législatifs se tire désormais au sort (`Random("legislative-seats:<seed>:<tick>")`, sans état checkpointé) au lieu d'aller au plus petit `party_id`. Golden et fixture explorer inchangés (aucun run enregistré ne tombait sur une égalité). OBS-027 ; la revue a fait préciser que `choose_party` et le formateur de coalition départagent toujours par `party_id` — des règles propres à polity, laissées telles quelles délibérément.

**Points bloquants**
- Un départage par nom pour les égalités d'utilité a été codé puis **mis de côté** (jamais ouvert en PR) : il échange la dépendance à l'ordre de listing contre une dépendance au nom, et casserait la parité avec le moteur client — à trancher sur les deux moteurs à la fois, pas en urgence.
- Le reste de la série reste ouvert : issues #662 à #667, suivies dans `docs/plan/vote-app/LISTING_ORDER_TIES.md` (#668).
- Mergify a cessé d'auto-mettre les PR en file (probable désactivation côté Mergify, cause non confirmée) : l'utilisateur coche les cases à la main depuis.
- Une demande de suppression des branches distantes fusionnées a été bloquée par le classificateur de permissions (portée jugée non vérifiable) ; les commandes ont été laissées à l'utilisateur.
- #681 (le flaky-check nocturne masque 28 tests de benchmark en échec permanent), #682 (le plancher de couverture backend annoncé à 90 % passe en réalité dès 89,5 %), #683 (`release.yml` devrait réutiliser les CI Backend/Frontend via `workflow_call` plutôt que dupliquer leurs jobs à la main), #684/#685 (les docs de release avaient déjà dérivé de ce qui s'est réellement passé — #685 en cours de correction).

**Décisions prises**
- Départage par nom mis de côté plutôt que shippé — *pourquoi* : trancher sur les deux moteurs (client et backend) en même temps évite de rouvrir un écart de parité pour en refermer un autre.
- Fusion manuelle de `main` (release et correctif) — *pourquoi* : `main` n'a pas de protection de branche et la file Mergify ne fusionne pas vers `main`.
- Garde « commit exact » + `push --atomic` sur `release.yml` — *pourquoi* : la garde précédente acceptait tout ancêtre de `main`, ouvrant la porte à une release dupliquée sur double dispatch.
- `polity` devient l'unique branche de travail à partir de maintenant — *pourquoi* : décision de l'utilisateur une fois `develop` et `polity` convergées juste après la première release taguée.

**Prochaines étapes**
- [ ] Traiter les issues #662–#667 (`docs/plan/vote-app/LISTING_ORDER_TIES.md`).
- [ ] #681 : sortir les 28 tests de benchmark en échec permanent du flaky-check nocturne qui les masque.
- [ ] #682 : faire que le plancher de couverture soit vraiment 90 % (precision=2).
- [ ] #683 : faire réutiliser Backend/Frontend CI par `release.yml` via `workflow_call`.
- [ ] Merger #685 (docs de release remises à jour).

**Pour aller plus loin** : `docs/plan/vote-app/LISTING_ORDER_TIES.md`, `docs/plan/polity/observations.md` OBS-026/OBS-027, `CLAUDE.md` (section Workflow).

---

## 2026-09-20 → 2026-09-26 — vLLM 0.29 puis 0.30, EAGLE-3 adopté, sonde NVFP4, et le premier run complet (30 ans / 500 citoyens)

**Contexte du jour.** Entrée reconstruite depuis les commits/PR, les résultats des scripts de bake-off et les mémoires `vllm-bump-recipe`/`vllm-experiment-queue`/`polity-full-run-prep` (pas de transcript de session associé). Plusieurs sessions se sont enchaînées sur le moteur d'inférence LLM de polity : bump de version, sonde de précision, adoption d'un décodage spéculatif, puis le premier vrai run à grande échelle et sa réplique sur trois graines.

**Ce qui a avancé**
- **vLLM 0.29.0 adopté** (#629, 09-21) : un A/B réel (12 workers, trafic réel) montre 0 gain de la spéculation n-gram en production (0.28.0+n-gram : 323 s/352 s ; 0.29.0 sans spéculation : 310 s/299 s), et un décodage 24-28 % plus lent par appel avec spéculation activée. Coût accepté : les sessions séquentielles (bake-off) ~43 % plus lentes (15,9→22,7 min), 13 réponses sur 174 changent (familles à pensée longue seulement), et la byte-identité à graine égale n'est plus garantie sans spéculation → **OBS-020** ouverte.
- **Sonde de précision NVFP4** (#630, 09-21) : Qwen3-8B en NVFP4 contre l'AWQ shippé — l'effondrement de `representative_response` et `coalition_decision` persiste identique (donc pas un artefact propre au format AWQ), mais le format 4 bits compte ailleurs (`candidacy` 351/500 contre 314 en AWQ, Holm p=0,028) ; coûte 1,8× plus cher — non adopté.
- **vLLM 0.30.0** (#631, 09-24/25).
- **OBS-021** (#642, 09-25) : fallback de `chamber_deliberation` à 5-12 % sur les seeds 1-3, cause trouvée — la validation rejette toute décision à plus de 3 shifts et rien n'est retenté ; ce n'est pas le serveur (le taux est le même sur 0.29.0 à code identique).
- **EAGLE-3** : sonde (#647, 09-25) puis adoption sur le serveur de production (#656, 09-26) — -32 % de temps mur sur 12 workers, -38 % sur deux runs réels 8 ans/p100 à un worker, byte-identique au bake-off plafonné en pensée. L'utilisateur accepte explicitement de perdre la garantie de reproductibilité contre la vitesse et le volume de logs.
- **Sidecar `llm_prompts.jsonl`** opt-in (#655, 09-26) pour pouvoir relire les prompts en détail après coup.
- **S2.4, première vague** (#648, 09-26) : Granite 4.2 8B et Gemma 4 12B testés contre l'effondrement de `coalition_decision` — reste plat sur les deux (Granite -0,033, Gemma +0,000) ; aucun des deux n'est un remplacement direct.
- **Préparation du run complet** (#654, 09-26) : plan, pré-vol, lanceur `systemd-run --user` avec veille désactivée et watchdog de plancher disque.
- **Premier run complet** (30 ans, 500 citoyens, 75 sièges, EAGLE-3, 12 workers relâchés, graine 42, 09-26) : 2 h 08, 11 mandats, 8 présidents, occupation 0,967, replay byte-identique (86 s). Résultats (#658) : OBS-021 confirmée à l'échelle (7,05 % de fallback chambre, cause = dépassement du plafond de shifts), **OBS-022** nouvelle (le positionnement de campagne tourne jusqu'à la limite de tokens sur 3 élections sur 11, seule la relance répond), **OBS-023** nouvelle (le budget de pensée de `vote_cast` sature à 86 % à population 500 contre 25 % à population 100).
- **Réplique sur les graines 1 et 2** (#670, 09-27) : confirme le structurel (fallback chambre 5,8-7,1 %, saturation `vote_cast` 72-86 %), isole ce qui est spécifique à la graine 42 (le positionnement qui tourne en boucle) et découvre deux nouveaux motifs — **OBS-024** (un lot de 3 votes ne répond que pour 1 électeur, identique sur les 3 tentatives) et **OBS-025** (un lot de 25 réactions tombe en entier si une seule dérive dépasse le plafond).

**Points bloquants**
- OBS-020 (byte-identité à graine égale) reste ouverte ; la cause suspectée (Model Runner V2) n'est pas confirmée.
- OBS-021/024/025 partagent le même défaut structurel : une seule réponse invalide fait tomber tout son lot (5 à 25 décisions). Retenter par décision plutôt que par lot n'est pas décidé — c'est un choix de l'utilisateur, pas encore fait.
- OBS-022 : pourquoi ce jeu de partis précis (graine 42 uniquement) fait tourner le modèle en boucle de pensée reste sans cause déterminée.

**Décisions prises**
- Abandon de la spéculation n-gram malgré le coût sur les sessions séquentielles — *pourquoi* : aucun gain sur le trafic réel à 12 workers, qui est le mode de production.
- Sonde NVFP4 non adoptée — *pourquoi* : 1,8× plus lente sans lever l'effondrement des deux types de décision visés.
- EAGLE-3 adopté en sacrifiant la garantie de reproductibilité — *pourquoi* : le call log détaillé suffit à l'objectif d'analyse, la vitesse compte davantage pour un run de cette taille.
- Run lancé « relâché » à 12 workers plutôt que « strict » — *pourquoi* : cohérent avec le choix ci-dessus (vitesse et volume de logs plutôt que reproductibilité).

**Prochaines étapes**
- [ ] Décider comment traiter « une réponse invalide fait tomber tout son lot » (retry par décision, ignorer les shifts nuls avant de compter le plafond, etc.) — OBS-021/024/025.
- [ ] Rouvrir OBS-020 si la reproductibilité redevient un objectif.
- [ ] Étendre un budget de pensée à `campaign_positioning` (aucun bras de bake-off n'existe encore pour ce type — seuls `vote_cast` et `chamber_deliberation` sont couverts).

**Pour aller plus loin** : `fast_api_voter/scripts/check_vllm_speculation_ab_results.md`, `check_nvfp4_precision_probe_results.md`, `check_vllm_eagle3_results.md`, `bakeoff_s24_first_wave_results.md`, `docs/plan/polity/plan-full-run.md`, `docs/plan/polity/observations.md` OBS-020 à OBS-025.

---

## 2026-09-16 → 2026-09-20 — Stage 4 sur le chemin LLM, l'explorateur de runs polity-ui, et le grand ménage anti-sur-ingénierie sur develop

**Contexte du jour.** Entrée reconstruite depuis les commits/PR et `docs/plan/polity/observations.md` (pas de transcript de session associé). Trois chantiers en parallèle : fermer les derniers calibrages Stage 4 du chemin LLM de polity, construire un explorateur visuel des runs, et un audit « sur-ingénierie » du Laboratoire qui débouche, en fin de période, sur la toute première série de correctifs d'égalités par ordre de premier-listé — le point de départ de ce qui deviendra la « Phase A » de l'audit du 24-27/09.

**Ce qui a avancé**
- **OBS-016** (09-14/15) : le disque racine se remplit, le run p500 graine 42 meurt au tick 13, toute la chaîne GPU qui suit échoue en cascade sur écriture impossible. Cause exacte non trouvée (ce qui a rempli le disque avait disparu au moment de l'inspection) ; absence confirmée d'un garde-fou sur le disque libre (seule la mémoire libre était vérifiée avant un run).
- **polity-ui** (#489 à #514, 09-15/16) : un nouvel explorateur qui rejoue un run tick par tick sur une carte (Canvas 2D, ADR-013 adoptée), biographies de citoyens, courbes macro à la demande, API dédiée `/api/v2/polity` — fusionné dans `polity` le 16/09 (#514). **OBS-017** le même jour : WebKit plante une fois en CI en pleine navigation vers `/polity`, non reproduit en isolation, imputé à la contention CPU du runner (2 workers Playwright en parallèle) plutôt qu'à la page.
- **Stage 4 sur le chemin LLM** : pilote (#536), pré-registration (#537), steps 1 à 5 (#539, #540, #542, #549, #550, #552, #569, #572). **OBS-018** : le contrat de réponse (pas le modèle) fixe la position présidentielle dans 22 des 650 réponses observées — corrigé par #545 (« le silence peut citer le motif 303 »). **OBS-019** : montrer au modèle les émotions de ses citoyens, même à poids nul, multiplie la mobilisation par 14 — c'est la présence du champ dans le prompt qui agit, pas un mécanisme de poids. D9 (mobilisation du jumeau déterministe) pré-registrée puis recalibrée (#524, #529, #530) : aucun niveau testé ne qualifie, D9 reste ouvert. S4.1 : `turnout_cost` 0,04 sélectionné et adopté (#570).
- **Audit extérieur du Laboratoire** (#515, `PLAN_SURFACE_EXTERIEURE.md`, 09-16) débouche sur un grand ménage « sur-ingénierie » (#553 à #586, 09-17/18) : code frontend mort supprimé, endpoints API sans appelant supprimés, clés i18n mortes retirées, dépendances front/back inutilisées abandonnées, doublons de helpers/labels/couleurs/popovers fusionnés en une seule source, une image de production unique construite depuis les lockfiles, scanners CI redondants supprimés.
- Scission du contexte Playground en quatre par fréquence de changement (#532, 09-16) et extension de la parité moteur client/backend à l'approbation et au jugement majoritaire (#534, #543, #546, #548).
- **Origine de la série « égalités par ordre de listing »** (#605 à #628, 09-19/20) : Kemeny-Young rendu exact et indépendant de la graine de hash de l'interpréteur (#604, #605), une table de règles unique (#608), fin du « le premier de la liste gagne » sur primaires, districts, assemblée, tallies, Monte-Carlo et théorie (#609, #615 à #618, #621 à #624), RNG global retiré des workers au profit d'un RNG par appel (#619, #625), catalogue de méthodes v1 dérivé de ce que le moteur calcule réellement plutôt que d'une liste à part (#626).

**Points bloquants**
- OBS-016 : cause exacte de ce qui a saturé le disque non trouvée ; aucun garde-fou disque n'a encore été ajouté aux runs longs ou aux chaînes GPU.
- OBS-017 : un seul cas observé, pas reproduit isolément — en observation, sans correctif.
- D9 reste ouvert : aucune recalibration de la mobilisation du jumeau déterministe testée jusqu'ici ne qualifie.

**Décisions prises**
- « Émotions à poids nul » documenté comme non neutre plutôt que corrigé dans l'immédiat — *pourquoi* : établir d'abord ce que révèle OBS-019 avant de décider quel taux de mobilisation est la cible, question renvoyée à une nouvelle pré-registration plutôt que tranchée dans l'urgence.
- Sur-ingénierie traitée par suppression plutôt que dépréciation — *pourquoi* : code sans appelant réel trouvé par l'audit, moins de surface à maintenir en le retirant plutôt qu'en le marquant obsolète.

**Prochaines étapes**
- [ ] Poursuivre la série de correctifs d'égalités par ordre de listing entamée par #605-628 (suite directe : Phase A du 24-27/09).
- [ ] Ajouter un garde-fou de disque libre aux runs longs et aux chaînes GPU (OBS-016).
- [ ] Rouvrir D9 avec un nouveau niveau de recalibration si un besoin se présente.

**Pour aller plus loin** : `docs/plan/polity/observations.md` OBS-016 à OBS-019, `docs/plan/PLAN_SURFACE_EXTERIEURE.md`, `docs/adr/ADR-013-*.md`.

---

## 2026-09-13 → 2026-09-14 — Clôture du chantier CI/qualité (décomposition radon, mutation testing, sonarjs) et sync vers polity

**Contexte du jour.** Entrée reconstruite depuis les commits/PR (pas de transcript de session associé). En parallèle de la session polity du 13/09 déjà journalisée (seed sweep, worktree/venv cassés, `check_llm_stack_versions.py`), une autre session fermait les derniers items du plan de remédiation CI/CD et du plan de solidité technique sur `develop`.

**Ce qui a avancé**
- Dernières fonctions de complexité rang F (radon) décomposées (#431 à #435, 09-13) : `workers*.py`/`election_service.py` dédupliqués (clones jscpd), 4 fonctions ramenées de F à B/C/A — clôture documentée (#436).
- Plan de remédiation CI/CD ajouté (#438), mis à jour avec les vrais résultats et liens de PR (#448), puis fermé le lendemain au profit d'un plan « structural-gaps » qui prend la suite (#482).
- Watchdog ci-health pour repérer les workflows non-requis qui pourrissent en silence (#451), suivi de plusieurs correctifs (#452, #454, #455, #456), puis regroupement des PR de snapshot triviales en cadence hebdomadaire plutôt que quotidienne (#460).
- Score de mutation : plancher mutmut codé à la main remplacé par un cliquet anti-régression (#462) ; fermeture de 53/57 puis 22/27 survivants de mutation sur le vote STAR et le split cycle (#459, #463).
- Lot 14 sonarjs : 19 corrections à haute confiance (#466) — 288 signalements restants, catégorisés et volontairement reportés à un lot dédié (mémoire `sonarjs-debt-status`).
- Bumps d'outillage : Node 20→24 sur tous les workflows (#468), TypeScript 6 + size-limit 13 (#477), jsdom 30 (#479), lockfiles Python compilés ajoutés (#484), image Docker Playwright resynchronisée (#478, #483).
- Sync `develop→polity` (#486, 09-14).

**Points bloquants**
- 288 signalements sonarjs restants (cognitive-complexity 38, no-nested-conditional 101, parameterized-tests 39, prefer-specific-assertions 33, no-unused-vars/no-dead-store 40, ~19 dispersés) — catégorisés mais délibérément reportés à un lot dédié plutôt que traités à la volée.

**Décisions prises**
- Remplacer le plancher mutmut fixe par un cliquet sans régression — *pourquoi* : un chiffre codé à la main dérive avec le temps, un cliquet suit automatiquement les progrès sans plafond arbitraire à remettre à jour.
- Regrouper les PR de snapshot ci-health en cadence hebdomadaire — *pourquoi* : une PR triviale par jour noie le flux de revue sans apporter d'information supplémentaire.

**Prochaines étapes**
- [ ] Attaquer le lot sonarjs dédié (cognitive-complexity en priorité, la catégorie la plus porteuse selon le plan lui-même).
- [ ] Poursuivre le plan « structural-gaps » qui a remplacé le plan de remédiation CI/CD clos ici.

**Pour aller plus loin** : mémoire `sonarjs-debt-status`, `docs/plan/vote-app/` (plan de remédiation CI/CD et plan structural-gaps).

---

## 2026-09-12 → 2026-09-13 — Track D confirme `office_occupancy` sur 10 seeds, un worktree et un venv abîmés par la migration ressurgissent, le système de lois se révèle pur design

**Contexte du jour.** Track D (politique de validation multi-seed du §4 de `plan-distribution-
positions-seeds.md`) devait recevoir son premier vrai sweep multi-seed depuis que le run flagship
existe — jusque-là chaque résultat publié tournait sur la seule seed 42, jamais validée comme
représentative (§4.3, `seed_representativeness: unvalidated`). Lancé le 12/09, le sweep a tourné
toute la journée ; la session du 13/09 devait construire un outil de vérification des versions du
stack LLM avant de lancer le lot p500, ce qui a d'abord exigé de réparer deux dégâts laissés par la
migration Ubuntu (§2026-09-04), puis a débouché sur un audit complet de l'état du projet Polity.

**Ce qui a avancé**
- **Bug réel trouvé sur le tout premier lancement du sweep** (`1edd5c65`) : `--resume-sweep`
  passait `--resume` sans condition dès que le `run_dir` existait, alors que `run_flagship` refuse
  de reprendre un dossier sans `checkpoint.json` — corrigé en vérifiant `checkpoint.json`
  spécifiquement et en passant `--force` sinon.
- **10 seeds indépendantes (1 à 10) exécutées** (`6be5cea6`), chacune un vrai
  `run_polity_flagship.py --engine llm --years 8 --population 100 --seats 15` contre le vLLM de
  production, ~11,5h de temps d'horloge au total. `office_occupancy` : moyenne 0,9303, stdev
  0,0516, min 0,8182 (seed 6), max 0,9697 (seeds 1, 2, 3, 7, 9) — voir
  `fast_api_voter/scripts/run_polity_seed_sweep_p100_results.md`. Règle, pour cette métrique à
  cette échelle, la question de représentativité ouverte au §4.3 : le correctif de vacance
  présidentielle (Track A, livré la veille) tient à travers les seeds, pas seulement sur celle où
  il a été vérifié à l'origine.
- **Effet de bord noté, pas encore un motif** : l'alerte de repli de `representative_response`
  (seuil >10 %, Track C2) s'est déclenchée sur 2 des 10 seeds (2 et 3 : 30,3 % et 36,4 %), muette
  sur les 8 autres. Résultat formalisé dans le plan lui-même, nouveau §4.1
  (`docs/plan/polity/plan-distribution-positions-seeds.md`). Le lot p500 (seeds 1, 2, 42) est
  construit et prêt, explicitement **mis en pause sur demande** après ce lot — pas lancé.
- **Worktree cassé, trouvé et réparé** : `.git` du worktree pointait encore vers
  `/home/burbanit0/Vote-App-polity/.git/worktrees/Vote-App-polity` (ancien chemin, pré-migration
  Ubuntu du 04/09), inexistant — toute commande git échouait. Réparé par `git worktree repair`
  depuis le dépôt principal (désormais `/home/burbanit0/Documents/Dev/Vote-App`) ; `git status`/
  `git log` fonctionnels après coup.
- **Même défaut de migration trouvé dans le venv, seulement contourné** :
  `fast_api_voter/.venv/bin/mypy` (et vraisemblablement les autres scripts installés) porte encore
  le shebang `#!/home/burbanit0/Vote-App-polity/fast_api_voter/.venv314/bin/python` — un venv créé
  `.venv314` à l'ancien chemin, renommé/déplacé sans jamais être recréé, ce qui casse tout
  script-console installé. Contourné en appelant `python -m mypy`/`python -m ruff` directement.
  Confirmé au passage : `flake8` n'est plus installé dans ce venv — `ruff` l'a remplacé projet
  entier (`pyproject.toml`, commentaire « Lot 1 de PLAN_SOLIDITE_TECHNIQUE.md ») ; `CLAUDE.md`
  reste muet sur ce point côté backend.
- **Nouvel outil construit** : `fast_api_voter/scripts/check_llm_stack_versions.py` (474 lignes),
  demandé avant le lancement du p500, pour vérifier que les images Docker et révisions Hugging Face
  épinglées (`docker-compose.llm*.yml`/`.ollama.yml`) sont encore à jour contre leur source réelle
  — reporte seulement, ne bump jamais automatiquement. Deux vrais bugs trouvés et corrigés pendant
  la construction, vérifiés en direct contre Internet :
  - Égress IPv6 de ce sandbox black-holé (SYN-SENT sans résolution, confirmé via `ss -tnp` et
    `curl -6`). `httpx` n'a pas de repli Happy-Eyeballs comme `curl` — un seul mauvais chemin
    dévorait tout le budget de timeout, en série sur ~11 appels HTTP successifs : ressemblait à un
    blocage, était ~180s de retries légitimes mais gâchés. Corrigé en forçant IPv4
    (`httpx.HTTPTransport(local_address="0.0.0.0")`) et un timeout connect/read explicitement
    séparé (5s/15s).
  - L'API REST de tags de `hub.docker.com` plafonne la pagination anonyme (confirmé en direct :
    403 en page 11, « pagination offset too large for anonymous requests ») — bien en deçà des
    ~1174 tags d'`ollama/ollama`. Une version antérieure du script contournait ce plafond en
    triant par récence et en ne lisant que les premières pages, ce qui n'est pas une approximation
    sûre mais activement FAUSSE : elle renvoyait `0.5.5` (poussé 2025-01-11) comme « dernière
    version » contre un vrai `0.33.3` pinné (poussé 2026-09-03), le bruit de tags multi-arch/
    rebuild ayant enterré la vraie dernière release hors de cette fenêtre. Corrigé en basculant
    entièrement sur l'API OCI Distribution v2 (`registry-1.docker.io`, le protocole que
    `docker pull` lui-même utilise pour les dépôts publics anonymes), sans cette limite — vérifié
    en paginant intégralement les ~1174 tags via l'en-tête `Link`.
  - Résultat final, re-vérifié en direct pendant la rédaction de cette entrée : mypy propre, ruff
    propre, et deux vrais écarts de version non appliqués — vLLM épinglé `v0.28.0` vs `v0.29.0`
    disponible (poussé 2026-09-09), Ollama épinglé `0.33.3` vs `0.34.0` disponible (poussé
    2026-09-09) — signalés, délibérément PAS bumpés.
- **Audit à 3 agents** (aucun code touché) de tout `docs/plan/polity/` + `ADR-008` +
  `fast_api_voter/api/domain/polity/`, pour répondre à « où en est le projet, en particulier le
  système de lois ». Confirmé : roadmap v0-v8 tous terminés (v8, bascule vLLM, « DÉBLOQUÉ ET
  TERMINÉ » depuis le 06/09) ; Phase 7 (dry-runs étagés) a passé ses 3 stages, porte franchie le
  11/09 — Stage 4 (le vrai run de 30 ans) est débloqué mais **pas lancé**
  (`plan-flagship-30y-run.md`, lignes 14-16). Qualité LLM par type de décision, état mixte :
  `pressure_action` corrigé et livré (10/09) mais un effondrement aveugle au contenu reconfirmé la
  même semaine via logprobs ; `representative_response` partiellement corrigé (11/09) ;
  `party_nomination_choice` corrigé et vérifié en direct ; `candidacy_considered` — tentative de
  calibration ÉCHOUÉE (accuracy 64 %→58,4 %), pas livrée ; `coalition_decision` — tenté, échoué,
  effondre toujours ; `chamber_deliberation`/`reaction_to_event` — véhicules seulement écrits.
  **Système de lois : pur design, zéro implémentation** — `ADR-008` (statut « Proposed »,
  2026-09-11) spécifie `law_proposal` + overlay borné `AmendableParameter`/`ActiveLaws` +
  `law_version`, mais son propre texte dit « No code changes ship with this ADR », confirmé par un
  grep du dépôt entier (zéro hit réel pour law/legislation/ratification) ; `veto_power` de
  `polity_config.yaml` est parsé mais sans effet comportemental, conséquence directe.
- **Les 4 autres constats de péremption documentaire trouvés pendant l'audit sont désormais
  corrigés** (non commités au moment de la rédaction) : `polity-llm-reference.md` (contredisait sa
  propre date de rédaction sur `representative_response`), `polity-decision-contracts.md`
  (compteur « 1 véhicule sur 6 » remplacé par « 4 sur 6 construits, 2 livrés »),
  `polity-simulation-design-v2.md` (B3 sorti de « reste bloquant avant v2 » — jamais bloqué en
  pratique, le roadmap est allé de v2 à v8 sans le critère prévu ; provider mis à jour vers `vllm`
  en production depuis le 06/09), `plan-coalition-negotiation-v7.md` (section « État » de fin
  passée de « Lot 1 pas encore autorisé » à « TERMINÉ », alignée sur son propre en-tête).
- **Discussion exploratoire NON actée** : une architecture multi-agent-citoyen plus riche (état
  affectif par citoyen pilotant une dérive continue de position dans l'espace 20-dim,
  élargissement de la fenêtre pré-élection à 2 ticks de Track E vers une vraie phase de campagne à
  4 ticks) a été discutée — déterminisme séquentiel du projet vs volonté affichée de sacrifier la
  reproductibilité inter-run pour la diversité narrative et la vitesse ; confirmé que les citoyens
  ordinaires ont des positions statiques aujourd'hui, seuls titulaires/candidats/membres de chambre
  bougent via `apply_shifts`. Reporté explicitement à après l'audit complet — piste ouverte, pas
  une décision.

**Points bloquants**
- Le lot p500 (seeds 1, 2, 42) est construit et prêt mais pas lancé — en pause sur demande.
- Bump vLLM (`v0.28.0`→`v0.29.0`) et/ou Ollama (`0.33.3`→`0.34.0`) avant ou après ce lot : pas
  tranché.
- Le venv `fast_api_voter/.venv` est diagnostiqué cassé (shebangs stale depuis la migration), pas
  réparé — à recréer proprement.
- Le hook `SessionStart` a signalé en début de session que
  `scaleprobe-8y-p500-deterministic-twin` a un `digest.json`/`digest.jsonl` (confirmé) mais pas de
  `TIMELINE.md` — toujours pas traité, nécessiterait `/log-run`.
- L'architecture multi-agent-citoyen (affect, dérive continue, campagne à 4 ticks) reste une
  discussion ouverte, non tranchée.

**Décisions prises**
- Réparer le worktree via `git worktree repair` plutôt que de le recréer — *pourquoi* : préserve
  tout l'état de travail en cours (branche, fichiers non commités) sans reconstruction manuelle.
- Contourner (pas corriger) le venv cassé via `python -m <outil>` plutôt que de le recréer
  immédiatement — *pourquoi* : éviter une opération lourde en plein milieu d'une session
  d'outillage/audit ; réparation reportée délibérément.
- Vérifier les versions du stack LLM via l'API brute du registre OCI (`registry-1.docker.io`)
  plutôt que l'API REST de `hub.docker.com` — *pourquoi* : seule à ne pas plafonner la pagination
  anonyme, la première approche ayant produit un résultat activement faux (`0.5.5` comme
  « dernière version »), pas seulement incomplet.
- Ne pas bumper vLLM/Ollama malgré les deux écarts trouvés — *pourquoi* : un bump doit rester une
  édition délibérée et revue, jamais un effet de bord d'une vérification, et il faut éviter de
  confondre un changement de version avec le p500 imminent.
- Reporter l'idée d'architecture multi-agent-citoyen à après l'audit complet — *pourquoi* :
  décision de l'utilisateur, établir l'état réel avant d'ouvrir un nouveau chantier de conception.

**Prochaines étapes**
- [ ] Lancer le lot p500 (seeds 1, 2, 42), construit et prêt depuis Track D.
- [ ] Trancher le bump vLLM/Ollama avant ou après ce lot.
- [ ] Recréer proprement `fast_api_voter/.venv` (shebangs cassés depuis la migration Ubuntu).
- [ ] Committer les 4 corrections de péremption documentaire encore non commitées et le nouvel
      outil `check_llm_stack_versions.py`.

**Pour aller plus loin** : `fast_api_voter/scripts/run_polity_seed_sweep_p100_results.md`,
`docs/plan/polity/plan-distribution-positions-seeds.md` §4.1, `docs/adr/ADR-008-law-system-seam-
bounds-and-comparability.md`, `docs/plan/polity/polity-llm-reference.md`,
`docs/plan/polity/polity-decision-contracts.md`, `fast_api_voter/scripts/
check_llm_stack_versions.py`.

---

## 2026-09-11 (suite) — Vacance présidentielle corrigée aux deux bouts, deux calibrations sur trois échouent proprement, Stage 3 repasse et déverrouille le run de 30 ans

**Contexte du jour.** Suite immédiate de la session du matin (retractation du « hang », clôturée à
`ebcbd773` 12:37) : combler la vraie lacune qu'elle avait révélée — rien ne distingue un run lent
d'un run figé — puis auditer l'état des 22 plans du dépôt avant d'enchaîner sur les chantiers
restés ouverts de `lets-build-a-solid-spicy-otter.md` : la vacance présidentielle chronique
(Track A), les calibrations de contrat C3 sur les décisions encore effondrées (Track B), trois
derniers points de fiabilité (Track C), l'étalement de l'élection présidentielle sur plusieurs
ticks (Track E), et le design — sans code — du système de lois (ADR-008). Refermé par un second
passage du Stage 3 du run flagship, qui franchit sa porte.

**Ce qui a avancé**
- **Battement de cœur intra-tick** (`1a2093bb`) : `ProgressTracker.record_llm_activity` écrit
  `progress.json` à chaque réponse LLM complétée, plus seulement par tick —
  `last_llm_response_at` (horodatage absolu, jamais « il y a N secondes »), `llm_calls_completed`,
  `tick_in_progress` distinct de `tick`. Porté par un point de passage unique
  (`HeartbeatClient` dans `_llm_client_scope`), donc aucun des neuf types de décision ne sait que
  le battement existe. Nouveau `scripts/check_run_liveness.py` consulte le battement ET le serveur
  d'inférence, refuse de trancher sur la seule preuve côté client — vérifié en direct contre le
  Stage 3 en cours : renvoie `ALIVE` exactement dans la configuration qui avait trompé la lecture
  du matin. 2159 tests passed, ruff/mypy propres (2 erreurs mypy pré-existantes dans
  `workers_playground.py`).
- **Audit des 22 plans du dépôt** (`f8d2bcc2`) : six documents affichaient un état devenu faux,
  dont un cassé le jour même — l'EXP écrit le matin avait pris le numéro « 002 », déjà utilisé sur
  `develop` ; renumérotée EXP-008 (puis EXP-015 après le merge du 12/09, puis EXP-017 après celui du 27/09, la même collision
  s'étant reproduite avec le `develop` synchronisé entretemps — voir l'entrée du 12-13/09).
  Corrigés aussi : `plan-coalition-negotiation-v7` (« Lot 1 pas encore autorisé » alors que les 3
  lots sont livrés depuis ~2 semaines, `rounds_used: 2` vérifié sur un run pop 500),
  `plan-vllm-switch-readiness` (« BLOQUÉ » alors que vLLM est le backend de prod depuis le 06/09),
  `polity-decision-contracts` (« corrections non commencées » contredisant son propre §3 « Livré »
  pour `pressure_action`), `plan-llm-protocol` (TOON « non shippé » pour `candidacy_considered`,
  shippé le jour même), `ci-hardening-plan.md` (supersédé par sa v2 le jour même de sa rédaction,
  jamais marqué).
- **Sonde de précision négative** (`c9396bf4`) : cinquième piste pour les effondrements de
  `representative_response`/`coalition_decision`, après framing adversarial et alignement/RLHF
  (éliminés) et la lacune C3 (ne corrigeait qu'un type sur cinq). Servi
  `ELVISIO/Qwen3-8B-NVFP4A16` (même modèle de base que l'AWQ de prod, quantification poids-seuls
  vérifiée via `config.json`) : négatif sur les deux types — `representative_response` toujours
  P(stance=1) = 0,999996–1,000000 sur les 9 points, `coalition_decision` toujours JOIN partout
  (≥0,88). Les effondrements ne sont pas un artefact de quantification.
- **Track A — vacance présidentielle corrigée aux deux bouts** (`847e26f5`) : 8/8 runs avec un
  recall tombaient en longue vacance (pire cas 87,5 %), prouvé structurel à `simple_rules.py` (un
  double déterministe pur recale deux fois et reste vacant pire que son jumeau LLM). A1+A2 : un
  vote de confiance gagné compte désormais réellement (`support(t)` remplace `mandate_strength` ;
  nouveau champ `averted_recall` empêche qu'un recall du même tick écrase une rétention gagnée —
  cas réel mesuré : président retenu à 69,2 % puis recalé le même tick avant le correctif). A3 :
  élection anticipée sur recall (`institutions.snap_election_on_recall`), vérifiée en direct :
  recall au tick 5, remplacé au tick 6. A4 : continuité de la chambre de tirage au sort pinnée en
  test (75/75 sièges, aucun trou, ticks 0–32). A5 : `office_occupancy` promu en vraie métrique
  (`RunMetrics`/`digest.json`) — corrige au passage les propres chiffres Track 0b du document
  (0,531/0,281 → 0,5152/0,2727, dénominateur faux). 2168 tests passed.
- **Track B — calibrations C3, deux échecs propres et un correctif partiel** : B1
  `representative_response` — correctif PARTIEL livré, énonçant enfin l'échelle de `mandate_dev`
  ([0,1] géométrique) et `street` (asymptote ~6,67) ; P(stance=1) chute à 0,1225 exactement au pôle
  zéro-pression (bascule vers SILENCE) — une vraie distinction zéro/non-zéro, pas un gradient
  lisse. B2 `coalition_decision` — TENTÉ, NÉGATIF, pas livré : même logique de référence (distance
  moyenne inter-partis), aucune amélioration mesurée (écart pôle-à-pôle -0,0004 contre -0,0026
  avant, plus petit en magnitude). B3 `candidacy_considered` — la clause C3 ne s'applique pas non
  plus ici : calibré sur l'ambition moyenne de la population, les déclarations montent de 40,4 % à
  47,6 % et l'exactitude CHUTE de 64 % à 58,4 % contre la vérité terrain. Pas livré. B6 : défaut
  d'échantillonnage corrigé dans le harnais de calibration lui-même (taille 1 tirait toujours du
  même pôle par construction) — la conclusion déjà tirée à une autre taille tenait déjà par une
  preuve indépendante, pas rejouée.
- **Track C — trois derniers points de fiabilité** : C1 isole le repli de
  `party_nomination_choice` parti par parti au lieu de faire échouer tout le tick (Stage 3 :
  10/15 nominations en repli à cause d'un seul parti sur cinq à chaque fois), puis énonce
  explicitement la borne par parti dans le prompt (`candidate_count`) — reproduction exacte du
  checkpoint Stage 3 vérifiée : le même parti répond 19 (légal) au lieu de 26 après correctif, avec
  la même confiance. C2 ajoute un taux de repli PAR TYPE et une alerte (seuil 10 %) à
  `run_digest.json` — le taux global de Stage 3 (0,26 %) masquait un type à 67 %. C3 corrige une
  vraie dérive : le contexte journalisé de `pressure_action` ne portait plus `blank_threshold`
  depuis la Phase E, silencieusement, sur un type à haut volume.
- **Track E — élection présidentielle étalée sur 3 ticks** (`75cde4b1`) :
  `institutions.staggered_election` (défaut `false`) sépare déclaration (J-2), nomination+
  positionnement (J-1) et vote (jour J) au lieu d'un seul tick portant ~1221 décisions LLM d'un
  coup. Neuf tests + vérification live confirment un vainqueur réel élu. PAS câblé dans
  `run_polity_flagship.py` — le changement d'ordre de tirage RNG qu'il force est explicitement
  renvoyé au Track D.
- **ADR-008, design du système de lois** (`92b44071`) : seam = nouveau decision type
  `law_proposal` sur la chambre de tirage au sort, paramètres bornés dans un overlay `ActiveLaws`
  plutôt que de muter le `PolityConfig` figé, comparabilité via un compteur `law_version`
  monotone. Aucun code livré avec cet ADR — sa propre section « When to build » constate que, des
  trois symptômes nommés comme raisons d'attendre, seule la vacance présidentielle est réellement
  corrigée (Track A) ; `representative_response` est partiel, `coalition_decision` reste un
  effondrement non résolu.
- **Stage 3 repassé et validé** (`54598c56`) : `completed`, 32/32 ticks, 8226 événements, 0 ligne
  malformée. Le correctif `vote_cast` (`246da0b`, 10/09) tient à population 500 sur les DEUX
  scrutins présidentiels (6/500 puis 0/500 replis, contre 494/500 et 476/500 avant correctif).
  Mais `party_nomination_choice` devient le pire type mesuré du simulateur (10/15 replis, 67 %) —
  root-cause tracée dans `replays.log` jusqu'à une réponse confiante et fausse
  (`winner_position=26` contre 18-19 candidats, P("2")=0,994). Projection du run de 30 ans revue à
  ~22,5h à partir des vrais chronométrages (tick ordinaire ~246s, tick électoral ~7580s, 120 ticks,
  7 élections), contre 35,6h/40,8h estimés précédemment. `TIMELINE.md` (245 lignes), premier récit
  produit par l'agent `run-narrator`, révèle qu'un président ayant GAGNÉ son vote de confiance
  (69,2 %) au tick 17 a quand même été recalé le même tick par le plancher de légitimité (avant le
  correctif Track A), puis la présidence est restée vacante ticks 18-31 (44 % du run) — tout le pan
  « redevabilité » du modèle à zéro strict sur ces 14 ticks, vérifié dans le journal.

**Points bloquants**
- `coalition_decision` reste un effondrement non expliqué — ni framing adversarial, ni
  alignement/RLHF, ni C3, ni précision de quantification ne l'expliquent. Deux hypothèses
  non tranchées : mauvaise référence choisie côté prompt, ou « rejoindre sur invitation » est une
  politique institutionnellement plausible indépendante de la distance de plateforme — auquel cas
  la réponse du modèle serait correcte, pas effondrée.
- `candidacy_considered` continue de violer la clause C3 (référence de population absente du
  prompt) ; la tentative de calibration a empiré l'exactitude plutôt que de la corriger — le
  véhicule est à repenser, pas juste à finir.
- Stage 4 est débloqué mais soulève une vraie question de conception avant d'être lancé : un
  plancher de légitimité automatique a recalé un président venant de GAGNER un vote de confiance
  populaire explicite ; Track A empêche désormais ce cas précis (A2), mais la question de fond
  (le plancher doit-il pouvoir écraser un vote populaire) reste posée devant toute décision de
  lancer le run de 30 ans.
- Track E n'est pas câblé dans le run flagship — le changement d'ordre RNG qu'il force reste à
  re-baseliner, tâche explicitement renvoyée à Track D.

**Décisions prises**
- Construire `scripts/check_run_liveness.py` plutôt que de fixer un seuil de temps arbitraire pour
  juger un run figé — *pourquoi* : le seul test honnête de vivacité est de consulter le serveur
  d'inférence lui-même, exactement ce que la mauvaise lecture du matin même n'avait pas fait.
- Ne pas rejouer Track B6 corrigé sur la matrice de calibration de `pressure_action` — *pourquoi* :
  la conclusion déjà tirée tenait déjà par une preuve indépendante (12/12 citoyens alternés).
- Ne pas câbler Track E dans le run flagship malgré des tests verts — *pourquoi* : le changement
  d'ordre de tirage RNG qu'il force est une frontière de version à re-baseliner, du ressort de
  Track D, pas de celui-ci.
- Écrire l'ADR-008 maintenant mais différer toute implémentation — *pourquoi* : son propre critère
  de lancement (les effondrements connus corrigés) n'est que partiellement rempli.

**Prochaines étapes**
- [ ] Retenter `coalition_decision` sous un angle différent de C3, ou documenter le verdict
      « réponse correcte, pas effondrée » comme hypothèse retenue.
- [ ] Statuer sur le plancher de légitimité pouvant recaler un président venant de gagner un vote
      de confiance — question nommée par le `TIMELINE.md` du Stage 3, à trancher avant Stage 4.
- [ ] Câbler Track E après le re-baseline RNG que Track D doit produire.
- [ ] Reprendre `candidacy_considered` avec un véhicule différent, la calibration C3 ayant empiré
      l'exactitude.

**Pour aller plus loin** : `docs/exploration/EXP-017-hook-taskcompleted-recit-run-polity.md`,
`docs/plan/polity/lets-build-a-solid-spicy-otter.md` (Tracks A-E), `docs/adr/ADR-008-law-system-
seam-bounds-and-comparability.md`, `docs/plan/polity/polity-decision-contracts.md` §3,
`fast_api_voter/scripts/flagship_runs/` (Stage 3, `TIMELINE.md`).

---

## 2026-09-10 (soir) → 2026-09-11 — `pressure_action` calibré livré, trois runs tués sur quatre jours par un repli manquant, et un run figé qui avait l'air vivant

**Contexte du jour.** Session continue, ouverte pour livrer la Phase E du plan de calibration de
`pressure_action` (signal `blank_threshold`, taille de batch 1) — la dernière étape de
`polity-decision-contracts.md`. Elle a fini par toucher presque tout le protocole LLM de la
polity : vérification en conditions réelles, adoption sélective de TOON, la clôture d'une série de
pannes fatales du run Stage 3 (scale probe population 500) étalée sur quatre jours, un document de
référence complet, la fermeture de la vulnérabilité « un batch invalide tue le run » sur les neuf
types de décision — et, en clôturant la journée, la découverte d'une panne plus grave que toutes
celles corrigées : un run qui se fige sans rien déclencher.

**Ce qui a avancé**
- **Phase E livrée** (`da83b28`) : `decide_pressure_actions` bascule sur les builders calibrés
  (`PRESSURE_THRESHOLD_SIGNAL`), chunké à 1 citoyen par appel. Les deux barres du plan étaient
  déjà franchies — Phase C : 100 % d'accord à batch 1 ; Phase D : coût réel 2,8-3,0x le batch 25,
  pas ~25x supposé. 14 tests réécrits, vérification live 12/12 sur le fil.
- **« A-t-on testé en conditions réelles ? » a fait remonter deux trous** (`1ada806`, `448b72d`) :
  le fichier de tests live `pressure_action` pour Ollama ne peut par construction pas tourner
  contre le vrai serveur vLLM (404 sur `/api/chat`, jamais servi par vLLM — un problème structurel
  de provider, pas une fixture devenue obsolète) ; les tests manquants recopiés dans
  `test_polity_vllm_live.py`, tous deux verts en direct. Et le test `vote_cast` qui échouait en
  direct depuis longtemps envoyait 25 citoyens en un seul batch, une forme que `cast_votes` ne
  produit jamais en production (toujours chunké à 3) — corrigé en testant à la vraie taille de
  production, ce qui donne au passage la première confirmation live du correctif de troncature du
  10/09.
- **Petit run réel de bout en bout** (`11aebdd`) : `run_simulation()` complet, 20 citoyens, 4 ans,
  contre le vrai serveur vLLM. Premier essai : zéro décision `pressure_action` malgré de vraies
  élections — `awakening.enabled`/`legitimacy.enabled` étaient à `false` dans le yaml livré (la
  porte de consultation de `pressure_action` elle-même), donc personne n'était jamais consulté.
  Corrigé en les activant. Résultat : 64 décisions réelles, histogramme `{0: 42, 4: 22}` — pas une
  constante — et un `self_gap` moyen matériellement plus élevé pour ceux qui choisissent le levier
  le plus affirmé (0,382 vs 0,234), même sens que la matrice de calibration.
- **TOON adopté, mais seulement pour `candidacy_considered`** (`1223c3c`) : 853→794 tokens de
  prompt (-6,9 %), précision IDENTIQUE contre la vérité terrain (16/25 dans les deux formats).
  `pressure_action` avait montré l'inverse (vraies économies, vraie régression de qualité) et reste
  sur JSON — pas de politique « TOON partout », chaque type tranche son propre A/B.
- **Trois runs multi-heures tués net par un repli manquant, sur quatre jours** : `chamber_deliberation`
  (08/09, Stage 1 smoke pop 100 — une boucle Mode-A `finish_reason='length'` épuise chaque replay à
  l'identique et remonte hors de `run_simulation`, réparée ce jour-là) ; `party_nomination_choice`
  (11/09, Stage 3 pop 500, `a8cf2f4`) — un `winner_position=26` hors bornes, contre **deux partis
  contestés distincts, l'un à 18 candidats déclarés, l'autre à 19** (vérifié verbatim dans le
  `replays.log` du run : `grep -o "winner_position=[0-9]* is out of range for its own [0-9]*
  declared" replays.log`) ; `representative_response` (11/09, Stage 3 pop 500, `a691e29`), 2,5h
  dans le run, sur deux shifts ciblant la même dimension. Un quatrième arrêt le même jour n'était
  pas un bug : un reboot de l'hôte a tué le process en cours à 07:14 (`0454010`).
- **Et une illustration mesurée que « repli » ne veut pas dire « sauvetage gratuit »** : le 10/09
  (`246da0b`), ce même Stage 3 a *survécu* à un défaut `vote_cast` (le prompt disait de classer
  tout candidat acceptable, le validateur imposait un top-5) précisément parce que `vote_cast` a un
  repli depuis le 06/09 — en basculant 494/500 puis 476/500 votes sur deux scrutins. Ces deux
  élections ont, dans les faits, été tranchées par la ligne de base déterministe pendant que le
  journal les enregistrait comme un run LLM.
- **De la lecture manuelle de ces arrêts est né le besoin d'un récit lisible par run** (`658b3e7`,
  `0454010`) : mesuré, pas supposé — seuls 3 des 8 répertoires de run flagship avaient un
  `viz_export.json`, écrit après le `try/finally` et donc sauté par toute exception. Nouveau
  `run_digest.py` écrit un `digest.json` à CHAQUE fin de run (succès, crash, SIGTERM), classifié
  sur si l'arrêt a été *demandé* plutôt que sur le type d'exception. Vérifié d'abord en synthétique
  (3/3 SIGTERM en cours de run produisent `outcome=interrupted` avec des comptes de ticks honnêtes),
  puis, en toute fin de journée, **en conditions réelles sur un vrai run de ~2h** — voir plus bas.
  Agent `run-narrator` + commande `/log-run` + hook `SessionStart` ajoutés pour transformer ce
  digest en `TIMELINE.md` — le hook `TaskCompleted` a été testé en premier et ne se déclenche pas
  pour les tâches Bash en arrière-plan (vérifié comme un vrai négatif : un hook `PostToolUse`
  ajouté dans le même changement, lui, s'est déclenché dans la même session).
- **Document de référence écrit** (`bdc2e4f`, `polity-llm-reference.md`, ~500 lignes) : demandé
  pour pouvoir conseiller sur l'état réel du simulateur sans relire 4000 lignes de moteur. Deux
  affirmations contradictoires d'agents de recherche vérifiées contre le code avant publication :
  la négociation de coalition EST une vraie boucle multi-tours, et la config flagship OUVRE bien
  le menu de pression (`electoral_only=False`, pétitions et mobilisation actives) — confirmé
  contre le journal d'un run réel dont des citoyens ont signé des pétitions. Ça décide si
  l'effondrement documenté de `pressure_action` en menu fermé s'applique aux vrais runs : non,
  c'est le bras de contrôle du palier §11.4.
- **Les neuf types de décision LLM ne peuvent plus tuer un run** (`9929651`) : les quatre qui
  pouvaient encore mourir ont chacun un repli déterministe reproduisant leur propre ligne de base
  §11.4 — `candidacy_considered` → `simple_rules.decide_candidacy` (seuil d'ambition),
  `campaign_positioning` → l'épingle sincère de `declare_candidacy` (aucun shift),
  `pressure_action` → `deterministic_pressure_action` à partir du contexte figé déjà vu par le
  modèle, `reaction_to_event` → le delta plat de `deterministic_reaction_to_event`. Deux trous
  trouvés en chemin, refermés : `party_nomination_choice` avait déjà un repli, mais son `try`
  n'entourait que la validation, pas l'appel LLM — un budget de replays épuisé passait à travers, un
  trou à moitié fermé qui se lisait comme fermé ; `coalition_decision` relançait l'exception au
  tour 1 alors qu'un échec au tour ≥2 dégradait proprement depuis v7 Lot 2 — aligné sur le même
  repli, mais explicitement PAS sa ligne de base (le polity finit sans gouvernement là où
  `form_coalition` en aurait produit un réel, choix de modélisation assumé et révisable). Les neuf
  types varient désormais l'échantillonnage en cas de retry (température 0,3 + décalage de seed
  par tentative, jamais au premier essai). Mesuré sur le run Stage 3 en cours pendant l'écriture :
  155 batches rejetés, `vote_cast` en a récupéré 108/115 et `chamber_deliberation` 38/38 grâce à
  cette variation — sans elle, ces 155 étaient irrécupérables par construction. Honnêteté
  nécessaire : les six types tout juste corrigés n'ont enregistré aucun rejet sur ces 15 ticks —
  une assurance contre une queue de distribution, pas un correctif pour un taux observé. Suite
  verte : 2146 passed, 43 skipped, mypy/ruff propres (les 2 erreurs mypy restantes sont
  préexistantes, dans `api/domain/election/workers_playground.py`, vérifié en stashant).
- **Incident mineur en fin de session** (`e947472`) : le hook de capture pre-commit a écrasé
  l'entrée de `bdc2e4f` dans `docs/journal/commits.jsonl` (son stash/restore est entré en conflit
  avec sa propre écriture fraîche). Récupérée verbatim depuis le patch laissé dans le cache
  pre-commit, réinsérée dans l'ordre chronologique, chaque ligne re-parsée en JSON avant écriture
  — `--no-verify` sur ce seul commit correctif pour ne pas retomber dans la même course.
- **Le run Stage 3 lui-même a fourni la première validation en conditions réelles de la chaîne
  SIGTERM → digest de `658b3e7`.** Il n'avançait pas lentement, il était bloqué : diagnostiqué
  après coup (1,92s de CPU en 1h59, journal inchangé depuis 09:57:51, une socket ESTABLISHED vers
  vLLM ouverte avec Recv-Q et Send-Q à 0 pendant que vLLM lui-même répondait normalement à
  `/v1/models` en 4 ms) — l'`eta_min` de `progress.json` était simplement périmé, écrit au dernier
  tick complété deux heures plus tôt. Tué proprement par SIGTERM sur décision de l'utilisateur :
  `digest.json` obtenu avec `outcome: interrupted`, `error: {"type": "_Terminated", "message":
  "received signal 15"}`, 7447,8s écoulées, 16/32 ticks journalisés, checkpoint au tick 15, 4624
  événements, **0 ligne malformée**, 3 replis, 240 retries, 1 mandat, 7 entrées de chronologie
  institutionnelle — vérifié directement dans le fichier. Relancé depuis ce checkpoint, désormais
  sur le code de `9929651`.

**Points bloquants**
- **L'erreur de la journée, et elle est de moi : j'ai diagnostiqué le run Stage 3 comme figé et je
  l'ai fait tuer. Il ne l'était pas. Il travaillait.** ~2h de calcul jetées sur une mauvaise
  lecture ; seul le checkpoint au tick 15 a limité la perte à un tick. Les quatre indices qui
  semblaient accablants ont tous une explication innocente : (1) 1,92s de CPU en 1h59 — normal, le
  processus est bloqué ~100 % du temps sur un serveur GPU et parser un petit batch JSON coûte moins
  d'un jiffy de 10 ms ; (2) journal muet pendant ~2h — normal, `cast_votes` décide **toute la
  population** avant que l'appelant ne journalise quoi que ce soit, soit ~167 appels séquentiels à
  ~3/min à population 500, donc ~1h de silence légitime, et le tick 16 est un tick d'élection (8 à
  10× un tick ordinaire, ce que je savais déjà) ; (3) une socket ESTABLISHED ouverte 1h41 plus tôt
  — ma pire inférence : httpx réutilise une seule connexion keep-alive, l'âge de la socket ne dit
  strictement rien sur l'âge de la requête ; (4) ETA de `progress.json` périmé — normal, il n'est
  écrit qu'à chaque tick complété.
  **La vérification que je n'ai pas faite et qui tranche en dix secondes : demander au serveur s'il
  travaille.** `docker logs vllm-polity` montrait `Running: 1 reqs` à 130-170 tok/s en continu,
  `nvidia-smi` 94 % de GPU, et un débit stable de 84 requêtes en 30 min avec notre processus pour
  seul client. Il n'y a pas de bug de gel. Il n'y en a jamais eu.
- **La vraie lacune, elle, est réelle : rien ne permet de distinguer un run lent d'un run figé.** À
  population 500, un run peut légitimement passer une heure sans une seule écriture de journal,
  sans mise à jour de `progress.json` et à ~0 % de CPU. Il faut un **battement de cœur intra-tick**
  dans `progress.json` (décisions complétées, phase courante, date de la dernière réponse LLM),
  pas seulement une écriture par tick. D'ici là, le seul test de vivacité honnête est le log du
  serveur LLM — et toute affirmation « le run est bloqué » qui ne l'a pas consulté doit être tenue
  pour fausse, y compris la mienne.
- `candidacy_considered` échoue à la même clause de contrat (C3, état perceptible) qui avait causé
  l'effondrement de `pressure_action` : `ambition_score` est envoyé sans aucune référence de
  population. Un run réel montre ~40 % des citoyens se déclarant candidats, invraisemblable face à
  une vraie polity. Le véhicule de correction est déjà écrit dans `polity-decision-contracts.md`,
  non construit.
- Rien n'agrège encore `payload.llm_fallback` en alerte lisible — seul `progress.json` porte un
  `fallback_count` brut, sans seuil ni porte. Un run dégradé sur la moitié de ses décisions et un
  run qui n'a jamais basculé finissent tous les deux et se ressemblent.
- Question ouverte, nommée mais non tranchée : donner aux DEUX tours de `coalition_decision` un
  repli `form_coalition`, ou garder la sémantique d'abandon actuelle du tour 1.

**Décisions prises**
- Adopter TOON pour `candidacy_considered` seul, pas pour `pressure_action` — *pourquoi* : chaque
  type de décision tranche son propre A/B (gain de tokens ET précision inchangée pour l'un, gain
  de tokens mais régression de qualité pour l'autre) plutôt qu'une politique uniforme.
- Faire dégrader les neuf types de décision au lieu d'en laisser mourir quatre — *pourquoi* :
  trois pannes fatales sur quatre jours, toutes sur des types qui n'avaient jamais échoué
  jusque-là, montrent qu'un run de plusieurs heures ne peut pas dépendre de l'absence historique
  d'échec pour rester en vie.
- Garder la sémantique d'abandon de `coalition_decision` au tour 1, alignée sur le tour ≥2 déjà en
  place depuis v7, plutôt que d'inventer un repli `form_coalition` pour ce cas précis —
  *pourquoi* : hérite d'une règle déjà livrée plutôt que d'improviser une deuxième règle pour un
  échec à un round d'écart ; documenté au code comme choix révisable.
- Utiliser `SessionStart` plutôt que `TaskCompleted` pour le hook de narration de run —
  *pourquoi* : `TaskCompleted` ne se déclenche pas pour les tâches Bash en arrière-plan (vérifié,
  pas supposé), et un reboot hôte qui tue un run en cours ne laisse justement rien tourner en
  session pour le détecter autrement.
- Tuer le run Stage 3 figé par SIGTERM plutôt que d'attendre plus longtemps — *pourquoi* : aucun
  signal disponible (progression, repli, crash) n'indiquait qu'il avançait encore, et la reprise
  depuis le checkpoint du tick 15 récupère de toute façon les correctifs de `9929651`.

**Prochaines étapes**
- [ ] Ajouter un battement de cœur intra-tick à `progress.json` (décisions complétées, phase
      courante, horodatage de la dernière réponse LLM), pour qu'un run lent soit distinguable d'un
      run figé sans avoir à lire les logs du serveur — la lacune qui m'a fait tuer un run sain.
- [ ] Attendre la fin du Stage 3 (relancé depuis le tick 15), narrer son `TIMELINE.md`, et mettre à
      jour `plan-flagship-30y-run.md` avec le verdict Stage 3 — porte d'entrée du Stage 4 (le run
      flagship de 30 ans).
- [ ] Construire le véhicule de correction C3 de `candidacy_considered` déjà écrit dans
      `polity-decision-contracts.md`.
- [ ] Agréger `payload.llm_fallback` en quelque chose de visible (seuil, avertissement, ou porte)
      plutôt que de laisser un run dégradé ressembler à un run réussi.

**Pour aller plus loin** : `polity-llm-reference.md` (référence complète, §4.4 pour la table des
runs tués et l'illustration `vote_cast`, §10 pour les lacunes connues), `polity-decision-contracts.md`
(véhicule de correction C3), `plan-flagship-30y-run.md` (Phase 7 Stage 3),
`fast_api_voter/scripts/flagship_runs/scaleprobe-8y-p500-v2-postfix/run/scaleprobe-8y-p500-v2-postfix/digest.json`,
`fast_api_voter/scripts/check_pressure_shipped_wiring_results.md`,
`check_pressure_small_run_results.md`, `check_toon_candidacy_ab_results.md`.

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
