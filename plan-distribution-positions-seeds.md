# Plan — Distribution des positions citoyennes et représentativité des runs

> Document de scoping, à discuter et amender avant toute implémentation.
> Objectif : résoudre à la racine le problème découvert lors de
> l'investigation `mobilization_only` (27,5% des seeds font gagner le
> vote blanc sous `position_dist: uniform`), avec une base théorique
> défendable, sans se contenter de choisir la distribution qui fait
> disparaître le symptôme le plus vite.

---

## 0. Rappel du problème (pour mémoire, pas à rediscuter)

- `citizens.position_dist: uniform` scatter 100 citoyens sur un espace à
  20 dimensions sans centre de masse naturel.
- Sous cette distribution, l'acceptabilité moyenne du meilleur candidat
  plafonne à ~54,9% — trop proche de la barre des 50% pour qu'une
  majorité simple soit une propriété robuste du système plutôt qu'un pari.
- Toute concentration testée (Gaussienne simple std=0.30 jusqu'à un
  mélange à 2-3 modes std=0.10) fait chuter le taux d'échec de 27,5% à
  quasi zéro.
- `gaussian_mixture` existe déjà comme valeur de config documentée mais
  `generate_population` la rejette (`NotImplementedError`).
- Tous les runs d'acceptance publiés à ce jour (v4 à v6b) ont tourné sous
  `uniform`, avec `seed=42` exclusivement, jamais validée comme
  représentative.

## 1. Cadrage théorique — quelle distribution est défendable, pas juste pratique

**Principe directeur** : ne pas choisir la distribution qui fait
disparaître le problème le plus efficacement (ce serait optimiser pour
un résultat, pas pour un modèle fidèle). Choisir celle qui a la
meilleure justification dans la littérature déjà mobilisée par le
projet, puis vérifier qu'elle résout aussi le problème empirique — dans
cet ordre.

### 1.1 Ce que dit la littérature déjà citée

- **Downs (1957), compétition spatiale** : suppose classiquement une
  distribution unimodale (souvent normale) de l'électorat sur l'axe
  idéologique — c'est l'hypothèse qui permet la convergence des partis
  vers le centre (théorème de l'électeur médian). Justifie
  théoriquement une **Gaussienne simple**, mais sur un espace à une
  dimension — notre espace en a 20.
- **Iyengar et al. (2019), polarisation affective**, déjà cité en §5 du
  plan de conception : documente une polarisation croissante de
  l'électorat réel, ce qui argumenterait plutôt pour un **mélange
  bimodal/multimodal** que pour un consensus unimodal artificiel.
- **Kollman-Miller-Page**, déjà cité comme grille de lecture a
  posteriori (§3.3) : les partis explorent l'espace par recherche
  locale ; un électorat déjà concentré en un point unique réduirait
  artificiellement l'intérêt de cette dynamique exploratoire.

**Tension à trancher, pas à esquiver** : un Gaussien simple est plus
proche de l'hypothèse Downsienne classique (aucune polarisation
préexistante, les partis convergent), un mélange à 2-3 modes est plus
proche de la réalité empirique documentée (Iyengar) mais avec un risque
de configuration arbitraire (combien de modes, quels poids, quelle
séparation).

### 1.2 Une option non encore testée à considérer sérieusement

Le espace à 20 dimensions indépendantes (Dirichlet sur les priorités +
position uniforme par dimension) ne reflète probablement pas comment de
vraies opinions politiques se structurent : dans la réalité, les 20
enjeux ne varient pas indépendamment — il existe une **structure
factorielle sous-jacente** (ex. un axe économique et un axe sociétal,
comme déjà envisagé en §14.2 du plan de conception pour la
visualisation). Une population générée avec des positions
**corrélées** entre dimensions (via une structure de covariance à bas
rang, projetée dans les 20 dimensions) produirait un centre de masse
émergent sans imposer artificiellement un ou plusieurs pics — plus
proche d'un phénomène de *bundling* idéologique réel que d'un mélange de
gaussiennes choisi à la main.

**Recommandation de ce document** : tester cette option (position
générée via 2-3 facteurs latents + bruit, projetés sur 20 dimensions)
en parallèle du mélange gaussien simple, avant de trancher — elle a une
justification structurelle plus forte (le §14.2 du plan l'anticipe déjà
comme grille de lecture) que le choix du nombre de modes d'un mélange.

### 1.3 Décision Phase 1 (2026-08-25)

**Retenu : structure factorielle à bas rang, avec facteurs latents tirés
d'une distribution unimodale (pas un mélange)** — synthèse des options
1.1/1.2, pas un des 4 candidats du §2 pris tel quel.

**Argumentation, débattue avant tout chiffre de sweep** :
- §14.2 du plan de conception dit explicitement que la vue méso existe
  pour *observer* si les partis convergent (Downs) ou se figent en
  équilibres polarisés (Kollman-Miller-Page) — et §3.6.1 tranche, sur un
  point voisin, à ne donner *aucun* critère théorique prescriptif au LLM,
  précisément pour observer des stratégies émergentes. Un mélange
  gaussien (option 3) présuppose la réponse à cette question dans la
  population de départ : un run qui montre des équilibres polarisés ne
  démontrerait rien, ce serait mécanique.
- Une Gaussienne simple (option 2) est neutre sur convergence/polarisation
  mais ne répond pas à l'objection déjà dans le plan (§1.2) : les 20
  dimensions restent indépendantes, alors que les vraies opinions
  politiques ont une structure de covariance (bundling idéologique).
- La structure factorielle à bas rang répond aux deux : facteurs tirés
  d'une distribution unimodale ⇒ neutre sur convergence/polarisation,
  préserve l'observabilité émergente ; loadings partagés entre les 20
  dimensions ⇒ corrèle les enjeux de façon réaliste, sans indépendance
  artificielle.
- `n_factors=2`, choix délibéré et non arbitraire : correspond exactement
  aux « axe économique et axe sociétal » déjà nommés en §14.2 du plan de
  conception, pas un nombre de facteurs inventé pour ce chantier.

**Ce que ça implique pour la Phase 2** : implémenter uniquement cette
option comme nouvelle valeur de `position_dist` (pas les 4 candidats du
§2 comme options de config permanentes — les options 2/3 servent de
points de comparaison empirique dans le sweep, pas de valeurs à
shipper). Nom retenu : `factor_structure` — distinct de `gaussian_mixture`
(déjà réservé, jamais implémenté, et sémantiquement différent : un
mélange, pas une structure factorielle unimodale).

## 2. Critère de décision, pré-enregistré avant tout test empirique

Comme pour toutes les investigations GPU de ces deux derniers jours :
**écrire le critère avant de voir les résultats**, pas après.

Candidats à comparer, sur le même protocole de sweep déjà construit
(40 seeds, mesure du taux de victoire du vote blanc + acceptabilité
moyenne du meilleur candidat) :
1. `uniform` (baseline actuelle, pour référence).
2. Gaussienne simple, std à calibrer (viser une acceptabilité moyenne
   dans une plage cible, pas un std choisi au hasard).
3. Mélange à 2-3 modes (polarisation).
4. Structure factorielle à bas rang + bruit (option 1.2).

**Critère de sélection, à fixer avant de lancer les 4 sweeps** :
- Taux de victoire du vote blanc < 5% sur 40 seeds (élimine le
  problème structurel).
- Variance de l'acceptabilité du meilleur candidat entre seeds — une
  distribution qui élimine le problème en écrasant toute variabilité
  (ex. std trop petit) serait suspecte pour une autre raison (plus
  aucune diversité d'opinion, un consensus artificiel aussi peu
  réaliste que le problème initial).
- Défendabilité théorique (score qualitatif, pas juste empirique) —
  qui doit être débattue **avant** de voir les chiffres du sweep, pour
  ne pas se laisser influencer par "celle qui marche le mieux".

### 2.1 Résultats Phase 2 (2026-08-25)

Implémenté : `citizens.position_dist: factor_structure` dans
`generate_population` (`api/domain/polity/citizen.py`) — nouvelle branche,
derrière un flag, `uniform` reste le défaut livré et byte-pour-byte
inchangé (`1730 passed, 41 skipped`, aucune régression). `n_factors=2`,
`factor_std=1.0`, `loading_std=1.0`, `noise_std=0.3` — calibrés (pas
devinés) contre le critère du §2 avant de figer les constantes en
production. 17 tests dédiés (déterminisme, invariants de population,
non-effondrement de la corrélation/variance) dans
`api/tests/test_polity_citizen.py`.

Sweep comparatif à 40 seeds, sur le même protocole que l'investigation
initiale, `uniform` et `factor_structure` passés à travers le vrai
`generate_population` de production (pas une ré-implémentation) :

| candidat | victoires du Blanc | acceptabilité moyenne | stdev (seed à seed) | acceptabilité min | corrélation moyenne inter-dimensions |
|---|---|---|---|---|---|
| `uniform` (défaut livré) | 11/40 (27,5%) | 0,549 | 0,045 | 0,450 | 0,080 |
| **`factor_structure` (retenu Phase 1)** | **0/40 (0,0%)** | **0,712** | **0,054** | **0,590** | **0,539** |
| gaussienne simple (référence, non implémentée) | 0/40 (0,0%) | 0,801 | 0,052 | 0,640 | 0,081 |
| mélange à 3 modes (référence, non implémenté) | 0/40 (0,0%) | 0,832 | 0,044 | 0,700 | 0,347 |

**Lecture par rapport au critère du §2, fixé avant ce tableau** :
- Taux de victoire du Blanc < 5% : **validé** (0,0%), avec une marge
  confortable (`accept_min=0,590`, aucune seed proche de la frontière à
  50%, contre `accept_min=0,450` sous `uniform` — déjà sous la barre pour
  plusieurs seeds).
- Variance non écrasée : `stdev=0,054` reste du même ordre de grandeur que
  celle observée sous `uniform` (0,045) — pas de consensus artificiel,
  la diversité d'opinion seed-à-seed est préservée.
- La gaussienne simple (référence) confirme empiriquement l'objection déjà
  posée en §1.2 : sa corrélation inter-dimensions (0,081) est du même
  ordre que le bruit de `uniform` (0,080) — un Gaussien appliqué
  indépendamment par dimension ne corrèle rien, contrairement à
  `factor_structure` (0,539), qui répond spécifiquement à cette critique.
- Le mélange à 3 modes (référence) atteint aussi une bonne acceptabilité,
  mais reste, par construction, le candidat qui présuppose le plus la
  polarisation — cohérent avec la réserve du §1.3 sur l'observabilité
  émergente.

**Statut** : Phase 2 terminée, critère du §2 satisfait par `factor_structure`.
Phase 3 (nouveau défaut livré, migration `THEORY.md`/`traceability.md`) et
Phase 4 (re-baseline sélectif) **non commencées** — présentées ici pour
validation avant de continuer, comme prévu par ce document.

## 3. `ambition_threshold=0.0` — sous-décision séparée, à ne pas mélanger

Ne pas toucher ce paramètre dans ce chantier sauf preuve qu'il reste
nécessaire une fois la distribution de position corrigée. Hypothèse de
travail : si le vrai problème est l'absence de centre de masse (§1),
corriger la distribution devrait suffire — `ambition_threshold=0.0`
peut rester un choix de conception distinct et légitime (garantir un
pool de candidats suffisant), pas un pansement sur le vrai problème.
À vérifier empiriquement une fois §2 tranché, pas supposé.

## 4. Politique de validation de seed — corriger le processus, pas seulement la config

Indépendamment de la distribution retenue, formaliser ce qui a été fait
ad hoc cette fois :

1. **Un sweep de seeds obligatoire avant tout nouveau palier de
   roadmap** (pas juste quand un problème est suspecté) — intègre-le
   comme étape de pré-vol dans le harnais de test déjà construit
   (`llm_test_harness`), au même titre que la capture d'environnement
   GPU.
2. **Documenter la seed retenue avec sa justification** dans chaque
   script d'acceptance — pas un choix silencieux par défaut.
3. **Marquer tous les runs d'acceptance déjà publiés** (v4 à v6b) comme
   `seed_representativeness: unvalidated` dans leurs métadonnées ou un
   fichier annexe — cohérent avec le marqueur `INVALID_PRE_GPU_FIXES.md`
   déjà utilisé pour un problème de nature différente mais de même
   esprit (ne pas réécrire l'historique, juste le qualifier honnêtement).

## 5. Plan d'exécution, phasé avec portes de validation

**Phase 1 — Décision théorique** (avant tout code)
- Trancher entre Gaussienne simple, mélange, ou structure factorielle
  (§1), avec argumentation écrite, débattue avant de lancer le sweep
  empirique de la §2.

**Phase 2 — Sweep comparatif** (empirique, critère déjà fixé)
- Implémenter les options retenues en Phase 1 dans `generate_population`
  (probablement derrière un flag, pas en remplaçant `uniform` tout de
  suite — rétrocompatibilité avec les runs déjà publiés).
- Lancer le sweep de 40 seeds sur chaque option, comparer au critère
  pré-enregistré.

**Phase 3 — Décision finale et migration**
- Choisir la distribution à adopter comme nouveau défaut pour les
  **futurs** runs — ne pas régénérer/invalider silencieusement les runs
  passés.
- Mettre à jour `polity_config.yaml` (nouvelle valeur par défaut,
  documentée avec justification), `THEORY.md` (nouvelle section
  méthodologique sur la génération de population), `traceability.md`.

**Phase 4 — Re-baseline sélectif**
- Décider si un ou plusieurs résultats scientifiques déjà publiés
  (§10.7-§10.10) méritent d'être rejoués sous la nouvelle distribution
  pour vérifier leur robustesse — pas un re-run systématique de tout
  l'historique, un choix ciblé sur les résultats dont la conclusion
  pourrait dépendre de la représentativité de la population.

## 6. Ce que ce plan ne couvre pas (hors périmètre, explicitement)

- Le mécanisme électoral lui-même (`two_round`, `build_ranking`) n'est
  pas remis en cause — le problème vient de la distribution amont, pas
  de la règle d'agrégation.
- Aucune implémentation ne démarre avant validation de ce document.

## Sortie attendue de la prochaine session

1. Débat et décision sur la Phase 1, écrite, avant tout code.
2. Si validé : implémentation Phase 2 avec tests dédiés (déterminisme de
   la génération à seed fixe, conservation des propriétés statistiques
   attendues).
3. Présentation des résultats du sweep Phase 2 avant de passer en Phase 3.
