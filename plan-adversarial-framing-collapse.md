# Cadrage acte/réponse vs auto-évaluation à seuil, et collapse de contenu en isolation — une hypothèse de conception, pas encore une loi générale

> Découverte de conception, pas une remédiation de prompt isolée — voir
> `plan-pressure-action-remediation.md` pour la question d'origine (comment
> réparer `pressure_action` spécifiquement), qui reste pertinente
> indépendamment de ce document et pourrait être informée par lui une fois
> le principe mieux compris. Ce document existe pour que cette découverte
> soit vue et citée indépendamment, pas enterrée en annexe d'un chantier
> plus étroit — même traitement que ADR-002/ADR-003 pour les découvertes
> de cette ampleur cette semaine.
>
> **Théorie révisée, 2026-08-30 (fin de journée)** : la lecture initiale
> (« cadrage adversarial/relatif-à-une-cible ») a été affinée deux fois en
> cours de route — d'abord parce qu'un test causal direct a montré que la
> simple présence d'une cible nommée ne suffit pas (`candidacy_considered`
> + référence neutre à un titulaire ne casse pas), puis parce que
> `representative_response` (qui collapse) n'a en fait AUCUNE référence à
> un autre acteur dans son `ctx`, contredisant même la lecture « acteur
> externe nommé ». Théorie retenue après un test décisif sur
> `party_nomination_choice` (comparatif entre pairs, sans acteur externe,
> sans forme acte/réponse — ne collapse pas) : **c'est la forme
> acte/réponse de la décision (une action ou une réaction avec conséquence
> institutionnelle vis-à-vis de l'extérieur) qui est à risque, pas la
> présence d'un acteur externe ni un ton adversarial en soi.** Le titre et
> le tableau-bilan reflètent cette théorie révisée ; les sections
> narratives ci-dessous gardent l'historique des deux lectures précédentes
> et pourquoi chacune s'est révélée incomplète — utile pour ne pas
> retomber dans les mêmes impasses si la théorie doit encore bouger.

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

## Bilan, corrigé 2026-08-31 : 4/5 cadrages acte/réponse collapsent (1 exception réelle), 2/2 auto-évaluations à seuil ne collapsent pas, 1 cas non tranché

**`campaign_positioning` est act/réponse par sa forme (ajuster sa plateforme en réaction aux
rivaux/à l'électorat) mais NE collapse PAS** (contenu vérifié, voir section dédiée ci-dessous) —
la théorie n'est donc plus un prédicteur à 100 % au sein de sa propre catégorie. Titre corrigé en
conséquence plutôt que laissé à « 4/4 », qui ne tient plus.

| Type de décision | Forme | Vérité de référence | Résultat |
|---|---|---|---|
| `pressure_action` | Acte (choisir un levier de pression) | Réelle, fonctionnelle | **Collapse** (0/70) |
| `representative_response` | Acte/réponse (choisir une posture) | Constante seulement | **Collapse** (4/4 identiques) |
| `coalition_decision` | Acte (rejoindre/refuser une coalition) | Partielle | **Collapse** (6/6 identiques) |
| `reaction_to_event` (SCANDAL) | Acte/réaction à un événement | Aucune | **Collapse** (6/6 identiques) |
| `candidacy_considered` | Auto-évaluation à seuil (ambition/soutien perçu) | Réelle, fonctionnelle | **Pas de collapse** (5/5 correct) |
| `party_nomination_choice` | Auto-évaluation comparative entre pairs (ambition) | Réelle, fonctionnelle | **Pas de collapse** (4/5, 80,0%) |
| `campaign_positioning` | Acte (ajuster sa plateforme de campagne) | Aucune | **Pas de collapse** — contenu vérifié, varie réellement entre nominés et entre pôles (2026-08-31) ; **exception au sein de la catégorie acte/réponse**. Défaut distinct et non résolu : 50-66% d'échec (troncature + fuite motif→cid) selon le pôle |
| `chamber_deliberation` | Acte/réflexion (maintenir ou ajuster sa position) | Aucune (prompt prescrit un cas) | **Non tranché sur la théorie** — pôle prescrit correct (3/3) ; incohérence du pôle dérivé (motif actif + aucun ajustement réel, 3/3 uniforme) **corrigée en production** (correctif d'étiquette tracé, pas un rejet), comportement sous-jacent toujours non expliqué |

## Le principe suspecté — hypothèse de conception, pas une loi générale

**Une décision formulée comme un acte ou une réponse avec conséquence
institutionnelle vis-à-vis de l'extérieur (agir, répondre, rejoindre,
réagir) semble structurellement à risque de collapse content-blind en
isolation (`size=1`, `think=False`) sur ce modèle (`qwen3:8b`) — tandis
qu'une auto-évaluation contre un seuil, même comparative entre plusieurs
pairs, ne l'est pas.** Ni la présence d'un acteur externe nommé dans le
`ctx` (`representative_response` n'en a aucun et collapse quand même), ni
un ton adversarial au sens strict (`coalition_decision` est une décision
de coopération et collapse aussi) ne se sont révélés être le facteur
discriminant une fois vérifiés précisément — voir les sections
ci-dessus pour l'historique complet des deux lectures écartées.

Ce que ce résultat NE dit PAS, pour rester honnête sur sa portée :
- **Pas une preuve causale du mécanisme.** 4 confirmations et 2 contrôles
  négatifs (5/5 et 4/5) est un signal fort, pas une preuve formelle —
  aucune variable confondue n'a été isolée expérimentalement comme LE
  facteur causal exact, seulement comme un axe qui explique mieux les 6
  cas déjà regardés que les deux lectures précédentes. `pressure_action` a
  déjà montré que retirer une phrase de cadrage spécifique ne suffit pas
  à elle seule (`plan-pressure-action-remediation.md` §3.1) — le
  mécanisme réel reste non identifié même pour le cas le mieux
  caractérisé des quatre.
- **Pas nécessairement propre à `qwen3:8b`** — non testé sur d'autres
  modèles pour CES types (le test cross-modèle de
  `plan-pressure-action-remediation.md` §1 ne portait que sur
  `pressure_action`, et lui-même n'a produit que 2 échantillons
  exploitables sur 4 modèles alternatifs).
- **Pas nécessairement lié au batching** — déjà écarté comme cause pour
  `pressure_action` (`size=1` collapse identiquement) ; `representative_
  response` est confirmé représentatif de la production (jamais batché) ;
  `coalition_decision`/`reaction_to_event` restent non vérifiés à leur
  échelle de batch réelle (voir la section batching ci-dessus).
- **Le collapse `think=True` en configuration single-citizen-batch (catalogué séparément dans
  `reasoning_budget_and_decision_quality_findings.md`) n'est PAS une preuve à l'appui de cette
  théorie** — vérifié 2026-08-30 (`check_candidacy_forced_reasoning_comparison.py`) : la même
  suppression totale de raisonnement se reproduit sur `candidacy_considered` (8/8 citoyens, deux
  pôles, aucun collapse sous son propre chemin `think=False` réel) sous ce même appel forcé.
  Semble être une propriété générale de cette configuration d'appel elle-même, jamais utilisée en
  production, pas un symptôme du cadrage acte/réponse.

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

## Les deux types réellement non testés — résultats nuancés, pas un simple oui/non (2026-08-30)

Les deux seuls types de décision jamais testés, structurellement, ni acte/réponse ni seuil a
priori évident (`campaign_positioning`/`chamber_deliberation` — aucune vérité de référence,
vérifié contre le code : tous deux remplacent un fallback constant « pas de changement », pas une
fonction de jugement réelle). Testés en signature de collapse comme prédit par la théorie
(act/réponse) — mais les deux résultats sont plus subtils qu'un simple « collapse ou pas », et le
verdict imprimé par chaque script (vérification binaire des paires de sortie) sous-estime la
nuance réelle — corrigé ici plutôt que repris tel quel.

### `campaign_positioning`

3 nominés loin de la moyenne électorale (dist. 1,73-1,83) vs 3 nominés déjà alignés (dist. 0,31) —
`think=True`, `size=1` (chunking réel de production : « a handful, `parties.initial_count` », donc
plus petit qu'un batch typique, écart non testé comme `coalition_decision`).

```
LOIN:    3/3 -> shifts=3, motif=602 (MEDIAN_VOTER_APPEAL)
ALIGNE:  1/3 -> shifts=3, motif=603 (BASE_CONSOLIDATION) ; 2/3 echec (troncature, motif fuite dans cid)
```

`max_positioning_shifts` livré = **3** — chaque appel réussi a saturé le plafond exact, dans les
deux pôles. Le motif diffère de façon plausible et cohérente avec chaque situation (appel au
centre pour qui en est loin, consolidation de base pour qui y est déjà) — pas un label arbitraire.
Mais le CONTENU réel des ajustements (quelles dimensions, quels deltas) n'a pas été loggé, donc
impossible de trancher si « toujours saturer le plafond » masque un collapse plus subtil (le
compte est fixe, seul le motif varie) ou reflète un vrai raisonnement stratégique dont seul le
volume happens to converge. **Non tranché** — 66% d'échec sur le pôle aligné (troncature +
fuite de motif dans le champ `cid`, la même signature déjà vue chez `qwen2.5:7b`) est lui-même un
résultat à part, distinct de la question du collapse.

**Résultat avec logging de contenu, 2026-08-31**
(`check_campaign_positioning_collapse_signature.py`, instrumentation corrigée) :

```
LOIN:    cid=93  dist=1.7254 -> shifts=1 content=((0, 0.3),)                            motif=602
         cid=295 dist=1.7352 -> shifts=3 content=((0, 0.3), (1, -0.18), (5, -0.19))       motif=603
         cid=49  dist=1.8344 -> ECHEC (batch desaligne : cid retourne = motif, pas 49)
ALIGNE:  cid=251 dist=0.3084 -> shifts=3 content=((11, -0.12), (15, -0.13), (16, 0.12))   motif=602
         cid=79  dist=0.3240 -> ECHEC (troncature, finish_reason=length)
         cid=64  dist=0.3306 -> ECHEC (batch desaligne : cid retourne = motif, pas 64)
```

**Tranché : PAS un collapse.** Le contenu varie réellement, entre nominés ET entre pôles — aucune
paire de sorties n'est identique. Ceci **corrige** l'affirmation ci-dessus (« chaque appel réussi a
saturé le plafond exact ») : `cid=93` (pôle LOIN) n'a produit qu'1 seul shift, pas 3 — le plafond
n'est donc pas systématiquement saturé, contrairement à ce que les 4 seuls appels réussis du
premier passage (sans logging de contenu) laissaient croire. Le motif varie aussi À L'INTÉRIEUR
d'un même pôle (602 chez `cid=93`, 603 chez `cid=295`, tous deux LOIN) — pas seulement entre pôles
comme supposé. `campaign_positioning` n'étend donc PAS le motif de collapse content-blind confirmé
sur les 4 autres types act/réponse — la prédiction de la théorie échoue ici.

**Réserve sur la taille d'échantillon** : seulement 3/6 appels réussis ce passage (50 %), 4/6 au
passage précédent — cumulé, ~7 observations valides sur 12 tentatives à travers les deux passages.
Suffisant pour rejeter « contenu toujours identique » (une seule paire différente suffit), mais
**pas** suffisant pour affirmer un raisonnement stratégique pleinement fiable — seulement pour
exclure le collapse tel que défini par ce critère.

**Le taux d'échec (50 % ce passage, cohérent avec 66 % côté ALIGNÉ au passage précédent) reste un
problème à part, non résolu par ce test et distinct de la question du collapse** : la même
signature de fuite motif→cid réapparaît (`cid` retourné = valeur de motif attendue, pas le cid
demandé) sur 2 des 3 échecs, plus une troncature pure (`finish_reason=length`) malgré le budget de
8000 tokens déjà généreux. `campaign_positioning` sous `think=True` reste donc peu fiable en
pratique même là où son contenu, quand il arrive à terme, n'est pas un collapse — deux défauts
indépendants, à ne pas confondre.

**Mesure du taux d'échec à plus grand n, 2026-08-31** (décision explicite de l'utilisateur : lancer
un test dédié plutôt que documenter seulement ou laisser tel quel).
`decide_campaign_positioning`'s own docstring (`llm_behavior_engine.py`) affirmait « 5/5 correct
batches » pour `think=True` — en contradiction avec le 50 % observé ci-dessus à n=6.
`check_campaign_positioning_failure_rate.py` (16 par pôle, n=32, même protocole, expérience
`20260831T233502Z-586e3c0e`) :

```
FAR pole:     4/16 failed
ALIGNED pole: 4/16 failed
overall:      8/32 (25,0%)
failure modes: {truncation: 6, cid_motif_leak_or_misalignment: 2}
```

**Le taux réel se stabilise à 25 %, pas 50 % — le n=6 était un tirage haut, pas du bruit pur (25 %
reste bien au-dessus de 0), mais le taux vrai est plus proche de 1 échec sur 4 que d'1 sur 2.**
Franchit exactement le seuil pré-enregistré (≥ 25 %) : **la revendication « 5/5, résolu proprement »
du docstring est fausse pour des batches `size=1`** — corrigé directement dans
`llm_behavior_engine.py` (RELIABILITY CAVEAT ajoutée à `decide_campaign_positioning`, pas une
réécriture de l'affirmation d'origine, qui reste vraie pour le contexte où elle a été mesurée -- un
acceptance run à la taille de batch réelle de production, plus grande que `size=1`). Le mode
dominant a aussi changé : troncature (6/8) plutôt que fuite motif→cid (2/8), contrairement à ce que
le n=6 seul suggérait (1 troncature, 2 fuites). Le contenu des 24 appels réussis confirme, à plus
grande échelle, l'absence de collapse déjà établie (motifs 601/602/603 tous observés, dimensions et
deltas différents à chaque appel, y compris entre nominés du même pôle). Ce que ce taux d'échec
implique pour la taille de batch réelle de production (plus grande que `size=1`) reste non mesuré.

**PROCHAINE ÉTAPE IMMÉDIATE, pas une dette vague (2026-08-31, à la demande de l'utilisateur avant
tout commit)** : vérifier si les 6/8 troncatures ci-dessus partagent la signature Mode A déjà
diagnostiquée et corrigée pour `chamber_deliberation` (§ ci-dessous, `lot3_chamber_reliability_
results.md` « Lot 5 correction ») — un paragraphe de rumination quasi identique répété des dizaines
de fois dans `message.reasoning`, atterrissant systématiquement pile sur le plafond de tokens
configuré, symptôme d'une boucle non convergente que le budget ne peut PAS résoudre (contrairement
à Mode B, où plus de budget suffit). Si confirmé, la correction serait la même méthode que pour
`chamber_deliberation` : une phrase de désambiguïsation dans le prompt ciblant l'état précis qui
déclenche la boucle, pas un changement de budget — et ce serait la première vraie victoire de
remédiation sur ce chantier (les 4 collapses act/réponse confirmés n'ont, à ce jour, aucune piste
positive — voir `plan-pressure-action-resolution.md`, Phase 2 entièrement négative).

**Obstacle diagnostique à contourner, déjà rencontré et déjà résolu une fois** : `OllamaJsonClient.
complete_json`'s `_extract_content`/`_extract_native_content` lèvent `LlmResponseError` dès que
`finish_reason != "stop"`, jetant `message.content`/`message.reasoning` avant que l'appelant ne les
voie — exactement le trou diagnostique que la sonde `chamber_deliberation` (`probe_chamber_
truncation.py`, scratchpad, jamais committé) a dû contourner par un POST HTTP brut reproduisant le
corps de requête réel (même technique que `pressure_action_harness.raw_pressure_call`, mais pour le
prompt de `campaign_positioning`, pas encore écrite). Prochaine étape concrète : un script du même
genre, appelant `build_positioning_system_prompt`/`build_positioning_user_prompt` réels, POST brut
bypassant `complete_json`, capturant `message.reasoning` complet sur les cas `finish_reason='length'`
spécifiquement — pré-enregistré via le harnais avant tout appel, comme le reste de cette
investigation. Cible naturelle : les 6 cid déjà identifiés comme troncature dans le run à n=32
(`184, 167, 126, 79, 209, 158` — expérience `20260831T233502Z-586e3c0e`, requêtes reproductibles au
même seed/config).

**Résultat, 2026-08-31** (`check_campaign_positioning_truncation_reasoning.py`, POST brut
mirroring `_complete_json_openai_compat`, `message.reasoning` capturée même hors `finish_reason=
'stop'`) :

```
cid=184: no_repro (finish_reason=stop cette fois, non-determinisme sous batching, deja documente ailleurs)
cid=167: MODE_A -- x242 "Wait, the user's instruction says that the decisions must be a list containing exactly the cid 16..."
cid=126: no_repro (finish_reason=stop cette fois)
cid=79:  MODE_A -- x55/x52/x51/x49/x47, cinq variantes de "Alternatively, maybe the electorate_mean is for each of the 10 dimensions, and the user provided 20 numb[ers]..."
cid=209: MODE_A -- x63 "This is conflicting.", x60 sur la liste decisions, x32 "However, the valid codes are 601-604."
cid=158: MODE_A -- x59 sur la liste decisions, x56 "So the decisions list is [158], and the codes are 601-604.", x33 "This is conflicting.", x31 "This is very confusing."
```

**CONFIRMÉ : signature Mode A, 4/4 troncatures reproduites** (2 des 6 cid n'ont pas retronqué à ce
tirage — cohérent avec le non-déterminisme déjà documenté sous batching, pas un désaccord). Même
mécanisme que `chamber_deliberation` : un paragraphe quasi identique répété 47 à 242 fois,
`finish_reason='length'` pile au plafond configuré (9596 tokens = `compute_max_tokens(1) +
_POSITIONING_THINK_TOKEN_ALLOWANCE`), le modèle boucle au lieu de conclure. **C'est la première
piste de remédiation réelle sur ce chantier** — les 4 collapses act/réponse confirmés n'en ont
aucune (Phase 2 de `plan-pressure-action-resolution.md` entièrement négative).

**Deux déclencheurs plausibles, distincts, ni l'un ni l'autre encore confirmé au niveau du prompt
(contrairement au cas chamber_deliberation, où la phrase ambiguë exacte a été identifiée avant
d'écrire le correctif)** :
1. `build_positioning_system_prompt` ne contient **aucune phrase de guidage shifts↔motif**
   (contrairement à `build_chamber_system_prompt`, qui dit explicitement « motif=701 correspond à
   une liste shifts vide, motif=702 à au moins un ajustement »). `CAMPAIGN_MOTIF_PROMPT_TABLE`
   liste juste 601-604 sans dire lequel correspond à une liste `shifts` vide (601 SINCERE_CONVICTION,
   par déduction) vs non vide (602-604) — cid=209/cid=158 rument précisément là-dessus (« the valid
   codes are 601-604 », « the decisions list is [...], and the codes are 601-604 », « This is
   conflicting »). Candidat direct pour une phrase de désambiguïsation, même forme que le correctif
   déjà livré pour `chamber_deliberation`.
2. cid=79 rumine sur autre chose : une confusion possible entre le nombre de dimensions de
   `issue_positions`/`electorate_mean` et celui de `issue_priorities` (« electorate_mean is for
   each of the 10 dimensions... the user provided 20 numb[ers] ») — **vérifié et écarté comme
   asymétrie réelle des données** : `issue_positions` et `issue_priorities` font toutes deux
   `config.citizens.issue_count=20` dimensions (`citizen.py:180`, `polity_config.yaml:121`), et
   `electorate_mean` est calculé sur ces mêmes 20 dimensions (`decide_campaign_positioning`'s
   `np.mean([c.issue_positions ...], axis=0)`, reproduit à l'identique dans le script de mesure).
   Le « 10 vs 20 » que le modèle invoque ne correspond à rien dans les données envoyées — un
   artefact de raisonnement, pas une ambiguïté de prompt identifiable comme celle de
   `chamber_deliberation`. Reste inexpliqué en tant que tel ; ne pas confondre avec l'hypothèse 1
   ci-dessus, qui elle reste une piste concrète et actionnable.

**Pas encore fait** : lire les traces `reasoning` complètes (39-42k caractères chacune, seuls les 5
fragments les plus répétés ont été extraits ici) pour confirmer laquelle de ces deux hypothèses (ou
une troisième) est la cause réelle avant d'écrire un correctif — même standard que
`chamber_deliberation`, où le diagnostic a précédé le correctif, jamais l'inverse.

**Traces complètes lues, 2026-08-31** (`check_campaign_positioning_truncation_reasoning.py`
modifié pour dumper `message.reasoning`/prompts complets, relancé sur les mêmes 6 cid) : mêmes 4
troncatures reproduites (167, 79, 209, 158), point de bascule entre mot ~400 et ~870 (bien avant
l'épuisement du budget de 8000 tokens).

**Hypothèse 1 confirmée, sur 3/4 traces (167, 209, 158)** : dans chacune, le travail de fond
(calcul des shifts par dimension, raisonnement sur le motif) est **substantiellement terminé** au
moment de la bascule — exactement le même schéma que `chamber_deliberation` (réponse correcte
trouvée tôt, puis spirale sur le format, pas sur le fond). La rumination elle-même est lisible et
concrète, ex. cid=209 : *« the decisions list must contain exactly [209]... But the valid codes are
601-604... This is conflicting »*, répété 30 à 63 fois. Le modèle lit la phrase « la liste decisions
doit contenir EXACTEMENT ces 1 cid... [209] » comme si elle entrait en conflit avec la table des
motifs (601-604) juste au-dessus — comme si la liste `decisions` devait À LA FOIS être `[209]` et
énumérer les 4 codes. Mécanisme plausible : contrairement au prompt de `chamber_deliberation` (deux
phrases tampon entre la table des motifs et l'auto-vérification cid), celui de `campaign_positioning`
n'avait **aucune** phrase de séparation entre les deux — et à `size=1`, « chacun une seule fois »
appliqué à une liste à un seul élément est une formulation particulièrement vide de sens,
probablement aggravante.

**Hypothèse 2 réfutée en tant qu'ambiguïté de prompt (cid=79)** : la confusion démarre dès le
premier paragraphe, avant tout travail de fond — différent des 3 autres cas. Vérifié directement
contre le corps de requête réel envoyé (`cid79_user_prompt.txt`) : `position`, `priorities`,
`party_platform` et `electorate_mean` font tous 20 éléments, aucune incohérence réelle. Le modèle
**tronque sa propre transcription** du tableau `position` à 10 éléments dans sa réponse (« Their
position is [0.5489, ..., 0.5217] » — exactement les 10 premiers des 20 réels), puis se rend
compte que l'`electorate_mean` (qu'il retranscrit correctement) ne correspond pas à sa PROPRE copie
tronquée, et boucle sur ce faux désaccord. Aucun « 10 » n'apparaît nulle part dans le prompt réel —
un artefact de transcription interne du modèle sur un long tableau numérique, pas une ambiguïté de
formulation qu'une phrase peut corriger.

**Correctif appliqué** (`llm_behavior_engine.py`, `build_positioning_system_prompt`) : une phrase
insérée entre la table des motifs et l'auto-vérification cid, précisant explicitement que le cid et
le motif sont deux informations indépendantes du même objet, pas des exigences concurrentes sur la
même liste — même forme que le correctif `chamber_deliberation`. Cible uniquement l'hypothèse 1 ;
aucune tentative de corriger l'artefact de transcription du cid=79 (pas actionnable par une
reformulation de prompt).

**Validation en direct, 2026-08-31** (`validate_campaign_positioning_disambiguation_fix.py`, mêmes
6 cid, 3 répétitions chacun, expérience `20260901T003657Z-0a0e4d59`) :

```
cid=184 [no-regression]:      0/3 troncature (avant : 0/2)
cid=167 [CIBLE DU CORRECTIF]: 0/3 troncature (avant : 2/2)
cid=126 [no-regression]:      0/3 troncature (avant : 0/2)
cid=79  [cause differente]:   0/3 troncature (avant : 3/3 -- 1 mesure initiale + 2 reproductions)
cid=209 [CIBLE DU CORRECTIF]: 0/3 troncature (avant : 2/2)
cid=158 [CIBLE DU CORRECTIF]: 0/3 troncature (avant : 2/2)

Cibles du correctif (167/209/158) : 0/9 troncature -- avant : 6/6.
```

**Le correctif fonctionne, franchement, sur les cas qu'il cible** : 0/9 contre 6/6 avant — le même
standard que la référence `chamber_deliberation` (7/7 → 0/7). C'est la première vraie victoire de
remédiation de tout ce chantier.

**Point à ne pas sur-interpréter** : `cid=79` (cause différente, non ciblée par ce correctif) est
AUSSI passé à 0/3, contre 3/3 avant sur trois mesures indépendantes. C'est notable, mais **pas une
preuve que l'artefact de transcription est réparé** — n=3 après correctif est un échantillon trop
petit pour trancher, et rien dans le correctif ne devrait mécaniquement affecter la façon dont le
modèle recopie un tableau de 20 nombres. Traité comme un résultat encourageant à surveiller, pas
comme un second correctif validé. Ne pas écrire dans la documentation de production que l'artefact
cid=79 est résolu tant qu'une mesure dédiée, à plus grand n, ne l'a pas confirmé.

### `chamber_deliberation`

3 membres à `chamber_position == sincere_position` (l'état que le prompt lui-même prescrit
explicitement : `shifts=[]`, `motif=701`) vs 3 membres avec un écart déjà présent (+0,3 sur une
dimension) — `think=True`, `size=1` **= la vraie taille de production** (`_CHAMBER_MAX_CHUNK_SIZE=1`
déjà, confirmé, pas un écart comme les deux ci-dessus).

```
IDENTIQUE:  3/3 -> shifts=[], motif=701 (exactement la reponse prescrite par le prompt)
DERIVE:     3/3 -> shifts=[], motif=702 (DELIBERATIVE_SHIFT — incoherent : ce motif suppose un ajustement reel)
```

Le pôle IDENTIQUE est un vrai résultat de justesse (pas juste une signature de collapse) — 3/3
correspondent exactement à ce que le prompt prescrit explicitement pour cet état. Le pôle DÉRIVE
n'est PAS un collapse plat (le motif diffère bien du premier pôle, contrairement aux 4 cas déjà
confirmés) — mais il révèle une incohérence systématique, uniforme sur les 3 membres sans aucune
variation : `motif=702` (qui suppose « j'ai ajusté ma position ») couplé à `shifts=[]` (aucun
ajustement réel). Le modèle semble remarquer qu'il y a un écart existant (d'où le motif différent)
sans jamais le traduire en une décision réelle — une forme d'insensibilité au contenu plus étroite
qu'un collapse total, mais bien réelle et bien reproduite (3/3, aucune exception).

### `chamber_deliberation` — correction déployée, question comportementale non close

Historique de l'ancien validateur retiré (`_check_motif_coherence`, `scripts/
lot3_chamber_reliability_results.md`) relu avant toute correction, pas redécouvert
empiriquement : la règle retirée était **bidirectionnelle** (`shifts non-vide ⟺ motif==702`),
et le taux de faux rejet mesuré (9/10 puis 6/6) venait exclusivement d'UNE direction — un petit
ajustement réel (ex. `{"dimension": 4, "delta": 0.05}`) étiqueté `motif=701` (sincère) par le
modèle. L'incohérence trouvée ici est la direction **opposée** (`motif=702` avec `shifts` vide)
— jamais mise en cause par l'historique de faux rejets, puisque tous ces cas portaient sur
`motif=701`, hors du champ d'une règle resserrée à `motif==702 ⟹ shifts non-vide`. Cette règle
plus étroite ne peut donc pas reproduire le problème historique — vérifié par construction, pas
supposé.

**Correction déployée (2026-08-30, pas un rejet — un correctif d'étiquette a posteriori)** :
`decide_chamber_deliberation` (`llm_behavior_engine.py`) corrige `motif` de 702 vers 701 quand
`shifts` est vide, et journalise la correction explicitement (`ChamberBatchOutcome.
motif_corrected`, propagé dans le payload `chamber_deliberation` de `run_polity_simulation.py`)
— même discipline que `retry_sampling_varied` pour `cast_votes` : ne jamais laisser une
intervention corrective se confondre avec une décision de première main. Pas un rejet-et-relance
(le mécanisme qui a résolu l'incohérence `vote_cast`) parce que l'incohérence mesurée ici est
**systématique** (3/3, aucune variance) plutôt qu'intermittente — un rejet-et-relance sur un cas
sans vraie variance à exploiter risquerait de tourner en boucle sans converger, la même leçon
apprise cette semaine avec la mitigation nonce du cache-reuse. Et `chamber_deviation` (la seule
métrique qui compte) lit `shifts`/`chamber_position` directement, jamais `motif` — l'incohérence
ne corrompait aucun comportement de simulation, seulement la piste d'audit ; corriger l'étiquette
répare exactement ce qui est cassé sans toucher à ce qui fonctionne. Régression testée
(`test_decide_chamber_deliberation_corrects_motif_702_with_empty_shifts_to_701` et deux tests
frères confirmant que la correction ne touche NI un `motif=702` cohérent NI l'autre direction
historique, `motif=701` avec un petit shift réel).

**Ce qui reste ouvert, malgré la correction d'étiquette — ne pas classer ce point comme réglé.**
Le comportement sous-jacent n'est pas expliqué, seulement rendu inoffensif pour l'audit. Direction
précise, pas celle initialement supposée : `motif=702` **affirme** qu'un ajustement actif a eu
lieu, alors que `shifts=[]` montre qu'aucun n'a eu lieu — le modèle sur-déclare l'action dans
l'étiquette, il ne sous-déclare pas une action réelle. Uniforme sur les 3 membres testés (aucune
variance), donc probablement pas du bruit. Lien possible, non vérifié, avec le biais acte/réponse
caractérisé en parallèle dans ce même document : même dans un cas où le contenu réel de la
décision reste passif (aucun ajustement), le modèle semble malgré tout attiré par l'étiquette qui
*décrit* une réponse active plutôt que la sincère/passive — une préférence pour le cadrage actif
qui se manifeste jusque dans le choix du motif, indépendamment de ce que la décision produit
réellement. Reste à comprendre un jour, pas aujourd'hui.

**Ni l'un ni l'autre ne confirme ou n'infirme proprement la théorie acte/réponse.** Aucun des deux
ne montre le collapse plat des 4 cas déjà confirmés (sortie strictement identique quel que soit le
pôle) — mais aucun des deux ne se comporte non plus comme les 2 cas qui ne collapsent pas
(`candidacy_considered`/`party_nomination_choice`, correction fine et cohérente sur toute la
plage testée). Les deux méritent un suivi ciblé avant d'être classés d'un côté ou de l'autre —
non fait ici, signalé pour décision.

## Vérification du batching réel en production (2026-08-30, avant tout nouveau test)

Avant de tester l'effet du batching sur les 3 nouveaux cas, vérifié directement contre le code
si c'est même pertinent — pas présumé :

- **`representative_response`** : `decide_representative_response` **ne chunk jamais** — batches
  les titulaires en poste ce tick, « 0-or-1 today (president only) ». Le test à `size=1` de ce
  document **est** exactement la forme de production, pas une isolation artificielle. Batching
  hors sujet pour ce cas — le collapse trouvé reflète déjà le comportement réel.
- **`coalition_decision`** : `decide_coalition` ne chunk pas non plus, mais batches les partis
  répondants directement — « a handful at most, `parties.initial_count` » (livré : 5, donc
  jusqu'à ~4 répondants non-initiateurs en un seul appel réel). Le test de ce document à
  `size=1` est **plus petit** qu'un batch de production typique — écart non testé.
- **`reaction_to_event`** : `decide_reaction_to_event` chunk réellement via `chunk_voters` à
  `config.llm.max_batch_size` (25) — « population-wide... À `population_size=100` livré, exactement
  4 chunks de 25. » Le test de ce document à `size=1` est bien en dessous de l'échelle réelle —
  écart non testé.

**Conséquence** : le collapse de `representative_response` est confirmé représentatif de la
production tel quel. Ceux de `coalition_decision` et `reaction_to_event` restent à vérifier à
leur échelle de batch réelle avant de conclure qu'ils se comportent pareil en production —
non fait ici, priorité donnée au levier diagnostique ci-dessous.

## Affiner l'hypothèse causale — cible nommée vs ton adversarial (2026-08-30)

Deux lectures de la découverte restent non départagées : est-ce la simple **présence d'une
cible nommée** dans le contexte (peu importe le ton), ou spécifiquement le **cadrage
adversarial/de pression** (« contre », « pression ») ?

**Protocole pré-enregistré, avant tout appel** : reprendre `candidacy_considered` — le seul
cadrage testé qui NE collapse PAS — et lui ajouter une référence à une cible/un rival dans son
`ctx`, **sans aucun ton adversarial** (une information neutre, pas une opposition). Mêmes 5
citoyens à `ambition_score` extrêmement bas déjà testés (0,0069 à 0,0214), même isolation totale
(`size=1`, `think=False`).

- **Si ça casse quand même** (le citoyen se met à « déclarer » malgré une ambition quasi nulle) →
  la simple **présence d'une cible** suffit, indépendamment du ton — le ton adversarial n'est pas
  le facteur spécifique, c'est la structure relationnelle elle-même (avoir un point de référence
  externe nommé dans la décision).
- **Si ça ne casse pas** (le citoyen continue de « renoncer » correctement) → le **ton
  adversarial/de pression** est bien le facteur spécifique, pas la simple présence d'une cible —
  resserre l'hypothèse à quelque chose dans le vocabulaire/cadrage de pression lui-même, pas dans
  la structure relationnelle générique.

**Résultat, 2026-08-30** (`check_candidacy_target_reference_ablation.py`) : mêmes 5 citoyens à
`ambition_score` extrêmement bas, `ctx.current_officeholder` ajouté (une phrase purement
factuelle, « une information de contexte, pas une cible d'action ni un rival à affronter »),
`size=1`, `think=False`.

```
5/5 correct -- outcome=0 (renonce) pour les 5 citoyens, motif=204 a chaque fois, meme avec la reference neutre ajoutee
```

**La simple présence d'une cible nommée, sans ton adversarial, ne suffit pas à casser
`candidacy_considered`.** Deuxième lecture pré-enregistrée confirmée : **le ton adversarial/de
pression est le facteur plus spécifique**, pas la structure relationnelle générique
(« il existe une autre partie nommée dans mon contexte »). Resserre l'hypothèse : ce n'est pas
« toute décision avec une cible référencée risque le collapse », c'est quelque chose dans le
cadrage de PRESSION/OPPOSITION lui-même (le vocabulaire « pression », « contre », le fait que la
décision porte sur une action envers/contre l'autre partie plutôt que sur un simple fait la
concernant) qui semble en cause.

## Test décisif : `party_nomination_choice` — comparatif entre pairs, sans acteur externe, sans forme acte/réponse

Comparaison précise des deux prompts (`candidacy_considered` vs `coalition_decision`) : la
présence d'un acteur externe nommé (le profil complet de l'initiateur dans `coalition_decision`)
n'explique pas `representative_response`, dont le `ctx` (`ResponseContext`, vérifié directement
dans le code) ne référence aucun autre acteur du tout — juste des attributs propres à l'élu
(`legitimacy`, `mandate_dev`) et un signal agrégé (`street`). Reformulation plus fine, qui tient
sur les 4 cas confirmés : ce n'est pas la présence d'un acteur externe qui compte, c'est si la
décision est formulée comme un **acte/réponse** (agir, répondre, rejoindre, réagir — une
conséquence institutionnelle vis-à-vis de l'extérieur) plutôt qu'une **auto-évaluation contre un
seuil** (`candidacy_considered` : ambition suffisante pour se présenter, oui/non).

**Protocole pré-enregistré** : `party_nomination_choice` — vérité de référence réelle
(`select_party_nominee`, `simple_rules.py` : ambition_score maximale parmi les membres
éligibles). Ni acteur externe à enjeu (comparaison purement interne, entre les propres membres
du parti), ni forme acte/réponse (« choisis lequel », pas « décide s'il agit/répond/rejoint »).
Devrait, selon la nouvelle hypothèse, se comporter comme `candidacy_considered` (pas de
collapse), pas comme les 4 cas qui collapsent.

Slates construits à partir d'une population réelle (500 citoyens) et d'une formation de partis
réelle (`initialize_parties`/`assign_party_affiliation`, k-means déterministe, aucun LLM) — 5
partis, chacun avec son membre le plus ambitieux face aux 3 membres éligibles les moins
ambitieux (marge measurée 0,16 à 0,35 — la distribution `beta(2,8)` compresse les scores juste
au-dessus du seuil, donc la marge se mesure contre le pire du groupe, pas le second, pour rester
non ambiguë).

```
party=1: 459 (0,510) vs 293/134/484 (~0,31) -> AGREE
party=0: 67  (0,622) vs 396/32/333 (~0,31)  -> AGREE
party=4: 266 (0,658) vs 50/222/19 (~0,31)   -> AGREE
party=2: 39  (0,523) vs 217/468/242 (~0,31) -> AGREE
party=3: 344 (0,467) vs 349/36/328 (~0,31)  -> DISAGREE (choisit le MOINS ambitieux du groupe)
```

**4/5 (80,0%) — franchit le seuil pré-enregistré, mais pas un résultat aussi net que les 5/5 de
`candidacy_considered`.** Le seul désaccord porte sur le cas à la marge la plus faible (0,16) et
à l'ambition maximale la plus basse des 5 (0,467) — un cas réellement à la limite, pas un
collapse total (0% uniforme sur tous les cas, comme dans les 4 cas confirmés) : ici 4 cas
corrects couvrant une large plage de marges, un seul désaccord sur le cas le plus serré, vers un
choix incohérent (le pire du groupe, pas un intermédiaire plausible).

**`party_nomination_choice` ne collapse pas.** Confirme « acte/réponse vs seuil » comme le
facteur qui explique les 5 cas testés jusqu'ici (4 collapsent, 2 ne collapsent pas), là où
« acteur externe nommé » échouait sur `representative_response` et où « ton adversarial » laissait
`coalition_decision` non expliqué. Théorie retenue : **une décision formulée comme un acte ou une
réponse avec conséquence institutionnelle vis-à-vis de l'extérieur est à risque de collapse en
isolation ; une auto-évaluation contre un seuil (même comparative entre pairs) ne l'est pas** —
toujours une hypothèse de conception, pas une loi prouvée (5 cas, pas une preuve causale du
mécanisme).

**Nuance à garder** : `representative_response` et `coalition_decision` (les deux autres cas
confirmés collapsants, en plus de `pressure_action`) sont-ils vraiment « adversariaux » au même
titre que `pressure_action` ? `representative_response` répond à une pression déjà reçue (pas une
action offensive) ; `coalition_decision` est une décision de coopération/négociation (rejoindre
une coalition), pas d'opposition. Si le facteur commun est bien « pression/opposition » au sens
strict, `coalition_decision` en particulier reste à expliquer — sa décision n'a rien
d'adversarial au sens littéral, seulement relationnel/stratégique. Ce point n'a pas été creusé
davantage ici ; à traiter avant de considérer l'hypothèse « ton adversarial » comme complète.

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
