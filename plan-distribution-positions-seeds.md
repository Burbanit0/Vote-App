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

> **Annotation (2026-08-29) — la ligne `uniform` de ce tableau n'est pas le
> critère livré.** Re-mesuré contre le pipeline de production
> (`select_party_nominee`, nominee au plus haut score d'ambition), `uniform`
> donne **70,0 % / 75,0 % / 67,5 %** de victoires du Blanc sur trois blocs de
> 40 graines, pas 27,5 % — cohérent avec les 68 % sur 60 graines de
> `THEORY.md` §10.10. Les 27,5 % correspondent à la variante **centroïde**
> du choix de nominee, que `THEORY.md` documente explicitement comme faisant
> passer le taux « de 70 % à 27,5 % ». La conclusion de Phase 2 tient — et
> l'écart réel en faveur de `factor_structure` est *plus* large que ce
> tableau ne le montre — mais ce point de comparaison est faux tel quel.
> Détail en §3.1.

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

### 2.2 Effet de bord du sweep : boucle Mode A sur `cast_votes` (2026-08-28)

Découvert en aval, pas anticipé par le critère du §2 : le run d'acceptance
LLM v6b sous le nouveau défaut `factor_structure` a **échoué deux fois de
suite**, au tick 0, dans `cast_votes` — `LlmResponseError: generation did not
finish cleanly: finish_reason='length'`, `completion_tokens=13596` (le budget
exact : `compute_max_tokens(1)=1596` + `_VOTE_THINK_TOKEN_ALLOWANCE=12000`).
Consigné ici, et pas comme un chantier séparé : c'est une conséquence
mesurable du changement de distribution documenté au §2.1.

**Diagnostic, au niveau de la réponse brute — pas inféré.** L'endpoint
OpenAI-compat d'Ollama renvoie le `<think>` dans un champ `message.reasoning`
**distinct** de `message.content` ; `_extract_content` ne lit que `content`,
d'où des logs de production vides sur les deux échecs. En lisant `reasoning`
(64 101 caractères capturés sur cid=8) : le modèle atteint la **bonne**
réponse (`[4,1,2,5,3]`) dans les ~1 500 premiers caractères, puis répète
~62 000 caractères d'un paragraphe quasi identique, re-citant textuellement la
REGLE du prompt système, sans jamais trancher ni émettre de JSON.
**Mode A caractérisé** (rumination non convergente), pas Mode B : le budget
avait déjà été relevé 4000 → 8000 → 12000, un cinquième chiffre n'aurait
déplacé que le plafond.

**Facteur causal majeur : l'ambiguïté du prompt** — pas la distribution, et
(mesuré après coup, voir plus bas) **pas la cause unique**. La REGLE de
`build_system_prompt` (« classe les POSITIONS des candidats acceptables du
plus proche au plus eloigne ») se lit aussi bien « classe *tous* les
acceptables » que « classe, c.-à-d. choisis, le plus proche » — c'est
exactement l'alternative sur laquelle le modèle tourne. `factor_structure` ne
crée pas l'ambiguïté ; il **augmente la fréquence** du cas qui la déclenche
(plusieurs candidats acceptables, donc un `ranking` réellement multi-éléments) :

| | `uniform` | `factor_structure` |
|---|---|---|
| candidats acceptables / électeur (moyenne) | 2,62 | 3,54 |
| électeurs à 0 acceptable (vote blanc) | 30,0% | 4,0% |
| électeurs à ≥ 2 acceptables | 62,0% | **88,0%** |
| électeurs à 5 acceptables | 33,0% | 41,0% |

Passer de 62% à 88% suffit à transformer un taux de boucle de ~6-7% par appel
en échec fiable d'un run complet. Deux pistes écartées par mesure directe : le
seul nombre de candidats acceptables ne prédit pas l'échec (cid=18, 5/5
acceptables dont 4 dans un intervalle de 0,0016, répond en 9,9 s) ; et ce
n'est pas déterministe (cid=7 échoue une fois puis réussit 5/5 sur requête
byte-identique — cohérent avec `ollama_structured_output_results.md`).

**Correctif retenu et vérifié avant livraison.** Une consigne stricte est
ajoutée au prompt système, immédiatement après la REGLE : « Le tableau
'ranking' doit OBLIGATOIREMENT contenir CHAQUE candidat juge acceptable […]
Ne te limite JAMAIS au seul candidat le plus proche ». Stress-test sur le vrai
`build_system_prompt` de production (insertion sur ancre, jamais un prompt
dupliqué) — 25 appels live : cid=8 ×10, cid=7 ×5, plus les deux électeurs
tous-acceptables à la marge au seuil la plus faible (cid=89, cid=53) ×5.
**0 boucle, 25/25 rankings exactement égaux à l'ensemble acceptable trié par
distance croissante.** cid=8 passe de 13 596 tokens sans réponse à 58 tokens
en 6,1 s. Suite complète `1731 passed, 41 skipped`, mypy/flake8 propres, tous
les tests de reproductibilité byte-for-byte inchangés.

**Taux réel, mesuré ensuite sur le run complet — le stress-test était trop
étroit.** Les 25 itérations portaient sur 4 électeurs choisis pour être les
cas les plus durs *identifiés* ; l'électorat en compte 100, et le run
d'acceptance qui a suivi (33 ticks, ~1 811 appels LLM, terminé) en donne le
dénominateur honnête :

| | diagnostic | stress-test (4 électeurs) | **run complet (~1 811 appels)** |
|---|---|---|---|
| troncatures | ~6-7% estimé | 0/25 | **11 → 0,6%** |
| absorbées par le rejeu | — | — | **11/11, aucune n'atteint `attempt 2/3`** |
| dont `cast_votes` | — | — | 9/11 |
| dont **`chamber_deliberation`** | — | — | **2/11** |

**Conclusion : ligne 2 de la matrice pré-enregistrée, pas ligne 1.** Des
boucles persistent, donc l'ambiguïté du prompt était un **facteur causal
majeur, pas la cause racine unique**. Deux constats l'établissent
indépendamment : le taux ne tombe pas à zéro (0,6%), et **2 des 11 rejeux
portent sur `chamber_deliberation`** — un type de décision dont le prompt
n'a pas été touché, qui n'a aucune notion de `ranking`, et dont le
constructeur (`build_chamber_system_prompt`) ne partage ni texte, ni
constante, ni helper avec celui du vote. Il subsiste donc un fond de
troncature indépendant du prompt corrigé.

Ce qui a permis au run d'aboutir n'est pas le prompt seul, mais son couplage
avec deux mécanismes déjà livrés : `llm.max_batch_replays=2` et
`_VOTE_CAST_RETRY_TEMPERATURE=0.3` — le rejeu à température non nulle casse
la boucle déterministe, ce pour quoi il avait été introduit.

**Décision** : conformément à la ligne 2, le repli vers `build_ranking` n'est
pas classé sans suite — son périmètre est écrit au §2.3 **avant** tout
développement. Il n'est pas implémenté à ce stade : à 0,6% intégralement
absorbé, le coût (mélanger deux sources de bulletins dans un même run) excède
le bénéfice. Non-déterminisme oblige, c'est une mesure de taux sur un run,
pas une garantie pour un run différent.

**Statut** : correctif livré et validé en conditions réelles — premier run
d'acceptance v6b complet sous `factor_structure` (33/33 ticks, 1 998
événements, `PYTHON_EXIT=0`, 4 h 06). Résultat scientifique de ce run :
**invalide selon son propre critère pré-enregistré**, voir §4.2.

### 2.3 Périmètre du fallback `build_ranking` (écrit, non implémenté)

Rédigé parce que la ligne 2 de la matrice l'exige, avant tout code, et pour
qu'une occurrence future n'ait pas à re-décider dans l'urgence. **Rien de ce
qui suit n'est implémenté.**

**Déclenchement.** Uniquement sur épuisement des rejeux, jamais en première
intention : `_complete_and_decode_with_replay` lève `LlmResponseError` après
`llm.max_batch_replays + 1` tentatives — c'est le seul point d'entrée. Le
run complet montre que ce seuil n'a jamais été atteint (aucune ligne
`attempt 2/3`), donc le fallback est un filet, pas un chemin courant. Nouvelle
clé de config dédiée, par défaut **désactivée** : le comportement livré reste
« un batch épuisé fait échouer le run », et l'activer est un choix
expérimental explicite, tracé dans le `config.json` archivé du run — même
registre que `max_batch_replays` lui-même.

**Portée du remplacement.** Le **votant** dont le batch a échoué, et lui
seul — jamais le tick, jamais le run. À `_VOTE_CAST_MAX_CHUNK_SIZE=1`, un
batch échoué est exactement un électeur, donc la granularité est déjà la
bonne sans découpage supplémentaire. `build_ranking(voter, candidates)`
produit le bulletin déterministe que `cast_votes` a remplacé en v2
increment 1 — même signature, même contrat, aucun code à écrire côté règle.
**Hors périmètre** : les six autres types de décision. En particulier
`chamber_deliberation`, pourtant concerné par 2/11 des rejeux, **n'a pas de
baseline déterministe à laquelle se replier** (v6b Lot 3 : « le statu quo
*est* le fallback », `chamber_position` reste figée sur `issue_positions`) —
un fallback y signifierait « ne rien décider ce tick », ce qui n'est pas la
même chose et demande sa propre décision.

**Marqueur journal.** Non négociable : un run mixte doit rester analysable.
L'événement `vote_cast` gagne une clé `"source"` valant `"llm"` ou
`"fallback"`, écrite **inconditionnellement** dès que la clé de config est
activée, jamais seulement sur la branche de repli — sans quoi l'absence de
clé serait ambiguë entre « LLM » et « ancien journal ». Conséquence à
accepter d'emblée : tout run avec fallback actif est **exclu** des
comparaisons §11.4 LLM-vs-déterministe, puisqu'il n'est ni l'un ni l'autre ;
`indexer.py` doit exposer le compte par `source` pour que cette exclusion
soit vérifiable depuis le journal, pas seulement depuis les logs.

**Ce qui rouvrirait la question** : un rejeu qui échoue à son tour
(`attempt 2/3` dans un `replays.log`), ou un taux de troncature qui remonte
au-delà de ~2% sur un run complet. Aucun des deux n'est observé à ce jour.

### 3.1 Résultats Phase 3 (2026-08-25)

Périmètre discuté et validé avant implémentation (options recommandées
retenues sur les deux points ouverts : extension du bullet §10.10 existant
plutôt qu'une nouvelle sous-section, migration silencieuse des scripts
d'acceptance sans les modifier).

- `polity_config.yaml` : `citizens.position_dist` bascule de `uniform` à
  `factor_structure` comme défaut livré, avec justification écrite en
  commentaire (chiffres du sweep §2.1, référence à ce document).
- **Découverte pendant l'implémentation, pas anticipée dans le cadrage** :
  plusieurs tests (`test_polity_citizen.py`, `test_polity_run_simulation.py`)
  dépendaient implicitement de `uniform` via `load_config()` — soit pour
  reproduire la séquence de tirage RNG d'origine (v4 Lot 2), soit parce que
  des seuils de déclenchement (mobilisation, pétition) avaient été calibrés
  empiriquement contre la population `uniform`/`seed=42` spécifique
  (`scripts/awakening_calibration_results.md`,
  `scripts/petition_calibration_results.md`). Corrigé en épinglant
  `position_dist: "uniform"` explicitement dans ces tests précis (pas dans
  toute la suite) — préserve leur intention réelle (tester le mécanisme,
  pas "quelle que soit la distribution livrée") sans dépendre du défaut
  livré. Suite complète : `1730 passed, 41 skipped`, aucune régression ;
  mypy/flake8 propres.
- `THEORY.md` §10.10 : le bullet seed=42 existant est étendu — la phrase
  « décision de corriger... reste délibérément ouverte » est remplacée par
  la décision réellement prise (`factor_structure`, argumentation, chiffres
  du sweep, non-rejeu des runs passés).
- `traceability.md` (autre worktree, commit séparé) : la ligne Polity est
  mise à jour dans le même sens.
- Aucun script d'acceptance modifié — chacun hérite du nouveau défaut via
  `load_config()` au prochain run.

**Statut** : Phase 3 terminée.

### 4.1 Vérification bon marché avant décision Phase 4 (2026-08-25)

Avant de décider d'un re-baseline sélectif, quatre sondes déterministes
(secondes chacune, scripts scratch, aucun run committé modifié, aucun
calcul LLM) rejouent sous `factor_structure` les configurations exactes de
résultats déjà publiés :

| arm | `uniform` (publié) | `factor_structure` (sonde) |
|---|---|---|
| v4 `both`, 8 ans | L=0,345, 2 rappels | L=0,745, **2 rappels** |
| v4 `mobilization_only`, 30 ans | L=0,061, 8 rappels | L=0,216, **7 rappels** |
| v4 `electoral_only`, 8 ans | L=0,510, 0 rappel | L=0,770, **0 rappel** |
| v6b `both`, plancher livré | occupation ~6-9%, 2 rappels | occupation 63,6%, **2 rappels** |

L'acceptabilité de base (`m`) monte substantiellement partout, mais les
comptes de rappel et la propriété de contrôle d'`electoral_only` restent
quasi inchangés — signal suggestif (pas concluant, ces sondes ne testent
que la ligne de base déterministe §11.4, pas l'arbitrage LLM) que les
dynamiques de crise sont structurelles, pas un artefact de la distribution.

**Décision (recommandation retenue)** : pas de re-run LLM complet à ce
stade — le signal déterministe ne justifie pas plusieurs heures de calcul
par run pour confirmer une conclusion déjà probable. Documenté dans
`THEORY.md` §10.10 et `traceability.md`.

**Statut** : Phase 4 **non engagée en re-run** — le constat ci-dessus en
réduit la priorité sans la clore. Décision distincte et toujours ouverte
si de nouvelles raisons de douter d'un résultat publié apparaissent.

### 4.2 Le bras LLM produit une crise plus sévère que la sonde déterministe ne le prédit (2026-08-28)

Résultat à part entière, pas une note de bas de page du run de §2.2 : c'est la
première mesure **like-for-like** LLM-sous-`uniform` contre
LLM-sous-`factor_structure`, et elle contredit quantitativement la sonde
déterministe qui avait servi à décider de la Phase 4.

Sur la configuration v6b `both`, 8 ans, plancher livré, seed 42 :

| mesure | occupation de la présidence | rappels |
|---|---|---|
| LLM, `uniform` (publié, v6b Lot 4 run 1) | ~6-9% | 2 |
| **sonde déterministe, `factor_structure` (§4.1, prédiction)** | **63,6%** | 2 |
| **bras LLM, `factor_structure` (mesuré ici)** | **33,3%** | 2 |

**Lecture.** `factor_structure` améliore réellement l'occupation sous LLM
(~6-9% → 33,3%, soit environ ×4), mais **la sonde déterministe la
surestimait d'un facteur ~2**. Sur la quantité *discrète* — le compte de
rappels — la sonde était juste (2 dans les trois cas). Sur la quantité
*continue* — combien de temps la présidence tient — elle ne l'était pas.

**Portée pour la décision de §4.1.** Cette décision (« pas de re-run LLM
complet, le signal déterministe ne le justifie pas ») n'est pas invalidée :
elle reposait explicitement sur les comptes de rappel et sur la propriété de
contrôle d'`electoral_only`, deux choses que la sonde prédit correctement.
Mais sa réserve écrite — « ces sondes ne testent que la ligne de base
déterministe §11.4, pas l'arbitrage LLM » — cesse d'être une précaution de
principe : elle est désormais **mesurée**, avec un facteur ~2 sur une
quantité continue. Toute sonde déterministe future doit être lue comme une
**borne optimiste** sur les dynamiques de crise, pas comme une prédiction.

**Pourquoi c'est cohérent avec le mécanisme.** `deterministic_pressure_action`
ne mobilise qu'au-delà du `blank_threshold` propre au citoyen — une règle
rigide qui plafonne mécaniquement la pression. Le LLM arbitre librement dans
le menu : le mix de leviers réalisé sur ce run
(`{0: 0,467, 1: 0,210, 2: 0,029, 3: 0,295}`) montre 29,5% de mobilisations et
21% de signatures, au-dessus de ce que la règle déterministe produit à
population identique. Le risque était nommé dès v4 Lot 7 (« une cohorte LLM
qui mobilise plus librement peut faire tomber `L` plus vite que n'importe quel
bras déterministe ») ; c'est sa première quantification.

**Conséquence directe** : le run de §2.2 est **scientifiquement invalide selon
son propre critère pré-enregistré** — `office_occupancy=0,333` contre un seuil
de 0,70, avertissement émis par le script lui-même. `mandate_deviation` reste
plat à 0 avec une couverture de 0,0 (`representative_response` ne se déclenche
que 11 fois sur 33 ticks faute de titulaire), donc la comparaison élu contre
tiré-au-sort qui motive v6b n'est pas réalisable sur ce run. Le confound de
vacance du run 1 de v6b Lot 4 est atténué par `factor_structure`, pas levé.

**Nuance apportée par le run `electoral_only` (§4.3), qui restreint la portée
de « borne optimiste ».** Sur ce run-là la sonde déterministe s'est révélée
**juste** : elle annonçait 0 rappel et `L≈0,77`, le bras LLM donne 0 rappel et
`L` à 0,720 puis 0,850. « Toute sonde déterministe surestime » est donc faux
tel quel. Ce qui le remplace est une **hypothèse de travail consolidée par ce
run, pas une règle établie** : la sonde serait fiable sur les quantités
mécaniquement déterminées (le point fixe `L ≡ m`, le compte de rappels sous un
menu où `écart(t) ≡ 0`) et optimiste sur celles qui dépendent de l'arbitrage
citoyen (l'occupation sous un menu où des leviers de pression existent). Elle
est cohérente avec le mécanisme décrit ci-dessus — sous `electoral_only` il n'y
a rien à arbitrer, donc rien qui puisse diverger de la règle rigide — mais elle
ne repose que sur **un seul cas favorable**, et sur un cas où sa propre clause
« rien à arbitrer » la rend presque tautologique. Le test qui la mettrait
réellement à l'épreuve n'a pas été fait : une sonde contre un bras LLM sous un
menu où des leviers existent *et* où la sonde prédirait une quantité continue
correctement. À ne pas citer ailleurs dans le projet comme acquise avant ce
test.

**Suite — résolue le 2026-08-29** : reprise sous `--menu electoral_only`, la
seule configuration qui lève le confound sans désactiver l'accountability comme
le faisait `recall_floor=0.0`. Run exécuté, critère franchi, résultats en §4.3.

### 4.3 Comparaison élu / tiré-au-sort enfin valide, sur n=2 présidents (2026-08-29)

**n=2.** Le run `electoral_only` franchit son propre critère pré-enregistré
(`office_occupancy = 1,0` contre un seuil de 0,70, là où le run `both` de §2.2
échouait à 0,333) et rend donc la comparaison v6b calculable pour la première
fois — mais le côté élu de cette comparaison repose sur **deux présidents
seulement, au comportement opposé, et qui ne partaient pas de positions
comparables**. Cette phrase vient avant les chiffres délibérément : elle
conditionne tout ce qui suit.

Configuration : v6b, 8 ans, seed 42, `factor_structure`, `--menu electoral_only`,
plancher livré `recall_floor=0.2` non touché. 15 037 s (4 h 10), 2 178
événements, sortie 0. Doc de résultats :
`fast_api_voter/scripts/acceptance_v6b_fs_electoral_only_results.md`.

| | moyenne | max | observations |
|---|---|---|---|
| Élu — `mandate_deviation_unified` | 0,0479 | 0,1702 (**écrêté**) | 33 ticks |
| Chambre — `chamber_deviation` | 0,000000 | 0,000000 | 990 délibérations |

La chambre n'a pas bougé : 989 délibérations sur 990 en `SINCERE_POSITION`, et
l'unique `DELIBERATIVE_SHIFT` est revenu avec un `shifts` vide — une étiquette
sans mouvement derrière (le validateur de cohérence a été retiré en v6b Lot 3
pour cause de fiabilité, le motif est donc déclaré, pas vérifié). Réponse à
§6bis.3 sur ce run : **sincère, pas erratique**.

**Ce que n=2 interdit d'affirmer.** Le président 42 (ticks 0-15) concède sur 13
ticks sur 16 ; le président 2 (ticks 16-31) répond `silence` 16 fois sur 16 et
ne bouge jamais. Une vérification ponctuelle contre la population régénérée à
seed 42 explique l'essentiel de cet écart structurellement, pas
comportementalement :

| | distance pondérée de la promesse au centre de masse | dispersion (σ) | citoyens au-delà de leur propre `blank_threshold` |
|---|---|---|---|
| Président 42 | 0,1495 | 0,152 | **29 / 99** |
| Président 2 | **0,0963** | **0,071** | **15 / 99** |
| référence population | 0,1939 (moyenne) | 0,193 (moyenne) | — |

Le président 2 est un quasi-centriste — 7ᵉ plus proche du centre de masse sur
100 sur sa position sincère, plateforme comprise entre 0,327 et 0,583 sur les
20 dimensions (son virage de campagne ne vaut que 0,0123, contre 0,0702 pour le
président 42, donc promesse et position sincère disent ici la même chose) — face à
environ moitié moins de mécontents. Sa dérive nulle est donc largement un cas
de « rien à concéder », pas une résistance démontrée à la pression. Lecture
honnête et étroite : **la dérive est atteignable côté élu et n'a pas été
atteinte une seule fois en 990 occasions côté chambre** — pas que l'élection
cause la dérive et le tirage au sort la prévienne. Cette seconde affirmation
demanderait plus d'une graine et plus de deux présidents.

**Le président a concédé 13 fois à une population qui n'a jamais agi.** Résultat
le plus inattendu du run, et il mérite d'être énoncé seul : `inaction_rate` vaut
**exactement 1,0 à chaque tick de 0 à 15** — sur tout le premier mandat, aucun
citoyen de la cohorte consultée n'a choisi autre chose que `NOTHING` — et
pendant ces mêmes seize ticks le président 42 a rendu `stance = concession`
treize fois. Le mix de leviers du run entier est `{0: 383, 4: 16}` : 383
non-actions explicites, 16 renvois à l'élection, zéro mobilisation, zéro
pétition. La dérive mesurée ici n'est donc **pas une réponse à la pression : il
n'y avait aucune pression à laquelle répondre**. §7bis.6 affirme qu'un
représentant qui trahit son mandat devant une population passive ne perd pas de
légitimité ; ce run montre l'image miroir, que la clause ne couvre pas — un
représentant qui *concède* à une population passive, sans y être poussé, avec
`L` plate à `m`. Modèle anticipant un électorat futur, ou artefact d'un prompt
qui réclame une réaction à chaque tick : ce run ne tranche pas.

**`clamped_at_bound` a fonctionné en conditions réelles, pour la première
fois.** L'événement ajouté en `397d0ac`, qui referme la « KNOWN OBSERVABILITY
GAP » documentée dans la docstring d'`apply_shifts`, s'est déclenché 8 fois :
4 sur `campaign_positioning` (ticks 0 et 32) et **4 sur `representative_response`
du président 42, aux ticks 8, 9, 13 et 15, dimensions 0 et 1**. Or la série
unifiée stagne à exactement 0,164 sur les ticks 10 à 13 avant de monter à 0,170.
Avant cet événement, ce plateau était indiscernable d'un « le modèle a cessé de
concéder », et la seule façon de trancher était la reconstruction non écrêtée
jetable et non commitée de l'investigation précédente (×2,8 à ×3,6 au-dessus du
chiffre écrêté, `THEORY.md` §10.9/§10.10). Ici les quatre écrêtages tombent
dans le plateau et le diagnostic se lit **depuis le seul journal**. Conséquence
à porter : le max de 0,1702 est un chiffre **écrêté, sous-estimé**.

**Troisième confirmation de la cécité du scope `top_k_priorities`, cette fois en
bande.** `mandate_deviation` (scope livré) affiche 0,0000 sur les 33 ticks
pendant que la version unifiée atteint 0,1702 sur les mêmes événements ;
`mandate_deviation_coverage = 0,0`, aucun `mandate_deviation_recorded` n'ayant
pu franchir un seuil de 0,1 sur une quantité qui n'a jamais quitté zéro. C'est
le premier run où le chiffre corrigé est **journalisé en bande** par du code de
production, et non reconstruit après coup : le trou de provenance visé par le
lot de câblage est refermé pour ce run.

**Fiabilité** : 11 rejeux, tous absorbés en `attempt 1/3`, aucun épuisement —
**8 `vote_cast`, 3 `chamber_deliberation`**. Rapporté aux ≥1 290 appels des deux
seuls types tournant en chunks de 1 (300 `vote_cast`, 990
`chamber_deliberation`), plus les autres types, cela reste sous le pour cent,
même ordre que les 0,6% du run `both` de §2.2. La composition compte plus que
le taux : trois rejeux sur `chamber_deliberation`, dont le prompt système n'a
pas été touché par le correctif de `cast_votes` et qui n'a aucune notion de
`ranking`. Le plancher résiduel se reproduit sur un troisième run indépendant,
ce qui maintient la ligne 2 de la matrice de §2.2 et garde le périmètre écrit
du fallback (§2.3) justifié plutôt qu'académique.

## 3. `ambition_threshold=0.0` — sous-décision séparée, à ne pas mélanger

Ne pas toucher ce paramètre dans ce chantier sauf preuve qu'il reste
nécessaire une fois la distribution de position corrigée. Hypothèse de
travail : si le vrai problème est l'absence de centre de masse (§1),
corriger la distribution devrait suffire — `ambition_threshold=0.0`
peut rester un choix de conception distinct et légitime (garantir un
pool de candidats suffisant), pas un pansement sur le vrai problème.
À vérifier empiriquement une fois §2 tranché, pas supposé.

### 3.1 Vérification (2026-08-29) — l'hypothèse est fausse, et dans un sens plus fort qu'attendu

Sonde déterministe, protocole du §2 (40 graines, vrai pipeline de production
`generate_population` → `initialize_parties` → `assign_party_affiliation` →
`select_party_nominee` → `declare_candidacy` → `build_ranking` →
`get_presidential_winner`), quatre cellules mesurées dans la même exécution
pour rester comparables entre elles :

| `position_dist` | `ambition_threshold` | citoyens éligibles (moy.) | nominees (moy.) | aucun candidat | victoire du Blanc | vainqueur réel |
|---|---|---|---|---|---|---|
| `uniform` | 0,0 | 100 | 5,00 | 0/40 | **28/40 (70,0 %)** | 12/40 |
| `uniform` | **0,7 (livré)** | **0,03** | **0,03** | **39/40 (97,5 %)** | 1/40 | 0/40 |
| `factor_structure` | 0,0 | 100 | 5,00 | 0/40 | **0/40 (0,0 %)** | 40/40 |
| `factor_structure` | **0,7 (livré)** | **0,03** | **0,03** | **39/40 (97,5 %)** | 0/40 | 1/40 |

**Résultat : `ambition_threshold=0.0` n'est pas un choix de conception
distinct, c'est une condition d'existence de l'élection.** Au seuil livré de
0,7, `ambition_dist: beta(2,8)` ne place pratiquement aucune masse au-dessus
du seuil — **0,03 citoyen éligible en moyenne sur 100** — donc 39 graines sur
40 ne produisent **aucun candidat** et aucune élection n'est même tenue. Ce
n'est pas un effet de la distribution des positions : le constat est
identique sous `uniform` et sous `factor_structure`, parce que le blocage
tient à un couple (`ambition_dist`, `ambition_threshold`) totalement
orthogonal aux positions.

L'hypothèse de §3 — « corriger la distribution devrait suffire » — est donc
fausse, mais pas comme anticipé : ce n'est pas que `ambition_threshold=0.0`
masquait encore un problème de position résiduel, c'est que **sans lui il n'y
a pas de démocratie à observer du tout**. Le commentaire « guarantees a real
elected president » que tout script d'acceptance porte n'est pas une
commodité : il est structurellement obligatoire à la configuration livrée.

**Ce que ça ouvre, et qui n'est pas tranché ici** : la configuration livrée
(`ambition_dist: beta(2,8)` + `ambition_threshold: 0.7`) est
*intrinsèquement* incapable de produire une élection — et
`rupture_path_enabled: false` fait de `decide_candidacy` le seul chemin de
candidature, donc il n'y a pas de voie de secours. Aucun run d'acceptance ne
l'a jamais exercée. Trancher (calibrer `ambition_dist`, baisser le seuil, ou
les deux) dépasse le périmètre de ce chantier (§6) : **c'est une découverte
nouvelle, sortie séparément en
`docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md`**, avec sa question
ouverte posée et non résolue. Ce chantier-ci est clos dans son périmètre
initial ; celui-là commence.

**Écart trouvé au passage dans le tableau du §2.1, à corriger séparément.**
La ligne `uniform` (défaut livré) du sweep de Phase 2 annonce **11/40
(27,5 %)** de victoires du Blanc. Cette valeur n'est pas reproductible contre
le pipeline livré : trois blocs de 40 graines indépendants (1-40, 41-80,
101-140) donnent **70,0 %, 75,0 % et 67,5 %**, cohérents entre eux et
cohérents avec les 68 % sur 60 graines déjà publiés en `THEORY.md` §10.10.
`THEORY.md` donne l'explication directement : « remplacer le critère livré
(le membre du parti au score d'ambition le plus élevé) par le membre le plus
proche du centroïde k-means du parti fait passer le taux de victoire du Blanc
de **70 % à 27,5 %** ». Le 27,5 % du tableau §2.1 est donc la variante
**centroïde**, pas le critère livré — la ligne de référence `uniform` sous-
estime le problème d'un facteur ~2,5. La décision de Phase 2 n'est pas
affectée (`factor_structure` gagne dans les deux lectures, et par une marge
*plus* large que documentée), mais le tableau donne un point de comparaison
faux et devrait être annoté.

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
