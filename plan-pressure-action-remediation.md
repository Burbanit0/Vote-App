# Plan — Remédiation `pressure_action` (collapse de contenu, cause structurelle non identifiée)

> Document de scoping, à discuter et amender avant toute implémentation.
> Suite directe de l'investigation qualité `pressure_action` (chantier
> `plan-decision-quality-validation.md`) : position écartée, taille de
> batch écartée (0/63 codes d'action même à size=1), la phrase de
> cadrage "0 et 4 sont légitimes" écartée comme cause suffisante isolée
> (ablation, résultat nul propre). Mécanisme réel non identifié.
> Objectif : documenter proprement le test cross-modèle déjà mené, puis
> poser un protocole strict pour tester trois pistes de refonte et leurs
> combinaisons — sans retomber dans le tâtonnement que ce chantier a
> précisément cherché à éviter jusqu'ici.

---

## 0. Rappel — ce qui est déjà établi, pour mémoire

- `pressure_action` a exactement deux états de défaillance selon la
  taille de batch : collapse uniforme à taille de production (21-25),
  évitement systématique des codes d'action à toute taille testée
  inférieure (3, 5, 10, 1) — aucune configuration de chunk_size
  fonctionnelle trouvée dans `[1, 25]`.
- Le batching est éliminé comme cause (size=1 collapse identiquement,
  0/63 codes d'action, y compris sur `cid=6` à ratio=4,226, le cas le
  plus extrême du jeu de données).
- La phrase de cadrage "0 (NOTHING) et 4 (WAIT_FOR_ELECTION) sont des
  résultats légitimes, jamais des échecs" est écartée comme cause
  **suffisante isolée** (ablation, 0 flip sur 5 cas, y compris un cas
  témoin qui aurait dû rester non-agissant) — mais pas exonérée comme
  facteur contribuant parmi d'autres.
- Précision de départ (avant tout raffinement) : 38,1% (8/21) sur les
  cas non ambigus, très en dessous du seuil de 90% déjà utilisé pour les
  autres sondes de ce chantier.

## 1. Documentation du test cross-modèle (à formaliser, correction du verdict imprimé)

**Le verdict du script ("pas spécifique à qwen3:8b") est trompeur tel
quel et doit être corrigé avant d'être cité ailleurs.** Documenter les
quatre résultats séparément, pas comme un verdict agrégé unique :

| Modèle | Résultat réel | Catégorie |
|---|---|---|
| `qwen3:8b` (référence) | Collapse content-blind vers NOTHING/WAIT | Collapse de contenu |
| `llama3.1:8b` | Échec de conformité au format structuré (ID de citoyen dupliqué, jamais une décision valide) sur 100% des appels | **Non évaluable** — problème de conformité JSON, pas de contenu |
| `gemma2:9b` | Même échec de conformité que `llama3.1:8b` | **Non évaluable** — idem |
| `mistral:7b` | Décode proprement sur 5/5, mais collapse à 100% vers MOBILIZE (y compris le cas témoin qui aurait dû rester non-agissant) | Collapse de contenu, **pôle opposé** à qwen3:8b |
| `qwen2.5:7b` | 3/5 décodés, les trois vers NOTHING | Échantillon insuffisant pour conclure (n=3) |

**Lecture correcte** : deux modèles ne sont pas évaluables du tout
(problème distinct, conformité de sortie structurée sur l'endpoint
natif d'Ollama — à noter séparément, hors scope de ce document). Des
deux modèles évaluables avec un échantillon exploitable, les deux
collapsent — mais vers des pôles opposés (jamais agir vs toujours agir).
C'est un argument **en faveur** de l'hypothèse structurelle (la forme de
la tâche elle-même, pas un biais de contenu appris par une famille de
modèle précise) plutôt qu'une simple réplication du même biais — deux
architectures différentes ne convergeraient pas vers deux pôles
opposés si la cause était un biais de contenu partagé.

**Action** : corriger le verdict imprimé par le script cross-modèle
lui-même (`compare_models_pressure_action.py` ou équivalent) pour
refléter ce tableau plutôt qu'une phrase unique, avant tout usage futur
de ce résultat comme référence.

## 2. Étape 0 — diagnostics rapides, avant toute refonte (nouveau, pas encore fait)

Deux vérifications bon marché, à faire **avant** d'investir dans l'une
des trois refontes, parce qu'elles informent laquelle mérite d'être
creusée en premier plutôt que de choisir arbitrairement.

### 2.1 Perturbation de température (diagnostic de décodage)

**Hypothèse** : le collapse pourrait être, en tout ou partie, un
artefact de décodage glouton (une seule trajectoire de tokens dominante
à température=0) plutôt qu'un biais de contenu appris — précédent
direct dans ce projet : `temperature=0,3` au retry a cassé une boucle
déterministe dégénérée pour `cast_votes` (§3.6.1).

**Protocole** : rejouer les mêmes cas déjà caractérisés comme
non-agissants à tort (`cid=6` et les autres cas extrêmes du sweep
étendu), à `temperature=0,3`, size=1 (pour ne pas réintroduire la
variable batch), même prompt de production sinon inchangé.

**Critère pré-enregistré** :
- Si des codes d'action crédibles apparaissent et sont cohérents avec
  la vérité de référence sur ces cas → le collapse a une composante de
  décodage significative, la piste de remédiation la plus légère (varier
  la température) devient un candidat sérieux, à tester à plus grande
  échelle avant toute refonte de prompt/schéma.
- Si aucun changement → le décodage glouton est écarté comme facteur,
  le problème est structurel au contenu/à la forme de la tâche, priorité
  aux trois pistes de refonte ci-dessous.

**Résultat, 2026-08-30** (`check_pressure_action_temperature_diagnostic.py`) : **0/4 cas
« devrait agir » ont basculé vers un code d'action à température=0,3** — les 5 cas (4 extrêmes +
témoin) produisent l'acte IDENTIQUE à celui mesuré à température=0,0, motif inclus. Décodage
glouton écarté comme facteur, conformément au critère pré-enregistré.

### 2.2 Biais d'ordre des options dans le menu

**Hypothèse** : l'ordre de présentation des 5 codes dans le prompt (pas
la position du citoyen dans un batch, déjà écartée) pourrait produire un
effet de primauté classique en faveur des options listées en premier.

**Protocole** : permuter l'ordre de présentation des 5 codes dans la
table du prompt (ex. codes d'action en premier, NOTHING/WAIT en
dernier), rejouer les mêmes cas de référence, size=1, température=0
(pour isoler cette seule variable).

**Critère pré-enregistré** :
- Si le taux de collapse se déplace significativement selon l'ordre →
  effet de primauté confirmé, à corriger indépendamment des trois pistes
  de refonte (un simple réordonnancement du prompt, testable et
  déployable sans refonte complète).
- Si aucun changement → écarté, ne pas revisiter.

**Résultat, 2026-08-30** (`check_pressure_action_order_diagnostic.py`) : table réordonnée (codes
d'action 1/2/3 en premier, NOTHING/WAIT_FOR_ELECTION en dernier — l'inverse exact de l'ordre de
production, qui encadre déjà la liste avec NOTHING en premier et WAIT_FOR_ELECTION en dernier).
**0/4 cas basculés, le cas témoin non plus.** Résultat identique acte-pour-acte à la table de
production sur les 5 cas. Effet de primauté/récence écarté, conformément au critère
pré-enregistré — malgré la configuration structurellement favorable au test (les deux codes
sûrs occupaient déjà les deux positions les plus consultées en production).

**Bilan de l'étape 0 : les deux diagnostics reviennent négatifs.** Ni la température ni l'ordre du
menu n'expliquent le collapse. Ils ne discriminent donc pas entre les trois pistes de refonte —
contrairement à ce que §2 anticipait, aucune des deux ne pointe vers une piste plutôt qu'une
autre. La priorisation entre §3.1/§3.2/§3.3 doit se faire sur une autre base (voir §3bis).

### 2bis. Priorisation proposée, puisque l'étape 0 ne discrimine pas

Les deux diagnostics n'orientant vers aucune piste en particulier, proposition raisonnée plutôt
qu'un choix arbitraire — à valider avant de lancer le test à grande échelle :

**§3.1 (binaire-puis-levier) en premier**, parce que : (a) c'est la piste la plus directement
motivée par la chaîne d'élimination complète (position, taille, phrase de cadrage tous écartés —
c'est le candidat nommé explicitement dans la clôture du chantier de diagnostic, pas une nouvelle
hypothèse) ; (b) elle ne change pas le format de sortie (JSON conservé à chaque étape), le
changement le plus chirurgical des trois par rapport au pipeline existant ; (c) son échec
éventuel serait lui-même informatif — si séparer agir/ne-pas-agir du choix du levier ne change
rien, ça affaiblirait directement l'hypothèse "structure du menu" et orienterait vers §3.2 (format
de sortie) ou §3.3 (ancrage par l'exemple) avec un argument plus fort qu'un choix a priori.

Non retenu pour l'instant, pas invalidé : §3.2 (format de sortie) — motivé indirectement par les
échecs de conformité JSON de `llama3.1:8b`/`gemma2:9b` observés dans le test cross-modèle, mais
c'est un changement de pipeline plus lourd (parseur algorithmique dédié) pour un lien encore
indirect. §3.3 (few-shot) — l'ablation a déjà montré que la RÈGLE ABSTRAITE ne suffit pas seule ;
un exemple concret teste un mécanisme différent (ancrage plutôt que règle), donc pas écarté par
ce résultat, mais moins directement motivé que §3.1 par ce qui a déjà été mesuré.

## 3. Les trois pistes de refonte, définies précisément

Aucune n'est testée aujourd'hui. Chacune attaque le problème par un
mécanisme différent — elles ne s'excluent pas mutuellement.

### 3.1 Binaire-puis-levier
Repense la **structure du choix** : décomposer la décision en deux
étapes explicites — (1) agir ou non (question binaire), (2) si "agir",
lequel des trois codes d'action. Hypothèse : séparer ces deux jugements
empêche le modèle de "retomber" directement sur une case sûre du menu à
5 options en une seule décision.

### 3.2 — Résultat, 2026-08-30 : ÉCHEC identique, chiffre pour chiffre

Priorisé après l'échec de §3.1 pour une raison diagnostique (pas une préférence) : si le collapse
survit au changement de STRUCTURE du choix (§3.1), l'hypothèse la plus économe devient que le
remplissage direct d'un champ JSON structuré est lui-même le facteur commun — §3.2 est la seule
des trois pistes qui change comment la réponse est PRODUITE (articulation en texte libre, PUIS
traduction purement algorithmique — aucun second appel LLM, ce qui violerait la règle du projet
contre le jugement d'un LLM par un LLM).

`check_pressure_action_primary_language_redesign.py` (nouveau, committé) : prompt demandant trois
lignes strictes (`SITUATION:` / `DECISION: AGIT|N_AGIT_PAS` / `MOTIF:`), appel natif Ollama SANS
contrainte de schéma JSON (texte libre, `think=False`), parseur regex purement algorithmique.
Même jeu de données que §3.1 (70 citoyens non ambigus, même élu `cid=5` non biaisé), même
`size=1`/`think=False`/`température=0,0`.

**Contrôle qualitatif avant le run complet** (4 citoyens, 2 « devrait agir » extrêmes + 2 « ne
devrait pas » extrêmes) : les 4 ont reçu la MÊME phrase SITUATION quasi mot pour mot (« écart de
mécontentement modéré »), sans rapport avec leur ratio réel (2,085 / 1,753 / 0,472 / 0,242), et
les 4 ont reçu `DECISION: AGIT`. L'étape d'articulation elle-même s'est révélée content-blind, pas
seulement la décision finale.

```
checked: 70/70 (0 échec de parsing)
accord avec la vérité de référence (agir vs ne pas agir) : 17/70 (24,3%)
```

**Échec identique, chiffre pour chiffre à §3.1** (même 17/70, même 24,3%) — cohérent avec un
collapse uniforme vers `AGIT` sur l'ensemble des 70 citoyens (fortement corroboré par le contrôle
qualitatif ci-dessus, pas indépendamment re-vérifié sur les 70 individuellement).

**Conséquence, par le protocole §4.3** : ni la structure du choix (§3.1) ni le mécanisme de
production de la réponse (§3.2) n'expliquent seuls le collapse — les deux échouent de façon
indiscernable. Ça laisse **§3.3 (few-shot) comme seule piste des trois encore non testée**, avec
un argument sensiblement renforcé maintenant que les deux autres axes sont affaiblis. Aucun
croisement justifié (§4.3.3) : ni §3.1 ni §3.2 ne montre de signal positif partiel à combiner.

### 3bis. Résultat du croisement §3.1 vs §3.2, et test de généralité hors pressure_action

**Croisement par identité de citoyen (gratuit, données déjà en main)** : les deux tests portent
sur exactement les mêmes 70 citoyens. Résultat : **recouvrement à 100%** — les mêmes 17 citoyens
« réussissent » et les mêmes 53 « échouent » dans les deux tests, zéro cas où un mécanisme
réussit et l'autre échoue sur le même citoyen. Mais l'inspection directe montre que ce n'est pas
un sous-ensemble de cas structurellement difficiles : **`will_act=True` pour les 70/70 citoyens,
dans les DEUX tests, sans exception.** Le recouvrement parfait est une conséquence mathématique
de deux fonctions constantes (toujours « oui »), pas la signature d'une disposition de contenu
sur des profils précis. Il n'y a aucune variation à tracer par citoyen — la question « qu'ont ces
cas en commun » n'a pas de réponse de contenu, parce qu'il n'y a pas de sous-ensemble : c'est
100% des citoyens, indépendamment de leur profil.

**Reformulation retenue** : la question qui reste ouverte n'est pas « quel profil de citoyen pose
problème » mais « ce collapse vers une réponse affirmative/engagée en isolation est-il propre à
`pressure_action`, ou une propension générale du modèle sur n'importe quelle décision binaire
isolée dont une réponse ressemble à s'engager/agir ? ».

**Protocole, pré-enregistré avant tout appel** : sonde `candidacy_considered` (vérité de
référence disponible : `decide_candidacy`, `citizen.ambition_score >= config.candidacy.
ambition_threshold`, seuil livré 0,30) sur des citoyens dont `ambition_score` est **loin** en
dessous du seuil (pas juste légèrement) — `size=1`, `think=False`, prompt/schéma de production
réels, aucune modification.

- **Si le modèle dit systématiquement « se présente » (outcome=1) même sur ces cas extrêmes** →
  confirme une disposition générale du modèle en isolation single-decision, indépendante du type
  de décision. Dépasse largement `pressure_action` — redirige l'investigation vers un phénomène
  plus large (potentiellement le fine-tuning instruct sous-jacent de qwen3, biaisé vers des
  réponses actives/engagées par défaut hors contexte conversationnel riche).
- **Si `candidacy_considered` reste correct sur ces cas** (dit « renonce » correctement) →
  confirme que le problème est spécifique à `pressure_action`, pas une disposition générale —
  rouvre la question de ce qui, dans CE type de décision précis (le cadre citoyen-vs-autorité,
  le mot « pression »), déclenche le biais.

Ce résultat prime sur §3.3 dans les deux cas — il détermine si le problème à résoudre est
« améliorer le prompt de pressure_action » ou quelque chose de bien plus large.

**Résultat, 2026-08-30** (`check_candidacy_considered_isolation_disposition.py`) : 5 citoyens à
`ambition_score` extrêmement bas (0,0069 à 0,0214 — 14x à 43x sous le seuil livré de 0,30), même
discipline d'isolation (`size=1`, `think=False`, prompt/schéma de production réels, aucune
modification).

```
5/5 correct -- outcome=0 (renonce) pour les 5 citoyens, motif=204 a chaque fois
```

**`candidacy_considered` reste correct sur ces cas extrêmes en isolation totale.** Deuxième
lecture pré-enregistrée confirmée : **le collapse est spécifique à `pressure_action`, pas une
disposition générale du modèle envers les réponses affirmatives/engagées en isolation.** Écarte
l'hypothèse d'un biais général du fine-tuning instruct de qwen3 (au moins pour ce type de
décision) — le problème reste local à la façon dont `pressure_action` pose sa propre question, pas
au fait de poser UNE question binaire isolée en général. Rouvre, sans y répondre : qu'est-ce qui,
spécifiquement dans le cadrage de `pressure_action` (citoyen-vs-autorité, la notion de « pression »
elle-même, le contenu du ctx) déclenche ce collapse alors qu'un cadrage structurellement similaire
(`candidacy_considered` : ambition vs seuil, soutien perçu, décision binaire déclare/renonce) ne le
déclenche pas.

**Conséquence pour §3.3** : la piste reste pertinente (le problème est bien dans le cadrage de
`pressure_action`, pas un phénomène général indépendant du prompt) mais son fondement causal
reste à préciser — ce n'est plus seulement « ancrer par l'exemple » en général, c'est comprendre
pourquoi `pressure_action` spécifiquement diffère de `candidacy_considered`, structurellement
proche mais épargnée.

### 3ter. Découverte de portée plus large — déplacée dans son propre document

Le test sur `representative_response` (l'autre décision à cadrage citoyen-vs-autorité/cible) a
confirmé le même collapse content-blind, chiffre pour chiffre comparable à `pressure_action`.
Vérifié ensuite sur `coalition_decision` et `reaction_to_event` (branche SCANDAL) : les deux
collapsent aussi. Seul `candidacy_considered` (cadrage purement autoréférentiel) n'collapse pas.

**Ceci dépasse le périmètre de ce document** — ce n'est plus « `pressure_action` a besoin de
remédiation » mais potentiellement « toute décision formulée comme un acte/une réponse (pas une
auto-évaluation à seuil) risque un collapse content-blind en isolation », un principe de
conception à auditer (théorie affinée deux fois : ni « acteur externe nommé » ni « ton
adversarial » ne tenaient sur `representative_response`/`coalition_decision` une fois vérifiés
précisément — voir le document pour l'historique complet). Preuves complètes, protocole, et la
question de portée (documentée dans le design doc §3.6.0) : **`plan-adversarial-framing-collapse.md`**.

**§3.3 en pause, par instruction directe (2026-08-30)** : le problème semble structurel à la
forme acte/réponse de la décision elle-même (4/4 types formulés ainsi collapsent, 2/2
auto-évaluations à seuil — dont `party_nomination_choice`, testé après coup — ne collapsent pas ;
voir `plan-adversarial-framing-collapse.md`), pas spécifique au prompt de `pressure_action` — une
reformulation locale par l'exemple a donc moins de valeur tant que le mécanisme exact
(pourquoi la forme acte/réponse déclenche le collapse) n'est pas mieux compris. La piste reste
pertinente et pourrait même être informée par cette découverte une fois digérée, mais n'est pas
relancée maintenant. Ce chantier reprendra une fois la découverte plus large mieux comprise, pas
avant.

### 3.2 Langage primaire + traduction algorithmique
Repense le **format de sortie** : le modèle produit une réponse en
grammaire minimale mais stricte (ex. lignes `SITUATION:` / `DÉCISION:` /
`MOTIF:`), traduite en JSON final par un parseur purement algorithmique
(pas un second appel LLM). Hypothèse : le remplissage direct d'un objet
JSON complet pousse vers un "auto-complétion sûre" ; une étape
d'articulation intermédiaire réduit cette pression.

### 3.3 Few-shot avec exemples travaillés
Repense **l'ancrage du prompt**, sans toucher à la structure du choix
ni au format : ajouter 1-2 exemples concrets et travaillés dans le
prompt, montrant explicitement un citoyen à ratio extrême recevant un
code d'action correct avec son motif. Hypothèse : ancre le modèle sur un
précédent concret plutôt que sur une règle abstraite déjà écartée par
l'ablation de §1.

### 3.1 — Résultat, 2026-08-30 : ÉCHEC net, et le même collapse revient sous une forme différente

`check_pressure_action_binary_lever_redesign.py` (nouveau, committé) implémente uniquement
l'étage 1 (jugement binaire agir/ne-pas-agir) — pas l'étage 2 (choix du levier), volontairement :
le critère d'accord de ce chantier n'a jamais porté que sur agir-vs-ne-pas-agir, construire
l'étage 2 avant de savoir si l'étage 1 passe son propre seuil aurait été de l'ingénierie
prématurée. Schéma/prompt locaux, isolés (rien touché dans `llm_schemas.py`/
`llm_behavior_engine.py`). Données : `self_gap`/`blank_threshold` recalculés de façon
déterministe (aucun appel LLM nécessaire pour construire les cas de test) contre un élu
`cid=5` frais via `declare_candidacy` (position non biaisée par un campaign_positioning LLM —
vérifié explicitement : `self_gap(cid=87, cet élu)=0,1648` contre `0,1777` dans le journal réel du
pilote, un écart réel et attendu, pas une incohérence — un élu sincère non modéré a une position
plus extrême qu'un élu ayant subi un shift de campagne). `population_size=190` → 70 citoyens non
ambigus (17 « devrait agir », 53 « ne devrait pas agir »), au-dessus du plancher de 60 (§4.1).

```
checked: 70/70 (0 échec de décodage)
accord avec la vérité de référence (agir vs ne pas agir) : 17/70 (24,3%)
seuil pré-enregistré : >= 80%
```

**Échec net, largement sous la barre.** Le chiffre 17/70 n'est pas un hasard d'accord partiel —
vérifié directement (pas seulement déduit de l'arithmétique) sur un échantillon de 6 citoyens (3
« devrait agir » à ratio extrême, 3 « ne devrait pas agir » à ratio extrême) : **`will_act=True`
dans les 6 cas, quel que soit le ratio réel.** Le nouveau schéma binaire ne s'est pas contenté
d'échouer — il a reproduit EXACTEMENT le même phénomène de collapse content-blind déjà
caractérisé pour le schéma à 5 voies, mais bascule vers le pôle OPPOSÉ (toujours « va agir » au
lieu de toujours « n'agit pas », qui était le collapse observé en production/size=1 sur le schéma
original). Les 17/70 corrects correspondent exactement aux 17 cas où la vérité de référence
attendait « agir » — le modèle a simplement dit « oui » à tout le monde.

**Conséquence, par le protocole §4.3** : ceci est un résultat réel et informatif, pas un échec à
retenter avec un critère assoupli. Séparer le jugement agir/ne-pas-agir du choix du levier n'a
pas empêché le modèle de « retomber » sur une réponse fixe, sur un batch d'une seule décision
malgré tout — ça affaiblit directement l'hypothèse « la structure à 5 voies du menu est la
cause » (une hypothèse plus fine serait nécessaire pour l'expliquer encore), et redirige la
priorité vers §3.2 (format de sortie) ou §3.3 (ancrage par l'exemple) avec un argument plus fort
qu'un choix a priori — pas vers une combinaison de pistes, puisque §3.1 seule ne montre aucun
signal positif partiel (le critère du §4.3.3 pour justifier un croisement n'est pas rempli).

## 4. Protocole de test strict — éviter le tâtonnement

**Principe directeur, non négociable** : ne jamais tester plusieurs
variantes de prompt sur un petit échantillon et choisir celle qui
"marche le mieux" a posteriori. Ce chantier a déjà mesuré qu'un taux
peut passer de 25% à 41,7% en doublant simplement la taille de
l'échantillon (sans changer la méthode) — sur un échantillon de cette
taille, une variante peut sembler gagnante par pur hasard
d'échantillonnage.

### 4.1 Taille d'échantillon minimale, fixée avant tout test

Compte tenu de l'instabilité déjà mesurée entre n≈30 et n≈60, **aucun
test de ce protocole ne doit conclure sur un échantillon inférieur à
60 citoyens non ambigus** (le point où le taux s'est stabilisé la
dernière fois, sans garantie que ce soit suffisant — à traiter comme un
plancher, pas une cible).

### 4.2 Pré-enregistrement individuel par piste

Pour chacune des trois pistes (§3.1-3.3), avant de lancer le moindre
appel :
- Hypothèse causale explicite (pourquoi cette piste devrait résoudre le
  collapse, pas seulement "on va essayer").
- Critère de succès numérique fixé à l'avance (proposition : ≥ 80%
  d'accord avec la vérité de référence sur cas non ambigus — sous la
  barre de 90% des autres sondes, parce qu'une piste de remédiation
  n'a pas besoin d'égaler la fiabilité déjà exigée d'une méthode de
  validation, juste de sortir clairement de l'état dégénéré actuel;
  à débattre avant de lancer).
- Critère d'échec explicite (ex. le pattern de collapse persiste
  identiquement, ou une bascule vers un nouveau mode dégénéré comme
  observé lors de la réduction de taille).

### 4.3 Ordre de test, informé par l'étape 0

1. Résultat de la perturbation de température (§2.1) et du biais d'ordre
   (§2.2) d'abord — ils orientent quelle(s) piste(s) de refonte tester
   en priorité, pas un ordre arbitraire.
2. Tester chaque piste **isolément** avant toute combinaison — jamais
   deux changements à la fois en premier passage, pour pouvoir attribuer
   un effet observé à sa cause.
3. **Croisements, seulement après qu'au moins une piste isolée montre un
   signal positif partiel** (pas un succès complet, mais un mouvement
   réel vers la vérité de référence) — sinon combiner deux pistes qui ne
   font rien seules n'a aucune raison de faire quelque chose ensemble,
   et ce serait un test coûteux pour une hypothèse non motivée.
4. Si des croisements sont justifiés : prioriser les paires plutôt que
   les trois pistes combinées d'emblée — plus simple à interpréter,
   moins coûteux à invalider si le résultat est négatif.

### 4.4 Garde-fou contre le fishing

- Toute variante testée (y compris une reformulation mineure d'une des
  trois pistes) doit être nommée et son hypothèse écrite **avant**
  observation du résultat — pas de génération de multiples variantes en
  parallèle suivie du choix de la "meilleure".
- Un résultat qui échoue à son propre critère pré-enregistré est
  documenté comme échec, pas retesté avec un critère assoupli après
  coup.

## 5. Sortie attendue

1. Tableau corrigé du test cross-modèle (§1), verdict du script mis à
   jour.
2. Résultats de l'étape 0 (§2.1, §2.2), avec la priorisation des trois
   pistes de refonte qui en découle.
3. Résultat de la première piste isolée testée, contre son critère
   pré-enregistré — présenté avant de décider de la suivante.
4. Aucune implémentation en production tant qu'une piste (seule ou
   combinée) n'a pas dépassé son critère de succès sur un échantillon
   ≥ 60 citoyens non ambigus.
