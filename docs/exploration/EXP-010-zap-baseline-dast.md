# EXP-010 — OWASP ZAP baseline : le SAST ne voit jamais les headers HTTP réels — mais le spider « moderne » peut bloquer indéfiniment

- **Date** : 2026-09-11 · **Statut** : adopté (gate CI non-bloquant, job dédié, nightly + push:develop) · **Coût réel** : ~3h30 (recherche du bon mode ZAP, mesures directes sur l'app réellement démarrée, un piège opérationnel trouvé et contourné, cycle complet d'injection/détection/retrait vérifié trois fois)
- **Verdict en une phrase** : sur une app qui n'envoie aujourd'hui **aucun** header de sécurité HTTP (vérifié par `curl -I` avant d'écrire le moindre test), un scan `zap-baseline.py` passif de ~30 s par cible (frontend build+preview réel, backend direct) trouve 9 alertes réelles de chaque côté sans jamais avoir besoin du mode actif que ce plan exclut explicitement — mais le spider « moderne » à base de navigateur headless (`-j`) a bloqué indéfiniment (~59 min, tué à la main) sur cette SPA, un vrai piège opérationnel trouvé en le faisant échouer, pas supposé, qui a changé la conception du job.

## Hypothèse de départ

Lot 9 du plan pose le problème sans présumer de la solution : Semgrep,
CodeQL, Trivy (tout `audit.yml`) ne lisent que le code source — aucun ne
regarde jamais une réponse HTTP réelle. Un header de sécurité manquant, une
CSP absente, un cookie mal configuré sont invisibles à tous les scanners
déjà en place. Trois questions à trancher avant d'écrire la moindre ligne de
CI : (1) cibler le frontend, le backend, ou les deux ; (2) l'action GitHub
officielle `zaproxy/action-baseline` est-elle toujours maintenue et le bon
outil, ou son cousin piloté par OpenAPI (`zap-api-scan.py`, et
`openapi.gen.json` existe déjà) est-il en fait plus adapté à une API pure ;
(3) le scan a-t-il vraiment des dents — trouve-t-il quelque chose de réel,
prouvé en l'injectant puis en le retirant, pas juste un rapport vert non
vérifié.

## Protocole

### 1. Choisir le mode ZAP — vérifié, pas supposé

Avant d'installer quoi que ce soit : lu le `--help` réel de `zap-baseline.py`
(`docker run --rm ghcr.io/zaproxy/zaproxy:stable zap-baseline.py --help`,
pas la doc de mémoire) et la doc zaproxy.org des deux scripts. Confirmé :
`zap-baseline.py` (mode « baseline ») lance un spider puis attend la fin du
scan **passif** — « the script doesn't perform any actual "attacks" ».
`zap-api-scan.py`, lui, « imports the definition [OpenAPI/SOAP/GraphQL]…
and then runs an Active Scan against the URLs found » et ses règles
« attempt exploitation » (injection SQL, etc.) — un mode qui a plus de sens
pour une API pure en théorie (import du schéma au lieu d'un spider HTML) mais
qui est structurellement le mode agressif que cet item du plan exclut
explicitement (« pas le "full scan" », et l'API scan a la même philosophie
d'attaque active, juste scopée à l'API plutôt qu'au HTML). Écarté sans
l'essayer, même réflexe que Lost Pixel/`license-checker` — pas une question
d'outillage mais de posture (`baseline` = ce que l'item demande).

Statut de maintenance de `zaproxy/action-baseline` vérifié avant adoption :
dernier commit sur `master` daté du 06/09/2026 (5 jours avant cette
session), dependabot mergé activement (`bump @babel/core`, `bump js-yaml`),
362 étoiles. Dernier tag publié : `v0.15.0` (24/10/2025), SHA du tag
`de8ad967d3548d44ef623df22cf95c3b0baf8b25` — épinglé à ce SHA exact, même
convention que chaque autre action tierce de ce dépôt (`# v0.15.0` en
commentaire).

### 2. Décider la cible — mesuré en direct, pas supposé

L'app a deux surfaces réelles : le SPA React (`voter-app`) et l'API REST
(`fast_api_voter`, 95 endpoints dans `openapi.gen.json`). Hypothèse initiale :
scanner seulement le frontend suffit, le spider découvrira l'API par
ricochet en observant les appels XHR du SPA. Vérifiée fausse en direct :
backend démarré (`uvicorn`, port dédié) et frontend construit+servi
(`npm run build && vite preview` — même commande que le job
`visual-regression`, pas le serveur de dev, pour scanner ce qu'un vrai
déploiement envoie), scan lancé contre le frontend seul — **zéro requête
backend** dans les logs d'accès JSON structurés du backend pendant tout le
run. Cohérent avec `EXP-004` : la plupart des pages de l'app ne font aucun
appel réseau au montage, et le spider traditionnel (voir piège ci-dessous)
n'exécute pas le JS qui déclencherait une navigation applicative vers
`/playground`. Décision : scanner **les deux cibles séparément** dans le même
job — frontend (`http://localhost:3000/`) et backend directement
(`http://localhost:4434/api/v2/docs`, l'entrée Swagger UI) — couverture
déterministe du backend au lieu d'espérer une découverte indirecte.

### 3. Le piège réel : le spider « moderne » bloque indéfiniment

`-j` (spider moderne, navigateur Selenium/Firefox headless réel par défaut
depuis la version testée) lancé contre le frontend avec un budget `-m 3`
(3 min). Log ZAP (`/home/zap/.ZAP/zap.log` dans le conteneur) : le spider
traditionnel termine en 61 ms (aucune découverte, cohérent avec un SPA sans
JS exécuté), puis le spider client démarre à 18:06:15, essaie de naviguer
vers `http://localhost:5173/`, et à 18:09:21 (~3 min 06 s, juste après le
budget `-m 3`) lève une `org.openqa.selenium.TimeoutException` côté
Selenium/Firefox — non récupérée. Le conteneur reste ensuite **vivant mais
inerte** (CPU 0,11 % mesuré via `docker stats`, 13 process `firefox-esr`
zombie) pendant **59 minutes** avant d'être tué à la main
(`docker kill` ; `time` confirme `59:04.17 total`). Pas une lenteur, un vrai
blocage : aucune activité process après l'exception, aucun rapport jamais
généré.

Décision : **retirer `-j` entièrement**, pas juste réduire son budget —
le budget `-m` n'a pas empêché le blocage, seulement retardé le moment où
Selenium a levé son exception non récupérée. Rejoué sans `-j` :
**28,6 s**, 25 URLs découvertes (tous les `<script src>`/`<link href>`
référencés en dur dans le HTML brut de `index.html` — chunks JS, CSS,
`sitemap.xml`, `robots.txt`, icônes PWA), 58 PASS, 9 WARN-NEW, exit 0. Le
spider traditionnel n'exécute aucun JS mais reste utile : il parse déjà le
HTML/CSS pour les ressources référencées, pas seulement les `<a href>`.
Contre le backend (`/api/v2/docs`, une page Swagger UI qui est elle-même une
mini-SPA), même choix (pas de `-j`) par cohérence et prudence — non retesté
séparément, le mécanisme sous-jacent (le même addon client-spider) étant
identique.

### 4. Vérifier le détecteur — injection, détection, retrait, trois fois

`curl -I` sur le backend et le frontend **avant tout changement de code** :
aucun des deux n'envoie `X-Content-Type-Options`, `Content-Security-Policy`,
`X-Frame-Options` ni `Referrer-Policy` — zéro header de sécurité, un vrai
état, pas une hypothèse. Scan baseline (backend, `/api/v2/docs`) sur cet état
réel : **WARN-NEW: 9, PASS: 58**, incluant
`X-Content-Type-Options Header Missing [10021] x 2`.

Correctif minimal ajouté (`fast_api_voter/api/main.py`, un middleware d'une
ligne, `response.headers["X-Content-Type-Options"] = "nosniff"` — même style
que les deux middlewares déjà présents dans ce fichier) :

```
AVANT (aucun header)     → WARN-NEW: 9, PASS: 58 (X-Content-Type-Options présent dans les WARN)
APRÈS (middleware actif) → WARN-NEW: 8, PASS: 59 (X-Content-Type-Options absent des WARN)
```

Retiré à nouveau (ligne commentée, backend redémarré) pour prouver que la
disparition n'était pas un artefact de run-à-run :

```
RE-CASSÉ (middleware commenté) → WARN-NEW: 9, PASS: 58 (X-Content-Type-Options réapparu, identique au premier run)
```

Middleware restauré comme état final commité. Cycle complet
détection → correction → confirmation → retrait → re-détection → retour au
vert, chacune des trois exécutions ~27-29 s, aucune autre alerte n'a bougé
d'un run à l'autre (seul `X-Content-Type-Options` apparaît/disparaît) —
signal propre, pas de bruit entre les runs.

### 5. Vérification de bout en bout du YAML réel

`zaproxy/action-baseline`'s `index.js` (lu directement depuis GitHub, pas
supposé) construit exactement :
`docker run -v $GITHUB_WORKSPACE:/zap/wrk/:rw --network="host" -t <image>
zap-baseline.py -t <target> -J report_json.json -w report_md.md
-r report_html.html <cmd_options>` — noms de fichiers **fixes**, pas
namespacés par cible. Rejoué cette commande exacte (deux fois, une cible
différente à chaque fois, un répertoire de travail simulant
`$GITHUB_WORKSPACE`) pour confirmer que la logique du job (déplacer
`report_json.json` avant le deuxième scan, sinon le second écrase le
premier avant que le step summary ne le lise) fonctionne réellement — piège
trouvé en lisant le code source de l'action avant d'écrire le YAML, pas
après un run CI raté. Le step de résumé (`jq` sur les deux JSON) rejoué en
local avec les deux vrais rapports donne exactement la sortie attendue :
9 alertes frontend listées (avec risque/nom/nombre), 8 alertes backend
(sans `X-Content-Type-Options`, la preuve du correctif dans les données
mêmes que verrait un lecteur du step summary).

## Ce que ça a trouvé

- **9 alertes réelles côté frontend**, **8 côté backend** (après le
  correctif), toutes de vrais WARN, zéro FAIL, zéro faux positif observé
  sur 6 runs consécutifs : `Content Security Policy (CSP) Header Not Set`,
  `Missing Anti-clickjacking Header`, `Permissions Policy Header Not Set`,
  `Cross-Origin-Resource-Policy`/`Cross-Origin-Embedder-Policy Header
  Missing`, `Sub Resource Integrity Attribute Missing`, `Timestamp
  Disclosure - Unix` (un timestamp Unix trouvé en dur dans un bundle JS),
  `Modern Web Application`/`Storable but Non-Cacheable Content`
  (informationnels). Aucun n'existait dans la conscience de l'équipe avant
  ce scan — invisibles à Semgrep/CodeQL par construction (ce sont des
  propriétés de la réponse HTTP, pas du code source).
- **Le spider moderne (`-j`) bloque indéfiniment sur cette SPA** — pas un
  cas limite hypothétique, reproduit une fois en conditions réelles
  (59 min, CPU à 0 %, aucune récupération automatique). Un futur ajout de
  scan ZAP sur ce dépôt devrait éviter `-j` par défaut, pas le redécouvrir à
  chaque fois.
- **Un seul correctif réel expédié** (`X-Content-Type-Options: nosniff`,
  backend) — délibérément le seul, pour garder le changement de code
  revuable comme la bascule de vérification du scanner, pas comme un
  chantier de durcissement complet des headers (qui toucherait CSP —
  risque réel de casser Tailwind/le service worker/RegimeGlobe sans le
  temps de vérifier composant par composant, hors du périmètre « câbler le
  DAST »).

## Ce que ça a coûté

~3h30 : ~45 min de recherche (aide `zap-baseline.py`, doc `zap-api-scan.py`,
statut de maintenance de l'action, lecture du `index.js` source) ; ~45 min à
démarrer les deux serveurs en local et mesurer les temps réels de scan ;
~1h à diagnostiquer le blocage du spider moderne (le laisser tourner pour
confirmer que ce n'était pas juste lent, `docker stats`/`docker exec ps`
pour comprendre l'état, puis le tuer et revalider sans `-j`) ; ~1h à
construire+vérifier le cycle complet d'injection/détection/retrait (trois
runs ZAP, plus le rejeu exact de la commande `docker run` de l'action pour
valider la logique de résumé du YAML). Une nouvelle image Docker
(`ghcr.io/zaproxy/zaproxy:stable`, ~800 Mo, tirée une fois) ; zéro nouvelle
dépendance Python/Node de production ou de dev.

## Verdict et pourquoi

**Adopté, job CI dédié non-bloquant** (`.github/workflows/dast.yml`),
`fail_action: false`. Trois raisons concrètes :

1. **Les findings sont réels et jamais vus par aucun scanner existant** —
   même argument que chaque scanner de ce plan, mais ici la catégorie
   entière (comportement HTTP réel) était un angle mort total avant cet
   item, pas une amélioration marginale d'un angle déjà couvert.
2. **Non-gating est le bon choix pour une app qui a une vraie dépendance à
   un serveur démarré** — un mode de panne (port pris, démarrage lent, pull
   d'image) qu'aucun autre scanner de sécurité de ce dépôt n'a. Bloquer les
   PR là-dessus avant d'avoir vu tourner le job en vrai sur GitHub Actions
   serait le même risque que `visual-regression` a documenté pour son
   propre `container:` (EXP-004) — appliqué ici à un mécanisme different
   (docker-outside-of-docker sur un runner nu) mais avec la même prudence.
3. **Le détecteur a des dents, prouvées trois fois, pas une** — même bar que
   EXP-004/EXP-006 : un cycle complet cassé→détecté→corrigé→confirmé
   vert→re-cassé→re-détecté→re-corrigé, avec des chiffres identiques aux
   deux extrémités (WARN-NEW 9↔8, PASS 58↔59), sur trois exécutions
   indépendantes.

## Ce que j'en retiens (transférable à un autre projet)

1. **« Baseline » et « API scan » ne sont pas deux profondeurs du même mode
   — ce sont deux postures différentes (passif vs actif) qui se recoupent
   juste sur le vocabulaire « API ».** Un `openapi.gen.json` déjà présent
   est une tentation forte de croire que le mode piloté par schéma est
   automatiquement le bon choix « parce que plus exhaustif » — vérifier la
   doc plutôt que le supposer a évité d'introduire un scan actif sous couvert
   d'un item qui demandait explicitement un scan passif.
2. **Un scanner « intelligent » (navigateur headless réel) n'est pas
   gratuit — il peut échouer d'une façon qu'un spider plus bête (parsing
   HTML statique) ne peut structurellement pas : bloquer indéfiniment plutôt
   que rendre un résultat partiel.** Le laisser tourner jusqu'à la certitude
   du blocage (plutôt que de le tuer après 5 minutes d'impatience et
   supposer) a transformé une intuition (« ça a l'air lent ») en un fait
   vérifié (« ça ne terminera jamais seul ») qui justifie vraiment de retirer
   la fonctionnalité plutôt que d'augmenter un timeout.
3. **Un spider HTML statique sur une SPA n'est pas aussi aveugle qu'il y
   paraît** — 25 URLs réelles découvertes sans exécuter une ligne de JS,
   parce qu'une SPA moderne référence quand même ses propres ressources en
   HTML brut (bundler oblige). Le renoncement au spider JS n'est donc pas un
   renoncement total à la couverture, juste à la découverte des routes
   *applicatives* (navigation React Router) — un compromis mesuré, pas
   supposé équivalent à zéro couverture.
4. **Lire le code source d'une action tierce avant d'écrire le YAML qui
   l'appelle** (ici : les noms de fichiers de rapport fixes, non namespacés)
   a évité un piège qui ne se serait révélé qu'au deuxième `uses:` du même
   job en CI — plus cher à diagnostiquer à distance qu'à lire 80 lignes de
   JS en amont.
