# EXP-012 — `prometheus-fastapi-instrumentator` + readiness/liveness split : `/health` reste-t-il vraiment « binaire » une fois qu'on y regarde ?

- **Date** : 2026-09-11 · **Statut** : adopté · **Coût réel** : ~2h30 (vérification maintenance des deux bibliothèques candidates, câblage `/metrics` + les deux nouvelles routes, un vrai cycle trouvaille→correction avec le contrat OpenAPI, un second avec le gate de licences, vérification en direct des trois endpoints + d'un scénario Redis injoignable)
- **Verdict en une phrase** : `prometheus-fastapi-instrumentator` retenu (actif, wrapper mince autour du `prometheus_client` officiel) plutôt que du câblage manuel, et vérifié en direct que ses compteurs bougent vraiment ; le vrai travail de fond n'était pas la bibliothèque mais la sémantique de `/health/ready` — puisque Redis est déjà conçu ici comme optionnel et dégradant gracieusement, la seule vraie « dépendance non prête » de cette app reste celle que `_check_redis()` distinguait déjà (configuré-mais-injoignable), pas l'absence de Redis elle-même — et deux trouvailles réelles en vérifiant plutôt qu'en supposant : Schemathesis a immédiatement détecté un `Content-Type` non documenté sur `/metrics`, et le gate de licences a rejeté la nouvelle dépendance de production avant correction.

## Hypothèse de départ

`PLAN_SOLIDITE_TECHNIQUE.md` (Lot 10) pose le problème sans l'ambiguïté
habituelle des autres items de ce lot : « `/health` existe mais reste
binaire ». Trois questions à trancher avant d'écrire la moindre ligne :

1. `prometheus-fastapi-instrumentator` (wrapper FastAPI) ou `prometheus_client`
   nu (câblage manuel d'une middleware) — lequel est réellement mieux
   maintenu aujourd'hui, pas juste plus connu ?
2. Qu'est-ce que « liveness » et « readiness » veulent dire concrètement
   pour CETTE app — un seul processus stateless, une seule dépendance
   optionnelle (Redis, déjà documentée comme dégradant gracieusement dans
   `_check_redis()`) — plutôt que copier le pattern générique k8s
   (DB obligatoire + cache optionnel + files d'attente) qui ne correspond à
   rien ici ?
3. Un `/metrics` non authentifié sur un déploiement public (Fly.io,
   `fly.toml`) est-il une vraie fuite d'information sur cette app précise,
   ou du bruit de conformité générique ?

## Protocole

### 1. Choix de bibliothèque — vérifié en direct, pas supposé

Même réflexe que EXP-004/EXP-009/EXP-011 : interroger l'état réel des deux
dépôts avant d'écrire du code, pas se fier à la notoriété du nom.

| | `prometheus-fastapi-instrumentator` | `prometheus_client` (nu) |
|---|---|---|
| Dépôt | `trallnag/prometheus-fastapi-instrumentator` | `prometheus/client_python` (le client officiel du projet Prometheus) |
| Archivé ? | Non (`gh api repos/... --jq .archived` → `false`) | Non |
| Dernier push | **2026-09-08** (3 jours avant cette session) | 2026-08-13 |
| Dernière release PyPI | 8.1.0, 26/07/2026 (8.0.0 29/05/2026 — cadence régulière) | (utilisé comme dépendance transitive, pas évalué seul) |
| Étoiles GitHub | 1 486 | 4 371 |
| Licence | ISC (OSI, permissive — pas dans l'allow-list actuelle de ce dépôt, voir plus bas) | `Apache-2.0 AND BSD-2-Clause` (déjà couvertes individuellement, mais pas cette expression composée exacte) |
| Ce que ça évite d'écrire | Une middleware ASGI qui mesure la durée/le compte par route + template de chemin (pas juste l'URL brute, qui exploserait la cardinalité sur des routes à paramètres) | La même middleware, à la main |

Décision : `prometheus-fastapi-instrumentator`. Il ne fait rien que
`prometheus_client` ne pourrait faire directement, mais l'énoncé de l'item
lui-même le décrit («&nbsp;wrapper FastAPI qui enregistre automatiquement un
endpoint `/metrics` et les métriques HTTP par défaut&nbsp;») et le vérifier en
direct plutôt que de l'assumer sur la seule notoriété était le point de cette
étape — dépôt actif il y a 3 jours, pas un nom connu mais à l'abandon (le
même risque que Lost Pixel dans EXP-004 ou `slsa-github-generator` dans
EXP-008). Il dépend de `prometheus_client` (le client officiel) en interne
— aucun risque de réinventer le format d'exposition Prometheus soi-même.

### 2. Additif, jamais une réécriture de `/health`

`fly.toml` cible `/api/v2/health` en dur pour son `[[http_service.checks]]`
de production — un vrai déploiement en dépend, pas une supposition. Décision
prise avant d'écrire une ligne : `/health` reste identique bit-pour-bit
(même route, même contrat 200/503, même corps), `/health/live` et
`/health/ready` sont deux routes NOUVELLES sur le même routeur. `fly.toml`
n'a pas été touché.

### 3. `/health/ready` — la vraie question du protocole

Lu `_check_redis()` avant d'écrire quoi que ce soit : le contrat existant
distingue déjà `{"ok": True, "configured": False}` (REDIS_URL absent — l'app
tourne stateless, c'est le déploiement de production documenté par
`fly.toml`: « Stateless: no Redis... required ») de `{"ok": False, "error":
"unreachable"}` (REDIS_URL configuré mais injoignable). Un pattern
readiness générique (« 503 si une dépendance ne répond pas ») appliqué
naïvement ici confondrait ces deux cas et referait exactement l'erreur que
Lot 10 reproche à `/health` — juste sous un nouveau nom d'endpoint.

Décision : `/health/ready` réutilise `_check_redis()` tel quel, sans
introduire de notion de dépendance « requise » distincte — parce
qu'il n'y en a structurellement qu'une dans cette app, et qu'elle porte déjà
sa propre distinction configuré/non-configuré. Conséquence assumée et
documentée dans le docstring de la route : `/health/ready` a AUJOURD'HUI la
même forme pass/fail que `/health` (un seul check, optionnel). La valeur
ajoutée n'est pas comportementale tout de suite, elle est sémantique — un
orchestrateur qui sait lire la distinction liveness/readiness peut cesser de
router du trafic vers une instance dégradée sans la tuer, ce que `/health`
seul (conflaté avec la liveness) ne peut pas exprimer. `/health/live` n'a
lui-même AUCUN check — vérifié en direct que couper Redis (REDIS_URL pointé
vers un hôte injoignable) laisse `/health/live` inchangé (200 `ok`) pendant
que `/health` et `/health/ready` passent à 503.

### 4. `/metrics` non authentifié — vrai risque ou bruit générique ?

Avant d'ajouter une garde : `.github/workflows/dast.yml` (ZAP baseline,
Lot 9/EXP-010) couvre-t-il déjà ça ? Relu le workflow — il cible
`http://localhost:4434/api/v2/docs` (l'entrée Swagger UI) avec le spider
TRADITIONNEL (pas de navigateur headless, cf. EXP-010), qui ne suit que les
liens HTML bruts (`<script src>`, `<link href>`) de la page rendue.
`/api/v2/metrics` n'est référencé nulle part dans le HTML de Swagger UI —
sa présence dans `openapi.json` n'est pas un lien HTML que ce spider suit.
**Déduit de EXP-010, pas revérifié par un nouveau scan dans cette session** :
EXP-010 documente déjà, chiffres à l'appui, que le spider traditionnel contre
`/api/v2/docs` découvre 7 URLs (Swagger UI + ses ressources statiques) sans
jamais exécuter de JS — `openapi.json` lui-même n'y figure pas comme une des
URLs visitées listées dans ce rapport-là. Un nouveau scan ZAP dédié à
`/api/v2/metrics` n'a pas été relancé ici (ça aurait dupliqué EXP-010 pour
confirmer un raisonnement déjà appuyé sur des chiffres réels) ; si ce
raisonnement s'avère faux à la prochaine exécution réelle de `dast.yml`
(nightly ou push:develop), ce sera visible dans son rapport d'artefact comme
pour toute autre route. Donc : chevauchement avec le Lot 9 jugé nul par
déduction documentée, pas par une nouvelle mesure — la garde ajoutée ici
reste la seule vérification connue pour couvrir ce chemin.

Sur le risque lui-même : cette app n'a ni PII ni secrets (`fly.toml`:
« Stateless... no secrets required »), et n'a d'authentification nulle part
ailleurs dans l'API — un `/metrics` ouvert ne crée donc pas une gravité
nouvelle par rapport au reste de la surface déjà publique (docs Swagger,
OpenAPI schema, toutes les routes de simulation). Mais ce n'est pas non plus
un risque nul : un visiteur peut voir en direct le volume de requêtes par
route, les taux d'erreur, et déduire des motifs d'usage — de l'information
qu'un déploiement pédagogique public n'a pas de raison de distribuer
gratuitement à qui tape l'URL. Résolu par le même principe que Redis dans
cette app : optionnel, dégradant vers « ouvert » par défaut.
`METRICS_AUTH_TOKEN` non configuré (`.env.example`, défaut local/dev) →
`/metrics` reste accessible sans en-tête ; configuré → `Authorization: Bearer
<token>` requis, vérifié avec les trois cas (absent, faux, correct) contre un
vrai serveur lancé en local.

### 5. Deux trouvailles réelles, pas fabriquées

**Contrat OpenAPI cassé, trouvé par le gate existant du Lot 3, pas par une
relecture manuelle.** `test_schema_contract.py` (Schemathesis) a immédiatement
échoué sur la première version câblée :

```
Undocumented Content-Type
Received:   text/plain; version=1.0.0; charset=utf-8
Documented: application/json
```

Cause : le handler que `Instrumentator.expose()` enregistre retourne un objet
`Response` Starlette construit à la main (le texte d'exposition Prometheus),
en court-circuitant l'inférence habituelle de FastAPI par `response_model` —
FastAPI documente alors `application/json` par défaut, sans rapport avec ce
que la route renvoie réellement. Corrigé en forwardant un `responses={200:
{"content": {CONTENT_TYPE_LATEST: ...}}}` à travers les `**kwargs` que
`.expose()` transmet à `app.get(...)` — `CONTENT_TYPE_LATEST` importé
directement de `prometheus_client` (pas recopié en dur), pour que la doc et
le comportement réel restent synchronisés même si la bibliothèque change ce
format de version un jour. Revérifié vert après correction.

**Nouvelle dépendance de production rejetée par
`scripts/check_license_compliance.sh`, trouvé en le rejouant pour de vrai,
pas en lisant seulement le champ licence sur PyPI.**
`prometheus-fastapi-instrumentator` porte `License: ISC` et sa dépendance
`prometheus_client` porte `License-Expression: Apache-2.0 AND BSD-2-Clause`
(confirmé via `pip-licenses` dans un venv réel, pas seulement lu sur PyPI) —
ni l'une ni l'autre chaîne exacte n'était dans l'`--allow-only` existant de ce
script (qui liste des formes MIT/BSD/Apache/MPL/PSF explicites, faute de
normalisation SPSX-vs-texte-classifieur par `pip-licenses`). Les deux
ajoutées à la liste après vérification que ISC est une licence permissive
approuvée OSI (fonctionnellement équivalente à MIT/BSD à deux clauses — texte
de la licence lu, pas seulement son nom) et qu'`Apache-2.0 AND BSD-2-Clause`
n'est qu'une combinaison des deux licences déjà individuellement acceptées
ailleurs dans ce même fichier. Rejoué le script en entier (venv isolé neuf,
comme le fait la CI) après correction : passe.

### 6. Vérifié en direct, pas seulement lu dans le code

- Serveur réel lancé (`uvicorn api.main:app`), `curl /api/v2/metrics` avant
  et après avoir tapé d'autres routes : `http_requests_total{handler="/api/v2/health"...}`
  passe de `1.0` à `3.0` après deux appels supplémentaires à `/health` — les
  compteurs bougent vraiment, pas juste « l'endpoint existe ».
  `/api/v2/metrics` lui-même n'apparaît jamais dans ses propres compteurs
  (`excluded_handlers`).
- `/api/v2/health`, `/api/v2/health/live`, `/api/v2/health/ready` : les
  trois interrogés en conditions normales (Redis non configuré) — les trois
  200.
- Scénario de panne réel simulé, pas halluciné : `REDIS_URL` pointé vers une
  IP privée injoignable (`10.255.255.1:6399`, timeout de connexion réel
  observé, ~5s) — `/health` et `/health/ready` passent à 503 avec
  `{"ok": false, "error": "unreachable"}`, `/health/live` reste 200
  `{"status": "ok"}` sans latence ajoutée. La séparation fait exactement ce
  qu'elle est censée faire.
- Garde d'authentification testée contre un vrai serveur avec
  `METRICS_AUTH_TOKEN` positionné : sans en-tête → 401, mauvais jeton → 401,
  bon jeton → 200 ; les autres routes restent inchangées (l'en-tête n'affecte
  que `/metrics`).

## Ce que ça a trouvé

Deux trouvailles réelles avant même la mise en service (voir §5) : un
contrat OpenAPI faux sur `/metrics` (Content-Type non documenté, capturé par
le Schemathesis du Lot 3) et une dépendance de production qu'un gate déjà
existant (Lot 6.7) aurait bloquée sans le correctif d'allow-list. Aucune des
deux n'aurait été visible en lisant seulement la documentation de la
bibliothèque — les deux sont sorties en faisant réellement tourner les gates
de ce dépôt contre le nouveau code, pas en les lisant.

Sur le fond de l'item lui-même : la vraie substance n'était pas
`/metrics` (la bibliothèque fait le travail, correctement vérifiée
maintenue) mais `/health/ready` — et la conclusion honnête est que cette app
n'a, aujourd'hui, qu'UNE seule dépendance vérifiable et qu'elle est
optionnelle par conception. `/health/ready` n'introduit donc pas un nouveau
mode d'échec, il rend explicite une distinction (configuré-et-cassé vs.
non-configuré) que `_check_redis()` portait déjà silencieusement.

## Ce que ça a coûté

~2h30 : ~40 min de vérification de maintenance des deux bibliothèques
(`gh api`, PyPI, lecture du code source d'`Instrumentator.expose()` pour
confirmer le mécanisme de `dependencies=`/`responses=` avant de l'utiliser) ;
~30 min d'écriture des routes + du câblage ; ~40 min pour les deux cycles
trouvaille→correction→revérification (contrat OpenAPI, licences) ; ~40 min de
vérification en direct (serveur réel, scénario Redis cassé, garde d'auth).
Une nouvelle dépendance de production (`prometheus-fastapi-instrumentator`,
qui tire `prometheus_client`), deux entrées ajoutées à l'allow-list de
licences, zéro nouvelle dépendance de dev.

## Verdict et pourquoi

**Adopté**, sans réserve majeure :

1. La bibliothèque fait ce que l'item décrit, vérifiée maintenue plutôt que
   supposée sur son nom — même discipline que EXP-004/EXP-008/EXP-009/EXP-011.
2. Le vrai risque de conception (confondre readiness générique et le design
   dégradant-gracieusement déjà en place pour Redis) a été pensé AVANT
   d'écrire le code, pas découvert après — l'item le demandait explicitement
   et la réponse honnête est que cette app n'a pas la topologie de
   dépendances pour laquelle le pattern readiness générique a été inventé.
3. Additif et vérifié sans surprise sur `fly.toml` : la route de production
   existante n'a pas bougé, testée intacte.
4. Les deux trouvailles réelles (contrat, licences) sont sorties de gates
   déjà en place dans ce dépôt, pas de vérifications ad hoc inventées pour
   cet item — la preuve que ces gates font leur travail sur du code neuf, pas
   seulement sur le code déjà en place au moment où ils ont été écrits.

## Ce que j'en retiens (transférable à un autre projet)

1. **Un pattern d'infrastructure « standard » (liveness/readiness k8s) ne se
   copie pas tel quel — il se réévalue contre la vraie topologie de
   dépendances de l'app.** Cette app a une dépendance, optionnelle, qui
   dégrade déjà gracieusement ; imposer le pattern générique (readiness
   échoue si une dépendance ne répond pas) aurait recréé le problème que
   l'item demandait de corriger, sous un nouveau nom de route.
2. **Un wrapper qui construit sa propre `Response` au lieu de passer par
   `response_model` casse silencieusement la documentation OpenAPI d'un
   framework qui, normalement, l'infère automatiquement** — un angle mort
   qu'un gate de contrat (Schemathesis, ici) rattrape bien mieux qu'une
   relecture, parce que le symptôme (mauvais Content-Type documenté) n'a
   aucune raison visuelle de sauter aux yeux dans le code source lui-même.
3. **Un gate de conformité de licences déjà en place doit être rejoué contre
   CHAQUE nouvelle dépendance, jamais supposé passant** — la même discipline
   que Lot 6.7 avait déjà établie, confirmée utile une seconde fois ici sur
   une dépendance qui n'avait à première vue rien d'exotique (deux licences
   permissives standard, juste sous une graphie que l'allow-list existante
   ne couvrait pas encore).
4. **Vérifier qu'un scanner DAST déjà en place couvre — ou pas — un nouvel
   endpoint avant d'ajouter sa propre garde évite de dupliquer un contrôle
   ou, pire, de croire à tort qu'un endpoint est déjà couvert.** Ici, relire
   le protocole déjà documenté (EXP-010) suffisait à établir que le spider
   traditionnel ne suit pas de lien HTML vers `/metrics` — sans relancer de
   scan pour cet item précis, donc une déduction documentée plutôt qu'une
   nouvelle mesure, mais pas une pure supposition non plus. La garde ajoutée
   ici n'est donc, en l'état des vérifications disponibles, ni redondante ni
   superflue.
