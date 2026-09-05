# Prompt — Mise en place du mutation testing (mutmut)

Copie ce prompt dans Claude Code à la racine du repo Vote-App.

---

Je veux introduire du **mutation testing** sur Vote-App avec `mutmut`, pour
vérifier que la couverture de tests existante détecte réellement des
régressions — pas juste qu'elle exécute le code. C'est un chantier
complémentaire à celui des invariants Hypothesis déjà en place
(`test_hypothesis_condorcet.py`, `test_hypothesis_monotonicity.py`,
`test_hypothesis_legitimacy.py`) : Hypothesis vérifie que les propriétés
théoriques tiennent sur des entrées générées, mutmut vérifie que si le
code *cassait*, un test le remarquerait.

**Discipline non négociable, comme pour le chantier Hypothesis** : si un
mutant survit (aucun test ne le détecte), la réaction par défaut n'est
**jamais** d'écrire un nouveau test ad hoc juste pour tuer ce mutant
spécifique sans réflexion. Pour chaque mutant survivant, détermine et
documente lequel des trois cas s'applique :
1. **Trou de test réel** — le code a un comportement testable qui n'est
   couvert par aucune assertion actuelle → écrire le test qui manque, en
   expliquant quel invariant ou comportement métier il protège.
2. **Mutant équivalent** — la mutation ne change aucun comportement
   observable (ex. `<=` → `<` sur une branche jamais atteinte avec égalité
   possible) → documenter pourquoi dans un fichier d'exclusions, pas dans
   le code de test.
3. **Signal réel de dette** — le mutant survit parce que le code testé est
   mort, non spécifié, ou que la fonction fait plus que ce que son nom
   indique → signaler-le mais ne pas corriger silencieusement sans mon
   accord, ce chantier est un audit, pas une session de refactoring.

Ne "corrige" jamais un test pour le faire passer sans avoir d'abord compris
pourquoi il échouait face au mutant.

## 1. Installation et configuration de base

- Ajoute `mutmut` à `requirements-dev.txt` (version épinglée, pas de
  caret/tilde flottant — cohérent avec la convention déjà en place pour
  `hypothesis==6.165.10`).
- Crée un fichier de configuration `setup.cfg` ou `pyproject.toml`
  (`[tool.mutmut]`) qui limite explicitement le périmètre aux deux fichiers
  suivants pour cette première passe — **pas tout le repo** :
  - `fast_api_voter/api/engine/utils/simulation_ranked_utils.py`
  - `fast_api_voter/api/domain/theory/workers.py`

  Exclus explicitement, pour cette première passe :
  - tout `fast_api_voter/api/domain/polity/` (module encore v0, code trop
    instable pour que la mutation testing apporte un signal utile
    maintenant)
  - tout fichier de test lui-même

## 2. Baseline avant tout seuil

Ne fixe **aucun seuil de score de mutation a priori**. Lance une première
passe complète sur les deux fichiers ciblés, et rapporte :
- nombre total de mutants générés
- nombre tués / survivants / mutants équivalents identifiés (timeout inclus,
  à distinguer des vrais survivants)
- temps d'exécution total de la passe complète

C'est cette mesure de baseline qui doit servir à fixer un seuil réaliste
ensuite — pas l'inverse. Présente-moi ces chiffres avant de proposer un
seuil cible.

## 3. Intégration CI — job séparé, non bloquant

Crée un workflow CI **distinct** du pipeline principal (`mutation-testing.yml`
ou équivalent selon la plateforme CI déjà en place dans le repo) :
- déclenché **manuellement** (`workflow_dispatch`) et en **cron
  hebdomadaire**, jamais sur chaque push/PR
- **non bloquant** : rapporte le score en artefact/résumé de run, mais ne
  fait jamais échouer le build
- n'interfère pas avec le pipeline principal existant (Ruff, mypy strict,
  Bandit, Semgrep, la suite pytest+coverage) : à faire tourner en parallèle,
  pas en remplacement ni en prérequis

## 4. Ce que je veux en sortie de cette première passe

- Le diff de configuration (`requirements-dev.txt`, config mutmut, fichier
  de workflow CI), présenté avant application, comme pour le chantier
  précédent.
- Le rapport de baseline (§2), brut, sans interprétation prématurée.
- Pour chaque mutant survivant : sa classification (1/2/3 ci-dessus) avec
  une ligne d'explication — pas de correction de code appliquée sans mon
  accord explicite, même si la correction semble triviale.
- Une proposition de seuil de score de mutation pour ce périmètre précis,
  basée sur la baseline observée, pas sur un chiffre générique du type
  "80% c'est la norme".

## 5. Contraintes transverses

- Respecte les conventions existantes : typage strict (mypy strict), Ruff,
  pas de dépendance nouvelle non justifiée au-delà de `mutmut` lui-même.
- Travaille sur une branche séparée (`feat/mutation-testing`), depuis
  `develop`.
- Ne touche à aucun fichier hors du périmètre listé en §1 dans cette
  première passe — même si tu repères des mutants potentiellement
  intéressants ailleurs. Signale-les pour une passe future plutôt que
  d'élargir le scope en cours de route.
