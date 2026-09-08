# EXP-001 — Heuristique `git blame` pour détecter les commentaires périmés

- **Date** : 2026-09-08 · **Statut** : suspendu · **Coût réel** : ~1h (script + inspection manuelle)
- **Verdict en une phrase** : l'écart temporel `git blame` entre un commentaire et le code qui le suit ne peut rien détecter tant que le dépôt n'a pas assez d'historique — prématuré ici, à réévaluer plus tard.

## Hypothèse de départ

Le [Lot 6.1 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#61--audit-de-pertinence-des-commentaires--l--%E2%AD%90%E2%AD%90-%F0%9F%93%9D%F0%9F%93%9D%F0%9F%93%9D)
propose deux approches pour trouver les commentaires périmés : (a) une
heuristique par `git log`/`git blame` (comparer la date du commentaire à celle
du code qu'il surplombe), (b) une passe LLM sémantique par lot. L'hypothèse
testée ici était que (a), moins chère, suffirait à faire un premier tri avant
d'investir dans (b).

## Protocole

`scripts/audit_stale_comments.py` (introduit dans [PR #316](https://github.com/Burbanit0/Vote-App/pull/316)) :
pour chaque bloc de commentaire/docstring (`#`, `//`, `/* */`, docstrings
Python autonomes) sous `fast_api_voter/api` et `voter-app/src`, `git blame`
la date du bloc et celle de la ligne de code juste après ; flague les paires
dont l'écart dépasse un seuil (1 jour par défaut).

## Ce que ça a trouvé

5 257 paires (commentaire, ligne de code suivante) scrutées ; seulement 4
dépassent un écart d'un jour ; les 4 vérifiées à la main sont des **faux
positifs** — dans chaque cas, la ligne juste après le commentaire a été
retouchée deux jours plus tard pour une raison sans rapport avec ce que dit
le commentaire (le plus souvent : un ajout d'import qui reformate la ligne de
déclaration en dessous), et le commentaire restait exact. Détail par
candidat dans `docs/comment-audit/README.md` (PR #316).

Cause racine : `fast_api_voter/api` et `voter-app/src` datent de quelques
jours (la migration strangler-fig s'est terminée le 2026-09-04) — la plupart
des fichiers n'ont qu'un seul commit qui touche l'essentiel de leurs lignes.
Un commentaire n'a structurellement pas encore eu le temps de dater par
rapport au code qu'il surplombe.

## Ce que ça a coûté

~1h : écriture du script (~150 lignes Python, aucune dépendance externe),
une exécution complète (quelques secondes), inspection manuelle des 4
candidats (`git show` sur le commit responsable de chacun).

## Verdict et pourquoi

**Suspendu, pas rejeté.** L'heuristique elle-même n'a rien de défectueux —
elle mesure exactement ce qu'elle prétend mesurer. Le problème est que la
grandeur mesurée (l'écart temporel `git blame`) n'a pas encore de variance
sur ce dépôt : elle redeviendra utile une fois que le code aura vécu assez
longtemps pour que des commentaires se décorrèlent réellement du code voisin.
Le seuil par défaut du script est documenté comme à remonter en conséquence.

## Ce que j'en retiens (transférable à un autre projet)

Une heuristique fondée sur l'historique git est **aveugle par construction**
sur un jeune dépôt (ou un dépôt fraîchement réécrit/migré) : elle a besoin de
mois de dérive pour produire un signal, quelle que soit la qualité de son
implémentation. Sur un projet jeune, une méthode qui lit le **contenu actuel**
du commentaire et du code (approche (b), LLM ou revue manuelle) trouvera un
commentaire redondant ou déjà faux dès sa première version — elle ne dépend
pas de l'âge du dépôt. Diagnostic à poser tôt : mesurer d'abord la variance
temporelle réelle disponible (`git log --format=%ad` sur le périmètre visé)
avant d'investir dans une heuristique fondée sur le temps.
