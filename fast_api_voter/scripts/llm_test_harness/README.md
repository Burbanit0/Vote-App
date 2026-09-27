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

## Piège d'outillage : le raisonnement n'est PAS dans `message.content`

**À lire avant d'écrire tout `run_call` qui investigue une troncature.** Lacune
d'outillage découverte le 2026-08-28, qui concerne toute investigation future, pas
seulement celle qui l'a révélée.

L'endpoint OpenAI-compat d'Ollama (`/v1/chat/completions`, `think=True`) renvoie le
contenu `<think>` dans un champ **`message.reasoning` distinct de `message.content`**.
Or les deux extracteurs de production (`llm_client._extract_content` et
`_extract_native_content`) ne lisent que `message.content` — et, pire pour le
diagnostic, ils lèvent sur `finish_reason`/`done_reason` **avant même** de regarder le
message. Conséquence : sur une troncature, `LlmResponseError` ne porte aucun
raisonnement, et un script qui se contente de capturer `message.content` enregistre
une chaîne **vide** en face d'un `completion_tokens` de plusieurs milliers.

Ce n'est pas une négligence du code de production : `decode_*` supprime les balises
`<think>` inline via `_THINK_TAG_RE`, donc le codebase est bien préparé à la forme
« raisonnement inline dans `content` ». La forme observée ici est l'autre, et aucun
extracteur ne la lit. (Non vérifié à ce jour : si l'endpoint natif `/api/chat` expose
un champ analogue. Ne pas le supposer — le mesurer.)

**Ce que ça implique pour un `run_call` :**

- Ne jamais dériver un diagnostic de `message.content` seul. Sur troncature, **dumper
  le corps JSON entier** (`response.json()`), pas les champs qu'on croit connaître.
- Capturer explicitement `msg.get("reasoning")` à côté de `msg.get("content")`, et
  logger la **longueur des deux**. Un `content_chars=0` avec
  `completion_tokens=13596` est le symptôme exact de ce piège.
- Le compte de tokens ne distingue pas les modes d'échec : sur troncature il vaut
  toujours le budget, par définition. Séparer **Mode A** (rumination non convergente —
  élargir le budget ne résout rien) de **Mode B** (raisonnement coupé alors qu'il
  approchait d'une conclusion — le budget est en cause) exige de lire le **contenu**
  du raisonnement, jamais son volume.

Cas fondateur : deux runs d'acceptance v6b avortés sous
`citizens.position_dist: factor_structure`, dont les logs de production étaient vides.
La première capture scriptée reproduisait la même erreur (`content` à 0 caractère pour
13 596 tokens) ; seul le re-dump du corps complet a révélé
`message.keys() == ['role', 'content', 'reasoning']` et 64 101 caractères de
raisonnement — de quoi caractériser un Mode A et remonter à la cause racine (une
ambiguïté du prompt système, pas un manque de budget). Voir le docstring de
`build_system_prompt` (`llm_behavior_engine.py`) et le §2.2 de
`plan-distribution-positions-seeds.md`.

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
