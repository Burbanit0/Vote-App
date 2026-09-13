# Prompt — Montée du seuil de couverture + introduction de Hypothesis

> À utiliser avec Claude Code, à la racine du repo Vote-App, sur `develop`
> (ou une branche dédiée `feat/test-hardening`). Deux chantiers menés en
> parallèle mais livrés séparément, sans casser la CI existante.

---

## Contexte

Je veux (1) faire monter le seuil de couverture minimum (actuellement
30% côté backend et frontend) de façon progressive, sans casser la CI
d'un coup, et (2) introduire le property-based testing (Hypothesis) sur
les invariants théoriques les plus forts du projet — pas au hasard, en
priorisant ce que la théorie garantit toujours, indépendamment de
l'entrée.

## Partie A — Montée progressive du seuil de couverture

1. **Mesure d'abord l'état réel**, module par module (pas juste le
   chiffre global actuel) : génère un rapport de couverture détaillé
   (`pytest --cov --cov-report=term-missing` côté backend, équivalent
   Vitest côté frontend) et identifie les modules les plus en dessous du
   seuil actuel — en particulier tout ce qui est sous `domain/polity/`,
   qui grossit vite et mérite un regard séparé.
2. **Propose un seuil différencié**, pas un seul chiffre global si
   `pytest-cov`/la config actuelle le permet : un seuil pour le cœur
   moteur de vote (déjà mature, peut monter plus vite), un seuil séparé
   et probablement plus bas au départ pour `domain/polity/` (plus jeune,
   à faire monter progressivement à mesure que le module se stabilise).
3. **Propose un palier immédiat réaliste** (pas un saut à un chiffre
   ambitieux) — base-toi sur l'état réel mesuré à l'étape 1, pas sur une
   cible arbitraire. Documente le palier suivant visé et la condition
   pour y passer (ex. "prochaine révision une fois le lot 5 du dev-plan
   v0 terminé").
4. Ne modifie aucun test existant pour "gonfler" artificiellement la
   couverture (ex. des tests qui exécutent du code sans assertion
   significative) — priorise l'ajout de vrais tests sur les zones
   identifiées comme sous-couvertes à l'étape 1.

## Partie B — Introduction de Hypothesis sur les invariants théoriques

Ajoute `hypothesis` aux dépendances de dev backend. Priorise les
invariants dans cet ordre (du plus fort théoriquement au plus
spécifique) :

1. **Conservation du poids en délégation liquide**
   (`liquid_democracy_utils.py`, si déjà implémenté suite au prompt
   précédent — sinon, prépare le test en parallèle de l'implémentation) :
   pour tout graphe de délégation généré aléatoirement (y compris avec
   cycles), la somme des poids doit toujours égaler le nombre d'électeurs.
2. **Critère de Condorcet** : pour tout profil de préférences généré
   aléatoirement contenant un vainqueur de Condorcet, vérifie que
   Schulze, Copeland et Minimax le désignent tous comme vainqueur.
3. **Monotonicité** : pour les méthodes qui la garantissent
   théoriquement (Plurality, Approval — vérifie dans `THEORY.md`/
   `traceability.md` lesquelles sont concernées avant d'écrire le test),
   améliorer la position d'un candidat dans un profil généré ne doit
   jamais le faire perdre, toutes choses égales par ailleurs.
4. **Bornes de `legitimacy_capital` `L(t)`** (`legitimacy.py`, module
   polity) : pour toute séquence d'événements générée (scandales,
   soutien, écart), `L(t)` doit rester dans les bornes définies par la
   config (`recall_floor`, etc.) à chaque pas de temps.
5. **Conservation du nombre de sièges** (D'Hondt/Sainte-Laguë, une fois
   implémentés) : pour toute distribution de votes générée, la somme des
   sièges attribués doit toujours égaler `assembly_seats`, quel que soit
   le nombre de partis ou la répartition des voix.

Pour chaque invariant :
- Écris la propriété comme un test Hypothesis (`@given(...)`), avec des
  stratégies de génération bornées de façon réaliste (ex. nombre
  d'électeurs, de candidats — pas des valeurs qui n'ont pas de sens dans
  le domaine).
- Si Hypothesis trouve un contre-exemple, ne "corrige" pas
  silencieusement le test pour le faire passer — présente le
  contre-exemple minimisé (`hypothesis` le réduit automatiquement au cas
  le plus simple) et demande-moi si c'est un vrai bug ou une limite
  connue et acceptée de l'implémentation actuelle.
- Documente chaque invariant testé dans `traceability.md` (colonne
  Statut : `implémenté` avec test dédié, pas seulement `partiel`).

## Contraintes transverses

- Respecte les conventions existantes (mypy strict, Ruff, docstrings).
- Ne modifie aucun fichier sans présenter le diff pour validation
  d'abord, comme d'habitude sur ce projet.
- Vérifie que l'ajout de Hypothesis n'allonge pas excessivement le temps
  de CI (limite le nombre d'exemples générés par test via
  `@settings(max_examples=...)` si nécessaire, documenté avec la
  justification du chiffre choisi).

## Sortie attendue

1. Rapport de couverture actuel, module par module.
2. Proposition de seuils différenciés + palier immédiat, en diff sur la
   config CI concernée.
3. Les tests Hypothesis proposés pour les invariants 1 à 5 (ou ceux déjà
   implémentables selon l'état actuel du code), en diff.
4. Tout contre-exemple trouvé par Hypothesis, signalé clairement comme
   tel, pas corrigé sans validation.
