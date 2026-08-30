# v8 — bascule vLLM : document d'exécution (pas de nouveau code)

Contrairement à `plan-rupture-candidacy-threshold.md`/`plan-llm-decision-
audit-sampling.md`, ce document ne scope pas une implémentation à écrire :
`VllmJsonClient`, `test_polity_vllm_live.py` (8 tests), et
`check_vllm_batching_determinism.py` existent déjà, complets, jamais
exécutés faute de serveur vLLM réel. Ce document scope l'**exécution** —
dans quel ordre, avec quels critères d'arrêt, avec quelle valeur de
modèle — pas le code.

## 0. BLOQUÉ 2026-08-30 — avant même l'axe (a)

**Le conteneur ne démarre pas du tout, sur cette plateforme, indépendamment
de toute question de modèle/quantification.** `vllm/vllm-openai:v0.28.0`
échoue à l'initialisation avec `RuntimeError: UVA is not available`
(`vllm/v1/worker/gpu/buffer_utils.py`, `UvaBuffer.__init__`) — le moteur
`GPUModelRunnerV2` de vLLM tente d'allouer un buffer UVA (Unified Virtual
Addressing) que WSL2/Docker Desktop n'expose pas dans cette configuration.

Confirmé comme bug connu, pas spécifique à ce projet : deux issues GitHub
upstream (vllm-project/vllm#43381, #47387) documentent exactement la même
erreur sous WSL2, sur d'autres GPU (RTX 4060, RTX 4050) et d'autres
versions vLLM. Le correctif (PR vllm-project/vllm#47579, qui ajoute un
repli automatique vers le moteur V0 quand UVA est indisponible) est
**toujours non mergé** (ouvert 2026-07-03, conflit de rebase constaté
2026-08-08) — aucune version vLLM publiée ne le contient à ce jour.

**Contournement testé et écarté** : `VLLM_USE_V1=0` (variable documentée
pour forcer l'ancien moteur V0) n'a aucun effet sur `v0.28.0` — la trace
d'erreur continue de passer par `vllm.v1.engine.*` malgré la variable,
ce qui indique que le moteur V0 a probablement déjà été retiré de cette
version, pas seulement rendu non prioritaire.

**Ce que ça change** : ce n'est PAS une question de calibration
(l'AWQ/confond du §2 reste valide et à traiter le jour où le backend
démarre), c'est un **blocage de plateforme** — cette version de vLLM ne
tourne pas du tout sous Docker Desktop/WSL2 sur ce poste, quel que soit
le modèle choisi. Deux tentatives distinctes (défaut, puis le seul
contournement documenté existant), toutes deux avec une cause racine
claire et sourcée — pas une exploration exhaustive de toutes les
versions vLLM possibles, qui serait une recherche non bornée sans signal
clair de quelle version cibler.

**Décision : ne pas continuer à deviner d'autres versions sans repère.**
Voies possibles, non tranchées ici :
1. Chercher une version vLLM antérieure au passage à `GPUModelRunnerV2`
   comme moteur par défaut (recherche non faite — demande de savoir
   quand ce changement a eu lieu, pas garanti d'exister en version
   encore maintenue/publiée avec le reste de la stack requise ici).
2. Attendre que #47579 (ou un correctif équivalent) soit mergé et publié.
3. Tester en dehors de Docker Desktop/WSL2 (Linux natif) si un tel hôte
   devient disponible — hors de ce qui est accessible aujourd'hui.
4. Revenir sur la décision de bascule vLLM elle-même pour l'instant,
   cohérent avec le traitement déjà donné au point ouvert #20 (le
   provider reste `ollama`, la limite déjà mesurée et acceptée).

Le reste de ce document (§1-6) reste la référence pour LE JOUR où un
backend vLLM démarre réellement — rien de son raisonnement n'est invalidé
par ce blocage, qui est en amont de tout ce qu'il couvre.

## 1. État confirmé aujourd'hui

- GPU/Docker : `nvidia` runtime présent, RTX 5070 Ti, 14,6 Go libres sur
  16,3 Go — passthrough fonctionnel, vérifié directement (`nvidia-smi`,
  `docker info`), pas supposé.
- `docker-compose.llm.yml` cible `Qwen/Qwen3-8B` en bf16 — 8B × 2 octets =
  16 Go rien que pour les poids, sur une carte à 16,3 Go. Lancerait
  presque certainement un OOM au démarrage, jamais nommé explicitement
  dans le fichier existant.
- Fix identifié : `Qwen/Qwen3-8B-AWQ` (4 bits, `--quantization awq`, noyau
  `awq_marlin`, compatible Blackwell) — environ 4-5 Go de poids, laisse de
  la marge pour le KV cache. Existence et compatibilité vLLM confirmées
  par recherche web (pas dans ce dépôt), pas encore testées en direct.

## 2. Le vrai confond à nommer — deux variables, pas une

Passer à Qwen3-8B-AWQ sur vLLM change **deux choses en même temps**, pas
une seule :
1. Le **serveur d'inférence** (llama.cpp/Ollama → vLLM) — ce que ce
   chantier visait à l'origine.
2. Les **poids du modèle eux-mêmes** (qwen3:8b GGUF non quantifié →
   Qwen3-8B-AWQ, quantification 4 bits) — un second facteur, confondu
   avec le premier si on ne le nomme pas.

Tout ce qui a été calibré cette semaine — `_POSITIONING_THINK_TOKEN_
ALLOWANCE=8000`, `_VOTE_CAST_MAX_CHUNK_SIZE=1`, le fix de prompt sur
l'ambiguïté de ranking, `_CHAMBER_MAX_CHUNK_SIZE=1` — a été mesuré contre
qwen3:8b **non quantifié** sur Ollama. Une quantification différente peut
changer la longueur de raisonnement, la propension à converger, ou
réintroduire un comportement Mode A sous une forme différente. Ces deux
axes doivent être testés et rapportés **séparément** — jamais un verdict
unique « vLLM marche »/« vLLM ne marche pas ».

### Les cas difficiles déjà caractérisés, à rejouer contre AWQ

Correction d'une hypothèse initiale : le point de départ nommait
« chamber_deliberation chunk=5 » — c'est faux, `_CHAMBER_MAX_CHUNK_SIZE`
est livré à **1**, pas 5 (5 a été essayé le 2026-08-22 et a re-échoué
avec la même signature ; voir `llm_behavior_engine.py` lignes 211-266
pour l'historique complet 10→5→1).

1. **`campaign_positioning`, prompt à 3989 tokens** —
   `llm_batching_determinism_results_gpu.md`, section « cross-request
   prompt-cache reuse » : `decide_campaign_positioning` a produit
   `finish_reason='length'` 3/3 sur ce prompt exact, `n_decoded` atterrissant
   pile sur `compute_max_tokens(5) + _POSITIONING_THINK_TOKEN_ALLOWANCE`.
   Le mécanisme identifié (cache de prompt llama.cpp de mauvaise qualité)
   est **spécifique à Ollama/llama.cpp** — vLLM utilise PagedAttention, pas
   le pool de cache de llama.cpp, donc ce mécanisme précis ne peut pas se
   reproduire tel quel. Ce qui reste à vérifier : le budget de raisonnement
   (8000 tokens) suffit-il encore pour ce même prompt sous AWQ ? C'est une
   question de comportement du modèle quantifié, indépendante du mécanisme
   de cache.
2. **`chamber_deliberation`, cas `chamber_position == sincere_position`** —
   `lot3_chamber_reliability_results.md` : boucle Mode A trouvée sur un
   sweep live de 270 appels (7/270, toujours cet état exact — l'état normal
   de tout membre fraîchement tiré au sort ou n'ayant jamais dévié, pas un
   cas rare). Corrigé le 2026-08-29 par une phrase de désambiguïsation
   ajoutée à `build_chamber_system_prompt`, vérifié 0/7 en direct sur
   Ollama. Une boucle Mode A dépend de la façon dont CE modèle précis
   résout une ambiguïté de prompt — un modèle quantifié différemment peut
   réagir différemment à la même phrase de désambiguïsation, dans un sens
   ou dans l'autre.

## 3. Critères go/no-go séparés

**Axe (a) — le backend vLLM lui-même** :
- Les 8 tests de `test_polity_vllm_live.py` passent tous.
- `check_vllm_batching_determinism.py` ne montre pas de divergence sous
  concurrence réelle (le risque spécifique à vLLM, §15bis.4c — distinct de
  la non-déterminisme déjà mesurée sur Ollama).
- **Absent des 8 tests existants, à ajouter avant de conclure sur l'axe
  (a)** : aucun ne reproduit directement le protocole qui a trouvé le bug
  de cache Ollama (amorcer avec un prompt dissemblable, puis mesurer si
  l'appel suivant échoue). Par construction (PagedAttention ≠ pool de
  cache de llama.cpp), ce mécanisme précis ne peut pas se reproduire à
  l'identique — mais l'absence de CE bug précis ne garantit pas l'absence
  de tout mécanisme de troncature propre à vLLM. Faire tourner un
  mini-harnais du même type (quelques dizaines d'appels avec des prompts
  de forme variable en amorce) avant de déclarer l'axe (a) validé.

**Axe (b) — le modèle quantifié AWQ produit-il un raisonnement comparable
au modèle non quantifié sur les cas déjà difficiles** :
- Rejouer le prompt `campaign_positioning` à 3989 tokens (reconstruit à
  partir des mêmes citoyens/candidats si possible, sinon un prompt de
  taille et de forme équivalente) sous `_POSITIONING_THINK_TOKEN_
  ALLOWANCE=8000` — converge-t-il dans ce budget ?
- Rejouer un batch `chamber_deliberation` avec `chamber_position ==
  sincere_position` (état de seating normal, trivial à reconstruire) —
  la phrase de désambiguïsation ajoutée le 2026-08-29 suffit-elle encore
  à empêcher la boucle Mode A sous AWQ ?
- **Si (b) échoue** : il faudra recalibrer les budgets/chunk sizes
  indépendamment de la question vLLM vs Ollama. Coût à chiffrer à ce
  moment-là (au minimum : refaire tourner l'équivalent de
  `lot3_chamber_reliability_results.md`/le sweep 270 appels pour ce
  modèle précis) — pas estimé ici, puisqu'il ne s'engage que si (b)
  échoue réellement.

## 4. Budget VRAM et KV cache

AWQ (~4-5 Go de poids) laisse ~9,6-10,6 Go sur les 14,6 Go actuellement
libres. **Le chiffre exact de KV cache par token n'est pas calculé ici à
partir de la mémoire de l'architecture Qwen3 — ce serait deviner un
nombre dans un document qui sert à prendre une décision.** vLLM rapporte
lui-même sa capacité réelle de KV cache et sa concurrence maximale dans
ses logs de démarrage (`num_gpu_blocks`, etc.) — c'est la première chose
à lire une fois le conteneur lancé, avant tout test.

Ce qui borne réellement le besoin ici : `llm_client.py`'s own module
docstring — ce projet n'émet jamais qu'**une requête à la fois** en usage
production (`check_vllm_batching_determinism.py`'s own concurrency est un
harnais de test explicitement mis en quarantaine, jamais du trafic de
production). La séquence la plus longue mesurée reste `campaign_
positioning`'s 3989 tokens de prompt + jusqu'à 9836 tokens de génération
dans le pire cas déjà vu sur Ollama — grand comparé à `chamber_
deliberation`/`vote_cast` (chunk=1 partout, prompts nettement plus
courts). Un seul contexte de cette taille à la fois tient largement dans
9,6-10,6 Go, mais le nombre EXACT de séquences concurrentes que le
serveur peut réellement soutenir doit venir du propre rapport de vLLM au
démarrage, pas d'un calcul a priori dans ce document.

## 5. Ordre d'exécution — isole les deux variables

1. **D'abord, l'axe (a) seul** : lancer `docker-compose.llm.yml` (image
   taguée, `Qwen/Qwen3-8B-AWQ` avec `--revision` épinglé, `--quantization
   awq`), faire tourner les 8 tests de `test_polity_vllm_live.py` +
   `check_vllm_batching_determinism.py` + le mini-harnais de cache
   dissemblable (§3). Lire les logs de démarrage pour le budget KV cache
   réel avant de lancer quoi que ce soit d'autre. Un seul verdict à ce
   stade : le backend fonctionne-t-il, indépendamment du modèle.
2. **Séparément ensuite, l'axe (b)** : rejouer les deux cas difficiles
   (§2) contre le MÊME serveur AWQ déjà validé à l'étape 1. Verdict
   distinct : le modèle quantifié raisonne-t-il de façon comparable.
3. Rapporter les deux verdicts séparément dans un
   `scripts/vllm_switch_results.md` (comme `check_vllm_batching_
   determinism.py`'s own docstring l'exige déjà) — jamais un seul
   « vLLM marche »/« vLLM ne marche pas ».

## 6. Valeurs encore à épingler avant de lancer

- Tag d'image `vllm/vllm-openai` — jamais `latest`, une version pinnée
  réelle à choisir.
- `--revision` (SHA de commit HF) pour `Qwen/Qwen3-8B-AWQ` — épingler les
  poids, pas juste le nom du repo (même règle que `llm.model` dans
  `config.py`).
- `--served-model-name` : rester `qwen3:8b` (déjà dans le fichier) pour
  que `llm.model`, et chaque octet de prompt/journal en aval, restent
  identiques entre providers — même si le nom ne correspond plus
  littéralement au repo HF servi (AWQ, pas le repo de base). Documenter
  cet écart nom/repo explicitement dans le compose file au moment de
  l'épingler, pour qu'un futur lecteur ne le lise pas comme une erreur.
