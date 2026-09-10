# Synthèse — ce que le programme LLM a établi au 10/09/2026

Document de conclusion intermédiaire. Il résume ce qui a été **mesuré**, ce qui reste
**suggéré mais non établi**, et ce qui a été **éliminé**. Chaque affirmation renvoie au
script et au results doc qui la porte ; rien ici n'est un résumé de raisonnement, tout
vient d'une mesure en direct contre le vrai serveur.

---

## 1. Le résultat principal : on sait enfin *mesurer* le collapse

Avant ce programme, le « collapse » était une inférence tirée de 4 à 6 cas construits à la
main, avec un tirage catégoriel par cas. C'était le goulot : **on ne peut pas réparer ce
qu'on ne sait pas mesurer.**

Le §5.C a résolu le vrai problème dur, celui que le premier incrément avait explicitement
laissé ouvert : **localiser le token qui porte la décision à l'intérieur d'une complétion
réelle contrainte par xgrammar**. Deux difficultés distinctes, résolues séparément :

1. **Le décalage du reasoning parser** — `content` est amputé du bloc `<think>`, alors que
   `tokens` couvre toute la génération brute. Un parcours d'offsets naïf est donc désaligné
   dès que `think=True`. Corrigé en reconstruisant le texte brut et en y localisant `content`
   comme sous-chaîne.
2. **L'alignement champ → token**, apparié à chaque `cid` via l'ordre documentaire.

Un troisième piège a été trouvé **en production, pas en théorie** : le codebook de motifs de
ce projet groupe ses codes par chiffre de tête partagé (401/402/403, 501/502/504/505…).
L'ancrage « premier caractère » renvoyait alors un token identique quelle que soit la valeur
à venir — non pas faux, mais **non informatif**, et `binary_probability` retournait son 0,5
« aucun candidat capturé » documenté, ce qui **ressemble à une vraie mesure**. Corrigé par un
paramètre `value_char_offset` (défaut rétrocompatible), avec les tests qui vont avec.

**Validation avant usage**, sur le seul type de décision qui a une vérité terrain
(`vote_cast` / `simple_rules.build_ranking`) : **16/16 alignements, 16/16 décisions correctes**,
séparation 0,997 (vérité=blanc) contre 0,049 (vérité=non-blanc). L'instrument est fiable avant
d'avoir servi à conclure quoi que ce soit.

---

## 2. Ce que l'instrument a trouvé : trois collapses quantifiés, dont un invisible

| Type de décision | Mesure en continu | Statut |
|---|---|---|
| `pressure_action` | P(act=4) ≥ 0,976 pour **chaque** citoyen, séparation +0,004 | Collapse **réel et nouveau** |
| `representative_response` | P(stance=1) = 1,000000 ± **0,000001** sur 9 points | Collapse **affiné** |
| `coalition_decision` | P(action=1) = 0,965–0,999 partout, y compris à taille de batch réelle | Collapse **confirmé et étendu** |
| `reaction_to_event` (ECONOMIC_SHOCK) | P(motif=402) = 1,0 à **toutes** les magnitudes | Mesuré, pas classé comme collapse |

### Le collapse que les métriques agrégées ne pouvaient pas voir

`pressure_action` est le résultat le plus important, et il était **structurellement invisible**.
Sous le menu fermé shippé (`electoral_only=true`), le choix légal se réduit à
{0 = ne rien faire, 4 = attendre l'élection}. Toutes les mesures antérieures avaient été prises
avec le menu **artificiellement ouvert** — configuration qu'aucun run réel n'utilise.

Résultat : P(act=4) ≥ 0,976 pour **tous** les citoyens, y compris le plus satisfait possible
(self_gap = 0,02, là où le proxy déterministe dit « ne rien faire »). Séparation satisfait /
mécontent : **+0,004**. Écarté comme artefact de batching par un contrôle en solo
(séparation +0,000008, encore plus plate).

**Pourquoi c'était invisible** : un taux plat d'act=4 sous menu fermé produit exactement le
`mobilization_rate` agrégé que le menu prédit déjà par construction. Aucune anomalie ne pouvait
émerger d'une métrique de population — seule une lecture P(act) **au niveau du citoyen** le
révèle. C'est un argument méthodologique qui dépasse ce projet : *une métrique agrégée peut
être parfaitement conforme et masquer une décision individuelle entièrement dégénérée.*

---

## 3. Ce qui a été éliminé : l'hypothèse d'alignement

§2 proposait que les collapses viennent du fine-tuning d'instruction (RLHF poussant le modèle
vers un attracteur sûr quand on lui demande de commettre un acte qui atterrit sur autrui) et
présentait le test base-vs-instruct comme décisif dans un sens ou dans l'autre.

**Le cadrage a d'abord dû corriger la forme du test** (§2bis) : `Qwen3-8B-Base` n'existe qu'en
bf16 (~16 Go de poids sur une carte de 16,3 Go), et **toute la famille Qwen3 ne compte qu'un
seul AWQ officiel** — précisément le modèle instruct déjà shippé. Le seul AWQ du modèle de base
est un requant communautaire à 5 téléchargements, qui aurait confondu la qualité du requant avec
la variable testée. Forme retenue : paire bf16 `Qwen3-4B` / `Qwen3-4B-Base` — même famille,
taille, précision, template, mêmes flags de service ; **seul le fine-tuning d'instruction
diffère**. Déblocage décisif au passage : les modèles de base Qwen3 embarquent le **même chat
template** que les instruct, donc aucune modification du client n'a été nécessaire.

### Verdict

| Type | Observation | Portée |
|---|---|---|
| `representative_response` | **Aucun collapse** sur le bras 4B *instruct* | Alignement **non nécessaire** : un modèle instruct traite le cas correctement |
| `coalition_decision` | Collapse **identique** avec et sans fine-tuning | **Contredit** l'hypothèse |
| `pressure_action` | Récupération partielle sur le bras base | Seul soutien — sous la barre, et le contrôle le désamorce |

Le seul signal positif a été répliqué sous une **seconde géométrie de sonde** (autres cids,
autres valeurs de self_gap, autres constantes d'appel, ordre de batch inversé) — et non avec
d'autres graines, ce qui n'aurait **rien** fait varier à `temperature=0` où l'échantillonnage
est un argmax. Le signal s'est **renforcé** (r : +0,378 p=0,135 → **+0,685 p=0,0024**)…
**mais le bras instruct aussi** (r=+0,494, p=0,044). « Le base suit self_gap, l'instruct non »
n'est donc pas soutenu.

**Conclusion : l'hypothèse d'alignement ne survit pas comme explication générale.** Elle est
contredite sur `coalition_decision`, inutile sur `representative_response`, et seulement
faiblement soutenue sur `pressure_action` — jamais au-dessus de la barre pré-enregistrée.

---

## 4. Trois régularités transversales

### 4.1 Le pôle du collapse est labile ; la platitude ne l'est pas

La constante vers laquelle `pressure_action` collapse a changé **trois fois** sans que sa
platitude bouge :

| Configuration | Collapse vers |
|---|---|
| 8B-AWQ instruct, prompt JSON | `act=4` (attendre l'élection) |
| 8B-AWQ instruct, prompt TOON | `act=0` (ne rien faire) |
| 4B-bf16 instruct, prompt JSON | `act=0` (ne rien faire) |

Le format de surface et l'identité du modèle déplacent tous deux *quel* constant est choisi ;
**aucun ne restaure la sensibilité au contenu**. Ce que l'on cherche est robuste à des
changements qui retournent pourtant sa sortie — contrainte forte sur le mécanisme.

### 4.2 Le contexte de niveau appel écrase le signal par citoyen

Trouvaille latérale de la réplication, et sans doute la plus actionnable. Sur le **même bras**,
en ne changeant que les constantes d'appel (`mandate_dev`, `ticks_to_election`, `target`) :
P(act=4) passe de ≈0,53–0,99 à ≈0,007–0,47 — **jusqu'à deux ordres de grandeur** — alors que
`self_gap`, le signal *par citoyen* dont la décision est censée dépendre, le déplace bien moins
à l'intérieur d'un même appel.

Attribution prudente (plusieurs constantes ont changé ensemble), mais cela caractérise l'échec
bien plus finement que « collapse » : **le modèle répond surtout au contexte partagé, très peu
à l'état propre du citoyen.**

### 4.3 La probabilité bouge là où la décision ne bouge pas

Dans les quatre cellules du 2×2 base/instruct × géométrie A/B, **la décision émise est
totalement collapsée** (toujours la même constante) — mais la probabilité sous-jacente, elle,
corrèle avec `self_gap` (jusqu'à r=+0,685). Le signal existe dans la distribution ; c'est
l'argmax qui le jette.

Un contrôle est offert gratuitement par la paire de géométries : A batchait en ordre croissant,
B en décroissant ; un artefact de position aurait **changé de signe**. Il ne l'a pas fait — la
corrélation est un effet `self_gap` réel.

**C'est exactement le mécanisme que §3.A.1 décrit**, et c'en est désormais la preuve empirique
plutôt que l'intuition : décodage glouton sur une distribution faiblement discriminée ⇒ sortie
constante. C'est ce qui fait de §3.A.1 la prochaine étape la mieux motivée.

---

## 5. Débit et format : ce qui a payé, ce qui n'a pas payé

**Gains sans contrepartie** (vérifiés en direct, déterminisme préservé) :
- **Continuité du cache de préfixes** (§3.B.7) : la liste de cids par chunk, embarquée en fin de
  system prompt, cassait le cache pour *chaque* chunk. Déplacée vers un champ `expected_cids` du
  user prompt → hit rate 65,2 % → 73,0 % en montée sur une rafale (`vote_cast`). Pour
  `chamber_deliberation`, le system prompt ne dépend désormais plus **du tout** des membres : il
  devient une constante pour tout un run.
- **Décodage spéculatif n-gram** (§3.B.6) : sans perte par construction à `temperature=0`,
  vérifié **octet pour octet**.
- **Précision des flottants** (§5.B) : 2 décimales sur les vecteurs lus holistiquement, en
  excluant explicitement `distances`/`blank_threshold` (comparaison seuil-à-seuil qui a déjà
  produit un collapse à 100 % blanc).

**TOON (§5.E) : la porte qualité tranche différemment selon le type.**

| Type | Tokens | Qualité | Verdict |
|---|---|---|---|
| `candidacy_considered` | **−6,9 %** | **identique** (16/25 = 16/25) | Passe |
| `pressure_action` | **−44,0 %** | **échoue** | Rejeté malgré le gain |

Sur `pressure_action`, TOON ne restaure pas la sensibilité : il **fait basculer la constante**
du collapse (toujours act=4 → toujours act=0), et sur le proxy disponible la nouvelle constante
fait *moins* bien qu'une base triviale « toujours prédire la classe majoritaire ». C'est la
confirmation concrète de la réserve n°2 écrite **avant** tout test : *token count ≠
compréhension*. Le gain de 44 % est réel et ne suffit pas.

---

## 6. Corrections apportées à nos propres affirmations

Ce programme a autant corrigé le projet qu'il l'a étendu :

- **Le bug critique de `vote_cast`** : la règle de troncature §3.6.1 était appliquée par le
  validateur mais **jamais communiquée dans le prompt** pour le cas tronqué — échec quasi total
  de `vote_cast` aux élections à population 500. Trouvé dans les données de la sonde d'échelle
  elle-même, corrigé, vérifié en direct 3 fois.
- **L'affirmation centrale de §1 était fausse** : « les quatre types compromis sont exactement
  les quatre inter-individuels » ne tient pas. La ligne `reaction_to_event` était périmée (son
  collapse SCANDAL était **déjà résolu sur vLLM** avant l'ouverture de ce document). Seuls
  **trois** des quatre portent un collapse confirmé. La moitié qui survit, et qu'il faut garder :
  *tout collapse confirmé est inter-individuel, mais inter-individuel n'implique pas collapse.*
- **Une recommandation méthodologique invalide** : « répliquer avec 2-3 graines » — impossible à
  `temperature=0` où le seed n'influence pas l'échantillonnage. Corrigée avant d'avoir coûté une
  après-midi GPU.

---

## 7. Où cela laisse le programme

**Acquis** : la mesure (§5.C), trois collapses quantifiés, les gains de débit sans contrepartie
(§3.B.6/7, §5.B), et l'élimination de l'hypothèse d'alignement (§2).

**Éliminé** : l'alignement comme explication générale ; TOON sur `pressure_action`.

**Prochaine étape la mieux motivée — §3.A.1, échantillonnage déterministe par citoyen.**
Elle n'est plus une intuition : §4.3 ci-dessus en fournit la preuve empirique. La distribution
porte le signal, l'argmax le détruit. Deux faits nouveaux la cadrent :

- `coalition_decision` collapse **identiquement** avec et sans fine-tuning d'instruction → le
  problème est dans la construction du prompt/de la tâche, pas dans le post-training ;
- le contexte de niveau appel écrase le signal par citoyen (§4.2) → toute correction devra agir
  sur **comment le signal propre au citoyen est présenté et résolu**.

**Réserves permanentes**, à ne pas perdre de vue : tout ceci reste **une graine** et, pour les
mesures 4B, **un run par bras** ; le contraste 8B-vs-4B est confondu trois fois (nombre de
paramètres, recette de post-training, quantification) ; et une distribution simplement plus
diffuse peut imiter une faible sensibilité.
