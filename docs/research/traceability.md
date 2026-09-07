# Traçabilité code ⇄ théorie — Vote-App

Ce document relie chaque méthode/modèle implémenté au fichier de code qui le
porte, à la section de [`THEORY.md`](../../THEORY.md) qui le documente, et à
la référence académique correspondante (clé BibTeX dans
[`bibliography.bib`](./bibliography.bib)).

Statuts : `implémenté` · `partiel` (logique présente, pas de test/contrôle
empirique dédié) · `prévu` (mentionné en théorie, pas encore codé).

> Ce tableau est un point de départ généré à partir d'une exploration du
> repo au 2026-07-29. Les correspondances marquées `(à confirmer)` doivent
> être vérifiées par l'agent `theory-curator` ou par toi — je n'ai pas
> tracé chaque fonction ligne à ligne.

## Méthodes de vote

| Méthode | Fichier(s) | THEORY.md | Référence | Statut |
|---|---|---|---|---|
| Plurality | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — (méthode de référence, pas de papier fondateur unique) | implémenté |
| Two-Round | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — | implémenté |
| Borda Count | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — (Borda, 1784, non retenu dans la bibliographie actuelle) | implémenté |
| Approval Voting | `engine/utils/simulation_score_utils.py` (à confirmer) | §2.1 | `brams1978` | implémenté |
| IRV | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — | implémenté |
| Coombs / Bucklin | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — | implémenté |
| Minimax (Simpson-Kramer) | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — | implémenté |
| Schulze | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | — | implémenté |
| Kemeny-Young | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | `kemeny1959` | implémenté |
| Copeland / Nanson / Baldwin | `engine/utils/simulation_ranked_utils.py` (à confirmer) | §2.1 | `nanson1882` | implémenté |
| Simple Score / STAR / Median / Majority Judgment | `engine/utils/simulation_score_utils.py` (à confirmer) | §2.2 | `balinski_laraki2010` | implémenté |
| Quadratic Voting | `engine/utils/quadratic_voting.py` | §2.3 | `lalley_weyl2018` | implémenté |
| Quadratic Funding | `engine/utils/quadratic_voting.py` | §2.3 | `buterin2019` | implémenté |
| SPAV / Phragmén | `engine/utils/simulation_multiwinner_utils.py` (à confirmer) | §2.3 | — (Phragmén, 1894, non retenu dans la bibliographie) | implémenté |

## Théorèmes d'impossibilité et paradoxes

| Concept | Fichier(s) | THEORY.md | Référence | Statut |
|---|---|---|---|---|
| Théorème d'Arrow (explorateur interactif) | `domain/theory/workers.py` | §3.1 | `arrow1951` | implémenté |
| Théorème de Gibbard-Satterthwaite | `domain/theory/workers.py` (à confirmer) | §3.2 | `gibbard1973`, `satterthwaite1975` | partiel |
| Chaos de Plott | `domain/theory/workers.py` (`_plott_chaos_worker`, exporté `plott_chaos`) | §3.3 | `plott1967` | implémenté |
| Paradoxe List-Pettit | `domain/theory/workers.py` (`_judgment_aggregation_worker`, exporté `judgment_aggregation`) | §3.4 | `list_pettit2002` | implémenté |
| Paradoxe libéral de Sen | `domain/theory/workers.py` (`_sen_paradox_worker`, exporté `sen_paradox`) | §3.5 | `sen1970` | implémenté |
| Impossibilité d'apportionment (Balinski-Young) | `domain/theory/workers.py` (`_apportionment_worker`, exporté `apportionment`) | §3.6 | `balinski_young1982` | implémenté |
| Paradoxe de Condorcet | `domain/theory/workers.py` (à confirmer) ; propriété testée : `api/tests/test_hypothesis_condorcet.py` (Schulze/Copeland/Minimax élisent le vainqueur de Condorcet sur profils générés) | §4.1 | — (Condorcet, 1785) | implémenté |
| Effet spoiler | `domain/theory/workers.py` | §4.3 | — | implémenté |
| Monotonicité (Plurality, Approval, Ranked Pairs) | `engine/utils/simulation_ranked_utils.py` ; propriété testée : `api/tests/test_hypothesis_monotonicity.py` | §2.1, §4bis | — | implémenté |

## Modèles de comportement électoral

| Modèle | Fichier(s) | THEORY.md | Référence | Statut |
|---|---|---|---|---|
| Vote sincère vs stratégique | `engine/utils/simulation_voting_utils.py` (à confirmer) | §5.1 | `gibbard1973` | implémenté |
| Modèle de campagne (Brownian Motion) | `engine/utils/campaign_dynamics.py` | §5.2 | `hotelling1929` (à confirmer, pas de papier Brownian dédié) | implémenté |
| Contagion sociale du vote blanc (SIS) | `domain/election/workers_dynamics.py` (à confirmer) | §5.3 | — (modèle épidémiologique générique, pas de référence électorale directe — `TODO(source à vérifier)`) | implémenté |
| Vote rétrospectif | `domain/election/workers_behavioral.py` (à confirmer) | §5.6 | `fiorina1981` | partiel |
| Polarisation affective | `domain/election/workers_behavioral.py` (à confirmer) | §5.7 | `iyengar2019` | partiel |
| Cascades d'information | `domain/election/workers_dynamics.py` (à confirmer) | §5.9 | `bikhchandani1992` | partiel |

## Systèmes alternatifs de gouvernance — extensions

| Système | Fichier(s) | THEORY.md | Référence | Statut |
|---|---|---|---|---|
| Liquid Democracy (délégation transitive révocable) — hors périmètre du simulateur polity | `domain/election/workers_behavioral.py` (`_liquid_democracy_worker`, exporté `liquid_democracy`) | §7.2 | `blum_zuber2016`, `kahng_mackenzie_procaccia2021` (algorithmique), `kling2015` (limite empirique : super-voters) | implémenté |
| Conviction Voting (accumulation continue / seuil dynamique) | `domain/election/workers_behavioral.py` (`_conviction_voting_worker`, exporté `conviction_voting`) | §7.3 | `commons_stack_1hive2019` | implémenté |
| Simulateur Polity (légitimité `L(t)`, rappel, pression citoyenne) — chantier séparé, aucun lien code/config/journal avec le moteur Vote Lab ci-dessus | `fast_api_voter/api/domain/polity/` ; bornes de `L(t)` propriété testée : `api/tests/test_hypothesis_legitimacy.py` | §10 | modèle propre au projet (`polity-simulation-design-v2.md`), pas de référence académique unique | implémenté (v4, v5, v6a, v6b) — ⚠ bug de métrique connu : `accountability.mandate_deviation` (pledge_scope=top_k_priorities) peut sous-estimer un drift réel jusqu'à zéro s'il porte sur des dimensions hors du top-5 de priorité de l'élu ; trouvé et documenté 2026-08-22 (v6b Lot 4, second run d'acceptance), voir la docstring de `mandate_deviation`/`pledge_weights` dans `accountability.py` ; second point d'observabilité, résolu : `apply_shifts` (`llm_behavior_engine.py`) clampe toujours silencieusement toute cible hors `[0,1]` (aucun changement de comportement) — mais depuis, chacun de ses trois appelants (`run_polity_simulation.py`, dt=5/6/11) journalise un événement `clamped_at_bound` séparé, adjacent à la décision qu'il concerne, dès qu'une dimension sature réellement ; le plafonnement d'un drift est donc directement détectable depuis les données de run, plus besoin de reconstruction manuelle. Trouvé 2026-08-22 (v6b Lot 4), résolu le même jour ; voir la docstring d'`apply_shifts`/`clamped_dimensions` dans `llm_behavior_engine.py` ; troisième constat, méthodologique et rétroactif, mécanisme désormais complet (pas seulement corrélatif) : **`seed=42` — utilisée par tout run d'acceptation du projet depuis v4 Lot 8 — n'a jamais été validée comme représentative**. Le Blanc l'emporte au second tour du `two_round` sur 41/60 graines testées (68 %) à la configuration livrée. Chaîne causale fermée par investigation dédiée (2026-08-24, contre le pipeline réel `generate_population`/`initialize_parties`/`select_party_nominee`/`build_ranking`/`get_two_round_winner`, 40-60 graines, aucun changement de code) : le second tour contre le Blanc est une condition déterministe — `build_ranking` classe tout candidat dans la tolérance (`blank_threshold`) d'un électeur au-dessus du Blanc et tout candidat hors tolérance en dessous, donc le Blanc gagne si et seulement si l'acceptabilité du finaliste dans l'ensemble de la population est `≤ 50 %` (frontière exacte mesurée : max 50,0 % quand le Blanc gagne, min 51,0 % quand un candidat réel gagne, aucun chevauchement). Cause racine : `citizens.position_dist: uniform` disperse la population sur 20 dimensions sans centre de gravité, combiné à une pondération individualisée par électeur (`priority_dist: dirichlet`) — aucun candidat n'est proche d'une majorité. La méthode de sélection du nominee (ambition vs centroïde du parti) a un effet secondaire réel (70 % → 27,5 % d'échec, 5 partis, 40 graines) ; le levier qui referme la chaîne est `position_dist: gaussian_mixture`, déjà légal dans le schéma de config mais jamais implémenté (`generate_population` le rejette avec `NotImplementedError`) — remplacer uniquement le tirage des positions par une gaussienne centrée fait chuter l'échec à 2,5 % (std=0,30) puis 0 % (std≤0,20 ou mélange à 2-3 modes), tout le reste du pipeline inchangé. Touche rétroactivement tout run d'acceptation antérieur (v4 Lot 8 à v6b). **Décision de correction prise le 2026-08-25** (`plan-distribution-positions-seeds.md`, Phase 3) : `citizens.position_dist` bascule de `uniform` à `factor_structure` (modèle factoriel à bas rang, 2 facteurs, distribution unimodale — neutre sur convergence/polarisation, corrèle les 20 dimensions de façon réaliste) comme nouveau défaut livré ; sweep à 40 graines contre le pipeline réel : 0/40 victoires du Blanc (la ligne de référence `uniform` de ce sweep annonce 11/40, mais re-mesurée le 2026-08-29 contre le critère de nominee réellement livré elle vaut 67,5-75 % sur trois blocs de 40 graines — les 11/40 correspondent à la variante centroïde ; l'écart réel en faveur de `factor_structure` est donc plus large que le tableau de Phase 2 ne le montre), pas `gaussian_mixture` (jamais implémenté, écarté — un mélange présupposerait la question que la vue méso existe pour observer). Runs déjà publiés (v4 Lot 8 à la cascade v4+v5+v6a) non rejoués ni réétiquetés rétroactivement, restent documentés comme ayant tourné sous `uniform`/`seed=42`. Robustesse vérifiée bon marché (2026-08-25, quatre sondes déterministes, aucun calcul LLM) : `m` monte substantiellement sous `factor_structure` partout, mais les comptes de rappel restent quasi inchangés (`both` 2→2, `mobilization_only` 8→7, v6b `both` 2→2) et la propriété de contrôle d'`electoral_only` (jamais de rappel) tient — signal suggestif que les conclusions déjà publiées ne sont pas un artefact de la distribution, pas une confirmation au niveau de l'agent LLM. Décision sur cette base : pas de re-run LLM complet à ce stade ; re-baseline sélectif reste ouvert, priorité réduite. **Mise à jour 2026-08-28/29 — cette confirmation au niveau LLM existe désormais, et elle est partiellement défavorable** : deux runs v6b sous `factor_structure` donnent la première comparaison like-for-like contre ces sondes. Sous le menu `both`, la sonde annonçait 63,6 % d'occupation de la présidence ; le bras LLM en produit **33,3 %** — gain réel sur les ~6-9 % d'`uniform`, mais **sonde optimiste d'un facteur ~2**, et ce run reste invalide selon son propre critère pré-enregistré de 0,70. Sous `electoral_only` la sonde était juste (0 rappel et `L≈0,77` annoncés ; 0 rappel et `L` à 0,720 puis 0,850 mesurés), `office_occupancy=1,0`, et la comparaison élu/tiré-au-sort devient enfin calculable : déviation unifiée du président 0,0479 en moyenne / 0,1702 au maximum (écrêté par `apply_shifts`, 4 événements `clamped_at_bound` à l'appui) contre une chambre strictement immobile sur 990 délibérations — mais sur **deux présidents seulement**, dont un quasi-centriste face à moitié moins de mécontents, donc la dérive est montrée *atteignable* côté élu, pas *causée* par l'institution. Règle qui en ressort, formulée comme **hypothèse de travail et non résultat établi** (un seul cas favorable, où sa propre clause « rien à arbitrer » la rend presque tautologique) : une sonde déterministe est fiable sur les quantités mécaniquement déterminées et optimiste sur celles qui dépendent de l'arbitrage citoyen. **Second constat, 2026-08-29, vérification de `ambition_threshold`** (§3 du plan, jusque-là non faite) : au seuil livré `candidacy.ambition_threshold: 0.7`, `ambition_dist: beta(2,8)` ne rend éligible que **0,03 citoyen sur 100** en moyenne — 39 graines sur 40 ne produisent **aucun candidat**, identiquement sous `uniform` et sous `factor_structure`. Le `ambition_threshold=0.0` que tout script d'acceptance impose n'est donc pas une commodité mais une condition d'existence de l'élection, et la configuration livrée n'a jamais été exercée par aucun run (`rupture_path_enabled: false` en fait le seul chemin de candidature — pas de voie de secours). **Sorti comme chantier séparé, non résolu : `docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md`.** Voir `scripts/acceptance_v6b_fs_electoral_only_results.md`, `scripts/acceptance_cascade_results.md` et `THEORY.md` §10.9/§10.10 |

## Systèmes alternatifs de gouvernance

| Système | Fichier(s) | THEORY.md | Référence | Statut |
|---|---|---|---|---|
| Sortition | `domain/election/workers_advanced.py` (`_sortition_worker`, exporté `sortition`) | §7.1 | — | implémenté |
| Conviction Voting | `domain/election/workers_behavioral.py` (`_conviction_voting_worker`, exporté `conviction_voting`) | §7.3 | — | implémenté |
| Deliberative Polling | `domain/election/workers_advanced.py` (`_deliberation_worker`, exporté `deliberation`) | §7.5 | `fishkin1988` | implémenté |
| Futarchie | — | §7.6 | — | prévu |

---

*À maintenir via la commande `/sync-theory` (voir `.claude/commands/sync-theory.md`).*
