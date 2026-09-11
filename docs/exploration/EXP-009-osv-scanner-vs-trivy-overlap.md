# EXP-009 — OSV-Scanner vs Trivy : mesurer le recouvrement réel, pas le supposer

- **Date** : 2026-09-11 · **Statut** : adopté (informational, local + CI — voir réserve réseau ci-dessous) · **Coût réel** : ~1h45 (recherche outillage/CLI, deux pièges d'environnement diagnostiqués et contournés, cross-vérification à trois outils : OSV-Scanner, Trivy réel via Docker, pip-audit réel)
- **Verdict en une phrase** : sur l'état réel des dépendances de ce dépôt aujourd'hui, OSV-Scanner et Trivy sont d'accord à **zéro vulnérabilité** (cross-vérifié par un troisième outil, pip-audit, également à zéro) — un écart nul *mesuré*, pas supposé par construction, confirmé par un détecteur dont la sensibilité a été vérifiée en direct contre deux paquets sciemment obsolètes ; la vraie valeur de l'outil est procédurale (une deuxième base de données CVE indépendante réduit le risque qu'une lacune ponctuelle d'une seule base passe inaperçue), pas un delta numérique aujourd'hui.

## Hypothèse de départ

Le [Lot 9 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#lot-9--sécurité-approfondie)
nomme explicitement l'expérience : Trivy (déjà en place, gating HIGH/CRITICAL
dans `audit.yml`) et OSV-Scanner utilisent des bases de vulnérabilités
différentes, recouvrement imparfait par construction — mesurer l'écart réel
sur ce dépôt, pas un dépôt jouet, est la question posée. Hypothèse testée :
combien de CVE l'un trouve que l'autre rate, dans les deux sens, sur les
dépendances de production réelles de ce dépôt (backend Python +
frontend npm) ?

## Protocole

Binaire officiel `osv-scanner` v2.5.1 (release GitHub, pas `go install`),
Trivy réel via son image Docker officielle (`aquasec/trivy:latest`, cette
session n'a pas de binaire Trivy local) contre les mêmes fichiers, dans le
même dépôt, au même commit :

```
osv-scanner scan source -L fast_api_voter/requirements.txt \
  -L fast_api_voter/requirements-dev.txt -L voter-app/package-lock.json \
  --data-source native --format json

docker run --rm -v <repo>:/repo:ro aquasec/trivy:latest fs \
  --scanners vuln --format json /repo   # une passe HIGH/CRITICAL, une passe toutes sévérités

pip-audit -r fast_api_voter/requirements.txt --format json   # troisième avis, déjà dans les gates du dépôt
```

Avant de faire confiance à un résultat « propre », vérifier que le détecteur
détecte vraiment quelque chose quand il y a vraiment quelque chose (même
discipline que EXP-004/EXP-006 — injecter puis confirmer, pas espérer) :
`requirements.txt` jouet avec `urllib3==1.26.4` et `Jinja2==2.4.1` (deux
versions sciemment obsolètes, CVE publiques connues).

## Ce que ça a trouvé

**Le détecteur fonctionne : 18 CVE réels remontés pour CHACUN des deux
paquets test** (`urllib3==1.26.4` → 18, `Jinja2==2.4.1` → 18, dont
`PYSEC-2021-108`, `PYSEC-2023-212`, `PYSEC-2014-8`…) — la sensibilité d'
OSV-Scanner est réelle, pas supposée, avant de faire confiance au résultat
sur le vrai dépôt.

**Sur les vraies dépendances de ce dépôt : accord total, zéro partout.**
OSV-Scanner (`--data-source native`, toutes sévérités) : **0** vulnérabilité
sur 15 paquets `requirements.txt` + 32 `requirements-dev.txt` + 1360 entrées
`package-lock.json`. Trivy (image Docker officielle, réel, pas simulé) : **0**
en HIGH/CRITICAL (la config gating actuelle de `audit.yml`) **et 0** toutes
sévérités confondues (une passe sans `--severity` pour ne pas favoriser
artificiellement l'accord). pip-audit (déjà un gate de ce dépôt) : **0** sur
les 15 + transitives résolues. Trois outils indépendants, même verdict —
cohérent avec le rythme hebdomadaire de Dependabot (`cooldown: 7j`, voir Lot 9
« minimumReleaseAge ») qui maintient ce dépôt à jour plutôt qu'un signe que le
recouvrement serait nul par construction.

Note méthodologique trouvée en comparant les rapports bruts, pas juste les
totaux : Trivy ne détecte **que** `requirements.txt` (15 paquets) — jamais
`requirements-dev.txt` — alors que l'invocation OSV-Scanner de cette
expérience couvre explicitement les deux via `-L` répété. Les comptages de
paquets npm ne sont eux-mêmes pas directement comparables entre les deux
outils (Trivy : 283 entrées ; OSV-Scanner : 1360) — vraisemblablement une
différence d'interprétation de l'arbre `package-lock.json` (dédoublonnage des
versions dupliquées vs comptage de chaque instance), sans incidence sur le
verdict vulnérabilité (zéro des deux côtés) mais un signal que comparer des
*comptes de paquets* entre scanners n'a pas de sens — seul le compte de
*vulnérabilités* en a.

**Deux pièges d'environnement réels, tous deux diagnostiqués avant d'être
contournés** (pas juste observés et évités) :

1. La source de données par défaut d'OSV-Scanner (`deps.dev`, résolution via
   gRPC) a timeout dans cette session sandboxée (`rpc error: ...
   connection timeout`) alors qu'un `curl` direct vers `https://api.deps.dev`
   et `https://api.osv.dev` répond en 200 ms — le problème est spécifique au
   transport gRPC de cet environnement, pas un blocage réseau général.
   `--data-source native` (résolution locale + requêtes REST vers osv.dev)
   contourne ce chemin ; utilisé en local ET en CI par cohérence, malgré un
   réseau CI a priori non affecté.
2. `osv-scanner scan source -r .` (mode récursif, l'invocation recommandée
   par défaut) trouve silencieusement **zéro** source de paquets quand il
   tourne depuis ce *worktree* git (`0 dirs visited, 1 inodes visited` puis
   `No package sources found`) — alors que les **mêmes** lockfiles, avec la
   **même** commande, sont trouvés sans problème (1360+32+15 paquets) une
   fois copiés hors du worktree dans un répertoire ordinaire. Isolé en
   testant `-L` explicite (fonctionne, dans le worktree) contre `-r`
   (échoue, dans le worktree seulement) : le bug est dans le walker
   récursif face à la structure `.git` d'un worktree (un fichier
   `gitdir: ...`, pas un répertoire), pas dans le dépôt ni dans les
   lockfiles eux-mêmes. `scripts/audit.sh` utilise `-L` par fichier pour
   cette raison — plus robuste, et accessoirement plus rapide (pas besoin
   d'exclure `node_modules`/`.venv`).

## Ce que ça a coûté

~1h45 : ~25 min de recherche outillage/CLI réel (pas la doc résumée — `--help`
de chaque sous-commande vérifié en direct, y compris la découverte que
`-r` prend des répertoires positionnels et non une liste après le flag) ;
~20 min à diagnostiquer le piège gRPC (curl de contrôle vers les deux
domaines avant de conclure que c'était le transport, pas le réseau) ; ~15 min
à isoler le piège du worktree (quatre invocations comparées : `-r` dans le
worktree, `-L` dans le worktree, `-r` hors-worktree, `-L` hors-worktree) ;
~20 min pour le run Trivy réel (pull de l'image ~180 Mo compris, deux passes
de sévérité) ; ~15 min pip-audit + vérification croisée des trois rapports ;
~10 min sanity-check du détecteur (paquets sciemment obsolètes). Aucune
nouvelle dépendance Python — `osv-scanner` est un binaire Go autonome (release
GitHub), Trivy tourne via Docker (déjà utilisé ailleurs dans ce dépôt/CI).

## Verdict et pourquoi

**Adopté, informational, local (`scripts/audit.sh`) + CI (job `osv-scanner`
dans `audit.yml`, workflow réutilisable officiel des mainteneurs,
`fail-on-vuln: false`).** Le détecteur est vérifié sensible (18/18 CVE sur
les paquets test), le zéro mesuré sur ce dépôt est cross-confirmé par deux
autres outils indépendants (Trivy réel, pip-audit réel) — pas un artefact
d'une invocation cassée. La valeur de l'item n'est pas le delta d'aujourd'hui
(il est nul) mais la réduction structurelle du risque qu'une lacune future
d'une seule base de données CVE (Trivy s'appuie en bonne partie sur les
avisories GHSA/NVD ; OSV-Scanner interroge directement osv.dev, qui agrège
GHSA, PYSEC, RustSec, OSS-Fuzz et d'autres sources écosystème par
écosystème) passe inaperçue.

**Réserve honnête** : le job CI n'a, comme le reste de cette session, jamais
tourné sur un vrai runner GitHub Actions (worktree isolé, sans droit de push
ni de PR). Les deux pièges d'environnement trouvés ici (gRPC, worktree) sont
tous deux, à la lecture de leur nature, spécifiques à cette session
sandboxée plutôt qu'au dépôt ou à un runner GitHub standard — mais ce n'est
pas *observé*, seulement *probable*. Recommandation identique à celle
d'EXP-004 pour son mécanisme `container:` jamais vu tourner en vrai : ne pas
promouvoir ce job en required check avant d'avoir vu un run réel passer
proprement.

## Ce que j'en retiens (transférable à un autre projet)

1. **Deux scanners de CVE qui « couvrent des bases différentes » ne
   garantissent pas un delta observable — le mesurer réellement, avec un
   troisième outil en arbitre, est la seule façon de savoir si l'écart de
   ce projet-ci est réel ou nul.** Un écart nul honnêtement mesuré (et
   cross-vérifié) est un résultat aussi valide qu'un écart positif — voir
   `docs/exploration/TEMPLATE.md`.
2. **Vérifier la sensibilité du détecteur AVANT de lui faire confiance sur du
   zéro** : sans les deux paquets test (`urllib3==1.26.4`, `Jinja2==2.4.1`),
   rien ne distingue « ce dépôt est propre » de « l'invocation est cassée et
   ne trouve jamais rien ». Les deux produisent exactement le même JSON vide
   en apparence.
3. **Un piège d'environnement trouvé en creusant (`/proc`, `ss`, des curls de
   contrôle) plutôt que contourné à l'aveugle change la conclusion qu'on en
   tire** : un simple retry ou un `--offline` réflexe aurait masqué que le
   problème était spécifiquement le transport gRPC, pas le réseau — une
   distinction qui compte pour savoir si le même piège frappera un runner
   GitHub Actions (réseau standard, transport gRPC identique) ou pas.
4. **Un `git worktree` n'est pas un détail d'infrastructure invisible aux
   outils tiers** — troisième fois que cette famille de piège apparaît dans
   ce plan sous une forme différente (comparer aux pièges git déjà
   documentés ailleurs dans ce dépôt) : un outil qui fait sa propre
   détection de racine de projet peut se comporter différemment face à un
   `.git` fichier plutôt que répertoire, silencieusement, sans erreur.
