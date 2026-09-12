# Journal de bord — Archive 2025 (reconstruction rétroactive)

> Entrées 2025-03-01 → 2026-01-13 (la genèse du projet, jusqu'à la reprise
> qui suit trois mois de pause), déplacées hors de
> [`../JOURNAL_DE_BORD.md`](../JOURNAL_DE_BORD.md) lors de sa rotation
> (Lot 12.2, `PLAN_SOLIDITE_TECHNIQUE.md`, 2026-09-11). Toutes reconstruites
> a posteriori le 2026-08-19 (voir l'entête de chaque entrée) — ce ne sont
> pas des entrées écrites en temps réel. Entrées plus récentes :
> [`JOURNAL_2026.md`](./JOURNAL_2026.md) et le
> [journal actif](../JOURNAL_DE_BORD.md).

---

## 2025-10-29 → 2026-01-13 — Reprise brève après une pause de trois mois

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all`.

**Contexte du jour.** Reprise du projet après une interruption d'environ trois mois et demi (dernier commit le 2025-07-04, reprise le 2025-10-29).

**Ce qui a avancé**
- Ajustements ponctuels du backend (nouvelles routes, image Docker) et du frontend.
- Amélioration de la couverture de tests et du CI/CD backend.
- Une entrée de TODO ajoutée (`cbdff9f add todo and solve issues`), dernier commit avant une nouvelle pause de plus de trois mois (jusqu'au 2026-05-03).

**Points bloquants**
- Non documentés.

**Décisions prises**
- Aucune retrouvée dans l'historique.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet)

**Pour aller plus loin** : `git log` entre `2b6cadb` et `cbdff9f`.

---

## 2025-03-01 → 2025-07-04 — Vote-App v1 : une application de vote (MVP Flask/React)

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all` (commits du tout premier au dernier avant la pause d'été 2025). Les messages de commit de cette période sont courts et ne documentent pas le raisonnement — cette entrée reste donc au niveau du "quoi", pas du "pourquoi", faute de source.

**Contexte du jour.** Démarrage du projet : une application de vote électronique classique (élections, candidats, votants, résultats) avec un backend Flask et un frontend React.

**Ce qui a avancé**
- CRUD élections/candidats/votants, table `Election`, routes API de base.
- Méthodes de dépouillement : majorité simple, vainqueur de Condorcet, deux tours.
- Premier moteur de "simulation" (interaction votants/candidats).
- Mise en place de la CI/CD (lint, tests) sur backend et frontend, séparément.
- Système de rôles utilisateur (organisateur/votant/candidat), pages de profil.

**Points bloquants**
- Non documentés à cette échelle temporelle — aucune trace écrite des difficultés rencontrées.

**Décisions prises**
- Aucune décision d'architecture motivée n'est retrouvable dans l'historique de cette période — les commits sont factuels, sans justification écrite.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet)

**Pour aller plus loin** : `git log` du repo entre les commits `5794f7c` et `7d8284c`.
