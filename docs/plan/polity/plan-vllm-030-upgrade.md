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

## 4. Candidats identifiés par recherche web (2026-09-24) — classement indicatif, pas `--discover`

Demande explicite : investiguer sans rien exécuter. Ce qui suit vient de
`WebSearch`/`WebFetch` (aucun accès direct à `huggingface.co`/`github.com`
depuis ce sandbox, seul `registry-1.docker.io` l'est) — **un substitut
dégradé à `--discover`, pas un remplacement**. Rien ici n'a été vérifié
contre l'API HF elle-même (pas de SHA de révision, pas de lecture directe de
`config.json`), donc aucun de ces points ne remplace l'étape 1 du §3. Classé
selon la forme réelle de ce projet (bascule `enable_thinking` par type de
décision, carte à 16,3 Go, tient à un seul flux, calibration Qwen3 déjà
investie), pas selon un classement de benchmark public.

**Budget de référence** (méthode de `check_llm_stack_versions.py`) : 16,3 Go ×
0,80 (`--gpu-memory-utilization`) ≈ 13,0 Go pour poids + KV cache d'une
séquence à 16384 tokens + 1,5 Go de marge. Le pin actuel (`Qwen3-8B-AWQ`, ~4-5
Go de poids) n'utilise qu'une fraction de ce budget.

### Rang 1 — `Qwen/Qwen3.5-9B` (quantification officielle FP8, PAS l'AWQ communautaire)

Alibaba, février 2026, Apache 2.0, même mécanisme de bascule que le pin actuel
(`chat_template_kwargs.enable_thinking` — zéro changement dans
`ThinkingControl`/`model_profiles.py`). C'est la génération Qwen encore
dense/petite/ouverte la plus récente : 3.6/3.7/3.8 ferment la porte (§ci-
dessous). C'est le candidat le plus « à jour dans la lignée déjà investie »,
mais avec un vrai coût d'ingénierie, pas un simple bump de tag :
- **Architecture différente, pas un GQA dense classique** : `Qwen3.5-9B`
  utilise une attention hybride Gated DeltaNet / Gated Attention
  (8×(3×DeltaNet→FFN→1×Attention→FFN), source : recherche web, pas confirmé
  sur le `config.json` réel). Le commentaire même de `_kv_cache_gib` dans
  `check_llm_stack_versions.py` documente déjà ce problème pour cette
  génération (« Qwen3.5/3.6 run linear attention on 24 of 32 layers... counting
  every layer overestimated their KV by 4x ») — donc l'outillage de ce projet
  sait déjà gérer ce cas, mais ça reste un changement d'architecture, pas
  seulement de poids. Vérifier `arch_supported` (`--discover`, ou directement
  `docker run ... ModelRegistry.get_supported_archs()`) avant tout le reste.
- **Pas d'AWQ officiel Qwen** trouvé pour cette taille — seulement des requants
  communautaires (`QuantTrio/Qwen3.5-9B-AWQ`, `cyankiwi/Qwen3.5-9B-AWQ-*`),
  exactement le type de second facteur confondu que ce projet a déjà refusé
  une fois (`cortecs/Qwen3-8B-NVFP4A16` rejeté pour cette même raison). Les
  formats officiels Qwen pour cette génération sont FP8 et GPTQ-INT4.
- **GPTQ-INT4 porte un risque neuf, introduit par CE bump précis** : les notes
  de version 0.30.0 suppriment le support de l'activation ordering GPTQ
  (`g_idx` ignoré, noyaux Marlin/GPTQ/CPU/RDNA3 associés retirés, §1). Un
  checkpoint GPTQ-INT4 qui dépend de `desc_act`/`g_idx` pourrait donc être
  cassé sur ce tag précis — à vérifier avant d'y toucher, pas supposé. **FP8
  officiel est le chemin de quantification le plus sûr** pour ce candidat sur
  `v0.30.0`, et une carte Blackwell (RTX 5070 Ti) a un support FP8 natif
  solide.
- Un bug réel AWQ+bascule-thinking a été trouvé et corrigé sur `Qwen3.5-122B-
  A10B` (fuite de `<think>` en mode non-thinking, `</think>` jamais émis en
  mode thinking — `vllm-project/llm-compressor#2680`, ouvert et fermé le
  2026-05-01 avec un correctif). Le rapport lui-même note que les variantes
  plus petites (`Qwen3-4B`, `Qwen3-30B`) ne reproduisaient pas le problème —
  mais ce n'est pas une garantie pour `Qwen3.5-9B` spécifiquement, c'est un
  signal que cette classe de bug existe dans cette lignée et doit être testée
  en direct (exactement `test_think_true_actually_produces_reasoning`, §2
  point 4), pas supposée absente.
- Changement de poids ET d'architecture = recalibration complète (chunk
  sizes, budgets de pensée, la phrase de désambiguïsation `chamber_position ==
  sincere_position`) — rien de mesuré aujourd'hui ne transfère.

### Rang 2 — `Qwen/Qwen3-8B-AWQ` (statu quo, pin actuel)

Pas plus « à jour », mais c'est la seule option sans coût de bascule : AWQ
officiel, transformeur dense classique (calcul KV simple, déjà chargé par
vLLM), et surtout **aucune version plus récente n'existe à cette taille dans
Qwen3 lui-même** — le rafraîchissement « 2507 » (Instruct/Thinking séparés,
qui aurait de toute façon cassé la bascule `enable_thinking`) n'a touché que
4B/30B-A3B/235B-A22B, jamais le 8B. Rester ici n'est pas « prendre du retard »
au sens strict : il n'y a rien de plus récent à l'intérieur de cette lignée
précise à adopter. Classé après le rang 1 uniquement parce que la demande
explicite est de rester aussi à jour que possible, et que 3.5 existe.

### Rang 3 — `ibm-granite/granite-4.2-8b`

Autre éditeur, Apache 2.0, sorti le 2026-08-25 — plus récent que la 3.5 de
février. Transformeur dense classique (GQA + RoPE) : Granite 4.2 **abandonne**
l'architecture hybride Mamba-2 de Granite 4.0/4.1 (confirmé par recherche
web), donc risque d'architecture plus bas que le candidat Qwen3.5 ci-dessus.
Même mécanisme de bascule (`chat_template_kwargs.enable_thinking`) — mais
nécessite son propre reasoning-parser (`granite_thinking_parser` /
équivalent `--reasoning-parser granite` côté vLLM) dont la présence dans
`v0.30.0` n'est pas vérifiée ici. Contexte natif 128K (contre 32K pour Qwen3-
8B) : la marge sur `--max-model-len 16384` est encore plus confortable, et le
point YaRN du §1 devient sans objet. Quantifications officielles IBM : FP8,
MXFP4, NVFP4 — pas d'AWQ officiel non plus, mais FP8/NVFP4 natifs sur
Blackwell sont un chemin légitime, pas un pis-aller.
**Le vrai coût** : changement total de famille = zéro calibration existante
réutilisable (chunk sizes, budgets de pensée, la phrase de désambiguïsation
Qwen3-spécifique) — recalibration aussi coûteuse qu'un nouveau projet
`model_profiles.py`, pas un bump. Classé après le rang 1 parce que ce coût est
strictement plus grand que celui d'un changement de poids à l'intérieur de la
même lignée, malgré une architecture plus simple et une quantification
officiellement plus proche de cette carte.

### Rang 4 — `openai/gpt-oss-20b` — à surveiller, pas recommandé maintenant

Apache 2.0, MoE. Intéressant structurellement : son contrôle
`reasoning_effort` correspond exactement au mode que `ThinkingControl` de ce
projet anticipe déjà (`field="reasoning_effort"`, pour « les modèles dont les
niveaux d'effort n'ont pas de vrai *off* ») — mais c'est justement le
problème : `reasoning_effort` n'a que low/medium/high, jamais de coupure nette
équivalente à `enable_thinking: False`, ce qui ne couvre pas les types de
décision de ce moteur qui ont besoin d'un dialogue rapide sans raisonnement du
tout. Et à l'échelle mémoire : les poids natifs MXFP4 seuls pèsent déjà ~16 Go
— pratiquement toute la carte avant même le cache KV et la marge, hors budget
du calcul ci-dessus (~13 Go). Écarté pour l'instant, pas définitivement — à
revisiter seulement si une variante officielle nettement plus compressée
apparaît.

### Mistral — investigué sur demande, écarté pour la même raison structurelle que DeepSeek-R1/Qwen-Thinking-2507

Aucune taille de la gamme Mistral actuelle ne passe la porte structurelle de
ce moteur (une bascule `enable_thinking` en exécution, un seul checkpoint) à
une taille qui tient sur cette carte :

- **`mistralai/Ministral-3-8B-{Instruct,Reasoning}-2512`** : bonne taille
  (8,4B LM), Apache 2.0, contexte 256K, FP8 officiel — mais Mistral livre
  Instruct et Reasoning comme **deux checkpoints séparés**, pas une bascule
  d'exécution sur un seul modèle (même défaut structurel que les variantes
  Qwen `*-Instruct-2507`/`*-Thinking-2507` déjà écartées, §ci-dessous) :
  couvrir les deux modes de ce moteur voudrait dire faire tourner deux
  serveurs, ou recharger le modèle par type de décision — incompatible avec
  le fonctionnement à un seul serveur vLLM de ce projet. Porte en plus un
  encodeur vision de 0,4B par défaut (multimodal), un axe jamais exercé en
  texte seul ici (même réserve que pour les générations Qwen 3.5+).
- **`mistralai/Magistral-Small-2506`/`-2509`** (24B) : modèle « reasoning »
  mais **toujours en train de raisonner** — pas de champ documenté
  équivalent à `enable_thinking: False`, le comportement se pilote par
  prompt/formatage plutôt que par une bascule propre. Ajoute une friction
  documentée spécifique à vLLM : « Magistral does not use special tokens to
  start thinking, which creates challenges with reasoning parsers in vLLM »
  — plus fragile que le tagging `<think>` propre de Qwen3 sur lequel
  `--reasoning-parser qwen3` et l'outillage de ce projet s'appuient déjà.
  Et côté mémoire : le checkpoint FP8 officiel pèse ~24 Go à lui seul, plus
  que la carte entière ; même un AWQ communautaire (aucun officiel trouvé)
  laisserait ~12 Go de poids seuls, une marge quasi nulle pour le cache KV
  et la surcharge sur un budget total de ~13 Go — même famille de problème
  que les 27B Qwen3.6/3.8 déjà écartés plus bas.
- **`mistralai/Mistral-Small-4-119B-2603`** : c'est le seul Mistral avec une
  vraie bascule par requête (`reasoning_effort`, mode instantané vs
  raisonnement) — structurellement le plus proche de ce que ce moteur
  attend — mais 119B de paramètres totaux (MoE, A6B actifs) doivent malgré
  tout tenir entièrement en VRAM au chargement : sans rapport avec une carte
  à 16,3 Go, indépendamment du nombre de paramètres actifs par requête.
- **`mistralai/Mistral-Small-3.2-24B-Instruct-2506`** : pas de mode
  raisonnement du tout (Instruct seul) — hors sujet pour ce moteur qui a
  besoin des deux modes sur les mêmes poids.

Verdict : à taille égale avec le pin actuel, Mistral n'offre aujourd'hui
aucun candidat à un seul checkpoint qui bascule proprement entre raisonnement
et réponse rapide — exactement la propriété que Qwen3/Qwen3.5 et Granite 4.2
ont, chacun à sa façon (§ci-dessus). Pas un jugement sur la qualité des
modèles Mistral en soi, un constat sur l'ajustement à la forme précise de ce
moteur.

### Écartés d'office, pas classés

- `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` et les variantes `*-Thinking-2507`
  (Qwen3-4B/30B-A3B/235B-A22B) : raisonnement toujours actif, aucune bascule
  `enable_thinking` réelle — incompatible structurellement avec le pilotage
  décision-par-décision de ce moteur, indépendamment de tout score de
  benchmark. Même chose en miroir pour les variantes `*-Instruct-2507` :
  jamais de raisonnement, dans l'autre sens.
- Qwen3.6/3.8 (27B, les plus petits membres denses **ouverts** de ces
  générations) : même à 4 bits, les poids seuls (~13,5 Go) engloutiraient tout
  le budget avant cache KV ni marge. Qwen3.7 : poids fermés (API seulement).
  Les variantes MoE de 3.5/3.6/3.8 : empreinte totale bien plus grande malgré
  un faible nombre de paramètres actifs, et toute la lignée à partir de 3.5
  est sortie multimodale (`image-text-to-text`) — un axe que ce projet n'a
  jamais exercé en texte seul.

**Ce classement reste une lecture de recherche web, pas une mesure.** Avant
d'agir dessus : faire tourner réellement `check_llm_stack_versions.py
--discover` (§3) sur une machine avec accès HF, qui confirmera ou infirmera
chaque point ci-dessus contre l'API réelle plutôt que contre un résumé de
page web.
