# Backlog — alternatives déjà évaluées ou identifiées

**But de ce fichier** : garder une trace centralisée des pistes déjà
considérées pour ce projet — pour ne jamais redécouvrir une piste sans se
souvenir qu'elle a déjà été écartée, et pour quelle raison précise (manque
de preuve, coût non justifié, pas de rapport avec le problème en cours —
jamais "par oubli"). Aucune de ces pistes n'est active tant que sa
condition de réévaluation n'est pas atteinte.

**Contexte d'origine** : investigation du bug 4 (dégénérescence de
génération `finish_reason='length'` sur resoumission d'une requête
`think=True` proche d'une entrée déjà en cache — voir
`fast_api_voter/scripts/llm_batching_determinism_results_gpu.md` pour le
détail du problème et `ADR-001-serving-layer-ollama-vs-llama-server.md`
pour la décision d'architecture qui en a découlé jusqu'ici).

## Couche de serving (remplacer ou compléter Ollama)

| Piste | Statut | Condition de réévaluation |
|---|---|---|
| `llama-server` natif | Spike mené (16 min, 2026-08-19), inconclusif sur la preuve d'immunité au bug 4 — n'a jamais reproduit le bug testé, à charge légère (4 prompts) et lourde (10 prompts, générations substantielles) | Si le bug 4 s'avère non maîtrisable sur Ollama même avec une mitigation validée |
| vLLM | Déjà dans la roadmap (§15, critère de bascule v4+ — décisions récurrentes par tick), non testé contre le bug 4 spécifiquement ; `VllmJsonClient` n'a jamais tourné contre un serveur vivant | Prioritaire dès que le critère de bascule roadmap est atteint — indépendamment du bug 4 |
| LocalAI | Identifiée, jamais testée — hub d'orchestration multi-backend, ajoute une couche d'abstraction supplémentaire par rapport à un accès direct à llama.cpp/vLLM | Seulement si un besoin multi-modal (image/audio) apparaît un jour ; pas de raison de la tester pour ce problème précis |

## Modèle (remplacer `qwen3:8b`)

| Piste | Statut | Condition de réévaluation |
|---|---|---|
| `qwen3:14b` | Identifiée comme candidat naturel (même famille, meilleure capacité) | Seulement une fois le pipeline stabilisé — recalibrerait tous les budgets de tokens existants (`compute_max_tokens`, `_POSITIONING_THINK_TOKEN_ALLOWANCE`, `_VOTE_THINK_TOKEN_ALLOWANCE`, etc.) |
| `gpt-oss:20b` (MoE) | Identifiée, citée comme référence 16 Go de l'été 2026 | Idem — pas de raison de tester avant stabilisation |
| DeepSeek-R1 (distillations 8B/14B) | Identifiée, raisonnement en chaîne de pensée explicite nativement | Idem, intéressant si le besoin de débogage du raisonnement devient prioritaire |

## Mécanismes internes à llama.cpp (pas un changement de couche)

| Piste | Statut | Condition de réévaluation |
|---|---|---|
| `--deterministic` / `GGML_DETERMINISTIC=1` (llama.cpp) | Recherché (2026-08-19) : PR [ggml-org/llama.cpp#16016](https://github.com/ggml-org/llama.cpp/pull/16016), **non mergée** (draft). Cible CUDA (BF16/FP16) uniquement, nécessite une reconstruction (`-DGGML_DETERMINISTIC=ON`), coût de débit reconnu par les auteurs. Aucune mention d'applicabilité à `llama-server` spécifiquement. Un mainteneur (Johannes Gaessler) s'oppose à l'approche et renvoie vers la gestion du cache de prompts comme alternative déjà existante — exactement le levier testé par le spike `llama-server`, de façon inconclusive. **Non exposé par Ollama** (absent de `envconfig/config.go`, cohérent avec le fait que la PR amont n'est pas mergée) | Si la PR est mergée en amont ET si `llama-server`/Ollama l'exposent un jour ; ou si le bug 4 devient assez coûteux pour justifier de builder llama.cpp soi-même en attendant |

## Précisions explicites

- **Aucune des pistes "Modèle" ne concerne le bug 4** — c'est un problème
  d'orchestration côté Ollama (gestion du cache de prompts, réutilisation
  cross-requête), pas une limite du modèle `qwen3:8b` lui-même. Les traiter
  maintenant ajouterait une variable non caractérisée en pleine
  investigation, exactement le risque que ce backlog existe pour éviter.
- **Seule la ligne `llama-server`/vLLM de la section "serving"** touche
  directement au bug 4 — et toutes deux restent en attente d'une condition
  de réévaluation précise, pas d'un abandon silencieux.
- Ce fichier est un backlog, pas un plan — aucune de ces pistes ne démarre
  tant que sa condition de réévaluation n'est pas explicitement atteinte et
  confirmée par la personne qui pilote ce projet.
