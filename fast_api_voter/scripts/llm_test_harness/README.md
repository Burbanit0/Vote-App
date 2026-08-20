# llm_test_harness

Système réutilisable pour les expériences GPU/LLM de ce projet — pré-enregistrement,
capture automatique de l'état d'environnement, stockage SQLite interrogeable, rapports
générés (jamais écrits à la main). Construit après l'investigation du bug 4
(2026-08-17/19), dont le principal facteur de bruit (un scan Windows Defender,
coïncidant avec un des trois échecs observés) n'a été découvert qu'après coup en
fouillant les journaux système Windows — exactement le genre de chose que
`environment.py` capture désormais en direct, pas reconstitué.

## Workflow

### 1. `register` (CLI) — avant tout run

Écris l'hypothèse et le critère de décision **avant** de lancer quoi que ce soit.
Immuable une fois enregistré : aucune fonction de mise à jour n'existe, nulle part
dans ce package.

```bash
python fast_api_voter/scripts/llm_harness.py register \
    --hypothesis "le nonce par tentative élimine la dégénérescence sur resoumission" \
    --decision-criterion "failure_rate > 0.1 = rejeter le nonce comme mitigation fiable" \
    --planned-n 20 --budget "1h GPU max" \
    --expected-effect-rate 0.19 --decision-threshold-for-sizing 0.1 \
    --threshold 0.1 --comparison gt --metric failure_rate
```

Si `--planned-n` est manifestement insuffisant pour le critère déclaré (calculé via
`sample_size.required_sample_size`), un **avertissement** s'affiche — jamais un blocage.

### 2. `run` — pas une commande CLI

Chaque protocole d'appel LLM est différent (chunking, schéma, endpoint natif ou
OpenAI-compat) — le harnais ne sait pas appeler un LLM lui-même, et ce n'est pas son
rôle. Écris un script Python (voir `example_experiment.py`) qui boucle sur :

```python
from llm_test_harness import trial

for i in range(1, planned_n + 1):
    trial.record_trial(
        experiment_id, i,
        container_name="ollama-polity",
        run_call=lambda: mon_appel_llm_reel(),  # retourne un trial.TrialResult
    )
```

`run_call` est TON appel réel — le harnais s'occupe de la capture d'environnement
avant/après et du stockage ; il ignore tout le reste.

### 3. `report` (CLI) — génère le markdown depuis la base

```bash
python fast_api_voter/scripts/llm_harness.py report <experiment_id> --out resultat.md
```

## Migrer un test ad hoc existant

1. Remplace ta boucle `for i in range(N): appel_llm()` par une boucle appelant
   `trial.record_trial(...)`, avec `run_call=lambda: trial.TrialResult(ok=..., ...)`
   construit à partir du résultat réel de ton appel.
2. Enregistre l'expérience **avant** de lancer, avec un vrai critère de décision —
   pas un jugement a posteriori sur les résultats.
3. Laisse `report` générer le markdown plutôt que d'en écrire un à la main.

Les rapports déjà écrits à la main (`llm_batching_determinism_results*.md`,
`ollama_context_window_results.md`, etc.) restent tels quels — seuls les **futurs**
essais passent par ce système. `check_llm_batching_determinism.py` lui-même n'est pas
migré : ses résultats historiques lui sont attribués tel qu'il est écrit aujourd'hui,
et même un wrapper léger changerait sa séquence d'exécution exacte — le genre de
perturbation que cette investigation a montré significative.

## Base de données

Un seul fichier SQLite par projet : `fast_api_voter/scripts/llm_test_harness/data/harness.db`
(gitignoré — état d'exécution local, pas du code source). Ce qui se committe, c'est le
markdown généré par `report`, pas la base elle-même — même registre que les répertoires
`acceptance_*_runs/` déjà non commités dans ce projet.

## Tests

```bash
pytest fast_api_voter/scripts/llm_test_harness/tests/ -o addopts=""
```

Le `-o addopts=""` est nécessaire : `pyproject.toml` fixe `testpaths = ["api/tests"]`
et des options de couverture spécifiques à `api/` qui ne s'appliquent pas ici — même
override que celui déjà utilisé partout dans ce projet pour lancer `api/tests` isolément.

## Ce que ce harnais ne fait PAS

- Il n'appelle jamais un LLM lui-même (voir §2 ci-dessus).
- Il ne bloque jamais un enregistrement à cause d'un `n` prévu insuffisant — seulement
  un avertissement (`register(..., warn=True)`, le défaut).
- Il n'évalue mécaniquement le critère de décision que si `threshold`/`comparison`/
  `metric` structurés sont fournis à `register` — sinon le critère reste du texte
  affiché à côté des chiffres bruts, à évaluer humainement.
- Le calcul de taille d'échantillon (`sample_size.py`) utilise l'approximation
  normale standard (Wald), pas un intervalle de Wilson — imprécis pour des taux
  proches de 0/1 ou un petit `n`. Documenté comme limite connue, pas corrigé.
- Il n'enregistre l'affiliation d'un essai à une expérience que via `experiment_id` —
  aucune contrainte n'empêche de réutiliser un `container_name` entre deux
  expériences différentes ; c'est délibéré (le même conteneur Ollama sert
  naturellement plusieurs investigations dans le temps), mais ça veut dire qu'une
  requête croisée doit toujours filtrer par `experiment_id`, jamais par
  `container_name` seul, pour rester correcte.
