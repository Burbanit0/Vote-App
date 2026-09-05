# Prompt — Implémentation Liquid Democracy & Conviction Voting

Copie ce prompt dans Claude Code à la racine du repo Vote-App.

---

Je veux ajouter deux nouveaux mécanismes de gouvernance à Vote Lab, dans le
même esprit que le reste du moteur `backend` (20 enjeux, `pref_voting`,
parité stricte client/backend contrôlée par le golden-fixture harness) :
**Liquid Democracy** et **Conviction Voting**. Les deux doivent être
implémentés comme des simulations de recherche (pas de vote binding réel),
avec des métriques exportables pour analyse.

Avant de coder, lis `THEORY.md` §7.2 et §7.3, `docs/research/traceability.md`
et `docs/research/bibliography.bib` pour le cadrage théorique attendu.

## 1. Liquid Democracy — `fast_api_voter/api/engine/utils/liquid_democracy_utils.py`

**Modèle :**
- N électeurs, chacun a soit un vote direct, soit une délégation vers un
  autre électeur (délégation transitive : A délègue à B qui délègue à C).
- Détection et gestion des cycles de délégation (A→B→A) : un cycle doit être
  cassé et traité comme une abstention collective de ses membres, pas comme
  une erreur silencieuse.
- Le poids d'un délégataire final = 1 (son propre poids) + somme des poids
  de tous ceux qui lui délèguent, transitivement.

**Dynamique temporelle (à simuler sur une séquence de votes, réutilise le
modèle à 20 enjeux de `domain/election`) :**
- Initialisation : chaque électeur choisit soit de voter directement, soit
  un délégué (ex. le voisin le plus proche dans l'espace des enjeux, ou un
  délégué aléatoire pondéré par proximité idéologique).
- À chaque vote : calcule la distance entre la position révélée du délégué
  (son vote effectif sur les enjeux) et le point idéal du délégant. Utilise
  cette distance pour faire évoluer une "dissatisfaction cumulée" par
  électeur (accumulateur type EWMA — exponentially weighted moving average).
- Règle de révocation : probabilité de changer de délégué (ou de repasser en
  vote direct) = fonction logistique de la dissatisfaction cumulée. Expose
  les paramètres (pente, seuil) en configuration.

**Métriques à calculer et exposer :**
- Distribution des poids délégués à chaque pas de temps (pour calculer
  indice de Gini / Herfindahl — objectif : pouvoir reproduire empiriquement
  le phénomène de "super-voters" documenté par Kling et al. 2015 sur des
  données synthétiques).
- "Demi-vie du pouvoir" : nombre de pas de temps nécessaires pour qu'un
  délégué qui vient de décevoir (vote éloigné du délégant) perde 50% de son
  poids délégué.
- Taux de rotation des délégations (churn) dans le temps.

**Tests :** cas simples (chaîne de délégation A→B→C, calcul de poids
attendu), cas de cycle (doit être détecté et neutralisé sans crash), cas
d'évolution sur N pas de temps avec assertions sur la conservation du poids
total (somme des poids = nombre d'électeurs à tout instant).

## 2. Conviction Voting — `fast_api_voter/api/engine/utils/conviction_voting_utils.py`

**Modèle de base (fidèle à l'implémentation 1Hive/Commons Stack) :**
```
conviction(t) = decay · conviction(t-1) + stake(t)
```
où `stake(t)` est le poids actuellement engagé par l'ensemble des électeurs
sur une proposition, et `decay ∈ (0,1)` un paramètre de demi-vie
configurable.

Seuil de passage dynamique, dépendant du montant/pouvoir demandé par la
proposition relativement au total disponible — plus la demande est
importante, plus le seuil devient difficile à atteindre (fonction convexe,
tend vers l'infini à l'approche d'un plafond `max_ratio` configurable).
Implémente une fonction `compute_threshold(requested_amount, total_funds,
max_ratio, decay, weight)` séparée et testée indépendamment de
`update_conviction`.

**Extension recherche — accountability continue d'un représentant :**
En plus du cas d'usage standard (financement de proposition), implémente une
variante où la "proposition" est *le maintien en fonction d'un représentant
élu* : les citoyens allouent en continu un stake de soutien ; si la
conviction accumulée du représentant chute sous un seuil (ou si un
challenger dépasse la conviction du titulaire), déclenche un événement
`recall_triggered`. Documente explicitement cette variante dans THEORY.md
comme une extension originale de Vote Lab et non comme le modèle original
1Hive — ne pas citer `commons_stack_1hive2019` pour cette partie spécifique
sans le préciser.

**Tests :** convergence de la conviction vers `stake / (1-decay)` en régime
stationnaire, décroissance exponentielle après retrait du stake, non-passage
d'une proposition dont le seuil dépasse le max_ratio quel que soit le stake.

## 3. Contraintes transverses

- Respecte les conventions existantes : typage strict (mypy strict), Ruff,
  docstrings au format du reste du repo, pas de dépendance nouvelle sans
  justification.
- Les deux modules doivent exposer une fonction `run_simulation(...)` qui
  retourne une structure sérialisable (dict/dataclass) prête pour le
  front-end (séries temporelles de poids/conviction) — cohérent avec le
  reste de `engine/utils`.
- Une fois l'implémentation stable, lance `/sync-theory` pour vérifier la
  cohérence avec `THEORY.md`, `traceability.md` et `bibliography.bib`, et
  passer les entrées `prévu` → `implémenté`.
- N'ajoute aucune référence académique qui ne soit pas déjà dans
  `bibliography.bib` ou explicitement validée par moi.
