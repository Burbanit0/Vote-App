# vLLM 0.29.0 → 0.30.0 — bascule patch, document d'exécution

Comme `plan-vllm-switch-readiness.md` §v8 : ce document ne scope pas une
implémentation à écrire, il scope une **vérification** — dans quel ordre, avec
quels critères d'arrêt — avant de faire confiance au tag `v0.30.0` pour un run
réel ou coûteux. Contrairement à v8, il n'y a ici qu'un seul axe : le serveur
change, ni le modèle ni la quantification (`Qwen/Qwen3-8B-AWQ`, `awq_marlin`,
`--served-model-name qwen3:8b` inchangés) — donc pas de second facteur confondu
à isoler cette fois.

## 0. Ce qui est fait, ce qui ne l'est pas

**Fait, dans cette session (sandbox sans GPU, réseau restreint à
`registry-1.docker.io`/`hub.docker.com` — `huggingface.co` et `github.com` sont
bloqués par la politique réseau de cet environnement, confirmé via
`/__agentproxy/status` plutôt que supposé) :**
- `docker-compose.llm.yml` épinglé sur `vllm/vllm-openai:v0.30.0`, existence et
  date de push (2026-09-22, deux jours avant la version précédente du
  2026-09-09) confirmées **directement contre l'API du registre** (le même
  flux que `check_llm_stack_versions.py` et que `docker pull` lui-même), pas
  devinées ni copiées d'une page web.
- Les notes de version 0.30.0 upstream lues via recherche web (le dépôt GitHub
  lui-même étant inaccessible depuis ce sandbox) et croisées contre ce que ce
  projet utilise réellement — détail au §1.

**Pas fait, faute de GPU dans ce sandbox — donc pas fiable pour un run réel
tant que ce n'est pas fait sur une machine avec GPU :**
- Aucun démarrage réel du conteneur sur ce tag.
- Aucun des tests live (`test_polity_vllm_live.py`, 8 tests).
- Aucune relecture des logs de démarrage (budget KV cache réel, sélection de
  noyau, avertissement éventuel sur `--max-model-len`).
- Aucune régénération de `check_llm_stack_versions.py --discover` (bloqué par
  l'absence d'accès réseau à `huggingface.co` dans ce sandbox précis — voir §3
  pour la question modèle).

## 1. Ce qui change en amont, et ce qui touche ce stack

762 commits, 315 contributeurs (source : notes de version GitHub v0.30.0,
lues via recherche web, pas via une lecture directe de la page — à
recouper par quiconque a accès à `github.com` avant de trancher un point
ambigu ci-dessous).

**Changements cassants listés en amont, revus un par un contre ce que
`docker-compose.llm.yml` utilise réellement — aucun ne s'applique tel quel :**
- Endpoints scale-out désormais opt-in (`--enable-scale-out`) : ce stack ne
  les utilise pas.
- Suppression du group/dynamic activation ordering GPTQ (`g_idx`, noyaux
  Marlin/GPTQ/CPU/RDNA3 associés) : ce stack sert de l'AWQ (`awq_marlin`), pas
  du GPTQ — sans objet.
- Variables d'environnement dépréciées supprimées
  (`VLLM_PREFIX_CACHE_RETENTION_INTERVAL`, `VLLM_MM_HASHER_ALGORITHM`) :
  aucune des deux n'est définie dans ce dépôt (`grep -r` fait, aucun résultat)
  — sans objet.
- Mode de cache Mamba `all` déprécié : `Qwen/Qwen3-8B-AWQ` est un modèle dense,
  pas de couches Mamba — sans objet.
- `python -m vllm.entrypoints.grpc_server` déprécié au profit de
  `vllm serve --grpc` : ce stack n'utilise pas le serveur gRPC — sans objet.

**Deux points revus, jugés vraisemblablement sans impact mais PAS vérifiés en
direct — à confirmer au démarrage réel avant de faire confiance au tag :**
- **YaRN aligné sur Transformers** : « peut réduire `max_model_len` pour les
  modèles concernés ». `Qwen/Qwen3-8B-AWQ` n'active pas de `rope_scaling` YaRN
  par défaut (contexte natif 32768, largement au-dessus du `--max-model-len
  16384` déjà épinglé) — improbable que ça morde ici, mais ce n'est qu'un
  raisonnement à partir de la description de la release, pas une lecture du
  `config.json` réel du poids servi (HF inaccessible depuis ce sandbox). **À
  vérifier** : lire les logs de démarrage du conteneur pour tout avertissement
  touchant `max_model_len` avant de lancer quoi que ce soit d'autre (la règle
  maison de ce fichier lui-même : vLLM rapporte sa vraie capacité au
  démarrage, jamais un calcul a priori).
- **`--structured-outputs-config` / xgrammar** : la 0.30.0 ajoute du support
  (`patternProperties`, `propertyNames`, `unevaluatedProperties`) mais aucune
  suppression relevée pour `{"backend": "xgrammar", "disable_any_whitespace":
  true}` — le correctif qui a éliminé la boucle de génération d'espaces sans
  fin (2 des 9 types de décision touchés, `check_vllm_*_sort_keys_truncation_
  results.md`) devrait donc tenir. **À vérifier** : ce correctif était
  spécifique à une version de xgrammar à l'époque ; rejouer au moins le
  sous-ensemble de cas qui avait initialement trouvé le bug avant de faire
  confiance au tag pour `PressureDecision`/`CandidacyDecision`/
  `PartyNominationDecision`.

**Un point identifié comme le plus sensible pour ce projet précisément — pas
un changement générique, un changement au mécanisme même dont R1 dépend :**
- Le `--reasoning-parser qwen3` change de mécanisme : « full-history reasoning
  scans eliminated ; `is_reasoning_end` now derived from grammar » (au lieu
  d'un scan de l'historique complet). C'est exactement le mécanisme que
  `docker-compose.llm.yml` documente déjà comme *load-bearing, not cosmetic*
  (risque résiduel R1 : sans lui, `enable_thinking: true` peut devenir un
  no-op silencieux sous contrainte de grammaire — la même signature de bug
  qu'un collapse déjà mesuré une fois sur Ollama sous un autre nom). Un
  changement du mécanisme de détection de fin de raisonnement peut aussi
  changer la forme du champ de sortie que `test_think_true_actually_produces_
  reasoning` lit aujourd'hui (`message.get("reasoning")`, nommé ainsi après
  une vérification live à `v0.28.0` — pas garanti stable d'une version majeure
  de mécanisme à l'autre). **C'est le test n°1 à rejouer, pas un test parmi
  d'autres.**
- Les notes mentionnent aussi : « invalid structured-output requests no longer
  halt engines ». Amélioration de robustesse a priori, mais un comportement
  différent sur requête invalide reste un comportement différent — à noter si
  un test échoue différemment qu'avant sous ce tag.

**Sans objet pour ce stack, informatif seulement :**
- Décodage spéculatif (MTP/EAGLE3/DFlash sous pipeline parallelism, drafts
  DSpark) : `docker-compose.llm.yml` n'a **aucun** `--speculative-config`
  depuis le 2026-09-20 (`check_vllm_speculation_ab_results.md` — pas de
  bénéfice mesuré sur trafic réel) ; sans objet.
- Model Runner V2 (recouvrement dual-batch, GC gelé pendant la capture des
  CUDA graphs, 28,9s→8,2s sur H200) : gains de performance annoncés, pas de
  revendication de changement de numérique cette fois (contrairement à la
  spéculation n-gram, dont 13/174 réponses de banque gelée différaient déjà de
  0.28.0 à 0.29.0 pour des raisons de numérique V2, acceptées le 2026-09-20).
  Rejouer `check_vllm_batching_determinism.py` quand même, par principe maison
  — jamais un seul verdict « ça marche » sans la sonde de déterminism dédiée.
- Nouveaux modèles (DeepSeek-V4.1-Flash, GLM-5.3-Flash, K2-Horizon, Cohere
  Compass, Bailing V3 VL, Nanbeige4.2, backend CPU DeepSeek-V4) : aucun n'est
  dans la lignée Qwen3 que ce projet sert — voir §3 pour la question modèle
  séparément.

## 2. Checklist obligatoire avant de faire confiance à ce pin pour un run réel

Dans l'ordre, sur une machine avec GPU (la seule chose que ce sandbox ne peut
pas fournir) :

1. `python fast_api_voter/scripts/check_llm_stack_versions.py --strict` —
   confirmer que `v0.30.0` est toujours la dernière stable et que la révision
   HF de `Qwen/Qwen3-8B-AWQ` n'a pas bougé entre-temps (ce script a déjà
   attrapé une dérive silencieuse une fois, voir `EXP-016`).
2. `docker compose -f docker-compose.llm.yml up -d`, lire les logs de
   démarrage : budget KV cache réel (`num_gpu_blocks`), noyau de quantification
   sélectionné, tout avertissement touchant `max_model_len` (§1, le point
   YaRN) — avant de lancer quoi que ce soit d'autre.
3. **≥3 redémarrages propres consécutifs** (`docker compose ... restart`),
   règle maison acquise sur l'incident `--max-model-len 24576` (marchait au
   premier démarrage, OOM au second, même flag) — un seul démarrage réussi ne
   prouve rien ici.
4. `POLITY_VLLM_LIVE=1 POLITY_VLLM_URL=http://localhost:8000/v1 \
   python -m pytest api/tests/test_polity_vllm_live.py -o addopts="" -v` — les
   8 tests, **`test_think_true_actually_produces_reasoning` en premier
   regard** (§1) : si le nom du champ de sortie ou la présence de raisonnement
   a changé, corriger le test/le client avant de considérer quoi que ce soit
   d'autre comme fiable.
5. Rejouer le sous-ensemble de cas `PressureDecision`/`CandidacyDecision`/
   `PartyNominationDecision` qui avait trouvé la boucle d'espaces sans fin (§1)
   — au minimum les scripts `check_vllm_*_sort_keys_truncation.py` déjà dans
   `scripts/`, contre ce tag.
6. `check_vllm_batching_determinism.py` — le risque de divergence sous
   concurrence réelle spécifique à vLLM, distinct du non-déterminisme déjà
   mesuré sur Ollama.
7. Si un seul de ces points diverge du comportement `v0.29.0` documenté dans
   les résultats déjà commités (`vllm_switch_results.md`,
   `check_vllm_speculation_ab_results.md`, etc.), traiter ça comme une
   trouvaille propre et l'écrire dans un
   `scripts/check_vllm_030_upgrade_results.md`, même convention que chaque
   changement de stack précédent — jamais un verdict global « ça marche »/« ça
   ne marche pas » sans ce document.
8. Seulement après ça, le tag est fiable pour un run polity réel/coûteux.

## 3. La question « meilleurs modèles » — pas tranchée ici, et pourquoi

`check_llm_stack_versions.py --discover` est l'outil que ce projet s'est déjà
donné exactement pour cette question — il croise les nouveaux modèles
officiels des lignées déjà épinglées contre trois portes que ce projet exige
réellement (tient dans la carte, l'architecture est chargeable par le vLLM
épinglé, honore `enable_thinking` en bascule d'exécution). **Il n'a pas pu
tourner ici** : `--discover` a besoin de l'API Hugging Face
(`huggingface.co`), bloquée par la politique réseau de ce sandbox précis (pas
un choix, une contrainte d'environnement — confirmée par
`/__agentproxy/status`, pas supposée).

Deux contraintes déjà documentées dans le docstring même de ce script, à
garder en tête pour quiconque lance `--discover` sur une machine qui, elle, a
accès à `huggingface.co` :
- Les générations Qwen plus récentes (3.5, 3.6, 3.8) sont sorties
  exclusivement multimodales (`image-text-to-text`) — pas un problème en soi
  pour `--discover` (déjà géré), mais un signal que « plus récent » dans cette
  lignée ne veut plus dire « même forme d'entrée ».
- Le rafraîchissement Qwen3-4B « 2507 » (mesuré le 2026-09-13) a scindé le
  modèle en deux : un Instruct qui ne raisonne jamais, un Thinking qui
  raisonne toujours — ni l'un ni l'autre n'a la bascule `enable_thinking` en
  exécution dont `model_profiles.py`/`llm_behavior_engine` dépendent
  structurellement (chaque décision choisit `think=True/False` par type). Un
  modèle « meilleur » sur un classement public mais sans cette bascule n'est
  **pas** un candidat pour ce projet tel qu'il est architecturé aujourd'hui —
  ce n'est pas une question de qualité de réponse, c'est une incompatibilité
  structurelle avec la façon dont ce projet pilote le raisonnement décision
  par décision.

**Recommandation, pas une décision** : lancer
`python fast_api_voter/scripts/check_llm_stack_versions.py --discover
--vram-gib <taille réelle de la carte>` sur une machine avec accès réseau
complet et GPU, lire la liste de candidats qui en ressort (chacun déjà
qualifié « worth evaluating » ou non par les trois portes ci-dessus), puis —
seulement pour un candidat qui passe les trois portes — traiter tout
changement de poids comme la deuxième variable confondue que
`plan-vllm-switch-readiness.md` nomme déjà : mesurer qualité de décision et
débit sur les sondes propres à ce projet avant de rien basculer. Rien dans ce
document ne nomme un modèle précis à adopter : ce serait deviner un nom à
partir d'une recherche web générale, exactement ce que ce projet a choisi de
ne jamais faire pour cette question (`check_llm_stack_versions.py`'s own
docstring).
