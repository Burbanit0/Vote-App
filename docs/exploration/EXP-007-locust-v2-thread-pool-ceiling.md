# EXP-007 — Locust : quel est le *vrai* plafond du pool de threads que le rate-limit 120/min a deviné ?

- **Date** : 2026-09-11 · **Statut** : adopté (script manuel, pas de gate CI) · **Coût réel** : ~4h (lecture du code de dispatch avant tout test, chronométrage direct des workers, un piège d'environnement trouvé et corrigé en cours de route, quatre paliers de charge réels, écriture)
- **Verdict en une phrase** : le pool partagé de 4 workers CPU-bound (`api/core/worker_dispatch.py`) sature bien avant le rate-limit `120/min` dès qu'un endpoint fait un calcul non-trivial — à 8 utilisateurs Monte-Carlo concurrents (charge plausible, aucun endpoint individuel ne dépassant jamais SON PROPRE rate-limit), la latence médiane est passée de 3,0 s à 7,2 s à 13-14 s à 25-30 s en doublant la concurrence à chaque palier, **zéro 429/503 sur toute la plage testée** — le premier symptôme visible d'une vraie surcharge ici n'est pas une erreur, c'est une page qui semble juste geler.

## Hypothèse de départ

`PLAN_SOLIDITE_TECHNIQUE.md` (Lot 8.2) pose la question précisément : pas
« l'API survit-elle à la charge » dans l'abstrait, mais « le rate-limit
120/min a été calibré au jugé (contre un flake e2e, cf. le docstring de
`check_v2_rate_limit`) — quel est le VRAI plafond du pool de threads contre
lequel il a été deviné ? ». Hypothèse de départ, à vérifier avant d'écrire
le moindre scénario de charge : les endpoints `/api/v2` sont-ils vraiment
servis par un pool de threads nu (l'exécuteur par défaut, `min(32, cpu+4)`),
et le rate-limit est-il vraiment ce qui le protège ?

## Protocole

### 1. Lire le code avant de charger quoi que ce soit

`api/core/worker_dispatch.py` (Lot 3 de ce même plan, déjà en place) répond
à la moitié de la question sans qu'il soit nécessaire de charger quoi que ce
soit : chaque route `/api/v2` est `async def`, mais délègue son calcul
CPU-bound via `asyncio.to_thread` **derrière un sémaphore partagé unique**
(`asyncio.Semaphore(4)`, `MAX_CONCURRENT_WORKERS = 4`) — pas l'exécuteur par
défaut. Ce sémaphore est **global au process** : un Monte-Carlo lourd et un
`profile-simulate` léger se disputent les 4 mêmes places. Le rate-limit
(`api/core/ratelimit.py`, `check_v2_rate_limit`, 120/minute) est, lui,
**par chemin** (`key_style="url"`) et par IP (`get_remote_address`) — chaque
route a son propre compteur indépendant. C'est cette asymétrie — un sémaphore
partagé contre un rate-limit cloisonné — qui rend la question du plan
intéressante : un endpoint qui reste sagement sous SA PROPRE limite peut,
ensemble avec un autre chemin, saturer le pool partagé sans qu'aucun des
deux rate-limits individuels ne s'en aperçoive.

`grep -n "check_v2_rate_limit\|@limiter.limit" api/routes/*.py` confirme la
valeur documentée : 120/min sur tous les routers v2 (`election`,
`simulations`, `tech`, `theory`, `export`), 10/min sur `/simulate` et
5/min sur `/compare` côté v1 public (`api/routes/public.py`) — la
distinction déjà documentée par `ratelimit.py` (v1 historique bas ; v2
120/min pour absorber le trafic débouncé du Playground) reste exacte,
vérifiée directement plutôt que recopiée du plan.

### 2. Chronométrer les workers directement, hors HTTP, avant de choisir un outil de charge

Avant d'écrire le moindre scénario Locust, appel direct des fonctions
worker (`_profile_simulate_worker`, `_monte_carlo_worker`) :

| Endpoint | Config | Temps mesuré |
|---|---|---|
| `profile-simulate` | défaut (300 électeurs, 3 candidats) | ~13 ms |
| `profile-simulate` | plafond production (1000 électeurs, 8 candidats) | ~125 ms |
| `monte-carlo` | défaut (100 runs, 150 électeurs) | ~1,0 s |

Au plafond du sémaphore (4 slots), le débit théorique isolé de
`profile-simulate` est ~4/0,125 s ≈ 32 req/s (≈1900/min, 16x le rate-limit)
— la question du plan ne se pose quasiment pas pour cet endpoint SEUL. Pour
`monte-carlo`, le débit isolé théorique est ~4/1 s = 4 req/s (240/min) — déjà
proche du double de SA PROPRE limite (120/min), ce qui suggérait que le
rate-limit serait la contrainte la plus stricte pour cet endpoint pris
isolément. Vérifié empiriquement ci-dessous — et l'intuition initiale sur
`profile-simulate` seul s'est confirmée, mais pas de la façon prévue (voir
§ « Ce que ça a trouvé »).

### 3. Choisir l'outil : Locust, pas k6

Le backend est un projet Python de bout en bout (`fast_api_voter/`) sans
aucun autre outillage JS côté serveur — Locust (Python, `requirements-dev.txt`)
s'installe et s'écrit dans le même venv que le reste des dépendances de dev,
sans nouveau langage ni toolchain. k6 (JS/Go) aurait été un choix
défendable (le frontend a déjà un toolchain JS, donc ce n'est pas un vrai
obstacle) mais aurait introduit un binaire externe distinct de tout ce que
`requirements-dev.txt` documente déjà — pour aucun bénéfice net sur ce
projet précis. Locust retenu.

### 4. Un piège d'environnement trouvé en cours de route — presque un doublon exact d'EXP-003

Premier jet : `uvicorn api.main:app --port 4434 &`, puis Locust dessus.
**Zéro 429 sur 130 requêtes** vers un endpoint dont le test du repo
(`test_ratelimit_v2.py`) prouve pourtant qu'il déclenche un 429 après 120
requêtes. Vérifié avant de conclure quoi que ce soit (même discipline
qu'EXP-003, § « contamination par un process tiers ») :

```
$ ps aux | grep uvicorn
10001   4557  ...  /usr/local/bin/python3.11 .../uvicorn api.main:app --host 0.0.0.0 --port 4434
```

`:4434` était déjà occupé par un process tiers (UID différent, Python 3.11
système, actif depuis avant cette session) — mon propre `uvicorn` avait
échoué à démarrer (« address already in use », noyé dans un fichier de log
jamais relu avant la première conclusion), et **toutes mes requêtes
frappaient ce process externe**, pas mon code. Exactement le même piège
qu'EXP-003 a déjà documenté sur ce même port, dans ce même repo — confirmé
en tuant mon process (qui n'existait pas, d'où l'échec du `kill`) et en
relançant sur un port dédié (`4436`), avec vérification directe (`curl`
+ log de démarrage) avant de faire confiance à quoi que ce soit. Toutes
les mesures citées plus bas viennent de cette seconde passe, vérifiée.

**Enseignement transférable immédiat** : un test qui « répond » n'est pas
une preuve qu'il répond depuis le bon process — surtout sur un port par
défaut documenté (donc un candidat naturel à collision dans un
environnement partagé). `CLAUDE.md`/`README.md` documentent `:4434` comme
port par défaut ; toute expérience future sur ce repo devrait soit changer
de port, soit vérifier le PID avant de faire confiance à une réponse HTTP.

### 5. Isoler le rate-limit du sémaphore — un deuxième correctif de méthode

Deuxième jet, sur le bon serveur : `ProfileSimulateUser` et `MonteCarloUser`
avec un `wait_time` quasi nul sur les deux. Résultat : **45 % d'échecs, 100 %
des échecs des 429** (rate-limit), zéro 503/timeout — la question posée
(le plafond du POOL DE THREADS) n'était pas celle mesurée (le plafond du
RATE-LIMIT, atteint bien avant). Corrigé en s'appuyant sur l'ordre réel
d'exécution confirmé en lisant le code (pas supposé) : `check_v2_rate_limit`
s'exécute comme dépendance FastAPI **avant** le corps de la route, qui
appelle `run_worker_bounded` (le sémaphore) — un utilisateur Locust en
boucle fermée ne peut envoyer sa requête suivante qu'une fois le
**round-trip complet** (check + attente sémaphore + calcul) terminé. Le
temps de service de plusieurs secondes de `monte-carlo` s'auto-limite donc
déjà bien sous 120/min, même à `wait_time=0` — contrairement à
`profile-simulate`, trop rapide pour s'auto-limiter (d'où un `wait_time`
explicite de 1 s sur cette classe, présente seulement comme trafic de fond
réaliste, pas pour chercher SON propre plafond). `MonteCarloUser` (poids 4,
`wait_time=0`) devient la classe qui génère la pression de concurrence
réelle.

### 6. Quatre paliers de charge réels, `-u` doublé à chaque fois

```bash
locust -f scripts/loadtest_v2_engine.py --headless -u N -r N/2 -t Ts \
    --host http://localhost:4436 --csv=/tmp/lt
```

## Ce que ça a trouvé

| `-u` (utilisateurs) | ~MonteCarloUsers concurrents | Médiane monte-carlo | Max | Échecs |
|---|---|---|---|---|
| 4 | ~3 | 3,0 s | 3,9 s | 0 |
| 10 | ~8 | 7,2 s | 9,6 s | 0 |
| 20 | ~16 | 14,0 s | 17,4 s | 0 |
| 40 | ~32 | 25-30 s | 33,0 s | 0 |

**Trois trouvailles, aucune devinée :**

1. **Le rate-limit par-chemin n'est pas ce qui protège le pool partagé.**
   Sur toute la plage testée (jusqu'à 32 utilisateurs Monte-Carlo
   concurrents), **zéro 429 et zéro 503** — le mécanisme censé borner
   l'abus (120/min par chemin) ne voit jamais rien d'anormal, parce
   qu'aucun chemin pris isolément ne dépasse jamais SA PROPRE limite (le
   débit agrégé mesuré plafonne lui-même à ~1,0-1,3 req/s, cohérent avec
   4 workers / ~3-4 s de temps de service moyen sous contention — bien en
   dessous de 120/min = 2 req/s). Le sémaphore sature en silence, sans
   qu'aucun garde-fou existant ne s'en aperçoive.
2. **Le premier symptôme visible d'une vraie surcharge est la latence, pas
   une erreur** — et elle croît de façon quasi-linéaire avec la
   concurrence au-delà de 4 requêtes simultanées (le comportement attendu
   d'une file d'attente bornée à N=4 serveurs) : chaque doublement de
   concurrence double presque la latence. À `-u 40`, un utilisateur du
   Playground attendrait ~30 secondes une réponse à une requête qui prend
   1 seconde isolément — sans le moindre message d'erreur, jusqu'au
   timeout de 180 s du sémaphore (`worker_dispatch.py`), jamais atteint
   dans cette expérience (il aurait fallu ~250 utilisateurs concurrents
   au rythme de croissance observé — hors budget de cette passe, et déjà
   hors de toute charge réaliste pour ce produit).
3. **L'intuition initiale du plan était la bonne, mais incomplète.**
   « 120/min a été deviné » est vrai — mais la vraie faille n'est pas que
   120/min soit trop haut ou trop bas pour un endpoint donné (il est même
   plutôt bien calé pour `profile-simulate` seul, avec 16x de marge) :
   c'est qu'un rate-limit par-chemin ne peut structurellement pas protéger
   une ressource partagée entre chemins. Aucun réglage du CHIFFRE 120
   n'aurait résolu ça — seule une limite qui connaît le sémaphore (ou le
   sémaphore lui-même, qui existe déjà) le peut.

## Ce que ça a coûté

~4h : ~45 min de lecture de code (`worker_dispatch.py`, `ratelimit.py`,
les routers v2) avant d'écrire quoi que ce soit ; ~30 min de chronométrage
direct des workers ; ~45 min à diagnostiquer et corriger le port déjà
occupé (quasi-doublon d'EXP-003, mais découvert indépendamment avant de se
souvenir du précédent) ; ~30 min à corriger le calibrage rate-limit vs
sémaphore (premier jet à 45 % d'échecs, tous des 429, pas le signal
cherché) ; ~1h30 des quatre paliers de charge réels + lecture des résultats.
Une nouvelle dépendance de dev (`locust==2.46.5`, qui tire Flask comme
dépendance interne de sa UI web — sans rapport avec l'app, qui a migré HORS
de Flask, cf. `CLAUDE.md`), zéro dépendance de production.

## Verdict et pourquoi

**Adopté comme script manuel, jamais un gate CI** — même raisonnement
qu'EXP-003 (couverture runtime), pour les mêmes deux raisons concrètes :

1. **Le coût est réel et le signal ne se dégrade pas entre deux
   exécutions.** Ce n'est pas une régression à surveiller commit après
   commit (rien dans le CODE n'a changé pendant cette expérience) — c'est
   une question de capacité à répondre une fois, puis à ressortir quand le
   produit change de forme (nouveaux endpoints lourds, changement du
   nombre de workers). Un job nightly n'ajouterait rien qu'une relecture
   ponctuelle de ce carnet ne donne déjà.
2. **Le chiffre trouvé est spécifique à CETTE machine.** La latence
   absolue (3 s à 4 utilisateurs, 30 s à 40) dépend directement de la
   vitesse CPU de la machine qui exécute `_monte_carlo_worker` — un runner
   GitHub Actions partagé donnerait des absolus différents. Le RATIO
   (latence ∝ concurrence/4, pas d'erreur avant ~250 utilisateurs) est le
   résultat transférable, pas les secondes précises — exactement le genre
   de nombre qu'un gate CI figerait à tort.

`scripts/loadtest_v2_engine.py` reste disponible, documenté dans
`CONTRIBUTING.md` (section « Charge »), à relancer à la demande après tout
changement touchant `MAX_CONCURRENT_WORKERS`, le nombre d'endpoints lourds,
ou avant une décision de dimensionnement de production.

## Ce que j'en retiens (transférable à un autre projet)

1. **Un rate-limit par-chemin/par-client ne protège JAMAIS une ressource
   VRAIMENT partagée** (un pool de threads, une connexion DB, un budget
   mémoire) — seule une limite qui connaît explicitement cette ressource
   (un sémaphore global, une queue bornée) le peut. C'est une propriété
   structurelle, pas un réglage : aucun chiffre de rate-limit, aussi bien
   calibré soit-il, n'aurait résolu ce que cette expérience a trouvé.
2. **Dans un système à sémaphore + timeout large, la latence dégrade
   BIEN AVANT les erreurs** — et un test de charge qui ne regarde que le
   taux d'erreur (« ça tient à N req/s ») rate complètement ce signal.
   « Pousser jusqu'à ce que quelque chose casse » doit inclure une latence
   devenue inacceptable, pas seulement un code d'erreur.
3. **Un port par défaut documenté, dans un environnement de dev partagé,
   est un candidat probable à collision silencieuse.** Ce précédent exact
   (process tiers sur `:4434`) s'est reproduit deux fois dans ce même repo
   (EXP-003, puis ici) sans lien entre les deux découvertes — assez
   systématique pour mériter une vérification réflexe (PID du process qui
   répond, pas seulement code HTTP) plutôt qu'une leçon à réapprendre une
   troisième fois.
4. **Calibrer un scénario de charge demande de comprendre l'ORDRE des
   mécanismes de protection existants**, pas seulement leurs valeurs
   individuelles — ici, le fait que le rate-limit s'exécute avant le
   sémaphore (et non l'inverse) est ce qui permet à un temps de service
   long de s'auto-limiter sous le rate-limit tout en stressant quand même
   le sémaphore. Un ordre inversé aurait changé toute l'expérience.
