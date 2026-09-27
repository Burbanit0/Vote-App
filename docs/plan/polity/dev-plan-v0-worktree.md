# Plan de développement v0 — Worktree `polity`

> Cible : le palier **v0** du §13 — squelette mécanique pur, 100 citoyens,
> décisions déterministes simplifiées, aucun LLM. Objectif unique : valider
> la mécanique institutionnelle en vase clos.
>
> Prérequis : avoir tranché les bloquants v0 de `audit-precision-plan.md`
> (A1 à A6, C1, D9).

---

## 1. Mise en place du worktree

Le worktree isole ce chantier du reste du repo sans dupliquer le clone, ce
qui permet de continuer à travailler sur `develop` en parallèle.

```bash
# depuis la racine du repo Vote-App
git fetch origin
git worktree add -b feat/polity-v0 ../Vote-App-polity origin/develop
cd ../Vote-App-polity
```

Arborescence résultante :
```
Vote-App/              # worktree principal (develop)
Vote-App-polity/       # worktree du chantier polity
```

Conventions à respecter (cohérentes avec `CONTRIBUTING.md` existant) :
- branche depuis `develop`, pas `main` ;
- PR vers `develop` en utilisant `.github/PULL_REQUEST_TEMPLATE.md` ;
- la CI locale (`ci-local/`) doit passer avant push : Ruff, mypy strict,
  Bandit, Semgrep.

Nettoyage en fin de chantier :
```bash
git worktree remove ../Vote-App-polity
```

---

## 2. Décisions à figer dans `polity_config.yaml` (D9)

Fichier unique de configuration, source de vérité de tous les paramètres —
à créer **avant** le premier module, pour éviter les constantes dispersées
en dur.

```yaml
run:
  seed: 42
  ticks_per_year: 4          # A1 — trimestre
  duration_years: 30
  population_size: 100       # §11.1

institutions:
  president_term_years: 4
  assembly_term_years: 4
  assembly_offset_years: 2   # §6, paramétrable
  assembly_seats: 100
  seat_allocation: dhondt    # A4
  electoral_threshold: 0.05
  presidential_method: two_round
  assembly_method: proportional

parties:
  initial_count: 5           # A2
  init_strategy: kmeans_on_citizens
  birth_enabled: false
  death_enabled: false

citizens:
  issue_count: 20
  blank_threshold_dist: beta(3,5)
  static_population: true    # D1 — pas de mortalité en v0

candidacy:
  ambition_threshold: 0.7            # A5
  independent_signature_ratio: 0.01  # C1
  rupture_path_enabled: false        # activé en v1

legitimacy:
  enabled: false             # activé en v4 seulement

journal:
  format: jsonl
  snapshot_every_ticks: 4    # §16.4, une fois par an simulée
```

---

## 3. Modules à écrire, dans l'ordre, avec leur contrat

Chaque module est un lot de travail autonome, testable seul. **Ne pas
commencer le suivant tant que les tests du précédent ne passent pas.**

### Lot 1 — `config.py` + `polity_config.yaml`
Chargement typé (dataclass + validation), aucune constante en dur ailleurs.
*Test* : un fichier de config invalide échoue explicitement, pas
silencieusement.

### Lot 2 — `citizen.py`
Entité `Citizen` (§2.2) avec `id`, `office`, `term_end_tick` (A3), et
population générée de façon déterministe à partir de `seed`.
*Test* : deux générations avec la même graine sont identiques champ à champ.

### Lot 3 — `parties.py` (A2)
Initialisation des N partis par k-means sur les positions citoyennes.
*Test* : nombre de partis conforme, plateformes distinctes, déterminisme.

### Lot 4 — `institutional_clock.py`
Calendrier : à partir d'un tick, dire quel scrutin a lieu (aucun,
présidentiel, législatif). Décalage paramétrable (§6).
*Test* : sur 120 ticks, exactement 8 présidentielles et 8 législatives, aux
ticks attendus ; changer l'offset décale bien le second calendrier.

### Lot 5 — `ballot_and_aggregation.py` (§3.2)
**Adaptateur, pas réimplémentation** : traduit l'état des citoyens en
bulletins, délègue le dépouillement à `engine/utils` existant, traduit le
résultat en sièges (`seat_allocation` de la config).
*Test* : parité avec le golden-fixture harness existant sur des cas connus.

### Lot 6 — `simple_rules.py` (A5)
Les décisions déterministes de la v0, isolées dans un module dédié —
c'est ce que `llm_behavior_engine.py` remplacera en v2, et qui restera le
**baseline de comparaison**. Vote par distance pondérée, candidature par
seuil d'ambition, coalition par plus proche voisin jusqu'à majorité.
*Test* : chaque règle testée isolément sur des cas construits à la main.

### Lot 7 — `journal.py` (§16.1-16.3)
Écriture append-only JSONL, jamais relue pendant le run, avec `event_id`
et ordre garanti (D8).
*Test* : un run interrompu brutalement laisse un journal lisible jusqu'au
dernier événement complet.

### Lot 8 — `run_polity_simulation.py`
Orchestration : boucle sur les ticks, appelle l'horloge, déclenche les
scrutins, journalise. Aucune logique métier propre — uniquement du
séquencement.
*Test d'intégration* : un run complet de 30 ans se termine sans erreur et
produit un journal non vide.

### Lot 9 — `metrics.py` (§10, sous-ensemble v0)
Uniquement les métriques calculables sans LLM ni légitimité : nombre
effectif de partis (Laakso-Taagepera), taux de cohabitation, durée de vie
des coalitions.
*Test* : Laakso-Taagepera vérifié à la main sur un cas connu (ex. 2 partis
à 50/50 ⇒ N = 2,0).

---

## 4. Test transverse — le plus important

**Test de reproductibilité de bout en bout** : deux runs complets avec la
même graine produisent des journaux **identiques octet pour octet**.

C'est le test qui protège toute la suite du projet (§4). S'il passe en v0
sur du code purement déterministe, il devient le garde-fou qui détectera
immédiatement toute fuite de non-déterminisme quand le LLM arrivera en v2.
À écrire dès le lot 8, pas après.

---

## 5. Définition de « v0 terminée »

- [ ] Les 8 bloquants v0 de l'audit sont tranchés et reflétés dans le plan
- [ ] Un run de 30 ans / 100 citoyens s'exécute de bout en bout
- [ ] Le test de reproductibilité passe (journaux identiques)
- [ ] Le calendrier produit le bon nombre de scrutins aux bons ticks
- [ ] `ballot_and_aggregation.py` est en parité avec le harness existant
- [ ] Les 3 métriques v0 sont calculées et exportées
- [ ] CI locale verte (Ruff, mypy strict, Bandit, Semgrep)
- [ ] `THEORY.md` / `traceability.md` mis à jour via `/sync-theory`

**Critère de passage à la v1** : pouvoir répondre à la question « sur ces
30 ans, combien de cohabitations, et combien de partis effectifs en fin de
période ? » — et que la réponse soit stable d'un run à l'autre à graine
constante.

---

## 6. Ce qu'il ne faut surtout PAS faire en v0

- Aucun appel LLM, même « juste pour tester » — le palier existe
  précisément pour isoler les bugs mécaniques.
- Aucune visualisation (§14) : le journal JSONL suffit à valider.
- Aucun paramètre de légitimité (§7) : `legitimacy.enabled: false`.
- Aucun événement exogène (§8).
- Pas d'optimisation de performance : 100 citoyens × 120 ticks est
  trivial, même en Python naïf. Vectoriser prématurément rendrait le
  débogage plus difficile.
