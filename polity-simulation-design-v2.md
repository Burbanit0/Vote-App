# Plan de conception — Simulateur de Polity ("La Fourmilière")

> **Révision 2c — 30/07/2026.** Intègre au document initial : la
> résolution du bloquant A6 (formule de `écart(t)`), la pression
> citoyenne repensée comme **leviers actionnables** et non comme
> accumulateurs mesurés (§7bis), les règles électorales additionnelles
> (§6bis), le schéma de sortie du LLM (§3.6, bloquant B1) et son codebook
> de compression (§3.7), et la reformulation du coût en **temps
> d'horloge** avec ses conséquences sur la parallélisation et le
> déterminisme (§15bis).
>
> Objectif : simuler une population de plusieurs milliers de citoyens sur
> 30 ans, avec élections présidentielles et parlementaires imbriquées,
> partis, coalitions, comportement électoral évolutif, et des mécanismes
> de pression citoyenne activables.
>
> Le citoyen est une entité unique (électeur ↔ candidat ↔ élu), et un LLM
> gouverne l'ensemble des comportements des citoyens (vote, candidature,
> choix de parti, coalition, campagne, réaction aux événements, réaction
> à la pression) — seuls le **format du bulletin**, la **méthode
> d'agrégation** et les **déclencheurs institutionnels durs** restent des
> fonctions déterministes externes au LLM.
>
> Statut des sections : 🟢 cadrage solide · 🟡 à discuter · 🔴 ouvert/non tranché

---

## 0. Vision et question de recherche 🟢

> **Comment le système électoral, le comportement de l'électorat, la
> stratégie des candidats, les moyens de pression dont disposent les
> citoyens et les règles constitutionnelles interagissent-ils pour
> produire, sur plusieurs décennies, de la stabilité ou de l'instabilité
> politique ?**

Livrables attendus d'un run : séries temporelles (fragmentation partisane,
légitimité des élus, polarisation, taux de vote blanc, déviation de
mandat), un journal d'événements (élections, coalitions formées/rompues,
pétitions, rappels déclenchés, scandales), et la possibilité de comparer
deux configurations constitutionnelles à graine aléatoire identique
(ex. avec/sans recall, avec/sans limitation de mandats).

**Ajout de la révision 2** : la question de recherche inclut désormais
explicitement les *moyens de pression*. Le document initial ne comportait
qu'un seul levier (le rappel automatique sur `L(t)`), binaire et
mécanique. Le §7bis en introduit plusieurs, de temporalités différentes,
**et — révision 2b — les traite comme des actions que les citoyens
décident d'entreprendre ou non**, plutôt que comme des mesures calculées
par l'observateur. La question devient donc autant « quels leviers une
constitution offre-t-elle ? » que « une population s'en saisit-elle ? ».

---

## 1. Vue d'ensemble de l'architecture 🟢

```
domain/polity/
├── citizen.py                 # Entité unique Citizen (état + transitions de rôle)
├── social_graph.py            # Réseau social / diffusion d'opinion
├── candidacy_rules.py         # Nomination de parti + seuil de candidature indépendante
├── institutional_clock.py     # Calendrier électoral (présidentiel/parlementaire)
├── ballot_and_aggregation.py  # Enclave déterministe n°1 (§3.2)
├── accountability.py          # NOUVEAU — canaux de pression citoyenne (§7bis)
├── llm_behavior_engine.py     # Cœur : décisions citoyennes via LLM, batchées par cohorte
├── llm_client.py              # Cache (hash d'entrée), appels batchés, schémas JSON (§3.6)
├── codebook.py                # NOUVEAU — tables de correspondance code ⇄ libellé (§3.7)
├── legitimacy.py              # Variable d'état L(t), enclave déterministe n°2 (§7.2)
├── events.py                  # Scandales, chocs économiques
├── journal.py                 # NOUVEAU — écriture append-only du journal (§16.1)
├── snapshots.py               # NOUVEAU — snapshots de reconstruction (§16.4)
├── indexer.py                 # NOUVEAU — compaction/indexation post-run (§16.6)
├── viz_export.py              # NOUVEAU — export pour les visualisations (§14)
├── run_polity_simulation.py   # Orchestration du run complet (30 ans)
└── metrics.py                 # Calcul des indicateurs de sortie
```

*(Résout C3 de l'audit de précision : l'arborescence initiale datait
d'avant les §14/§15/§16 et omettait les modules de données.)*

**Principe structurant** : il n'y a pas de séparation entre un « moteur
vectorisé déterministe » et une « couche générative optionnelle ». Le
comportement citoyen *est* gouverné par le LLM par défaut. Il existe
exactement **trois enclaves déterministes**, et elles sont limitatives :

1. `ballot_and_aggregation.py` — format du bulletin et règle d'agrégation
   (§3.2), correspondant à `engine/utils` existant (29 méthodes de vote) ;
2. `legitimacy.py` — le plancher dur sur `L(t)` et son déclenchement de
   rappel (§7.2), pour garantir la lisibilité externe de l'événement ;
3. `accountability.py` — les **seuils** de déclenchement des leviers de
   pression et le **menu constitutionnel** disponible (§7bis), pour la
   même raison : le LLM gouverne *qui agit et comment*, jamais *quels
   leviers existent* ni *à quel seuil* une institution se déclenche.

---

## 2. Le citoyen unifié 🟢 (mécanique de transition 🟡)

### 2.1 Principe

Une seule entité `Citizen`, pas des types séparés `Voter`/`Candidate`/
`Party`. Le rôle est un champ d'état qui transite dans les deux sens :

```
role   ∈ {électeur, candidat, élu}
office ∈ {aucun, président, député}          # A3 de l'audit
term_end_tick : int | None                    # A3
```

Un électeur peut décider de se présenter (→ candidat). Un candidat non élu
redevient électeur. Un candidat élu devient élu, puis redevient électeur
(ou re-candidat) à la fin de son mandat, à sa défaite, ou à un rappel.

*(`office` et `term_end_tick` résolvent A3 : un « élu » pouvait être
président ou député, deux mandats aux règles, durées et mécaniques de
rappel différentes — le champ `role` seul était inutilisable.)*

### 2.2 État par citoyen

| Champ | Description |
|---|---|
| `citizen_id` | Identifiant stable sur toute la durée du run (D1) |
| `issue_positions[20]` | Position sur les 20 enjeux, `[0,1]` |
| `issue_priorities[20]` | Poids relatif de chaque enjeu |
| `role` | électeur / candidat / élu |
| `office` | aucun / président / député |
| `term_end_tick` | Tick de fin de mandat si élu |
| `mandates_served` | Compteur de mandats accomplis (§6bis.1) |
| `party_affiliation` | Parti d'appartenance (ou indépendant) |
| `ambition_score` | Propension à se porter candidat si l'occasion se présente |
| `pledged_platform` | Plateforme engagée à l'élection (§7bis.5) |
| `revealed_position` | Position effective en cours de mandat (§7bis.5) |
| `legitimacy_perceived[office]` | Confiance perçue envers chaque élu en poste (si électeur) |
| `legitimacy_capital` `L` | Variable d'état si élu — cf. §7 |
| `social_neighbors` | Liste d'indices vers le graphe social |
| `archetype_id` | Référence vers la bibliothèque de personas (§9) |

**Population figée sur 30 ans** en v0-v5 (`static_population: true`) : ni
mortalité ni natalité, pour ne pas mélanger un effet de renouvellement
démographique avec un effet de dynamique politique. À rouvrir comme
palier explicite si nécessaire.

### 2.3 Limiter le nombre de candidats — par les règles, pas par un plafond arbitraire 🟡

Pas de plafond numérique fixé en dur (hors garde-fou de dernier recours
`max_candidates_hard_cap`). Le pool de candidats effectifs est borné par
deux règles institutionnelles réalistes, dans `candidacy_rules.py` :

1. **Nomination de parti** : plusieurs citoyens ambitieux d'un même parti
   peuvent vouloir se présenter, mais le parti désigne *un seul* candidat
   officiel — décision confiée au LLM (§3.6.3), qui arbitre entre les
   prétendants internes.
2. **Seuil de candidature indépendante** — **jamais implémenté, retiré du
   config le 2026-08-29** : un citoyen hors parti ne devient candidat que
   s'il franchit un seuil de soutien préalable (parrainages simulés) —
   mécanique d'accès au bulletin standard dans les démocraties réelles, qui
   évite un scrutin à 200 candidats sans limite artificielle. Ce point est
   resté à l'état d'intention depuis le v0 : aucun citoyen n'est jamais
   réellement « hors parti » dans le modèle (`assign_party_affiliation`
   assigne toujours le parti le plus proche), donc aucun code de domaine n'a
   jamais eu de branche à câbler contre `independent_signature_ratio`. Voir
   `docs/adr/ADR-003-ballot-access-filter-is-inert.md`, section « Decision on
   option 3 » : si un chemin de candidature indépendante est un jour conçu,
   il aura son propre chantier, sa propre ADR et un seuil choisi à ce
   moment-là — ce paramètre-ci ne valait pas la peine d'être ressuscité.

### 2.4 Deux chemins vers la candidature 🟢

1. **Chemin dominant — soutien perçu** : un citoyen se porte candidat
   quand son `ambition_score` et le soutien qu'il perçoit dans son réseau
   social (§5) dépassent un seuil combiné. C'est le chemin normal.
2. **Chemin rare — candidature de rupture** : un citoyen en désaccord
   marqué peut se présenter *indépendamment* du soutien perçu, avec une
   probabilité volontairement très faible — parce que la majorité des
   citoyens en désaccord n'agit pas.

**Résolution de C1** (contradiction §2.3 ↔ §2.4) : le chemin de rupture
n'est **pas exempté** du filtre d'accès au bulletin — il bénéficie d'un
seuil de signatures **réduit** (`rupture_signature_ratio: 0.005`, contre
`0.01` prévu à l'origine pour un indépendant classique, seuil retiré depuis
faute de chemin à gater — voir §2.3 point 2), pas d'une exemption totale.
Sans ça, le mécanisme de bornage du §2.3 était purement et simplement
annulé.

Les deux chemins alimentent le même pool, mais produisent des dynamiques
différentes à observer : le premier des candidats consensuels, le second
des candidatures protestataires peu nombreuses mais parfois disruptives —
cohérent avec la littérature sur la diffusion du vote de protestation
(Superti, 2020).

---

## 3. Le LLM comme moteur comportemental 🟡

### 3.1 Périmètre

Tout ce qui relève d'une **décision d'un ou plusieurs citoyens** passe par
le LLM :
- décision de vote de chaque électeur ;
- décision de se présenter (candidat potentiel → candidat officiel) ;
- choix du parti entre ses prétendants internes ;
- formation, maintien et rupture de coalition après une législative ;
- positionnement de campagne d'un candidat ;
- réaction collective à un scandale ou un choc économique ;
- **réaction d'un élu à la pression citoyenne (§7bis)** — ajout rév. 2 ;
- **choix du levier de pression actionné par un citoyen mécontent
  (§7bis.3)** — ajout rév. 2b, y compris le choix de ne rien faire.

### 3.2 Ce qui reste strictement en dehors 🟢

Le **format du bulletin** (classé, score, approbation...) et la **règle
d'agrégation** (Plurality, IRV, Condorcet, SPAV, Two-Round...) — la
mécanique pure de comptage, dans `ballot_and_aggregation.py`, identique à
`engine/utils` existant. Le LLM produit des *préférences* ; l'agrégation
reste une fonction déterministe éprouvée par le golden-fixture harness.

S'y ajoutent, depuis la révision 2, les **seuils de déclenchement
institutionnel** (plancher de `L(t)`, seuil de signatures d'une pétition,
seuil d'invalidation par vote blanc) — même justification : lisibilité
externe de l'événement institutionnel (§7.2).

**🟡 Ouvert** : ce périmètre pourra évoluer — par exemple si le LLM devait
un jour raisonner sur le choix de la méthode électorale elle-même (débat
constitutionnel simulé). Non retenu pour l'instant.

### 3.3 Rien n'est figé — la théorie devient une grille de lecture 🟢

**Décision tranchée** : le LLM ne reçoit *aucun* critère théorique
prescriptif (pas de « utilise une recherche locale à la
Kollman-Miller-Page », pas de « privilégie une coalition connexe
minimale »). L'objectif est d'**observer quelles stratégies émergent
spontanément** quand des citoyens et des partis cherchent à atteindre
leurs buts en respectant uniquement les règles du jeu.

Ce que le LLM reçoit se limite à :
1. **Le but du citoyen/parti** ;
2. **Les règles du jeu en vigueur** (méthode électorale, calendrier,
   composition de l'assemblée, canaux de pression actifs) ;
3. **L'état perçu** (positions des autres acteurs, historique récent,
   `L(t)` et signaux de pression si élu).

Les références théoriques déjà mobilisées (Kollman-Miller-Page, Axelrod,
Riker, Fiorina, Downs) **ne disparaissent pas** — elles se déplacent
vers le **§11 (audit)**, comme grille de lecture *a posteriori*.

### 3.4 Communication inter-agents 🟢

**Cas 1 — Pipeline (à implémenter en premier)** : pas de dialogue direct
entre deux LLM, une chaîne où la sortie structurée de l'un devient une
entrée de l'autre.

```
LLM "générateur de personas" (rare, §9)
        ↓ produit la bibliothèque d'archétypes
LLM "comportement citoyen" (fréquent, batché, §3.5)
        ↓ consomme les personas comme contexte
```

Rien n'impose le même modèle aux deux étapes. La bibliothèque de personas
est un artefact figé et versionné entre deux régénérations — cohérent
avec l'exigence de reproductibilité (§4).

**Cas 2 — Négociation multi-tours (palier v7, réservé à la coalition)** :
deux instances LLM échangent plusieurs tours avant qu'une décision finale
n'émerge. Contraintes dès la conception : condition d'arrêt explicite,
cache/hash de la **transcription complète**, pas de framework
d'orchestration multi-agents (une boucle Python reste plus auditable).

### 3.5 Batching obligatoire, pas optionnel 🟢

Puisque *tous* les électeurs passent par le LLM, un appel par citoyen est
structurellement impossible en volume. `llm_behavior_engine.py` doit :
- regrouper les citoyens par `archetype_id` (§9) et situation similaire ;
- soumettre un batch en un seul appel, retournant un tableau structuré ;
- ne jamais raisonner citoyen par citoyen dans la boucle principale.

**🟡 Reste ouvert (B3)** : critère exact de similarité et taille de
cohorte. `max_batch_size: 25` est fixé en config, mais le critère de
regroupement reste à préciser — dernier bloquant v2 non résolu.

---

### 3.6 Schéma de sortie du LLM 🟢 *(nouveau — résout B1)*

#### 3.6.0 Principes transverses

**Contrainte de format, pas de contenu.** Le JSON est contraint côté
serveur d'inférence (grammaire / JSON mode), jamais obtenu par
fine-tuning. Le fine-tuning (v8) sert uniquement à stabiliser le
*contenu* dans le cadre du §3.3.

**Enveloppe de batch.** Chaque appel porte sur une cohorte :

```json
{
  "decisions": [
    { "cid": 412, "...": "voir schéma spécifique au type" },
    { "cid": 413, "...": "..." }
  ]
}
```

**Règle dure** : la réponse contient **exactement un élément par citoyen
envoyé**, dans le même ordre. Un décompte différent est traité comme un
échec de batch complet (rejeu intégral, jamais de correction partielle
silencieuse) — sinon un désalignement `cid` ⇄ décision devient
indétectable et casse la reproductibilité (§4).

**Décisions formulées comme acte/réponse — obligation de vérification
avant tout nouveau type de décision (2026-08-30, révisé la même soirée ;
hypothèse, pas une loi générale prouvée).** Quatre types de décision
existants formulés comme un acte ou une réponse avec conséquence
institutionnelle vis-à-vis de l'extérieur (`pressure_action` : choisir un
levier de pression ; `representative_response` : choisir une posture ;
`coalition_decision` : rejoindre/refuser une coalition ; `reaction_to_event`
branche SCANDAL : réagir à un événement) collapsent tous vers une réponse
fixe, content-blind, en isolation totale (`size=1`, `think=False`) — les
deux types testés formulés comme une **auto-évaluation contre un seuil**
(`candidacy_considered` : ambition suffisante pour se présenter ;
`party_nomination_choice` : comparaison d'ambition entre pairs, sans
acteur externe) ne collapsent pas (5/5 et 4/5). Lecture affinée deux fois
avant de s'arrêter ici : ni « présence d'un acteur externe nommé »
(`representative_response` n'en a aucun dans son `ctx` et collapse quand
même) ni « ton adversarial » (`coalition_decision` est une décision de
coopération, pas d'opposition, et collapse aussi) ne tenaient sur les 6
cas regardés. 4/4 formulations acte/réponse collapsent, 2/2
auto-évaluations à seuil ne collapsent pas — un signal fort, pas une
preuve causale du mécanisme (le retrait d'une phrase de cadrage
spécifique ne suffit déjà pas à expliquer le cas le mieux caractérisé des
quatre, `pressure_action`). Preuves complètes, protocole, et ce que ce
résultat ne prouve pas : `plan-adversarial-framing-collapse.md`.

**Ce que ça impose concrètement** : tout futur type de décision formulé
comme un acte ou une réponse avec conséquence institutionnelle (pas une
simple auto-évaluation contre un seuil) doit être testé en isolation
(`size=1`, cas extrêmes des deux pôles, vérité de référence si elle
existe sinon signature de collapse) **avant** d'être considéré fiable en
production — ne pas présumer qu'une auto-évaluation et un acte/réponse se
comportent pareil sous prétexte qu'ils partagent le même schéma de sortie
JSON/batch. Ce n'est pas une interdiction de ce type de décision,
seulement une charge de vérification qui ne s'applique pas à une
auto-évaluation à seuil.

#### 3.6.1 Vote citoyen — `vote_cast`

**Résolution du corollaire de B1** (classement complet vs tronqué) : la
forme du bulletin dépend de la méthode active, jamais un format unique.

| Famille de méthode | Format | Troncature |
|---|---|---|
| `plurality`, `two_round`, `irv`, `coombs`, `bucklin`, `minimax`, `schulze`, `kemeny_young`, `copeland`, `nanson`, `baldwin` | `ranking` | **Complet si ≤ 6 candidats, sinon top-5** ; les non-classés sont ex æquo derniers (convention Condorcet standard, déjà cohérente avec `engine/utils`) |
| `approval` | `approved` (liste d'ids) | Aucune |
| `simple_score`, `star`, `median`, `majority_judgment` | `scores` (id → valeur) | Aucune, échelle fixée par la méthode |
| Vote de confiance (§7bis.4a) | `binary` | N/A |

*Justification du seuil de 6* : au-delà, un classement complet dégrade la
qualité de sortie du LLM sans gain réaliste — un électeur humain n'ordonne
pas 15 noms non plus. Le top-5 reste compatible avec toutes les méthodes
de Condorcet listées, qui gèrent nativement les classements partiels.

**Contrainte dure sur `blank`** : si `blank = 1`, tous les autres champs
de choix doivent être vides — validé applicativement avant écriture au
journal, pas seulement espéré du LLM.

#### 3.6.2 → 3.6.8 Autres types de décision

Un schéma par type : `candidacy_considered` / `candidacy_declared` (avec
le champ `path` distinguant les deux chemins du §2.4),
`party_nomination_choice`, `campaign_positioning`,
`representative_response` (§3.6.5, détaillé ci-dessous),
`pressure_action` (§3.6.6, détaillé ci-dessous), `reaction_to_event`,
`coalition_decision`.

`campaign_positioning` et `representative_response` renvoient un **delta
borné** de position (`revealed_position_delta`), pas la position absolue :
plus facile à valider par garde-fou de plausibilité, et moins coûteux
qu'un vecteur à 20 dimensions à chaque tick.

#### 3.6.5 `representative_response` — le schéma central de la révision 2 🔴

C'est ici que les signaux de pression (§7bis) entrent explicitement dans
le contexte du LLM-représentant, et que sa réaction est capturée de façon
structurée et exploitable statistiquement :

```json
{
  "cid": 205,
  "dt": 6,
  "office": 1,
  "ctx": { "L": 0.34, "mandate_dev": 0.41, "street": 0.58, "lame_duck": 0, "ticks_left": 6 },
  "delta": { "7": -0.15 },
  "stance": 1,
  "motif": 302
}
```

`stance` est un **enum fermé** (pas de texte libre), ce qui rend
observable sans relecture qualitative systématique le comportement
recherché en §7bis.4b — réaction prématurée à un signal faible, ou
inversement indifférence jusqu'à la sanction institutionnelle :

```
1 = concession             # ajuste sa position vers le mécontentement perçu
2 = defiance               # maintient ou accentue malgré la pression
3 = silence                # aucun ajustement, aucune communication
4 = counter_mobilization   # tente de mobiliser son propre camp en retour
```

#### 3.6.6 `pressure_action` — la décision citoyenne de pression 🟢 *(rév. 2b)* 🔴 **fiabilité non établie, 2026-08-30**

**Alerte qualité, pas un point de conception ouvert — clôturée (pas résolue) le 2026-08-30** :
`reasoning_budget_and_decision_quality_findings.md` a écarté trois causes par test direct
(position, taille de chunk de 1 à 25 y compris isolation totale, la phrase « 0/4 sont des
résultats légitimes » agissant seule) sans identifier le mécanisme réel. Hypothèse structurelle
restante, non testable par suppression : le menu à 5 options dont 2 (`NOTHING`,
`WAIT_FOR_ELECTION`) sont structurellement posées comme catégorie toujours légitime. **Candidat
concret pour une session de conception future** (même discipline que le concept de « loi »
manquant pour #11) : scinder la décision en jugement binaire agir/ne-pas-agir d'abord, puis choix
du levier (SIGN/LAUNCH/MOBILIZE) seulement si « agir ». Voir le document de findings et
`plan-decision-quality-validation.md` pour la preuve complète. Toute lecture de
`mobilization_rate`/pression citoyenne issue d'un run avec `llm.enabled=True` depuis
l'introduction de ce type de décision (v4 Lot 7) devrait être considérée avec cette réserve
jusqu'à remédiation.

Symétrique de `representative_response` : ce que le citoyen mécontent
décide de faire, parmi le menu constitutionnel disponible (§7bis.2).

```json
{
  "cid": 412,
  "dt": 10,
  "target": 205,
  "ctx": { "self_gap": 0.61, "mandate_dev": 0.41, "neighbors_acting": 0.22, "ticks_to_election": 9 },
  "act": 1,
  "motif": 301
}
```

`act` est un enum fermé (§3.7.1) : `0` ne rien faire · `1` signer une
pétition en cours · `2` lancer une pétition · `3` participer à une
mobilisation · `4` attendre la prochaine élection.

**`neighbors_acting` n'est renseigné qu'à partir de v6** (§7bis.9e) : il
suppose le graphe social du §5. En v4, le champ vaut `null` et chaque
citoyen décide sans voir les autres — régime de pression atomisée
(§7bis.9f).

**Contrainte dure** : seules les valeurs autorisées par le
`pressure_menu` actif peuvent apparaître — un `act` hors menu invalide le
batch (rejeu, §3.6.10). Les codes `0` et `4` restent toujours valides,
quel que soit le menu.

**Remplace** l'ancien `petition_signature_decision` de la rév. 2, qui ne
couvrait qu'un seul levier et ne permettait pas d'observer l'arbitrage
entre leviers — ni l'inaction.

#### 3.6.9 Motifs — codes courts partout, texte libre aux pivots

**Résolution du point ouvert n°7** : codes courts obligatoires sur toute
décision courante ; `rationale_free_text` autorisé uniquement sur une
liste fermée d'événements pivots — `candidacy_declared`, changement de
parti, `representative_response` avec `stance ∈ {concession, defiance}`,
`confidence_vote_result` menant à un rappel, `opinion_shift` majeur.
Longueur bornée (1-2 phrases), jamais libre : un champ non borné romprait
le budget de tokens que ce compromis cherche précisément à protéger.

#### 3.6.10 Validation et gestion d'échec

- Schéma imposé par grammaire JSON côté serveur d'inférence (vLLM et
  Ollama supportent tous deux le JSON contraint).
- Validation applicative dans `llm_client.py` avant écriture : cohérence
  `blank` ⇄ champs de choix, longueur de batch, `cid` présents et uniques.
- Un batch invalide est **rejoué intégralement**, jamais corrigé
  partiellement — pour ne pas introduire de non-déterminisme silencieux
  (cohérent B2).

---

### 3.7 Codebook — compression des sorties par tables de correspondance 🟢 *(nouveau — contribue à B4)*

#### 3.7.0 Principe

Les champs énumérés sortent en **entiers**, pas en chaînes. Un champ
comme `"STREET_PRESSURE_RESPONSE"` coûte plusieurs tokens ; le code `302`
en coûte un à deux. Sur un batch de 25 citoyens avec 4-5 champs énumérés
par décision, répété à chaque tick et pour chaque type de décision,
c'est le poste d'économie le plus direct sur le budget total de B4
(`ticks × cohortes × types de décision`).

Le LLM reçoit la table **une fois** dans son system prompt ; le décodage
vers les libellés humains se fait **en aval**, à la compaction analytique
(§16.6), jamais pendant le run.

**Règle dure** : le codebook est un artefact **figé et versionné**, au
même titre que la bibliothèque de personas (§9). Toute modification
implique un nouveau `codebook_version` — jamais une édition silencieuse
de la version en cours, qui casserait la reproductibilité (§4). Un run
archive son `codebook_version` au même titre que sa config et sa graine.

Stockage : `docs/research/codebook.json`, archivé avec chaque run.

#### 3.7.1 Tables principales

| Champ | Codes |
|---|---|
| `role` | 0 électeur · 1 candidat · 2 élu |
| `office` | 0 aucun · 1 président · 2 député |
| `decision_type` (`dt`) | 1 vote_cast · 2 candidacy_considered · 3 candidacy_declared · 4 party_nomination_choice · 5 campaign_positioning · 6 representative_response · 8 reaction_to_event · 9 coalition_decision · 10 pressure_action |
| `ballot_format` (`bf`) | 1 ranking · 2 approval · 3 scores · 4 binary |
| `path` (candidature) | 1 dominant · 2 rupture |
| `outcome` | 0 declined · 1 declared |
| `action` (coalition) | 1 join · 2 leave · 3 maintain · 4 propose |
| `act` (pression, §3.6.6) | 0 rien · 1 signer · 2 lancer · 3 mobiliser · 4 attendre |
| `stance` (§3.6.5) | 1 concession · 2 defiance · 3 silence · 4 counter_mobilization |

Le code `7` (`petition_signature_decision`) est **retiré et non
réattribué** : réutiliser un code libéré rendrait deux
`codebook_version` différentes silencieusement incompatibles à la
relecture d'anciens journaux.

**Booléens en 0/1**, jamais `true`/`false` : `blank`, `confidence`,
`lame_duck`, `party_change`.

#### 3.7.2 Motifs — plages par catégorie

Convention : **préfixe de catégorie × 100**, pour permettre l'extension
sans collision.

| Plage | Catégorie | Exemples |
|---|---|---|
| 100-199 | Vote | 101 NO_MATCHING_PRIORITY · 102 SOCIAL_CONTAGION · 103 RETROSPECTIVE_PUNISHMENT · 104 STRATEGIC_DEFECTION |
| 200-299 | Candidature | 201 INSUFFICIENT_PERCEIVED_SUPPORT · 202 IDEOLOGICAL_RUPTURE · 203 AMBITION_THRESHOLD_MET |
| 300-399 | Pression citoyenne | 301 MANDATE_DEVIATION_HIGH · 302 STREET_PRESSURE_RESPONSE · 303 LEGITIMACY_FLOOR_APPROACHING · 304 RESIGNATION_NO_LEVERAGE · 305 DEFERRED_TO_ELECTION · 306 FOLLOWING_NEIGHBORS |
| 400-499 | Événements exogènes | 401 SCANDAL_TRUST_EROSION · 402 ECONOMIC_SHOCK_REACTION |
| 500-599 | Coalition | 501 IDEOLOGICAL_PROXIMITY · 502 OFFICE_SEEKING · 503 COALITION_RUPTURE_DISAGREEMENT |

Liste volontairement **non figée** : à stabiliser à l'usage réel, pas à
sur-spécifier avant d'avoir observé de vraies sorties.

#### 3.7.3 Ce qui reste en clair, volontairement

Trois catégories ne sont **pas** codées, par choix délibéré :

1. **Identifiants** (`cid`, `party_id`, `coalition_id`) — déjà compacts ;
   les coder ne gagne rien et complique le débogage.
2. **`rationale_free_text`** — en clair par nature.
3. **Valeurs numériques continues** (`delta`, `scores`, positions) — déjà
   compactes ; coder du continu n'a pas de sens.

Le codebook cible spécifiquement les **champs énumérés à faible
cardinalité mais répétés à très haute fréquence** — c'est là qu'est le
gain réel.

#### 3.7.4 Décodage en aval

Cohérent avec la séparation chaud/froid (§16.1) : le journal brut reste
**en codes**, aussi compact que possible. Le décodage se fait uniquement
à l'indexation post-run (§16.6), par jointure contre le codebook figé —
jamais par réécriture du journal brut.

---

## 4. Reproductibilité et cache 🟡

### 4.1 Principe

Une même graine doit reproduire exactement le même run, y compris les
décisions issues du LLM — condition nécessaire à la comparaison contrôlée
de configurations (§10).

**Trois artefacts figés** conditionnent cette garantie et doivent être
archivés avec chaque run : la **config** (`polity_config.yaml`), la
**bibliothèque de personas** (§9) et le **codebook** (§3.7).

### 4.2 Mécanique de cache

`llm_client.py` mémorise chaque réponse indexée par le hash de l'entrée
exacte envoyée. Rejouer un run avec la même graine régénère les mêmes
entrées → mêmes hash → mêmes réponses en cache, sans appel réseau.

**Conditions nécessaires (B2)**, en contraintes dures dans `llm_client.py` :
- `temperature = 0` — sinon deux appels identiques divergent avant même
  d'atteindre le cache ;
- **version de modèle épinglée** — un tag `latest` qui change casse
  silencieusement la reproductibilité entre deux sessions de travail.

**⚠️ Ces deux conditions pourraient être insuffisantes.** La sortie d'un
serveur d'inférence batché peut varier selon la composition du batch,
même à température nulle (§15bis.4c). Hypothèse non vérifiée du plan
actuel, alors qu'elle conditionne le test de reproductibilité le plus
important du projet — protocole de vérification en §15bis.5, à exécuter
**avant** d'écrire `llm_behavior_engine.py`.

### 4.3 Limite à accepter 🔴

Le cache garantit la reproductibilité **d'un run rejoué**, mais ne permet
quasiment aucune réutilisation **entre** runs Monte Carlo différents
(chaque run explore un espace d'états différent). À documenter comme
limite connue plutôt qu'à résoudre prématurément — le coût d'appel doit
être budgété en conséquence (§12, auto-hébergement).

---

## 5. Réseau social et contagion 🟢

Fondement théorique inchangé :
- **Diffusion à seuil** (Granovetter, 1978) pour l'adoption de
  comportements collectifs.
- **Diffusion du vote blanc/nul comme protestation** (Superti, 2020 ;
  Aron & Superti, 2022).
- **Polarisation affective** (Iyengar et al., 2019).

Ces mécanismes sont des **éléments de contexte fournis au LLM** (ex. « X%
du voisinage social de ce citoyen a déjà adopté le vote blanc ») plutôt
que des formules de mise à jour numérique autonomes — cohérent §3.3.

**Ajout rév. 2b** : le graphe social alimente le champ
`neighbors_acting` de la décision `pressure_action` (§3.6.6) et module le
seuil d'éveil des citoyens (§7bis.9c). C'est le lien direct entre la
contagion micro et la pression institutionnelle macro — et **la condition
nécessaire de tout basculement collectif** : sans lui (régime v4), les
cascades sont mécaniquement impossibles (§7bis.9f).

**🔴 Ouvert** : graphe social statique ou évolutif (homophilie) ? — informé, pas clos, par le palier
v6a : `social_graph.evolving` est analysé (un typo échoue bruyamment) mais **rejeté** si `true`
(garde-fou TRANCHÉ, v6a Lot 1) ; seul un graphe statique est implémenté et exercé par le run
d'acceptation de v6a Lot 4 (`scripts/acceptance_v6a_results.md`). La question elle-même reste ouverte.

---

## 6. Horloge institutionnelle 🟢

**Unité de temps tranchée (A1)** : `1 tick = 1 trimestre` (4 ticks/an,
**120 ticks** sur 30 ans). Un mandat de 4 ans = 16 ticks. Équilibre entre
finesse temporelle et coût LLM (3× moins d'appels qu'une granularité
mensuelle).

- Élection présidentielle : `t = 0, 4, 8, ... 28` (ans)
- Élection parlementaire : `t = 2, 6, 10, ... 30` (ans), décalage
  **paramétrable**, pour permettre la comparaison de configurations
  constitutionnelles (Shugart & Carey, 1992).

**Attribution des sièges (A4)** : 100 sièges, D'Hondt par défaut
(`sainte_lague` et `largest_remainder` disponibles), seuil d'accès à 5%.
Ces choix ont un effet direct et documenté sur le nombre effectif de
partis — la métrique centrale du §10 — et ne pouvaient pas rester
implicites sans laisser un artefact d'implémentation contaminer le
résultat.

États institutionnels dérivés : `president`, `assembly_composition`,
`government_coalition`, `cohabitation: bool`.

---

## 6bis. Règles électorales additionnelles *(nouveau)*

### 6bis.1 Limitation de mandats 🟡

Les champs existaient déjà en config mais valaient `null`. L'enjeu n'est
pas de les activer : c'est d'observer l'**effet lame duck** — un élu en
dernier mandat possible devrait, en théorie, être moins sensible aux
canaux de pression du §7bis, puisqu'il ne cherche plus la réélection.

- **v0/v1** : compteur `mandates_served`, blocage de candidature si
  `mandates_served >= term_limit`. Aucun effet comportemental.
- **v2+** : le prompt indique explicitement le statut (« tu ne peux pas
  te représenter »). On observe si le LLM ajuste sa sensibilité — sans
  qu'aucune règle ne force ce changement (§3.3).

**Nouvelle métrique** : `lame_duck_deviation_delta` — `mandate_deviation`
moyen des élus en dernier mandat vs élus rééligibles. Test empirique
direct de l'hypothèse.

### 6bis.2 Vote blanc compétitif 🟡

Le champ existait (`blank_vote_competitive`, prévu v1), sans spécification.

**Règle** : si le vote blanc dépasse `blank_invalidation_threshold` (0.5
par défaut) des suffrages exprimés, l'élection est **invalidée** — aucun
élu, nouveau scrutin après `reelection_delay_ticks`, plafonné à
`reelection_max_attempts` (au-delà, un résultat est forcé pour éviter la
boucle infinie).

**Décision recommandée** : les candidats de l'élection invalidée sont
**interdits de se représenter immédiatement**. Sinon le mécanisme n'a
aucun effet réel : un vote blanc massif suivi du retour des mêmes
candidats ne change rien à l'espace politique observable.

**Interaction §7bis** : un vote blanc massif alimente aussi
`discontent_signal(t)`, même sans citoyen individuellement identifié
comme mobilisé — cohérent avec la diffusion du vote blanc comme
protestation (Superti, 2020).

### 6bis.3 Chambre de tirage au sort 🔴

Mentionnée comme « prévue » dans `traceability.md` §7.1, jamais
développée. La plus structurante des quatre règles.

**Principe** : chambre séparée de citoyens tirés au sort, mandat court non
renouvelable. Intérêt scientifique direct : **groupe de contrôle**
insensible à toute pression électorale (aucune réélection possible),
comparable à la chambre élue soumise aux trois canaux du §7bis.

- **v0/v1** : tirage uniforme, mandat court fixe, ni vote de confiance ni
  rappel applicables — par construction, un tiré au sort n'a aucun mandat
  électoral à trahir.
- **v2+** : gouverné par LLM pour ses décisions en chambre, mais **sans
  aucun** des trois canaux de pression injectés dans son prompt.
  Hypothèse à tester : l'absence de pression électorale produit-elle des
  décisions plus « sincères » (alignées sur ses propres
  `issue_positions`) ou plus erratiques (aucun garde-fou de
  responsabilité) ?

**Décision de calendrier** : maintenue en **v6+**, pas d'activation
simultanée avec les canaux de pression du §7bis — pour ne pas faire porter
deux nouveautés majeures au même palier de validation.

**🔴 Ouvert, différé au-delà de la feuille de route actuelle (v0-v8),
2026-08-29** : pouvoir réel de la chambre — veto suspensif limité
(recommandé : retarde une loi de N ticks sans la bloquer) ou purement
consultatif ? Sans pouvoir réel, l'intérêt de la comparaison s'effondre.

**Découverte en cadrant ce point** : « pouvoir réel » suppose un concept
de **loi individuelle** (quelque chose qu'un veto pourrait retarder) qui
**n'existe nulle part dans le modèle**. `legislative_result` n'est que
l'allocation de sièges d'une élection ; rien en aval ne représente un
acte législatif précis. `chamber_deliberation` (v6b Lot 3, dt=11, déjà
implémenté) n'a aucun lien avec quoi que ce soit de législatif — chaque
membre décide seulement de dévier ou non de sa **propre** position
(`ChamberDecision.shifts`/`motif`), exactement le même patron
auto-référentiel que `representative_response` ; ce n'est pas un
mécanisme de revue législative sur lequel greffer un veto.

Donner un pouvoir réel à la chambre exigerait donc : (1) inventer ce que
la chambre voterait concrètement (candidat le plus naturel : retarder
l'entrée en vigueur d'une coalition nouvellement formée de N ticks — le
seul artefact du modèle qui ressemble à « un programme de gouvernement »),
(2) un nouveau `decide_*` distinct de `chamber_deliberation`, sa propre
config/codebook/schéma/spike de fiabilité/run d'acceptance, (3) définir
ce que « retardé » signifie mécaniquement dans le séquencement de
`run_polity_simulation.py`. Un chantier de la taille de v7 (négociation
de coalition), pas un Lot 1 léger — au-delà de ce que §13 planifie
jusqu'à v8. Décision explicite : différer, ne pas cadrer aujourd'hui.
Cette découverte reste valable pour une future décision — pas besoin de
la refaire.

### 6bis.4 Calendrier concurrent vs décalé 🟡

Déjà paramétrable, jamais traité comme variable d'intérêt en soi.
Proposition : en faire une **dimension explicite de comparaison Monte
Carlo** (§14.5).

**Hypothèse à observer** : la pression citoyenne est-elle plus efficace en
calendrier concurrent (`offset = 0`, les deux mandats sanctionnés
simultanément, effet « coup de balai » possible) ou décalé (`offset = 2`,
élections intermédiaires servant de test de mi-mandat, cf. littérature sur
le *midterm effect*) ?

### 6bis.5 Interactions avec les canaux de pression

| Règle électorale | Interagit avec (§7bis) | Effet attendu à observer |
|---|---|---|
| Limitation de mandats | Mandat impératif, mobilisation | Effet lame duck sur les deux canaux continus |
| Vote blanc compétitif | Mobilisation sociale | Pression diffuse sans identification individuelle |
| Chambre de sortition | Aucun, par design | Groupe de contrôle élu vs tiré-au-sort |
| Calendrier concurrent/décalé | Pétition, vote blanc | Timing de la sanction électorale vs continue |

---

## 7. Capital de légitimité et rappel 🟡

### 7.1 `L` reste une variable d'état numérique

`legitimacy_capital` existe par élu, mis à jour à chaque tick
(accumulateur EWMA). Ce n'est pas remplacé par du texte libre — c'est un
nombre que le LLM **lit** comme contexte.

**Formule réintégrée (résout A6)** :

```
L(t) = decay · L(t-1) + support(t) − écart(t)
L₀   = f(force du mandat initial)
```

`écart(t)` est défini en §7bis.0. `support(t)` reste à définir
opérationnellement — non bloquant en v0 (`legitimacy.enabled: false`),
bloquant pour v4.

### 7.2 Plancher dur — lisibilité externe avant tout 🟢

**Décision tranchée** : `L(t)` déclenche un rappel **automatiquement** dès
qu'il franchit un plancher dur, indépendamment de tout raisonnement du
LLM. Raison explicite : garder un événement institutionnel **lisible de
l'extérieur** — pouvoir dire « voilà ce qui s'est passé et pourquoi » sans
décortiquer un raisonnement génératif opaque.

Ça ne contredit pas §3.1 : le LLM continue de gouverner *comment* le
mécontentement s'accumule et se diffuse, mais le **déclenchement
institutionnel** reste une règle du jeu déterministe et auditable, au même
titre que la méthode d'agrégation (§3.2).

**Tranché** : plancher **fixe** pour toute la simulation
(`recall_floor: 0.2`), non indexé sur `L₀` — un plancher mobile aurait
rendu l'événement moins lisible de l'extérieur, ce qui contredit la
justification même du mécanisme.

---

## 7bis. Pression citoyenne sur les représentants *(réécrit — rév. 2b)*

### 7bis.0 Le défaut corrigé par cette réécriture 🟢

La première version de cette section décrivait trois « canaux de
pression » qui, à l'examen, n'en étaient pas :

- `mandate_deviation` était **calculé** par comparaison de deux vecteurs —
  aucun citoyen n'agissait ;
- `street_pressure` était **calculé** à partir d'une distance moyenne —
  aucun citoyen n'agissait davantage ;
- la pétition avait une moitié définie (qui signe) et une moitié absente
  (qui la lance).

C'étaient donc des **accumulateurs de mécontentement mesurés par le
concepteur**, pas des leviers actionnés par quelqu'un. Un modèle qui
prétend étudier les moyens de pression des citoyens ne peut pas laisser
la pression émerger d'une formule qu'aucun citoyen ne décide d'appliquer.

### 7bis.1 Principe : deux étages, une frontière déjà existante 🟢

La résolution ne consiste pas à choisir entre « le concepteur décide » et
« les citoyens décident » — les deux interviennent, à des étages
différents, selon la frontière déjà posée en §3.2 :

| Étage | Qui décide | Nature | Analogue existant |
|---|---|---|---|
| Quels leviers **existent** dans cette constitution | Le concepteur, via config | Règle du jeu | Méthode électorale, seuil à 5% |
| Quel levier un citoyen mécontent **actionne** | Le LLM | Comportement | Décision de vote |

Le concepteur fixe le **menu**, les citoyens choisissent **dans le menu**.
Imposer le menu est légitime — c'est une règle constitutionnelle au même
titre que D'Hondt. Imposer *quel* levier est utilisé serait exactement la
prescription comportementale que le §3.3 refuse.

### 7bis.2 Le menu constitutionnel 🟢

Chaque levier est activable indépendamment. La comparaison de deux menus
devient un objet d'étude en soi (§14.5).

```yaml
pressure_menu:
  petition_enabled: true          # lancer / signer une pétition de défiance
  mobilization_enabled: true      # participation à une mobilisation publique
  electoral_only: false           # si true, désactive tout : seule la
                                  # prochaine élection permet de sanctionner
```

Le cas `electoral_only: true` est le **groupe de contrôle** le plus
important du modèle : une démocratie purement représentative, sans aucun
recours entre deux scrutins. C'est le point de comparaison contre lequel
tout levier additionnel doit prouver son effet.

### 7bis.3 `pressure_action` — la décision citoyenne manquante 🟢

Nouveau `decision_type` (§3.6.6bis), soumis à un citoyen dont le
mécontentement envers un élu dépasse un seuil d'éveil. Le LLM reçoit :

1. **Son état de mécontentement** — écart entre ses propres
   `issue_positions` et la `revealed_position` de l'élu, et l'écart entre
   la `pledged_platform` de cet élu et sa `revealed_position` (§7bis.5) ;
2. **Le menu disponible** — uniquement les leviers activés en config ;
3. **L'état du contexte** — pétitions en cours, niveau de mobilisation
   déjà visible, nombre de ticks avant la prochaine élection ;
4. **Ce que son voisinage social a fait** (§5).

Aucune heuristique n'est fournie sur *quoi* choisir. Le choix est fermé :

```
0 = ne rien faire
1 = signer une pétition en cours
2 = lancer une pétition
3 = participer à une mobilisation publique
4 = attendre la prochaine élection (sanction différée assumée)
```

**L'inaction (0) et l'attente (4) sont des options explicites et
journalisées.** Même raisonnement que pour `candidacy_considered` en
§16.3 : le comportement rare n'est observable que si l'on voit aussi ceux
qui ont renoncé. La proportion de mécontents qui n'agissent pas est
probablement le résultat le plus intéressant du modèle — c'est
exactement ce que la littérature sur le vote de protestation décrit
(Superti, 2020 : la majorité des mécontents « baisse les bras »), et le
même raisonnement que celui qui justifie déjà le chemin rare du §2.4.

**Distinction 0 vs 4** : ne rien faire par résignation n'est pas la même
chose qu'attendre délibérément l'échéance électorale. Les distinguer
permet de mesurer si un électorat privé de leviers intermédiaires
(`electoral_only: true`) se résigne ou reporte réellement sa sanction sur
l'urne — question directement liée à §6bis.4 (calendrier concurrent vs
décalé).

### 7bis.4 Les leviers, un par un

#### a. Pétition de défiance 🟡

Deux actions distinctes, ce qui manquait : **lancer** (code 2) et
**signer** (code 1). Une pétition n'existe que si un citoyen la lance.

```
signed_ratio(t) = signatures cumulées / population_size

si signed_ratio(t) >= petition_threshold :
    → déclenche un vote de confiance (référendum binaire sur le maintien)
    → cooldown_ticks avant qu'une nouvelle pétition vise le même élu
```

Le vote de confiance reste dans `ballot_and_aggregation.py` (format
binaire, aucune nouvelle méthode d'agrégation). Une pétition qui n'atteint
pas son seuil avant `petition_lifespan_ticks` expire — et cet échec est
lui-même une donnée : une mobilisation avortée est un signal politique.

**Événements** : `petition_launched`, `petition_signed`,
`petition_expired`, `confidence_vote_triggered`, `confidence_vote_result`.

**🟡 Ouvert** : plusieurs pétitions concurrentes contre le même élu
peuvent-elles coexister, ou une seule à la fois (les signatures se
concentrant alors mécaniquement) ?

#### b. Mobilisation publique 🟡

Le levier sans seuil institutionnel : il ne déclenche rien
automatiquement, il **rend visible** un mécontentement.

```
mobilization_rate(t) = participants(t) / population_size
street_pressure(t)   = decay_rue · street_pressure(t-1) + mobilization_rate(t)
```

**Changement majeur par rapport à la première version** :
`mobilization_rate(t)` est désormais un **décompte de décisions réelles**
(combien de citoyens ont choisi le code 3), plus un proxy de distance
moyenne. Ça supprime l'incohérence de la version précédente, où tout
était gouverné par LLM en v2+ *sauf* précisément ce signal, resté sur une
formule.

`street_pressure(t)` conserve son double rôle : il alimente `écart(t)`
(§7bis.6) **et** il est injecté qualitativement dans le contexte du
représentant (§3.6.5), ce qui permet d'observer s'il réagit à un signal
faible ou l'ignore jusqu'à la sanction.

#### c. Sanction électorale différée 🟢

Pas un levier actif, mais une option explicite du menu (code 4) : le
citoyen assume d'attendre l'échéance. Ce choix n'a aucun effet sur
`écart(t)` au tick courant — son effet apparaît au scrutin suivant, dans
la décision de vote (§3.6.1).

C'est le seul levier **toujours disponible**, y compris quand
`electoral_only: true` désactive tout le reste.

### 7bis.5 `mandate_deviation` — reclassé : information, pas levier 🟢

**Correction conceptuelle importante.** `mandate_deviation(t)` n'est pas
un canal de pression : personne ne l'« actionne ». C'est une **mesure de
l'écart entre promesse et comportement**, qui sert à deux choses :

1. **Information fournie au citoyen** dans son `pressure_action` (§7bis.3,
   point 1) — c'est ce qui peut *motiver* une action, pas l'action ;
2. **Métrique d'observation** pour l'analyste (§10), notamment le test
   lame duck du §6bis.1.

```
mandate_deviation(t) = distance(pledged_platform, revealed_position(t))
```

- **v0/v1** : `revealed_position` figée = `pledged_platform`, donc
  déviation nulle par construction. Cas de contrôle volontaire : sans
  LLM, aucune dérive de mandat n'est mécaniquement possible.
- **v2+** : la position peut dériver (§3.6.5). Aucune règle n'impose
  *comment* (§3.3).

**Événements** : `mandate_pledge_declared` (à l'élection),
`mandate_deviation_recorded` (au-delà d'un seuil seulement, pour ne pas
saturer le journal).

### 7bis.6 Recomposition de `écart(t)` 🟡

La conséquence directe du §7bis.5 : `écart(t)` n'est plus alimenté par une
mesure de distance, mais par des **actions citoyennes effectives**.

```
écart(t) = w_pet · petition_pressure(t) + w_mob · street_pressure(t)
```

où `petition_pressure(t)` est le ratio de signatures actives contre cet
élu au tick courant.

**Conséquence assumée, et c'est le cœur du modèle** : un représentant qui
trahit intégralement son mandat devant une population **passive** ne perd
aucune légitimité. L'érosion vient de ce que les citoyens *font*, jamais
de ce qu'un observateur *mesure*. C'est une affirmation forte, et c'est
précisément ce qui rend le modèle intéressant — il porte sur la capacité
d'une population à se saisir de ses leviers, pas sur une comptabilité
automatique de la trahison.

**Garde-fou optionnel** si ce parti pris s'avère trop radical à
l'usage — une érosion de fond, indépendante de toute action :

```yaml
legitimacy:
  passive_erosion_weight: 0.0   # 0.0 = pur modèle par l'action (défaut)
                                # > 0 = mandate_deviation érode un peu
                                #       même sans mobilisation
```

Laissé à `0.0` par défaut, pour ne pas réintroduire par la porte de
derrière la mécanique que cette réécriture supprime. À n'activer qu'avec
une justification explicite.

### 7bis.7 Séquencement par tick 🟢

1. Mise à jour de `revealed_position` des élus (§3.6.5) et calcul de
   `mandate_deviation(t)` — **information seulement**
2. Identification des citoyens dont le mécontentement dépasse le seuil
   d'éveil → soumission des cohortes `pressure_action` au LLM (§7bis.3)
3. Agrégation des actions : `petition_pressure(t)`,
   `mobilization_rate(t)`, mise à jour de `street_pressure(t)`
4. Calcul de `écart(t)`, puis de `L(t)`
5. Vérification du seuil de pétition (signatures cumulées)
6. Vérification du plancher dur sur `L(t)` (§7.2) — **priorité sur la
   pétition** si les deux se déclenchent au même tick : la règle la plus
   dure l'emporte
7. Si aucun déclenchement, le représentant reçoit `street_pressure(t)` en
   contexte pour sa décision du tick suivant

**Note d'ordonnancement** : les actions citoyennes (étape 2) sont évaluées
**avant** la réaction du représentant (étape 7, effective au tick
suivant). Le représentant réagit donc toujours à une pression du tick
précédent, jamais simultanément — ce décalage d'un tick évite une boucle
de rétroaction instantanée non résoluble, et correspond à la réalité
(une mobilisation est constatée avant d'être répondue).

### 7bis.8 Coût à assumer 🟡

Avec plusieurs leviers ouverts simultanément, on ne peut plus attribuer
un effondrement de légitimité à un canal précis. La comparaison Monte
Carlo (§14.5) porte alors sur des **menus constitutionnels**
(`electoral_only` vs `pétition seule` vs `pétition + mobilisation`)
plutôt que sur des canaux isolés.

C'est plus riche scientifiquement — c'est même la question du §0 — mais
l'analyse de sensibilité devient combinatoire. Recommandation : traiter
le menu comme **une seule variable expérimentale à 4 modalités**, pas
comme deux booléens indépendants, pour garder un plan d'expérience
lisible.

### 7bis.9 Le seuil d'éveil — hétérogène, dérivé des personas 🟡

#### a. Pourquoi un seuil unique ne peut pas fonctionner

Un seuil global constant produit mécaniquement l'un des deux
comportements dégénérés, et jamais autre chose :

- **trop bas** : toute la population est sollicitée à chaque tick — coût
  LLM prohibitif (§B4), et une mobilisation permanente qui ne signifie
  plus rien ;
- **trop haut** : aucun levier n'est jamais actionné, le §7bis ne produit
  aucune donnée.

Surtout, un seuil unique rend **structurellement impossible** le
phénomène le plus intéressant à observer : le basculement collectif
brutal d'une population jusque-là inerte. Avec un seuil homogène, la
mobilisation croît de façon continue avec le mécontentement moyen. Or ce
n'est pas ainsi que les mobilisations réelles se produisent — un
mouvement de type Gilets jaunes n'émerge pas parce que le mécontentement
moyen a doublé, mais parce que la **distribution des seuils** comportait
un point de rupture, et qu'un déclencheur l'a franchi.

#### b. Fondement théorique — déjà présent dans le projet

C'est exactement l'objet de la **diffusion à seuil (Granovetter, 1978)**,
déjà mobilisée en §5 : des seuils individuels hétérogènes produisent des
dynamiques collectives non linéaires. Un individu à seuil très bas agit
seul ; un individu à seuil élevé n'agit que si beaucoup d'autres l'ont
déjà fait. C'est la **forme de la distribution**, pas sa moyenne, qui
détermine si une population bascule ou reste inerte.

Aucune référence nouvelle n'est introduite : Granovetter figure déjà dans
la bibliographie du projet.

#### c. Le seuil comme propriété du persona 🟡

Le seuil d'éveil devient un **champ du persona** (§9), donc hétérogène
par construction dans la population.

```
awakening_threshold(citoyen) = persona.base_threshold
                             × f(contexte au tick t)
```

où `persona.base_threshold` est une propriété stable de l'archétype
(un « militant » a un seuil bas, un « désengagé » un seuil très élevé),
et `f(contexte)` un modulateur borné, fonction de :

- l'ampleur de la déviation de mandat visible (§7bis.5) ;
- la proximité de la prochaine échéance électorale (un mécontent à trois
  mois d'un scrutin a moins de raisons d'agir hors des urnes) ;
- **en v6 uniquement** : la proportion du voisinage social déjà mobilisée
  (§5) — c'est le terme qui rend les cascades possibles.

**Conséquence sur le point ouvert D5** (schéma de persona non défini) :
cette section le résout partiellement — un persona doit au minimum
porter un `base_threshold`. Le reste du schéma reste ouvert.

#### d. La distinction structurante : le seuil est une porte, pas une décision 🟢

**C'est le point le plus important de cette section.** Coder une règle de
basculement à la Granovetter en dur produirait un basculement **garanti
mais imposé** — pas émergent. Ce serait exactement l'heuristique
comportementale prescrite que le §3.3 refuse, et l'on retomberait dans le
travers qui a fait sortir Liquid Democracy du périmètre.

La sortie tient à une séparation nette :

| Rôle | Qui | Nature |
|---|---|---|
| **Qui est consulté** ce tick-ci | Le seuil d'éveil | Porte d'échantillonnage, mécanique, motivée par le coût |
| **Ce qui est décidé** une fois consulté | Le LLM (§3.6.6) | Comportement, émergent, non prescrit |

Le seuil ne dit jamais « ce citoyen se mobilise ». Il dit seulement « ce
citoyen est suffisamment concerné pour qu'on lui pose la question ». Un
citoyen consulté peut parfaitement répondre `act = 0` — et c'est un
résultat, pas un échec.

Le **basculement collectif**, lui, émerge des décisions elles-mêmes : le
LLM voit `neighbors_acting` dans son contexte (§3.6.6) et décide seul si
ça le fait basculer. Personne ne lui a dit qu'il devait suivre son
voisinage.

**Si l'on inverse cette séparation** — si le seuil décide de l'action —
on obtient une simulation de Granovetter avec un LLM décoratif par-dessus,
c'est-à-dire l'inverse exact de l'objectif du §3.3.

#### e. Deux problèmes de calendrier révélés par cette section 🔴

**1. La cascade a besoin du graphe social, qui n'arrive qu'en v6.** Le
champ `neighbors_acting` du schéma `pressure_action` (§3.6.6) suppose le
graphe social du §5 — or §5 est en v6 et la pression citoyenne en v4.
Incohérence introduite par la révision 2b et corrigée ici.

**2. Une cascade a besoin d'une étincelle.** Les mobilisations réelles
partent d'un déclencheur ponctuel, pas d'une érosion lente. Dans le
modèle, ce rôle revient aux **chocs exogènes du §8** — palier v5. Sans
eux, la seule source de mécontentement en v4 est la dérive de mandat
accumulée, qui produit des érosions graduelles, pas des ruptures.

**Conclusion assumée : un basculement de type Gilets jaunes n'est pas
atteignable avant v6.** Il requiert simultanément le graphe social (v6),
les chocs exogènes (v5) et les leviers de pression (v4).

#### f. Deux régimes explicites, et la comparaison comme résultat 🟢

Plutôt que de réordonner la feuille de route pour tout empiler en v4, on
assume deux régimes distincts — et leur comparaison devient elle-même un
résultat :

| Régime | Palier | `f(contexte)` inclut le voisinage ? | Cascade possible ? |
|---|---|---|---|
| **Pression atomisée** | v4 | Non | Non, par construction |
| **Pression avec contagion** | v6 | Oui | Oui |

En v4, chaque citoyen décide seul, sans voir ce que font les autres.
Aucune cascade n'est mécaniquement possible — c'est le **baseline**.

En v6, le graphe social alimente `neighbors_acting`, et les basculements
deviennent possibles sans jamais être imposés.

La comparaison des deux répond à une question qui mérite d'être posée
frontalement : **une population isolée se mobilise-t-elle jamais, ou la
contagion sociale est-elle la condition nécessaire de toute mobilisation
d'ampleur ?** C'est un résultat plus intéressant que ce qu'aurait produit
l'empilement de tous les mécanismes au même palier.

#### g. Conséquence sur le budget (B4) 🔴

Un basculement est, par définition, un **pic d'appels LLM synchrone** :
une fraction importante de la population franchit son seuil au même tick
et doit être consultée simultanément.

La charge cesse donc d'être régulière (`ticks × cohortes × types de
décision`) pour devenir **explosive par moments**. Deux conséquences :

- le dimensionnement doit viser le **pic**, pas la moyenne — une moyenne
  sous-estimerait structurellement le besoin ;
- argument supplémentaire pour vLLM et son *continuous batching* dès que
  le régime de contagion est activé (§15bis.6).

**En auto-hébergement, ce pic ne coûte pas plus cher : il prend plus de
temps** (§15bis.0). L'hypothèse d'un plafonnement des consultations par
tick, envisagée dans une version antérieure de cette section, est donc
**abandonnée** — elle répondait à une logique de facturation à l'appel,
et aurait écrêté précisément le phénomène qu'on cherche à observer. Voir
§15bis.1.

### 7bis.10 Points ouverts de cette section

1. Distribution des `base_threshold` sur les personas (§7bis.9c) : quelle
   forme ? C'est elle, et non la moyenne, qui détermine si la population
   peut basculer — le paramètre le plus structurant de la section.
2. Calibration de `w_pet` / `w_mob` dans `écart(t)`.
3. Pétitions concurrentes contre un même élu : une seule ou plusieurs ?
4. `passive_erosion_weight` doit-il rester à 0.0, ou le modèle purement
   actionnel produit-il des représentants trop impunis ?
5. ~~Plafonnement des consultations LLM par tick~~ — **tranché** : aucun
   plafonnement (§15bis.1), la prémisse était une logique de facturation
   inapplicable en auto-hébergement.

## 8. Événements exogènes 🟡

Scandales (processus de Poisson) et chocs économiques (AR(1) léger),
inchangés dans leur principe. Leur traitement en aval passe par le LLM
(réaction des citoyens, §3.6.7) plutôt que par une formule d'impact
directe sur `legitimacy_perceived`.

**Calendrier tranché** : volontairement en **v5**. Simuler ces chocs avant
que le cœur comportemental soit stable rendrait impossible de distinguer
un effet du choc d'un artefact du modèle sous-jacent.

---

## 9. Bibliothèque de personas 🟡

20 à 50 archétypes, non calibrés sur des données démographiques réelles
dans un premier temps. Chaque `Citizen` référence un `archetype_id`,
régénéré non pas à fréquence fixe mais à des points de rupture (après un
choc économique majeur).

Artefact **figé et versionné** entre deux régénérations — comme le
codebook (§3.7) et la config, il conditionne la reproductibilité (§4.1).

**Champ obligatoire (rév. 2b)** : chaque persona porte un
`base_threshold` — son seuil d'éveil à l'action politique (§7bis.9c). La
**distribution** de ce champ sur la bibliothèque d'archétypes est le
paramètre qui détermine si la population peut basculer collectivement ou
reste inerte ; c'est une décision de conception, pas un détail de
calibration. Résout partiellement D5 (schéma de persona non défini) — le
reste du schéma demeure ouvert.

---

## 10. Métriques de sortie 🟢

| Métrique | Source | Fréquence | Palier |
|---|---|---|---|
| Nombre effectif de partis | Laakso & Taagepera (1979) | à chaque législative | v0 |
| Taux de cohabitation | dérivé de §6 | cumulatif | v0 |
| Durée de vie des coalitions | dérivé de §3 | par coalition | v0 |
| Trajectoire de légitimité moyenne | `L(t)` moyen | par tick | v4 |
| Fréquence de rappel | dérivé de §7 | cumulatif | v4 |
| **Déviation de mandat moyenne** | §7bis.5 | par tick | v4 |
| **`lame_duck_deviation_delta`** | §6bis.1 | par fin de mandat | v4 |
| **Taux d'inaction des mécontents** | §7bis.3 (`act = 0`) | par tick | v4 |
| **Non-linéarité de la mobilisation** | §7bis.9f (détection de basculement) | par tick | v6 |
| **Répartition des leviers actionnés** | §7bis.3 (`act`) | par tick | v4 |
| **Taux de pétition aboutie** | §7bis.4a | cumulatif | v4 |
| **Distribution des `stance`** | §3.6.5 | par tick | v4 |
| Taux de vote blanc | dérivé de §5 | à chaque élection | v0 |
| Polarisation affective | dérivé de §5 | par tick | v6 |
| Convergence des plateformes | dérivé de §3 | par tick | v2 |

*(En gras : métriques ajoutées par la révision 2.)* Le **taux d'inaction
des mécontents** et la **répartition des leviers actionnés** sont les deux
métriques les plus directement liées à la question de recherche révisée du
§0 : elles disent si une population dispose de leviers *et* s'en saisit.
La **distribution des `stance`** en donne le pendant côté représentants.

---

## 11. Stratégie de validation 🔴

1. **Analyse de sensibilité** : faire varier un paramètre à la fois
   (decay de légitimité, méthode électorale, `w_pet`/`w_mob`). Le
   **menu de pression** (§7bis.2) est traité comme une variable unique à
   4 modalités, pas comme des booléens indépendants — sinon le plan
   d'expérience devient combinatoire (§7bis.8).
2. **Calibration sur cas réels** (en second) : comparer le nombre effectif
   de partis simulé à des trajectoires réelles connues.
3. **Audit d'échantillon des décisions LLM** : vérifier périodiquement que
   le raisonnement reste dans des bornes plausibles.
4. **Comparaison baseline vs LLM** (renforcée par la rév. 2b) : en v0/v1,
   la déviation de mandat est nulle par construction (§7bis.5) et aucune
   `pressure_action` n'existe. Tout écart observé en v2 est donc
   **entièrement attribuable au LLM** — c'est le test le plus propre dont
   dispose le modèle pour mesurer ce que la couche générative apporte.

**🔴 Ouvert** : fréquence et taille de l'audit d'échantillon.

### 11.1 Progression d'échelle 🟢

Construire et tester à **100 citoyens**, puis **1 000**, avant d'envisager
plusieurs milliers. Un comportement incohérent est bien plus facile à
diagnostiquer sur 100 agents que sur 5 000. Ne monter en échelle qu'une
fois le palier précédent stable et compris.

**À VÉRIFIER EXPLICITEMENT AU MOMENT DU PASSAGE À 1 000, pas après.** La
liste opérationnelle complète — règle générale, audit des 27 paramètres en
ratio, et trois autres classes de sensibilité à l'échelle — est **committée**
dans **`docs/adr/v3-readiness-checklist.md`** ; ce fichier-ci n'est pas versionné,
donc c'est la checklist qui fait foi. Origine :
`docs/adr/ADR-003-ballot-access-filter-is-inert.md`. Résumé :

- Le seuil de signatures du chemin de rupture (`rupture_signature_ratio:
  0.005`) **ne rejette structurellement personne tant que
  `population_size <= 200`**, parce que `sympathizer_ratio` compte le citoyen
  lui-même et vaut donc au minimum `1/population_size`. À 1 000, ce plancher
  tombe à `0,001 < 0,005` et le filtre **devient vivant sans prévenir** : il
  faudra alors au moins cinq sympathisants pour déclarer une candidature de
  rupture. Ce n'est pas un paramètre dormant, c'est **un changement de régime
  déclenché par ce palier précis**. Mesurer le taux de rejet du filtre avant
  et après le changement d'échelle, et le publier, plutôt que de découvrir
  l'écart dans les résultats.
- **Classe de risque à balayer, pas seulement ce paramètre** : tout seuil
  exprimé en *ratio de population* dont le plancher atteignable est `1/n`
  change de régime avec `n`. Passer en revue les autres ratios de
  `candidacy:` et `petition:` au même moment (`independent_signature_ratio`
  est concerné en théorie — mais il n'est lu par aucun code de domaine
  aujourd'hui, cf. ADR-003, ce qui est un défaut à traiter avant, pas
  pendant, le changement d'échelle).
- Rappel de coût : `sympathizer_ratio` est en O(n) par citoyen, donc O(n²)
  par évaluation de candidature. À n=100 c'est négligeable et déjà payé par
  le chemin LLM ; à n=1 000 c'est 100× plus cher et à mesurer avant de
  lancer un run complet.

---

## 12. Auto-hébergement et fine-tuning 🟢

- Modèles open-weight pour démarrer (Qwen3, Gemma, Mistral Small), Ollama
  en local pour prototyper, vLLM pour le débit une fois l'architecture
  validée.
- Fine-tuning par distillation théorique — « théorique » au sens
  **méthode principled/formalisée**, PAS théorie-dérivée (voir
  résolution ci-dessous) — en **toute fin** de feuille de route (v8).
- Un seul modèle fine-tuné généraliste (le type de décision passe en
  paramètre du prompt), pas un modèle par type.
- **Ne pas fine-tuner pour le format** (JSON contraint côté serveur
  d'inférence, §3.6.10) ni pour la connaissance (RAG) — seulement pour
  stabiliser le comportement dans le cadre du §3.3.

**Résolu, 2026-08-30** : « distillation théorique » n'était définie nulle
part ailleurs dans ce document ni dans `THEORY.md`, ni dans l'historique
git ou le code. Deux lectures étaient en tension directe :
1. **Auto-distillation sur les bonnes trajectoires** : entraîner le
   modèle sur SES PROPRES décisions déjà réussies (filtrées via l'outil
   d'audit du point ouvert #3, `sample_llm_decisions_for_audit.py`) pour
   réduire les échecs Mode A/B déjà caractérisés cette semaine
   (`lot3_chamber_reliability_results.md`, la saga
   `_VOTE_CAST_MAX_CHUNK_SIZE`/`_CHAMBER_MAX_CHUNK_SIZE`). Cohérent avec
   §3.6.0 (« stabiliser le contenu ») et ne contredit pas §3.3 — aucune
   théorie n'est injectée, seulement moins d'échecs de raisonnement.
2. **Distiller des priors théoriques** (Downs, Riker, etc.) dans les
   poids du modèle — contredirait frontalement §3.3 tel qu'il est écrit
   aujourd'hui (« le LLM ne reçoit aucun critère théorique prescriptif »).

**Tranché en faveur de la lecture 1**, sur deux arguments :
- **La source la plus proche l'emporte.** §3.6.0 pose la clause de but
  du fine-tuning (« stabiliser le contenu dans le cadre du §3.3ᵢ ») dans
  le même souffle que la mention elle-même — la source la moins
  susceptible d'avoir dérivé du sens original. §12, à l'inverse, est le
  seul endroit où « théorique » apparaît, sans aucun contexte pour
  l'ancrer.
- **La nature du flottement est elle-même diagnostique.** Un document
  qui pratique le renvoi croisé rigoureux partout ailleurs, mais laisse
  un terme clé non défini dans une phrase isolée marquée 🟡, ressemble
  bien plus à un vestige de rédaction non nettoyé qu'à une décision
  philosophique assumée. Si un changement de philosophie pour v8 avait
  été voulu, §3.3 lui-même porterait une réserve explicite (« sauf en
  v8 » ou équivalent) — elle n'existe pas.

Cette lecture ne clôt pas le cadrage complet du fine-tuning (données
d'entraînement précises, méthode, protocole d'évaluation restent à
écrire le jour où ce chantier est ouvert) — seulement l'ambiguïté sur ce
que « théorique » désigne, qui bloquait tout cadrage tant qu'elle restait
ouverte.

---

## 13. Feuille de route 🟢

**Principe directeur** : « avant de lâcher les fourmis dans la fourmilière,
il faut construire un vivarium solide où elles ne s'échapperont pas ».
Paramètres ajoutés un à la fois, jamais en bloc.

1. **v0 — squelette mécanique pur, 100 citoyens** : décisions
   déterministes (pas de LLM), calendrier décalé, agrégation via
   `ballot_and_aggregation.py`.
2. **v1 — modèle Citizen unifié** : transitions de rôle, les deux chemins
   de candidature (§2.4), toujours en décisions simplifiées.
3. **v2 — bascule comportementale vers le LLM** :
   `llm_behavior_engine.py`, schéma §3.6, codebook §3.7, batching, cache.
   **Prérequis bloquant** : le protocole de vérification du déterminisme
   sous batching (§15bis.5) doit être exécuté et documenté *avant*
   d'écrire le module.
4. **v3 — passage à 1 000 citoyens** : aucun nouveau paramètre,
   uniquement un test de robustesse au changement d'échelle.
   **Porte d'entrée obligatoire** : `docs/adr/v3-readiness-checklist.md` (résumé
   au §11.1). Seuils exprimés en ratio de population qui changent de régime
   avec `n` — `rupture_signature_ratio` bascule précisément entre 200 et
   1 000 — plus les rythmes par citoyen, les compteurs absolus calibrés à
   n=100, et les calibrations dont la *dérivation* supposait l'échelle.
   « Aucun nouveau paramètre » ne veut pas dire « aucun paramètre ne change
   de comportement ».
5. **v4 — légitimité, rappel et pression citoyenne (§7 + §7bis)** :
   `L(t)`, plancher dur, `pressure_action` et son menu constitutionnel,
   pétition, mobilisation, limitation de mandats (§6bis.1), vote blanc
   compétitif (§6bis.2). *Palier élargi par la révision 2* — c'est ici
   que se joue la question de recherche du §0.
6. **v5 — événements exogènes** (§8).
7. **v6 — contagion sociale et polarisation** (§5) : bascule du régime
   de **pression atomisée** vers le régime de **pression avec contagion**
   (§7bis.9f) — c'est ici, et pas avant, qu'un basculement collectif de
   type mouvement social devient possible, puisqu'il requiert
   simultanément le graphe social (v6), les chocs exogènes (v5) et les
   leviers de pression (v4). + chambre de sortition (§6bis.3) en
   extension isolée.
8. **v7 — négociation multi-tours pour la coalition** (§3.4, Cas 2).
9. **v8 — fine-tuning et auto-hébergement** (§12).

Chaque palier ne progresse au suivant qu'une fois stable et compris.

**Note sur l'élargissement de v4** : les leviers de pression y sont
regroupés parce qu'ils partagent tous `écart(t)`, le même
`decision_type` (§3.6.6) et le même séquencement (§7bis.7) — les séparer
en trois paliers aurait produit des paliers intermédiaires non
interprétables. En revanche, le **menu** reste modulable en config, ce qui
permet l'analyse de sensibilité levier par levier sans multiplier les
paliers.

---

## 14. Représentation graphique 🟡

Quatre échelles distinctes, chacune répondant à une question différente.

### 14.1 Micro — réseau social
Graphe de force (D3.js), citoyens colorés par opinion/vote/parti, pour
observer la contagion se propager visuellement.

### 14.2 Méso — carte de l'espace des enjeux
Projection 2D des 20 dimensions, nuage de citoyens + positions des
partis, animé sur 30 ans. La vue la plus utile scientifiquement : elle
permet de *voir* si les partis convergent vers le centre (Downs) ou se
figent en équilibres polarisés (Kollman-Miller-Page).

**Ajout rév. 2** : afficher simultanément `pledged_platform` et
`revealed_position` d'un élu rend la **dérive de mandat visible
directement** (§7bis.5) — l'écart entre les deux points est la
représentation graphique la plus immédiate du canal.

### 14.3 Macro — séries temporelles
Légitimité moyenne, fragmentation, polarisation, taux de vote blanc,
déviation de mandat, distribution des `stance`.

### 14.4 Institutionnel — frise chronologique
Élections, coalitions, pétitions, rappels, scandales, en timeline Gantt.

### 14.5 Comparatif Monte Carlo
Plusieurs runs superposés avec bandes de confiance, pour comparer deux
configurations constitutionnelles — l'usage scientifique final du modèle.
Dimensions de comparaison prioritaires : **menu de pression** (§7bis.2 —
`electoral_only` vs pétition seule vs pétition + mobilisation),
avec/sans recall, `assembly_offset_years` 0 vs 2 (§6bis.4), avec/sans
limitation de mandats (§6bis.1).

### 14.6 Contraintes techniques 🟡

> **Note (rév. 1)** : cette section est **révisée par le §16.0** pour ce
> qui concerne le *stockage*. La recommandation ci-dessous ne vaut que
> pour le **rendu graphique**, pas pour la persistance analytique.
> *(Résout C2 de l'audit : les deux sections se contredisaient pour un
> lecteur lisant dans l'ordre.)*

- **Rendu** : au-delà de quelques centaines de points animés, éviter le
  SVG par nœud — passer par Canvas 2D ou WebGL (PixiJS).
- **Pipeline** : distinguer les **métriques agrégées** (légères, à chaque
  tick) des **snapshots complets pour l'animation** (échantillonnés, une
  fois par année simulée).

**🔴 Ouvert** : snapshots générés pendant le run ou en post-traitement ?

---

## 15. Auto-hébergement — infrastructure Docker 🟢

Les deux serveurs d'inférence exposent une API **compatible OpenAI** — le
backend FastAPI n'a besoin que de `httpx`, aucun SDK propriétaire.

- **`ollama/ollama`** : prototypage v0-v2, faible trafic, CPU suffisant.
- **`vllm/vllm-openai`** : *continuous batching* adapté au batching par
  cohorte (§3.5). Point de vigilance : au-delà d'environ 4 requêtes
  concurrentes par GPU, le temps de première réponse tend à doubler.

**Critère de bascule révisé (rév. 2c)** : passer à vLLM **dès
l'apparition de décisions récurrentes par tick** (v4), et non au palier
de population v3 comme initialement prévu — cf. §15bis.6, le facteur de
charge dominant n'est pas la taille de la population.

Le cache de reproductibilité (§4.2) se matérialise en **Redis** dans la
même stack. Voir `docker-compose.llm.yml`.

**Argument supplémentaire pour vLLM dès v6** : un basculement collectif
produit un pic d'appels synchrone (§7bis.9g), exactement le cas d'usage
où le *continuous batching* apporte le plus. Le dimensionnement doit
viser le **pic**, pas la moyenne.

**À vérifier avant v2** : support du *prompt caching* par vLLM/Ollama —
détermine si le codebook (§3.7) et la bibliothèque de personas peuvent
n'être payés qu'une fois par session de batch plutôt qu'à chaque appel.
Impact direct sur le budget B4.

---

## 15bis. Parallélisation, temps d'horloge et déterminisme 🟡 *(nouveau — rév. 2c)*

### 15bis.0 Reformulation : le coût est un temps, pas un prix 🟢

Toute la conception précédente raisonnait implicitement en logique API,
où le coût est une facturation au token. En auto-hébergement (§12, §15),
ce cadre est faux. Le coût marginal par token tend vers zéro ; ce qui
reste :

| Poste | Nature | Contrainte réelle |
|---|---|---|
| GPU (achat ou location) | Fixe | Indépendant du volume de tokens |
| **Temps d'horloge d'un run** | Variable | **Le vrai facteur limitant** |
| VRAM | Plafond | Borne la taille du modèle et du batch, pas le volume total |
| Temps humain (ops, débogage, relances) | Variable | Largement sous-estimé |

**Ordre de grandeur pour ce modèle** (120 ticks, batch de 25, 1000
citoyens, v4 complet) : de l'ordre de 2000 à 3000 appels par run, quelques
millions de tokens en sortie. Sur un GPU unique avec vLLM et *continuous
batching*, un run se situe dans la fourchette de quelques dizaines de
minutes ; une campagne Monte Carlo de 30 runs tient dans une nuit.

> ⚠️ **Ce sont des ordres de grandeur, pas des mesures.** Le débit réel
> dépend du GPU, du niveau de quantification et de la longueur effective
> des prompts. À mesurer sur un run de 100 citoyens avant toute
> extrapolation — et à consigner, car ce chiffre conditionne B4.

### 15bis.1 Révision de §7bis.9g — ne pas plafonner les cascades 🟢

Le point ouvert n°19 proposait de plafonner le nombre de citoyens
consultés par tick pour borner le coût d'un pic de mobilisation. **Cette
proposition répondait à un problème de facturation, pas
d'auto-hébergement.**

En auto-hébergé, un pic de cascade ne coûte pas davantage : il prend
simplement plus de temps. Le GPU sature, le tick dure plus longtemps,
et c'est tout.

**Décision tranchée : aucun plafonnement.** Écrêter les consultations
reviendrait à mutiler le phénomène même que le §7bis.9 cherche à
observer, pour économiser une ressource qui ne se paie pas. On accepte
que certains ticks soient dix fois plus lents que d'autres — la seule
contrainte réelle est la patience de l'expérimentateur.

*(Le point ouvert n°19 est donc clos, non par arbitrage mais parce que sa
prémisse était erronée.)*

### 15bis.2 Ce que Docker ne parallélise pas 🟢

Lancer N instances de vLLM sur **un seul GPU** ne multiplie rien :

- chaque instance charge sa propre copie des poids en VRAM — soit N× la
  mémoire, avec un dépassement probable avant même N = 2 pour un modèle
  8B sur 24 Go ;
- toutes se disputent les mêmes unités de calcul ; le débit agrégé reste
  celui du GPU, **diminué** de la contention.

**Le parallélisme recherché existe déjà, à un autre niveau** : le
*continuous batching* de vLLM traite déjà des dizaines de requêtes
concurrentes dans les mêmes passes. Les 25 citoyens d'une cohorte (§3.5)
sont déjà « des agents en parallèle » — au niveau du batch, pas du
conteneur.

**Précision de vocabulaire** : « un agent LLM par citoyen » est
explicitement exclu par le §3.5. Mille citoyens équivaudraient à 120 000
appels par run — la structure que le batching existe précisément pour
éviter. Dans cette section, « worker » désigne toujours un processus
traitant *une part de la charge*, jamais *un citoyen*.

### 15bis.3 Ce qui parallélise réellement 🟢

| Levier | Gain | Complexité | Risque sur §4 |
|---|---|---|---|
| **Runs Monte Carlo en parallèle** (une graine par worker) | Linéaire | Faible | **Nul** |
| Plusieurs GPU, un vLLM par GPU | Quasi linéaire | Moyenne | Faible |
| Sharding des cohortes d'un même tick | Réel si multi-GPU | Élevée | **Élevé** (§15bis.4) |
| Plusieurs conteneurs sur un seul GPU | Nul ou négatif | — | — |

**Recommandation : paralléliser entre runs, pas dans un run.** La charge
dominante n'est pas un run isolé mais la **campagne Monte Carlo**
(§14.5), et les runs sont indépendants par construction — c'est du
parallélisme trivial, sans aucun risque pour la reproductibilité. Chaque
worker prend une graine, écrit son propre journal, et rien n'est partagé.

### 15bis.4 Les trois menaces sur le déterminisme 🔴

Le dev-plan v0 pose comme test transverse le plus important : *deux runs
complets à même graine produisent des journaux identiques octet pour
octet*. Toute parallélisation **à l'intérieur** d'un run menace ce test.

#### a. Composition des batchs

Si les cohortes sont distribuées dynamiquement (« le premier worker libre
prend le lot suivant »), leur composition varie d'une exécution à
l'autre. Or le cache du §4.2 est indexé sur le hash de l'entrée exacte :
batch différent → hash différent → cache manqué → reproductibilité
perdue.

**Contrainte dure** : sharding **statique et déterministe**
(`citizen_id % N`), jamais un ordonnancement opportuniste.

#### b. Ordre d'écriture au journal

D8 exige un `event_id` et un ordre garanti. Avec N workers concurrents,
l'ordre d'arrivée est non déterministe.

**Contrainte dure** : soit l'écriture est sérialisée par un unique
processus, soit les `event_id` sont attribués **en amont** par
l'ordonnanceur, jamais par les workers.

#### c. Le non-déterminisme de vLLM lui-même 🔴

Le plus insidieux. Même à `temperature = 0`, la sortie d'un batch peut
varier selon la **composition du batch** : les réductions en virgule
flottante ne sont pas associatives, et les noyaux GPU empruntent des
chemins différents selon la taille du lot.

**Conséquence** : la garantie B2 (température zéro + modèle épinglé)
pourrait être **insuffisante en pratique**. C'est une hypothèse non
vérifiée du plan actuel, et elle en conditionne le test le plus
important.

### 15bis.5 Protocole de vérification, à exécuter avant v2 🟢

À faire **avant** d'écrire `llm_behavior_engine.py`, pas après :

1. Même prompt exact, soumis dans des batchs de tailles différentes
   (1, 5, 25, 50). Comparer les sorties octet pour octet.
2. Même batch, même taille, exécuté dix fois de suite. Comparer.
3. Répéter après redémarrage du conteneur vLLM (état de compilation des
   noyaux potentiellement différent).

**Si les sorties divergent** — hypothèse à considérer comme probable
plutôt qu'improbable — alors :

- le déterminisme ne peut plus reposer sur le modèle, mais **entièrement
  sur le cache** (§4.2) ;
- la composition des batchs doit être strictement reproductible, ce qui
  rend le sharding statique (§15bis.4a) non pas préférable mais
  **obligatoire** ;
- un run rejoué sans cache chaud n'est plus garanti identique — limite à
  documenter au même titre que celle du §4.3.

**Ce protocole est un prérequis de v2, à ajouter à la définition de
« v2 terminée ».**

### 15bis.6 Révision du critère de bascule Ollama → vLLM 🟡

La feuille de route (§13) place Ollama en v0-v2 et vLLM à partir de v3,
au motif du passage de 100 à 1000 citoyens. **Ce découpage suppose que le
facteur de charge est la taille de population — ce que la révision 2b
contredit.**

Le facteur dominant est le **nombre de décisions par tick** :

| Décision | Fréquence sur 30 ans |
|---|---|
| `vote_cast` | ~16 fois (une par scrutin) |
| `pressure_action` | **120 fois** (à chaque tick) |
| `representative_response` | **120 fois** |

L'arrivée de v4 change donc davantage la charge que le passage de 100 à
1000 citoyens. Ollama, qui batche mal, deviendra le goulot d'étranglement
bien avant le palier de population qui était censé déclencher la bascule.

**Critère révisé** : passer à vLLM **dès l'apparition de décisions
récurrentes par tick** (v4), indépendamment de la taille de population —
et non au palier v3.

## 16. Données et traçabilité individuelle 🟢 (schéma 🟡)

### 16.0 Priorité assumée — et révision du §14.6

**Décision tranchée** : pour ce module, la réactivité front-end et la
compacité sont explicitement *dé*prioritisées au profit d'un objectif
unique — suivre le **parcours individuel de chaque citoyen sur 30 ans**.

Ceci **révise la recommandation du §14.6** (« ne pas exporter l'état
complet de chaque citoyen à chaque tick ») : celle-ci reste valable pour
l'**animation graphique**, mais pas pour le stockage analytique. La
volumétrie réelle est modeste (1 000 citoyens × 120 ticks, trivial pour
DuckDB) — c'était un problème de rendu navigateur, pas de stockage.

### 16.1 Deux régimes de flux, strictement séparés 🟢

**Régime chaud — pendant le run** (léger, réactif)
- Seules des **métriques agrégées** circulent, poussées vers le front via
  WebSocket, calculées **incrémentalement en mémoire**, jamais par requête
  sur le journal.
- Le journal (§16.3) est écrit **append-only**, mais n'est ni relu, ni
  indexé, ni interrogé pendant le run. **Il reste en codes** (§3.7.4).

**Régime froid — après le run** (complet, interrogeable)
- Une étape de **compaction/indexation** transforme le journal brut en
  base analytique, avec index sur `citizen_id`, `tick`, `event_type`, et
  **décodage du codebook par jointure** (§3.7.4).
- C'est là que vivent la vue biographie (§16.7) et l'analyse scientifique.

**Pourquoi cette séparation est structurante** : écrire en append-only est
quasi gratuit ; ce sont l'indexation et l'agrégation qui coûtent. Les deux
régimes ont des optimisations contradictoires (write- vs read-optimized).
Et un run interrompu laisse malgré tout un journal exploitable.

### 16.2 Patron retenu : event sourcing

On journalise chaque **événement significatif** en append-only ; la
biographie d'un citoyen se reconstruit en rejouant son journal.

- « Qu'est-il arrivé au citoyen #4172 en 30 ans ? » devient une requête
  filtrée, pas une reconstitution laborieuse.
- Rejouer un run avec la même graine doit produire un journal identique —
  ce qui en fait aussi un excellent test de régression.
- Les métriques du §10 deviennent des **vues dérivées**, pas une seconde
  source de vérité à maintenir.

### 16.3 Schéma d'événement 🟡

Table unique `citizen_events`, une ligne par événement :

| Champ | Description |
|---|---|
| `run_id` | Identifiant du run (+ graine) |
| `event_id` | Identifiant séquentiel garantissant l'ordre (D8) |
| `codebook_version` | Version du codebook utilisée (§3.7) |
| `tick` | Pas de temps simulé |
| `citizen_id` | Le citoyen concerné |
| `event_type` | Type d'événement |
| `payload` | JSON : détails spécifiques au type |
| `motif` | Code court (§3.7.2) |
| `rationale` | Texte libre, uniquement sur événements pivots (§3.6.9) |

Types d'événements journalisés :
- `opinion_shift` — déplacement de `issue_positions` (avec ampleur et cause)
- `party_joined` / `party_left`
- `candidacy_considered` — y compris les *non*-candidatures : le chemin
  rare du §2.4 n'a de sens observable que si l'on voit combien de citoyens
  ont hésité puis renoncé
- `candidacy_declared` / `nomination_won` / `nomination_lost`
- `mandate_pledge_declared` / `mandate_deviation_recorded` *(rév. 2)*
- `vote_cast`
- `pressure_action` — **y compris `act = 0` (inaction)** *(rév. 2b)*
- `petition_launched` / `petition_signed` / `petition_expired` *(rév. 2b)*
- `confidence_vote_triggered` / `confidence_vote_result` *(rév. 2)*
- `representative_response` *(rév. 2)*
- `election_invalidated` / `snap_election_triggered` *(rév. 2)*
- `elected` / `defeated` / `term_ended` / `recalled`
- `legitimacy_updated`
- `reaction_to_event`

**🟡 Ouvert** : faut-il aussi coder `event_type` en entier, par cohérence
avec le codebook (§3.7) ?

### 16.4 Snapshots de reconstruction

Un **snapshot complet de la population à intervalle régulier** (une fois
par année simulée, soit tous les 4 ticks) sert de point de reprise.
Reconstruire l'état du citoyen #4172 au tick 87 = charger le snapshot
annuel le plus proche, puis rejouer les quelques événements postérieurs.

### 16.5 Capturer le *pourquoi* 🟢

Chaque événement décisionnel porte la justification du modèle — c'est ce
qui transforme un journal de données en *récit* : non pas « le citoyen
#4172 a voté blanc au tick 148 », mais « il a voté blanc parce qu'aucun
candidat ne portait sa priorité dominante, après avoir vu son voisinage
social le faire deux scrutins de suite ».

**Tranché** (point ouvert n°7) : **codes courts partout** (§3.7.2), très
peu coûteux en tokens, + **texte libre réservé aux événements pivots**
(§3.6.9), rares donc soutenables. Le texte libre est borné à 1-2 phrases :
un champ non borné romprait le budget que ce compromis protège.

### 16.6 Choix de stockage 🟡

- **DuckDB** (un fichier `.duckdb` par run) — recommandé : orienté
  colonnes, excellent pour « tous les événements du citoyen #4172 » ou
  « distribution des motifs de vote blanc par année », zéro serveur, un
  fichier = un run reproductible.
- **Parquet + DuckDB** pour archiver plusieurs dizaines de runs Monte Carlo.
- **PostgreSQL** : pertinent seulement si le playground doit interroger ces
  données en direct — ce qui n'est pas la priorité.

C'est à cette étape que s'effectue le **décodage du codebook** (§3.7.4).

**🟡 Ouvert** : DuckDB par run confirmé, ou Postgres par cohérence avec la
stack existante ?

### 16.7 Vue « biographie citoyenne »

Une **fiche individuelle** : frise des 30 ans d'un citoyen, opinions qui
dérivent, affiliations, votes, candidatures, pétitions signées,
justifications associées. Contrepartie micro de la §14.4, et probablement
la vue la plus révélatrice pour comprendre *comment* la fourmilière
fonctionne de l'intérieur.

Pour un **élu**, cette vue devient particulièrement dense grâce à la
rév. 2 : `pledged_platform` vs `revealed_position` dans le temps,
trajectoire de `L(t)`, pétitions subies, série des `stance` adoptées face
à la pression. C'est le récit complet d'un mandat sous contrainte.

Pour un **électeur**, la rév. 2b ajoute la série de ses `pressure_action`
— y compris ses inactions. Un citoyen constamment mécontent qui n'agit
jamais est un récit aussi instructif que celui d'un militant.

---

## État des bloquants de l'audit de précision

| # | Objet | Statut | Résolution |
|---|---|---|---|
| A1 | Unité de temps | ✅ | Trimestre, 120 ticks (§6) |
| A2 | Origine des partis | ✅ | 5 partis, k-means, ni naissance ni mort en v0 |
| A3 | `role` président/député | ✅ | `office` + `term_end_tick` (§2.1) |
| A4 | Sièges et attribution | ✅ | 100 sièges, D'Hondt, seuil 5% (§6) |
| A5 | Décisions simplifiées | 🟡 | Règles de vote/candidature fixées ; départage de coalition encore imprécis |
| A6 | Formule de `L(t)` | ✅ | `écart(t)` défini (§7bis.0) ; `support(t) = (1−decay)·m`, `m` = part des bulletins classant le vainqueur au-dessus de Blanc — résolu par le plan v4 (Lot 3), implémenté dans `legitimacy.py`, documenté en `THEORY.md` §10.1 |
| B1 | Schéma de sortie LLM | ✅ | §3.6 |
| B2 | Déterminisme LLM | ✅ | `temperature: 0`, modèle épinglé (§4.2) |
| B3 | Composition des cohortes | 🔴 | Taille fixée (25), critère de similarité non spécifié |
| B4 | Budget de coût | ✅ | Reformulé en **temps d'horloge** et non en prix (§15bis.0) ; mesure réelle faite sur un run de 100 citoyens — v4 Lot 8, `scripts/acceptance_v4_results.md` |
| — | **Déterminisme sous batching** | 🔴 | **Nouveau (§15bis.4c)** : B2 pourrait être insuffisant — protocole de vérification §15bis.5 à exécuter avant v2 |
| C1 | Contradiction §2.3/§2.4 | ✅ | Seuil réduit, pas d'exemption (§2.4) |
| C2 | §14.6 vs §16.0 | ✅ | Note de renvoi ajoutée en §14.6 |
| C3 | Modules de données manquants | ✅ | Arborescence §1 complétée |
| D9 | Fichier de configuration | ✅ | `polity_config.yaml` |

**Reste bloquant avant v2** : B3 (critère de cohorte).
**Reste à finir pour v0** : règle de départage de coalition (A5).

---

## Points ouverts

1. ~~Seuil de la candidature de rupture (§2.4) : quelle fonction de l'écart
   idéologique ?~~ — **tranché 2026-08-29** : `weighted_distance` du
   citoyen à son propre parti affilié, modulant `rupture_base_probability`
   (pas `rupture_signature_ratio`, qui reste la barrière ADR-003 générique)
   via `p = rupture_base_probability × (1 + rupture_distance_multiplier ×
   distance)`, `rupture_distance_multiplier` livré à `2.0`. Byte-identique
   à v1 à distance nulle. Voir `plan-rupture-candidacy-threshold.md` pour
   le cadrage complet (options écartées, y compris une correction en
   implémentant : le cas `party_affiliation is None` envisagé au cadrage
   n'existe pas en pratique).
2. ~~Valeur du plancher dur sur `L(t)`~~ — **tranché** : fixe (§7.2).
3. Fréquence et taille de l'audit d'échantillon des décisions LLM (§11).
4. ~~Scission de parti : dans le scope ou non ?~~ — **tranché 2026-08-29,
   hors scope** : aucune motivation de recherche n'a jamais été écrite
   nulle part dans ce document pour la scission de parti, contrairement à
   chacun des autres points ouverts déjà tranchés cette semaine — juste
   un flag de config réservé (`parties.split_enabled`), jamais consommé
   par aucun code (même classe que `candidacy.independent_signature_ratio`,
   ADR-003). Même traitement que la candidature indépendante (§2.3 point
   2) : flag supprimé (`config.py`, `polity_config.yaml`), pas seulement
   laissé réservé. Si une scission de parti est un jour motivée par une
   vraie question de recherche, ce sera un chantier dédié avec sa propre
   conception (déclencheur, règle de partage des sièges/de l'électorat,
   etc.) — pas la réactivation d'un flag resté vide de sens depuis le v0.
5. Régénération des personas : à quels points de rupture précis ? Partiellement
   informé (pas clos) par v5 Lot 1 : `events.economy_shock_threshold` définit
   désormais concrètement ce qu'est « un choc économique majeur » — mais la
   bibliothèque de personas elle-même (§9) reste à construire.
6. ~~Fréquence des snapshots~~ — **tranché** : annuelle, 4 ticks (§16.4).
7. ~~Granularité des justifications LLM~~ — **tranché, mais decision
   partiellement non livrée -- rouvert puis reclos 2026-08-29** :
   `llm.rationale_mode` accepte `codes | free_text | hybrid` en config,
   mais `llm_behavior_engine.py:451-452` lève explicitement
   `NotImplementedError` pour tout sauf `codes` — la partie « texte libre
   borné aux pivots » de la décision n'a jamais été implémentée, seul
   `codes` est un chemin réel. Trouvé en cadrant #3 (audit d'échantillon) :
   aucun raisonnement brut n'est donc persisté nulle part pour un appel
   réussi (seul le JSON structuré final atteint le journal) — voir
   `plan-llm-decision-audit-sampling.md` §2 pour les conséquences sur ce
   que peut réellement auditer un échantillonnage. Le choix `codes`
   partout reste le comportement livré ; seule la partie « texte libre »
   de cette entrée était fausse.
8. ~~Stockage (§16.6) : DuckDB par run, ou PostgreSQL ?~~ — **tranché** :
   DuckDB, shipped (PR #140) — `compaction.py`, `indexer.py`,
   `run_polity_simulation.py`, `polity_config.yaml`.
9. ~~Format du vote de confiance (§7bis.4a) : binaire, ou avec challenger ?~~
   — **tranché** : binaire, `accountability.confidence_vote_format: binary`
   (`polity_config.yaml:252`, commentaire « pas de multi-candidats »).
10. Calibration de `w_pet` / `w_mob` dans `écart(t)` (§7bis.6). Mesuré
    (pas tranché) par les sweeps v4 Lot 4/5 — `scripts/awakening_calibration_results.md`,
    `scripts/petition_calibration_results.md` — sans changement des valeurs
    livrées ; informé, pas clos.
11. Pouvoir de la chambre de sortition (§6bis.3) : veto suspensif ou
    consultatif pur ?
12. ~~Vote blanc compétitif (§6bis.2) : interdiction immédiate de se
    représenter confirmée ?~~ — **tranché** : oui, `barred_from_immediate_rerun`
    (shipped `true`, un vrai bras de comparaison via ce toggle) implémenté en
    Lot 9 (PR #141) — `PendingRerun`, `reelection_delay_ticks`,
    `reelection_max_attempts` dans `run_polity_simulation.py`.
13. Distribution des `base_threshold` sur les personas (§7bis.9c) — c'est
    sa **forme**, et non sa moyenne, qui détermine si la population peut
    basculer collectivement. Paramètre le plus structurant de la rév. 2b,
    et le plus sensible au coût LLM. Mesuré (pas tranché) par
    `scripts/awakening_calibration_results.md` (v4 Lot 4) : la distribution
    livrée (`beta(3,5)`) n'a pas été changée, faute de preuve qu'une autre
    forme serait meilleure — informé, pas clos.
14. ~~Codebook (§3.7) injecté en entier dans chaque prompt, ou porté par le
    prompt caching du serveur d'inférence ? Dépend du support technique
    réel — à vérifier avant de trancher (§15).~~ — **prémisse invalidée,
    2026-08-29** : la question suppose un choix entre les deux options.
    Il n'y en a pas. `llm_batching_determinism_results_gpu.md` (18-19 août)
    a établi, en lisant le code source d'Ollama (`llm/llama_server.go`),
    que `cache_prompt: true` est **codé en dur**, sans aucun chemin de
    configuration côté API publique — le cache de prompt du serveur est
    donc actif inconditionnellement, que le codebook soit injecté en
    entier ou non. Injecter le codebook en entier n'est pas une
    alternative au cache serveur, les deux se produisent toujours
    simultanément.
    Pire : ce même cache a été identifié comme facteur causal probable
    d'un vrai bug de fiabilité (troncature `finish_reason='length'` sur
    les appels `think=True`, corrélée à un `f_keep` bas — correspondance
    partielle de mauvaise qualité contre une entrée de cache non
    apparentée), mitigé (pas résolu) par `recycle_after_n_calls`
    (`llm_client.py`). Ce n'est donc pas une optimisation gratuite sur
    laquelle s'appuyer.
    La vraie question que cette investigation soulève, et qu'elle laisse
    explicitement ouverte (« a call for the project owner to make »,
    ligne ~320 du fichier de résultats) : Ollama reste-t-il la bonne
    couche de service pour ce workload (`think=True`, raisonnement long,
    prompts jamais exactement répétés), face à un `llama-server` natif
    (qui expose `cache_prompt` comme une vraie option par requête) ou au
    switch vLLM déjà scopé (§15bis.6, `VllmJsonClient` mergé mais jamais
    basculé en production) ? Non tranchée ici — décision du porteur de
    projet, pas quelque chose que je dois trancher en corrigeant ce
    point.
15. ~~Faut-il coder `event_type` du journal en entier (§16.3), par
    cohérence avec le codebook ?~~ — **tranché 2026-08-29** : non. 29
    valeurs distinctes, stockées en `VARCHAR` indexé dans DuckDB
    (`compaction.py:104`, `:115`) — DuckDB compresse déjà nativement une
    colonne à cardinalité aussi faible, donc aucun gain de stockage réel.
    `event_type` est de plus utilisé en comparaisons littérales
    directement lisibles partout dans `indexer.py`
    (`event["event_type"] == "elected"`, etc.) — coder casserait cette
    lisibilité sans bénéfice mesurable. Contrairement à `decision_type`
    (`codebook.py`'s `DecisionType`), qui reste codé.
16. ~~Ambiguïté Liquid Democracy~~ — **tranché** : hors périmètre du
    polity (cf. « Périmètre exclu » ci-dessous).
17. ~~`passive_erosion_weight` (§7bis.6) doit-il rester à `0.0` ? Le modèle
    purement actionnel produit-il des représentants trop impunis face à
    une population passive ?~~ — **tranché 2026-08-29** : reste à `0.0`.
    Cohérent avec la discipline établie de ne pas rouvrir une calibration
    shippée sans preuve qu'elle est fausse (même logique que #10/#13). Si
    rouvert un jour, la vraie valeur mériterait son propre sweep de
    calibration (comme `awakening_calibration_results.md`), pas une
    décision à la volée.
18. ~~Pétitions concurrentes contre un même élu (§7bis.4a) : une seule à la
    fois, ou plusieurs simultanées ?~~ — **tranché** : une seule à la fois,
    `accountability.concurrent_allowed: false` — le code source le
    qualifie déjà de « TRANCHÉ false » en commentaire
    (`accountability.py:374`, `:479`).
19. ~~Plafonnement des consultations LLM par tick~~ — **tranché** : aucun
    plafonnement (§15bis.1).
20. ~~Le déterminisme de vLLM sous batching variable (§15bis.4c) tient-il ?~~
    — **cadrage périmé, 2026-08-29** : la question telle qu'écrite vise
    vLLM spécifiquement, mais `llm.provider` reste `ollama` (jamais
    basculé en production). La question générale a néanmoins reçu une
    réponse réelle, pour le provider effectivement en usage : `llm_client.py`
    documente une mesure live où température=0 + seed fixée produit quand
    même des sorties différentes sous batching (réduction flottante non
    déterministe en inférence multi-thread) — limite acceptée au §4.3.
    Ce n'est donc plus « la question ouverte la plus critique du plan »,
    c'est une limite déjà mesurée et acceptée pour le provider live ; la
    question resterait à réévaluer spécifiquement si/quand vLLM devient
    le provider effectif.
    **Tentative réelle et blocage, 2026-08-30** : bascule vLLM tentée
    (v8) — le conteneur ne démarre pas du tout sous WSL2/Docker Desktop
    sur ce poste (`RuntimeError: UVA is not available`, bug amont connu,
    correctif non mergé). Décision : `provider` reste `ollama`, pas une
    question de calibration cette fois mais un blocage de plateforme en
    amont. Voir `plan-vllm-switch-readiness.md` §0/§0bis pour le
    diagnostic complet et les conditions de réouverture explicites (le
    correctif amont mergé ET publié, ou un passage à Linux natif pour une
    autre raison) — cette question 20 reste donc « réponse acceptée pour
    le provider live », maintenant avec une tentative de bascule réelle
    et documentée derrière, pas seulement une intention jamais testée.
21. Sharding intra-run (§15bis.3) : **sans objet pour l'instant** —
    subordonné au point 20, jamais eu de second GPU physique pour le
    justifier. À rouvrir seulement si un besoin de déterminisme sous
    plusieurs GPU se présente réellement.

---

## Périmètre explicitement exclu

Cette section existe pour éviter qu'un concept écarté ne revienne
implicitement par une puce isolée dans une liste — le cas exact qui a
produit l'ambiguïté n°16.

### Liquid Democracy — hors périmètre 🟢

La délégation transitive de vote **ne fait pas partie du modèle polity**.
Le module `engine/utils/liquid_democracy_utils.py` reste un chantier
distinct : une simulation de recherche autonome sur les méthodes de vote,
avec sa propre population, sa propre séquence temporelle et sa propre
règle de révocation déterministe. Aucun lien de code, de configuration ou
de journal avec `domain/polity/`.

**Justification du retrait :**

1. **Incompatibilité de principe avec le §3.3.** Déléguer son vote est une
   décision citoyenne ; dans le polity, elle devrait donc être gouvernée
   par le LLM sans heuristique prescrite. Or le modèle de recherche repose
   sur une règle logistique de dissatisfaction cumulée — exactement le
   type de comportement prescrit que le §3.3 refuse.
2. **Échelles temporelles non transférables.** Le module de recherche
   simule une séquence de votes à pas arbitraire ; le polity a des
   trimestres et un calendrier électoral fixe. Les paramètres de decay ne
   se transposent pas.
3. **Trou de responsabilité non résolu.** Un « super-voter » au sens de
   Kling et al. (2015) serait, dans le polity, un citoyen **non élu**
   détenant un pouvoir de vote massif sans aucun canal de responsabilité :
   pas de plateforme engagée donc pas de `mandate_deviation`, pas de
   mandat donc pas de rappel, pas de limitation de mandats. Il échapperait
   intégralement aux trois canaux du §7bis. C'est une question de recherche
   légitime et intéressante — mais elle exigerait un quatrième canal de
   pression conçu pour un pouvoir informel, ce qui dépasse largement le
   cadre de la révision 2.

**Réouverture possible** : ce point 3 est la vraie raison de garder la
porte entrouverte. Si la délégation revient un jour dans le polity, ce
sera comme **palier dédié**, avec son propre `decision_type` gouverné par
LLM (§3.6) et une réponse explicite au trou de responsabilité — pas comme
un simple mode à activer en configuration.

### Conséquence à répercuter dans `traceability.md`

Liquid Democracy y figure aujourd'hui **deux fois**, dans deux tableaux
distincts (« extensions en cours » avec fichier à créer, et « systèmes
alternatifs » sans fichier ni référence). Une seule ligne doit subsister,
celle du chantier `engine/utils`, avec mention explicite qu'elle ne relève
pas du polity.

### Point de vigilance — Conviction Voting 🟡

Le même risque de recouvrement existe, et il est **plus sérieux** : le
prompt d'implémentation de Conviction Voting prévoit une extension
« accountability continue d'un représentant », où les citoyens allouent un
stake de soutien et où un décrochage déclenche un `recall_triggered`.

C'est fonctionnellement un **quatrième canal de pression**, conçu
indépendamment des trois du §7bis, avec sa propre mécanique de
déclenchement de rappel — en concurrence directe avec le plancher dur du
§7.2 et la pétition du §7bis.4a.

**À trancher avant d'implémenter cette extension** : soit elle reste
strictement dans le module de recherche autonome (recommandé, symétrique
au traitement de Liquid Democracy), soit elle devient un canal du §7bis à
part entière — auquel cas elle doit passer par `écart(t)` et le
séquencement du §7bis.7, et non par un mécanisme de rappel parallèle.
Les deux mécanismes de rappel ne peuvent pas coexister sans rendre
l'événement institutionnel illisible de l'extérieur, ce qui annulerait la
justification même du §7.2.
