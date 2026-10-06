## Demande

<!-- La demande d'origine, mot pour mot (lien vers l'issue ou citation). Pas un résumé écrit après coup. -->

## Description

<!-- Décris les changements apportés et pourquoi -->

## Critères d'acceptation

<!-- Un critère vérifiable par ligne, tiré de la demande. Coche seulement ce qu'une preuve ci-dessous montre. -->

- [ ] C1 —
- [ ] C2 —

## Preuves

<!--
Les commandes lancées et leur résultat réel (dernières lignes utiles), captures pour l'UI.
Le bloc que `/verify` imprime convient tel quel.
-->

**Non vérifié :** <!-- obligatoire : ce qui n'a pas été vérifié et pourquoi ; « rien » seulement si c'est vrai -->

## Type de changement

- [ ] `feat` — nouvelle fonctionnalité
- [ ] `fix` — correction de bug
- [ ] `refactor` — refactoring sans changement de comportement
- [ ] `docs` — documentation uniquement
- [ ] `ci` — CI/CD / pipeline
- [ ] `security` — correctif sécurité
- [ ] `perf` — amélioration de performance

## Checklist

### Code
- [ ] Le code respecte le style existant (pas de console.log, imports inutilisés, etc.)
- [ ] Aucun secret / credential n'est committé (cf. detect-secrets)
- [ ] Les noms de variables et fonctions sont clairs et en anglais

### Tests
- [ ] Les tests existants passent (`npm test` / `pytest`)
- [ ] Des tests ont été ajoutés pour les nouvelles fonctionnalités (si applicable)
- [ ] Le coverage ne régresse pas

### Sécurité
- [ ] `npm run audit:gate` (dans `voter-app/`) passe
- [ ] Les inputs utilisateur sont validés côté backend
- [ ] Aucune dépendance vulnérable ajoutée

### Frontend (si applicable)
- [ ] Testé en mode light et dark
- [ ] Testé en mode Expert et Débutant
- [ ] Testé sur mobile (tableaux responsifs)
- [ ] Aucune régression sur HomePage, PlaygroundPage, LaboratoirePage

### Backend (si applicable)
- [ ] Les nouveaux endpoints coûteux en calcul sont protégés par rate limiting (`check_v2_rate_limit` ou équivalent)
- [ ] Les nouvelles routes sont testées
- [ ] CORS respecté (pas de `*` ajouté)

## Screenshots (si changement UI)

<!-- Avant / Après si pertinent -->

## Notes pour le reviewer

<!-- Informations utiles : décisions architecturales, compromis, points d'attention -->
