# Plan — Angles morts structurels de la CI (évaluation notée du 2026-09-14)

> **Origine** : à la clôture de `PLAN_REMEDIATION_CI_CD.md` (6/6 items
> fermés, voir sa mise à jour du 2026-09-14), l'utilisateur a demandé une
> évaluation notée /5 de la CI, catégorie par catégorie, avec points
> d'amélioration concrets. Chaque catégorie a été vérifiée en direct dans la
> même session (checks empiriques : forcer TypeScript 7 et tracer les
> `require()` réels pour comprendre pourquoi `typescript-eslint` bloque,
> vérifier les 55 pins Python directs contre l'API PyPI, lire
> `audit.yml`/`scripts/audit.sh` en entier), pas une relecture de
> documentation existante.
>
> Légende de statut : 🔴 pas fait / ouvert · 🟡 dette documentée, non
> bloquant · 🟢 fait/résolu.
>
> **Portée** : ce plan couvre uniquement les points d'amélioration concrets
> issus de cette évaluation — pas une nouvelle exploration d'outils, et pas
> un doublon de `PLAN_REMEDIATION_CI_CD.md` (items disjoints, vérifié).

---

## 0. Contrainte de cette session d'exécution

**Le GPU est occupé par un run polity en cours (conteneur Docker
`vllm-polity`, vLLM servant un modèle, ~93% d'utilisation GPU au moment de
l'écriture) et ne doit pas être interrompu.** Aucun item ci-dessous n'a
besoin du GPU (uniquement des scripts CI, du texte de config, et des
installations Python/npm CPU-only) — la contrainte n'a donc changé aucune
décision technique, elle est notée ici pour traçabilité.

---

## 1. Constat général

La note globale de l'évaluation était **4/5** — un pipeline mature, avec une
densité de commentaires « pourquoi » datés et vérifiés rare pour un dépôt de
cette taille, mais avec des failles concrètes et démontrées cette même
session, pas hypothétiques :

| # | Catégorie évaluée | Note |
|---|---|---|
| 1 | Gestion des dépendances & prévention de dérive | 4/5 |
| 2 | Scan de sécurité | 5/5 |
| 3 | Cliquets qualité (mutation, coverage, complexité) | 4/5 |
| 4 | E2E / multi-navigateur / régression visuelle | 3/5 |
| 5 | Architecture CI / merge | 5/5 |
| 6 | Reproductibilité des dépendances Python | 3/5 |
| 7 | Documentation & mémoire institutionnelle | 4/5 |

Cinq points d'amélioration concrets en sont sortis, listés ci-dessous par
priorité. **Deux d'entre eux (D et une partie de E) n'ont finalement demandé
aucune action** — vérifiés en relisant le code existant, la « faille »
supposée n'en était pas une.

---

## 2. Items à traiter, par priorité

### 2.A 🔴→🟢 Image Docker de `visual-regression` désynchronisable de `@playwright/test` — angle mort de Dependabot

**Constat** : `.github/workflows/e2e.yml`, job `visual-regression`, épingle
`container: image: mcr.microsoft.com/playwright:v<X>-noble` en dur, qui doit
rester en lock-step exact avec `@playwright/test` dans
`voter-app/package.json` (rendu byte-identique du screenshot de référence).
Dependabot a bien un ecosystem `docker`, mais il ne parse que les
`Dockerfile` — pas un champ `container: image:` inline dans un workflow. Ce
n'est pas hypothétique : PR #469 (Dependabot, bump routine
`@playwright/test` 1.62.1 → 1.63.0) a cassé `develop` pour de vrai, confirmé
via `gh run list --workflow=e2e.yml --branch=develop` montrant le run
post-merge de #469 lui-même en `completed failure`, corrigé en hotfix
séparé (PR #478).

**Pourquoi ça compte** : c'est le seul job requis dont le mécanisme de
protection (Dependabot) a un angle mort connu et déjà exploité — deux fois
en une semaine, une fois par un bump routine, un point de dérive qui va
forcément se représenter au prochain bump `@playwright/test`.

**Action** : ajouter un job CI rapide, sans conteneur, qui tourne toujours
(pas seulement quand `visual-regression` se déclenche) et échoue avec un
message clair si le tag de `e2e.yml` ne correspond plus à
`@playwright/test` dans `package.json` — transforme l'échec du prochain
bump d'un `Executable doesn't exist at /ms-playwright/...` cryptique côté
`visual-regression` en une erreur explicite et immédiate sur n'importe
quelle PR.

**Effort** : S · **Priorité** : haute (déjà touché le dépôt réel deux fois).

### 2.B 🔴→🟢 Dette `eslint-plugin-sonarjs` jamais gatée malgré la consigne « ne doit pas augmenter »

**Constat** : `PLAN_SOLIDITE_TECHNIQUE.md` Lot 14 documente déjà cette dette
comme « informationnel, jamais traité » (304 findings). Après la passe de
19 findings de PR #466, il en reste 288 — suivi en mémoire long-terme
(`sonarjs-debt-status.md`, `sonarjs-no-increase.md`) avec la consigne
explicite de l'utilisateur : ce chiffre ne doit jamais remonter. Mais
aujourd'hui rien ne l'impose — c'est une règle qui vit uniquement dans un
fichier mémoire, pas dans `check_quality_ratchet.sh`, alors que
vulture/radon/deptry/knip/jscpd le sont tous.

**Pourquoi ça compte** : c'est la seule dette suivie qui n'est *pas*
protégée par un cliquet réel — une régression silencieuse ne serait
détectée que si quelqu'un (humain ou agent) pense à relire la mémoire.

**Action** : ajouter le compte de findings `lint:sonarjs` à
`check_quality_ratchet.sh`, avec la même logique de non-régression que les
5 autres outils (référence actuelle : 288).

**Effort** : S/M · **Priorité** : haute (ferme le dernier trou d'une
philosophie « tout est cliqueté » par ailleurs cohérente).

### 2.C 🟡 Pas de lockfile Python — reproductibilité transitive non garantie — PR #484 mergée, freshness check ajouté

**Constat** : `requirements.txt`/`requirements-dev.txt` épinglent les 55
dépendances directes en `==` exact (vérifié live : 49/55 déjà à la dernière
version PyPI, les 6 autres soit bloquées et documentées soit trop récentes
pour le cooldown de 7 jours), mais rien ne verrouille les transitives — au
contraire du côté npm, reproductible byte pour byte via
`package-lock.json`.

**Pourquoi ça compte** : « ce qui tourne réellement en CI » n'est pas
figé côté Python — deux installations à des instants différents peuvent
résoudre des transitives différentes sans qu'aucun diff ne le montre.

**Fait (PR #484)** : `uv.lock` ne s'applique pas ici — il attend une table
`[project.dependencies]` PEP 621 dans `pyproject.toml`, que ce dépôt n'a
pas (essayé : produit un fichier de 3 lignes, vide). L'outil réel est
`uv pip compile`, l'interface compatible pip-tools d'uv, qui prend
`requirements*.txt` directement. Deux lockfiles générés, calquant le vrai
découpage prod/dev (root `Dockerfile` installe `requirements.txt` seul,
`fast_api_voter/Dockerfile`/`ci-local/backend.Dockerfile` installent les
deux) : `requirements.lock.txt` (58 paquets), `requirements-dev.lock.txt`
(176 paquets). Ajout pur, aucun workflow reconfiguré pour les consommer.

**Fait (cette session, suite)** : un lockfile commité qu'on ne revérifie
jamais dérive silencieusement — exactement la classe de bug que cette
session corrige ailleurs. Ajouté `scripts/check_python_lockfile_freshness.sh`
(informationnel, `continue-on-error`, câblé dans `backend-ci-cd-pipeline.yml`
et `ci-local/backend.Dockerfile`) qui vérifie que chaque pin direct de
`requirements*.txt` apparaît avec la même version dans le lockfile
correspondant — **pas** une re-résolution `uv pip compile` + diff (ça
signalerait une « dérive » à chaque fois qu'une transitive publie un
nouveau patch en amont, sans aucun rapport avec ce dépôt). Détail réel
trouvé en testant : `requirements.txt` épingle `prometheus_client`
(underscore), `uv pip compile` normalise en `prometheus-client` (PEP 503)
— même paquet, même version, pas une vraie dérive ; le script normalise
les noms avant de comparer. Vérifié dans les deux sens (cas qui passe, et
une dérive simulée réellement détectée) avant de committer.

**Fait (suite, même session)** : `backend-ci-cd-pipeline.yml` (le required
check qui gate réellement chaque PR backend) et son miroir
`ci-local/backend.Dockerfile` installent maintenant depuis
`requirements-dev.lock.txt` au lieu de résoudre `requirements*.txt` en
direct — les deux gardés en synchro ensemble dans le même commit
(changer l'un sans l'autre aurait été une nouvelle dérive, pas une
étape sûre). Vérifié avec un run réel complet du miroir `ci-local`
(build `--no-cache`, versions installées confirmées identiques au
lockfile, puis la suite de gating complète — ruff/mypy/pytest+coverage/
benchmarks — passe de bout en bout).

**Reste ouvert** : vérifié précisément (grep, pas une estimation) — 9
autres workflows (`flaky-check-backend.yml`, `atheris-fuzzing.yml`,
`release.yml`, `e2e.yml`, `audit.yml`, `openapi-contract.yml`,
`mutation-testing.yml`, `schemathesis.yml`, `dast.yml`) et 4 autres
`Dockerfile` (`ci-local/e2e.Dockerfile`, `Dockerfile` racine,
`fast_api_voter/Dockerfile`, `fast_api_voter/Dockerfile.prod`) qui
installent encore `requirements*.txt` en direct restent hors scope —
chacun a son propre rayon d'impact à évaluer séparément plutôt qu'un
rebranchement en masse.

**Effort** : S (lockfiles + freshness check, fait) → M (Backend CI +
son miroir, fait) → L (reste des 9 workflows/4 Dockerfile, hors scope)
· **Priorité** : moyenne.

### 2.D 🟢 « Redondance » gitleaks/trufflehog — déjà tranchée, aucune action

**Constat vérifié** : en relisant `audit.yml` et `scripts/audit.sh` en
entier pour un autre item, le commentaire au-dessus du step TruffleHog est
explicite : gitleaks fait du pattern-matching, TruffleHog vérifie les
secrets détectés en LIVE contre l'API du fournisseur (`--results=verified`)
— défense en profondeur délibérée, pas un doublon, déjà documenté comme
tel avec sa justification (« a secret that doesn't actually work is a much
lower-priority finding than one that does »).

**Action** : aucune — retiré de la liste des items ouverts par cette
vérification même.

### 2.E 🟡 L'agent `doc-drift` existe mais ne tourne jamais sur un cycle régulier

**Constat** : deux dérives de documentation réelles trouvées *cette même
session* (le nombre de wheel `cp314` de `pygit2` dupliqué et faux dans 3
fichiers, corrigé PR #481 — trouvé par hasard via `/code-review ultra` sur
un autre commit, pas par une vérification systématique). L'agent
`doc-drift` existe précisément pour ce genre de dérive mais n'a aucun
déclenchement récurrent configuré (`CronList` de cette session : aucun job
programmé).

**Pourquoi ce n'est *pas* un item de code** : `doc-drift` est un agent
Claude Code, pas un script autonome — il ne peut pas être ajouté à
`.github/workflows/` comme un job CI classique sans Claude Code pour
l'exécuter. C'est une recommandation opérationnelle, pas une PR.

**Action** : aucune dans ce plan. Recommandation notée : invoquer
périodiquement l'agent `doc-drift` (par exemple après chaque PR touchant
de la documentation, comme sa propre description le suggère) plutôt que de
compter sur une relecture incidentelle.

---

## 3. Séquencement

Pas de dépendance entre les items. Ordre d'exécution cette session :

1. **2.A** — S, déjà touché le dépôt réel deux fois, prioritaire.
2. **2.B** — S/M, ferme le dernier trou de la philosophie cliquet.
3. **2.C** — S pour l'ajout seul du lockfile ; le rebranchement complet est
   explicitement hors scope aujourd'hui (item ouvert, pas fermé par ce
   plan).
4. **2.D**, **2.E** — pas d'action de code, déjà closes par la
   vérification elle-même.

---

## 4. Vérification — commandes de référence

```bash
# 2.A — vérifier la cohérence de l'image Playwright vs @playwright/test
grep -oP '"@playwright/test":\s*"\^?\K[0-9.]+' voter-app/package.json
grep -oP 'mcr.microsoft.com/playwright:v\K[0-9.]+' .github/workflows/e2e.yml

# 2.B — recompter les findings sonarjs actuels
cd voter-app && npm run lint:sonarjs 2>&1 | tail -5

# 2.C — générer et inspecter le lockfile Python
cd fast_api_voter && uv lock && git diff --stat uv.lock
```
