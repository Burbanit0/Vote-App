# Plan — Calibration candidature (ADR-002, moitié restante)

> Document de scoping, à discuter et amender avant toute implémentation.
> Suite directe d'ADR-002 (moitié visibilité déjà close, commit
> `218d1d6`). Objectif : trancher pourquoi la configuration livrée
> (`ambition_threshold=0.7`, `ambition_dist=beta(2,8)`,
> `rupture_path_enabled=false`) ne produit jamais de candidat, et quoi
> corriger — avec la même discipline que le chantier de distribution
> (décision théorique avant chiffre, critère pré-enregistré avant sweep).

---

## 0. Rappel du problème et de son coût déjà chiffré

- Au seuil livré, 0,03 citoyen éligible sur 100 en moyenne — 39 graines
  sur 40 sans aucun candidat, indépendamment de `position_dist`.
- `rupture_path_enabled: false` ferme la seule voie de secours : il n'y a
  aucun autre chemin de candidature possible.
- Coût déjà connu de toute correction touchant `ambition_dist` ou le flux
  RNG de `generate_population` : au moins une preuve de byte-identité
  (`test_blank_vote_competitive_enabled_but_never_triggered_...`) devra
  être reconstruite sur un autre mécanisme, plus trois autres tests qui
  dépendent implicitement du défaut actuel.
- Tous les scripts d'acceptance à ce jour contournent le problème via
  `dataclasses.replace(..., ambition_threshold=0.0)` — aucun résultat
  publié n'a jamais exercé la valeur livrée.

## 1. Trancher d'abord la question la moins chère : `rupture_path_enabled` était-il l'accident ?

**Avant tout débat théorique sur la calibration**, vérifier l'hypothèse
la moins coûteuse nommée dans ADR-002 : peut-être que `decide_candidacy`
n'a jamais été censé être le seul chemin, et que c'est
`rupture_path_enabled: false` qui est l'anomalie de configuration, pas
`ambition_threshold`.

**Test à faire, avant toute autre chose** :
- Relire §2.4 du plan de conception (`polity-simulation-design.md`) :
  le chemin de rupture y est explicitement décrit comme rare et
  probabiliste (`rupture_base_probability: 0.001`, un tirage par
  citoyen et par tick), pas comme un substitut au chemin dominant.
  Confirme si cette lecture tient toujours, ou si une relecture plus
  attentive suggère que le chemin de rupture devait être actif par
  défaut dès la v1.
- Si `rupture_path_enabled: true` est activé seul (sans toucher
  `ambition_dist`/`ambition_threshold`), une sonde déterministe sur les
  mêmes 40 graines : est-ce que ça suffit à produire des élections dans
  une fraction raisonnable des runs ?

**Si cette piste suffit** : c'est la correction la moins chère de
toutes — un seul flag de config, aucun changement au flux RNG de
`generate_population`, aucune preuve de byte-identité à reconstruire
(le test cité dépend d'`ambition_threshold`, pas de `rupture_path_enabled`
— à vérifier explicitement, pas supposer). Documenter et clore ADR-002
sans toucher à la calibration si c'est le cas.

**Si cette piste ne suffit pas ou est théoriquement écartée** (§2.4 est
clair sur le caractère volontairement rare de ce chemin) → passer à la
Phase 2.

### 1.1 Résultats Phase 1 (2026-08-29) — piste écartée, et elle n'était même pas la moins chère

**Relecture de §2.4 : la lecture d'ADR-002 tient, et elle est plus nette
qu'annoncée.** Le plan de conception oppose explicitement les deux chemins :
le dominant est « **le chemin normal** », le second est « chemin **rare** […]
avec une probabilité volontairement très faible — parce que la majorité des
citoyens en désaccord n'agit pas », et les deux « produisent […] des
candidatures protestataires **peu nombreuses** ». Rien dans §2.4 ne suggère
que le chemin de rupture ait jamais été pensé comme actif par défaut : il est
défini *par contraste* avec le chemin dominant, qu'il présuppose donc vivant.

**Sonde déterministe** (scratchpad, non commitée — même convention que la
sonde d'ADR-002). Protocole du §2 du chantier distribution : graines 1..40,
`run_simulation` de bout en bout, moteur déterministe (pas de LLM), durée
livrée (30 ans = 121 ticks, 8 présidentielles par run = **320 élections**),
trois bras mesurés dans la même exécution. Compté depuis le journal lui-même,
jamais redérivé de la config.

| Bras | Élections | avec vainqueur | champ candidat VIDE | candidats mais Blanc l'emporte | runs sans aucun élu |
|---|---|---|---|---|---|
| A — livré (`rupture: false`) | 320 | 8 (2,5 %) | **312 (97,5 %)** | 0 | **39/40** |
| B — livré + `rupture: true` | 320 | **212 (66,3 %)** | **86 (26,9 %)** | 22 (6,9 %) | **0/40** |
| C — `ambition_threshold=0.0` | 320 | **320 (100 %)** | 0 | 0 | 0/40 |

Le bras A reproduit exactement ADR-002 (39/40 graines stériles) : la sonde est
donc calibrée sur un résultat déjà publié avant d'être lue sur le bras B.

**Candidats en lice par élection**, et par quel chemin ils sont arrivés :

| Bras | 0 cand. | 1 | 2 | 3 | 4 | 5 | 6 | déclarations par chemin |
|---|---|---|---|---|---|---|---|---|
| A | 312 | 8 | — | — | — | — | — | dominant 8 |
| B | 86 | 102 | 70 | 39 | 20 | 2 | 1 | **rupture 476, dominant 8** |
| C | — | — | — | — | — | 320 | — | dominant 1600 |

**Verdict : la piste est écartée, sur trois motifs indépendants.**

1. **Elle ne restaure pas le chemin dominant, elle le remplace.** 476
   candidatures de rupture contre 8 dominantes : **98,3 % des candidatures
   deviennent protestataires**, l'exact inverse de la proportion que §2.4
   décrit. Le total de nominations de parti est **inchangé par rapport au bras
   A — 8, toutes issues de la seule graine où un citoyen franchit 0,7** :
   activer la rupture n'ajoute pas un seul candidat par le chemin dominant, par
   construction. Sur 312 des 320 élections, `select_party_nominee` renvoie
   `None` pour les cinq partis, donc le mécanisme de nomination (§2.3) et le
   point de décision LLM qui l'arbitre (§3.6.3) restent **inertes**. Or c'est
   précisément ce mécanisme que la question 2 du §2.1 ci-dessous cherche à
   rendre non vide.
2. **Elle ne résout pas non plus le symptôme.** 86 élections sur 320 (26,9 %)
   n'ont toujours **aucun candidat**, et 188/320 (58,8 %) en ont zéro ou un —
   c'est-à-dire une ratification sans opposition. Le « 0/40 runs stériles » est
   un artefact de cadrage : à l'échelle du run, un seul candidat sur huit
   scrutins suffit à masquer sept scrutins vides. **La bonne unité d'analyse
   est l'élection, pas le run** — conséquence directe pour le critère
   pré-enregistré du §2.2, qui était formulé au niveau du run.
3. **Le seuil de signatures est inerte, donc C1 n'est pas non plus « résolue »
   à la taille de population livrée.** `sympathizer_ratio` itère sur toute la
   population **y compris le citoyen lui-même** (`weighted_distance(c, c) = 0 ≤
   c.blank_threshold`), donc le ratio vaut au minimum `1/100 = 0,01`, toujours
   ≥ `rupture_signature_ratio: 0.005`. Le garde-fou d'accès au bulletin ne peut
   donc rejeter personne à `population_size: 100` — et c'est mesuré, pas déduit :
   sur les 40 mêmes graines, **477 495 tirages, 476 succès au pile-ou-face,
   476 passages du seuil de signatures — zéro rejet**. Le chemin de rupture est,
   à la configuration livrée, un pur pile-ou-face ; la « RÉSOLUTION C1 »
   annoncée dans le YAML ne mord pas.

**Et l'hypothèse de coût du §1 est fausse — vérifiée, pas supposée.** Le plan
supposait « aucune preuve de byte-identité à reconstruire (le test cité dépend
d'`ambition_threshold`, pas de `rupture_path_enabled` — à vérifier
explicitement) ». Vérification : suite complète relancée avec la seule ligne
`rupture_path_enabled: true` (plugin pytest qui redirige
`_DEFAULT_CONFIG_PATH` vers une copie temporaire — rien de modifié dans le
dépôt) → **7 tests échouent**, dont
`test_blank_vote_competitive_enabled_but_never_triggered_..._byte_for_byte`.
Raison : ce test ne dépend pas d'`ambition_threshold`, il dépend de
`nominees == []`, et **les deux corrections détruisent cette propriété
également**. La piste « rupture » n'a donc aucun avantage de coût sur les
options de calibration : même rayon d'explosion (7 tests contre 7, voir §3.1),
pour un résultat théoriquement écarté et empiriquement insuffisant.

→ **Passage en Phase 2.** ADR-002 ne peut pas être close par sa quatrième
lecture.

## 2. Cadrage théorique de la calibration, si la Phase 1 ne suffit pas

**Principe directeur, identique à celui du chantier distribution** : ne
pas choisir la valeur qui fait disparaître le symptôme le plus vite (un
seuil à 0.0 "parce que ça marche" reviendrait à graver le contournement
déjà utilisé partout). Choisir une calibration défendable, puis vérifier
qu'elle résout aussi le problème empirique.

### 2.1 Ce qu'il faut décider, dans l'ordre

1. **La forme de `ambition_dist` est-elle le problème, ou seulement son
   échelle ?** `beta(2,8)` a une moyenne théorique de 0,2 — poser la
   question suivante avant de changer quoi que ce soit : cette forme
   (la plupart des citoyens peu ambitieux, une minorité très ambitieuse)
   est-elle défendable en soi (cohérent avec la littérature déjà citée
   sur la candidature, §2.3-§2.4 du plan) ? Si oui, le problème n'est pas
   la distribution mais uniquement le seuil qui la coupe à un point où
   presque rien ne passe.
2. **Quelle est la bonne cible pour le nombre attendu de citoyens
   éligibles à candidature dominante ?** Pas un chiffre arbitraire — une
   justification : combien de candidats potentiels une population de
   100 citoyens devrait-elle raisonnablement produire pour que le
   mécanisme de nomination de parti (§2.3, arbitrage entre prétendants
   internes) ait un sens ? Un seul citoyen éligible rend cet arbitrage
   vide de sens ; un nombre trop élevé le rend trivial.
3. **`ambition_threshold` doit-il rester un seuil fixe global, ou
   devenir relatif à la distribution réelle de la population** (ex. un
   percentile plutôt qu'une valeur absolue) ? Cette option n'était pas
   dans les trois lues par ADR-002 — à évaluer : un seuil relatif
   éliminerait structurellement le risque qu'une future modification de
   `ambition_dist` ou de `position_dist` recrée le même problème par
   accident, exactement le type de garde-fou déjà appliqué à la
   politique de validation de seed (chantier distribution, §4).

### 2.1bis Décision théorique proposée (2026-08-29) — À VALIDER avant tout sweep

> Écrite avant tout chiffre de calibration, conformément à la discipline du §2.
> Aucun sweep n'a été lancé. Les seuls chiffres ci-dessous sont ceux de la
> Phase 1 et des propriétés déjà publiées.

#### Le fait qui reformule la question : `decide_candidacy` n'implémente pas §2.4

Avant de répondre aux trois questions du §2.1, une lecture croisée du plan de
conception et du code change ce qui est en cause. §2.4 définit le chemin
dominant ainsi :

> « un citoyen se porte candidat quand son `ambition_score` **et le soutien
> qu'il perçoit dans son réseau social (§5)** dépassent un **seuil combiné**. »

et §2.2 définit `ambition_score` comme une « **propension** à se porter
candidat si l'occasion se présente » — un trait latent, pas un score à seuiller
seul. Or `simple_rules.decide_candidacy` est un `citizen.ambition_score >=
config.ambition_threshold` nu, dont la docstring annonce pourtant « Design doc
§2.4 dominant path ». **L'implémentation déterministe a laissé tomber l'un des
deux termes nommés par §2.4 tout en conservant la valeur du seuil.**

Ce n'est pas une déduction : le codebase le dit déjà de lui-même ailleurs.
`llm_behavior_engine.decide_candidacies` se décrit comme « v2 increment 2's
replacement for `decide_candidacy`'s **bare** ambition_score threshold », et
elle alimente le modèle avec `ambition_score` **et** `perceived_support`
(= `sympathizer_ratio`, la même fonction qui sert déjà de proxy de parrainage
au chemin de rupture). Le bras LLM applique donc déjà la règle à deux signaux
de §2.4 ; le bras déterministe applique une réduction connue à un seul signal.
Conséquence latérale, jamais nommée jusqu'ici : **les deux bras de chaque
comparaison d'acceptance ne filtrent pas les candidatures sur la même
information.**

Cela ouvre une **quatrième option**, absente des trois lues par ADR-002 :

> **Option 4 — implémenter §2.4 tel qu'écrit.** `decide_candidacy` gate sur un
> score combinant `ambition_score` et `sympathizer_ratio`, comparé à
> `ambition_threshold`.

Ses propriétés, à mettre en face des trois autres :

- **Coût RNG nul.** `sympathizer_ratio` est déterministe à partir d'états déjà
  tirés ; le flux de `generate_population` n'est pas touché. Même classe de
  coût que l'option 2 (baisser le seuil), pas que l'option 1.
- **Elle réconcilie les deux moteurs** sur les mêmes entrées. Nuance à ne pas
  survendre : `decide_candidacies` (LLM) ne lit pas `ambition_threshold` du
  tout — le modèle arbitre. L'alignement porte sur les *entrées*, pas sur la
  règle.
- **Elle répond à §2.4 au lieu de le réinterpréter**, ce qu'aucune des trois
  autres options ne fait : toutes trois supposent la règle correcte et ne
  discutent que les nombres.
- **Coût à accepter, honnêtement.** (a) `sympathizer_ratio` est O(n) par
  citoyen, donc O(n²) par évaluation — négligeable à n=100, à re-mesurer avant
  le n=1000 de §11.1 ; le chemin LLM paie déjà exactement ce prix. (b) Elle
  **ré-entrelace le pool de candidats avec `position_dist`**, que le §3.1 du
  chantier distribution était content de trouver orthogonal : toute mesure
  future qui compare deux `position_dist` verra désormais aussi un pool de
  candidats différent. C'est voulu par §2.4 (un candidat doit avoir du soutien)
  mais c'est un confondant nouveau, à déclarer. (c) Elle recoupe le constat
  §10.10 (« le membre au score d'ambition le plus élevé — un trait indépendant
  de la position politique ») sans le traiter : le §4 de ce plan met la
  sélection du nominee hors périmètre, et **l'option 4 ne l'y ramène pas** —
  elle change l'éligibilité, pas le critère de choix parmi les éligibles.

#### Réponses proposées aux trois questions du §2.1

**Q1 — la forme ou l'échelle ? → la forme est défendable, c'est
l'appariement qui ne l'est pas.** `beta(2,8)` est asymétrique à droite,
moyenne 0,2 : la plupart des citoyens n'envisagent jamais de se présenter, une
minorité y est fortement disposée. C'est la bonne forme pour une propension à
la candidature. **Mais la justification s'arrête là, et il faut le dire :** la
« littérature déjà citée sur la candidature » que le §2.1 invoque n'existe
pas. §2.3 ne cite personne ; §2.4 ne cite que Superti (2020), sur la diffusion
du vote protestataire, pas sur l'émergence de candidats. `THEORY.md` ne cite
rien non plus sur l'ambition politique. La seule justification écrite de
`beta(2,8)` est le commentaire du YAML : « la plupart des citoyens sont peu
ambitieux ». **Ne pas toucher à la forme** (rien ne justifie de la changer, et
la changer coûte le flux RNG), et enregistrer que son support bibliographique
est un commentaire de config, pas une citation.

**Q2 — quelle cible d'éligibles ? → une bande [10 %, 40 %], argumentée par
le mécanisme que le seuil doit rendre vivant, pas par le symptôme.** Deux
bornes, chacune dérivée d'un mécanisme existant :
- *Plancher.* §2.3 confie au parti l'arbitrage entre **plusieurs** prétendants
  internes, et §3.6.3 en fait un point de décision LLM. Il faut donc ≥ 2
  éligibles par parti **en moyenne** pour que cet arbitrage ne soit pas vide.
  À `initial_count: 5` et `population_size: 100` (≈ 20 membres par parti), cela
  donne un taux d'éligibles ≥ **10 %**. À 20 %, la probabilité qu'un parti ne
  présente personne tombe sous ~2 % — chaque scrutin est alors réellement
  disputé à cinq, comme au contournement `0.0`.
- *Plafond.* Au-delà de ~40 %, `ambition_score` cesse de discriminer et le
  seuil ne porte plus d'information : on retombe sur le régime `0.0`, où
  l'éligibilité est universelle et **tout le poids de la sélection bascule sur
  le départage de `select_party_nominee`** — précisément le régime dont §10.10
  a mesuré qu'il coûte 70 % de victoires du Blanc sous `uniform`. Graver `0.0`
  n'est donc pas neutre : c'est un choix de modélisation déjà mesuré comme
  nuisible, pas un défaut inoffensif.

**Q3 — seuil fixe ou relatif (percentile) ? → rester fixe, et prendre le
garde-fou ailleurs.** Le seuil relatif est séduisant pour la raison exacte que
le §2.1 avance (immunité structurelle à une future dérive de `ambition_dist`),
mais il coûte trop cher au regard d'un principe que ce dépôt applique déjà :
- `ambition_threshold` vit dans la section `candidacy:` — **les règles du
  jeu**. L'objet du fichier de config (ligne 3 : « aucune constante
  institutionnelle en dur dans le code ») est de comparer deux *constitutions*
  à graine identique. Un percentile garantit une offre de candidats constante
  **quelle que soit** l'ambition réelle de la population : le modèle perd la
  capacité d'exprimer « cette population s'est dépolitisée ». Un paramètre
  exogène devient une normalisation endogène.
- **Le précédent interne est déjà tranché dans ce sens.** §7.2 refuse un
  plancher de légitimité mobile parce qu'« un plancher mobile détruit la
  lisibilité externe que le mécanisme existe pour produire », et `config.py`
  rejette `recall_floor_indexed_on_L0: true` à l'analyse pour cette raison.
  Un seuil de candidature indexé sur la distribution courante est le même objet.
- **Le garde-fou existe déjà et coûte moins cher** : `_warn_if_no_candidate_is_possible`
  (livré le 2026-08-29). Il suffit d'élargir sa condition de « pool vide » à
  « taux d'éligibles sous le plancher retenu en Q2 » pour obtenir l'immunité
  visée, sans convertir une constante institutionnelle en statistique. Ce n'est
  pas la `PolityConfigError` qu'ADR-002 a explicitement rejetée : cela nomme,
  cela ne tranche pas à la place de l'opérateur.

#### Ce que la décision proposée n'est pas

Elle ne fixe **aucune valeur**. Elle fixe la *règle* (option 4 ou option 2), la
*cible* (Q2) et la *forme du paramètre* (Q3). Le sweep du §2.2 ne sert qu'à
vérifier que la règle défendue atteint aussi la cible — **et s'il montre
qu'elle ne l'atteint pas, c'est un résultat à publier, pas une licence à
chercher la valeur qui passe.**

### 2.2 Critère de décision, à fixer avant tout sweep empirique

> **Corrigé le 2026-08-29, unité changée.** La rédaction initiale de ce §2.2
> comptait en **runs** (« taux de runs avec au moins un candidat éligible sur
> 40 seeds ≥ 90 % »). La Phase 1 a montré que cette unité est aveugle au
> problème qu'elle est censée mesurer : le bras rupture atteint **100 % des
> runs** — 0/40 runs stériles, ce qui passerait un critère à 90 % sans
> discussion — tout en laissant **26,9 % des élections sans aucun candidat**.
> Un seul candidat sur huit scrutins suffit à faire passer un run pour sain.
> **L'unité est donc l'élection, pas le run**, dans tout ce qui suit. Le
> critère ci-dessous remplace intégralement la version précédente ; il est
> pré-enregistré, à valider tel quel avant de voir le moindre chiffre de
> calibration.

1. **Élections à champ candidat vide : 0/320.** Pas un taux — zéro. Une
   élection sans candidat n'est pas un résultat dégradé, c'est l'absence du
   mécanisme.
2. **Taux d'éligibles moyen dans [10 %, 40 %]** (justification Q2 ci-dessus).
3. **Arbitrage de nomination vivant** : ≥ 4 partis sur 5 présentent un nominee
   dans ≥ 95 % des élections, et ≥ 2 prétendants internes par parti en moyenne.
   C'est la traduction, en unité « élection », de la deuxième puce d'origine
   (« ni systématiquement 1, ni systématiquement proche de 100 »).
4. **Le trait discrimine encore** : le taux d'éligibles reste ≤ 40 % — un
   seuil que tout le monde franchit n'est pas un seuil.
5. **Reproductibilité sur un bloc de graines indépendant** (41..80 en plus de
   1..40), avec les deux blocs publiés. Leçon directe du §2.1 du chantier
   distribution, dont la ligne à 27,5 % ne s'est pas reproduite.
6. **Défendabilité théorique de la règle retenue, débattue avant les chiffres**
   — puce conservée telle quelle de la version d'origine, c'est la discipline
   de la Phase 1 du chantier distribution et elle n'est pas affectée par le
   changement d'unité.
7. **Sweep contre le pipeline réel** (`run_simulation` de bout en bout, durée
   livrée), jamais contre un instantané d'une seule élection — la Phase 1 a
   montré que le cadrage run/élection change la conclusion.

### 2.3 Vérification RNG de l'option 4 (2026-08-29) — mesurée, pas supposée

Le §2.1bis affirmait « coût RNG nul » pour l'option 4. Postulat vérifié, avec
la discipline qui vient de montrer que le postulat de coût de la Phase 1 était
faux.

**Faits structurels d'abord.** (a) `simple_rules.py` ne contient **qu'un seul
site de tirage**, `rng.random()` ligne 240, dans `attempt_rupture_candidacy` :
`sympathizer_ratio` et `decide_candidacy` sont sans RNG. (b) `issue_positions`
est assigné **une seule fois**, dans `generate_population` (`citizen.py:208`),
et muté nulle part dans le paquet — donc `sympathizer_ratio` est constant sur
un run. Le terme ajouté par l'option 4 ne tire rien, par construction.

**Mesure ensuite, et elle a d'abord failli être vide.** Première version de la
sonde : `bare @0.7` contre `comb @0.7`, tous flux identiques, journaux
identiques sur 5/5 graines. **Ce résultat ne prouve rien** — aux deux règles le
pool est vide (0 éligible), donc les deux runs sont le même run. Même classe
d'erreur que le postulat de coût de la Phase 1 : une vérification qui passe
parce qu'elle ne teste rien. Refaite avec des bras dont les pools **diffèrent
réellement**, et en comparant l'option 4 à l'**option 2** plutôt qu'au statu
quo cassé — la question décisionnelle est de savoir si l'option 4 coûte *plus*
que l'option 2, pas plus qu'une configuration qui ne tient aucune élection.

Métrique : **l'état final du bit generator** de chaque flux après le run, pas
le nombre d'appels (`choice` sur un pool de 99 ou 100 éléments peut consommer
un nombre de bits différent pour un même appel). 5 graines, rupture + events +
sortition **tous activés** pour que les trois flux per-tick soient réellement
consommés.

| Bras | éligibles/100 | flux dont l'état final bouge | journaux différents |
|---|---|---|---|
| `bare @0.7` (livré, référence) | 0 | — | — |
| `comb @0.7` (option 4, seuil livré) | 0 | **aucun** | 0/5 |
| `bare @0.35` (option 2) | 11–15 | `rupture` | 5/5 |
| `comb @0.35` (option 4) | 66–93 | `rupture` | 5/5 |
| `bare @0.0` (contournement) | 100 | `rupture` | 5/5 |

**Trois conclusions.**

1. **Les flux `population` et `parties` finissent dans un état identique dans
   tous les bras**, y compris à 0.0 et 0.35. Ni l'option 2 ni l'option 4 ne
   touchent le flux de `generate_population`. C'est mesuré sur l'état final du
   générateur, pas déduit de la lecture du code.
2. **Le seul flux qui bouge est `rupture_rng`, et il bouge identiquement pour
   l'option 2, l'option 4 et le contournement 0.0.** C'est une conséquence du
   pool qui cesse d'être vide, pas un coût propre à l'option 4. Il ne bouge que
   si `rupture_path_enabled` est vrai — à la configuration livrée (rupture
   `false`) il n'est jamais tiré, l'early-return précédant le `rng.random()`.
3. **Option 4 contre option 2 au même seuil (0,35) : aucun flux ne diffère**,
   malgré des pools très différents (66–93 contre 11–15 éligibles). Mécanisme :
   `select_party_nominee` ne renvoie qu'**un** nominee par parti, donc la
   *taille* du pool ne change pas combien de citoyens sont sautés par
   `_attempt_rupture_candidacies` — seule change la question de savoir si
   chaque parti présente quelqu'un.

**Verdict : le « coût RNG nul » du §2.1bis est confirmé, et l'option 4 ne coûte
rien de plus que l'option 2 sur ce plan.** Détail d'implémentation trouvé au
passage et à ne pas rater : `_declare_nominees` passe à `select_party_nominee`
une liste **déjà filtrée** (limites de mandat + ensemble barré §6bis.2) ; le
soutien perçu doit être calculé contre la population **entière**, sinon le
dénominateur est silencieusement faux.

### 2.4 Résultats du sweep Phase 2 (2026-08-29) — l'option 4 ne suffit pas seule

Sweep contre le critère pré-enregistré du §2.2 corrigé. Rupture **désactivée**
partout : la Phase 1 a écarté ce chemin, et ce sweep calibre le chemin
dominant. Règle combinée pré-enregistrée avant toute mesure :
`combiné = (ambition_score + sympathizer_ratio) / 2`, moyenne arithmétique non
pondérée — symétrique dans les deux signaux nommés par §2.4, **aucun paramètre
de poids libre qu'un sweep pourrait ajuster en douce**, et reste dans [0,1]
donc `ambition_threshold` demeure un ratio validé par `_get_ratio`. La
conjonction (« les deux signaux au-dessus du seuil ») est écartée *sur la
théorie, avant mesure* : elle est strictement plus dure que la porte actuelle,
donc incapable de réparer une porte trop restrictive.

**Étape A — taux d'éligibles par règle et par seuil** (graines 1..40) :

| seuil | `bare` élig. % | `bare` prét./parti | `combiné` élig. % | `combiné` prét./parti |
|---|---|---|---|---|
| 0,00 | 100,0 | 20,0 | 100,0 | 20,0 |
| 0,20 | 43,5 | 8,7 | 99,9 | 20,0 |
| 0,25 | **30,1** | 6,0 | 99,0 | 19,8 |
| 0,30 | **20,0** | 4,0 | 92,9 | 18,6 |
| 0,35 | **12,5** | 2,5 | 76,4 | 15,3 |
| 0,40 | 6,9 | 1,4 | 53,3 | 10,7 |
| 0,45 | 3,8 | 0,8 | **29,5** | 5,9 |
| 0,50 | 1,9 | 0,4 | **13,2** | 2,6 |
| 0,60 | 0,3 | 0,1 | 1,4 | 0,3 |
| **0,70 (livré)** | **0,0** | 0,0 | **0,1** | 0,0 |

**Étape B — pipeline réel sur les bras dans la bande, 320 élections** :

| Règle | seuil | élig. % | prét./parti | champ VIDE | ≥ 4 partis % | cand. moy. | verdict |
|---|---|---|---|---|---|---|---|
| `bare` | 0,25 | 30,1 | 6,0 | **0** | 100,0 | 4,97 | **PASS** |
| `bare` | 0,30 | 20,0 | 4,0 | **0** | 100,0 | 4,88 | **PASS** |
| `bare` | 0,35 | 12,5 | 2,5 | 0 | 90,0 | 4,38 | échec (critère 3) |
| `combiné` | 0,45 | 29,5 | 5,9 | **0** | 100,0 | 4,80 | **PASS** |
| `combiné` | 0,50 | 13,2 | 2,6 | 0 | 75,0 | 3,95 | échec (critère 3) |
| `bare` | **0,70 (livré)** | 0,0 | 0,0 | **312** | 0,0 | 0,03 | échec |
| `combiné` | **0,70 (option 4 seule)** | 0,1 | 0,0 | **304** | 0,0 | 0,05 | **échec** |
| `bare` | 0,00 (contournement) | 100,0 | 20,0 | 0 | 100,0 | 5,00 | échec (critère 4) |

**Étape C — critère 5, bloc de graines indépendant 41..80** : les trois bras
PASS se reproduisent (`bare @0,25` : 30,1 % → 30,8 % ; `bare @0,30` : 20,0 % →
20,4 % ; `combiné @0,45` : 29,5 % → 31,1 % ; champ vide 0 et ≥ 4 partis 100 %
dans les deux blocs). Pas de répétition du fiasco de reproductibilité du §2.1
du chantier distribution.

**Réponse directe à la question posée : l'option 4 ne suffit pas seule, et
elle ne « réduit » même presque pas le problème.** Au seuil livré de 0,7 elle
laisse **304 élections sur 320 sans candidat**, contre 312 pour la règle nue —
8 élections gagnées sur 320. La raison est arithmétique : une moyenne
**compresse**, elle ne translate pas. Atteindre 0,7 en moyenne exige
`ambition + soutien ≥ 1,4` ; le soutien plafonne autour de 0,6, il faudrait
donc une ambition ≥ 0,8 que `beta(2,8)` ne produit pratiquement jamais.
**L'option 4 déplace ce qu'il faut calibrer, elle ne supprime pas la
calibration.** L'option 2 reste donc ouverte — et les deux sont bien
nécessaires **ensemble** si l'option 4 est retenue.

**Le critère ne départage pas les deux règles — et c'est un résultat, pas un
manque.** Trois bras passent : deux `bare`, un `combiné`. Le choix entre eux ne
peut donc pas être empirique ; il doit se faire sur la fidélité à §2.4, exactement
comme le §2.2 (puce 6) l'exigeait.

**Mesure discriminante ajoutée, et elle est défavorable à l'option 4** —
puisque sans elle le choix se ferait à l'aveugle. §2.4 revendique que les
candidats aient un soutien perçu : la métrique qui discrimine est donc le
soutien de ceux qui deviennent **effectivement** nominees, pas la taille du
pool.

| Règle | seuil | soutien moyen des nominees | ambition moyenne des nominees | victoires du Blanc |
|---|---|---|---|---|
| `bare` | 0,25 | 0,6137 | 0,4573 | 0/320 |
| `bare` | 0,30 | 0,6143 | 0,4609 | 0/320 |
| `combiné` | 0,45 | **0,6315** | 0,4594 | 0/320 |

**+0,018 de soutien moyen, soit ~3 % — et rien d'autre ne bouge.** La cause est
identifiable et déjà connue du projet : `select_party_nominee` choisit
l'**argmax sur `ambition_score`** parmi les éligibles. Élargir ou reformer la
*porte d'éligibilité* ne change donc presque pas qui finit candidat — l'argmax
sur l'ambition lave l'effet. C'est exactement le constat §10.10 (« le membre au
score d'ambition le plus élevé — un trait indépendant de la position
politique »).

**Conséquence pour la décision, énoncée sans la trancher** : la revendication de
fond de §2.4 — « un candidat doit avoir du soutien » — **n'est pas livrée en
réparant `decide_candidacy` seul**, elle est bloquée en aval par le critère de
nomination, que le §4 de ce plan met explicitement hors périmètre. L'option 4
paierait donc ses coûts (entrelacement du pool avec `position_dist`, O(n²), un
confondant nouveau pour toute comparaison future de distributions) pour un
effet mesuré quasi nul **tant que la question §10.10 n'est pas ouverte avec
elle**.

## 3. Coût de migration, à accepter explicitement avant d'implémenter

- Si `ambition_dist` ou son flux RNG change : au moins
  `test_blank_vote_competitive_enabled_but_never_triggered_...` devra
  être reconstruit sur un mécanisme différent (pas juste corrigé en
  surface) — documenté comme un vrai coût, pas une ligne à ignorer.
- Vérifier s'il existe d'autres tests dépendant implicitement du défaut
  actuel au-delà des quatre déjà identifiés dans ADR-002, avant de
  commencer l'implémentation — pas en découvrir un cinquième après coup.
- Aucun run d'acceptance déjà publié n'a exercé la valeur livrée — donc
  aucun re-baseline rétroactif n'est nécessaire pour ce changement
  précis (contrairement au chantier distribution, qui touchait des
  résultats déjà publiés sous `uniform`).

### 3.1 Coût de migration mesuré (2026-08-29) — il y a bien un cinquième test, et c'est une seconde preuve de byte-identité

Mesuré maintenant, comme le §3 l'exige, plutôt que découvert en cours
d'implémentation. Méthode : suite complète relancée sous un plugin pytest qui
redirige `config._DEFAULT_CONFIG_PATH` vers une copie temporaire du YAML —
**aucun fichier du dépôt modifié**. Référence : **1774 tests passent** à la
configuration livrée.

| Configuration sondée | Résultat |
|---|---|
| livrée (référence) | 1774 passent |
| `ambition_threshold: 0.0` | **7 échecs**, 1767 passent |
| `rupture_path_enabled: true` | **7 échecs**, 1767 passent |

ADR-002 en annonçait **quatre**. Il y en a **sept**, et la différence n'est pas
que du volume.

**Les deux preuves de byte-identité (pas une).**

1. `test_blank_vote_competitive_enabled_but_never_triggered_..._byte_for_byte`
   — celle qu'ADR-002 nomme. Elle casse **avant** la comparaison d'octets, sur
   son assertion préalable : dès qu'un champ de candidats existe, les clés
   `attempt`/`forced` apparaissent et `blank_vote_competitive` cesse d'être un
   no-op. À reconstruire sur un autre mécanisme de champ vide, comme prévu.
2. `test_events_enabled_but_structurally_inert_..._byte_for_byte` (v5) —
   **non identifiée par ADR-002**, et elle casse plus fort : sur la comparaison
   d'octets elle-même, 64 lignes contre **1485**. Cause diagnostiquée :
   `_config_with_events_enabled` force `awakening.enabled=True` (règle
   inter-champs de `config.py`) alors que sa référence `_config_with_output_dir`
   ne l'active pas. Tant que la présidence reste vacante, `awakening` n'a
   personne contre qui produire de `pressure_action` et les deux journaux
   coïncident ; dès qu'un président existe, le bras « on » en écrit **1421**.
   Cette preuve ne démontre donc pas « events on == events off » mais « events
   on == events off *à présidence perpétuellement vacante* ». Réparation
   identifiée : activer `awakening` **des deux côtés**, ce que le test voulait
   comparer depuis le début — isoler la variable `events`. Le commentaire du
   helper dit d'ailleurs déjà, à tort, qu'`ambition_threshold` y est laissé
   intact « purement parce que ces tests ne portaient pas sur la dynamique
   électorale, pas parce que quoi que ce soit casserait si un vainqueur
   existait ».

**Les cinq autres, par classe de réparation.**

- *Réparation locale (épingler le seuil dans le test)* :
  `test_shipped_config_warns_that_no_candidacy_is_ever_possible` et
  `test_election_no_winner_names_an_absent_candidate_field` — les deux tests
  livrés **la veille** avec la moitié visibilité, adossés par construction à la
  valeur livrée. `test_no_pressure_action_events_while_the_presidency_is_vacant`
  et `test_no_petition_events_while_the_presidency_is_vacant` — les deux tests
  de vacance (ADR-002 n'en comptait qu'un).
- *Assertion à réécrire* :
  `test_a_real_firing_events_run_produces_scandal_and_economic_shock_events`,
  dont le `assert all(e["payload"]["target"] is None ...)` porte le commentaire
  « never a winner at shipped ambition_threshold ».

**Deux nuances qui changent le chiffrage selon l'option retenue.**

- Le sondage `ambition_threshold` mesure le coût de **l'ouverture du pool**. Il
  ne mesure **pas** le coût du décalage de flux RNG, qui ne concerne que
  l'option 1 (`ambition_dist`) et s'y ajoute. Les options 2 et 4 ne paient que
  la colonne mesurée ici.
- Le sondage `rupture_path_enabled` fait tomber un test de plus,
  `test_legitimacy_is_flat_at_mandate_strength_for_the_entire_run`, qui pourtant
  **impose déjà** `ambition_threshold=0.0`. Il épingle `m = 0.51`, une valeur
  dérivée d'un champ à cinq nominees : il casse dès que la **composition** du
  champ change, pas seulement son cardinal. Signal utile pour l'option 1, dont
  le décalage RNG changera la composition partout.

**Ce qui ne coûte rien, confirmé** : aucun run d'acceptance publié n'a exercé
la valeur livrée (tous imposent `ambition_threshold=0.0`), donc aucun
re-baseline rétroactif n'est dû pour ce changement — contrairement au chantier
distribution.

**Trouvé au passage, hors périmètre** : `candidacy.independent_signature_ratio`
(le « seuil de candidature indépendante » du §2.3) est parsé et validé par
`config.py`, mais **jamais lu par le code de domaine** — ni `simple_rules.py`
ni `run_polity_simulation.py` ne le référencent. Combiné au constat du §1.1
(le seuil de signatures de rupture est structurellement inerte à n=100), le
filtre d'accès au bulletin de §2.3 n'existe aujourd'hui dans aucun des deux
chemins. À traiter séparément, pas ici.

## 3bis. Re-baseline déterministe des résultats publiés — vérifié NON APPLICABLE (2026-08-29)

Question posée après l'implémentation de l'option 2 : les résultats déjà
publiés dans `THEORY.md` §10.4-§10.9 restent-ils valides maintenant que le
seuil livré change (0,7 → 0,30) ? Avant d'écrire un critère qualitatif/
numérique pour trancher, la prémisse elle-même a été vérifiée — et elle
était fausse.

### La prémisse initiale était fausse : `ambition_threshold` n'est jamais lu sur le chemin LLM

Recherche exhaustive (`grep` sur tout `fast_api_voter/`) : le **seul** site de
lecture fonctionnelle d'`ambition_threshold` dans tout le paquet de domaine
est `simple_rules.py:196` (`decide_candidacy`), appelé uniquement par
`select_party_nominee` — le chemin **déterministe**. `_declare_nominees_llm`
route vers `decide_candidacies` (`llm_behavior_engine.py`), qui n'arbitre
QUE sur `ambition_score` et `perceived_support`, sans jamais comparer à un
seuil — confirmé par sa propre docstring (« v2 increment 2's replacement for
`decide_candidacy`'s bare ambition_score threshold ») et par
`_declare_nominees`'s propre branchement (`if config.llm.enabled: return
_declare_nominees_llm(...)` — la branche qui lit `ambition_threshold` est
après ce `if`, donc inatteignable quand `llm.enabled` est vrai).

**Conséquence directe : tout résultat mesuré sous `--engine llm` est
structurellement, par construction, invariant au changement 0,7→0,30 — pas
parce que l'effet mesuré serait petit, mais parce que le chemin de code qui
porterait l'effet n'existe pas.** Or les affirmations chiffrées de §10.4 à
§10.9 (déviation de mandat, comparaison contagion/atomisé, comparaison
chambre/président, amplitude de l'étincelle) sont **toutes** issues de runs
`--engine llm`. Le "critère qualitatif/numérique + décision sur le run LLM à
~6500 s" initialement envisagé répondait donc à une question qui ne se pose
pas — la même classe d'erreur que le postulat de coût de la Phase 1
(§1.1) : une prémisse non tracée, prise pour acquise.

### Ce qui reste réellement ouvert, et sa nuance

Seul le moteur `--engine deterministic` lit `ambition_threshold`. Deux
usages distincts de ce moteur ont été vérifiés séparément, précisément parce
qu'un même seed/config peut apparaître dans les deux registres sans que ce
soit évident au premier coup d'œil :

1. **Ancres de pré-vol internes aux scripts d'acceptance** — un sanity-check
   bon marché avant de lancer le bras LLM coûteux (ex. `run_v6a_acceptance.py` :
   « compare its own recall count / final mean_legitimacy against
   `mobilization_only/deterministic/8y`'s own committed anchor... before
   proceeding to `--engine llm` »). Jamais cité comme résultat scientifique
   en soi.
2. **La citation à part entière de `THEORY.md` §10.10** — les « quatre sondes
   déterministes » du 2026-08-25 (chantier distribution, Phase 4), qui
   rejouent « les configurations exactes de v4 Lot 8 (`both`, `electoral_only`,
   `mobilization_only`) et de la troisième comparaison v6b sous
   `factor_structure` », avec leurs propres chiffres cités dans le texte
   (`L=0,510→0,770`, etc.) et leur propre statut épistémique (« preuve
   suggestive, pas concluante ») — dont dérive l'heuristique « sonde fiable
   sur les quantités mécaniques, optimiste sur l'arbitrage citoyen » réutilisée
   depuis dans ce même chantier de calibration (§2.1bis).

**Vérifié : ce sont les mêmes configurations sous-jacentes** (même seed=42,
même `population_size=100`, mêmes deux valeurs de `position_dist` en jeu —
`uniform` pour v4 Lot 8/v5/v6a et les trois premières sondes du §10.10 v6b,
`factor_structure` pour v6b `factor_structure`/`fs_electoral_only` et la
quatrième sonde). Un seul contrôle couvre donc les deux usages ; inutile
d'en construire deux séparés.

### Contrôle structurel, puis mesure directe (pas d'un seul, des deux)

**Étape 1 — structurel, quasi gratuit.** `static_population: true`,
`president_term_limit: null` (illimité) et aucune de ces configs n'active
`blank_vote_competitive` : le pool éligible que voit `select_party_nominee`
est donc le **même** — la population de parti au complet — à **chaque**
élection du calendrier, pas seulement à la première. Un seul calcul
d'argmax(`ambition_score`) par parti et par `(seed, position_dist)` suffit
donc à caractériser tout le run, pas juste son premier tick.

| `position_dist` (seed=42, n=100) | argmax `ambition_score` par parti (min sur les 5) | clears 0,30 |
|---|---|---|
| `uniform` | 0,4553 (min ; max 0,5560) | **oui, les 5** |
| `factor_structure` | 0,4068 (min ; max 0,5654) | **oui, les 5** |

Aucun cas limite : la marge la plus faible est +0,10 au-dessus du seuil. Si
l'argmax de chaque parti franchit déjà 0,30, le **même** citoyen est nominee
de chaque parti à `ambition_threshold=0.0` et à `0.30` — donc la même
élection, à chaque tour, pour toute la durée du run.

**Étape 2 — mesure directe, pas seulement l'argument.** Le raisonnement
ci-dessus est exact (le tiebreak reproduit lettre pour lettre celui de
`select_party_nominee`), mais la discipline de ce chantier est de mesurer,
pas de faire confiance à un raisonnement seul (cf. la vérification RNG de
l'option 4, §2.3, dont la première version s'est révélée vide). Pipeline
réel de bout en bout, `ambition_threshold=0.0` contre `0.30`, comparaison
d'octets sur le journal complet, sur les 8 configurations couvrant chaque
famille de script d'acceptance publiée :

| Configuration | Byte-identique 0,0 vs 0,30 |
|---|---|
| v4 Lot 8 `both`, `uniform` | **oui** |
| v4 Lot 8 `electoral_only`, `uniform` (= base v5) | **oui** |
| v4 Lot 8 `mobilization_only`, `uniform` (= base v6a) | **oui** |
| `both`, `factor_structure` | **oui** |
| `electoral_only`, `factor_structure` (v6b fs_electoral_only) | **oui** |
| v6b `both` + `sortition_chamber`, `uniform` | **oui** |
| v6b `both` + `sortition_chamber`, `factor_structure` (§10.10, 4ᵉ sonde) | **oui** |
| cascade `both` + `events` + `social_graph`, `uniform` (r=0,08, s=0,12) | **oui** |

**Huit configurations sur huit, byte-identiques.** Couvre chaque famille de
script (v4/v5/v6a/v6b/cascade), les deux `position_dist` jamais utilisées par
un run publié, avec et sans `sortition_chamber`/`events`/`social_graph`
activés.

### Conclusion — VÉRIFIÉ NON APPLICABLE, pas reporté

**La question du re-baseline est close, pas différée.** Ni les affirmations
scientifiques de §10.4-§10.9 (toutes mesurées sous `--engine llm`, chemin qui
ne lit jamais `ambition_threshold` — invariance structurelle, prouvée par
lecture de code) ni les ancres de pré-vol déterministes (invariance mesurée,
huit configurations byte-identiques) ne sont affectées par la calibration
0,7→0,30. Aucun ajustement de script n'est nécessaire : les ancres
committées restent exactes telles quelles.

Si un jour une des huit configurations cessait d'être byte-identique (ex.
après un changement d'`ambition_dist`, de `position_dist`, ou de
`parties.initial_count`), ce serait un **ajustement mécanique de config**
dans le script concerné — jamais une remise en cause d'un résultat
scientifique publié, puisque toutes les affirmations elles-mêmes reposent
sur le chemin LLM, structurellement hors d'atteinte.

## 4. Ce que ce plan ne couvre pas

- Le mécanisme de sélection de nominee (`ambition` vs `centroïde`) n'est
  pas remis en cause ici — déjà mesuré et documenté (§10.10) comme un
  facteur distinct, agissant sur le même mode d'échec mais indépendant
  de cette calibration.
- Le diagnostic du plancher de troncature `chamber_deliberation` reste
  un chantier séparé, non traité ici.

## Sortie attendue de cette session

1. Résultat de la Phase 1 (test `rupture_path_enabled`) — si suffisant,
   clore ADR-002 sans toucher à la calibration, avec justification
   théorique écrite (pas seulement "ça marche").
2. Si insuffisant : décision théorique de la Phase 2.1, écrite avant
   tout chiffre, présentée pour validation avant le sweep empirique.
3. Si un sweep est lancé : résultats confrontés au critère
   pré-enregistré de la Phase 2.2, présentés avant toute implémentation
   en production.

### État au 2026-08-29

- **Sortie 1 — FAITE.** Phase 1 écartée sur trois motifs (§1.1). ADR-002 ne
  peut pas être close par sa quatrième lecture, et cette lecture n'était même
  pas la moins chère : même rayon d'explosion de 7 tests que les options de
  calibration.
- **Sortie 2 — ÉCRITE.** Décision théorique en §2.1bis (dont une quatrième
  option qu'ADR-002 ne listait pas). Critère pré-enregistré **corrigé en unité
  « élection »** dans le §2.2 lui-même (la rédaction « runs » d'origine aurait
  laissé passer le bras rupture sans discussion).
- **§3 — FAIT en avance.** Coût de migration mesuré (§3.1) : sept tests, pas
  quatre, dont une **seconde** preuve de byte-identité qu'ADR-002 n'avait pas
  identifiée. Exactement le « cinquième découvert après coup » que le §3
  voulait éviter.
- **Sortie 3 — FAITE.** Sweep lancé et confronté au critère pré-enregistré
  (§2.4). Trois bras passent (`bare @0,25`, `bare @0,30`, `combiné @0,45`), tous
  reproduits sur le bloc de graines indépendant. **Le critère ne départage pas
  les règles** : le choix reste théorique.
- **Vérification RNG de l'option 4 — FAITE** (§2.3), sur l'état final du bit
  generator, après avoir écarté une première version vide de contenu.
- **Trace séparée du bug C1** — `docs/adr/ADR-003-ballot-access-filter-is-inert.md`,
  avec pointeur au site de config, comme ADR-002.
- **TRANCHÉ ET IMPLÉMENTÉ (2026-08-29)** : option 2, `ambition_threshold`
  `0.7 → 0.30`. `ambition_dist` et la règle de `decide_candidacy` restent
  inchangées. Option 4 (règle combinée §2.4) **reportée et explicitement
  groupée avec la question du critère de nomination §10.10**, puisque la mesure
  discriminante montre que l'argmax sur l'ambition lave son effet (+0,018 de
  soutien moyen des nominees, ~3 %) tant que ce critère n'est pas rouvert.
  Suite complète verte : **1776 tests** (1774 avant, +2 nouveaux garde-fous).
  Les deux preuves de byte-identité sont reconstruites sur
  `institutions.president_term_limit: 0` — champ candidat vide **par
  construction**, à chaque tick, pour chaque graine, indépendamment de tout
  tirage — là où l'ancien mécanisme n'était que distributionnel. Les scripts
  d'acceptance gardent `ambition_threshold=0.0`, désormais par continuité et
  non par nécessité.
- **Re-baseline déterministe — VÉRIFIÉ NON APPLICABLE (§3bis), pas
  reporté.** La prémisse initiale (« le run LLM à ~6500 s pourrait devoir
  être rejoué ») était fausse : `ambition_threshold` n'a qu'un seul site de
  lecture fonctionnelle dans tout le paquet de domaine, et c'est le chemin
  déterministe — le chemin LLM (`decide_candidacies`) ne le consulte jamais.
  Trouvé en traçant le code avant d'écrire le moindre critère, la même
  discipline que la Phase 1 sur `rupture_path_enabled` et que la
  vérification RNG de l'option 4 : remonter à la source plutôt que de partir
  d'une prémisse non vérifiée. Les ancres de pré-vol déterministes (jamais
  citées comme résultat scientifique) ET la citation séparée du §10.10
  (les « quatre sondes déterministes », mêmes configs sous-jacentes,
  vérifié) sont toutes les deux mesurées byte-identiques entre 0,0 et 0,30
  sur huit configurations couvrant chaque famille de script publiée. Aucun
  script à ajuster.
- Sondes en scratchpad, non commitées (convention du dépôt) :
  `probe_rupture_phase1.py`, `probe_signature_bar.py`,
  `probe_threshold_plugin.py` / `probe_rupture_plugin.py`, `option4.py`,
  `probe_option4_rng.py` / `_rng2` / `_rng3`, `probe_sweep.py`,
  `probe_discriminate.py`, `probe_preflight_anchor_check.py`,
  `probe_preflight_byte_identity.py`, `probe_v6b_byte_identity.py`,
  `probe_cascade_byte_identity.py`.
