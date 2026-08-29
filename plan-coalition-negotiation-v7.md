# v7 — négociation multi-tours pour la coalition (§3.4 Cas 2) : document de scoping

**Statut** : scoping écrit, **Lot 1 (config + codebook) pas encore autorisé** — ce document
répond aux quatre points soulevés avant le feu vert, rien n'est implémenté.
**Date** : 2026-08-29
**Palier** : v7, §13 point 8 — le seul item que §13 assigne à v7 est "négociation multi-tours
pour la coalition (§3.4, Cas 2)". Le "maintien et rupture" d'une coalition existante à travers
les ticks (§3.1) est un chantier distinct, non assigné à un palier précis — voir §2 ci-dessous.

---

## 1. Ce qui existe déjà — `decide_coalition` (v2 incrément 5, dt=9)

`llm_behavior_engine.decide_coalition` (dt=9) forme une coalition en **un seul appel batché** :
le formateur (désignation déterministe, `tiebreak_key`) est proposé simultanément à tous les
partis sièges non-initiateurs, chacun répond JOIN/LEAVE **sans visibilité sur les autres** —
la docstring de `build_coalition_user_prompt` le dit explicitement : *"Deliberately does NOT
include a roster of the other responders' own context... a single-shot call cannot express 'I
join iff party X joins'; that conditional-coalition reasoning is what the deferred v7
multi-turn negotiation palier... exists for."* C'est exactement le trou que v7 comble.

Le résultat est assemblé **déterministiquement** (`assemble_coalition`, distance croissante à
l'initiateur, partage à égalité par sièges puis `party_id`) à partir des réponses JOIN — le LLM
ne contribue que la volonté de rejoindre, jamais l'ordre d'assemblage.

`CoalitionDecision` (`llm_schemas.py:498`) : `party_id`, `action: Literal[1, 2]` (JOIN/LEAVE),
`motif: Literal[501, 502, 504, 505]`, avec cohérence action↔motif **imposée** (comme
`VoteCastDecision`). `CoalitionAction`/`CoalitionMotif` (`codebook.py`) réservent déjà
`MAINTAIN=3` et `COALITION_RUPTURE_DISAGREEMENT=503` pour un futur palier de maintien à travers
les ticks, explicitement hors scope de l'incrément actuel.

Journalisation (`run_polity_simulation.py:1084`) : un événement `coalition_decision` **par
parti répondant** (payload `party_id`, `action`, `initiator` ; `motif` en champ séparé), puis un
événement agrégé `coalition_formed`/`coalition_failed`.

---

## 2. Périmètre — formation uniquement, pas de retouche de schéma à prévoir (remarque 1)

**Vérifié, pas supposé** : le schéma de transcription conçu ci-dessous pour v7
rend-il `MAINTAIN=3`/`COALITION_RUPTURE_DISAGREEMENT=503` structurellement impossibles à
ajouter plus tard ?

**Non — et ce n'est pas parce que v7 les anticipe, c'est parce qu'ils n'ont jamais dépendu du
mécanisme que v7 construit.** `CoalitionDecision.action` est *déjà* typé `Literal[1, 2]` dans le
code existant, **avant même que v7 n'existe** — restriction délibérée, documentée dans son
propre docstring (*"3 (maintain) belongs to the deferred maintenance-across-ticks palier"*). Le
maintien à travers les ticks est, par construction, un processus différent en nature : il
tournerait **à chaque tick d'un mandat en cours** (rejouer "cette coalition tient-elle
encore ?"), alors que la négociation de formation ne tourne **qu'une fois par élection
législative**, au moment où un formateur est désigné. Ce sont deux déclencheurs différents dans
la boucle de tick, donc structurellement deux types de décision et deux types d'événement de
journal différents — jamais une extension du même wrapper "round".

**Conséquence concrète pour v7** : le schéma de "round" conçu au §4 ci-dessous s'appuie sur
`CoalitionDecision` **tel qu'il existe déjà**, sans le modifier. Le seul engagement pris
maintenant pour ne rien fermer inutilement : le nouvel `event_type` de journal (§4) reste nommé
distinctement de ce qu'un futur "maintien" utiliserait, pour qu'aucune collision de nom ne soit
à démêler plus tard. Rien d'autre n'a besoin d'anticiper cette fonctionnalité — elle n'a jamais
partagé de mécanique avec la négociation de formation, dans le design comme dans le code.

**Périmètre de v7, donc** : uniquement la négociation multi-tours **au moment de la formation**.
Le maintien/rupture reste un chantier à part entière, non planifié, à réévaluer le jour où il
sera autorisé — sans dette laissée par ce lot-ci.

---

## 3. Condition d'arrêt — `max_negotiation_rounds` (remarque 2)

**Ce que la littérature déjà citée (Riker 1962, Axelrod 1970) donne réellement** : ce sont des
théories de **sélection d'équilibre** — qui prédisent QUELLE coalition se forme (taille minimale
gagnante pour Riker ; taille minimale gagnante *connexe* idéologiquement pour Axelrod) — pas des
modèles de **processus de négociation** avec un nombre de tours. Aucune des deux ne donne, ni ne
prétend donner, un nombre de tours. Affirmer le contraire serait une justification de façade.

**La valeur est donc un choix pragmatique, explicitement marqué comme tel — pas empirique tant
qu'aucun sweep n'a été fait (Lot 2+ seulement).**

**Proposition : `max_negotiation_rounds = 3`, structurellement dérivée, pas arbitraire :**

1. **Round 1** = exactement le mécanisme actuel (§1) : chaque répondant décide sans visibilité
   sur les autres. Ceci préserve un test de parité direct — round 1 seul, batch unanime,
   reproduit *byte-for-byte* la sortie actuelle de `decide_coalition` (même invariant que le
   test de parité déjà existant pour `assemble_coalition`).
2. **Round 2** = premier round où le raisonnement conditionnel devient possible : chaque
   répondant voit l'issue provisoire du round 1 et peut réviser ("je rejoins si X a rejoint").
   C'est le round qui justifie v7 à lui seul.
3. **Round 3** = une seconde révision, nécessaire parce qu'un changement d'avis au round 2 peut
   lui-même modifier le calcul d'un parti qui n'avait pas prévu de bouger (dépendance à deux
   sauts). Au-delà, dans un jeu à au plus `parties.initial_count - 1` répondants (4 dans la
   config livrée), le contenu informationnel marginal d'un tour supplémentaire est faible : la
   plupart des dépendances conditionnelles dans un groupe aussi petit se résolvent en un ou deux
   sauts.

La condition d'arrêt anticipée (§3.4 l'exige) est double : **borne dure** à
`max_negotiation_rounds`, **et** arrêt anticipé dès qu'un round ne change aucune décision
JOIN/LEAVE par rapport au round précédent (point fixe atteint) — cette seconde condition rend le
coût réel généralement inférieur à la borne dure, mesurée seulement une fois le Lot 2 en place.

**Nouveau paramètre de config (Lot 1)** : `parties.coalition_max_negotiation_rounds: 3`,
à côté de `coalition_majority_ratio` dans `PartiesConfig` (`config.py:144`).

---

## 4. Transcription et rejouabilité (remarque 3)

**Correction par rapport à ma propre présentation précédente** : j'avais supposé que le
mécanisme de cache décrit au §4.2 de `polity-simulation-design-v2.md` ("mémorise chaque réponse
indexée par le hash de l'entrée exacte envoyée") existait et pourrait absorber le rejeu partiel
gratuitement. **Vérifié dans le code, pas dans le document de design — et c'est faux** :
`llm_client.py` le dit explicitement dans son propre docstring de module : *"No caching here
(§4.2 deferred to a later increment, per the approved plan)."* Il n'y a **aucun cache
applicatif** aujourd'hui. Pire : même la reproductibilité "même graine → même réponse" que ce
cache était censé garantir ne tient déjà pas au niveau du modèle — le même docstring documente
qu'une paire de requêtes textuellement identiques (mêmes prompts, même seed) a produit des
décisions différentes sur un run réel (ordre de réduction flottant non-déterministe du backend
multi-thread). C'est exactement le type de piège que la remarque 3 anticipait — trouvé en
vérifiant, pas en supposant que le document de design décrivait l'état réel du code.

**Conséquence directe** : il n'y a pas de "clé de cache" à concevoir, parce qu'il n'y a pas de
cache à indexer. Ce qui garantit réellement la traçabilité dans ce projet aujourd'hui, ce n'est
pas le rejeu du modèle — c'est le **journal**, seule source durable de ce qui s'est passé (la
méthodologie de ce lot-ci elle-même : reconstruire l'état depuis le journal d'un run, jamais en
ré-invoquant le modèle en espérant une sortie identique).

**Conception retenue pour la transcription, donc — journal, pas cache :**

- **Un événement `coalition_decision` par (round, parti répondant encore indécis)**, payload
  étendu d'une seule clé additive : `round: int` (1-indexé). Rien d'autre ne change dans ce
  payload — additif pur, comme documenté au §1, donc **aucune rétro-incompatibilité** avec les
  runs déjà publiés (dont le payload n'a jamais eu cette clé, produits par un code différent) ni
  avec `metrics.py`, qui ne lit pas `round` aujourd'hui et n'a pas besoin de le faire.
- **Croissance du prompt, PAS du journal** : le prompt de chaque round *k* n'encode que
  **l'état courant résolu** après le round *k-1* (qui est actuellement "dedans", qui est
  "dehors", au sens de `assemble_coalition`) — pas un historique verbatim croissant de tous les
  tours précédents. C'est exactement le même principe que `chamber_position` (un instantané
  mutable, jamais un journal de tous les `shifts` passés) déjà appliqué ailleurs dans ce module.
  La taille du prompt reste donc **bornée**, pas croissante avec le nombre de rounds — feuille
  de route explicitement anti-framework du §3.4 respectée (une boucle Python, un appel par
  round, chaque appel aussi simple qu'un appel `decide_*` ordinaire).
- **Chaque round est écrit au journal dès qu'il se termine, avant que le round suivant ne
  commence.** C'est ce qui répond directement à la question du rejeu partiel : si le round 3 sur
  5 échoue (budget de rejeu de `_complete_and_decode_with_replay` épuisé, `LlmResponseError`
  non récupérée), **les rounds 1 et 2 sont déjà durablement écrits** — rien n'est perdu, parce
  que rien ne dépendait d'un cache qui n'existe pas. La négociation s'arrête à l'échec, pas de
  retry silencieux au niveau de la boucle de rounds elle-même (le retry existe déjà *à
  l'intérieur* de chaque appel round via `_complete_and_decode_with_replay`, inchangé).
- **Marquage explicite de l'échec** (précédent direct : `PendingRerun`'s `forced`, jamais un
  défaut silencieux) : `coalition_failed`'s payload gagne deux clés additives,
  `aborted_at_round: int | None` et `rounds_completed: int`, distinguant "aucune majorité
  atteignable par consentement après négociation complète" de "négociation interrompue par un
  échec LLM irrécupérable au round k" — deux causes différentes, un seul et même
  `coalition_failed` aujourd'hui les confondrait silencieusement.
- **`coalition_formed`'s payload gagne `rounds_used: int`** — combien de rounds ont réellement
  été nécessaires avant le point fixe, la mesure qui validera ou invalidera la borne de 3 choisie
  au §3, une fois Lot 2 livré.

Rien de ceci n'invente de nouveau mécanisme : c'est le même patron event-sourcing (§16.2) déjà
utilisé pour `sortition_rotation`, `chamber_deliberation`, etc. — pas une brique nouvelle.

**Point vérifié séparément, pas implicite dans ce qui précède** : la durabilité par round
protège contre la *perte* de travail, mais ne dit rien, à elle seule, sur la question plus fine
— un rejeu du round 3 peut-il **diverger silencieusement** en reconstruisant les rounds 1-2 sur
une base différente de ce qui a réellement eu lieu ? Deux cas, à traiter séparément :

1. **Rejeu à l'intérieur du même processus** (le round 3 échoue, mais la boucle Python de
   négociation elle-même est toujours en vie — c'est le seul cas que `_complete_and_decode_
   with_replay`'s propre budget de rejeu couvre) : **aucun risque de divergence**, par
   construction. Le prompt du round 3 est bâti à partir des objets Python déjà produits par les
   rounds 1 et 2 — calculés une seule fois, jamais régénérés. L'écriture au journal (ci-dessus)
   sert la durabilité/l'audit, pas la reconstruction de l'état d'entrée du round 3 : cet état ne
   vient jamais du journal en cours de boucle, il vient de la mémoire du round précédent,
   directement.
2. **Rejeu après redémarrage complet du run** (le processus entier meurt — ex. conteneur down —
   et le run est relancé de zéro avec la même graine) : **non protégé, et ce n'est pas le rôle de
   v7 de le protéger.** Vérifié directement dans le code : `run_polity_simulation.py` ne contient
   **aucun** mécanisme de reprise/checkpoint (`grep` sur resume/checkpoint/from_tick : zéro
   résultat) — un redémarrage complet régénère tout depuis le tick 0, pour **tout** type de
   décision LLM, pas seulement `coalition_decision`. Le round 1 (et donc toute la chaîne round
   1→2→3) peut donc diverger sur un tel redémarrage, exactement comme n'importe quel autre appel
   LLM de ce projet le peut déjà aujourd'hui — c'est la limite du §4.3 déjà nommée et acceptée
   (*"Limite à accepter"*), pas une régression introduite par v7. Construire un mécanisme de
   reprise au niveau du run entier serait un chantier transverse à tout le pipeline, hors
   périmètre de ce lot — v7 n'a aucune raison de le résoudre seul pour la négociation de
   coalition quand aucun autre `decide_*` ne le résout pour lui-même.

**Donc** : la conception ci-dessus élimine la divergence silencieuse dans le seul cas qu'elle a
les moyens de couvrir (rejeu intra-processus), et hérite honnêtement — sans l'aggraver ni la
masquer — de la limite déjà documentée pour le cas qu'elle ne peut pas couvrir (redémarrage
complet). Les deux clés additives `aborted_at_round`/`rounds_completed` (ci-dessus) existent
justement pour qu'un tel redémarrage, s'il produit un résultat différent de la tentative
précédente, laisse une trace lisible plutôt qu'un écart muet entre deux journaux.

---

## 5. Coût — mesuré sur un run réel, pas dérivé de la config (remarque 4)

Comptage réel sur `acceptance_v6b_runs_fs_electoral_only/sortition-llm-8y` (run électoral LLM de
référence, 8 ans, config livrée) :

| Type d'événement | Compte sur 8 ans |
|---|---|
| `chamber_deliberation` | 990 |
| `pressure_action` | 399 |
| `vote_cast` | 300 |
| `candidacy_considered` | 300 |
| `coalition_decision` | **8** |
| `coalition_formed` | **2** |

**2 formations de coalition en 8 ans** (cohérent avec `assembly_term_years: 4`), **4 décisions
de parti par formation** (5 partis livrés − 1 initiateur = 4 répondants) — mesuré, pas déduit de
la formule "sièges / partis".

`decide_coalition` aujourd'hui : **1 appel LLM par formation** (batch de tous les répondants en
un seul appel — `decide_coalition`'s docstring : *"Deliberately does NOT use chunk_voters...
this batches seated parties (a handful at most), not citizens"*). Coût actuel sur 8 ans : **2
appels**.

**v7, cas favorable (le batching actuel tient à `max_negotiation_rounds=3`, comme
`party_nomination`/`campaign_positioning` l'ont fait sans jamais avoir besoin d'être chunkés)** :
`2 formations × 3 rounds = 6 appels` sur 8 ans.

**v7, cas défavorable (la fiabilité force un jour un chunking à 1 répondant par appel — le sort
qu'ont fini par subir `vote_cast` et `chamber_deliberation`, à vérifier empiriquement en Lot 2+,
pas supposé maintenant)** : `2 formations × 3 rounds × 4 répondants = 24 appels` sur 8 ans.

**Sur 30 ans** (borne haute citée) : environ 7-8 formations (extrapolation linéaire de la mesure
sur 8 ans, à confirmer par un run réel le moment venu) → 21-24 appels (cas favorable) à 84-96
appels (cas défavorable pessimiste).

**Conclusion, dans les deux cas** : ceci reste **deux à trois ordres de grandeur en dessous** de
`chamber_deliberation` (990 sur 8 ans, ~3 700 projetés sur 30 ans) ou `vote_cast` (300 sur 8 ans).
v7 ne change pas la donne du budget GPU/temps d'un acceptance run complet, même dans son
scénario le plus coûteux. Ce n'est pas un chantier à optimiser pour le coût — c'est un chantier
à valider pour la fiabilité (Lot 2+), exactement comme les autres dt LLM de ce projet l'ont été.

---

## 6. Lot 1 — ce qui est livré (documentation + config/codebook, aucune boucle)

Cohérent avec le patron déjà établi pour tous les paliers précédents (v0 à v6) : Lot 1 pose les
fondations statiques, Lot 2 écrit la mécanique, Lot 3+ la valide en conditions réelles.

- **Config** (`config.py`, `polity_config.yaml`) : `parties.coalition_max_negotiation_rounds: 3`
  (§3), avec le commentaire complet de la dérivation ci-dessus — même discipline que le
  commentaire d'`ambition_threshold` (ADR-002).
- **Codebook** : **aucun changement**. `CoalitionAction`/`CoalitionMotif` restent exactement ce
  qu'ils sont (§2) — v7 réutilise `CoalitionDecision` sans le modifier.
- **Journal** : le schéma étendu du §4 (`round` sur `coalition_decision` ; `rounds_used` sur
  `coalition_formed` ; `aborted_at_round`/`rounds_completed` sur `coalition_failed`) est
  **documenté ici**, pas encore implémenté — `_form_and_journal_coalition_llm` n'est pas touché
  dans ce lot.
- **Ce que Lot 1 NE fait PAS** : pas de boucle de négociation, pas de nouveau
  `build_coalition_*_prompt` multi-round, pas de test de reliability contre le modèle réel. Ça,
  c'est Lot 2.

---

## État

Scoping complet, quatre points de la remarque intégrés avec vérification directe du code (pas
seulement du document de design, qui s'est révélé périmé sur le point du cache — §4). **Lot 1
pas encore autorisé.**
