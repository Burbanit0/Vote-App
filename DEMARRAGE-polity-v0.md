# Démarrage du chantier Polity — v0

> Document de transmission. À déposer à la racine du repo Vote-App aux
> côtés de `polity-simulation-design-v2.md`, ou à copier dans Claude Code
> comme prompt de démarrage (même convention que
> `prompt-liquid-democracy-conviction-voting.md`).
>
> Objectif : ouvrir le chantier v0 — squelette mécanique pur, 100
> citoyens, aucun LLM — avec un périmètre entièrement spécifié.

---

## 1. Opérations préalables sur les fichiers du projet

À faire **avant** d'écrire la première ligne de code.

### 1.1 Remplacer le plan de conception

`polity-simulation-design-v2.md` **remplace**
`polity-simulation-design.md`. Ne pas conserver les deux : c'est
exactement le mode de défaillance identifié dans le plan lui-même
(section « Périmètre exclu ») — un concept vivant dans deux documents
jamais réconciliés. Supprimer l'ancien, ou l'archiver hors du répertoire
de travail.

### 1.2 Remplacer la configuration

`polity_config.yaml` est fourni en version complète (fichier joint). Il
conserve la convention de marquage `[v0]`..`[v8]` du fichier existant et
ajoute les blocs des révisions 2b/2c, tous inactifs en v0.

### 1.3 Corriger `docs/research/traceability.md`

Liquid Democracy y figure **deux fois**, dans deux tableaux distincts
(« extensions en cours » et « systèmes alternatifs de gouvernance »).
Ne conserver qu'une seule ligne, celle du chantier `engine/utils`, et y
ajouter la mention : *hors périmètre du simulateur polity*.

### 1.4 Annoter l'audit de précision

`audit-precision-plan.md` reste utile comme trace historique. Ajouter une
ligne en tête renvoyant au tableau « État des bloquants » de
`polity-simulation-design-v2.md`, qui fait désormais autorité.

---

## 2. Périmètre de la v0 — ce qui est dans le lot

Cible : le palier v0 du §13 du plan. Squelette mécanique pur, 100
citoyens, 120 ticks (30 ans × 4 trimestres), décisions déterministes,
**aucun appel LLM**.

Objectif unique : valider la mécanique institutionnelle en vase clos.

**Point important pour le cadrage** : les trois révisions de conception
les plus récentes (canaux de pression §7bis, schéma LLM §3.6, codebook
§3.7, parallélisation §15bis) portent toutes sur les paliers v2 et v4. La
v0 n'en est pas affectée. Le périmètre ci-dessous est stable et ne
subira pas de remaniement pendant l'implémentation.

### Décisions déjà tranchées, à respecter sans les rediscuter

| Sujet | Décision | Réf. |
|---|---|---|
| Unité de temps | 1 tick = 1 trimestre, 120 ticks | §6 |
| Partis | 5 fixes, k-means sur positions citoyennes, ni naissance ni mort | §A2 |
| Rôles | `role` + `office` + `term_end_tick` | §2.1 |
| Sièges | 100, D'Hondt, seuil 5 % | §6 |
| Candidature indépendante | seuil de signatures 1 % ; chemin de rupture désactivé en v0 | §2.4 |
| Légitimité | désactivée (`legitimacy.enabled: false`) | §7 |
| Journal | JSONL append-only, `event_id` séquentiel, snapshot tous les 4 ticks | §16 |

---

## 3. Modules à écrire — voir `dev-plan-v0-worktree.md`

Le découpage en 9 lots et leurs contrats de test restent **valides
intégralement**. Ne pas le réécrire, le suivre.

Rappel de la règle de séquencement : *ne pas commencer un lot tant que
les tests du précédent ne passent pas.*

Deux compléments apportés par les révisions récentes :

### 3.1 Lot 2 — `citizen.py`

Ajouter deux champs au schéma d'état, inutilisés en v0 mais qui évitent
une migration en v4 :

- `mandates_served: int` — compteur de mandats accomplis (§6bis.1)
- `pledged_platform` / `revealed_position` — en v0, `revealed_position`
  est figée égale à `pledged_platform` (§7bis.5)

Ce choix est délibéré : la déviation de mandat est **nulle par
construction** sans LLM, ce qui fait de la v0/v1 le groupe de contrôle
contre lequel mesurer l'apport du LLM en v2 (§11.4).

### 3.2 Lot 7 — `journal.py`

Le journal doit porter dès maintenant les champs `run_id`, `event_id`,
`tick`, `citizen_id`, `event_type`, `payload`. Le champ
`codebook_version` (§3.7) peut être présent et vide en v0.

Ne **pas** implémenter le codebook lui-même en v0 : aucune décision LLM
n'est produite, donc aucun code à traduire.

---

## 4. Le seul point encore ouvert dans le périmètre v0

### A5 — règle de départage de coalition

Le plan spécifie « plus proche voisin idéologique jusqu'à majorité » sans
préciser trois cas limites. **Proposition à valider avant le lot 6** (les
lots 1 à 5 n'y touchent pas — le chantier peut démarrer sans attendre) :

1. **Parti initiateur** : le parti ayant obtenu le plus de sièges. En cas
   d'égalité de sièges, celui ayant obtenu le plus de voix ; si égalité
   encore, le plus petit `party_id` (départage déterministe explicite,
   jamais un ordre d'itération implicite — sinon la reproductibilité
   dépend d'un détail d'implémentation).
2. **Ordre d'agrégation** : distance euclidienne croissante entre
   plateformes, partis ajoutés un à un jusqu'à franchir 50 % des sièges.
   Égalité de distance départagée par nombre de sièges décroissant, puis
   `party_id`.
3. **Échec** : si l'ajout de tous les partis ne produit pas de majorité
   (impossible à 100 sièges sans abstention parlementaire, mais à coder
   défensivement), journaliser un événement `coalition_failed` et laisser
   l'assemblée sans coalition de gouvernement pour la législature.

Le point 1 et le point 2 ont la même exigence de fond : **tout départage
doit être explicite**. Un `max()` sur un dictionnaire ou un tri instable
introduit une dépendance à l'ordre d'insertion qui casserait le test de
reproductibilité octet-pour-octet sans laisser de trace lisible.

---

## 5. Tâche parallèle, indépendante du code

### Protocole de vérification du déterminisme (§15bis.5)

À exécuter **dès maintenant**, en parallèle des lots 1 à 5. Ne dépend pas
du simulateur : il suffit d'un conteneur vLLM (ou Ollama) et d'un prompt
quelconque.

1. Même prompt exact, soumis dans des batchs de tailles 1, 5, 25, 50.
   Comparer les sorties octet pour octet.
2. Même batch, même taille, dix exécutions consécutives. Comparer.
3. Répéter après redémarrage du conteneur.

**Pourquoi maintenant** : le plan suppose que `temperature = 0` + modèle
épinglé suffisent à garantir la reproductibilité (B2). Cette hypothèse
n'a jamais été vérifiée, et elle conditionne le test le plus important
du projet. Si elle est fausse, il vaut infiniment mieux le découvrir
avant d'écrire `llm_behavior_engine.py` que six mois plus tard.

Consigner le résultat dans le repo, quel qu'il soit.

---

## 6. Le test qui compte plus que les autres

**Reproductibilité de bout en bout** : deux runs complets à graine
identique produisent des journaux **identiques octet pour octet**.

À écrire **dès le lot 8**, pas après. C'est le garde-fou qui détectera
toute fuite de non-déterminisme quand le LLM arrivera en v2 — et compte
tenu de l'incertitude sur le batching (§5 ci-dessus), il vaut encore plus
cher que ce que le dev-plan initial anticipait.

Points de vigilance classiques pour ce test : ordre d'itération des
dictionnaires, `set` non ordonnés, `hash()` de chaînes (randomisé par
défaut en Python — fixer `PYTHONHASHSEED` ou ne jamais en dépendre),
horodatages dans le journal, tri instable.

---

## 7. Définition de « v0 terminée »

- [ ] Les fichiers de la §1 sont remplacés/corrigés
- [ ] Un run de 30 ans / 100 citoyens s'exécute de bout en bout
- [ ] Le test de reproductibilité passe (journaux identiques)
- [ ] Le calendrier produit le bon nombre de scrutins aux bons ticks
      (8 présidentielles, 8 législatives sur 120 ticks)
- [ ] `ballot_and_aggregation.py` est en parité avec le golden-fixture
      harness existant
- [ ] Les 3 métriques v0 sont calculées et exportées (Laakso-Taagepera,
      taux de cohabitation, durée de vie des coalitions)
- [ ] CI locale verte (Ruff, mypy strict, Bandit, Semgrep)
- [ ] Le protocole §5 est exécuté et son résultat consigné
- [ ] `THEORY.md` / `traceability.md` mis à jour via `/sync-theory`

**Critère de passage à la v1** : pouvoir répondre à « sur ces 30 ans,
combien de cohabitations, et combien de partis effectifs en fin de
période ? », et que la réponse soit stable d'un run à l'autre à graine
constante.

---

## 8. Ce qu'il ne faut surtout pas faire en v0

- **Aucun appel LLM**, même « juste pour tester ». Le palier existe
  précisément pour isoler les bugs mécaniques.
- **Aucune visualisation** (§14) : le journal JSONL suffit à valider.
- **Aucun canal de pression** (§7bis) : c'est v4.
- **Aucun événement exogène** (§8) : c'est v5.
- **Aucun graphe social** (§5) : c'est v6.
- **Pas d'optimisation de performance** : 100 citoyens × 120 ticks est
  trivial même en Python naïf. Vectoriser prématurément rendrait le
  débogage plus difficile.
- **Aucune constante institutionnelle en dur** : tout paramètre passe par
  `polity_config.yaml`. C'est la condition pour pouvoir comparer deux
  configurations constitutionnelles plus tard.

---

## 9. Conventions du repo à respecter

Reprises de `CONTRIBUTING.md` et du dev-plan :

- worktree dédié : `git worktree add -b feat/polity-v0 ../Vote-App-polity origin/develop`
- branche depuis `develop`, jamais `main` ; PR vers `develop`
- CI locale verte avant push : Ruff, mypy strict, Bandit, Semgrep
- typage strict, docstrings au format du reste du repo
- **aucune dépendance nouvelle sans justification explicite**
- aucune référence académique ajoutée qui ne soit pas déjà dans
  `bibliography.bib` ou validée explicitement
