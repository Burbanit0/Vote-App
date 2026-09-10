# PLAN — Solidité technique & exploration outillée

> Plan d'exécution auto-suffisant, écrit pour être repris étape par étape (par
> moi ou par un agent) sans contexte préalable. **Une branche `feat/*` + une PR
> par item**, contre `develop`, merge `--no-ff` — comme le mandate `CLAUDE.md`.
>
> **Date d'ouverture** : 2026-09-07
> **État de départ** : `develop` à `a5cb7ce`, tous les gates verts
> (`ci-local/run-ci.sh all` : Backend CI, Frontend CI, Playwright E2E, Security
> Audit — 1789 tests backend, 91 % de couverture, 0 vulnérabilité Trivy,
> 0 secret Gitleaks).

---

## Pourquoi ce plan existe

Vote-App poursuit deux explorations en parallèle, et ce plan sert les deux :

1. **Une exploration des méthodes de vote** — 26 méthodes en parité verrouillée
   entre deux implémentations, une théorie formelle documentée, un objectif
   pédagogique.
2. **Une exploration des technologies et pratiques de développement** — qu'est-ce
   qui tient vraiment la route sur un projet réel, qu'est-ce qui coûte plus
   qu'il ne rapporte, qu'est-ce qui trouve des bugs que rien d'autre ne trouve.

La seconde exploration n'a de valeur que si elle est **documentée honnêtement,
échecs compris**. Un outil essayé et rejeté avec une raison précise vaut autant
qu'un outil adopté — souvent plus, parce que personne ne publie ses rejets.

D'où le principe directeur de ce plan :

> **Chaque item est une expérience, pas une tâche.** Elle se termine par un
> verdict écrit (adopté / rejeté / suspendu) accompagné de ce qu'elle a
> réellement trouvé et de ce qu'elle a réellement coûté.

### Les deux axes de notation

Chaque item est noté sur deux axes indépendants, parce qu'ils ne se recouvrent
pas dans un projet exploratoire :

| Axe | Notation | Ce que ça mesure |
|---|---|---|
| **Solidité** | ⭐ à ⭐⭐⭐ | Ce que ça apporte à la robustesse réelle du code |
| **Récit** | 📝 à 📝📝📝 | La richesse de ce qu'il y aura à raconter à l'issue |

Un item ⭐📝📝📝 (peu solide, très racontable — ex. Z3) mérite d'être fait **ici**
alors qu'il ne le mériterait pas sur un projet purement produit. C'est
précisément ce qui distingue ce plan d'un plan de durcissement classique.

**Effort** : `S` (≤ 1 h) · `M` (une demi-journée) · `L` (1 jour ou plus).

---

## Lot 0 — Le dispositif de documentation *(à faire en premier)*

Ce lot passe avant tout le reste : c'est lui qui transforme les 11 lots suivants
en matière partageable au lieu d'une suite de commits. Le faire après, c'est
reconstituer de mémoire ce qu'on a trouvé — donc mal.

### 0.1 — Séparer les surfaces de documentation

Le repo a déjà plusieurs supports qui se chevauchent mal. À clarifier une fois
pour toutes, dans un court `docs/README.md` :

| Surface | Rôle | Rythme | Existe ? |
|---|---|---|---|
| `docs/journal/JOURNAL_DE_BORD.md` | Chronologie narrative, par session de travail | Par session | ✅ |
| `docs/exploration/EXP-*.md` | Par expérience/outil : verdict + enseignement transférable | Par expérience | ❌ à créer |
| `docs/adr/` | Décisions d'architecture engageantes, avec alternatives écartées | Rare | ✅ (polity seulement — à ouvrir à l'app) |
| `CODE_AUDIT.md` | État de santé daté du code, rejouable | Par passe de nettoyage | ✅ |
| `docs/journal/commits.jsonl` | Trace machine exhaustive, générée — archéologie et alimentation des autres surfaces | Par commit (auto) | ❌ à créer (§0.5) |
| Mémoire Claude polity | Écueils rechargés d'office à chaque session — le seul support qui empêche *réellement* la répétition | Par écueil rencontré | ✅ (manuel → à automatiser, §0.5) |

**Effort** S · Solidité ⭐ · Récit 📝📝

### 0.2 — Créer `docs/exploration/` avec son gabarit

Un fichier par expérience, gabarit fixe :

```markdown
# EXP-00X — <Outil> : <ce qu'on cherchait à savoir>

- **Date** · **Statut** : adopté | rejeté | suspendu · **Coût réel** : Xh
- **Verdict en une phrase** :

## Hypothèse de départ
Ce que j'espérais que ça trouve, avant de commencer.

## Protocole
Ce que j'ai fait exactement (commandes, config, périmètre).

## Ce que ça a trouvé
Les vraies trouvailles, avec des liens vers les commits/PR de correction.
Zéro trouvaille est un résultat valide et intéressant.

## Ce que ça a coûté
Temps d'installation, temps CI ajouté, faux positifs, charge de maintenance.

## Verdict et pourquoi
## Ce que j'en retiens (transférable à un autre projet)
```

La dernière section est la charge utile du partage : elle doit tenir debout
pour quelqu'un qui ne connaît pas Vote-App.

**Effort** S · Solidité ⭐ · Récit 📝📝📝

### 0.3 — L'index des verdicts

`docs/exploration/README.md` : un tableau `EXP | Outil | Domaine | Verdict |
Trouvailles réelles | Coût`. Mis à jour à chaque expérience close.

**C'est le livrable partageable du projet** : « j'ai essayé ~25 outils de qualité
sur un vrai projet, voilà lesquels ont trouvé quelque chose ». Ce tableau
n'existe nulle part ailleurs parce que personne ne tient le compte de ses rejets.

**Effort** S · Solidité ⭐ · Récit 📝📝📝

### 0.4 — Commande `/log-experiment` + agent `experiment-writer`

Sur le modèle exact de `/log-session` + `journal-writer` déjà en place : l'agent
lit le diff, les résultats d'outil et la conversation, puis rédige le carnet
d'expérience selon le gabarit, à valider avant application.

**Effort** M · Solidité ⭐ · Récit 📝📝

### 0.5 — Capture automatique par commit dans le worktree polity

**Origine** : `/log-session` + `journal-writer` ont d'abord été construits pour
résumer les expérimentations du worktree `Vote-App-polity`. L'objectif reste le
même, mais il n'est atteint qu'à moitié : le récapitulatif dépend de la
discipline de le lancer. Objectif visé : **chaque commit du worktree polity
alimente automatiquement une trace, pour ne pas refaire en boucle les mêmes
erreurs.**

#### Les contraintes réelles, vérifiées

| Fait | Conséquence de conception |
|---|---|
| **Les hooks git sont partagés entre worktrees** — depuis polity, `git rev-parse --git-path hooks` → `/home/burbanit0/Vote-App/.git/hooks` | Un `post-commit` **doit se garder** sur le worktree/la branche, sinon il se déclenche aussi sur les commits de `develop`. |
| **361 commits sur 30 jours** (~12/jour) | Un recap LLM par commit = ~360 entrées/mois. C'est le volume qui **tue** la relecture : le remède deviendrait le mal. |
| **La mémoire polity existe déjà** (~20 fichiers, namespace propre) et contient déjà des écueils (« awakening-gate landmine », « DuckDB `->>` precedence gotcha ») | Le mécanisme anti-boucle **existe** — il est alimenté à la main, et par lot. Le travail est de l'automatiser, pas de le réinventer. |
| Le worktree polity a **déjà des hooks Claude** `PreToolUse` (garde graphify) | Le pattern est connu et en service : on l'étend, on n'introduit pas un concept neuf. |

#### L'architecture en trois étages

La distinction structurante : **le log sert l'archéologie et le récit ; la
mémoire sert la non-répétition.** Un fichier de log qu'il faut penser à relire
n'empêche aucune boucle — la mémoire, elle, se recharge d'office à chaque
session. « Un recap par commit » mélange ces deux besoins ; les séparer les sert
tous les deux.

**Étage 1 — Capture exhaustive, par commit, sans LLM** · `M` · ⭐⭐⭐ 📝📝

Un `post-commit` gardé sur le worktree polity écrit une ligne dans un JSONL
append-only (`docs/journal/commits.jsonl`) : sha, date, branche, message,
fichiers touchés, stats, plus les signaux propres à polity (un fichier de
résultats d'acceptance a-t-il bougé ? un paramètre de config ?).

Coût nul, aucune latence, **jamais bloquant** (`|| true` systématique — un hook
ne doit jamais empêcher un commit). C'est la trace d'archéologie exhaustive,
celle qui permet de répondre à « quand ai-je touché ce paramètre, et
combien de fois ? ».

**Étage 2 — Récit par session/lot, avec LLM** · `S` · ⭐ 📝📝📝

`/log-session` existe déjà : il est simplement **alimenté par l'étage 1** au
lieu de reconstituer de mémoire. La granularité narrative reste la session ou le
lot — c'est déjà celle de la mémoire polity (`v5_lot1`, `v5_lot2`…), donc la
granularité naturelle du projet.

**Étage 3 — Mémoire d'écueils, alimentée automatiquement** · `M` · ⭐⭐⭐ 📝📝📝

**C'est l'étage qui sert réellement l'objectif anti-boucle.** Quand l'étage 1
détecte un signal d'échec, le pipeline propose une entrée dans le namespace
mémoire polity (`~/.claude/projects/-home-burbanit0-Vote-App-polity/memory/`) —
donc rechargée d'office à chaque session, sans effort de relecture.

Signaux détectables **sans LLM**, à partir du seul JSONL :

- un `revert`, ou un commit qui annule le précédent ;
- un message contenant `fix`/`revert`/`retry`/`workaround` ;
- **l'oscillation d'un paramètre** — même fichier de config modifié N fois en
  M jours : signature d'une recherche à tâtons, donc d'un écueil non compris ;
- un nouveau fichier de résultats d'acceptance : chaque run porte un verdict à
  capter ;
- **le signal le plus utile** : un commit qui touche un fichier déjà cité dans
  une mémoire d'écueil existante.

Ce dernier point justifie à lui seul le dispositif : un hook `PreToolUse` — sur
le modèle exact de la garde graphify déjà en service — peut **prévenir au moment
où tu touches une zone documentée comme piégeuse**, avant l'erreur, et non après.

#### Points d'implémentation à ne pas rater

- Garde de worktree obligatoire dans le `post-commit` (hooks partagés).
- Jamais bloquant, jamais d'appel réseau synchrone au commit.
- Enrichissement LLM **différé et par lot** (`/recap` traite les commits non
  encore résumés), jamais au fil du commit : pas d'appel LLM sur un « wip typo ».
- Répartition develop/polity conforme à la règle établie : le mécanisme
  générique (script, commande) sur `develop`, l'activation et les mémoires
  d'écueils côté polity.
- `commits.jsonl` est un artefact **généré** : jamais édité à la main.

### 0.6 — Ouvrir les ADR côté application

`docs/adr/` ne contient que des ADR polity. Les décisions structurantes de
l'app (le double moteur et sa parité, le choix SVG natif vs Recharts, l'archi
en 5 moments du Playground, le refus d'authentification) ne sont documentées
nulle part comme *décisions avec alternatives écartées*. Les écrire
rétroactivement — c'est de la reconstitution assumée, à signaler comme telle.

**Effort** M · Solidité ⭐⭐ · Récit 📝📝📝

---

## Lot 1 — Quick wins d'infrastructure

Effort minime, bénéfice immédiat, débloque le confort de tous les lots suivants.

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **Groupes Dependabot** (`groups:`) | `dependabot.yml` n'a aucun groupe → les 13 PR en cascade du 06/09 auraient été 2-3 PR. Cause racine identifiée, correctif de 20 min. | S | ⭐⭐⭐ | 📝📝 | ✅ PR #321 |
| **Merge queue** | Résout structurellement l'invalidation en cascade (« doit être à jour avec develop ») : la queue rebase et teste en série toute seule. | S | ⭐⭐⭐ | 📝📝 | ✅ **fait et vérifié en direct** (PR #338, mergée par `app/mergify` en 15s, 0 intervention manuelle). Native GitHub bloquée (réservée aux repos publics *organisation* — 422 confirmé) ; pivot Mergify (gratuit OSS). Effet de bord utile : drift réel trouvé et corrigé — `develop` n'avait que 5 checks requis sur les 12 documentés (`scripts/setup-branch-protection.sh`), restauré en direct. `strict` (« up to date ») désactivé sur `develop` — Mergify l'a lui-même signalé bloquant en direct (« Configuration not compatible with a branch protection setting ») avant de fonctionner ; `required_status_checks` reste injecté automatiquement, pas dupliqué dans `.mergify.yml` |
| **Ruff** (remplace flake8) | ~100× plus rapide, couvre flake8 + isort + pyupgrade + bugbear + une partie de bandit. Le meilleur ratio du plan. | S | ⭐⭐⭐ | 📝📝 | ✅ swap fidèle fait ; isort/pyupgrade/bugbear pas activés (scope creep — voir note du `[tool.ruff]`) |
| **`uv`** (remplace pip en CI) | Installation Python drastiquement plus rapide + lockfile reproductible (aujourd'hui `requirements.txt` épinglé à la main). | M | ⭐⭐ | 📝📝 | ✅ swap fidèle fait (5 workflows + 4 Dockerfiles, vérifié par build Docker réel de chacun) ; `requirements.txt` reste la source de vérité, pas de migration `uv.lock`/`pyproject` — la reproductibilité de lockfile reste à faire, scope creep écarté comme pour Ruff |
| **Cache CI** (npm / pip / couches Docker) | Boucle de feedback plus courte sur tous les lots suivants. | S | ⭐⭐ | 📝 | ✅ npm/pip déjà en place partout (vérifié) ; couches Docker ajoutées pour `image-scan` |
| **`diff-cover`** | Exiger 100 % de couverture *sur les lignes modifiées d'une PR* — bien plus mordant qu'un seuil global à 90 % qu'on atteint en diluant. | S | ⭐⭐⭐ | 📝📝 | ✅ Backend CI + Frontend CI, gate PR uniquement ; lcov (frontend) demande un préfixe de chemin (`voter-app/`) que Cobertura (backend) n'a pas besoin — testé en local dans les deux sens (ligne couverte/non couverte) avant push ; pas de mirroir `ci-local/` (pas de branche de base dans une image Docker) |
| **Codecov** | Commentaire de couverture par PR + tendance visible dans le temps. | S | ⭐ | 📝 | ✅ compte + `CODECOV_TOKEN` créés par l'utilisateur ; upload backend+frontend câblé, `codecov.yml` (informational: true des deux côtés — diff-cover reste le seul gate réel), validé via `codecov.io/validate` |
| **`act`** | Lancer les workflows GitHub en local, complète `ci-local/`. | S | ⭐ | 📝📝 | ✅ installé sans sudo, `.actrc` + `ci-local/act-pr-event.json` ajoutés, testé en vrai contre `openapi-contract.yml` (job non couvert par `ci-local/`) ; limites documentées (paths-filter interroge l'API GitHub, secrets absents, CodeQL/Scorecard non exécutables) |

---

## Lot 2 — Rendre les conventions exécutables

Le repo a beaucoup de règles **écrites** (`CLAUDE.md`, skills) que rien
n'applique. Ce lot les transforme en garde-fous. Angle de récit : *« combien de
mes conventions documentées étaient déjà violées sans que je le sache ? »* —
avec un chiffre réel à la clé.

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **`import-linter`** | La couche `route → domain → engine` du skill `voter-api` n'est qu'une convention. import-linter la rend bloquante. | M | ⭐⭐⭐ | 📝📝📝 | ✅ contrat `layers` dans `pyproject.toml`, gate bloquant en CI + `ci-local/`, 0 violation trouvée (déjà propre). `api.core`/`api.schemas`/`api.sockets` volontairement hors contrat — le skill ne documente que routes→domain→engine |
| **Règles Semgrep custom** | Semgrep tourne avec des règles génériques. Écrire les miennes : « aucun worker n'importe `api.routes` », « tout endpoint v2 a un rate-limit », « pas de `except Exception` sans log » — soit exactement les 3 bugs corrigés le 06/09, transformés en anti-récidive. | M | ⭐⭐⭐ | 📝📝📝 | ✅ 2 règles bloquantes dans `.semgrep/vote-app-rules.yml` (la 3e est déjà couverte par import-linter, pas dupliquée). Les deux ont trouvé de la vraie dette en les écrivant : 3 routers v2 sans rate-limit (corrigé), 18 `except Exception` muets sur 9 fichiers (corrigés) — pas laissé en baseline |
| **`dependency-cruiser`** ou `eslint-plugin-boundaries` | Équivalent front : règles d'architecture sur les imports + cycles. | M | ⭐⭐ | 📝📝 | ✅ règle `lib-is-pure` bloquante dans `.dependency-cruiser.json` (`src/lib` ne doit pas importer `src/components`/`src/pages`, cf. CLAUDE.md — Playground), gate CI + `ci-local/`, imports type-only exemptés. Baseline propre (287 modules, 1558 deps, 0 violation), règle vérifiée en direct sur une violation synthétique injectée puis retirée. Épinglé `17.4.3` : `18.x` exige Node ≥22, ce repo est encore sur Node 20 |
| **`deptry`** | Équivalent de knip pour Python (deps déclarées inutilisées / utilisées non déclarées). Détection présente côté front, absente côté back. | S | ⭐⭐ | 📝📝 | ✅ scope `api/` (exclut `scripts/` polity + `api/tests/`, par design de l'outil), baseline 0, `[tool.deptry]` dans `pyproject.toml`, câblé dans le cliquet qualité. Effet de bord : `ruff`/`pytest*` dupliqués dans `requirements.txt` retirés, `Dockerfile` dev installe désormais `requirements-dev.txt` aussi |
| **Hooks Claude** (`settings.json`) | `PreToolUse` **bloquant** sur `engineParity.json` → rend impossible l'édition manuelle que `CLAUDE.md` interdit par écrit ; `PostToolUse` sur le moteur → rappel de régénérer la parité. ~~Le `.claude/` n'a aucun hook aujourd'hui~~ *(faux — les garde-fous graphify existaient déjà, corrigé)*. | M | ⭐⭐⭐ | 📝📝📝 | ✅ les deux hooks ajoutés (`.claude/hooks/*.py`), **testés en direct** : une vraie tentative d'`Edit` sur `engineParity.json` a été rejetée par le hook (pas juste simulée), checksum du fichier inchangé après |
| **`madge`** | Cycles d'imports front + visualisation du graphe. | S | ⭐ | 📝 | ✅ `npm run madge:circular` + `scripts/audit.sh --quality`, informationnel (pas dans le cliquet, vu son ⭐ bas). 1 cycle trouvé (`useSimulationWorker.ts` ↔ `IdeologyHeatmap.tsx`), bénin — `import type` uniquement, éliminé à la compilation. Visualisation du graphe documentée mais pas générée (nécessite `graphviz`/`dot`, indisponible sans sudo) |

---

## Lot 3 — Le contrat API et la résilience

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **Schemathesis** | `openapi.gen.json` est versionné avec un gate de drift, mais **le contrat n'est jamais vérifié contre l'implémentation**. Schemathesis génère des centaines de requêtes depuis le schéma, fuzze, et vérifie la conformité des réponses. Chaînon manquant le plus évident du projet. | M | ⭐⭐⭐ | 📝📝📝 | ✅ `api/tests/test_schema_contract.py` + workflow dédié `schemathesis.yml` (pas dans `backend-ci-cd-pipeline.yml` par prudence — un run complet mesure ~220s (~3.5-4 min) en local mais n'a pas été revérifié sur un runner GitHub réel). Génération `derandomize=True` + `seed=` fixe pour la reproductibilité (une première tentative avec `derandomize=True` seul ne suffisait pas d'un process à l'autre — `PYTHONHASHSEED` non fixé fausse la dérivation de graine de Hypothesis ; un `seed=` explicite au niveau du `Config` schemathesis, qui ne passe pas par `hash()`, règle le problème). A trouvé et corrigé 6 bugs réels avant d'être mergé : (1) codes de statut atteignables mais jamais documentés (400/404/500/503) sur les 7 routers — corrigé via `responses=` + schéma `ErrorDetail` partagé ; (2) crash `IndexError` sur `/theory/identity-voting` (le schéma acceptait 2 candidats, le worker en exige 3) — corrigé en remontant `min_length` ; (3) crash `max() iterable argument is empty` sur `/assembly`, `/assembly-scorecard`, `/temporal`, `/structural-fairness` quand deux partis partagent un nom (collision de clé dict) — corrigé par un `field_validator` rejetant les doublons ; (4) crash `TypeError`/`IndexError` sur `/campaign-sensitivity` (`snapshot_days` mal typé `List[Any]` + bornes non vérifiées, un jour négatif de grande magnitude débordait l'indexation Python) — corrigé en typant `List[Union[int, Literal["final"]]]` et en bornant des deux côtés (`max(0, min(...))`) ; (5) crash `AttributeError` sur `/choice-overload` (`heuristic_weights` explicitement `null` contournait le défaut de `.get()`) — corrigé en `or {}` ; (6) crash `AttributeError` sur `/tech/polis` (le schéma promet `List[str]`, le worker traitait chaque élément comme un dict) — corrigé pour accepter les deux formes. Le reste (~40 endpoints) est de la dette pré-existante trackée nommément dans `KNOWN_FAILURES` (requêtes délibérément peu typées, timeouts sur des simulations lourdes — recoupe directement l'item "Timeouts & backpressure" ci-dessous), pas noyée dans un chiffre global |
| **Test du rate-limit (429)** | La valeur 120/min a été calibrée après deux échecs e2e — mais rien ne teste que la limite se déclenche vraiment. | S | ⭐⭐ | 📝📝 | |
| **Résilience Redis** | Le rate-limiter dépend de Redis. Que se passe-t-il quand il tombe ? Aujourd'hui : inconnu. | M | ⭐⭐⭐ | 📝📝📝 | |
| **Timeouts & backpressure** | Sémaphore limitant les simulations concurrentes + `asyncio.wait_for` sur les workers, au lieu de saturer le pool de threads. | M | ⭐⭐⭐ | 📝📝 | |
| **Déconnexion Socket.IO en plein run** | Partiellement testé le 06/09, à compléter (client qui coupe, run orphelin). | S | ⭐⭐ | 📝 | |

---

## Lot 4 — Le domaine électoral *(le cœur exploratoire)*

**C'est le lot à plus forte valeur du plan, et le plus spécifique à ce projet.**
Les critères de la théorie du choix social sont littéralement des propriétés
testables — un levier que presque aucun repo ne possède.

### 4.1 — Tests axiomatiques systématiques ⭐⭐⭐ 📝📝📝 · `L`

Pour chacune des 26 méthodes, vérifier les critères qu'elle **doit** satisfaire
*et ceux qu'elle doit violer* : Condorcet, majorité, monotonie, participation,
indépendance des clones, symétrie par renversement, Pareto, unanimité.

Un test qui vérifie qu'**IRV échoue la monotonie** est aussi précieux qu'un test
de succès : il documente la théorie *et* détecte une implémentation qui
deviendrait accidentellement monotone — donc fausse. `test_anonymity.py` est
déjà ce germe, à généraliser en matrice méthode × critère.

Sous-produit : cette matrice est **directement publiable** comme contenu
pédagogique, et recoupe `THEORY.md`.

### 4.2 — Oracle tiers (`pref_voting` / `abcvoting`) ⭐⭐⭐ 📝📝📝 · `M`

La parité actuelle compare *mes deux* implémentations — qui peuvent être fausses
**ensemble**. Croiser avec une bibliothèque académique indépendante (celle de
Pacuit & Holliday) casse cette corrélation d'erreur. Tout écart est soit un bug
chez moi, soit une divergence de convention à documenter — les deux sont du bon
contenu.

### 4.3 — Vérification exhaustive des petits cas ⭐⭐⭐ 📝📝📝 · `M`

Pour n ≤ 4 candidats et m ≤ 5 électeurs, l'espace des profils est **fini et
petit**. On passe de « 60 scénarios aléatoires » à une **preuve exhaustive**
front/back sur tout le domaine borné. Gain de confiance considérable pour un
coût dérisoire.

### 4.4 — `fast-check` côté TypeScript ⭐⭐⭐ 📝📝 · `M`

Hypothesis couvre le Python ; `playgroundVoting.ts` — l'autre moitié du contrat
de parité — n'a aucun test à propriétés.

### 4.5 — Contre-exemples de la littérature comme fixtures nommées ⭐⭐ 📝📝📝 · `M`

Paradoxe de Condorcet, exemples de manipulation Borda, profils de Saari…
chaque exemple classique devient une fixture nommée et sourcée (clé BibTeX de
`docs/research/`). Double emploi test + pédagogie.

### 4.6 — Z3 / model checking ⭐ 📝📝📝 · `L` *(expérience à risque assumé)*

Prouver l'équivalence de deux implémentations sur des configurations bornées
plutôt que d'échantillonner. **Peut très bien échouer** (encodage trop lourd,
explosion combinatoire) — et un échec documenté « voilà pourquoi le SMT ne passe
pas à l'échelle sur ce problème » est un excellent carnet d'expérience.

---

## Lot 5 — Robustesse des tests eux-mêmes

*Qui teste les tests ?* Angle de récit fort : la couverture à 91 % ment-elle ?

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Score de mutation ciblé + gating** | mutmut/Stryker tournent mais sont informatifs. Un seuil *par module critique* (le moteur uniquement) vaut mieux qu'un score global mou. | M | ⭐⭐⭐ | 📝📝📝 |
| **`pytest-randomly`** | Ordre d'exécution aléatoire → révèle les tests couplés par effet de bord (déjà rencontré avec le limiter partagé). | S | ⭐⭐ | 📝📝 |
| **Chasse au flake nocturne** | Relancer la suite N fois et tracker l'instabilité. Le « flaky check » existe en e2e, rien côté backend. | M | ⭐⭐ | 📝📝 |
| **Régénérabilité de `engineParity.json`** | Un job qui régénère et diffe prouverait que le fichier n'a pas été édité à la main — aujourd'hui c'est une règle écrite, rien ne l'applique. | S | ⭐⭐⭐ | 📝📝 |
| **`syrupy`** (snapshots pytest) | Sorties de simulation riches, plus lisibles qu'des assertions à la main. | S | ⭐ | 📝 |

---

## Lot 6 — Ce que l'analyse statique ne voit pas

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Couverture *runtime*** (Istanbul sur e2e + `coverage.py`) | Trouve le code jamais exécuté **même en usage réel** — angle mort total de vulture/knip qui sont statiques. Après avoir supprimé 16 500 lignes mortes, la question « qu'est-ce qui reste inatteignable ? » est légitime. | M | ⭐⭐⭐ | 📝📝📝 |
| **`basedpyright`/pyright** | Moteur d'inférence différent de mypy → attrape d'autres choses. Combien, sur un code déjà mypy-strict-clean ? Bonne question d'expérience. | S | ⭐⭐ | 📝📝📝 |
| **`refurb`** + **`perflint`** | Modernisation Python et anti-patterns de perf — pertinent sur un moteur CPU-bound. | S | ⭐ | 📝📝 |
| **`type-coverage`** (TS) | % de code réellement typé (les `any` implicites que `tsc` laisse passer). | S | ⭐⭐ | 📝📝 |
| **`eslint-plugin-sonarjs`** | Complexité cognitive (≠ cyclomatique, déjà mesurée par radon) + bugs courants. | S | ⭐⭐ | 📝 |
| **`pip-licenses` / `license-checker`** | Conformité de licences sur un repo public MIT. | S | ⭐ | 📝 |

### 6.1 — Audit de pertinence des commentaires · `L` · ⭐⭐ 📝📝📝

Aucun outil du repo ne regarde les commentaires. Ils sont pourtant du **code
non compilé, non testé, jamais vérifié** — la seule zone du projet où une
affirmation fausse peut survivre indéfiniment sans que rien ne la signale.

**Poids mesuré** (2026-09-07) : ~174 k tokens côté `fast_api_voter/api`
(26,6 % du volume) et ~79 k côté `voter-app/src` (9,5 %), soit **~253 k tokens
de commentaires et docstrings**.

**L'audit trie en quatre catégories, avec un traitement distinct :**

| Catégorie | Traitement | Justification |
|---|---|---|
| **Périmé** — décrit du code qui a changé | Corriger ou supprimer | Activement nuisible : induit en erreur humains et agents. La passe de doc du 06/09 (PR #313) a traité ce problème au niveau des fichiers `.md` ; personne ne l'a jamais fait au niveau des commentaires. |
| **Redondant** — paraphrase le code | Supprimer | Coût pur, zéro information. Sur du code typé mypy-strict, un docstring qui répète la signature n'apporte rien. |
| **Archéologique** — récit d'une session (« le 25/08, essayé X, échoué parce que… ») | **Migrer vers `docs/exploration/`** | C'est du carnet d'expérience égaré dans du code source (cf. Lot 0.2). |
| **« Pourquoi »** — contrainte, bug passé, alternative écartée | **Garder en place, non négociable** | C'est le mécanisme anti-répétition du Lot 0.5 à l'échelle de la ligne. Le docstring de `api/core/ratelimit.py` expliquant *pourquoi 120/min et pas 30* est ce qui empêche de le « ré-optimiser » à 30 et de recasser l'e2e. |

**Cadrage explicite — ce que cet audit n'est pas** : ce n'est pas un projet
d'économie de tokens, et il ne consiste pas à *déplacer* les commentaires hors
du code. L'hypothèse a été mesurée puis écartée : `package-lock.json` seul
(~155 k tokens) coûte plus cher que l'intégralité des commentaires du frontend
(~79 k), et son exclusion via `.claudeignore` (§12.2) est gratuite et sans
risque. Surtout, un commentaire voyage **dans le même diff** que le code qu'il
explique — pas un fichier récap, qui dérive. Sortir les « pourquoi » du code
fabriquerait à grande échelle exactement la dérive que la PR #313 a passé une
session à réparer. Le bénéfice visé ici est la **justesse**, pas le volume ;
la réduction de tokens n'est qu'un effet de bord des catégories « redondant »
et « archéologique ».

**La mesure à publier** : *« j'ai audité 253 k tokens de commentaires — quelle
proportion mentait ? »* Ce chiffre n'existe nulle part, et il se prête à une
méthode reproductible sur d'autres projets.

**Piste d'outillage** : pas d'outil établi pour la détection de commentaires
périmés. Deux approches à essayer et à comparer dans le carnet d'expérience —
(a) heuristique par `git log` : commentaire dont la dernière modification est
nettement plus ancienne que celle des lignes de code qu'il surplombe ;
(b) passe LLM par lot sur des blocs `(commentaire, code)`. Le contraste entre
les deux est lui-même un bon contenu.

---

## Lot 7 — Surfaces perçues par l'utilisateur

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **a11y sur *toutes* les routes** | `routes.ts` est déjà « data » — boucler dessus et échouer si une surface n'est pas auditée, même mécanique que l'anti-rot e2e existant. | M | ⭐⭐⭐ | 📝📝 |
| **Régression visuelle** (Playwright screenshots / Lost Pixel) | L'app est quasi entièrement visuelle (SVG, cartes, Recharts) et **rien** ne détecte qu'une carte s'affiche de travers. | M | ⭐⭐⭐ | 📝📝📝 |
| **Viewport mobile en e2e** | App pédagogique → usage mobile probable, zéro test mobile aujourd'hui. | M | ⭐⭐ | 📝📝 |
| **`i18next-parser`** + `eslint-plugin-i18next` | Clés orphelines/manquantes et chaînes en dur (5 encore trouvées à la main le 06/09). | M | ⭐⭐ | 📝📝 |
| **Pseudo-locale à chaînes longues** | Casse les layouts avant que l'anglais ou une future langue ne le fasse. | S | ⭐⭐ | 📝📝📝 |
| **Webkit en e2e** | Seuls chromium et firefox tournent aujourd'hui. | S | ⭐⭐ | 📝 |

---

## Lot 8 — Performance

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **`pytest-benchmark` + seuils** | Une régression de perf sur `simulation_ranked_utils` est aujourd'hui totalement invisible. | M | ⭐⭐⭐ | 📝📝 |
| **Charge (k6 ou Locust)** | Le rate-limit 120/min a été calibré au jugé ; un test de charge donne le vrai plafond du pool de threads. | M | ⭐⭐⭐ | 📝📝📝 |
| **Invariant de perf du form-lock** | Documenté dans le skill `voter-ui`, jamais mesuré. React Profiler + assertion. | M | ⭐⭐ | 📝📝📝 |
| **Budget de bundle** | Seuil de taille sur le build Vite, échec si dépassement. | S | ⭐⭐ | 📝 |

---

## Lot 9 — Sécurité approfondie

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **DAST — ZAP baseline** | SAST (Semgrep/CodeQL) ne voit que le code, jamais le comportement de l'app qui tourne. | M | ⭐⭐ | 📝📝 |
| **Fuzzing à couverture** (`atheris` ou `hypofuzz`) | Bien plus profond qu'Hypothesis seul sur le moteur et les parseurs. | L | ⭐⭐ | 📝📝📝 |
| **`guarddog`** (Datadog) | Détecte les paquets *malveillants* (typosquatting, install-scripts hostiles) — angle mort de pip-audit/Trivy qui ne voient que les CVE connues. | S | ⭐⭐ | 📝📝📝 |
| **`trufflehog`** | Secrets **vérifiés actifs**, pas juste des motifs (complète gitleaks + detect-secrets). | S | ⭐ | 📝 |
| **OSV-Scanner** | Base de vulnérabilités différente de Trivy, recouvrement imparfait. Mesurer l'écart réel est une bonne expérience. | S | ⭐ | 📝📝📝 |
| **Signature d'images + provenance SLSA** (cosign/sigstore) | Suite logique du SBOM + Scorecard déjà en place. | M | ⭐⭐ | 📝📝📝 |
| **`minimumReleaseAge`** (via Renovate) | Attendre 3-7 j avant d'adopter une release : vraie défense contre les paquets compromis. | S | ⭐⭐⭐ | 📝📝 |

---

## Lot 10 — Observabilité

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Sentry ou GlitchTip** | Le handler global ajouté le 06/09 *logge* — mais personne ne lit les logs d'une app pédagogique. Sans collecteur, ce travail ne sert à rien en pratique. | M | ⭐⭐⭐ | 📝📝 |
| **OpenTelemetry** | Traces par endpoint, temps réel par méthode de vote — alimente aussi le Lot 8. | L | ⭐⭐ | 📝📝📝 |
| **`/metrics` Prometheus** + readiness/liveness distincts | `/health` existe mais reste binaire. | M | ⭐⭐ | 📝 |

---

## Lot 11 — Outillage Claude avancé

Le `.claude/` actuel est mince : 2 skills, 1 agent, 1 commande, **0 hook**.
Angle de récit : *« à quoi ressemble un repo réellement outillé pour le
développement assisté par agent ? »* — sujet sur lequel il existe très peu de
retours concrets.

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Agent `parity-guardian`** | Dès qu'une règle de vote bouge : régénère la parité, lance le test, explique tout écart. | M | ⭐⭐⭐ | 📝📝📝 |
| **Agent `dep-triage`** | Lit les PR Dependabot, classe patch/mineur/majeur, lit les changelogs, propose l'ordre de merge. Répond pile à la douleur du 06/09. | M | ⭐⭐ | 📝📝📝 |
| **Agent `axiom-checker`** | Vérifie qu'une nouvelle méthode de vote arrive avec ses tests axiomatiques (Lot 4.1). | M | ⭐⭐ | 📝📝 |
| **Agent `flake-hunter`** | Isole les tests instables, propose un correctif. | M | ⭐⭐ | 📝📝 |
| **Agent `doc-drift`** | Celui improvisé le 06/09, figé en agent réutilisable + cron mensuel. | S | ⭐⭐ | 📝📝📝 |
| **Skill `voter-testing`** | Comment tester ici : Hypothesis, fixtures de parité, testids e2e, pièges connus. | M | ⭐⭐ | 📝📝 |
| **Skill `voter-ci`** | Diagnostiquer un échec CI, où sont les gates, que faire quand le ratchet casse. | M | ⭐⭐ | 📝📝 |
| **Skill `release`** | Checklist `develop → main`. | S | ⭐⭐ | 📝 |
| **Agents planifiés** | Revue hebdo du diff de la semaine, audit doc mensuel, veille de dépendances. | M | ⭐⭐ | 📝📝📝 |
| **`/code-review ultra`** sur les PR du moteur | Existe déjà, sous-utilisé sur les changements sensibles. | S | ⭐⭐ | 📝📝 |

---

## Lot 12 — Économie de tokens & efficacité du contexte

Lot transversal : **12.1 et 12.2 peuvent démarrer immédiatement**, le reste
s'installe au fil des autres lots.

La garde `graphify` déjà en service dans le worktree polity (`PreToolUse` qui
impose une requête de graphe avant tout grep) appartient déjà à cette famille —
ce lot la généralise plutôt qu'il n'introduit un concept neuf.

Principe directeur : **le levier n'est pas de « parler moins », c'est de ne
jamais charger ce qui n'apporte rien.**

### 12.1 — Mesurer d'abord · `S` · ⭐⭐ 📝📝📝

On n'optimise pas ce qu'on ne mesure pas.

- **Télémétrie OpenTelemetry de Claude Code** : consommation et coût par session.
- **Analyse des transcripts locaux** (`~/.claude/projects/**/*.jsonl`) : ils
  contiennent déjà les usages par tour — exploitables par script maison ou par
  un outil communautaire type `ccusage` (à évaluer, pas à adopter d'office).
- `/cost` en séance pour le retour immédiat.
- **Rattachement au Lot 0.2** : ajouter une ligne « coût en tokens » au gabarit
  de carnet d'expérience. Chaque expérience du plan porte alors son coût réel —
  et le tableau des verdicts (0.3) devient *« ce que chaque outil a trouvé, et
  ce qu'il a coûté »*, ce qui est nettement plus intéressant à partager.

### 12.2 — Ne jamais charger ce qui ne doit pas l'être · `M` · ⭐⭐⭐ 📝📝

Mesure réelle sur ce repo (estimation à ~4 octets/token) :

| Fichier | Poids | Nature |
|---|---|---|
| `voter-app/package-lock.json` | ~155 k tok | généré |
| `fast_api_voter/Electors simulation.ipynb` | ~152 k tok | notebook **avec sorties stockées** |
| `fast_api_voter/openapi.gen.json` | ~116 k tok | généré |
| `voter-app/src/api/types.gen.ts` | ~88 k tok | généré |
| `voter-app/src/lib/__fixtures__/engineParity.json` | ~33 k tok | généré |

**Ces cinq fichiers pèsent ~544 k tokens** — largement plus qu'une fenêtre de
contexte. Une seule lecture intégrale accidentelle de l'un d'eux consomme
l'équivalent de plusieurs heures de travail utile. Aucun n'a de raison d'être lu
en entier : quatre sont des artefacts générés, le cinquième est un notebook dont
l'essentiel du poids est constitué de sorties.

Actions :

- **`.claudeignore`** (absent aujourd'hui) sur les artefacts générés.
- **Hook d'avertissement** sur la lecture intégrale d'un fichier généré, calqué
  sur la garde `graphify` déjà éprouvée.
- **`nbstripout`** en pre-commit sur le notebook : les sorties stockées n'ont
  pas à être versionnées, et représentent ici l'essentiel des 152 k tokens.
- **Rotation du journal** : `JOURNAL_DE_BORD.md` pèse déjà ~42 k tokens et
  croît à chaque session. Archiver par année, sinon **le dispositif
  anti-répétition devient lui-même le poste de dépense** — exactement le piège
  identifié au Lot 0.5.

### 12.3 — Lire moins cher ce qu'on lit quand même · `M` · ⭐⭐ 📝📝📝

| Outil | Gain |
|---|---|
| **`graphify`** | Éprouvé côté polity — évaluer son portage sur `develop`. |
| **`ast-grep`** | Recherche *structurelle* : beaucoup moins de faux positifs que grep, donc beaucoup moins de lecture pour les écarter. |
| **`repomix --compress`** | Empaquette le repo en gardant les signatures sans les corps : vue large à coût réduit. |
| **Cartes de fichier** (signatures seules, via tree-sitter/ast-grep) | S'orienter dans un fichier de 30 k tokens sans le charger. |
| **Lecture par plage** (`offset`/`limit`) | Réflexe par défaut sur les gros fichiers plutôt que la lecture intégrale. |
| **Sorties d'outils courtes** | `pytest -q --tb=short`, `jq` plutôt que du JSON brut, `--stat` plutôt qu'un diff complet. Une sortie verbeuse est un coût récurrent. |

### 12.4 — Architecture de session · `M` · ⭐⭐ 📝📝📝

- **Les sous-agents sont le levier majeur** : le contexte de fouille reste chez
  eux, seul le rapport remonte. Pratiqué le 06/09 (4 agents de documentation en
  parallèle) — à systématiser sur les tâches exploratoires.
- **Un modèle par agent** (`model:` dans le frontmatter des définitions) : les
  agents mécaniques du Lot 11 (`doc-drift`, `dep-triage`) n'ont pas besoin du
  modèle le plus cher ; le jugement, si.
- **Plan mode** pour cadrer avant d'exécuter — évite les allers-retours coûteux.
- Sessions ciblées plutôt que fleuves.

### 12.5 — Cache de prompt · `S` · ⭐⭐ 📝📝

`CLAUDE.md` pèse ~1 200 tokens et est chargé **à chaque requête** : c'est sain
aujourd'hui, l'enjeu est que ça le reste. Un gate CI sur sa taille suffit.
Corollaire : éviter de modifier en cours de session les fichiers chargés
d'office, chaque modification invalidant le cache.

### 12.6 — Le lien avec tout le reste du plan · ⭐⭐⭐ 📝📝📝

**Chaque gate automatisé est un token économisé.** Un linter qui renvoie
l'erreur en trois lignes remplace un tour de conversation entier passé à la
chercher. Vu sous cet angle, les Lots 1 à 9 ne sont pas seulement du
durcissement : ce sont des économies de contexte.

C'est probablement l'angle de récit le plus original de tout le plan —
« j'ai mesuré ce que mon outillage qualité me faisait économiser en tokens » est
un chiffre que personne ne publie.

---

## Lot 13 — Synthèse & partage *(à faire en dernier, il consomme tout le reste)*

| Item | Contenu | Effort | Récit |
|---|---|---|---|
| **Index des verdicts complété** | Le tableau du Lot 0.3, rempli par ~25 expériences réelles. | S | 📝📝📝 |
| **Rétrospective du plan** | Ce plan a-t-il survécu au contact ? Quels items abandonnés, lesquels ajoutés en route, lesquels ont déçu. | M | 📝📝📝 |
| **Les 3-4 histoires les plus partageables** | Candidats naturels : « la couverture à 91 % ment-elle ? » (Lot 5) · « 25 outils de qualité sur un vrai projet, le tableau des verdicts » (Lot 0.3) · « tester une théorie mathématique comme on teste du code » (Lot 4) · « combien de mes conventions écrites étaient déjà violées » (Lot 2). | L | 📝📝📝 |
| **`CODE_AUDIT.md` rejoué** | Nouvelle édition datée après tous les lots, comparaison avec l'édition du 2026-09-06. | S | 📝📝 |
| **README qui raconte** | Le repo est public : rendre visible la double exploration (méthodes de vote *et* pratiques de dev). | M | 📝📝📝 |

---

## Séquencement recommandé

```
Lot 0  (documentation)          ← EN PREMIER, sinon tout le reste est perdu
   ↓
Lot 1  (quick wins)             ← débloque le confort de tous les suivants
   ↓
Lot 2  (conventions exécutables) ─┐
Lot 3  (contrat API + résilience) ├─ indépendants entre eux
Lot 5  (robustesse des tests)     │
Lot 6  (angles morts du statique) ─┘
   ↓
Lot 4  (domaine électoral)      ← le cœur ; mérite d'être fait posément
   ↓
Lot 7 (surfaces) · Lot 8 (perf) · Lot 9 (sécurité) · Lot 10 (observabilité)
   ↓
Lot 11 (outillage Claude)       ← profite de tout ce qui précède
   ↓
Lot 13 (synthèse & partage)

Lot 12 (économie de tokens)     ← TRANSVERSAL : 12.1 et 12.2 dès maintenant,
                                   le reste s'installe au fil des autres lots
```

**Dépendances dures** (le reste est librement réordonnable) :

- Lot 0 avant tout — c'est le dispositif de capture.
- Lot 1 avant les lots lourds en CI (cache, `uv`, groupes Dependabot).
- Lot 4.1 (axiomes) avant Lot 11 `axiom-checker` — l'agent a besoin de la matrice.
- Lot 12.1 (mesure) avant les lots coûteux, sinon on n'a pas de point de
  comparaison pour chiffrer ce qu'ils économisent (§12.6).
- Lot 13 en dernier par construction.

## Règles d'exécution

- **Une branche `feat/*` + une PR par item**, contre `develop`, merge `--no-ff`.
- Un item se termine par un **carnet d'expérience** (`docs/exploration/EXP-*.md`)
  quand il s'agit d'un outil essayé — pas pour les items purement internes.
- **Un verdict « rejeté » est un succès du plan**, pas un échec : il faut juste
  qu'il soit argumenté avec ce que l'outil a réellement trouvé et coûté.
- Ne pas empiler plus de 2-3 items ouverts en parallèle : la protection de
  branche invalide les PR entre elles (leçon du 06/09).
- Chiffrer avant/après quand c'est possible — un plan d'exploration sans mesure
  ne produit pas de récit crédible.
