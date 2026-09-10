# EXP-001 — Heuristique `git blame` pour détecter les commentaires périmés

- **Date** : 2026-09-08 · **Statut** : adopté (comme filtre, pas comme verdict) · **Coût réel** : ~1h30 (script + deux passes de vérification)
- **Verdict en une phrase** : l'écart temporel `git blame` réduit efficacement l'espace de recherche (5 200 → 329 blocs) mais ne détecte pas la péremption elle-même — sur 5 candidats vérifiés à la main, 5 sont un vrai décalage temporel et 5 sont des vrais négatifs sur la véracité du commentaire.

## Hypothèse de départ

Le [Lot 6.1 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#61--audit-de-pertinence-des-commentaires--l--%E2%AD%90%E2%AD%90-%F0%9F%93%9D%F0%9F%93%9D%F0%9F%93%9D)
propose deux approches pour trouver les commentaires périmés : (a) une
heuristique par `git log`/`git blame` (comparer la date du commentaire à celle
du code qu'il surplombe), (b) une passe LLM sémantique par lot. L'hypothèse
testée ici était que (a), moins chère, suffirait à faire un premier tri avant
d'investir dans (b).

## Protocole

`scripts/audit_stale_comments.py` (introduit dans
[PR #319](https://github.com/Burbanit0/Vote-App/pull/319)) : pour chaque bloc
de commentaire/docstring (`#`, `//`, `/* */`, docstrings Python autonomes)
sous `fast_api_voter/api` et `voter-app/src`, `git blame` la date du bloc et
celle de la ligne de code juste après ; flague les paires dont l'écart dépasse
un seuil (1 jour par défaut).

## Ce que ça a trouvé

**Un premier passage a produit un résultat faux, corrigé avant publication** —
gardé ici parce que le correctif est lui-même l'enseignement transférable de
cette expérience (section finale). Ce premier passage tournait dans un clone
au fetch git tronqué : `git blame` n'y voyait qu'une poignée de commits
récents, donc chaque paire (commentaire, code) semblait dater du même jour ou
presque — 4 candidats sur 5 257 paires, tous avec un écart d'un jour. La
conclusion tirée à l'époque (« le dépôt est trop jeune pour que le signal
existe ») décrivait une limite de l'environnement d'exécution, pas une
propriété du dépôt.

Avec l'historique complet (1 553 commits sur `develop`, remontant à
2025-03-01), le même script sur le même commit donne : **329 candidats
au-dessus du seuil d'un jour** (sur ~5 200 blocs scrutés, soit ~6 %), avec des
écarts réels allant jusqu'à **379 jours**.

**5 candidats vérifiés à la main**, en couvrant le haut du classement et un
échantillon au milieu — détail complet dans
[`docs/comment-audit/README.md`](../comment-audit/README.md) :

| Fichier | Écart | Ce qui a réellement changé |
|---|---|---|
| `fast_api_voter/api/engine/population_simulation.py:9` | 379 j | Reformatage voisin sans rapport — bannière de fichier restée exacte |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py:346` | 219 j | Annotation de type stricte ajoutée (passe mypy) — commentaire resté exact |
| `voter-app/src/types.ts:1` | 253 j | Rien de sémantique — commentaire auto-référentiel (`// src/types.ts`), candidat au retrait pour redondance, pas pour péremption |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py:540` | 174 j | Fonction inchangée ; écart dû à une passe de typage plus tardive ailleurs dans le fichier |
| `fast_api_voter/api/domain/election/__init__.py:164` | 23 j | Marqueur de section toujours exact, bloc de code suivant retouché pour une raison indépendante |

**5/5 sont un vrai décalage temporel, et 5/5 sont des vrais négatifs sur la
péremption.** Dans chaque cas, c'est le **code** qui a bougé pour une raison
sans rapport avec le commentaire (durcissement de types, reformatage, passe
de lint) — jamais l'inverse.

## Ce que ça a coûté

~1h30 au total : ~1h pour l'écriture du script (~270 lignes Python, aucune
dépendance externe) et la première exécution (quelques secondes) ; ~30 min
supplémentaires pour diagnostiquer et corriger le problème d'historique
tronqué, régénérer les résultats, et vérifier 5 candidats à la main
(`git blame -L`/`git log --follow` directs sur chacun).

## Verdict et pourquoi

**Adopté, mais comme filtre de présélection, pas comme détecteur de
péremption.** L'heuristique fait précisément ce qu'un signal temporel peut
faire : réduire ~5 200 blocs à 329 candidats à examiner (~94 % de réduction),
en un temps négligeable et sans dépendance externe. Elle ne fait pas ce
qu'elle ne peut pas structurellement faire : juger si un commentaire décrit
encore fidèlement le code voisin — cela exige de lire le **contenu** des
deux, pas seulement leurs dates. Sur l'échantillon vérifié, sa précision pour
la péremption réelle est de 0/5 ; sa capacité à repérer un vrai décalage
temporel est de 5/5.

**Conséquence pour le Lot 6.1** : la phase 2 applique l'approche (b) — une
passe sémantique, LLM ou revue manuelle — sur les 329 candidats déjà
présélectionnés par (a), pas sur l'ensemble des blocs de commentaire du
dépôt. Les deux approches sont complémentaires : (a) réduit l'espace de
recherche à coût quasi nul, (b) tranche sur le contenu.

## Ce que j'en retiens (transférable à un autre projet)

Deux enseignements distincts, tous deux indépendants des détails de
Vote-App :

1. **Un décalage temporel `git blame` est un bon proxy pour « ce commentaire
   mérite d'être relu », un mauvais proxy pour « ce commentaire est faux ».**
   Il capture surtout du code qui bouge pour des raisons sans rapport
   (typage, style, lint) — pas des commentaires qui divergent sémantiquement
   du code. Une heuristique fondée sur le temps présélectionne ; elle ne
   remplace pas une lecture du contenu.
2. **Vérifier la profondeur réelle de l'historique disponible avant de tirer
   une conclusion d'un outil fondé sur `git log`/`git blame`.** Un clone au
   fetch tronqué (courant dans un environnement CI ou un bac à sable frais)
   produit un signal artificiellement plat qui ressemble exactement à
   « ce dépôt est jeune » — et cette ressemblance est trompeuse précisément
   parce qu'elle est plausible. Un contrôle d'une ligne
   (`git log --oneline | wc -l`, `git rev-parse --is-shallow-repository`)
   avant d'interpréter un résultat fondé sur l'historique aurait évité la
   première conclusion, fausse, de cette expérience.
