# Plan — Résolution du collapse `pressure_action` (voie tout-LLM)

> ## ⚠️ CE PLAN EST INVALIDÉ DANS SA PRÉMISSE — 2026-08-31
>
> **Il n'y a pas de collapse `pressure_action`.** Toutes les mesures de ce
> document (§2.1, §2.3, §2.4, et les §0 qui reprennent §3.1/§3.2) ont tourné
> sous le menu constitutionnel **livré** — `electoral_only: true`,
> `petition_enabled: false`, `mobilization_enabled: false` — où
> `menu_acts()` renvoie `(0, 4)` et où le prompt de production déclare
> « CONTRAINTE ABSOLUE : le champ act doit valoir UN DES CODES SUIVANTS,
> et aucun autre : **[0, 4]** ». Les codes d'action 1/2/3 sont **interdits
> par conception**, et la vérité de référence du harnais les exigeait
> quand même. Ces runs mesuraient une impossibilité, pas un comportement —
> ce qui explique aussi pourquoi §3.1 et §3.2 « échouaient identiquement à
> 17/70 » : ils comptaient la même contrainte.
>
> **Mesure décisive, menu ouvert, mêmes 70 citoyens, même prompt de
> production** (`check_pressure_action_open_menu_baseline.py`) :
> **29/70 codes d'action émis** (NOTHING 40, SIGN_PETITION 27, MOBILIZE 2,
> WAIT_FOR_ELECTION 1), pôle « devrait agir » à **9/17 (52,9 %)** contre
> 0/17 sous menu fermé. Le modèle utilise les leviers dès qu'ils sont
> légaux.
>
> **Ce qui reste vrai** : la justesse est médiocre (60,0 % d'accord global
> contre une barre à 80 %) — indépendamment cohérent avec la seule mesure
> toujours valide, le pilote d'origine (41,7 % de désaccord, ≈ 58 %
> d'accord), qui lui ouvre le menu explicitement. Le vrai chantier est
> donc **la qualité de décision**, pas un collapse.
>
> Les conclusions négatives des §2.1/§2.3/§2.4 ne disent rien : elles
> testaient si un ajustement de prompt pouvait faire émettre un code
> interdit. Ne pas s'en servir pour écarter température, contrainte
> grammaticale ou few-shot — ces pistes sont **non testées**, pas écartées.

> Document de scoping, à valider avant toute implémentation.
> **Objectif assumé** : faire fonctionner le chemin LLM, pas basculer sur
> un repli déterministe. Le déterminisme reste le baseline de comparaison
> (§3.1 du plan de conception), pas la solution visée.
>
> **Principe directeur** : instrumenter avant de tester, tester isolément
> avant de combiner, combiner seulement ce qui montre un signal. Empiler
> des mitigations non mesurées ne multiplie pas les chances de succès —
> ça rend le résultat non attribuable et non débogable, exactement
> l'erreur déjà payée avec le nonce cette semaine.

---

## 0. État de la connaissance (établi, ne pas retester)

**Écarté comme cause, avec preuve :**
- Position dans le batch (permutation × 2, même résultat).
- Taille de batch (0/63 codes d'action même à `size=1`, y compris
  `cid=6` à ratio 4,226 — le cas le plus extrême du jeu de données).
- La phrase de cadrage « 0 et 4 sont des résultats légitimes » comme
  cause **suffisante isolée** (ablation, 0 flip sur 5 cas, témoin
  inclus) — pas exonérée comme facteur contribuant.
- Structure du menu (binaire-puis-levier, §3.1) — échec à 24,3 %.
- Mécanisme de production de la sortie (langage primaire, §3.2) — échec
  au taux **identique**, 24,3 %.
- La suppression totale du raisonnement sous `think=True`/`size=1` est
  un **artefact de cette configuration jamais utilisée en production**
  (`candidacy_considered`, immunisé au collapse réel, la reproduit aussi
  8/8) — pas un symptôme du mécanisme acte/réponse.
- **Perturbation de température à 0,3** (`plan-pressure-action-
  remediation.md` §2.1) — 0/4 cas basculés, décodage glouton écarté
  comme facteur à cette valeur. `temperature=0,7` reste non testé.
- **Ordre de présentation des options** (`plan-pressure-action-
  remediation.md` §2.2) — table réordonnée (codes d'action en premier,
  NOTHING/WAIT en dernier), 0/4 cas basculés, effet de primauté/récence
  écarté. **Correction de ce document** : la §2.2 initiale de ce plan
  qualifiait cette piste de « jamais testée », ce qui était faux —
  présenter un résultat négatif propre déjà obtenu comme une piste
  vierge est exactement l'erreur que ce chantier essaie d'éviter.
  Retirée de la Phase 2 ci-dessous (doublon strict, aucune information
  nouvelle à en attendre).

**Bloqué techniquement :**
- §3.4 (réordonnancement du schéma, raisonnement avant décision) :
  `json.dumps(sort_keys=True)` dans `llm_client.py` alphabétise
  récursivement tout le corps de requête, y compris le schéma passé en
  `format`. Le contournement toucherait du code partagé par tous les
  types de décision — scoping séparé requis, cf. §4 de ce document.

**Portée du problème :**
- 4/4 types de décision à cadrage relationnel/acte-réponse collapsent
  (`pressure_action`, `representative_response`, `coalition_decision`,
  `reaction_to_event`) ; le seul type purement seuil testé
  (`candidacy_considered`) ne collapse pas.
- Cross-modèle : `qwen3:8b` et `mistral:7b` collapsent tous deux, vers
  des pôles **opposés** — argument en faveur d'une cause structurelle
  (forme de la tâche) plutôt qu'un biais de contenu appris.

---

## 1. Phase 1 — Instrumentation (avant tout nouveau test)

**Rationale** : plusieurs tests de cette investigation ont produit des
résultats ininterprétables faute d'instrumentation (le premier test de
`campaign_positioning`, le piège `message.reasoning` découvert
tardivement, la sur-généralisation du script `think=True` attrapée de
justesse). Aucun nouveau test ne doit être lancé tant que ces points
ne sont pas en place.

### 1.1 Capture systématique de la réponse brute complète
- Dumper **l'intégralité du JSON de réponse** (pas seulement
  `content` — inclure `message.reasoning`, `finish_reason`,
  `done_reason`, compteurs de tokens) pour chaque appel de test.
- Rappel du piège déjà documenté : `_extract_content` ne lit que
  `content` ; une exception de troncature ne porte aucun raisonnement.

### 1.2 Capture du corps de requête réellement envoyé
- Dumper le corps de requête **après** sérialisation (post
  `json.dumps`), pas la structure Python avant envoi — c'est
  précisément ce qui a permis de découvrir le tri alphabétique du
  schéma. Toute manipulation de prompt/schéma doit être vérifiée sur ce
  qui part réellement sur le fil, jamais sur l'intention.

### 1.3 Journalisation enrichie par décision testée
Pour chaque appel, enregistrer dans un format structuré (SQLite via le
harnais existant, ou CSV à défaut) :
- Entrées : `self_gap`, `blank_threshold`, ratio, `mandate_dev`,
  `neighbors_acting`, `ticks_to_election`, taille de chunk, position
  dans le chunk.
- Sortie : `act`, `motif`, texte de raisonnement complet, ordre réel
  d'apparition des champs dans le JSON brut.
- Contexte : variante testée (température, ordre du menu, few-shot,
  etc.), horodatage, hash du commit.

Objectif : pouvoir requêter *a posteriori* « tous les cas où le ratio
dépassait 1,5 et où le modèle a répondu 0 », sans relancer un test.

### 1.4 Correction du bug `neighbors_acting=null`
Déjà identifié : le modèle interprète `null` comme « aucun voisin
actif » alors que la sémantique est « non suivi ». Corriger la
formulation dans le prompt (ou ne pas transmettre le champ du tout
quand le graphe social est désactivé) — c'est un vrai bug de
compréhension du contexte, indépendant du collapse, et il pollue toute
lecture de raisonnement produite pendant les tests.

---

## 2. Phase 2 — Batterie de tests isolés (une variable à la fois)

**Protocole commun, non négociable :**
- Chaque variante est **pré-enregistrée** (hypothèse causale + critère
  de succès + critère d'échec) avant tout appel.
- Échantillon minimum **60 citoyens non ambigus** (le point où le taux
  s'est stabilisé lors du sweep étendu — plancher, pas cible).
- Cas extrêmes des **deux pôles** systématiquement inclus (jamais un
  échantillon à sens unique — erreur déjà attrapée une fois).
- Une seule variable change par test, le reste strictement identique au
  chemin de production.

### 2.1 Perturbation de température — extension à 0,7 *(0,3 déjà écarté)*
**Statut corrigé** : `temperature=0,3` a déjà été testée
(`plan-pressure-action-remediation.md` §2.1) et écartée (0/4 cas
basculés). Ce n'est pas une piste vierge — **attente de succès faible**,
pré-enregistrée comme telle. Testée quand même parce que le coût est
quasi nul (5 appels) et que `0,7` reste un point non couvert.

**Hypothèse** : le collapse est en tout ou partie un artefact de
décodage glouton (une trajectoire de tokens dominante à `temperature=0`),
et `0,3` n'a pas suffi à le perturber mais un écart plus grand
pourrait. Précédent dans ce projet : `temperature=0,3` au retry a cassé
une boucle déterministe sur `vote_cast` (§3.6.1) — mais un précédent
positif à `0,3` sur un AUTRE type de décision n'a déjà pas transféré à
`pressure_action` une fois testé, donc l'attente reste modeste ici,
pas nulle.

**Protocole** : mêmes cas, `size=1`, `temperature=0,7`, prompt de
production inchangé, via `pressure_action_harness.py` (capture complète
requête/réponse/raisonnement).

**Critère** : des codes d'action apparaissent, cohérents avec la vérité
de référence, sur les cas extrêmes « devrait agir » → composante de
décodage réelle malgré l'échec à 0,3, piste à creuser. Aucun changement
→ décodage glouton définitivement écarté à toute température
raisonnable, ne pas retester à d'autres valeurs sans nouvelle
justification.

**Résultat, 2026-08-31** (`resolution_2_1_temperature_0_7.py`, expérience
`20260831T230900Z-cc92c474`) :

```
cid=6   expected=True  act=0 NOTHING          DISAGREE
cid=152 expected=True  act=0 NOTHING          DISAGREE
cid=270 expected=True  act=4 WAIT_FOR_ELECTION DISAGREE
cid=146 expected=True  act=4 WAIT_FOR_ELECTION DISAGREE
cid=158 expected=False act=0 NOTHING          AGREE
1/5 (20,0%)
```

**0/4 cas « devrait agir » basculés, même signature qu'à 0,3.**
Décodage glouton écarté définitivement, à 0,3 comme à 0,7 — pas de
piste à creuser ici. Confirme l'attente faible pré-enregistrée.

### 2.2 Ordre de présentation des options — RETIRÉ de la Phase 2, déjà tranché (§0)

Testé avec le protocole exact décrit ici
(`plan-pressure-action-remediation.md` §2.2) : table réordonnée, 0/4 cas
basculés, effet de primauté/récence écarté. Aucune variable nouvelle
dans ce que cette section proposait — relancer serait un doublon strict.
Voir §0 pour le résultat complet.

### 2.3 Retrait de la contrainte grammaticale *(jamais testé — issu de Tam et al. 2024)*

**Protocole clarifié, 2026-08-31** : le protocole initialement écrit ici
(« alléger la description du schéma dans le prompt, garder le
décodage contraint ») ne correspond pas à ce que l'article cité compare
réellement — le prompt de production actuel n'injecte déjà quasiment
aucun texte de schéma (juste la phrase CONTRAINTE ABSOLUE et les
tables act/motif en langage naturel), donc « alléger » ce texte a peu
de prise. Retenu à la place, la comparaison réelle de l'article : schéma
contraint (`format=json_schema`, décodage par grammaire) **vs** simple
consigne « réponds en JSON » en prose, sans contrainte structurelle,
avec parsing tolérant côté client. Structurellement différent de §3.2
(texte libre non-JSON, `SITUATION:`/`DECISION:`/`MOTIF:`) — ici la
sortie reste un objet JSON, juste sans grammaire imposée par Ollama.

**Hypothèse** : le papier `Let Me Speak Freely?` (Tam et al. 2024)
mesure qu'un schéma strict imposé au décodage dégrade davantage qu'une
simple consigne de format — sur GSM8K, la suppression de la contrainte
de schéma améliore la moyenne et réduit la variance entre variantes de
prompt, sur plusieurs modèles. Chiffres non repris ici comme
justification (non vérifiables pour ce contexte précis) — seule la
distinction mécanique (contrainte grammaticale vs consigne libre)
motive ce test.

**Protocole** : même prompt système de production (menu à 5 voies,
mêmes explications ctx), remplace la contrainte `format` par une
instruction en prose demandant un objet JSON avec les clés
`cid`/`act`/`motif`/`target`, sans schéma structurel imposé au
décodage. `size=1`, `think=False`, `température=0,0`, mêmes 70 citoyens
que §3.1/§3.2. Parsing tolérant côté client (extraction JSON depuis la
réponse texte, comme pour tout LLM non contraint) — un échec de parsing
est un résultat à enregistrer, pas une exception à ignorer.

**Critère** : réduction du taux de collapse (accord ≥ 60 % avec la
vérité de référence sur cas non ambigus, sous la barre de 80 % des
pistes précédentes puisque le parsing tolérant introduit sa propre
marge d'erreur) → le décodage par grammaire contrainte est un facteur
réel ; sinon écarté.

**Résultat, 2026-08-31** (`resolution_2_3_no_grammar_constraint.py`,
expérience `20260831T230900Z-9e2f9246`) :

```
parse failures: 0/70
checked: 70/70
raw agreement (both poles): 53/70 (75,7%)
should-act subset only: 0/17 (0,0%)
```

**Le critère mécanique tel qu'écrit est passé (75,7 % ≥ 60 %), mais ce
n'est PAS un signal positif — c'est un artefact de déséquilibre de
classe que la pré-inscription n'avait pas anticipé.** 0 des 70 réponses
n'a jamais émis un code d'action (1/2/3) : les 70 sorties sont
`act=0 NOTHING`, sans une seule exception. Le sous-ensemble « ne devrait
pas agir » (53/70 citoyens) obtient trivialement 100 % sous une
politique « toujours NOTHING », ce qui pousse seul le taux brut à
75,7 % — c'est numériquement identique à ce que produirait un modèle qui
ignore entièrement `ctx`. Le sous-ensemble informatif, « devrait agir »
(17/70), est à 0 % — la même signature de collapse (17 cas, échec
complet) que `plan-pressure-action-remediation.md` §3.1/§3.2, sur le
même jeu de 70 citoyens harvesté. Retirer la contrainte grammaticale ne
change rigoureusement rien à l'output du modèle sur ce test.

**Correction méthodologique à retenir** : un critère d'accord brut sur
un jeu de test déséquilibré est mal posé quand l'hypothèse nulle
(réponse triviale, invariante à `ctx`) peut à elle seule dépasser le
seuil. Le sous-ensemble « devrait agir » est la seule mesure valide ici
et pour toute future piste testée sur ce même jeu de 70 — à corriger
dans le pré-enregistrement de §2.4 avant de le lancer (voir critère
révisé ci-dessous). **§2.3 est donc écarté** : pas de piste à creuser,
n'entre pas en Phase 3.

### 2.4 Few-shot avec exemples travaillés *(§3.3, scopé jamais exécuté)*
**Hypothèse** : le prompt décrit une règle abstraite mais ne montre
aucun précédent concret d'un cas extrême recevant correctement un code
d'action.

**Protocole** : 2 exemples travaillés dans le prompt (un « devrait
agir », un « ne devrait pas »), montrant un citoyen à ratio extrême
recevant le code d'action correct avec son motif — construits sur le
**vrai schéma de production**, valeurs réelles du jeu de 70 citoyens
déjà harvesté (§3.1), pas inventées.

**Règle de sélection fixée avant tout appel, pour éviter le fishing sur
le choix des exemples** : les 2 citoyens au ratio le plus extrême de
chaque côté (le plus haut pour « devrait agir », le plus bas pour « ne
devrait pas ») parmi les 70 — un critère mécanique, pas un choix
discrétionnaire. Retirés du jeu de test pour cette piste (68 restants,
toujours au-dessus du plancher de 60, §4.1) pour ne jamais évaluer le
modèle sur les cas mêmes qu'il a vus en exemple.

**Critère, corrigé après §2.3** : ≥ 80 % d'accord sur les 68 cas restants
ET une amélioration réelle sur le **sous-ensemble « devrait agir »
seul** (16 des 68, les deux exemples retirés étant un par pôle) par
rapport au 0 % mesuré en §2.3 sur ce même pôle. Le taux brut sur les 68
cas mélange à nouveau les deux pôles ; §2.3 a montré qu'un collapse
total (0 code d'action jamais émis) peut à lui seul produire ~76 % —
sous la barre de 80 % ici, donc moins trompeur qu'en §2.3, mais pas
suffisant en soi : un score ≥ 80 % obtenu avec un sous-ensemble
« devrait agir » toujours à 0 % ne serait pas un ancrage réel, seulement
un déséquilibre de classe légèrement moins favorable au collapse.
Vérifier explicitement qu'au moins un code d'action (1/2/3) apparaît
avant de qualifier ce résultat de signal.

⚠️ **Attention méthodologique sur cette piste** : le choix des exemples
est lui-même un degré de liberté. Fixer les exemples **avant** de voir
le résultat (règle mécanique ci-dessus, pas un choix a posteriori), ne
pas les ajuster après coup pour améliorer le score — sinon c'est du
fishing déguisé.

**Résultat, 2026-08-31** (`resolution_2_4_few_shot.py`, expérience
`20260831T230900Z-05bb4cc9`) :

```
exemples sélectionnés : should_act=cid74 (ratio=7,39), should_not_act=cid173 (ratio=0,13)
checked: 68/68
raw agreement (both poles): 52/68 (76,5%)
should-act subset only: 0/16 (0,0%)
acting codes ever emitted: NONE
```

**Négatif, sans ambiguïté, sur les deux critères.** Le taux brut
(76,5 %) est déjà sous la barre naïve de 80 % — contrairement à §2.3, il
n'a même pas besoin de la correction méthodologique pour être écarté.
Le sous-ensemble informatif confirme : 0/16 « devrait agir » corrects,
et **aucun code d'action (1/2/3) n'a jamais été émis sur les 68 appels**
— y compris face à deux exemples travaillés montrant explicitement,
dans le contexte immédiat, qu'un cas à ratio extrême doit recevoir
`act=2, motif=301`. L'ancrage par précédent concret ne change
rigoureusement rien : même signature de collapse totale que §2.3 et que
`plan-pressure-action-remediation.md` §3.1/§3.2. **§2.4 est écarté.**

---

## 3. Phase 3 — Combinaisons (conditionnelles, pas systématiques)

**Constat, 2026-08-31 : la règle d'entrée n'est pas remplie, cette phase
ne s'ouvre pas.** Les trois tests de la Phase 2 sont négatifs : §2.1
(0,7) 1/5 sans amélioration sur le pôle informatif, §2.3 (retrait
grammaire) 0/17 sur le pôle « devrait agir », §2.4 (few-shot) 0/16 sur
le même pôle, aucun code d'action jamais émis dans ces deux derniers
tests malgré l'absence de contrainte de schéma et malgré deux exemples
travaillés explicites. Aucune des trois pistes ne montre le moindre
mouvement vers la vérité de référence, même incomplet — pas seulement
« insuffisant », mais **nul** (0 % sur le sous-ensemble informatif dans
les deux pistes réellement neuves). Il n'y a rien à combiner : combiner
trois pistes à effet individuel strictement nul ne peut produire un
effet combiné réel, seulement du bruit non attribuable — exactement ce
que la règle d'entrée ci-dessous existe pour éviter.

**Règle d'entrée** : une piste n'entre en combinaison que si elle a
montré, seule, un **signal positif partiel** (mouvement réel vers la
vérité de référence, même incomplet).

**Justification** : combiner deux mitigations sans effet individuel
n'augmente pas la probabilité de succès — ça rend le résultat non
attribuable (impossible de savoir laquelle agit) et non débogable (rien
à isoler si le comportement change plus tard). C'est exactement le
risque payé avec le nonce cette semaine : une mitigation jamais isolée
proprement a interagi avec l'état du cache d'une façon imprévue.

**Ordre** :
1. Paires d'abord (la plus prometteuse × la deuxième), jamais les
   trois d'emblée.
2. Chaque combinaison pré-enregistrée comme un test à part entière,
   même critère d'échantillon (n ≥ 60).
3. Si une combinaison réussit : vérifier qu'elle tient sur un
   **échantillon indépendant** (autres graines) avant tout déploiement
   — le taux de 25 % devenu 41,7 % en doublant l'échantillon reste
   l'avertissement de référence.

---

## 4. Phase 4 — Débloquer §3.4 (scoping séparé, conditionnel)

À n'ouvrir **que si** les phases 2-3 échouent toutes, et jamais comme
raccourci en cours de route.

Question à trancher par écrit avant tout code : peut-on exclure le
schéma (`format`) du tri alphabétique **sans** compromettre la
reproductibilité byte-à-byte des requêtes que `sort_keys=True` protège
pour tous les types de décision ?

Options à évaluer (non tranchées ici) :
- Sérialiser le schéma séparément, hors du corps trié.
- Utiliser une structure ordonnée qui survit au tri (renommage des clés
  pour que l'ordre alphabétique **soit** l'ordre voulu — ex. préfixes
  `a_reasoning`, `b_act` — hack visible mais non invasif et
  réversible ; à évaluer sérieusement, c'est de loin le moins coûteux).
- Exception ciblée documentée dans `llm_client.py`.

⚠️ Cette phase touche du code partagé par **tous** les types de
décision — impact sur la reproductibilité à mesurer explicitement,
pas supposé.

---

## 5. Ce que ce plan ne fait pas

- **Ne bascule pas `pressure_action` sur le repli déterministe.** Choix
  assumé, cohérent avec l'objectif tout-LLM — mais à noter : les quatre
  types relationnels restent marqués non fiables en production tant
  qu'aucune piste n'a abouti, et un run d'acceptance produit pendant
  cette période porte ce défaut connu.
- **N'applique aucune mitigation « au cas où »** sans mesure. Chaque
  changement conservé doit avoir un effet attribuable, sinon il devient
  une dette non débogable.
- **Ne traite pas les trois autres types relationnels** — le protocole
  établi ici leur sera applicable une fois une piste validée sur
  `pressure_action`, pas en parallèle.

## 6. Sortie attendue

1. Phase 1 complète (instrumentation) — diff présenté avant application.
2. Les **trois** pré-enregistrements de la Phase 2 (température 0,7 —
   extension marginale — allègement du schéma, few-shot ; l'ordre des
   options est retiré, déjà tranché négativement en §0), écrits
   **avant** tout appel, présentés ensemble.
3. Résultats des trois tests isolés, chacun confronté à son propre
   critère, présentés avant toute combinaison.
4. Décision explicite : piste retenue, combinaison justifiée, ou constat
   d'échec des trois pistes → passage à la Phase 4 (scoping §3.4).

**Note honnête sur la portée réelle** : cette phase ne teste que deux
vraies pistes neuves (§2.3, §2.4) plus une extension marginale à faible
attente de succès (§2.1 à 0,7) — pas quatre pistes vierges comme la
version initiale de ce document le laissait entendre. L'espace des
mitigations bon marché déjà identifiées est presque épuisé ; mieux vaut
le dire explicitement que de maintenir un compte artificiellement élevé.

**Constat final, 2026-08-31** : les trois tests sont exécutés et
négatifs (voir §2.1/§2.3/§2.4 pour le détail). Phase 3 ne s'ouvre pas
(§3, règle d'entrée non remplie). Conformément au point 4 ci-dessus,
ceci constate l'échec des trois pistes de la Phase 2 — la Phase 4
(scoping séparé de §3.4) devient la seule voie encore identifiée, mais
n'est **pas ouverte par ce constat lui-même** : §4 est explicite qu'elle
ne doit jamais être un raccourci pris en cours de route, et sa propre
question de cadrage (exclure `format` du tri alphabétique sans
compromettre la reproductibilité byte-à-byte partagée par tous les
types de décision) n'a reçu aucun début de réponse ici. Décision de
l'ouvrir, et quand, laissée à l'utilisateur.

**Où en est la fiabilité de `pressure_action` à l'issue de ce plan** :
inchangée par rapport à l'état décrit dans le RELIABILITY WARNING de
production (`llm_behavior_engine.py`) — le collapse spécifique aux cas
« devrait agir » reste entier et non expliqué. Ce que ce plan ajoute :
trois causes mécaniques plausibles explicitement écartées par la
mesure (décodage glouton/température, contrainte grammaticale de
décodage, absence de précédent concret en contexte), qui ne sont donc
plus à retester sans nouvelle justification.
