# Validation de la qualité des décisions LLM — le vrai Lot 1 de v8

## Contexte

`reasoning_budget_and_decision_quality_findings.md` (2026-08-24, jamais
repris depuis — un seul commit, aucun suivi) a établi une découverte
restée sans suite : **seul `vote_cast` a jamais eu une vérité terrain
calculable pour juger la qualité d'une décision LLM** — pas juste sa
validité structurelle (JSON bien formé, motif valide), sa **justesse**.
Le jour où cette vérité terrain a été vérifiée (`think=False`,
`weighted_distance` réelle), le résultat a été un effondrement silencieux
— 1/15 correct — pas un échec bruyant. Les 8 autres types de décision LLM
n'ont **jamais** été vérifiés que structurellement, jamais sémantiquement.
Le document nomme ceci « la découverte la plus importante » de son
investigation et scope un chantier de validation dédié — jamais ouvert.

**Pourquoi ceci précède v8, pas en parallèle** : la lecture tranchée pour
« distillation théorique » (§12, résolue 2026-08-30) est l'auto-
distillation sur les décisions déjà réussies du modèle. Mais « réussi »
n'a jamais signifié que « valide structurellement » pour 8 types de
décision sur 9. Curer des données d'entraînement sur cette base risque
de graver dans le marbre une corruption silencieuse déjà démontrée
possible — la définition même de pourquoi ce chantier doit précéder,
pas accompagner, la curation de données de v8.

## 1. Inventaire vérifié (pas supposé)

Le document de 2026-08-24 proposait des pistes de vérité terrain pour 3
types sans vérifier contre le code réel. Vérifié ici avant d'écrire quoi
que ce soit d'autre :

| Type | dt | `think` | Référence déterministe pré-LLM ? | Vérifié |
|---|---|---|---|---|
| `candidacy_considered` | 2 | `False` | **Oui** — `decide_candidacy` (seuil `ambition_score`) | `simple_rules.py:191` |
| `party_nomination_choice` | 4 | `False` | **Oui** — `select_party_nominee` (max `ambition_score` parmi les éligibles) | `simple_rules.py:285` |
| `pressure_action` | 10 | `False` | **Oui** — `deterministic_pressure_action(citizen, gap, menu, can_sign, can_launch)`, mêmes entrées que le chemin LLM | `simple_rules.py:412` |
| `coalition_decision` | 9 | `False` | Partiel — `form_coalition` existe mais décide au niveau parti/algorithme, pas « ce parti rejoindrait-il CE regroupement précis » | `simple_rules.py:358` |
| `reaction_to_event` | 8 | `False` | **Non, contrairement à l'hypothèse du doc de 2026-08-24** — `deterministic_reaction_to_event(event_type, config, magnitude)` ne prend **aucun paramètre `Citizen`**, une valeur plate appliquée identiquement à tout le monde « no per-citizen judgment by construction » (son propre docstring). Ne peut pas juger une décision individuelle. | `simple_rules.py:503` |
| `campaign_positioning` | 5 | `True` | Non — LLM-only depuis son introduction (v2 increment 4) | — |
| `representative_response` | 6 | `False` | Non — LLM-only depuis son introduction | — |
| `chamber_deliberation` | 11 | `True` | Non — LLM-only depuis son introduction (v6b Lot 3) | — |

**Correction d'une hypothèse du document source** : sa proposition
« `reaction_to_event` contre... » n'a jamais été vérifiée contre le code
réel avant d'être écrite — `deterministic_reaction_to_event` est
structurellement inutilisable comme vérité terrain par-citoyen. Corrigé
ici avant de le découvrir en implémentant, pas après.

## 2. Méthodologie, par groupe

### Groupe A — vérité terrain forte disponible (3 types)

`candidacy_considered`, `party_nomination_choice`, `pressure_action` ont
chacun une règle déterministe pré-LLM qui prend **les mêmes entrées**
que la décision LLM correspondante. Méthode directe, même patron que la
sonde `vote_cast`/`think=False` déjà validée dans le document source :
faire tourner la règle déterministe ET la décision LLM sur le même
citoyen/contexte réel (population/config d'un run réel), comparer.

Le désaccord n'est pas en soi une preuve de corruption — le LLM existe
précisément pour dépasser la règle simple dans les cas ambigus. Le signal
à chercher : désaccord sur des cas **non ambigus** (`party_nomination_
choice` : un contendant domine largement en `ambition_score` ET
`sympathizer_ratio` — les deux signaux, pas seulement celui du document
source, puisque `select_party_nominee` utilise `ambition_score`,
`sympathizer_ratio` mesure autre chose ; `pressure_action` : `gap` très
au-delà ou très en-deçà du seuil d'éveil ; `candidacy_considered` :
`ambition_score` loin dans un sens ou l'autre du seuil).

### Groupe B — vérité terrain partielle, à construire (1 type)

`coalition_decision` : pas de fonction réutilisable telle quelle, mais
une règle bon-sens constructible à partir de `seats`/`votes`/`platform`
déjà disponibles au moment de la décision — rejoindre pousserait-il
clairement au-dessus du seuil de majorité, et la plateforme du
regroupement est-elle proche ou loin de celle du répondant ? Cas non
ambigus seulement (majorité déjà large sans ce parti, ou beaucoup trop
loin idéologiquement pour rejoindre un regroupement cohérent) — pas une
réimplémentation de `form_coalition`, une règle de bon sens plus
grossière, construite pour ce chantier.

### Groupe C — aucune vérité terrain disponible (4 types)

`campaign_positioning`, `representative_response`, `reaction_to_event`,
`chamber_deliberation` : LLM-only depuis leur introduction, aucune règle
pré-existante à comparer. Construire un proxy théorique ici (« un
candidat devrait se rapprocher de l'électeur médian ») reproduirait
exactement l'erreur que ce projet vient de refuser pour la distillation
elle-même — injecter un critère théorique prescriptif que §3.3 exclut.

**Repli, plus faible mais réel — garantie explicitement plus faible que
les groupes A/B, pas un substitut équivalent** : la stabilité sur appels
répétés ne prouve jamais la justesse d'une décision, seulement l'absence
de variance grossière. Une décision peut être stable ET fausse (biais
systématique reproductible), tout comme une décision correcte peut
légitimement varier sur un cas réellement ambigu. À documenter comme tel
dans les résultats du Groupe C, pas comme une validation de qualité au
même titre que les Groupes A/B.

Test d'auto-cohérence : même citoyen,
même contexte, plusieurs appels à température=0 — la décision reste-t-elle
stable, ou varie-t-elle sans que rien dans l'entrée n'ait changé ? Une
forte variance n'identifie pas la bonne réponse, mais signale une
instabilité que même l'absence de vérité terrain ne peut pas excuser. Ce
groupe reste honnêtement moins vérifié que les groupes A/B après ce
chantier — à documenter comme tel, pas comme résolu.

### Audit de cohérence structurelle (transversal, hors LLM) — FAIT, 2026-08-30

Chaque schéma de décision (`llm_schemas.py`) vérifié contre sa propre
taxonomie de motifs réelle (`codebook.py`), pas contre ce que son
docstring affirme :

| Type | Règle de cohérence ? | Statut |
|---|---|---|
| `vote_cast` | Oui (`_check_blank_consistency`) | — |
| `representative_response` | Oui (`_check_stance_coherence`) | — |
| `reaction_to_event` | Oui (`_check_irrelevance_coherence`) | — |
| `coalition_decision` | Oui (`_check_action_motif_coherence`) | — |
| `party_nomination_choice` | Non | **Vraiment indépendant, confirmé** — `winner_position` est un simple index de liste, aucun motif n'implique logiquement une position précise. |
| `pressure_action` | Non | **Délibéré, bien justifié** — absence documentée en détail (306 a cassé une ancienne partition propre, argument de surface de rejet, plus gros volume d'appels du projet). |
| `chamber_deliberation` | Non | **Délibéré, fondé sur mesure** — une règle plus stricte a été essayée puis retirée après qu'un spike live a trouvé des boucles Mode A (9/10, 6/6 échecs). |
| `candidacy_considered` | Non | **Vrai écart trouvé.** Le docstring affirme « outcome et motif sont indépendants... rien à maintenir cohérent » — faux une fois vérifié contre `CandidacyMotif` : un seul motif (203, `AMBITION_THRESHOLD_MET`) est une raison de déclarer, les trois autres (201, 204, 205) sont toutes des raisons de décliner. `outcome==1 ssi motif==203` est une règle réellement applicable, jamais posée, et l'affirmation du docstring qui la niait n'a jamais été vérifiée avant aujourd'hui. |
| `campaign_positioning` | Non | **Vrai écart trouvé.** Le docstring dit lui-même « une liste vide signifie que le nominee se présente sur sa position sincère (motif=SINCERE_CONVICTION) » — une relation shifts↔motif affirmée mais jamais appliquée. |

**Décision : ne rien corriger dans ce lot.** Ajouter une règle de
cohérence est elle-même un risque de fiabilité — l'historique de
`chamber_deliberation` (règle ajoutée, boucles Mode A trouvées, règle
retirée) est le contre-exemple direct. Les deux écarts trouvés
(`candidacy_considered`, `campaign_positioning`) sont documentés et
remontés ici ; la décision de les corriger (et la vérification de
non-régression Mode A/B que ça exigerait, même discipline que Chamber)
reste un chantier séparé, pas une correction à la volée dans ce lot.

## 3. Ordre d'exécution et pilote

1. **Audit de cohérence structurelle** (§2, transversal) — code only,
   fait en premier, coût négligeable.
2. **Pilote unique : `pressure_action`** avant de construire les 7 autres
   sondes. Choisi parce que : entrées déjà pré-calculées et frozen par
   caller (`PressureContext`, aucune dépendance cachée à recréer),
   volume de données le plus élevé de tout ce module (tourne chaque tick
   pour chaque citoyen consulté — cf. `llm_behavior_engine.py` : « la
   première décision réutilisant `chunk_voters` depuis increment 1 » à
   l'échelle), et sert de validation de la MÉTHODE elle-même
   (comparaison contre une règle déterministe à mêmes entrées) avant
   d'investir dans les 7 autres.
3. **Si le pilote confirme la méthode** : Groupe A restant
   (`candidacy_considered`, `party_nomination_choice`), puis Groupe B
   (`coalition_decision`), puis Groupe C (auto-cohérence, moins
   prioritaire — signal plus faible, coût similaire).

### Critère pré-enregistré du pilote — écrit avant tout appel live

`deterministic_pressure_action` n'est **pas** une échelle graduée : une
seule porte binaire (`gap < blank_threshold` → NOTHING, sinon → un acte
choisi par une priorité de menu rigide sign > launch > mobilize > wait).
Le pilote ne compare donc **pas** quel levier précis le LLM choisit parmi
sign/launch/mobilize — c'est exactement l'axe d'arbitrage libre que ce
palier existe pour observer (§11.4 : « Lot 7's LLM sees the whole menu
and arbitrates freely »), pas un axe à valider contre la règle rigide.
Ce qui est vérifié, plus étroit et plus défendable : **agir vs ne pas
agir** (tout acte ≠ NOTHING/WAIT_FOR_ELECTION), dans la direction attendue
par la position du citoyen relativement à son propre `blank_threshold`.

- **Cas « non ambigu »** défini relativement à chaque citoyen, pas par un
  seuil absolu arbitraire : `gap < 0.5 × blank_threshold` (clairement en
  dessous, NOTHING attendu) ou `gap > 1.5 × blank_threshold` (clairement
  au-dessus, un acte est attendu). Marge symétrique de 50 % autour du
  seuil propre à chaque citoyen — les cas entre les deux (le voisinage
  du seuil, là où le désaccord raisonnable est attendu) sont exclus du
  calcul d'accord.
- **Taille** : ~30 citoyens consultés réels (même ordre de grandeur que
  les spikes de fiabilité déjà établis ce projet), tirés d'un run réel
  ou d'une population/contexte synthétique réaliste.
- **La méthode est validée** (construire les 6 sondes restantes) si,
  sur les cas non ambigus uniquement : le taux d'accord agir/ne-pas-agir
  entre le LLM et la porte déterministe est **≥ 90 %**, ET les
  désaccords observés (s'il y en a) sont explicables à l'inspection
  directe (une décision lisible, pas un charabia ou une réponse dégénérée)
  plutôt qu'un signe de corruption structurelle.
- **Zone grise, ni l'un ni l'autre** (documenter honnêtement comme telle,
  ne pas forcer une conclusion) : désaccord entre ~10 % et ~20-25 %.
  Même réflexe que le test de stationnarité à ~50 % cette semaine — une
  lecture forcée dans un sens ou l'autre serait prématurée sur un seul
  pilote.
- **La méthode a un problème** (arrêter, ne pas construire les 6 autres
  sondes avant d'avoir compris pourquoi) si : le taux de désaccord sur
  les cas non ambigus dépasse ~20-25 %, OU un motif de collapse
  structurel apparaît (le même acte quel que soit `gap`, la signature
  « permutation quasi-uniforme » déjà documentée pour `cast_votes` sous
  `think=False`). Dans ce cas, deux explications possibles à départager
  avant de continuer : soit la marge « non ambigu » choisie ici est
  elle-même mal calibrée, soit `pressure_action` a un vrai problème de
  fiabilité de contenu que la validation structurelle n'a jamais capté —
  et dans les deux cas, ça se documente et se remonte avant d'aller plus
  loin, pas une décision à trancher après avoir vu le taux.

### Résultat du pilote — VERDICT « la méthode a un problème », 2026-08-30

Deux tirages : 122 décisions (population 100, 40 cas non ambigus, désaccord 25,0 %, zone grise
au sens du critère ci-dessus) puis 313 décisions (population 280, 108 cas non ambigus, désaccord
41,7 %) — le second tirage n'a pas resserré l'intervalle autour de 25 %, il a montré que ce taux
était lui-même une sous-estimation d'échantillon. **41,7 % dépasse largement le seuil « problème »
(~20-25 %)** : verdict tranché par le critère pré-enregistré lui-même, pas une lecture forcée.

Investigation du mécanisme (`check_pressure_action_chunk_reorder.py`,
`check_pressure_action_chunk_size_sensitivity.py`, `check_pressure_action_chunk_generality.py`,
`check_pressure_action_chunk_size_curve.py` — tous committés) : le désaccord n'est ni un biais par
citoyen ni un artefact de position dans le batch (deux réordonnancements du même chunk collapsé
reproduisent le même résultat). C'est une bascule nette entre deux états, aucun des deux correct :
à la taille de production (`max_batch_size=25`), le chunk entier converge vers un seul acte,
ignorant le `ctx` individuel ; à toute taille testée en dessous (3, 5, 10 — 3 chunks réels, 189
décisions), le modèle n'a **jamais** choisi un code d'action (SIGN/LAUNCH/MOBILIZE), quel que soit
le contenu. Généralité confirmée sur 3 chunks distincts, deux polarités de collapse d'origine.
Troncature écartée structurellement (`_extract_native_content` échoue dur sur tout `done_reason`
non-`"stop"` — le script n'aurait pas pu terminer sans erreur sinon). **Pas un problème de
dimensionnement de batch** (contrairement à `cast_votes`/`chamber_deliberation`, où réduire la
taille a suffi) — plus probablement quelque chose dans la formulation même du prompt/schéma de
`pressure_action`. Détail complet et preuves :
`reasoning_budget_and_decision_quality_findings.md`.

**Conséquence, par le critère pré-enregistré lui-même** : arrêt, pas de construction des 6 autres
sondes tant qu'une piste de remédiation n'est pas identifiée. `pressure_action` marqué non fiable
en production (docstring de `decide_pressure_actions`, §3.6.6 du document de conception) — un vrai
type de décision qui tourne dans les runs actuels, pas seulement un résultat de recherche.

### Clôture du chantier `pressure_action`, 2026-08-30 — trois causes écartées par test direct, mécanisme réel non identifié, différé avec candidat concret

Suite complète des éliminations, chacune testée directement, pas supposée : **pas un artefact de
position** (deux réordonnancements du même chunk collapsé reproduisent le même résultat) ; **pas
un problème de taille de batch** (courbe complète 1/3/5/10/production testée sur 3 chunks réels —
0/63 codes d'action même à taille 1 en isolation totale, y compris le cas « devrait agir » le plus
extrême du jeu de données) ; **pas la phrase « 0/4 sont des résultats légitimes » agissant seule**
(ablation causale pré-enregistrée, 0 bascule sur 4 cas extrêmes + 1 témoin). Le canal de
raisonnement forcé (`think=True`) s'est révélé indisponible à taille 1 pour ce type de décision
(collapse silencieux vers `act=4`/`motif=305`, confirmé sur 6 citoyens) — un mode de défaillance
catalogué à part, pas un chemin d'explication.

**Mécanisme réel non identifié.** Hypothèse structurelle restante, nommée et non testable par
suppression : le menu à 5 options dont 2 (`NOTHING`, `WAIT_FOR_ELECTION`) sont structurellement
posées comme une catégorie toujours légitime — pas seulement décrites ainsi par la phrase déjà
retirée, mais construites dans la forme même de la décision (un choix plat parmi cinq). **Candidat
concret pour une session de conception future, même discipline que le concept de « loi » manquant
pour le veto de la chambre (#11)** : scinder la décision en deux étapes — un jugement binaire
strict agir/ne-pas-agir d'abord, puis, seulement si « agir », un choix parmi
SIGN/LAUNCH/MOBILIZE. Non testé — un vrai changement de schéma/flux de décision, avec son propre
cycle de pré-enregistrement et de validation, pas un diagnostic rapide de plus.

**Statut, 2026-08-30** : chantier refermé pour aujourd'hui à ce point — différé, daté, avec une
prochaine étape nommée, pas abandonné. `pressure_action` reste marqué non fiable en production,
mécanisme bien caractérisé mais non résolu. Les 6 autres sondes restent en pause jusqu'à ce que ce
point soit repris.

## 4. Coût estimé

Chaque sonde de type Groupe A/B suit l'échelle déjà établie par ce
projet pour un spike de fiabilité (~25-30 essais live, comme
`lot3_chamber_reliability_results.md`) — mais ici doublé effectivement
puisqu'il faut la décision LLM ET la comparaison déterministe pour
chaque cas, pas juste une décision seule. Ordre de grandeur : 4 sondes
(Groupes A+B) × ~30 essais chacune, appels courts (`think=False` pour
3 des 4) — nettement moins cher qu'un spike `think=True` typique. Groupe
C (auto-cohérence, 4 types) : même ordre de grandeur par type, mais
`campaign_positioning`/`chamber_deliberation` tournent en `think=True`,
plus coûteux par appel (cf. `_POSITIONING_THINK_TOKEN_ALLOWANCE=8000`,
`_CHAMBER_MAX_CHUNK_SIZE=1`). Total forecast : de l'ordre de quelques
heures GPU, pas des jours — à confirmer sur le pilote avant d'engager le
reste, pas une promesse.

## 5. Hors scope de ce lot

- Construire la moindre donnée d'entraînement ou pipeline de fine-tuning
  — dépend entièrement du verdict de ce chantier.
- Corriger quoi que ce soit trouvé en cours de route (un vrai bug de
  corruption silencieuse trouvé sur un des 9 types serait documenté et
  remonté, pas réparé à la volée dans ce même lot).
- Un juge automatisé quel qu'il soit — même raisonnement que l'outil
  d'audit du point ouvert #3 : rien d'autre dans ce projet ne fait juger
  le LLM par le LLM, et ce chantier ne commence pas cette pratique.

## 6. Statut après le chantier `pressure_action` / cadrage acte-réponse (2026-08-30)

**Une distinction à ne pas perdre, par instruction explicite** : en creusant `pressure_action` et
la découverte de portée plus large qui en a émergé (`plan-adversarial-framing-collapse.md`), 5
des 6 autres types initialement scopés ici ont été **touchés**, mais pas selon le protocole
complet de ce document (Groupe A/B/C, ≥30-60 essais, barre ≥90%/≥80%). Ils ont reçu un test de
**signature de collapse** : la question binaire et grossière « ce type de décision s'effondre-t-il
vers une réponse fixe en isolation, sur des cas extrêmes des deux pôles (4-6 essais) », pas la
question fine « quelle est sa précision réelle sur l'ensemble de sa distribution de production,
avec une confiance suffisante ». Cette distinction compte concrètement : le premier pilote
`pressure_action` a lui-même mesuré 25,0% de désaccord sur un petit échantillon, puis 41,7% une
fois l'échantillon doublé — un type de décision qui « ne collapse pas » sur 4-6 cas extrêmes n'a
**aucune garantie** d'avoir 90% de précision sur sa distribution réelle. Les résultats de
signature de collapse sont une contribution réelle au chantier de conception (`act/réponse vs
seuil`), pas un score de fiabilité de production validé.

| Type | Statut mis à jour | Détail |
|---|---|---|
| `pressure_action` | Mécanisme de collapse **confirmé**, fiabilité de production **non fiable, marqué comme tel** | Pilote complet mené (41,7% de désaccord), pas juste signature de collapse — voir `reasoning_budget_and_decision_quality_findings.md` |
| `representative_response` | Mécanisme de collapse **confirmé** (signature seulement) | `plan-adversarial-framing-collapse.md` — fiabilité de production non validée par le protocole complet, mais non fiable de toute façon (marqué comme tel dans le principe de conception §3.6.0) |
| `coalition_decision` | Mécanisme de collapse **confirmé** (signature seulement) | idem — non fiable de toute façon |
| `reaction_to_event` (branche SCANDAL) | Mécanisme de collapse **confirmé** (signature seulement, une seule branche testée) | idem — non fiable de toute façon ; branche ECONOMIC_SHOCK non testée |
| `candidacy_considered` | Mécanisme de collapse **écarté** (signature seulement) | Candidat légitime pour le protocole complet Groupe A — pas de défaut structurel connu |
| `party_nomination_choice` | Mécanisme de collapse **écarté** (pilote réel avec vérité de référence, 4/5 = 80%) | Candidat légitime pour le protocole complet Groupe A — le seul des 5 « touchés » à avoir déjà une mesure de précision réelle, pas seulement une signature ; un second échantillon resserrerait la confiance |

**Conséquence pour la suite de ce chantier** : les 3 types dont le collapse est confirmé
(`representative_response`, `coalition_decision`, `reaction_to_event`) restent en file d'attente
pour le protocole complet, mais ne le méritent pas tant que la remédiation n'est pas trouvée —
mesurer précisément la précision d'un système déjà cassé n'apporte rien. `candidacy_considered`
et `party_nomination_choice` restent candidats légitimes pour la validation complète, puisqu'ils
n'ont pas ce défaut structurel connu.

`campaign_positioning`/`chamber_deliberation` : testés (`plan-adversarial-framing-collapse.md`),
résultats **non tranchés**, ni collapse plat ni comportement propre — `campaign_positioning`
sature son plafond de shifts (3) dans les deux pôles testés avec un motif qui varie de façon
plausible (contenu réel des ajustements non loggé, 66% d'échec sur un pôle) ;
`chamber_deliberation` répond correctement à l'état que le prompt prescrit explicitement mais
couple systématiquement un motif « ajustement actif » à une liste de shifts vide sur son second
pôle. Ni candidats francs pour le protocole complet, ni classables comme cassés — suivi ciblé
nécessaire avant de trancher, pas fait ici.
