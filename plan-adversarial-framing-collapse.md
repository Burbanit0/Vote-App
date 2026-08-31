# Cadrage adversarial/relatif-à-une-cible et collapse de contenu en isolation — une hypothèse de conception, pas encore une loi générale

> Découverte de conception, pas une remédiation de prompt isolée — voir
> `plan-pressure-action-remediation.md` pour la question d'origine (comment
> réparer `pressure_action` spécifiquement), qui reste pertinente
> indépendamment de ce document et pourrait être informée par lui une fois
> le principe mieux compris. Ce document existe pour que cette découverte
> soit vue et citée indépendamment, pas enterrée en annexe d'un chantier
> plus étroit — même traitement que ADR-002/ADR-003 pour les découvertes
> de cette ampleur cette semaine.

## Contexte

En remédiant `pressure_action` (`plan-pressure-action-remediation.md` §3.1/
§3.2), deux refontes structurellement différentes (décomposition
binaire-puis-levier, puis langage primaire + traduction algorithmique) ont
échoué au chiffre près identique (17/70, 24,3%) — et un croisement par
identité de citoyen a montré que les deux mécanismes collapsent
**totalement** vers `will_act=True` pour les 70/70 citoyens testés, dans
les deux tests, sans exception. Ce n'était donc pas un sous-ensemble de
cas difficiles pour un contenu donné : aucune variation à tracer, puisque
les deux fonctions sont constantes.

Ça a reformulé la question : ce collapse est-il propre à `pressure_action`,
ou une propension plus générale du modèle sur une décision binaire isolée
dont une réponse ressemble à s'engager/agir ? Un premier test de contrôle
(`candidacy_considered`, autoréférentiel) a écarté l'hypothèse d'une
disposition générale — ce qui a fait émerger l'hypothèse retenue ici :
**pas une disposition générale, mais un risque spécifique au cadrage
adversarial/relatif-à-une-cible** (une partie répondant à/contre une
autre), par opposition à un cadrage purement autoréférentiel.

Quatre types de décision testés au total, même discipline dans chaque
cas : isolation totale (`size=1`), cas extrêmes des deux pôles (pas de cas
ambigus), `think=False` (le chemin de production), prompt/schéma de
production réels et non modifiés, vérité de référence vérifiée contre le
code réel avant tout test — jamais présumée.

## Les deux cas confirmés

### `pressure_action` (dt=10)

Vérité de référence : `deterministic_pressure_action` (`simple_rules.py`),
même entrées que le chemin LLM. Caractérisé en détail dans
`reasoning_budget_and_decision_quality_findings.md` (mises à jour du
2026-08-30) : collapse uniforme du chunk entier à la taille de production
(21-25) ; évitement total des codes d'action à toute taille testée en
dessous, y compris `size=1` en isolation complète (0/63 codes d'action,
0/70 dans le test de remédiation, `check_pressure_action_size_one.py` et
`check_pressure_action_binary_lever_redesign.py`). Position, taille de
batch (1 à 25), et la phrase de cadrage « 0/4 sont des résultats
légitimes » écartées comme causes suffisantes par test causal direct
(réordonnancement, courbe de taille, ablation).

### `representative_response` (dt=6)

Vérité de référence : **vérifiée d'abord, pas présumée** — contrairement à
`candidacy_considered`, `decide_representative_response`'s propre
docstring confirme que le « fallback déterministe » qu'il remplace est
simplement « no delta, stance=silence » **constant**, jamais fonction de
la situation réelle de l'élu. Aucun proxy de justesse possible ; méthode
retenue : la signature de collapse elle-même (même sortie quel que soit un
contexte radicalement différent), pas un taux d'exactitude.

Protocole (`check_representative_response_collapse_signature.py`) : deux
pôles opposés — CRISE (`L=0,05`, `mandate_dev=0,8`, `street=3,0`,
`ticks_left=2`) vs AUCUN-PROBLÈME (`L=0,95`, `mandate_dev=0,0`,
`street=0,0`, `ticks_left=20`) — 3 élus différents par pôle,
`declare_candidacy` pour une position non biaisée.

```
CRISE:          cid1 -> CONCESSION (3 ajustements, motif=301) | cid2 -> idem | cid3 -> echec de decodage
AUCUN-PROBLEME: cid1 -> CONCESSION (3 ajustements, motif=301) | cid2 -> idem | cid3 -> echec de decodage
```

Les 4 appels décodés avec succès donnent un résultat **exactement
identique** — même stance, même nombre d'ajustements, même motif — dans
les deux pôles. (`cid=3` a échoué au décodage dans les deux pôles avec un
code de motif fuité dans le champ `cid` — 302 puis 308, ce dernier étant
précisément le motif exigé par `stance=3` silence — indice suggestif mais
inutilisable comme preuve, jamais décodé correctement.)

## Le cas de contrôle négatif : `candidacy_considered` (dt=2)

Vérité de référence : `decide_candidacy`, `citizen.ambition_score >=
config.candidacy.ambition_threshold` (seuil livré 0,30) — une fonction
réelle de la situation du citoyen, pas une constante.

Protocole (`check_candidacy_considered_isolation_disposition.py`) : 5
citoyens à `ambition_score` extrêmement bas (0,0069 à 0,0214 — 14x à 43x
sous le seuil), même isolation totale (`size=1`, `think=False`, prompt de
production réel).

```
5/5 correct -- outcome=0 (renonce) pour les 5 citoyens, motif=204 a chaque fois
```

**`candidacy_considered` reste correct sur ces cas extrêmes en isolation
totale.** Différence structurelle avec les deux cas ci-dessus : son `ctx`
est purement autoréférentiel (`ambition_score`, `perceived_support` — à
propos du citoyen seul), sans aucune cible/autre partie nommée dans la
décision elle-même.

## Vérification sur les deux types restants

### `coalition_decision` (dt=9)

Vérité de référence : **partielle seulement** (`plan-decision-quality-
validation.md` §1) — `form_coalition` décide au niveau parti/algorithme,
pas « ce parti rejoindrait-il CE regroupement précis ». Signature de
collapse utilisée, comme pour `representative_response`.

Protocole (`check_coalition_decision_collapse_signature.py`) : pôle
REJOINDRE-ÉVIDENT (plateforme identique à l'initiateur, dépasse
confortablement la majorité, l'initiateur en a besoin) vs pôle
REFUSER-ÉVIDENT (distance maximale sur 20 dimensions, l'initiateur a déjà
la majorité seul), 3 partis répondants différents par pôle.

```
REJOINDRE-EVIDENT: party50/51/52 -> JOIN (motif=501) a chaque fois
REFUSER-EVIDENT:   party50/51/52 -> JOIN (motif=501) a chaque fois
```

**6/6 identiques.** Le collapse s'étend à `coalition_decision` — un
troisième type de décision relationnel/relatif-à-une-cible (le
formateur), bien que de nature plus coopérative/stratégique
qu'adversariale au sens strict.

### `reaction_to_event` (dt=8, branche SCANDAL)

Vérité de référence : **aucune** — vérifié contre le code, pas présumé
malgré la vérification déjà faite pour `plan-decision-quality-
validation.md` §1 : `deterministic_reaction_to_event` ne prend aucun
paramètre `Citizen`, ne peut juger aucune décision individuelle, pour
aucun `event_type`. Signature de collapse utilisée. Branche SCANDAL
choisie spécifiquement : contrairement à ECONOMIC_SHOCK (`target` toujours
nul, événement systémique impersonnel), SCANDAL porte une vraie `target`
(le président visé) — le point de comparaison le plus proche des trois
autres cas au sein de ce type de décision.

Protocole (`check_reaction_to_event_collapse_signature.py`) : pôle
FAIBLE-SALIENCE (`event_salience=0,0`) vs FORTE-SALIENCE
(`event_salience=0,9`), 3 citoyens différents par pôle.

```
FAIBLE-SALIENCE: cid10/20/30 -> salience_delta=0,2000 motif=401 a chaque fois
FORTE-SALIENCE:  cid10/20/30 -> salience_delta=0,2000 motif=401 a chaque fois
```

**6/6 identiques.** Le collapse s'étend à `reaction_to_event` (branche
SCANDAL) — un quatrième type de décision.

## Bilan : 4/4 cadrages relationnels collapsent, 1/1 cadrage autoréférentiel n'collapse pas

| Type de décision | Cadrage | Vérité de référence | Résultat |
|---|---|---|---|
| `pressure_action` | Citoyen vs élu cible (pression) | Réelle, fonctionnelle | **Collapse** (0/70) |
| `representative_response` | Élu répondant à la pression citoyenne | Constante seulement | **Collapse** (4/4 identiques) |
| `coalition_decision` | Parti répondant à un autre parti (formateur) | Partielle | **Collapse** (6/6 identiques) |
| `reaction_to_event` (SCANDAL) | Citoyen face à un événement ciblant un élu | Aucune | **Collapse** (6/6 identiques) |
| `candidacy_considered` | Citoyen seul (ambition/soutien perçu) | Réelle, fonctionnelle | **Pas de collapse** (5/5 correct) |

## Le principe suspecté — hypothèse de conception, pas une loi générale

**Un cadrage de décision construit autour d'une partie répondant à/contre
une autre partie spécifique (cible, autorité, formateur, événement visant
un tiers) semble structurellement à risque de collapse content-blind en
isolation (`size=1`, `think=False`) sur ce modèle (`qwen3:8b`) — tandis
qu'un cadrage purement autoréférentiel ne l'est pas.**

Ce que ce résultat NE dit PAS, pour rester honnête sur sa portée :
- **Pas une preuve causale du mécanisme.** 4 confirmations et 1 seul
  contrôle négatif est un signal fort, pas une preuve formelle — aucune
  variable confondue (longueur de prompt, présence d'un champ « target »
  vs absence, nombre d'options du menu) n'a été isolée expérimentalement
  comme le facteur causal exact. `pressure_action` a déjà montré que
  retirer une phrase de cadrage spécifique ne suffit pas à elle seule
  (`plan-pressure-action-remediation.md` §3.1) — le mécanisme réel reste
  non identifié même pour le cas le mieux caractérisé des quatre.
- **Pas nécessairement propre à `qwen3:8b`** — non testé sur d'autres
  modèles pour CES quatre types (le test cross-modèle de
  `plan-pressure-action-remediation.md` §1 ne portait que sur
  `pressure_action`, et lui-même n'a produit que 2 échantillons
  exploitables sur 4 modèles alternatifs).
- **Pas nécessairement lié au batching** — déjà écarté comme cause pour
  `pressure_action` (`size=1` collapse identiquement) ; les trois autres
  cas sont eux aussi testés exclusivement en isolation, donc rien ici ne
  dit si le cadrage adversarial collapse aussi ou non en configuration
  batchée.

## Portée — tranchée, 2026-08-30 : documenté comme contrainte de conception

**Décision** : le risque d'oublier ce principe dépasse largement le coût
de l'écrire maintenant. Versé dans `polity-simulation-design-v2.md` §3.6.0
« Principes transverses », formulé explicitement comme **obligation de
vérification future**, pas comme loi générale prouvée — le mécanisme
causal reste non identifié (voir ci-dessus), donc la contrainte porte sur
la charge de la preuve pour tout futur type de décision au cadrage
relationnel/relatif-à-une-cible (tester en isolation avant de faire
confiance en production), pas sur une explication déjà tenue pour
acquise.

## Hors scope de ce document

- La remédiation de `pressure_action` elle-même — reste dans
  `plan-pressure-action-remediation.md`, potentiellement informée par ce
  document une fois son fondement causal mieux compris, mais pas
  dépendante de lui.
- L'identification du mécanisme causal exact (présence du champ `target`,
  longueur/complexité du prompt, autre chose) — non testé ici,
  candidat pour un chantier dédié si la portée de ce document est
  confirmée.
- Test sur d'autres modèles pour ces quatre types de décision — non fait,
  hors scope de cette découverte initiale.
