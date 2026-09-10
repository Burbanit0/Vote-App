# Contrats de décision — ce que chaque type de décision LLM doit recevoir

Document de spécification. Il définit, pour les 9 types de décision LLM du simulateur, **quel
comportement est attendu** et **quelles informations le prompt doit porter pour que la question
posée soit répondable**.

Il existe parce qu'une série de mesures (septembre 2026) a montré que plusieurs types de décision
émettent une constante quel que soit l'état du citoyen, et que la cause la plus probable n'est ni
le modèle ni le format, mais **une question mal posée** : une grandeur brute envoyée sans échelle,
sans historique et sans critère. Voir `fast_api_voter/scripts/check_pressure_missing_threshold_results.md`
et `synthese-programme-llm-2026-09-10.md`.

Ce document est la référence contre laquelle toute modification de prompt doit être vérifiée.

---

## 1. Le contrat

Un type de décision est **bien posé** si et seulement s'il satisfait les cinq clauses suivantes.
Les quatre premières sont une lecture directe du §3.3 et du §7bis.9d du document de conception ;
la cinquième vient de `plan-decision-quality-validation.md`.

| # | Clause | Fondement |
|---|---|---|
| **C1** | **Le but** de l'agent est énoncé. | §3.3 item 1 |
| **C2** | **Les règles du jeu** sont énoncées : options légales, bornes, codes valides. | §3.3 item 2 |
| **C3** | **L'état est perceptible** : toute grandeur dont dépend la décision porte *une* échelle — une valeur de comparaison propre à l'enregistrement, une normalisation, ou un historique récent. | §3.3 item 3, qui nomme explicitement « positions des autres acteurs, **historique récent** » |
| **C4** | **Rien de prescriptif** : aucune règle ne fait correspondre un état à une action. | §3.3 (« aucun critère théorique prescriptif ») et §7bis.9d (« si le seuil décide de l'action … un LLM décoratif … l'inverse exact de l'objectif du §3.3 ») |
| **C5** | **Noté sur l'échelle qu'on lui montre** : si la validation raisonne en unités de X, le prompt exprime la grandeur en unités de X. | `plan-decision-quality-validation.md` définit le « cas non ambigu » comme `gap < 0,5 × blank_threshold` ou `> 1,5 × blank_threshold` |

**C3 et C4 ne s'opposent pas — elles se complètent.** C4 interdit de dire *quoi choisir* ; C3 exige
de dire *ce que les nombres veulent dire*. Envoyer à un citoyen son propre seuil de tolérance en le
définissant, sans jamais dire ce qu'il faut faire au-dessus, satisfait les deux. Écrire « si
self_gap > blank_threshold alors act=4 » viole C4.

**C5 est la clause la plus facile à violer sans s'en apercevoir.** Aujourd'hui le protocole de
validation note `pressure_action` en multiples de `blank_threshold` — une échelle que le prompt ne
montre jamais. On corrige une copie sur un barème que l'élève n'a pas vu.

---

## 2. Audit des 9 types

Établi par lecture directe du code (`llm_behavior_engine.py`, `simple_rules.py`), septembre 2026.

| Type | C1 | C2 | C3 | C4 | C5 | Statut mesuré |
|---|:--:|:--:|:--:|:--:|:--:|---|
| `vote_cast` | ✅ | ✅ | ✅ | ⚠️ | ✅ | **Fiable** (23/24) |
| `campaign_positioning` | ✅ | ✅ | ✅ | ✅ | n/a | Pas de collapse (autre défaut : 50-66 % d'échec) |
| `party_nomination_choice` | ✅ | ✅ | ⚠️ | ✅ | n/a | Pas de collapse (4/5) |
| `candidacy_considered` | ✅ | ✅ | ❌ | ✅ | ❌ | Pas de collapse, mais 64 % de justesse mesurée |
| `coalition_decision` | ✅ | ✅ | ⚠️ | ✅ | n/a | **Collapse confirmé** |
| `representative_response` | ✅ | ✅ | ❌ | ✅ | n/a | **Collapse confirmé** (8B) |
| `chamber_deliberation` | ✅ | ✅ | ❌ | ✅ | n/a | Non tranché |
| `reaction_to_event` | ✅ | ✅ | ❌ | ✅ | n/a | Pas de collapse détecté sur l'axe testé |
| `pressure_action` | ✅ | ✅ | ❌ | ✅ | ❌ | **Collapse confirmé** |

### La régularité que l'audit fait apparaître

**Les deux seuls types qui portent une véritable référence d'échelle sont les deux qui ne
collapsent pas.**

- `vote_cast` envoie `distances` (pré-calculées) **et** `blank_threshold` par électeur, **et**
  énonce la règle d'acceptabilité mot pour mot. C'est le seul type noté fiable — et le seul qui
  porte un ⚠️ en C4, puisqu'il énonce bel et bien un critère. Ce n'est pas une violation : la règle
  n'y couvre que l'*acceptabilité* ; le classement entre candidats acceptables, le motif et les cas
  limites restent en arbitrage libre. C'est le modèle à suivre — **calibrer la partie mécanique,
  laisser libre la partie de jugement.**
- `campaign_positioning` envoie `electorate_mean`, une référence de population. Pas de collapse.

Inversement, tout type qui envoie une grandeur nue sans référence collapse ou sous-performe :
`pressure_action` (`self_gap` seul), `candidacy_considered` (`ambition_score` seul),
`representative_response` (`L`, `mandate_dev`, `street` — décrits verbalement, jamais normalisés),
`chamber_deliberation`, `reaction_to_event` (`event_salience` seul).

`coalition_decision` est le cas intermédiaire instructif : il porte une échelle pour les **sièges**
(`majority_seats_threshold`, `initiator_shortfall`) mais **aucune** pour `distance_to_initiator`,
qui est justement le signal d'affinité sur lequel porte la décision. Il collapse.

---

## 3. Comportement attendu, type par type

Chaque énoncé est rédigé pour être **testable** : il doit être possible de construire deux
situations qui, selon lui, exigent des réponses différentes.

### `pressure_action` (dt=10) — pilote de correction

> Un citoyen consulté, dont l'écart au titulaire dépasse nettement sa propre tolérance, choisit plus
> souvent d'agir qu'un citoyen dont l'écart est nettement en dessous. **Où** il place sa limite, et
> **quel** levier il choisit dans le menu légal, restent son arbitrage.

- Libre : le point de bascule, le choix du levier, la réaction à `neighbors_acting`.
- À calibrer (C3) : `self_gap` doit venir avec une échelle. Trois véhicules légaux — le seuil propre
  au citoyen (défini, jamais prescriptif), l'écart au tick précédent (« historique récent »), la
  position dans la cohorte consultée.
- Note C4 : `deterministic_pressure_action` compare `gap < blank_threshold`. **Cette règle ne doit
  jamais être écrite dans le prompt** — ce serait exactement le « LLM décoratif » du §7bis.9d.

**Vérifié en direct, 2026-09-10** (`fast_api_voter/scripts/check_pressure_calibration_matrix_results.md`) :
l'énoncé ci-dessus tient — **à la taille de batch 1 seulement**. Les quatre véhicules calibrés (seuil,
historique, rang de cohorte, écart à la promesse) obtiennent chacun 100 % (9/9 essais) sur le sous-
ensemble non ambigu, contre le menu fermé ET le menu ouvert. **Aucun ne survit au-delà** : à taille 5
et 25, les cinq variantes retombent au niveau d'une réponse constante (~52 %), de façon uniforme et
totale, pas graduelle. Le mécanisme de calibration n'est donc pas en cause — c'est le partage d'un
appel entre plusieurs citoyens qui detruit le signal, quelle que soit la donnée fournie. La taille de
batch devient la seule question restante (Phase D).

### `candidacy_considered` (dt=2)

> Un citoyen dont l'ambition est nettement supérieure à ce qui est nécessaire pour se présenter s'y
> engage plus souvent qu'un citoyen nettement en dessous.

- Libre : le point de bascule, le poids relatif d'`ambition_score` et de `perceived_support`.
- À calibrer : `ambition_score` est envoyé nu. `config.ambition_threshold` n'apparaît nulle part.
  ⚠️ Ce seuil n'est **pas** une vérité terrain valide (ADR-002 : la valeur shippée rend le chemin
  déterministe inerte) — préférer une référence de population, dans la forme qu'a déjà
  `perceived_support`.

### `representative_response` (dt=6)

> Un élu dont la légitimité s'effondre et qui fait face à une mobilisation soutenue réagit
> différemment d'un élu en position confortable.

- Libre : la stance choisie, l'ampleur et la direction des ajustements.
- À calibrer : `L`, `mandate_dev` et `street` sont décrits en prose (« accumulateur NON BORNE ») mais
  jamais normalisés. Le véhicule le plus simple et incontestablement légal (C2, « règles du jeu ») :
  les constantes shippées qui bornent ces grandeurs — `mandate.max_response_delta`, le plancher de
  légitimité.

### `coalition_decision` (dt=9)

> Un parti idéologiquement proche du formateur rejoint plus souvent qu'un parti maximalement
> éloigné, à situation institutionnelle égale.

- Libre : tout l'arbitrage — c'est le type où le §3.3 est le plus explicitement invoqué.
- À calibrer : `distance_to_initiator` n'a aucune référence. Une échelle non prescriptive existe et
  est déjà calculée ailleurs : la distance moyenne entre partis de l'assemblée.

### `chamber_deliberation` (dt=11)

> Un membre dont la position exprimée a dérivé de sa position sincère se comporte différemment d'un
> membre resté aligné.

- Libre : ajuster ou non, de combien, dans quelle direction.
- À calibrer : les deux vecteurs sont envoyés bruts ; l'écart entre eux n'est jamais donné, ni borné
  par `sortition_chamber.max_deliberation_delta`.

### `reaction_to_event` (dt=8)

> Un citoyen déjà très sensibilisé réagit moins fortement à un nouvel événement qu'un citoyen
> vierge (rendements décroissants).

- Libre : l'ampleur de `salience_delta`, le seuil de pertinence personnelle.
- À calibrer : `event_salience` est envoyé nu, sans `events.max_reaction_delta` comme échelle.
- Note : c'est le seul énoncé déjà partiellement vérifié — la branche SCANDAL montre 0,20 contre
  0,15 selon la salience antérieure, dans le bon sens.

### Types conformes — à ne pas modifier

`vote_cast`, `campaign_positioning`, `party_nomination_choice` satisfont le contrat et ne montrent
pas de collapse. `party_nomination_choice` porte un ⚠️ en C3 (`platform_distance` sans référence)
mais compare des candidats **entre eux** dans un même enregistrement, ce qui fournit l'échelle
implicitement — d'où, vraisemblablement, sa fiabilité.

---

## 4. Ce que ce document engage

- Toute modification de prompt se vérifie contre C1-C5 **avant** d'être mesurée.
- Aucune correction ne peut faire passer un type de ❌ en ✅ sur C3 en violant C4. Si la seule façon
  de faire fonctionner un type est de lui dicter la règle, c'est un **résultat** à consigner (ce
  type ne supporte pas l'arbitrage libre à cette échelle de modèle), pas un correctif à livrer.
- Les énoncés du §3 sont des hypothèses testables, pas des acquis. Chacun doit être confronté au
  barème de `plan-decision-quality-validation.md` (≥ 90 % sur les cas non ambigus) avant d'être
  traité comme le comportement réel du simulateur.

**Statut** : audit établi ; corrections non commencées. `pressure_action` est le pilote, conformément
à `plan-decision-quality-validation.md` qui prescrit de valider la méthode sur ce type avant de
construire les sondes restantes.
