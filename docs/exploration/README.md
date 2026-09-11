# Index des verdicts

Le livrable partageable de l'exploration outillage/pratiques du
[plan de solidité technique](../../PLAN_SOLIDITE_TECHNIQUE.md) (Lot 0.3) :
« j'ai essayé ~25 outils de qualité sur un vrai projet, voilà lesquels ont
trouvé quelque chose ». Un rejet argumenté vaut autant qu'une adoption —
souvent plus, parce que personne ne publie ses rejets.

Une entrée par expérience close, gabarit dans [`TEMPLATE.md`](./TEMPLATE.md),
rédigée via `/log-experiment`.

| EXP | Outil | Domaine | Verdict | Trouvailles réelles | Coût |
|---|---|---|---|---|---|
| [001](./EXP-001-audit-commentaires-heuristique-git-blame.md) | Heuristique `git blame` (staleness) | Audit de commentaires (Lot 6.1) | Adopté (comme filtre) | 329/~5 200 blocs présélectionnés (écarts jusqu'à 379j) ; 5 vérifiés à la main, 5/5 vrai décalage temporel mais 0/5 péremption réelle — bon proxy pour « à relire », mauvais pour « c'est faux » | ~1h30 |
| [002](./EXP-002-z3-formal-voting-proofs.md) | Z3 (solveur SMT) | Preuves formelles du moteur de vote (Lot 4.6) | Adopté (partiel) | Minimax/Schulze : critère de Condorcet prouvé pour TOUS les électorats jusqu'à n=7 (pas un échantillon). IRV : 1er encodage silencieusement faux (règle de départage omise), corrigé seulement en croisant un contre-exemple déjà connu — puis a trouvé un contre-exemple à 7 bulletins prouvé minimal | ~3h |
| [003](./EXP-003-couverture-runtime-e2e.md) | `coverage.py` + Istanbul (`vite-plugin-istanbul`) sous Playwright | Couverture *runtime* e2e (Lot 6) | Adopté (script manuel, pas de gate CI) | Backend 34 % exécuté en e2e vs 91,56 % unitaire ; frontend 63 % vs 87,05 %. `api/domain/polity/*` (2 813 lignes, ~19 % du backend) : 0 % e2e, ~99 % unitaire, aucune route enregistrée. `/simulation/compare` : page retirée du routage, backend + hook frontend toujours testés à 100 % unitaire, invisibles à `knip` (import satisfait par leur propre test) | ~5h |
| [004](./EXP-004-regression-visuelle-playwright-screenshots.md) | Playwright `toHaveScreenshot` (Docker épinglé) vs Lost Pixel | Régression visuelle (Lot 7) | Adopté (gate CI, job séparé) | Lost Pixel écarté sans essai (dépôt archivé, équipe partie chez Figma, avril 2026). Détecteur vérifié contre une régression injectée : une tolérance `maxDiffPixelRatio: 0.01` choisie « par prudence » laissait passer un marqueur mal coloré (0,07 % des pixels) — supprimée, la même injection échoue alors proprement (303px, ratio 0,01). `ParliamentCanvas` sans backend affiche un état d'erreur permanent, pas une carte légèrement différente — backend ajouté au job CI. Un flash de légende intermittent (~1 échec/3 runs) tracé à un race React Strict-Mode-dépendant, corrigé par une attente de son cycle de vie fixe. 8/8 runs natifs + 6/6 Docker, zéro échec | ~5h |
