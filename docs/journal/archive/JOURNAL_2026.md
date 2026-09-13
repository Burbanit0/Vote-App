# Journal de bord — Archive 2026 (reconstruction rétroactive)

> Entrées 2026-05-03 → 2026-08-19, déplacées hors de
> [`../JOURNAL_DE_BORD.md`](../JOURNAL_DE_BORD.md) lors de sa rotation
> (Lot 12.2, `PLAN_SOLIDITE_TECHNIQUE.md`, 2026-09-11) pour garder le
> journal actif petit. Toutes reconstruites a posteriori le 2026-08-19 (voir
> l'entête de chaque entrée) — ce ne sont pas des entrées écrites en temps
> réel. Entrées plus récentes : [journal actif](../JOURNAL_DE_BORD.md).
> Entrées plus anciennes (2025 et la reprise de janvier 2026) :
> [`JOURNAL_2025.md`](./JOURNAL_2025.md).

---

## 2026-08-19 — Mise en place du journal de bord et reconstruction rétroactive de l'historique du projet

**Contexte du jour.** Réception de l'outillage du journal de bord
(sub-agent `journal-writer`, commande `/log-session`, gabarit de
reconstruction rétroactive) livré sous forme de 4 fichiers dans un
dossier `files/` à la racine du repo. Objectif : installer cet
outillage à ses emplacements définitifs, puis l'utiliser une première
fois pour reconstruire l'historique du projet depuis son tout premier
commit.

**Ce qui a avancé**
- Rangement des 4 fichiers reçus à leurs emplacements définitifs :
  `.claude/agents/journal-writer.md`, `.claude/commands/log-session.md`,
  `docs/journal/JOURNAL_DE_BORD.md` (pré-rempli avec l'entrée GPU du
  17-18/08), `docs/journal/prompt-reconstruction-retroactive-journal.md`
  — dossier `files/` supprimé une fois le rangement terminé.
- **Incohérence trouvée et corrigée** : `journal-writer.md` et
  `JOURNAL_DE_BORD.md` référençaient une commande `/journal`
  inexistante — le fichier de commande s'appelle `log-session.md`, donc
  la commande réelle est `/log-session`. Corrigé aux deux endroits.
- **Reconstruction rétroactive menée à son terme** : tentative d'accès à
  une conversation claude.ai fournie par l'utilisateur en source
  privilégiée — échec en 403 Forbidden (conversation privée, non
  accessible sans authentification). Reconstruction effectuée à la
  place à partir de `git log --all` (1177 commits sur l'ensemble du
  dépôt) et des documents datés du repo
  (`polity-simulation-design-v2.md`, `audit-precision-plan.md`,
  `dev-plan-v0-worktree.md`, `DEMARRAGE-polity-v0.md`), complétée pour
  les paliers polity récents par les notes de session conservées dans
  la mémoire de l'agent (source hors périmètre strict du prompt de
  reconstruction, mais explicitement signalée comme telle).
- **16 entrées reconstruites**, présentées à l'utilisateur pour
  validation, validées telles quelles ("appliquer tel quel"), puis
  insérées dans `JOURNAL_DE_BORD.md` en ordre chronologique inverse
  (16 août 2026 en remontant jusqu'à mars 2025), à la suite de l'entrée
  GPU déjà en place. Chaque entrée reconstruite porte la mention
  explicite de sa méthode de reconstruction en tête, conformément au
  gabarit de reconstruction rétroactive.

**Points bloquants**
- Aucun nouveau — session d'outillage et de documentation, pas de code
  modifié.

**Décisions prises**
- Poursuivre la reconstruction sans la conversation claude.ai source
  malgré l'échec d'accès, plutôt que d'attendre un export manuel —
  *pourquoi* : le git log et les documents datés du repo couvraient déjà
  la majorité des paliers avec un niveau de détail suffisant pour une
  narration honnête, et les notes de session en mémoire comblaient le
  reste pour les paliers récents.
- Ne pas rédiger d'entrée pour une éventuelle relance de l'acceptance
  run v6b après l'entrée GPU, malgré la présence de fichiers non
  trackés (`run_v6b_acceptance.py`, `acceptance_v6b_runs/`) suggérant un
  travail en cours — *pourquoi* : aucune preuve datée (commit ou
  document) ne permettait de confirmer si, quand, ni avec quel résultat
  cette relance a eu lieu ; signalé comme observation non confirmée
  plutôt que comme fait acté.

**Prochaines étapes**
- [ ] Reprendre le fil laissé en suspens par l'entrée GPU du 17-18/08 :
      fiabiliser le banc d'essai de reproduction du bug 4 (cache-reuse
      cross-requête d'Ollama).
- [ ] Clarifier le statut des fichiers non trackés liés à v6b
      (`run_v6b_acceptance.py`, `acceptance_v6b_runs/`,
      `sortition_calibration_runs/`) — travail en cours à documenter,
      ou artefacts à nettoyer.
- [ ] Utiliser `/log-session` en routine à la fin des prochaines
      sessions significatives, maintenant que l'outillage est en place.

**Pour aller plus loin** : `.claude/agents/journal-writer.md`,
`.claude/commands/log-session.md`,
`docs/journal/prompt-reconstruction-retroactive-journal.md`.

---

## 2026-08-16 — Palier v6b, Lots 1-3 : la chambre de tirage au sort, jusqu'à sa première décision LLM

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #151-153) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_v6b_lot1_sortition_config.md`, `project_polity_v6b_lot2_sortition_chamber.md`, `project_polity_v6b_lot3_chamber_deliberation.md`).

**Contexte du jour.** Immédiatement après la clôture de v6a (bloc 15), démarrage du second volet de v6 : une chambre législative tirée au sort, groupe de contrôle contre lequel comparer la dérive de mandat de l'élu.

**Ce qui a avancé**
- **Lot 1 (config+codebook)** : §6bis.3 identifié par grep comme la section la moins spécifiée de tout le plan de conception (4 mentions seulement, aucune sous-section §3.6.x, aucun concept de "loi"/proposition législative nulle part dans le code sur lequel le pouvoir de veto de la chambre pourrait s'exercer). Soumis explicitement à l'utilisateur via `AskUserQuestion` avant toute planification — **l'utilisateur choisit un MVP, le veto est différé** à un futur palier nécessitant un concept de légifération qui n'existe pas encore. Une vraie collision trouvée en implémentation : le plan proposait les codes motif 501/502, déjà utilisés par `CoalitionMotif` — corrigé vers une plage neuve 700-799 avant d'écrire quoi que ce soit.
- **Lot 2 (`sortition_chamber.py`)** : **le risque de calibration déjà signalé au Lot 1 se confirme, mesuré, pas seulement calculé à la main** — à la config par défaut, l'éligibilité stricte "jamais servi" viderait complètement la chambre à partir du tick 16 (87,5% d'un run complet). Résolu par une sélection à deux niveaux : bassin strict tant qu'il peut remplir les sièges, puis relaxation à "pas actuellement siégeant" — la relaxation s'engage *proactivement* (dès le tick 12), la chambre n'est en réalité jamais sous-dimensionnée. Un second vrai bug de signature trouvé en implémentation : `InstitutionalClock.from_config` cherchait `sortition_chamber` sous `institutions`, alors qu'il s'agit d'un champ de premier niveau — corrigé sur les quatre points d'appel concernés.
- **Lot 3 (`chamber_deliberation`, dt=11, la décision LLM)** : chaque membre siégeant reçoit une délibération LLM entièrement isolée de tout canal de pression du §7bis — aucune exposition à la dérive de mandat, ni pression de rue, ni pétition, ni plancher de légitimité. **Deux vrais bugs de fiabilité trouvés par le spike et corrigés dans le code** : la règle de cohérence shifts↔motif échouait à haut taux face au vrai modèle (9/10 rejetés sur un lot de 10) — retirée entièrement, même précédent que la décision de pression de v6a Lot 3 ; un appel de 30 (et même un chunk de 15) laissait tomber silencieusement toutes les décisions sauf les 6 dernières, cause racine tracée à deux tableaux flottants 20-dimensions envoyés en clair par membre — résolu par une constante de taille de chunk dédiée, plus petite, distincte de `MIN_SAFE_BATCH_SIZE`.

**Points bloquants**
- Aucun restant en fin de journée pour ces trois lots. v6b est 3 de 4 lots planifiés — le Lot 4 (acceptance, comparaison élu vs tiré-au-sort) n'est pas encore autorisé.

**Décisions prises**
- Différer le pouvoir de veto à un futur palier plutôt que l'implémenter en MVP — *pourquoi* : décision de l'utilisateur, faute d'un concept de "loi"/proposition législative sur lequel un veto pourrait porter dans le code existant.
- Dispatcher `chamber_deliberation` directement depuis la boucle de tick plutôt que dans la phase d'accountability — *pourquoi* : la garde de retour anticipé de cette phase n'a pas de disjonction `sortition_chamber.enabled`, et la chambre est architecturalement indépendante de la boucle d'accountability présidentielle.

**Prochaines étapes**
- [ ] v6b Lot 4 : acceptance — comparaison de trajectoire `mandate_deviation` (élu) vs `chamber_deviation` (tiré au sort), clôture du palier v6b.

**Pour aller plus loin** : `lot3_chamber_reliability_results.md`, PR #151-153.

---

## 2026-08-16 — Palier v6a complet : le graphe social et la contagion de mobilisation

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #147-150) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_v6_lot1..3_*.md`, `project_polity_v6a_lot4_acceptance.md`).

**Contexte du jour.** Les quatre lots du palier v6a (config, génération de graphe, câblage de la contagion, acceptance) tous conçus, implémentés et fusionnés dans la même journée — le graphe social (§5) et la chambre de tirage au sort (§6bis.3) sont deux fonctionnalités structurellement indépendantes que le plan de conception lui-même déconseille de valider simultanément ; scindées en v6a (ce jour) et v6b (jour suivant, bloc 16).

**Ce qui a avancé**
- **Lot 1 (config+codebook)** : parse le bloc `social_graph:` déjà réservé mais jamais consommé. `evolving` (réécâblage homophile du graphe) est parsé pour échouer bruyamment sur une faute de frappe mais rejeté purement s'il est activé — le point ouvert 🔴 du plan de conception (graphe statique ou évolutif ?) reste réellement ouvert, ceci n'est qu'une garde de parsing.
- **Lot 2 (`social_graph.py`)** : choix `networkx` vs implémentation numpy maison **tranché par mesure réelle**, pas par supposition — zéro dépendance transitive, accepte nativement le générateur RNG du projet, byte-reproductible confirmé, jamais de nœud isolé sur Watts-Strogatz à l'échelle livrée contrairement à Erdős–Rényi (confirmé, documenté comme état légitime à gérer, pas un bug). Correction en cours d'implémentation : le plan approuvé prévoyait de câbler un objet graphe inutilisé dans l'orchestration — retiré, car contrairement aux générateurs de choc (v5 Lot 2), le graphe n'a rien à observer avant le Lot 3.
- **Lot 3 (`neighbors_acting`)** : retire la garde `NotImplementedError` de la porte d'éveil. Résolution du verbe "déjà mobilisée" du plan de conception : compte uniquement le dernier acte `MOBILIZE` *appliqué* d'un voisin (jamais signature/lancement de pétition, catégorie distincte), et scopé à la même cible (un voisin mobilisé contre un élu depuis parti ne compte pas pour le nouveau). Décalage d'un tick, même registre que le décalage `street_pressure` du Lot 6 de v4 : un lot entier de décisions est figé avant que rien n'atterrisse.
- **Lot 4 (acceptance — atomisé vs contagion)** : un seul bras nouveau nécessaire (les runs "mobilisation seule" déjà commités du v4 Lot 8 servent tels quels de référence "atomisée", confirmé par inspection directe qu'ils ne touchent jamais `social_graph`/`events`). **Résultat honnête et nuancé, pas l'histoire naïve "la contagion amplifie la mobilisation"** : sur le mélange cumulé de leviers, la part `MOBILIZE` était en fait légèrement *plus basse* sous contagion (0,629 vs 0,699 atomisé) et la légitimité moyenne finale *plus haute* (0,475 vs 0,370) — la contagion n'est pas un multiplicateur d'amplitude. Ce qu'elle produit réellement : un pic de synchronisation au niveau du tick sans équivalent atomisé — jusqu'à 85 citoyens sur ~100 mobilisés au même tick sous contagion+LLM, contre un maximum de 39 sur la baseline déterministe appariée.
- **Un vrai bug attrapé par le test, pas supposé** : le script d'acceptance ne sérialisait jamais trois champs de métriques pourtant lus par `summarize()` — `KeyError` au tout premier appel, après ~2h de run LLM déjà terminé. Corrigé sans re-lancer le run coûteux, en ré-indexant directement depuis le journal déjà écrit sur disque.

**Points bloquants**
- Aucun restant — v6a est déclaré complet en fin de journée.

**Décisions prises**
- Découpler l'activation de `PressureContext.neighbors_acting` de la modulation de la porte d'éveil — *pourquoi* : le graphe peut alimenter le contexte de dt=10 comme signal d'observabilité pur sans gater mécaniquement qui est consulté, un bras expérimental réel que le Lot 1 avait explicitement préservé.
- Formuler le résultat comme "la contagion change la forme temporelle de la mobilisation (pics synchronisés), pas son volume agrégé, sur cette graine (n=1)" plutôt que revendiquer un effet d'amplification — *pourquoi* : c'est ce que les chiffres montrent réellement, et une revendication plus large ne serait pas soutenue par une seule graine.

**Prochaines étapes**
- [ ] v6b : la chambre de tirage au sort (§6bis.3), scindée de v6a dès le départ.

**Pour aller plus loin** : `THEORY.md` §10.8, PR #147-150.

---

## 2026-08-15 — Vote blanc compétitif (Lot 9) et palier v5 complet en une seule journée : événements exogènes, l'« étincelle »

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #141-146) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_lot9_blank_vote.md`, `project_polity_v5_lot1..5_*.md`), qui documentent chaque bug et chaque correction en cours de route.

**Contexte du jour.** Journée exceptionnellement dense : clôture du dernier item différé de v4 (le vote blanc compétitif), puis les cinq lots complets du nouveau palier v5 (événements exogènes, §8) — configuration, générateurs de choc, extension de la porte d'éveil, décision LLM, et acceptance — tous conçus, implémentés et fusionnés le même jour.

**Ce qui a avancé**
- **Lot 9 (§6bis.2, vote blanc compétitif)** : une élection présidentielle s'invalide quand la part de bulletins classant le blanc en tête dépasse un seuil ; un second tour est programmé, le calendrier fixe est *suspendu* (pas simplement cumulé) jusqu'à résolution ; les candidats de l'élection invalidée sont exclus du second tour (cumulatif à travers les invalidations répétées). **Un vrai bug attrapé par un test qui échouait réellement, pas juste raisonné** : les nouvelles clés `attempt`/`forced` étaient gatées uniquement sur le flag de config, ce qui changeait les octets du journal pour *chaque* élection dès l'activation du flag, même sans aucun candidat — l'hypothèse du plan ("aucun citoyen ne franchit jamais le seuil d'ambition") s'est révélée incomplète (des candidats *peuvent* exister même quand aucune élection ne produit de vainqueur). Corrigé en gatant aussi sur la non-vacuité des candidats.
- **v5 Lot 1 (config+codebook)** : décision structurante — un choc **ne touche jamais directement** la légitimité ; il perturbe la porte d'éveil via un nouveau champ `event_salience` décroissant, qui augmente la consultation — tout le reste passe par le chemin `pressure_action` déjà existant, gouverné par le LLM.
- **v5 Lot 2 (`shock.py`)** : processus de scandale (tirage Bernoulli par tick) + climat économique AR(1). Une vraie mine trouvée en planification : la garde `NotImplementedError` du Lot 1 sur `event_salience` était en fait atteignable indépendamment de `llm.enabled` — protégée seulement par une marge de sécurité étroite (le seuil d'ambition par défaut ne produit jamais de vainqueur au seed=42), pas une garantie structurelle.
- **v5 Lot 3 (`event_salience` + extension de la porte d'éveil + baseline déterministe)** : retire la garde du Lot 2. Deux vrais bugs trouvés et corrigés pendant la planification elle-même (ordre du "step 0" dans la séquence d'accountability corrigé pour matcher la roadmap littéralement ; une cible de scandale capturée une seule fois au tirage plutôt que recalculée en aval, pour éviter une désynchronisation silencieuse sur un tick où scandale et élection coïncident).
- **v5 Lot 4 (`reaction_to_event`, dt=8, la décision LLM)** : forme de message re-dérivée contre le schéma réellement livré des décisions voisines plutôt que gardée telle qu'esquissée dans la roadmap initiale — `ctx.self_gap`/`mandate_dev` abandonnés pour une raison dure (ils exigent un élu réel, qui n'existe pas en vacance présidentielle, alors que dt=8 tourne sur toute la population, vacance ou non). Spike live 12/12 sur qwen3:8b.
- **v5 Lot 5 (acceptance — l'« étincelle »)** : une vraie correction trouvée en direct pendant l'implémentation — l'arme "les deux" (menu de pression complet) faisait rappeler le président en 1-2 ticks sur presque chaque élection, laissant le poste vacant ~82% d'un run de 8 ans, écrasant justement le signal à mesurer. Basculé sur `electoral_only`. Résultat mesuré : taux de consultation 0,695 sur un tick avec choc contre 0,595 sur un tick calme — ratio 1,168, l'« étincelle » est réelle et dans le sens prédit. `mandate_deviation` n'est pas une dérive continue comme supposé mais une concession ponctuelle suivie d'un plateau — nuance honnêtement documentée dans `THEORY.md` §10.7.

**Points bloquants**
- Aucun restant en fin de journée pour le palier v5 — les 5 lots sont clos, `THEORY.md` synchronisé.
- Explicitement **pas** revendiqué : un effet de cascade (`neighbors_acting` reste structurellement `null` à travers tout v5) — scope réservé à v6.

**Décisions prises**
- Regrouper scandale (Poisson) et choc économique (AR(1)) dans un seul lot (Lot 2) plutôt que les séparer — *pourquoi* : même type de décision, même emplacement de séquencement, même point d'arrivée ; les séparer aurait produit un point d'arrêt intermédiaire ininterprétable.
- Basculer l'arme d'acceptance de "les deux" à `electoral_only` en cours de route — *pourquoi* : un dry-run de calibration a montré que l'arme initialement prévue rendait le poste vacant la majorité du temps, empêchant structurellement de mesurer le signal visé.

**Prochaines étapes**
- [ ] v6 : le graphe social (§5), prérequis explicite de l'effet de cascade que v5 ne revendique pas.

**Pour aller plus loin** : `THEORY.md` §10.7, `events_calibration_results.md`, `acceptance_v5_results.md`, PR #141-146.

---

## 2026-08-14 — Clôture du palier v4 : acceptance à 4 modalités, deux bugs LLM réels à l'échelle réelle, bascule vLLM et stockage DuckDB

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #138-140) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_v4_lot8_llm_reliability.md`, `feedback_llm_reliability_investigation.md`, `project_polity_vllm_switch.md`, `project_polity_storage_duckdb.md`), qui documentent le raisonnement derrière chaque bug et chaque choix au-delà de ce que montre le diff seul.

**Contexte du jour.** Le run d'acceptance du Lot 8 (100 citoyens, 20 dimensions d'enjeu, vraie diversité de candidats, runs de 8 ans, 4 modalités de menu de pression) fait ce que les spikes de fiabilité de chaque lot précédent ne faisaient pas : tourner à échelle réelle de production. Deux bugs de qualité de contenu LLM, invisibles à tous les spikes précédents (qui ne vérifiaient que la validité du schéma, jamais la plausibilité du contenu), en sortent.

**Ce qui a avancé**
- **`indexer.py`** livré — le module de réduction de métriques par relecture du journal, nommé mais jamais construit depuis v0.
- **Bug 1 — `decide_campaign_positioning`** : produisait un lot 100% reproductible et dégénéré (un candidat dupliqué, les autres perdus) pour une combinaison de candidats réellement récurrente. Corrigé par `think=True` + un budget de tokens plus large, mesuré.
- **Bug 2 — `cast_votes`** : produisait 100% de bulletins présidentiels blancs à l'échelle réelle (100 votants × 5 candidats × 20 dimensions). Cause racine : le modèle devait juger l'acceptabilité d'un candidat à partir de vecteurs bruts sans définition opérationnelle — exactement le calcul de distance pondérée que la baseline déterministe effectue déjà. Corrigé en précalculant cette distance et en la fournissant au modèle comme un nombre simple, plus une règle mécanique explicite ; ajout de `VoteMotif.ACCEPTABLE_MATCH` (105), aucun motif existant ne décrivant un vote sincère pour un candidat imparfait mais tolérable.
- **Décision méthodologique explicite de l'utilisateur, actée ce jour-là** : face à une sortie suspecte (100% de blanc), investiguer la cause racine plutôt que mitiger rapidement (augmenter les répétitions, raccourcir les délais) — même au prix d'un temps significatif. Le vote blanc doit rester un dernier recours pour le citoyen simulé, jamais une valeur par défaut quand le modèle est incertain.
- Les 4 modalités tournent proprement : 12/12 élections présidentielles remportées, zéro répétition nécessaire, zéro erreur.
- **Bascule vLLM** (`VllmJsonClient`, dispatch par `provider`) livrée en code/config, **jamais vérifiée en direct** faute de serveur GPU disponible dans cet environnement — le `provider` par défaut reste `ollama` explicitement pour cette raison, et parce que `qwen3:8b` sur Ollama est un GGUF quantisé alors que `Qwen/Qwen3-8B` sur vLLM serait en bf16 — poids différents, aucun résultat déjà commité ne transfère.
- **Stockage DuckDB** (`compaction.py`) : résolution du point ouvert §16.6 (DuckDB plutôt que Postgres — aucune stack SQL préexistante, DuckDB embarqué = zéro nouvelle infrastructure). Décodage volontairement restreint au seul champ `motif` (jamais de réécriture du journal brut). Un gotcha DuckDB réel documenté : `x = 'a' AND payload ->> '$.k' = 'b'` non parenthésé mixe mal la précédence et tente de caster tout le payload JSON en nombre.

**Points bloquants**
- Aucun bloquant restant en fin de journée pour le palier v4 lui-même. La bascule vLLM reste **non vérifiée en direct** — reportée explicitement jusqu'à ce qu'un hôte GPU soit disponible.

**Décisions prises**
- Root-cause complet plutôt que mitigation rapide sur les deux bugs de qualité LLM — *pourquoi* : décision explicite de l'utilisateur, motivée par une opinion de modélisation substantielle (le vote blanc doit représenter un vrai désaveu, pas un artefact d'incertitude du modèle).
- Le `provider` par défaut reste `ollama` malgré la bascule vLLM livrée — *pourquoi* : rien n'a été vérifié en direct côté vLLM, et les poids diffèrent (GGUF quantisé vs bf16) — aucun résultat déjà mesuré ne transfère sans nouvelle vérification.

**Prochaines étapes**
- [ ] Lot 9 : vote blanc compétitif (§6bis.2), seul item du palier v4 explicitement différé.
- [ ] Si un hôte GPU devient disponible : vérifier vLLM en direct avant de basculer le `provider` par défaut.

**Pour aller plus loin** : `acceptance_v4_results.md`, PR #138-140, mémoire `project_polity_v4_lot8_llm_reliability.md`.

---

## 2026-08-11 → 2026-08-12 — Polity v4 Lots 6-7 : les deux premières décisions LLM du palier — le mandat peut enfin dériver

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #136-137).

**Contexte du jour.** Après cinq lots de substrat purement déterministe (bloc 11), branchement des deux premières décisions LLM du palier v4 : `representative_response` (l'élu répond à la pression) et `pressure_action` (le citoyen choisit sa pression). À partir d'ici, toute déviation de mandat mesurée est attribuable au LLM.

**Ce qui a avancé**
- **Lot 6 — `representative_response` (dt=6)** : "schéma central de la révision 2" du plan de conception. Spike de fiabilité préalable (16/16 propre sur des lots de 1/3/5/10, via `think=False` sur l'endpoint natif Ollama plutôt que `/v1`) — a aussi révélé honnêtement un défaut d'alignement préexistant sur `decide_campaign_positioning`, déjà livré, sous les mêmes conditions. Le décalage d'un tick (§7bis.7) est réalisé par position d'appel : un appel batché unique tout en haut de la phase d'accountability, avant que la boucle par élu ne mute `street_pressure` — vérifié par un test structurel (muter `street_pressure` après construction du contexte ne peut pas atteindre le prompt). Aucune fonction de repli déterministe : sans LLM, rien ne peut jamais faire diverger `revealed_position` de `pledged_platform`, l'absence d'appel EST le repli.
- **Lot 7 — `pressure_action` (dt=10)** : remplace la baseline déterministe derrière `config.llm.enabled` pour chaque citoyen "éveillé". Réconciliation d'un appel batché figé par tick avec l'état de pétition vivant intra-tick du Lot 5 via un découpage à deux niveaux : le menu constitutionnel est validé et peut rejeter tout le lot (contrainte dure) ; l'état de pétition réel (peut-on signer/lancer *maintenant*) est résolu à l'application, en dégradant un acte devenu caduc plutôt qu'en avortant tout le lot. Spike de confirmation contre le vrai schéma de production (tailles 1/5/20/25, deux modalités de menu, 16/16 propre) puis vérifié live.

**Points bloquants**
- Aucun bloquant restant — les deux lots passent en test hors-ligne (1030 puis suite étendue) et en test live contre le vrai modèle.

**Décisions prises**
- Activer `representative_response` sur `config.llm.enabled ET config.mandate.enabled`, sans nouvelle clé de config — *pourquoi* : garde les deux tests de reproductibilité byte-à-byte LLM existants inchangés, et offre au Lot 8 (acceptance) un bras de contrôle gratuit (leviers de pression actifs, mandat désactivé = le contrôle pur du §7bis.5).
- `revealed_position` accumule la dérive à partir de sa propre valeur courante, jamais de `pledged_platform` — *pourquoi* : c'est ce qui rend `mandate_deviation` non-nul pour la première fois de l'histoire du projet, et fait volontairement diverger l'identité `keep_ratio == mandate_strength` du Lot 5.

**Prochaines étapes**
- [ ] Lot 8 : acceptance, comparaison des 4 modalités de pression, clôture du palier v4.

**Pour aller plus loin** : PR #136-137, `lot6_batch_reliability_results.md`.

---

## 2026-08-09 → 2026-08-10 — Polity v4 Lots 1-5 : légitimité, mandat, pression citoyenne — le substrat déterministe avant tout LLM

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #131-135).

**Contexte du jour.** Premier tiers du palier v4 (légitimité/accountability/pression, §7bis) : cinq lots construisent l'ensemble du substrat mécanique — `L(t)`, écart de mandat, porte d'éveil, action de pression, pétition, vote de confiance — entièrement sans LLM, pour que toute dérive observée à partir du Lot 6 soit imputable au LLM et à rien d'autre.

**Ce qui a avancé**
- **Lot 1** : surface de config (5 nouvelles dataclasses) + réservations codebook (dt=6/dt=10), zéro changement de comportement.
- **Lot 2** : champs `Citizen` (`base_threshold`, `legitimacy_capital`), `accountability.py` (mandate_deviation, self_gap — primitive de distance pondérée réutilisée du vote), phase d'accountability par tick (mesure seule, aucune mutation encore).
- **Lot 3** : `legitimacy.py` — `L(t)` réel. Point de conception central : `L0 = f(force du mandat) = identité` — le seul choix sous lequel `update_legitimacy`, appliqué chaque tick y compris celui de l'élection, garde `L(t) == m` pour tout le mandat quand `écart == 0` (un vrai point fixe, pas une approximation). Test central : la série de légitimité reste exactement plate à `m` sur un run complet de 30 ans, vérifié `m` indépendant de la méthode électorale (deux-tours, IRV, Borda, Schulze).
- **Lot 4** : porte d'éveil (§7bis.9d — qui est consulté chaque tick), baseline déterministe `deterministic_pressure_action`, agrégation de la mobilisation en `street_pressure` réel (remplace le stub à 0.0 du Lot 3). Vérifié numériquement qu'une mobilisation systématique amplifierait `L` de 33,3× à la config par défaut — la baseline gate donc la mobilisation sur le seuil de tolérance du citoyen plutôt que de mobiliser sans condition, sous peine de faire s'effondrer `L` au premier tick de chaque mandat.
- **Lot 5** : levier de pétition (lancement/signature/expiration) + vote de confiance binaire déterministe — ferme le dernier stub de `écart(t)`, rendant les quatre modalités du menu de pression (électoral seul, pétition seule, mobilisation seule, les deux) toutes atteignables pour la première fois.

**Points bloquants**
- Un point documenté sans être corrigé dans ce lot : sous la modalité "les deux" (pétition + mobilisation), l'amplification de la mobilisation (Lot 4) éclipse la mécanique de pétition — noté comme découverte, pas traité dans ce palier.

**Décisions prises**
- `self_gap` reste une pure primitive à ce stade, sans premier appelant réel avant la porte d'éveil du Lot 4 — *pourquoi* : éviter d'exposer une fonctionnalité à moitié câblée avant que son consommateur naturel n'existe.
- Les limites de mandat ne sont appliquées que sur la voie déterministe de candidature, pas sur la voie LLM déjà livrée (v2 incrément 4) — *pourquoi* : `decide_campaign_positioning` calcule une moyenne électorale sur la liste complète des citoyens ; la pré-filtrer changerait silencieusement le contexte d'un incrément déjà livré et vérifié. Fermé plus tard, aux Lots 6/7, une fois `lame_duck` intégré au contexte de dt=6 de toute façon.

**Prochaines étapes**
- [ ] Lots 6-7 : les deux premières décisions LLM du palier v4 (`representative_response`, `pressure_action`).

**Pour aller plus loin** : PR #131-135.

---

## 2026-08-06 → 2026-08-09 — Polity v2 incréments 2-5 : candidature, nomination de parti, positionnement de campagne, coalition — et un vrai bug d'état président sortant

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #123-127, #130).

**Contexte du jour.** Extension du pattern LLM additif inauguré par le vote (bloc 9) à quatre décisions citoyennes supplémentaires, chacune avec ses propres surprises de fiabilité face au modèle réel.

**Ce qui a avancé**
- **Résolution de la question ouverte du bloc 9** : un balayage live de 20 à 25 citoyens (2 répétitions chacun) sur le vrai chemin de production ne reproduit la corruption observée à aucune taille — `MIN_SAFE_BATCH_SIZE=20` inchangé, l'hypothèse retenue est un incident isolé de non-déterminisme d'ordre de réduction flottante en inférence CPU multi-thread, pas une frontière liée à la taille.
- **Incrément 2 — `candidacy_considered`** : seuil `ambition_score` de la voie dominante devient un jugement LLM (la voie de rupture reste déterministe). Bug de fiabilité trouvé en test live : le cadrage subjectif du prompt ("ce citoyen devrait-il se présenter ?") pousse qwen3:8b à consommer tout son budget en raisonnement `<think>` invisible, quel que soit le budget (jusqu'à 6144 tokens) — `think=False` sur l'endpoint natif `/api/chat` d'Ollama (pas `/v1`) résout le problème et est ~7× plus rapide (~35s vs 4+ min pour un lot de 20).
- **Incrément 3 — `party_nomination_choice`** : arbitrage LLM du départage entre candidats déclarés d'un même parti (unité de décision = un parti, pas un citoyen). L'hypothèse initiale (`think=True`, en cohérence avec le vote) était fausse — le même échec `finish_reason='length'` survient indépendamment de la taille de lot ; cause tracée au cadrage subjectif/comparatif du prompt, pas à la taille ; corrigé en `think=False` avant merge.
- **Incrément 4 — `campaign_positioning`** : premier incrément LLM à changer un intrant réel du vote (pas seulement qui est éligible ou comment un bulletin est formé) — un candidat peut décaler stratégiquement sa position affichée. Deux bugs trouvés et corrigés avant le premier run live : les bornes réelles (`max_positioning_delta`/`shifts`) n'étaient pas énoncées dans le prompt (seul un plafond structurel lâche l'était) ; un tri incohérent entre prompt utilisateur et vérification d'alignement faisait échouer tout appel réaliste.
- **Incrément 5 — `coalition_decision`** : décision LLM join/leave par parti non-initiateur après une élection législative ; désignation de l'initiateur reste déterministe. Premier schéma à utiliser un validateur croisé action↔motif Pydantic.
- **Fix hors incréments — président sortant** : `_hold_presidential_election` ne réinitialisait jamais le rôle/office d'un président sortant non réélu, ce qui pouvait laisser deux citoyens simultanément "en fonction" de président. Sans effet observable en v0-v2 (rien ne lisait encore ce champ), mais bloquant pour tout travail futur en dépendant (limites de mandat, légitimité, réponse représentative) — corrigé, test de régression confirmé en échec sans le fix.

**Points bloquants**
- Aucun restant en fin de période — la suite live complète des 5 incréments tourne en ~77 min avec seulement deux échecs, tous deux déjà documentés comme flakiness connue et sans lien avec le code de cet incrément.

**Décisions prises**
- Garder trois fonctions `decode_*_batch` quasi-identiques plutôt que les généraliser prématurément — *pourquoi* : une tentative antérieure de version générique avait concrètement échoué au typage mypy strict, rien n'a changé depuis.
- `party_nomination_choice` et `coalition_decision` ne passent pas par `chunk_voters`/`MIN_SAFE_BATCH_SIZE` — *pourquoi* : ces gardes protègent des lots de *citoyens* (dizaines à centaines), pas des lots de *partis contestés* (une poignée au plus, souvent zéro) ; les y forcer rendrait la fonctionnalité définitivement inatteignable.

**Prochaines étapes**
- [ ] Palier v4 (légitimité/accountability/pression citoyenne).

**Pour aller plus loin** : `ollama_structured_output_results.md`, PR #123-127, #130.

---

## 2026-07-31 → 2026-08-01 — Polity v2 incrément 1 : le premier vote gouverné par un LLM

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #120-122).

**Contexte du jour.** Premier branchement d'un LLM local (qwen3:8b via Ollama) sur une décision citoyenne réelle — le vote — en gardant candidature/parti/coalition sur `simple_rules.py`, additif et jamais une modification de la baseline déterministe.

**Ce qui a avancé**
- **PR A** : fondations hors-ligne (`LlmConfig`, `codebook.py`, schémas Pydantic `VoteCastDecision`/`VoteCastBatch`) — entièrement testables sans Ollama.
- **Lot 0, spike bloquant** : deux problèmes réels trouvés et corrigés avant tout code client.
  - **Finding A** : la sortie structurée d'Ollama ne gère pas l'imbrication `$defs`/`$ref` de Pydantic — un schéma avec un `BaseModel` imbriqué consomme silencieusement tout le budget de tokens sans jamais produire de contenu visible. Fix : déréférencer (`$ref` inlinés) avant envoi.
  - **Finding B** : une instruction "retourne exactement N décisions" seule est insuffisante — le modèle laisse tomber le dernier élément d'un lot de 25 de façon reproductible, quel que soit le budget de tokens. Fix : énumérer explicitement la liste complète des cids attendus dans le prompt système, plus une auto-vérification.
  - Risque ouvert, non résolu ce jour-là : un petit lot de 3 citoyens échoue systématiquement quel que soit le budget de tokens, cause racine inconnue.
- **PR C** : client Ollama synchrone (jamais async — un appel batché est une seule requête/réponse), vote LLM live-vérifié contre le vrai modèle de bout en bout, pas seulement contre le script de spike.
- **Root-cause du petit lot** : en isolant uniquement le nombre de citoyens (dimensions et candidats fixés à la config connue-bonne), 1/3/8/10/12 citoyens échouent tous identiquement, 15 et 25 fonctionnent — attribution propre au nombre de citoyens seul, mécanisme sous-jacent non déterminé (aurait nécessité de comparer quantisations/backends de serving, jugé disproportionné). Recommandation : `MIN_SAFE_BATCH_SIZE = 20`, chunking proche-égal plutôt que taille fixe avec petit reliquat.
- **Consolidation post-merge** : le test live a révélé des bugs invisibles hors-ligne — budget de tokens trop serré pour le raisonnement `<think>` de Qwen3, timeout client sans marge réelle (les deux relevés) ; collision de cid entre candidats et votants (les candidats sont aussi des citoyens, partagent le même espace de numérotation) — corrigée en indexant `ranking` par position 1-indexée dans la liste de candidats plutôt que par cid brut, traduit en cid réel seulement à la frontière bulletin/journal.

**Points bloquants**
- Un lot de 20 citoyens (exactement `MIN_SAFE_BATCH_SIZE`) a corrompu deux fois les mêmes citoyens en test live (blanc=0 avec ranking vide, auto-contradictoire) — marge de sécurité jugée potentiellement insuffisante, question laissée ouverte pour une investigation ultérieure (résolue le 06/08, cf. bloc suivant).

**Décisions prises**
- Client Ollama toujours synchrone, jamais async — *pourquoi* : le script de mesure du déterminisme est délibérément async pour prouver que des requêtes concurrentes divergent (bloc 8) ; ce pattern ne doit pas fuiter dans le code de production, où un appel batché est un seul aller-retour.
- `LlmResponseError` jamais réessayée, `LlmTransportError` réessayée jusqu'à 3 tentatives sans backoff — *pourquoi* : température=0 + seed fixe rend un nouvel essai après une erreur de réponse un no-op garanti ; l'absence de concurrence rend le backoff inutile.

**Prochaines étapes**
- [ ] Résoudre la question ouverte de la frontière de taille de lot (20 citoyens).
- [ ] Étendre le pattern LLM additif aux décisions suivantes (candidature, nomination de parti, positionnement, coalition).

**Pour aller plus loin** : `ollama_structured_output_results.md`, PR #120-122.

---

## 2026-07-31 — Polity v0 : squelette mécanique pur, puis v1 (candidature de rupture) — et une première preuve empirique que le batching LLM casse le déterminisme

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (9 lots v0 + v1 + protocole §5, tous mergés le 31/07/2026 via les PR #117-119).

**Contexte du jour.** Premier jour de code du chantier polity : construire, lot par lot, le squelette mécanique pur défini le 30/07 — 100 citoyens, calendrier électoral, agrégation des scrutins, journal append-only, orchestration — sans aucun appel LLM, pour disposer d'une baseline connue-bonne avant que le risque de non-déterminisme n'existe.

**Ce qui a avancé**
- **Lots 1-3** : chargeur de config typé, entité `Citizen` + génération de population déterministe, initialisation des plateformes de partis par k-means (Lloyd's algorithm déterministe — clusters vides gardent leur centroïde précédent plutôt que d'être réamorcés).
- **Lot 4** : `institutional_clock.py` — un vrai bug de borne trouvé et corrigé : un intervalle de ticks valides *demi-ouvert* (plus « pythonique ») perdait silencieusement la 8ème élection législative avec la config par défaut, parce que 120 partage le même résidu modulo la durée de mandat que le décalage d'assemblée ; corrigé en intervalle *fermé* des deux côtés, vérifié contre les deux exemples travaillés du plan de conception.
- **Lot 5** : `ballot_and_aggregation.py`, adaptateur pur au-dessus du moteur de vote existant (17 méthodes) — un test verrouille la table de dispatch contre l'énumération de `config.py` pour qu'une méthode non supportée échoue au chargement de la config, pas en cours de run.
- **Lot 6** : `simple_rules.py`, la baseline déterministe v0 (règle de vote par distance pondérée aux enjeux, candidature par seuil d'ambition, coalition par plus proche voisin idéologique) — tous les départages explicites (jamais de `max()`/`min()` implicite sur l'ordre d'insertion), pour que le test de reproductibilité byte-à-byte du Lot 8 ne dépende jamais d'un accident d'implémentation.
- **Lot 7** : `journal.py` — écriture flush après chaque événement (un crash ne peut tronquer que la *prochaine* ligne, jamais corrompre une déjà écrite, vérifié par un test qui ajoute une ligne tronquée après 5 écritures propres) ; clés de payload sérialisées avec `sort_keys=True` pour que deux runs produisant un dict équivalent dans un ordre d'insertion différent restent byte-identiques.
- **Lot 8** : `run_polity_simulation.py` — orchestration pure. Le test central : deux runs complets à seed identique produisent des journaux byte-identiques ("le test qui compte le plus"), vérifié maintenant, sur du code purement mécanique, précisément pour disposer d'une baseline connue-bonne avant que le risque LLM (v2) n'existe.
- **Lot 9** : `metrics.py` — les trois seules lignes du §10 calculables sans LLM ni légitimité (nombre effectif de partis de Laakso-Taagepera, taux de cohabitation, durée de vie des coalitions).
- **v1** : candidature de rupture (§2.4, voie rare) — probabilité plate par tick indépendante de la distance idéologique (choix explicite de l'utilisateur), seuil de signatures simulé via un proxy de ratio de sympathisants. Reproductibilité byte-à-byte étendue et vérifiée avec la voie de rupture activée, pas seulement dans la config par défaut.
- **Protocole §5** : vérification empirique, avant même que `llm_behavior_engine.py` n'existe, que des appels LLM séquentiels sont byte-identiques (10 répétitions, redémarrage complet du conteneur inclus) mais que 5/25/50 appels *concurrents* identiques divergent entre eux et de la référence non-batchée — confirmation empirique, quasi certainement liée à la non-associativité en virgule flottante du batching matriciel, que `batch_sharding` doit rester statique et `intra_run_workers` rester à 1.

**Points bloquants**
- Aucun bloquant v0 restant en fin de journée — les 9 lots de `dev-plan-v0-worktree.md` sont clos, 93 tests, mypy strict et flake8 propres. La CI reste rouge un moment sur `develop` après le merge du Lot 9 (mypy 1.16.0 pinné trouve deux erreurs de narrowing invisibles avec un mypy local non pinné 2.1.0) — corrigé le jour même.

**Décisions prises**
- Garder les deux premiers paliers (v0/v1) sur des décisions déterministes explicites plutôt que reporter au LLM — *pourquoi* : elles deviennent le baseline de comparaison contre lequel mesurer ce que le LLM apportera réellement en v2 (sans elles, impossible de dire si le LLM change quoi que ce soit).
- Vérifier le déterminisme du batching LLM *avant* d'écrire le premier module qui en dépend — *pourquoi* : évite de découvrir un problème structurel après coup, une fois le code de production déjà construit dessus.

**Prochaines étapes**
- [ ] v2 : router la première décision citoyenne (le vote) à travers un LLM local.

**Pour aller plus loin** : `dev-plan-v0-worktree.md`, `llm_batching_determinism_results.md`.

---

## 2026-07-30 — Cadrage du chantier Polity : plan de conception, audit de précision, périmètre v0 figé

> Entrée reconstruite a posteriori le 2026-08-19, à partir des documents datés du repo (`polity-simulation-design-v2.md` révision 2c, `audit-precision-plan.md`, tous deux explicitement datés du 30/07/2026 dans leur en-tête) et de `dev-plan-v0-worktree.md`/`DEMARRAGE-polity-v0.md`. Ces documents sont gitignorés (non versionnés) — leur contenu ne peut être cité que verbatim ici, pas diffé.

**Contexte du jour.** Avant d'écrire une ligne de code, rédaction d'un plan de conception complet pour un nouveau chantier : simuler une population de plusieurs milliers de citoyens sur 30 ans (élections présidentielles/parlementaires imbriquées, partis, coalitions, pression citoyenne), où un LLM gouverne l'ensemble des comportements citoyens et seuls le format du bulletin, la méthode d'agrégation et les déclencheurs institutionnels durs restent déterministes.

**Ce qui a avancé**
- `polity-simulation-design-v2.md` (révision 2c) : résolution du bloquant A6 (formule de `écart(t)`), refonte de la pression citoyenne en leviers actionnables (§7bis) plutôt qu'accumulateurs mesurés, schéma de sortie LLM (§3.6) et son codebook de compression (§3.7), reformulation du coût en temps d'horloge (§15bis).
- `audit-precision-plan.md` : passe de relecture systématique identifiant tout ce qui est trop imprécis pour être codé — classé par criticité, avec des bloquants v0 explicites (A1 : granularité du tick tranchée à un trimestre — A2 : origine des partis tranchée à N partis fixes initialisés par k-means — A3 : distinction président/député — A4 : taille/méthode d'attribution des sièges — A5 : règles déterministes v0/v1 spécifiées, futur baseline de comparaison contre le LLM — A6 : formule de `L(t)`).
- Périmètre v0 figé dans `DEMARRAGE-polity-v0.md` : squelette mécanique pur, 100 citoyens, 120 ticks (30 ans × trimestre), décisions déterministes, aucun appel LLM.
- Mise en place d'un worktree Git dédié (`Vote-App-polity`, branché sur `develop`) pour isoler le chantier sans dupliquer le clone.

**Points bloquants**
- Aucun bloquant v0 restant à l'issue de cette journée — c'est précisément l'objet de l'audit de précision : ne rien laisser d'ouvert qui empêcherait d'écrire la première ligne de code.

**Décisions prises**
- Trimestre comme granularité de tick (120 ticks sur 30 ans) plutôt qu'année ou mois — *pourquoi* : compromis entre coût LLM (×3 vs annuel), volume du journal, et finesse de `L(t)`, en gardant la possibilité de raffiner plus tard.
- N partis fixes à `t=0`, plateformes initialisées par k-means sur les positions citoyennes, ni naissance ni mort de parti en v0 — *pourquoi* : la dynamique partisane (naissance/mort) est un trou majeur du document initial, mais ouvrir cette question en v0 aurait bloqué tout le reste ; reportée à un palier ultérieur explicite.
- Remplacer `polity-simulation-design.md` par sa révision v2 plutôt que les faire coexister — *pourquoi* : documenté dans `DEMARRAGE-polity-v0.md` comme le mode de défaillance que le plan lui-même identifie (un concept vivant dans deux documents jamais réconciliés).

**Prochaines étapes**
- [ ] Ouvrir le chantier v0 : squelette mécanique pur, 100 citoyens, sans LLM.

**Pour aller plus loin** : `polity-simulation-design-v2.md`, `audit-precision-plan.md`, `dev-plan-v0-worktree.md`, `DEMARRAGE-polity-v0.md`.

---

## 2026-06-10 → 2026-07-30 — Playground/Laboratoire : consolidation UX, pédagogie, jeu — jusqu'au seuil du chantier polity

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all`. Période dense (près de 400 commits) résumée par motif plutôt que fonctionnalité par fonctionnalité.

**Contexte du jour.** Sur cette période de sept semaines, l'application bascule d'une collection de dizaines de pages/onglets de recherche vers une expérience unifiée : le "Playground" (un instrument de simulation unique, en cinq moments) absorbe progressivement le "Election Lab" et les 40 phénomènes qu'il hébergeait, avant que le tout ne se réorganise encore autour de la pédagogie et de la découverte grand public.

**Ce qui a avancé**
- Playground P0-P5 : canevas d'élection unique, canevas d'assemblée, dynamique temporelle, "banded scorecard", raccords bidirectionnels Lab ↔ Playground.
- Absorption complète du Election Lab (40 phénomènes en 6 familles repliables), puis retrait pur et simple de la page `/election-lab` (redirection).
- Extension des dimensions du modèle d'électorat (3ème axe, bruit de mesure, import/export JSON, vue orbitale 3D).
- Découpage en "moments" narratifs (Électorat → Méthode → Stratégie → Campagne → Bilan), et extraction d'un `/laboratoire` séparé pour l'analyse avancée — séparant délibérément l'instrument pédagogique (Playground) de l'outil d'exploration (Laboratoire).
- Identité visuelle dédiée ("instrument-lab"), i18n complet FR/EN du Playground.
- Harnais de parité moteur client ⇄ backend sur 14 règles de vote — a mis au jour 4 bugs réels côté backend (Bucklin non cumulatif, élimination IRV/Coombs incorrecte, chemin de Schulze erroné, égalité de départage STAR) et 1 défaut côté client, tous corrigés.
- Volet grand public : `/decouvrir` (méthodes de vote pour néophytes), `/campagne` (dynamiques électorales), "À vous de jouer" (bulletin interactif, cinq langages de bulletin), retrait de l'authentification/communauté pour rendre l'application entièrement anonyme et sans état.
- Déploiement public mono-conteneur (Fly.io), analytics anonymes sans cookies (Umami auto-hébergé).
- Rédaction de `THEORY.md` (référence théorique complète, 17 méthodes) et nettoyage de la documentation en amont du pivot suivant (`GUIDE_UTILISATEUR.md`, `README.md`).

**Points bloquants**
- Plusieurs correctifs 422 répétés sur `/simulate` (payload contenant des métadonnées UI, cap de candidats trop bas) — résolus au fil de l'eau, sans qu'un blocage de fond ne persiste.

**Décisions prises**
- Retirer entièrement le Election Lab plutôt que le faire cohabiter avec le Playground une fois l'absorption complète — *pourquoi* : éviter la duplication de state et les "drill-downs circulaires" entre deux surfaces qui montrent la même donnée (mentionné explicitement dans le message du commit de retrait).
- Rendre l'application anonyme (suppression auth/communauté) — *pourquoi* : non détaillé dans les messages de commit au-delà de "backend stateless" ; cohérent avec l'orientation outil de recherche public plutôt que plateforme communautaire.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet ; le chantier suivant, le 30/07, est le cadrage du simulateur polity)

**Pour aller plus loin** : `git log` entre `bf21e83` (2026-06-10) et `6895d21` (2026-07-30) ; `THEORY.md`.

---

## 2026-05-23 → 2026-06-09 — Refonte d'architecture : Flask → FastAPI, Pydantic, TanStack Query/Zustand, Tailwind

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all` (les messages de commit de cette période, structurés en phases numérotées, documentent explicitement l'intention de chaque étape).

**Contexte du jour.** Après trois semaines de sprint fonctionnel pur, une refonte technique en profondeur — menée en phases nommées et séquentielles (Phase 0 à 7) — consolide la base de code avant de continuer à empiler des fonctionnalités.

**Ce qui a avancé**
- **Phase 0-1** : logs structurés (structlog), schémas Pydantic générant des types TypeScript.
- **Phase 2-4** : backend FastAPI monté en parallèle de Flask (`/api/v2/`), puis migration endpoint par endpoint (35 endpoints d'élection, 52 endpoints de théorie, CRUD scénarios, auth via `fastapi-users` + OAuth Google/GitHub, streaming Monte-Carlo Socket.IO) — chaque lot vérifié et fusionné indépendamment.
- **Phase 4.5** : suppression complète de Flask, `api_v2` renommé `api` — le backend est désormais 100% FastAPI.
- **Phase 5** : couche de données frontend réécrite — client `openapi-fetch` typé + TanStack Query, remplacement des Context React par des stores Zustand (auth, UI, lab, élection), suppression d'axios.
- **Phase 6** : `response_model` Pydantic sur tous les endpoints, migration Jest → Vitest, Bootstrap → Tailwind v4 + shadcn/ui (migration fichier par fichier, une soixantaine de PRs).
- **Phase 7** : nettoyage des pages secondaires, ADRs, `security.txt`.
- Durcissement CI continu : mypy strict de bout en bout (26 modules retirés de la liste d'exclusion), flake8 bloquant, ESLint bloquant (0 warning), plusieurs itérations pour stabiliser la couverture de tests sous CI Linux (istanbul ↔ v8, alias `@/`).

**Points bloquants**
- Une série de faux départs sur la configuration de couverture de tests frontend sous CI Linux (alternance istanbul/v8, plusieurs tentatives de résolution de l'alias `@/`) — résolue après plusieurs itérations, documentée dans les messages de commit successifs plutôt que dans un doc dédié.

**Décisions prises**
- Migrer Flask → FastAPI par lots indépendants plutôt qu'en une seule bascule — *pourquoi* : chaque lot de migration (`phase3-batchN`) est fusionné et vérifié séparément, réduisant le risque d'une régression massive difficile à isoler.
- Retirer les Context React au profit de Zustand plutôt que les faire coexister durablement — *pourquoi* : les contextes ont été conservés un temps comme "shims" (facade de compatibilité) avant suppression définitive, seulement une fois tous les consommateurs migrés — logique de bascule progressive et vérifiée déjà observée sur la migration backend.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet, cf. bloc suivant)

**Pour aller plus loin** : `git log` entre `1946395` (Phase 0) et `0dfa354` (2026-06-09).

---

## 2026-05-03 → 2026-05-23 — Sprint « Vote Lab » : des dizaines de méthodes de vote, théorèmes et visualisations

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all`. Le volume de commits sur cette période (plusieurs centaines) rend une reconstruction commit-par-commit disproportionnée ; cette entrée résume le motif plutôt que chaque fonctionnalité individuellement.

**Contexte du jour.** Dans la foulée du pivot du 3 mai, un sprint continu de trois semaines ajoute méthode après méthode, théorème après théorème, à un rythme d'une à plusieurs fonctionnalités par jour.

**Ce qui a avancé**
- Extension du nombre de méthodes de vote comparées de 19 à plus de 30 (Majority Judgment, STV, Copeland, Nanson, Baldwin, Evaluative, SPAV, Phragmén, Quadratic Voting, etc.).
- Une vingtaine de modèles/paradoxes de théorie du choix social implémentés en pages interactives dédiées : théorème d'Arrow, chaos de Plott, paradoxe de Sen, apportionment de Balinski-Young, indices de pouvoir de Shapley-Shubik/Banzhaf, manipulation de Gibbard-Satterthwaite, bulle épistémique (Epistocracy), cascades d'information, biais comportementaux, vote liquide, Conviction Voting, sortition, Duverger, deliberation à la DeGroot, etc.
- Nombreuses visualisations (carte d'idéologie, radar, Voronoi, courses Monte-Carlo, heatmaps, graphes de similarité D3).
- Durcissement sécurité/production en parallèle (CORS, rate limiting, migration CRA → Vite, correctifs CVE Dependabot répétés).
- Fusion des 35 onglets de comparaison en un seul "Election Lab", avant d'être lui-même absorbé plus tard par le "Playground" (cf. bloc suivant).

**Points bloquants**
- Non documentés individuellement à cette échelle — la vélocité du sprint (une fonctionnalité fusionnée toutes les quelques heures) ne laisse pas de trace de blocage au niveau des messages de commit.

**Décisions prises**
- Empiler les fonctionnalités de recherche en pages dédiées plutôt que dans un cœur de moteur unique dès le départ — *pourquoi* : non documenté explicitement, mais cohérent avec l'exploration rapide d'un large espace de sujets avant consolidation (cf. blocs 5-6, qui refondent ensuite l'architecture ET l'UX).

**Prochaines étapes**
- (reconstruction rétroactive — sans objet, cf. blocs suivants)

**Pour aller plus loin** : `git log` entre `e7b3f91` (2026-05-04) et `f484ec9` (2026-05-17), et entre `8c2bc52`…`50db12e` (théorie/recherche, 18-19 mai).

---

## 2026-05-03 — Pivot : abandon du système d'élection, naissance de la plateforme de recherche en simulation

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all` (messages de commit détaillés de cette journée).

**Contexte du jour.** Un seul jour de travail, mais une bascule complète d'orientation : le projet cesse d'être une application de vote électronique pour devenir un outil de recherche/pédagogie sur les méthodes de vote elles-mêmes.

**Ce qui a avancé**
- Remplacement du modèle d'utilité par un modèle de vote spatial explicite (positions idéologiques `[0,1]` par enjeu, distributions centriste/polarisée/gauche/droite), 5 stratégies de vote stratégique (Duverger, enterrement Borda, compromis IRV, vote utile en approbation, exagération en score), moteur de comparaison (regret bayésien, satisfaction majoritaire, vulnérabilité stratégique, cohérence de Condorcet).
- **Suppression complète du système d'élection** : tables `Election`/`Vote`/`Result`, routes, services, pages associées — remplacées par un sandbox de simulation. Conservation de `User`/`Party`/`SimulationScenario`.
- 67 tests unitaires écrits pour les 19 méthodes de vote — l'écriture des tests a révélé deux bugs réels (Minimax et Schulze ne comptaient l'opposition par paire que dans un seul sens, rendant le vainqueur dépendant de l'ordre d'itération Python plutôt que déterministe) — corrigés le jour même.
- Vérificateur empirique des critères d'Arrow, interface de comparaison en sandbox côté frontend.

**Points bloquants**
- Non documentés au-delà des deux bugs Minimax/Schulze, résolus le jour même.

**Décisions prises**
- Retirer entièrement le système d'élection plutôt que le faire coexister avec le sandbox — *pourquoi* : le message de commit documente une restructuration complète du code autour du sandbox de simulation, pas une addition en parallèle.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet, cf. bloc suivant)

**Pour aller plus loin** : commits `a093a15`, `7b0bebd`, `3524b9a`, `4777ec0` (`CLAUDE.md` réécrit pour le nouveau focus).
