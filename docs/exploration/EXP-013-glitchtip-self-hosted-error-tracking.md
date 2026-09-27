# EXP-013 — GlitchTip (self-hosted) : le handler global logge, mais est-ce que quelqu'un le lit ?

- **Date** : 2026-09-11 · **Statut** : adopté · **Coût réel** : ~3h (recherche architecture GlitchTip réelle vs supposée, écriture du compose, mise en service réelle, découverte + vérification de la double capture, écriture du test de régression, gates)
- **Verdict en une phrase** : oui — un seul `sentry_sdk.init()` gated sur `GLITCHTIP_DSN`, posé avant `FastAPI(...)`, capture réellement les deux chemins visés (le handler global *et* les erreurs déjà interceptées en interne par les workers) contre une vraie instance GlitchTip self-hébergée, sans toucher un seul fichier de worker — mais l'architecture réelle de GlitchTip (v6, tout-en-un) et le comportement réel de `TestClient` face à un handler `Exception` global se sont tous les deux révélés différents de ce que la prémisse de ce lot supposait.

## Hypothèse de départ

`PLAN_SOLIDITE_TECHNIQUE.md` (Lot 10) : « Le handler global ajouté le 06/09
*logge* — mais personne ne lit les logs d'une app pédagogique. Sans
collecteur, ce travail ne sert à rien en pratique. » Le choix explicite était
GlitchTip self-hébergé (jamais Sentry SaaS). La prémisse technique à vérifier,
pas à supposer : `configure_logging()` route tout `log.error(...)` à travers
le module `logging` stdlib ; le `LoggingIntegration` par défaut de
`sentry_sdk.init()` capture tout appel `logging.error()`/`.exception()` comme
événement — donc un seul point d'intégration capturerait à la fois le handler
global **et** chaque worker qui catch déjà sa propre exception en interne
(`api/domain/**`, `log.error(..., exc_info=True)`, jamais remonté au
handler).

La consigne était explicite : vérifier contre une vraie instance qui tourne,
pas seulement écrire du code qui « a l'air juste ».

## Protocole

### 1. Le docker-compose officiel de GlitchTip — pas depuis la mémoire d'entraînement

Le dépôt `gitlab.com/glitchtip/glitchtip` (celui que la tâche nommait) est en
réalité un *meta-repo* (wiki, gouvernance) sans code ni compose file. Le vrai
code vit dans `gitlab.com/glitchtip/glitchtip-backend` (trouvé en listant les
projets du groupe GitLab via l'API). Son `compose.yml` est un compose de
**développement** (build from source, montage du code) — pas la référence
self-host. La vraie référence self-host est un fichier statique séparé,
`https://glitchtip.com/assets/compose.sample.yml`, lié depuis la page
d'installation officielle (`glitchtip.com/documentation/install`), récupéré
et lu pour de vrai (`curl`), pas résumé par un fetch générique.

Tag GitLab le plus récent au 2026-09-11 : `v6.2.6`. Tag Docker Hub exact
correspondant vérifié via l'API Docker Hub (`hub.docker.com/v2/repositories/
glitchtip/glitchtip/tags`) : `glitchtip/glitchtip:6.2.6` existe bien
(poussé 2026-08-08), donc pinné exactement plutôt que le tag flottant `:6`
que le sample officiel utilise lui-même (leur politique documentée :
mineur/patch non-breaking, donc suivre le majeur est un choix assumé côté
GlitchTip — mais la convention de ce dépôt pin toujours l'exact, cf.
`requirements.txt`, `docker-compose.llm.yml`).

### 2. Divergence n°1 (trouvée en vérifiant, pas supposée) : pas de services séparés `migrate`/`worker`

La tâche demandait, en citant une architecture GlitchTip classique :
« postgres, redis, a one-off migrate job, `web`, and `worker` services at
minimum ». Le compose officiel réel (v6, 2026) n'a **qu'un seul service**
`web` avec `SERVER_ROLE=all_in_one` — cela embarque le worker
(`GLITCHTIP_EMBED_WORKER` implicite) **et** lance les migrations
automatiquement au démarrage (`SKIP_INIT` par défaut `False`), confirmé en
lisant la doc des variables d'environnement et en observant les logs réels du
conteneur (`Starting worker with concurrency=20...`, `Local scheduler lock
acquired...` — dans le MÊME conteneur que le serveur web). Le modèle
« web + worker + migrate séparés » existe toujours (pour scaler
horizontalement), mais n'est plus le défaut recommandé — inutile à l'échelle
de cette app pédagogique. `docker-compose.observability.yml` documente cette
divergence en tête de fichier plutôt que de la corriger silencieusement.

### 3. Mise en service réelle

```
docker compose -f docker-compose.observability.yml up -d
```

postgres:18 + valkey/valkey:9 + `glitchtip/glitchtip:6.2.6` (`SERVER_ROLE=
all_in_one`) démarrent proprement ; `/`_health/` répond `ok` en ~15s.
Port hôte 8080 (pas le défaut 8000 — déjà pris sur cette machine par
`docker-compose.llm.yml`/vLLM, `docker ps` vérifié avant de choisir).

### 4. Divergence n°2 : le premier compte ne se fait ni par signup UI ni par `createsuperuser`

La tâche envisageait `GLITCHTIP_ENABLE_ORGANIZATION_CREATION` + signup UI, ou
un équivalent `createsuperuser`. Les deux existent réellement (confirmé dans
la doc d'install : le tout premier utilisateur peut toujours créer la toute
première organisation via l'UI, `ENABLE_ORGANIZATION_CREATION` ne restreint
qu'« après la première » ; `createsuperuser` existe sous `[auth]` dans
`./manage.py help`) — mais il existe une troisième voie, non mentionnée dans
la tâche, bien plus rapide pour un premier essai scripté :
`./manage.py bootstrap_dev`, listée dans `[projects]` de `./manage.py help`,
description : « Bootstrap a dev environment with a user, org, project, and
API token ». Exige `DEBUG=True` (échoue explicitement sinon : `CommandError:
bootstrap_dev requires DEBUG=True`) — ajouté au compose avec un commentaire
expliquant pourquoi c'est acceptable ici (stack dev/eval locale uniquement,
jamais exposée).

Exécutée une fois, en une commande :
```
docker compose -f docker-compose.observability.yml exec web ./manage.py bootstrap_dev
```
Sortie réelle : un user (`test@example.com`), une org (`org`), un projet
(`project`), une team, un token API, et surtout une **vraie DSN** :
`http://5026852a3ec34dfaa13ba34fcd928c04@localhost:8080/1`.

### 5. `sentry-sdk` réel, contre l'API réellement installée

`sentry-sdk==2.69.1` (dernière stable PyPI au 2026-09-11, vérifié via
`pip index versions`). Pas d'`integrations=[FastApiIntegration(), ...]`
explicite dans `api/main.py` : sentry-sdk a un mécanisme d'« auto-enabling
integrations » qui détecte `fastapi`/`starlette` installés et les active tout
seul — confirmé en inspectant le traceback réel d'une requête capturée (les
frames passent par `sentry_sdk/integrations/starlette.py` et
`sentry_sdk/integrations/fastapi.py` alors qu'aucune de ces classes n'a été
nommée dans le code de ce dépôt).

Isolation du client réel (`sentry_sdk.get_client()`/`sentry_sdk.get_global_
scope().set_client(...)`) et pattern de transport factice
(`sentry_sdk.transport.Transport`, sous-classé pour intercepter au lieu
d'envoyer) confirmés en lisant le code source installé de sentry-sdk (pas la
doc) : `make_transport()` accepte directement une instance de `Transport`
passée à `init(transport=...)` — c'est exactement le mécanisme que le
conftest.py du dépôt `getsentry/sentry-python` lui-même utilise pour ses
propres tests.

### 6. Preuve live des deux chemins de capture, contre la vraie instance

Un `uvicorn` local pointé sur la vraie DSN (`GLITCHTIP_DSN=http://...@
localhost:8080/1`), avec deux sondes ajoutées temporairement (jamais
committées — script jetable en dehors du dépôt) :

- **Chemin 1 — handler global** : une route qui lève une exception non
  gérée. `GET` dessus → `500 {"detail": "Internal server error"}`, log réel
  `http.unhandled_exception` observé côté serveur.
- **Chemin 2 — erreur déjà catchée par un worker** : `api/domain/public.py`'s
  `_simulate_worker` catch déjà tout et logge `public.simulate.failed`
  (`exc_info=True`) — mais aucune entrée réellement invalide via l'API
  publique ne le déclenche (`num_candidates`/`num_voters` sont *clampés*, pas
  rejetés ; c'est justement pourquoi le test existant de ce fichier
  (`test_public_v1.py::test_500_and_logs_on_compute_failure`) force l'échec
  en monkeypatchant `compare_all_methods`, pas via un input réel). Même
  technique reprise ici, mais appliquée à un vrai process serveur (le
  monkeypatch tourne au démarrage du process cible, avant `uvicorn.run`) puis
  déclenchée par une vraie requête HTTP `POST /api/v1/simulate` — sans
  toucher au code d'erreur du worker lui-même.

Les deux routes retournent un vrai `500` sur le réseau ; le fichier de log du
process confirme les deux lignes `error`.

Vérifié contre l'API GlitchTip elle-même (pas seulement « ça n'a pas
crashé ») :
```
curl -H "Authorization: Bearer <token>" \
  http://localhost:8080/api/0/organizations/org/issues/?project=1
```
**4 issues réelles** sont apparues (`PROJECT-1` à `PROJECT-4`), horodatées à
la seconde des deux déclenchements. Découverte non anticipée : **chaque
déclenchement produit DEUX événements**, pas un — le `LoggingIntegration`
capture l'appel `log.error(...)` (titre = la ligne de log complète,
colorée ANSI en dev à cause du `ConsoleRenderer` de `configure_logging()`),
**et**, indépendamment, l'intégration Starlette/FastAPI auto-activée capture
l'exception elle-même (titre propre : `ValueError: ...` /
`HTTPException: Simulation failed: ...`, avec fichier/fonction corrects).
Pour le chemin 2 en particulier, ceci confirme que même une erreur qu'un
worker « avale » complètement (elle ne remonte jamais au handler catch-all)
finit quand même par traverser Starlette une seconde fois sous forme de
`HTTPException(500)` (le mécanisme `raise_for_status`/`run_worker_bounded`
de `api/core/worker_dispatch.py`), donc capturée une seconde fois,
indépendamment du `log.error` du worker.

### 7. Divergence n°3 : `TestClient` par défaut masque le handler global

En écrivant le test de régression, `TestClient(app)` par défaut
(`raise_server_exceptions=True`) **re-lève** l'exception vers l'appelant du
test au lieu de renvoyer la réponse 500 que le handler catch-all a pourtant
bien construite (le `log.error` se déclenche, visible dans la sortie) — un
artefact de Starlette quand plusieurs `@app.middleware("http")`
(`BaseHTTPMiddleware`) sont empilés au-dessus d'un handler `Exception`
global, propre à ce fichier (`security_headers`, `default_rate_limit_state`,
`log_requests`). `raise_server_exceptions=False` est nécessaire pour observer
ce qu'un vrai client HTTP reçoit réellement — confirmé identique au
comportement d'un vrai `uvicorn` interrogé via `curl` (étape 6). Documenté
dans `api/tests/test_error_tracking.py` pour que ça ne se reperde pas au
prochain test similaire.

## Ce que ça a coûté

- Recherche de la vraie architecture GlitchTip (le meta-repo GitLab n'a pas
  le code ; le compose sample est un asset statique du site marketing, pas du
  dépôt de code) : ~45 min à elle seule, entièrement due à une prémisse
  (« web + worker + migrate ») qui datait d'une version antérieure du
  produit.
- Écriture + vérification live du compose : ~40 min (choix de port, découverte
  de `bootstrap_dev`, `DEBUG=True` requis).
- Vérification live des deux chemins + lecture de l'API GlitchTip : ~40 min.
- Test de régression (isolation du client sentry_sdk entre tests, choix du
  mécanisme de capture) : ~35 min.
- Gates (`mypy`, `pytest`, `ruff`) : quelques minutes, rien à corriger.

Aucun faux positif rencontré côté GlitchTip lui-même — chaque déclenchement
attendu a produit une entrée réelle, immédiatement, sans configuration
supplémentaire au-delà de la DSN.

## Verdict et pourquoi

**Adopté.** La prémisse centrale du Lot 10.1 tient : un seul point
d'intégration (`sentry_sdk.init()`, gated sur `GLITCHTIP_DSN`, posé avant la
construction de `FastAPI(...)`) capture réellement les deux familles
d'erreurs visées, sans modifier un seul fichier de worker existant — vérifié
contre une vraie instance GlitchTip self-hébergée, pas supposé depuis la
documentation. Le fait que trois détails d'implémentation se soient révélés
différents de la prémisse de départ (architecture all-in-one plutôt que
web/worker/migrate séparés ; `bootstrap_dev` plutôt que signup UI ou
`createsuperuser` ; `TestClient` par défaut masquant le comportement réel)
n'invalide rien — au contraire, c'est exactement le genre d'écart que ce
plan est construit pour débusquer avant qu'il ne devienne une supposition
tranquillement fausse dans un futur commit.

## Ce que j'en retiens (transférable à un autre projet)

- **Un « docker-compose officiel » nommé dans une tâche peut vivre ailleurs
  que le dépôt qu'on croit** : un meta-repo GitHub/GitLab au nom du produit
  n'est pas nécessairement là où vit le code ou les assets d'installation.
  Lister les projets du groupe/organisation avant de conclure à l'absence
  d'un fichier.
- **Une intégration de logging existante peut produire un doublon avec une
  intégration framework auto-activée** — les deux capturent la même erreur
  sous un angle différent (message de log brut vs exception structurée).
  Ni faux ni cassé, mais à anticiper avant de compter les issues dans un
  dashboard de suivi.
- **`TestClient(raise_server_exceptions=True)` (le défaut) n'est pas fiable
  pour vérifier le comportement d'un handler d'exception global** dès qu'il y
  a plusieurs middlewares `BaseHTTPMiddleware` au-dessus — vérifier contre un
  vrai serveur HTTP (même juste `uvicorn` + `curl` en local) avant de faire
  confiance à ce que `TestClient` par défaut rapporte pour ce genre de code.
