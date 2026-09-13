# EXP-016 — Script maison `check_llm_stack_versions.py` : la version épinglée du stack LLM est-elle encore la bonne ?

- **Date** : 2026-09-13 · **Statut** : adopté · **Coût réel** : ~12 min mesurées en direct dans le transcript de session (écriture du script + les deux cycles de debug en direct), à l'intérieur d'une séance plus large d'environ 8h non chronométrée par chantier séparé (corrections git/venv, mise à jour d'un doc de plan, audit de recherche à 3 agents) · **Coût en tokens** : ~96 k tok de sortie + ~170 k tok nouvellement mis en cache sur ~100 tours modèle en ~12 min (estimation transcript, `/cost` non lancé en séance — voir « Ce que ça a coûté » pour la réserve sur le chiffre de cache relu)
- **Verdict en une phrase** : un script maison sur l'API OCI Distribution v2 anonyme trouve une vraie dérive de version (deux images sur deux, un cran derrière) en ~1s une fois corrigé, mais son premier brouillon donnait une réponse silencieusement fausse en s'appuyant sur l'API REST commerciale de hub.docker.com, plafonnée en pagination anonyme bien avant la fin d'un dépôt à forte rotation de tags.

## Hypothèse de départ

Ce carnet ne part pas d'un item numéroté « Lot N » de
[`PLAN_SOLIDITE_TECHNIQUE.md`](../../PLAN_SOLIDITE_TECHNIQUE.md) — comme
[EXP-015](./EXP-015-hook-taskcompleted-recit-run-polity.md), c'est une
demande ad hoc directe, ici formulée avant un run de balayage de graines à
population 500 déjà évoqué comme prochaine étape ouverte dans
`docs/plan/polity/plan-distribution-positions-seeds.md` (« p500 reste
ouvert »). Cette expérience reste dans le périmètre de l'index pour la même
raison qu'EXP-015 : c'est un outil réel, avec un protocole rejouable et une
trouvaille vérifiable, pas une note de travail.

Le stack LLM de ce projet épingle tout délibérément — le commentaire de
module de `docker-compose.ollama.yml` le dit explicitement : « a pinned
version tag, not `latest` » — chaque pin a été vérifié à la main, une fois,
directement contre l'API source, jamais deviné ni copié depuis une page web
(voir les commentaires `--revision` de `docker-compose.llm*.yml`). La
question posée avant de commencer : peut-on automatiser cette même
vérification — « ce pin est-il encore le plus récent stable côté amont ? »
— de façon fiable, en s'appuyant uniquement sur des API de registre/hub
publiques et non authentifiées, sans compte ni jeton ? Rien ne présupposait
que ce soit trivial ni que ce soit fiable — c'est ce que l'expérience devait
trancher, pas une conclusion déjà connue.

## Protocole

Tout ce qui suit est rejouable avec
`python fast_api_voter/scripts/check_llm_stack_versions.py [--strict] [--json]`.

1. **Lecture des pins directement dans les fichiers compose**, pas
   maintenue à la main dans le script : `_collect_pins` parcourt
   `docker-compose.llm.yml` / `.llm-4b.yml` / `.llm-nvfp4.yml` / `.ollama.yml`
   via PyYAML, extrait `services.*.image` (repo:tag) et les paires
   `--model`/`--revision` dans `command`.
2. **Première version** : chaque image interrogée contre l'API REST de
   hub.docker.com (`/v2/repositories/<repo>/tags`, triée par
   `-last_updated`), recherche du plus récent tag matchant un regex semver
   stable strict (`vX.Y.Z[.postN]`, excluant `latest`/rc/alpha/beta/dev/
   nightly).
3. **Premier run réel, lancé en tâche de fond** à 05:21:52 —
   `Command did not complete within its 120s timeout and was moved to the
   background`, fichier de sortie vide à 05:23:58 (confirmé par lecture
   directe du fichier). Diagnostic fait en direct, pas supposé :
   `ss -tnp` sur le process montre une connexion `ESTAB` normale vers un
   hôte IPv4 (`3.168.73.129:443`) à côté d'une `SYN-SENT` vers une adresse
   IPv6 (`[2603:7001:...]:47022`) qui ne se résout jamais. Confirmé par
   trois `curl` directs contre la même URL Hugging Face : par défaut
   200/0,33 s ; forcé IPv4 (`-4`) 200/0,042 s ; forcé IPv6 (`-6`) `Connection
   timed out after 6002 milliseconds` (exit 28) — l'égress IPv6 de ce
   bac à sable est noire. httpx (client sync) n'a pas de repli
   Happy-Eyeballs comme `curl` : chacun des ~11 appels HTTP séquentiels
   pouvait payer la totalité du délai de connexion sur cette route morte.
   Correctif : `httpx.HTTPTransport(local_address="0.0.0.0")` pour forcer
   IPv4, plus un timeout scindé (`connect=5.0` / `read=15.0`) pour qu'une
   mauvaise route échoue vite plutôt que d'épuiser tout le budget.
4. **Deuxième run, complet en ~1s mais faux** (05:26:00) : `ollama/ollama`
   rapporté « up to date » avec un « latest stable » de `0.5.5` (poussé
   2025-01-11), contre un pin réel `0.33.3` (poussé 2026-09-03) — le tag
   « le plus récent » trouvé était en réalité vieux de plus d'un an. Au
   même run, `vllm/vllm-openai` était *lui aussi* faux dans l'autre sens :
   « latest stable » `v0.20.2` (poussé 2026-05-09), antérieur au pin réel
   `v0.28.0` — les deux checks étaient silencieusement dans l'erreur, pas
   seulement Ollama. Cause confirmée par inspection : trier par récence et
   ne lire que les 300 premiers tags (3 pages × 100) n'est pas une
   approximation sûre pour un dépôt à forte rotation de tags multi-arch —
   le vrai tag de release le plus récent peut être enterré loin au-delà de
   cette fenêtre par des republications récentes sans rapport.
5. **Tentative d'élargir le plafond de pagination** de l'API REST de
   hub.docker.com elle-même : mur confirmé en direct — `curl` complet avec
   en-têtes donne `HTTP 403` à la page 11 (offset 1000), corps
   `{"message":"pagination offset too large for anonymous requests; sign in
   to page further"}` (05:27:32). Le champ `count` de la même API confirme
   `ollama/ollama` = 1174 tags, `vllm/vllm-openai` = 598 — un dépôt réellement
   trop grand pour être énuméré ainsi sans authentification.
6. **Bascule complète vers l'API OCI Distribution v2 anonyme**
   (`registry-1.docker.io/v2/<repo>/tags/list`, paginée via l'en-tête
   `Link`, avec le même flux de challenge/réponse à jeton anonyme que
   `docker pull` utilise lui-même pour un dépôt public) — vérifiée d'abord
   dans un script jetable autonome : énumération complète et confirmée en
   direct, `TOTAL TAGS: 1176`, `BEST STABLE TAG: 0.34.0` (05:28:17), sans
   le plafond de la première API. Câblée ensuite dans le script définitif,
   et le même utilitaire d'authentification anonyme réutilisé pour le check
   de manifeste Ollama-library (`registry.ollama.ai`) que le script fait
   aussi, sans dupliquer le code.
7. Gates de ce projet passées à la fin (`python -m mypy scripts/
   check_llm_stack_versions.py`, `python -m ruff check
   scripts/check_llm_stack_versions.py` — invoquées via `-m`, pas via les
   scripts-console installés du venv), en trois passes itératives, pas d'un
   coup : 16 erreurs mypy à la première exécution (05:30:21) — un tuple
   optionnel comparé sans garde (`>=`/`<=` sur `tuple | None`), deux retours
   `Any` non typés, un argument `httpx` `Any | None` — réduites à 4 puis 1
   erreur après correction d'une réutilisation du même nom de variable dans
   les trois boucles de collecte (`image_check`/`model_check`/
   `ollama_check` au lieu d'un nom partagé), puis 0.

## Ce que ça a trouvé

**Premier run de production réel (05:33:04, sortie complète capturée) :**

- `vllm/vllm-openai` : pin `v0.28.0` (poussé 2026-08-26T09:20:42Z) vs
  `v0.29.0` disponible (poussé 2026-09-09T06:06:32Z) — **NEWER VERSION
  AVAILABLE**.
- `ollama/ollama` : pin `0.33.3` (poussé 2026-09-03T17:12:32Z) vs `0.34.0`
  disponible (poussé 2026-09-09T23:25:11Z) — **NEWER VERSION AVAILABLE**.
- Les 4 révisions Hugging Face épinglées (`Qwen/Qwen3-8B-AWQ`,
  `Qwen/Qwen3-4B`, `Qwen/Qwen3-4B-Base`, `ELVISIO/Qwen3-8B-NVFP4A16`)
  correspondent toutes exactement au HEAD actuel de leur dépôt — à jour.
- Le modèle Ollama-library `qwen3:8b` : digests de config et de poids
  identiques au pin enregistré dans le commentaire de
  `docker-compose.ollama.yml` — aucune dérive.

Aucun des deux bumps n'a été appliqué — le script ne fait que rapporter,
jamais éditer un compose file ni déclencher un pull, conformément à la
règle du projet (« bump is a deliberate, reviewable edit ») et pour ne pas
introduire une deuxième variable confondante juste avant le run p500 prévu.

**La vraie trouvaille de cette expérience n'est pas la dérive de version
elle-même — c'est que la première approche, plausible et basée sur une API
officielle, produisait un faux résultat silencieux** (« up to date » alors
que `ollama/ollama` était en réalité un peu plus d'un an de tags derrière un
plafond de pagination anonyme, et `vllm/vllm-openai` rapportait un « latest »
antérieur au pin réel). Un script qui répond « tu es à jour » quand ce n'est
pas vrai est pire que pas de script du tout, puisqu'il désarme la
vérification manuelle qu'il prétend remplacer. Le bug a été trouvé en
comparant le résultat à un fait déjà connu par ailleurs (`0.33.3` pinné le
2026-09-03 ne peut pas être plus récent que `0.5.5` daté 2025-01-11), pas
par une assertion du script lui-même.

## Ce que ça a coûté

Le fil de travail identifiable dans le transcript de session va de
l'écriture du fichier (05:21:43) au run final propre (05:33:14) : environ
11 min 30 s, ~100 tours modèle. Ce chiffre est net — le hang de 120 s, les
tests `curl -6`/`-4`, la découverte du mur à la page 11, la réécriture vers
l'API OCI et les trois passes mypy tiennent tous dans cette fenêtre — mais
il ne peut pas être proprement isolé du reste d'une séance de session
beaucoup plus longue (~8h, du 05:10 au 13:30 UTC ce jour-là) qui a aussi
couvert des corrections git/venv sans rapport, une mise à jour de document
de plan, et un audit de recherche à 3 sous-agents : ce n'était pas un bloc
de travail chronométré à part.

Coût en tokens, à partir des champs `usage` du transcript sur ce fil précis
(indices de ligne 237–504 du fichier de session `.jsonl`) : ~96 384 tokens
de sortie, ~170 372 tokens nouvellement écrits en cache (lectures de
fichiers/résultats d'outils), sur ~100 appels modèle. Le cumul de tokens de
cache **relus** sur ce même fil atteint ~20,15 millions — mais ce chiffre
ne doit pas être lu comme un coût marginal propre à cette expérience : il
reflète tout le contexte cumulé de la séance (jusqu'à ~242 k tokens de
contexte par tour vers la fin de ce fil) renvoyé intégralement à chaque
tour, un artefact du cache de prompt sur une longue session à contexte
unique, pas une mesure du travail spécifique à ce script. `/cost` n'a pas
été lancé en séance ; ceci est une estimation de transcript, pas une mesure
facturée.

Aucun temps CI ajouté : ce script n'est pas branché sur une porte CI, c'est
un outil de vérification manuelle à lancer avant un run coûteux. Coût de
maintenance résiduel mesuré directement : 474 lignes (`wc -l`), une seule
liste de baseline à mettre à jour à la main en cas de re-pin délibéré
(`_OLLAMA_LIBRARY_MODELS`), et une dépendance à deux API externes en plus de
Hugging Face (`registry-1.docker.io`, `hub.docker.com` pour l'horodatage
seul, `registry.ollama.ai`) — chacune peut échouer indépendamment et le
script est écrit pour rapporter « could not verify » plutôt que planter.

## Verdict et pourquoi

**Adopté.** Le script (`fast_api_voter/scripts/check_llm_stack_versions.py`)
existe, passe `mypy`/`ruff` sans erreur (vérifié directement, pas
transcrit), et a trouvé une dérive réelle et jusque-là inconnue dès son
premier run de production — sur les deux images qu'il vérifie, pas sur un
cas synthétique. À la date de rédaction de ce carnet, le fichier est encore
non suivi par git (`git status` : `??`) — écrit, vérifié, pas encore
committé.

Le verdict n'est pas seulement « ça marche » : c'est que la première
implémentation plausible, appuyée sur l'API officielle grand public de
hub.docker.com, échouait silencieusement sur exactement le cas qui compte
(un dépôt à forte rotation de tags où le vrai dernier stable n'est pas dans
les tags les plus « récemment mis à jour »), et que ce n'est qu'en
descendant au protocole de registre brut — celui que `docker pull`
utilise lui-même, sans commercialisation ni plafond anonyme différencié —
que la vérification est devenue correcte et complète.

## Ce que j'en retiens (transférable à un autre projet)

1. **Une API REST « pratique » construite au-dessus d'un registre n'a pas
   forcément les mêmes garanties que le protocole natif que les outils
   officiels utilisent.** hub.docker.com propose une API de confort
   (tri par date, pagination simple) mais la plafonne pour les requêtes
   anonymes ; l'API OCI Distribution v2 brute, plus rugueuse à utiliser
   (challenge de jeton, pagination par en-tête `Link`), n'a pas cette
   limite parce que c'est celle que `docker pull` lui-même doit pouvoir
   utiliser sans compte. Quand une vérification doit être *complète*, pas
   seulement pratique, préférer le protocole que l'outil officiel utilise
   lui-même à l'API de confort construite par-dessus.
2. **« Trier par récence et couper après N résultats » n'est une
   approximation sûre de « le plus récent stable » que si le volume de
   bruit (retags, builds multi-arch, republications) reste petit devant N.**
   Sur un dépôt à forte rotation, cette hypothèse casse silencieusement — le
   symptôme n'est pas une erreur, c'est une réponse plausible et fausse.
   Avant de couper une pagination à un plafond arbitraire, vérifier
   explicitement combien d'éléments existent au total (`count` ou
   équivalent) et comparer ce chiffre au plafond choisi, plutôt que de
   supposer que la fenêtre coupée contient déjà le maximum recherché.
3. **Un outil de vérification qui répond « tu es à jour » a plus de valeur
   négative qu'un outil absent s'il se trompe silencieusement** : il
   désarme la vigilance manuelle qu'il prétend remplacer sans qu'aucun
   signal n'indique que quelque chose a été raté. Traiter tout résultat
   « conforme » d'un tel outil comme suspect tant qu'il n'a pas été
   confronté à un fait déjà connu par un autre canal — ici, une date de
   publication déjà documentée dans le dépôt lui-même a suffi à révéler
   l'erreur.
4. **Une route réseau cassée dans un environnement (ici : egress IPv6
   noire dans ce bac à sable) peut se manifester comme un blocage total et
   silencieux plutôt que comme une erreur**, parce que les clients HTTP
   synchrones n'ont pas tous un repli Happy-Eyeballs comme `curl`. Face à
   un appel réseau qui ne rend jamais la main, diagnostiquer avec l'état de
   la socket (`ss -tnp`, l'état `SYN-SENT` qui ne progresse jamais) avant de
   supposer un problème côté serveur distant — et forcer explicitement la
   famille d'adresse qui fonctionne plutôt que d'augmenter le timeout.
