# Plan — Remédiation CI/CD post-PLAN_SOLIDITE_TECHNIQUE

> **Origine** : audit CI/CD complet demandé le 2026-09-13, à la clôture de
> `PLAN_SOLIDITE_TECHNIQUE.md`. État vérifié **en direct** (API GitHub via
> `gh`, lecture réelle des workflows, `gh run list` sur les 40-100 derniers
> runs) — pas un résumé de documentation. Deux agents dédiés ont mené l'audit
> en parallèle : l'un a extrait les items CI/CD des Lots 6-14 du plan de
> solidité, l'autre a vérifié l'état réel du dépôt (protection de branche,
> Dependabot, Mergify, cliquet qualité, mutation testing, `release.yml`,
> `ci-local/`).
>
> Légende de statut : 🔴 pas fait / ouvert · 🟡 dette documentée, non
> bloquant · 🟢 fait/résolu.
>
> **Portée** : ce plan ne couvre que ce que l'audit a trouvé de concret sur
> l'état *actuel* du pipeline — pas une nouvelle exploration d'outils. Chaque
> item est indépendant, une branche `feat/*` + une PR par item contre
> `develop`, merge `--no-ff`, comme le mandate `CLAUDE.md`.

---

## 1. Constat général

Le pipeline est globalement sain : les quatre checks requis (Backend,
Frontend, Playwright E2E, Generated artifacts in sync) sont verts sur
l'essentiel de l'activité récente sur `develop`, Dependabot/Mergify
fonctionnent comme prévu (0 PR ouverte, historique propre), et le cliquet
qualité (`.github/quality-baseline.json`) est cohérent avec ce que le script
calcule réellement.

L'audit a trouvé **6 items concrets** qui méritent une action — le 6e
(`ci-local` désynchronisé, §2.6) ajouté après une vérification en direct de
« le mirroir local est-il à jour ? » — et confirme **2 items de dette déjà
connus et volontairement différés** (Lot 14 du plan de solidité, non repris
ici en détail).

---

## 2. Items à traiter, par priorité

### 2.1 🔴 Le cliquet mutation testing (mutmut) échoue en silence

**Constat** : sur les 15 derniers runs de `mutation-testing.yml`, le job
`Backend mutation score (mutmut, floor 70%)` a échoué **9 fois** à l'étape du
seuil. Stryker (frontend, seuil 80%) passe à chaque run — ce n'est donc pas
un problème d'outillage, c'est une vraie régression de couverture de
mutation sur `simulation_ranked_utils.py`/`simulation_score_utils.py`. Le
job n'est délibérément pas un check requis (règle du skill `voter-ci` : un
check requis sur un workflow qui ne tourne jamais en PR bloque la PR pour
toujours), donc personne ne le voit passer au rouge.

**Pourquoi ça compte** : c'est exactement le gate que le Lot 5 du plan de
solidité a mis en place pour éviter un score de mutation qui se dégrade sans
bruit sur le moteur — et c'est en train de faire ce que le plan voulait
éviter.

**Action** : lancer `mutmut run` en local sur les deux fichiers, identifier
les mutants qui survivent maintenant et ne survivaient pas avant (probable
lien avec les PR récentes de décomposition — `feat/decompose-start-monte-carlo`,
`feat/decompose-democratic-backsliding-worker`, cf. git log). Soit ajouter
les tests qui tuent ces mutants, soit documenter explicitement pourquoi le
seuil doit baisser (jamais en douce — même logique que le cliquet qualité :
un changement de seuil se commit avec sa justification).

**Effort** : M · **Priorité** : haute (dette qui grossit sans alarme).

### 2.2 🔴 Dérive de la protection de branche `develop` (`strict`)

**Constat** : `gh api repos/Burbanit0/Vote-App/branches/develop/protection`
renvoie `required_status_checks.strict: false` ; `scripts/setup-branch-protection.sh`
configure `strict: true`. Tout le reste correspond exactement (12 contexts
requis, 0 review obligatoire, pas de force-push). Le plan de solidité
mentionne que Mergify a un jour signalé `strict` comme incompatible avec sa
queue — mais rien ne documente si la désactivation est le choix final ou un
correctif temporaire jamais revisité.

**Pourquoi ça compte** : `strict: false` veut dire que des PR peuvent merger
sans être à jour avec `develop` — exactement le problème que la queue
Mergify est censée résoudre structurellement (cf. Lot 1 du plan de
solidité). Si c'est un choix définitif, il doit être écrit quelque part
(commentaire dans `setup-branch-protection.sh` ou le skill `release`) ; sinon
il faut réactiver `strict` et vérifier que ça ne recasse pas la queue.

**Action** : trancher, puis soit mettre à jour le script pour refléter l'état
voulu, soit relancer `setup-branch-protection.sh` et vérifier qu'un run
Mergify réel passe toujours derrière.

**Effort** : S · **Priorité** : haute (protection de branche = garde-fou
silencieux, une dérive ici n'affiche aucune erreur).

### 2.3 🔴 `release.yml` taguerait l'état obsolète de `main`

**Constat** : le job `release` fait un `checkout` explicite sur `ref: main`
avant de bump la version, créer le tag et pousser — sans jamais fusionner ou
fast-forward `develop` dedans. Les jobs CI/E2E qui le précèdent tournent sur
la ref qui a déclenché le `workflow_dispatch` (vraisemblablement `develop`),
mais le commit de release, lui, part de `main`. `main` traîne encore
~750 commits de retard.

**Pourquoi ça compte** : déclencher ce workflow aujourd'hui « publierait »
une version taguée de l'ancien `main`, pas de l'état réel du projet — un
piège silencieux au moment précis où on a le moins envie d'improviser (une
release).

**Action** : vérifier ce que documente réellement le skill `release` sur
l'étape manuelle de fast-forward `develop → main` avant dispatch ; si elle
existe mais n'est qu'une note humaine, envisager un garde-fou dans le
workflow lui-même (ex. un step qui échoue si `main` n'est pas un ancêtre
direct de `develop` au moment du dispatch).

**Effort** : S (vérif) → M (si garde-fou ajouté) · **Priorité** : haute mais
non urgente (aucune release n'est prévue immédiatement — à traiter **avant**
la prochaine, pas dans l'heure).

### 2.4 🟡 Trigger `merge_group` mort dans `audit.yml`

**Constat** : `audit.yml` déclenche sur `merge_group:`, mais
`gh api repos/Burbanit0/Vote-App/rulesets` renvoie `[]` (aucune ruleset
GitHub native) et `gh run list --event merge_group` ne renvoie aucun run,
jamais. Mergify est une queue tierce, pas le mécanisme natif `merge_group` —
ce trigger n'a donc probablement jamais eu de raison de se déclencher.

**Action** : soit confirmer qu'il ne sert à rien et le retirer, soit
documenter pourquoi il reste (ex. migration future vers une merge queue
native).

**Effort** : S · **Priorité** : basse (config morte, pas un risque actif).

### 2.5 🟡 Documentation obsolète — la « bonne nouvelle » du changement de
branche par défaut n'est pas actée

**Constat** : `mutation-testing.yml`, `schemathesis.yml`,
`flaky-check-backend.yml`, `atheris-fuzzing.yml` (et le skill `voter-ci`)
affirment tous que leurs triggers `schedule`/`workflow_dispatch` se
résolvent contre `main`, branche par défaut du dépôt et distante de ~750
commits — rendant ces triggers inertes en pratique. **C'est aujourd'hui
faux** : `gh api repos/Burbanit0/Vote-App --jq .default_branch` renvoie
`develop`. La bascule a déjà eu lieu. Preuve en direct : le `schedule` de
`flaky-check-backend.yml` a tourné et réussi le 2026-09-12, et le
`workflow_dispatch` d'`atheris-fuzzing.yml` a tourné et réussi le
2026-09-11.

**Action** : mettre à jour les commentaires dans les 4 fichiers de workflow
et le skill `voter-ci` pour refléter l'état réel (branche par défaut =
`develop`, triggers `schedule`/`workflow_dispatch` fonctionnels) — sinon la
prochaine personne (humaine ou agent) qui lit ces fichiers croit résoudre un
problème déjà résolu.

**Effort** : S · **Priorité** : basse (aucun impact fonctionnel, seulement
un risque de travail en double futur).

### 2.6 🔴 `ci-local/` a dérivé — trois gates réels absents du mirroir Docker

**Constat** : vérifié en diffant chaque Dockerfile/script contre le workflow
GitHub qu'il prétend reproduire, au-delà des 3 écarts déjà documentés dans
`ci-local/README.md` (couverture 85%/90%, `pip-audit` non-bloquant en local,
`image-scan`/`code-quality`/CodeQL absents) :

| Écart | CI réelle | Mirroir `ci-local/` | Documenté ? |
|---|---|---|---|
| License compliance (Lot 6.7) | step bloquant dans `backend-ci-cd-pipeline.yml` **et** `frontend-ci-cd-pipeline.yml` | **absent** de `backend.Dockerfile` et `frontend.Dockerfile` | ❌ |
| Webkit en E2E (Lot 7) | `playwright install --with-deps chromium firefox webkit` | `e2e.Dockerfile` n'installe que `chromium firefox` | ❌ |
| Règles Semgrep custom (Lot 2) | `audit.yml` passe `--config=.semgrep/vote-app-rules.yml` | absent de la commande Semgrep dans `audit-ci.sh` | ❌ |

Effet concret : un run `ci-local` tout vert aujourd'hui ne détecterait ni une
violation de licence, ni un vrai bug WebKit-only, ni une violation des deux
règles Semgrep écrites spécifiquement pour ne pas répéter les bugs du 06/09
— exactement la classe de problème que `ci-local` existe pour attraper.

Trouvaille annexe, cosmétique seulement : le commentaire d'en-tête
d'`audit.Dockerfile` affirme que Trivy est « informational, non-gating »,
alors qu'`audit-ci.sh` juste en dessous le fait bien gater (`exit "$fail"`)
— comportement correct, commentaire à corriger.

**Action** : ajouter les 3 steps/flags manquants (mécanique — copier
l'invocation exacte du workflow réel), corriger le commentaire
`audit.Dockerfile`, et ajouter ces 3 nouveaux écarts à la section « Fidelity
caveats » du README au fur et à mesure qu'ils sont fermés (ou dès maintenant
si un écart est jugé acceptable à garder).

**Effort** : S · **Priorité** : haute (un mirroir de confiance qui ne
détecte pas 3 gates réels est pire qu'un mirroir absent — il donne un faux
sentiment de sécurité).

---

## 3. Dette déjà connue, volontairement différée (rappel, pas une nouveauté)

Ces deux items viennent du Lot 14 de `PLAN_SOLIDITE_TECHNIQUE.md`, où ils
sont explicitement marqués non urgents (« rien ici n'est bloquant, chaque
ligne peut attendre indéfiniment sans risque ») — repris ici seulement pour
mémoire, aucune action proposée :

- **Cliquet type-coverage** (`--at-least`) jamais câblé comme gate — 280
  `any` non typés restants.
- **Dette `eslint-plugin-sonarjs`** — 304 findings, informationnel
  uniquement, jamais traité.

---

## 4. Séquencement recommandé

Pas de dépendance stricte entre les items — ils peuvent partir en parallèle
comme le permet la règle du plan de solidité (2-3 items ouverts max pour
éviter l'invalidation en cascade des PR). Ordre suggéré par rapport
risque/effort :

1. **2.2** (protection de branche) — S, silencieux, à trancher vite.
2. **2.6** (`ci-local` désynchronisé) — S, mécanique, corrige un faux
   sentiment de sécurité dès maintenant.
3. **2.4** puis **2.5** — S chacun, sans risque, bon échauffement.
4. **2.1** (mutmut) — M, demande une vraie investigation du moteur.
5. **2.3** (`release.yml`) — à traiter avant la prochaine release, pas dans
   l'urgence immédiate si aucune n'est planifiée.

---

## 5. Vérification — commandes de référence

```bash
# 2.1 — reproduire le score de mutation en local
cd fast_api_voter && mutmut run && mutmut results

# 2.2 — état réel de la protection de branche
gh api repos/Burbanit0/Vote-App/branches/develop/protection | jq '.required_status_checks.strict'

# 2.3 — vérifier l'ancêtre commun avant tout dispatch de release.yml
git merge-base --is-ancestor main develop && echo "main est bien un ancêtre de develop"

# 2.4 — historique du trigger merge_group
gh run list --event merge_group --limit 20

# 2.5 — confirmer la branche par défaut actuelle
gh api repos/Burbanit0/Vote-App --jq .default_branch

# 2.6 — vérifier que les 3 gates manquants sont bien absents du mirroir local
grep -c "license" ci-local/backend.Dockerfile ci-local/frontend.Dockerfile   # attendu: 0 avant fix
grep "playwright install" ci-local/e2e.Dockerfile                            # attendu: sans webkit avant fix
grep "vote-app-rules" ci-local/audit-ci.sh                                   # attendu: aucun résultat avant fix
```
