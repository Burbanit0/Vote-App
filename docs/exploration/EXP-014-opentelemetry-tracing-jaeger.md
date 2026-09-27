# EXP-014 — OpenTelemetry (traces) : Jaeger auto-hébergé, et le vrai graphe d'appel du moteur de vote

- **Date** : 2026-09-11 · **Statut** : adopté (périmètre volontairement réduit à un seul point de dispatch réel, pas de gate CI — un test de régression suffit, rien à gater) · **Coût réel** : ~2h (recherche de versions + vérification de l'image Jaeger + lecture du graphe d'appel réel + implémentation + vérification en direct + tests + incident de venv partagé + doc)
- **Verdict en une phrase** : adopté avec un périmètre délibérément étroit — un seul point de dispatch réel (`POST /api/v2/simulations`, ranked+scores) porte les spans par méthode plutôt que les ~15 sites d'appel dispersés du moteur, cohérent avec l'effort `L`/récit ⭐⭐ que cet item s'attribue lui-même — et une vraie trace capturée par un Jaeger v2 réellement démarré confirme que ça fonctionne, avec une surprise en cours de route (l'image `jaegertracing/all-in-one` demandée par l'item est en réalité gelée depuis ~9 mois).

## Décision préalable — Jaeger auto-hébergé, pas un APM SaaS

Ce lot n'impose aucun collecteur : des traces OpenTelemetry ont besoin d'une
destination, et le choix (SaaS hébergé vs auto-hébergé) n'est tranché nulle
part dans `PLAN_SOLIDITE_TECHNIQUE.md` pour ce point précis. Un autre chantier
concurrent sur ce dépôt vient d'ajouter GlitchTip **auto-hébergé** pour le
suivi d'erreurs — le propriétaire du dépôt a explicitement choisi
l'auto-hébergement plutôt qu'une option SaaS quand la question s'est posée.
Décision ici : **rester cohérent avec cette préférence déjà exprimée** plutôt
que d'ouvrir un nouvel arbitrage non confirmé pour le tracing — un Jaeger
*all-in-one* (image Docker unique, zéro compte, zéro inscription, gratuit,
local, réversible) plutôt qu'un APM SaaS. C'est un choix par défaut, pas une
validation explicite du propriétaire du dépôt *pour le tracing* — d'où cette
section en tête de carnet, pour qu'il soit facile à revoir si ce n'est pas le
bon calcul.

## Hypothèse de départ

La seule phrase de `PLAN_SOLIDITE_TECHNIQUE.md` pour cet item : « Traces par
endpoint, temps réel par méthode de vote — alimente aussi le Lot 8. » Trois
choses à vérifier avant d'écrire du code, pas à supposer :

1. Les paquets OpenTelemetry Python suggérés sont-ils toujours les paquets
   activement maintenus, à quelles versions ?
2. `jaegertracing/all-in-one` (le nom evident pour « essayer OTel en local »)
   est-il toujours l'image à utiliser ?
3. « Le » point de dispatch par méthode de vote — au singulier, comme le
   demande l'item — existe-t-il vraiment dans ce code, ou le graphe d'appel
   réel est-il plus éclaté que ça ?

## Protocole

### 1. Versions réelles, pas supposées

`pip index versions` (pas une recherche web) contre le vrai PyPI :

| Paquet | Version retenue | Note |
|---|---|---|
| `opentelemetry-api` | 1.44.0 | dernière stable |
| `opentelemetry-sdk` | 1.44.0 | dernière stable |
| `opentelemetry-exporter-otlp-proto-http` | 1.44.0 | dernière stable |
| `opentelemetry-instrumentation-fastapi` | 0.65b0 | le dépôt `contrib` ne publie QUE des pré-releases `0.xxb0` — `pip index versions` sans `--pre` retourne silencieusement « aucune distribution trouvée », un piège trouvé en le heurtant directement |

`opentelemetry-instrumentation-fastapi` à `0.65b0` est bien la ligne
compatible avec le cœur à `1.44.0` : l'écart de version entre les deux
lignes (65-44=21) correspond exactement à celui déjà observé entre les
paquets `opentelemetry-instrumentation*` (`0.58b0`) et `opentelemetry-sdk`
(`1.37.0`) déjà présents dans le venv partagé de cette machine — installés
là comme dépendance transitive de `semgrep`, pas par ce dépôt (voir la
section « surprise » plus bas).

### 2. `jaegertracing/all-in-one` — vérifié, pas supposé, et non retenu

L'item cite `jaegertracing/all-in-one` comme configuration standard pour «
essayer OTel en local ». Vérifié en direct contre Docker Hub avant de
l'utiliser : cette image est **effectivement gelée** — dernier tag
(`1.76.0`) et `latest` poussés il y a ~9 mois au moment d'écrire ceci, aucune
publication depuis. Jaeger a migré vers **Jaeger v2** (binaire unifié),
publié sous un nom d'image différent, `jaegertracing/jaeger` — toujours
disponible en mode "all-in-one" (collector + query + stockage en mémoire
dans un seul process) sans configuration particulière. Confirmé en direct
sur Docker Hub : `jaegertracing/jaeger:2.20.0`, poussé il y a ~2 mois,
identique au tag `latest`. `docker-compose.observability-tracing.yml`
utilise cette image, pas le nom historique que l'item suggérait —
suivre la lettre d'une suggestion vraisemblablement obsolète aurait été
moins utile que la vérifier d'abord.

Ports OTLP confirmés actifs par défaut sur cette image (doc officielle +
vérification en direct ci-dessous) : 4317 (gRPC), 4318 (HTTP). UI sur 16686.

### 3. HTTP plutôt que gRPC — un choix, pas une contrainte

Jaeger v2 expose les deux receveurs OTLP par défaut ; aucun écart
fonctionnel entre les deux pour ce cas d'usage. Retenu : `opentelemetry-
exporter-otlp-proto-http`, qui n'a pas de dépendance `grpcio` — ce dépôt
traite déjà la disponibilité des wheels Python 3.14 comme une contrainte
réelle (le commentaire scipy de `requirements.txt`). Vérifié pour être
honnête sur la raison : `grpcio` publie en fait déjà une wheel `cp314`
(`grpcio-1.83.1-cp314-cp314-manylinux…`, téléchargée avec succès) — ce
n'est donc pas un contournement de compatibilité forcé, juste un choix
« pas de raison de payer cette dépendance en plus quand les deux protocoles
sont équivalents ici ».

### 4. Le graphe d'appel réel — pas un point de dispatch unique

L'item demande « le » point de dispatch par méthode de vote, au singulier.
Grep systématique des appelants de `simulation_ranked_utils.py` /
`simulation_score_utils.py` (hors tests et le module lui-même) : **15
modules distincts** appellent directement ces fonctions, chacun avec son
propre dict littéral `{méthode: fonction(...)}` inline —
`_electorate.py`, `workers.py`, `workers_advanced.py`,
`workers_behavioral.py`, `workers_mechanisms.py`,
`domain/polity/ballot_and_aggregation.py`, `domain/simulations/base.py`,
`domain/simulations/compare.py`, `domain/theory/workers.py`,
`arrow_criteria.py`, `campaign_dynamics.py`, `gibbard_satterthwaite.py`,
`real_election_data.py`, `simulation_metrics.py`,
`simulation_voting_utils.py`. Il n'existe **aucun** dispatcher central dans
ce backend — chaque worker inline son propre sous-ensemble de méthodes.

Instrumenter les 15 sites aurait été un changement bien plus large que le
budget `L`/⭐⭐ que cet item s'attribue lui-même (« garder le périmètre
proportionné, ne pas sur-construire »). Décision : instrumenter **un seul**
point de dispatch réel, choisi pour être (a) atteignable par une vraie
requête HTTP, (b) déjà couvert par une route + des tests existants, (c)
représentatif des deux familles de méthodes (ordinales et cardinales) —
`api/domain/simulations/base.py`'s `_simulate_votes_worker`, qui sert `POST
/api/v2/simulations` (l'endpoint legacy déjà testé, dont la branche
`scores` vient d'être couverte par un commit récent de ce même dépôt) et
calcule déjà les 12 vainqueurs ordinaux + 6 vainqueurs cardinaux par
requête. Les 14 autres sites restent non tracés — décision de périmètre
explicite, documentée ici, pas un oubli.

### 5. Propagation de contexte à travers un thread — vérifiée, pas supposée

`_simulate_votes_worker` s'exécute hors de la boucle événementielle via
`asyncio.to_thread` (`api/core/worker_dispatch.py`). OpenTelemetry
s'appuie sur `contextvars` pour propager le span courant — une inquiétude
légitime avant d'écrire le moindre span : est-ce que ce déport de thread
casse la relation parent/enfant entre le span de requête HTTP
(auto-instrumenté) et les spans par méthode ? Vérifié dans le code source
de `asyncio.to_thread` (stable depuis Python 3.9) : il exécute la fonction
via `contextvars.copy_context().run(func, *args)`, ce qui propage
explicitly le contexte courant dans le thread. Confirmé en direct dans la
trace capturée ci-dessous : les 12 spans `voting_method.*` ont bien pour
parent le span de requête, malgré la traversée de thread — zéro code de
liaison supplémentaire nécessaire.

### 6. Implémentation

- `api/core/config.py` : `otel_exporter_otlp_endpoint` (défaut `""` =
  désactivé) + `otel_service_name`. Même motif que `redis_url`/GlitchTip
  ailleurs dans ce fichier.
- `api/core/tracing.py` (nouveau) : `configure_tracing()` (installe un
  `TracerProvider` + `OTLPSpanExporter` + `BatchSpanProcessor`, no-op si
  l'endpoint est vide) et `instrument_app()` (`FastAPIInstrumentor`, même
  garde). Piège d'API trouvé en lisant la source du paquet installé plutôt
  qu'en supposant : `OTLPSpanExporter(endpoint=...)` n'ajoute
  `/v1/traces` automatiquement QUE lorsque l'endpoint est lu depuis la
  variable d'environnement `OTEL_EXPORTER_OTLP_ENDPOINT` par l'exporteur
  lui-même — un `endpoint=` explicite au constructeur est utilisé tel
  quel, donc `tracing.py` ajoute `/v1/traces` lui-même.
- `api/main.py` : `configure_tracing()` + `instrument_app(app)` appelés au
  niveau module, avant le wrap Socket.IO (`app` est encore la vraie
  instance FastAPI à ce point du fichier).
- `api/domain/simulations/base.py` : `_traced_winner(method, fn, *args)` —
  `tracer.start_as_current_span(f"voting_method.{method}", attributes=
  {"voting.method": method})` autour de chaque appel de fonction de
  vainqueur, dans les branches `ranked` et `scores` de
  `_simulate_votes_worker`. `tracer = trace.get_tracer(__name__)` au
  niveau module — se résout paresseusement vers le tracer no-op tant
  qu'aucun `TracerProvider` réel n'est installé (comportement du
  `ProxyTracer` d'`opentelemetry-api`, vérifié dans sa source), donc aucun
  `if` conditionnel n'est nécessaire au site d'appel.

### 7. Vérification en direct — pas juste "le code a l'air bon"

1. `docker compose -f docker-compose.observability-tracing.yml up -d` →
   `jaegertracing/jaeger:2.20.0` démarré avec succès, UI répond 200 sur
   `:16686`.
2. API lancée en local (`uvicorn`, hors Docker) avec
   `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` — log
   `tracing.configured` confirmé au démarrage.
3. `POST /api/v2/simulations` avec `simulationType: "ranked"` (200), puis
   `"scores"` (200).
4. Interrogation de l'**API** de Jaeger (pas seulement l'UI cliquée à la
   main) : `GET /api/services` → `["jaeger", "vote-lab-api-verify"]`.
   `GET /api/services/vote-lab-api-verify/operations` → 18 opérations
   `voting_method.*` (12 ordinales + 6 cardinales) en plus de `POST
   /api/v2/simulations`. `GET /api/traces/<id>` sur la requête `ranked` :
   17 spans — le span racine `POST /api/v2/simulations` (9,37 ms) avec 12
   enfants `voting_method.<règle>` (8 à 69 µs chacun), tous avec l'attribut
   `voting.method` correctement renseigné et le bon `parent` (le span
   racine). Exemple exact extrait de la trace :

   ```
   POST /api/v2/simulations           9373us  (racine)
   ├─ voting_method.condorcet           44us  voting.method=condorcet
   ├─ voting_method.two_round           17us  voting.method=two_round
   ├─ voting_method.borda               22us  voting.method=borda
   ├─ voting_method.plurality            8us  voting.method=plurality
   ├─ voting_method.approval            18us  voting.method=approval
   ├─ voting_method.irv                 21us  voting.method=irv
   ├─ voting_method.coombs              26us  voting.method=coombs
   ├─ voting_method.positional_score    25us  voting.method=positional_score
   ├─ voting_method.kemeny_young        69us  voting.method=kemeny_young
   ├─ voting_method.bucklin             17us  voting.method=bucklin
   ├─ voting_method.minimax             35us  voting.method=minimax
   └─ voting_method.schulze             31us  voting.method=schulze
   ```

   C'est exactement ce que l'item demande : le temps par méthode de vote
   est visible séparément du temps par requête, dans une vraie trace
   capturée par un vrai collecteur — pas une affirmation basée sur la seule
   absence d'erreur au démarrage.
5. Nettoyage : process `uvicorn` arrêté, `docker compose … down` (sans
   `--remove-orphans` — d'autres conteneurs d'un chantier concurrent
   tournaient sur cette même machine, intentionnellement laissés
   intacts).

### 8. Test de régression — in-memory span exporter

`api/tests/test_tracing.py` : `opentelemetry.sdk.trace.export.
in_memory_span_exporter.InMemorySpanExporter` + un `TracerProvider` de test
installé une fois pour le process, puis appel direct de
`_simulate_votes_worker` (pas de vrai collecteur nécessaire). Trois cas :
branche `ranked` → exactement 12 spans ; branche `scores` → exactement 6 ;
branche `votes` → 0 span (témoin négatif, cette branche n'appelle jamais de
fonction de vainqueur). Les trois passent.

### 9. Surprise — un venv de dev partagé entre agents concurrents

`fast_api_voter/.venv` (utilisé par tous les worktrees de cette machine
faute d'un venv par worktree) avait déjà `opentelemetry-api`/`-sdk`/
`-exporter-otlp-proto-http` à `1.37.0` et `opentelemetry-instrumentation*`
à `0.58b0` — installés comme dépendances transitives de **`semgrep`**
(épinglées par lui à `~=1.37.0`/`==0.58b0`), pas par ce dépôt. Installer
les versions `1.44.0`/`0.65b0` que cet item demande dans ce même venv
partagé casse immédiatement ces épingles (`pip` l'a signalé sans attendre
une exécution réelle de `semgrep`). Comme cette machine fait tourner
plusieurs agents concurrents sur des worktrees différents qui partagent
probablement ce même venv, casser l'environnement de dev partagé aurait
été un problème plus large et plus difficile à diagnostiquer pour un autre
chantier que pour celui-ci. Corrigé en réinstallant les versions d'origine
dans le venv partagé (vérifié : `semgrep --version` fonctionne toujours
après) et en construisant un venv jetable, propre à cette tâche, pour
toute la vérification (`pytest`, `mypy`, `uvicorn`) — `requirements.txt`
du dépôt reste la seule source de vérité pour CI et pour un venv frais.

## Ce que ça a trouvé

- L'image `jaegertracing/all-in-one` demandée par l'item est en réalité
  gelée depuis ~9 mois — utiliser `jaegertracing/jaeger:2.20.0` (Jaeger v2)
  à la place, vérifié en direct.
- `opentelemetry-instrumentation-fastapi` ne publie que des pré-releases —
  `pip index versions` sans `--pre` masque silencieusement son existence.
- Le graphe d'appel du moteur de vote n'a pas de dispatcher central : 15
  sites d'appel distincts, pas un seul comme l'item le laissait entendre —
  périmètre réduit à un seul en conséquence, documenté explicitement plutôt
  que laissé implicite.
- Une trace réelle, capturée par un Jaeger effectivement démarré, avec le
  détail par méthode visible et correctement imbriqué sous le span de
  requête malgré la traversée d'un thread (`asyncio.to_thread` propage bien
  les contextvars, vérifié dans sa source).
- Un venv de dev partagé entre agents concurrents sur cette machine est un
  vecteur de collision réel (conflit avec les dépendances OTel de
  `semgrep`), pas hypothétique.

## Ce que ça a coûté

~2h : ~30 min recherche de versions + vérification image Jaeger (Docker
Hub, docs officielles, wheel `grpcio` cp314) ; ~20 min lecture du graphe
d'appel réel (grep systématique avant d'écrire le moindre span) ; ~40 min
implémentation (config, module de tracing, spans, docker-compose) ; ~20 min
vérification en direct (Jaeger + API + trace réelle) ; ~15 min test de
régression + incident de venv partagé + réparation. Une nouvelle
dépendance de production (le groupe OpenTelemetry, 4 paquets, désactivé
par défaut) ; zéro dépendance de dev supplémentaire (le venv jetable de
vérification n'est pas committé).

## Verdict et pourquoi

**Adopté**, avec un périmètre volontairement étroit :

1. La prémisse de l'item (« traces par endpoint, temps réel par méthode de
   vote ») est démontrée pour de vrai sur un point de dispatch réel et
   atteignable en HTTP — pas seulement plausible sur le papier.
2. Le périmètre est délibérément réduit à ce point de dispatch unique, pas
   aux ~15 sites d'appel dispersés du moteur — cohérent avec l'effort
   `L`/récit ⭐⭐ que l'item s'attribue lui-même, et évite de sur-construire
   un item déjà signalé comme le moins prioritaire des trois du Lot 10.
3. No-op par défaut (`OTEL_EXPORTER_OTLP_ENDPOINT` vide) : zéro coût pour
   quiconque ne configure pas de collecteur — même contrat que Redis/
   GlitchTip ailleurs dans `config.py`.
4. Le choix du collecteur (Jaeger auto-hébergé) reste un défaut cohérent
   avec la préférence déjà exprimée pour GlitchTip, pas une validation
   explicite pour le tracing spécifiquement — à confirmer ou à corriger par
   le propriétaire du dépôt.

## Ce que j'en retiens (transférable à un autre projet)

1. **Un nom d'image Docker "évident" pour un outil d'observabilité peut
   être gelé sans que la doc grand public le crie sur les toits** — la
   page "getting started" la plus citée pour Jaeger nomme encore
   implicitement `all-in-one` dans beaucoup de tutoriels alors que le
   projet a migré vers un nom d'image différent. Vérifier la fraîcheur
   réelle (date du dernier push, pas juste "l'image existe encore") avant
   de graver un nom d'image dans un fichier destiné à durer.
2. **« Le » point de dispatch d'un item de plan n'existe pas toujours** —
   grep le graphe d'appel réel avant d'écrire le moindre span plutôt que de
   supposer une architecture centralisée qui n'a jamais été construite.
   Réduire le périmètre en conséquence, explicitement, plutôt que
   d'essayer de forcer une prémisse fausse à tenir en instrumentant 15
   sites disparates sous pression de "faire ce que l'item dit".
3. **Vérifier la propagation de contexte à travers une frontière de
   thread/process avant de committer une architecture de tracing** —
   `contextvars` + `asyncio.to_thread` fonctionnent ensemble par défaut
   depuis longtemps, mais ce n'est pas vrai de toutes les frontières de
   concurrence (un vrai pool de process, par exemple, ne le ferait pas) ;
   le vérifier dans le code source plutôt que de le supposer a évité un
   design de span cassé silencieusement (spans orphelins, jamais imbriqués
   sous la requête).
4. **Un venv de dev partagé entre agents/sessions concurrents sur une même
   machine est une source de collision réelle** — un outil de dev
   apparemment sans rapport (`semgrep`) peut épingler la même famille de
   dépendances qu'une nouvelle fonctionnalité, et casser silencieusement
   son fonctionnement pour tout le monde sur cette machine si l'installation
   se fait dans l'environnement partagé plutôt que dans un venv jetable
   dédié à la vérification.
