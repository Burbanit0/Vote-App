# Journal de bord — Vote-App / La Fourmilière

> Une entrée par session de travail significative, la plus récente en
> haut. Objectif : raconter l'histoire du projet au jour le jour — ce qui
> avance, ce qui bloque, les décisions prises — pour soi-même en
> relecture, et pour pouvoir reprendre le contexte facilement dans une
> autre conversation. Rédigé via le sub-agent `journal-writer` (commande
> `/log-session`), toujours en proposition avant application.

---

## 2026-08-29 — Le chantier distribution se referme, et découvre en sortant que la configuration livrée ne peut pas tenir d'élection

**Contexte du jour.** Suite directe de l'entrée du 24/08 : la chaîne causale seed=42 était fermée (positions `uniform` + priorités individualisées favorisent structurellement le Blanc au second tour), mais la décision de corriger restait entièrement ouverte, et la réécriture de `THEORY.md` §10.10 non commitée. Objectif de la période : trancher et implémenter le correctif, le faire vivre sous charge LLM réelle, et fermer le chantier distribution proprement.

**Ce qui a avancé**
- **Phases 1 à 4 du plan (`plan-distribution-positions-seeds.md`), exécutées dans l'ordre prescrit.** Phase 1 : décision théorique écrite *avant* tout chiffre de sweep — structure factorielle à bas rang à 2 facteurs (`factor_structure`) retenue contre une gaussienne simple (ne corrèle pas les 20 dimensions) et contre un mélange gaussien (présupposerait la polarisation que la vue méso existe pour observer) ; `n_factors=2` reprend les axes économique/sociétal déjà nommés au §14.2 du plan de conception. Phase 2 (`918377e`) : implémentée en opt-in, sweep 40 graines contre le vrai `generate_population` — 0/40 victoires du Blanc, corrélation inter-dimensions réaliste (0,539), variance seed-à-seed préservée. Phase 3 (`a3ebfa9`) : bascule du défaut livré ; découverte non anticipée que plusieurs tests dépendaient implicitement de `uniform` (séquence RNG de v4 Lot 2, seuils calibrés empiriquement pour la porte d'éveil/mobilisation/pétition) — épinglés explicitement sur `uniform` plutôt que corrigés en masse. Phase 4 (`98dbdd3`) : quatre sondes déterministes bon marché rejouant les configurations déjà publiées (both, mobilization_only, electoral_only, v6b) → décision de ne pas relancer les bras LLM au complet, le signal déterministe restant suggestif mais pas conclusif.
- **Le run d'acceptance v6b sous le nouveau défaut a échoué deux fois avant d'aboutir**, sur `cast_votes` (dt=1), troncature `finish_reason='length'` au budget exact (13 596 tokens = 1596 + allowance 12000). Diagnostiqué au niveau de la réponse brute, pas par inférence : la règle du prompt (« classe les positions des candidats acceptables du plus proche au plus éloigné ») est ambiguë entre « classer tous les acceptables » et « classer, c'est-à-dire choisir, le plus proche » — le modèle trouve la bonne réponse en ~1500 caractères puis boucle ~62 000 caractères à re-citer la règle sans jamais émettre de JSON (Mode A, pas Mode B : le budget avait déjà grimpé 4000→8000→12000, une cinquième valeur n'aurait fait que déplacer le plafond). `factor_structure` ne crée pas l'ambiguïté, elle augmente la fréquence de la condition qui la déclenche : la part d'électeurs à ≥2 candidats acceptables passe de 62 % à 88 %.
- **Correctif implémenté et vérifié en direct** (`13e4a14`) : une phrase explicite imposant que `ranking` porte *chaque* candidat acceptable, jamais le seul plus proche. Testé en stress sur les 4 électeurs les plus difficiles identifiés (25 appels, 0 boucle) avant de relancer le run complet.
- **Piège d'outillage réel découvert et documenté à part** (README `llm_test_harness`) : l'endpoint `/v1` d'Ollama renvoie le contenu `<think>` dans `message.reasoning`, un champ séparé de `message.content`, que ni `_extract_content` ni `_extract_native_content` ne lisent — les deux lèvent sur `finish_reason` avant même de regarder le message. Une exception de troncature ne porte donc aucun raisonnement ; toute future investigation de ce type doit dumper le corps JSON entier.
- **Le run complet a confirmé, honnêtement, que le fix n'est pas la cause unique** : sur ~1822 appels, 11 troncatures (0,6 %, contre 6-7 % estimé au diagnostic), toutes absorbées au premier retry — mais 2 sur 11 tombent sur `chamber_deliberation` (dt=11), un prompt jamais touché par ce fix et sans notion de `ranking`. Le plancher de troncature résiduel reste donc réel, non diagnostiqué (Mode A ou B inconnu). Le fallback `build_ranking` (§2.3 du plan) a été scopé par écrit — déclenchement uniquement sur épuisement des retries, périmètre limité au seul électeur en échec, marqueur de source obligatoire — mais délibérément non implémenté : à 0,6 % totalement absorbé, mélanger deux sources de bulletin dans un même run coûte plus qu'il ne rapporte.
- **Run `both` sous `factor_structure` : invalide selon son propre critère pré-enregistré** — `office_occupancy=0,333` contre un seuil de 0,70. Résultat scientifique conservé quand même (§4.2 du plan) : première comparaison like-for-like sonde/LLM — la sonde déterministe annonçait 63,6 %, le bras LLM en produit 33,3 %, surestimation d'un facteur ~2 sur une quantité continue, alors qu'elle était juste sur le compte de rappels (2 dans les deux cas).
- **Run `electoral_only` relancé et franchit le critère** (`efffdca`) : `office_occupancy=1,0`, zéro rappel, `L` plate à `m` par mandat. Comparaison v6b enfin calculable : président élu 0,0479 moyenne / 0,1702 max (écrêté) contre chambre strictement immobile (0,000000 sur 990 délibérations) — troisième confirmation indépendante de la cécité de `top_k_priorities`, et première fois que le chiffre corrigé est journalisé en bande par du code de production (`clamped_at_bound`, 8 événements, 4 tombant exactement dans le plateau de la série).
- Mais réserve explicite posée avant même de citer les chiffres : n=2 présidents au comportement opposé (l'un concède 13/16, l'autre 16/16 silencieux) et pas des positions de départ comparables. Vérifié contre la population régénérée : le second président est un quasi-centriste (7e plus proche du centre de masse sur 100, 15 mécontents contre 29 pour le premier) — sa dérive nulle est un cas de « rien à concéder », pas une résistance démontrée. Résultat le plus inattendu du run : `inaction_rate` vaut exactement 1,0 sur tous les ticks 0-15, et le président concède quand même 13 fois — la dérive n'est pas une réponse à la pression, il n'y en avait aucune.
- Bug réel corrigé au passage dans `run_v6b_acceptance.py` : l'en-tête de `summarize()` codait en dur « full pressure menu », contredisant la ligne suivante sur un répertoire `electoral_only` — rendu conditionnel au menu, les cinq répertoires de runs existants re-rendus sans erreur.
- **Chantier distribution fermé** (`dc91f5f`) : les caveats déjà posés sur §10.7/§10.8 ne couvraient que la chronologie de fiabilité GPU (bug 4), pas le fait que ces runs tiraient leur population sous `uniform`/seed=42 — corrigé aux trois endroits où la promesse de non-rétroactivité avait été faite (§10.10, le YAML, `traceability.md`) sans jamais être honorée à l'usage. Écart trouvé au passage : la ligne `uniform` du tableau §2.1 (11/40, 27,5 %) n'est pas reproductible contre le critère de nominee réellement livré — trois blocs de 40 graines donnent 70,0/75,0/67,5 %, c'est la variante centroïde qui était mesurée, mal étiquetée. La décision de Phase 2 n'est pas affectée (la marge réelle est ~2,5× plus large), annoté à trois endroits plutôt que corrigé en douce.
- **En vérifiant le §3 du plan resté ouvert (« `ambition_threshold=0.0` : à vérifier empiriquement »), découverte que l'hypothèse est fausse dans l'autre sens.** Sonde déterministe, 40 graines, 4 cellules : au seuil livré `ambition_threshold=0.7` avec `ambition_dist: beta(2,8)`, seuls 0,03 citoyen sur 100 est éligible — 39 graines sur 40 ne produisent **aucun** candidat, identique sous `uniform` et `factor_structure`. Le blocage est le couple (ambition_dist, ambition_threshold), orthogonal aux positions, et `rupture_path_enabled: false` fait de `decide_candidacy` le seul chemin de candidature — pas de voie de secours. Conséquence : aucun résultat publié (§10.4 à §10.9) n'a jamais exercé la valeur livrée ; les cinq scripts d'acceptance la contournent tous silencieusement via `dataclasses.replace`.
- Sorti en **ADR-002** (`docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md`, `dc91f5f` puis affiné `c2d68d7`), statut « Open — problem named and measured, decision deliberately deferred », sur demande explicite de ne pas noyer ce constat dans les limites de fin de section.
- Rebase de la branche sur `develop` (qui avait avancé de 57 commits — CI, dépendances, refactors et tests) sans conflit, PR précédente #188 déjà mergée entretemps → nouvelle branche `fix/polity-cast-votes-ranking-ambiguity`, **PR #216 ouverte contre `develop`**. Suite complète verte après rebase : 1767 passés, 41 ignorés, couverture 91,17 % ; `flake8`/`mypy --strict` propres.

**Points bloquants**
- Le plancher de troncature de `chamber_deliberation` (2 puis 3 occurrences sur deux runs indépendants) n'a jamais été diagnostiqué — Mode A ou Mode B inconnu, seul défaut connu encore actif.
- Le run `both` sous `factor_structure` reste invalide selon son propre critère et n'est délibérément pas rejoué.
- **La configuration livrée ne peut pas tenir d'élection dans l'écrasante majorité des cas, et rien ne le signale.** Un run aux défauts livrés produit zéro candidat, zéro élection, aucune erreur, aucun avertissement — il se termine « avec succès » sans contenir la moindre démocratie. C'est le constat central d'ADR-002, laissé volontairement sans décision de correctif (calibrer `ambition_dist`, baisser `ambition_threshold`, les deux, ou vérifier si `rupture_path_enabled: false` était l'accident réel) — choisir un correctif est un jugement de modélisation et une décision de re-baseline, pas un effet de bord de fermeture de ce chantier.
- Tout reste à n=1 graine sur les bras LLM ; le multi-graines coûterait ~4h par run. La comparaison v6b n=2 présidents reste une réserve non levée, plutôt durcie par la vérification faite.
- L'hypothèse « sonde fiable sur les quantités mécaniques, optimiste sur celles qui dépendent de l'arbitrage citoyen » reste une hypothèse de travail consolidée par un seul cas favorable (presque tautologique par sa propre clause), pas une règle établie — à ne pas citer ailleurs comme acquise.
- `traceability.md` (autre worktree, gitignoré) mis à jour localement, non commitable depuis ce dépôt.
- La justification théorique de `factor_structure` vit dans le bullet §10.10 « Limites connues » plutôt que dans une section méthodologique dédiée — rangement volontairement laissé de côté.

**Décisions prises**
- Retenir `factor_structure` (structure factorielle unimodale à 2 facteurs) plutôt qu'un mélange gaussien — *pourquoi* : un mélange présupposerait la polarisation que la vue méso du projet existe justement pour observer, contrairement à une structure unimodale qui corrèle les dimensions sans imposer de modes.
- Ne pas relancer les bras LLM complets en Phase 4 — *pourquoi* : les quatre sondes déterministes montrent une hausse cohérente de l'acceptabilité partout, avec rappels et propriété de contrôle `electoral_only` inchangés ; le coût (heures de calcul par bras) n'était pas justifié pour confirmer un résultat déjà probable, la réouverture reste possible mais différée.
- Corriger l'ambiguïté du prompt `cast_votes` plutôt que d'augmenter encore le budget de tokens — *pourquoi* : la troncature n'était pas un problème de budget insuffisant (déjà escaladé trois fois) mais un problème de convergence, une règle ambiguë que le modèle ne pouvait pas résoudre seul.
- Scoper par écrit le fallback `build_ranking` sans l'implémenter — *pourquoi* : consigne explicite de ne pas conclure trop vite que le fallback n'a pas de raison d'être (2 troncatures sur `chamber_deliberation` restent hors du périmètre du fix) ; mais à 0,6 % totalement absorbé, l'implémenter tout de suite coûterait plus (deux sources de bulletin à distinguer) qu'il ne rapporte.
- Documenter le run `both` comme invalide plutôt que de le présenter avec des réserves — *pourquoi* : il manque son propre critère pré-enregistré (0,333 contre 0,70), la seule position honnête est l'invalidité, pas une nuance.
- Sortir ADR-002 en document séparé plutôt qu'en bullet de fin de section — *pourquoi* : le problème (aucune élection possible aux valeurs livrées, silencieusement) est structurellement plus grave que les limites habituellement listées en §10.10 et mérite sa propre traçabilité de décision.
- Prioriser explicitement le garde-fou contre l'échec silencieux avant la question de calibration `ambition_dist`/`ambition_threshold` — *pourquoi* : une valeur mal calibrée reste détectable en observant les résultats, alors qu'un mécanisme qui dégénère silencieusement rend un run d'apparence propre sans le moindre indice qu'il manque quelque chose ; c'est aussi l'option la moins coûteuse des deux, sans décision de re-baseline ni changement d'ordre RNG.
- Ne pas corriger silencieusement l'étiquette erronée du tableau §2.1 (ligne `uniform` mesurée avec la variante centroïde) — *pourquoi* : annoter l'écart à trois endroits préserve la trace de ce qui a réellement été mesuré, même quand la décision finale n'en est pas affectée.

**Prochaines étapes**
- [ ] **Priorité 1 sur ADR-002 : implémenter le garde-fou contre l'échec silencieux** — `PolityConfigError` au chargement quand `(ambition_dist, ambition_threshold)` ne peut produire aucun pool de candidats, et/ou garde-fou à l'exécution quand un tick d'élection trouve zéro nominee, et/ou événement de journal explicite. À traiter **avant** la question de calibration ci-dessous.
- [ ] Trancher ensuite la calibration `ambition_dist`/`ambition_threshold` (relever le seuil d'ambition, baisser le seuil de candidature, les deux, ou vérifier d'abord si `rupture_path_enabled: false` était l'accident réel) — non commencé, aucune option évaluée à ce stade.
- [ ] Diagnostiquer le plancher de troncature résiduel de `chamber_deliberation` (Mode A ou B, prompt distinct de `cast_votes`) — non commencé.
- [ ] Faire suivre la PR #216 (contre `develop`) en revue/merge.

**Pour aller plus loin** : `plan-distribution-positions-seeds.md` (protocole complet Phases 1-4 et §3.1 pour la sonde ambition_threshold), `THEORY.md` §10.9-§10.10, `docs/adr/ADR-002-ambition-threshold-blocks-candidacy.md`, `fast_api_voter/scripts/acceptance_v6b_fs_electoral_only_results.md`, `fast_api_voter/scripts/llm_test_harness/README.md` (piège `message.reasoning`), PR #216, entrée du 2026-08-24 pour la fermeture de la chaîne causale seed=42 qui a ouvert ce chantier.

---

## 2026-08-24 — Le run cascade à trois ingrédients ne franchit pas la barre de go/no-go, et révèle un problème plus grave que celui qu'il cherchait à tester

**Contexte du jour.** La PR #184 (v6b Lot 4 acceptance + investigation fiabilité LLM + déterminisme GPU + métrique de déviation unifiée), qui rassemble le travail déjà raconté dans les entrées du 19 au 23 août, a été mergée sur `develop` ce matin (squash `c40b1bb`) — non re-racontée ici. Nouvelle branche `feat/polity-cascade-acceptance` ouverte pour le chantier suivant, identifié depuis plusieurs sessions comme le point qui referme la revendication à trois ingrédients du §7bis.9e (« un basculement de type Gilets jaunes n'est pas atteignable avant v6… il requiert simultanément le graphe social, les chocs exogènes et les leviers de pression ») : un run d'acceptation qui active pour la première fois `events` (v5) et `social_graph`/`neighbors_acting` (v6a) *ensemble*, sous `mobilization_only`, alors que chaque run précédent n'en avait isolé qu'un seul à la fois.

**Ce qui a avancé**
- Script `fast_api_voter/scripts/run_cascade_acceptance.py` écrit, avec critère de décision pré-enregistré dans le docstring avant tout lancement : escalader vers le bras LLM (~2,5-5h prévues) seulement si le dry-run déterministe atteint `office_occupancy >= 0.5` et au moins 2 ticks de tir de scandale + 1 de choc ; sinon diviser par deux `scandal_rate`/`economy_sigma` et relancer le dry-run (quasi gratuit) — jamais relâcher `legitimacy.recall_floor`, option explicitement exclue en citant la conclusion déjà actée du v6b Lot 4 (« scientifiquement peu élégant… désactive la responsabilité plutôt que de la tester »).
- Dry-run déterministe exécuté (`scripts/acceptance_cascade_runs/cascade-deterministic-8y-r0.08-s0.12/`, seed=42, `scandal_rate=0.08`/`economy_sigma=0.12`, point de départ délibérément prudent — environ moitié moins que le calibrage v5 déjà retenu, ce dernier n'ayant jamais été validé pour cette combinaison précise). Résultat : `office_occupancy=0.152`, largement sous la barre `>=0.5`.
- Escalade prescrite par le script tentée (division par deux du taux à `r0.04/s0.06`) : résultat byte-identique au run précédent (`office_occupancy=0.152`, mêmes 2 rappels, zéro scandale, zéro choc déclenché) — preuve directe que les événements ne se déclenchent jamais avant l'effondrement, donc qu'aucun recalibrage de ce type ne peut réparer quoi que ce soit.
- Racine tracée dans le journal du run lui-même : élection au tick 0, rappel au tick 1 (`L` chute de 0,345 à 0,026, sous le plancher 0,2), poste vacant jusqu'au tick 16, nouvelle élection, nouveau rappel au tick 17, vacant jusqu'au tick 32. Au tick 0, la porte d'éveil est maximalement permissive (aucun terme de modulation contextuel n'a encore eu la chance d'être non nul), ce qui consulte 67/100 citoyens et en mobilise 33/100 — exactement le chiffre déjà documenté par v4 Lot 4 (« mobilize max ≈0.33 juste après élection »), déjà à l'intérieur du mur d'amplification x33,3 que le docstring de v4 Lot 4 nommait déjà. Ce résultat (`legitimacy_floor=2`, `mean L (last)=0.345`) est byte-identique à la ligne `mobilization_only` déjà committée de v4 Lot 8 et à la ligne contagion déjà committée de v6a Lot 4 — preuve qu'il s'agit d'une propriété préexistante de la ligne de base déterministe `mobilization_only`, présente depuis v4 Lot 8, jamais repérée jusqu'ici faute d'une métrique `office_occupancy` explicite dans les scripts d'acceptation précédents.
- Décision prise en conséquence, sans consommer le budget GPU du bras LLM : le bras LLM (~2,5-5h) n'a délibérément pas été lancé — la barre de go/no-go n'étant franchissable par aucun des leviers autorisés par le plan, le résultat déterministe est documenté tel quel comme un résultat honnête (limite structurelle, pas un bug ni un résultat nul) dans `fast_api_voter/scripts/acceptance_cascade_results.md`.
- **Découverte plus large en cours de route, faite en balayant 11 graines alternatives (1, 2, 3, 5, 7, 10, 13, 21, 99, 100, 123) pour vérifier si un autre tirage de population évitait l'effondrement** : 9 sur 11 n'élisent aucun président du tout — le Blanc l'emporte au second tour (`election_no_winner`) dès qu'assez d'électeurs jugent les 5 plateformes de parti inacceptables — et les 2 restantes (10, 99) qui élisent quelqu'un s'effondrent quand même par le même mécanisme de rappel. `seed=42` — la seule graine jamais utilisée par un run d'acceptation de ce projet, de v4 Lot 8 jusqu'aux runs v6b les plus récents — se situe juste sous ce seuil de basculement (~32-34 % de bulletins classant Blanc en tête) par coïncidence de tirage, pas par une propriété distinctive de la population générée : son `blank_threshold` moyen et sa distance moyenne au nominee le plus proche ne sont pas systématiquement plus favorables que plusieurs graines qui échouent. Vérifié directement que ce phénomène est indépendant de `pressure_menu`/`social_graph`/`events` (les élections se résolvent avant que ces mécanismes n'interviennent) : `electoral_only` aux seeds 1 et 7 produit le même `election_no_winner`.
- Deux notes de documentation ajoutées, pure documentation sans changement de code/comportement : un nouveau paragraphe en tête de §10.10 « Limites connues » de `THEORY.md` ; une troisième clause datée (2026-08-24) ajoutée à la cellule Statut de la ligne Polity de `traceability.md` (autre worktree `C:\Users\burba\Vote-App`, gitignoré donc invisible au `git diff` de ce dépôt — vérifié directement dans le fichier).
- Travail du jour committé (`87d319b`) et poussé, PR #188 ouverte contre `develop` — non mergée à la demande explicite de l'utilisateur (« no need to merge »).
- **Revirement plus tard dans la même session : l'investigation de fond sur la représentativité des graines, explicitement écartée plus haut dans cette même entrée, a finalement été autorisée et menée à terme le jour même** (« lets start the investigation », après la mise en attente initiale). Menée intégralement en lecture/mesure contre le pipeline réel (`generate_population`, `initialize_parties`, `select_party_nominee`, `build_ranking`, `get_two_round_winner`), via des scripts éphémères dans le scratchpad de session — jamais commités, jamais destinés à l'être. Chaîne causale fermée, pas seulement corrélée :
  - Élargi le sweep à 60 graines : le Blanc l'emporte sur **41/60 (68 %)** à la configuration livrée — un taux bien plus élevé que les 9/11 du premier sweep ne le laissait supposer, et le taux de bulletins « Blanc forcé » (aucun des 5 nominee dans la tolérance de l'électeur) reste étonnamment resserré d'une graine à l'autre (0,29 à 0,52, écart-type 0,054) — signe que ce n'est pas un tirage de population particulier qui échoue, mais une propriété quasi systématique du modèle.
  - **Mécanisme du second tour identifié comme déterministe, pas probabiliste** : une fois le Blanc qualifié, `build_ranking` classe tout candidat dans la tolérance d'un électeur au-dessus du Blanc et tout candidat hors tolérance en dessous — le second tour se réduit donc, par électeur, à une seule question binaire (« ce finaliste m'est-il acceptable ? »), indépendante des trois autres candidats. Vérifié : le Blanc gagne si et seulement si l'acceptabilité du finaliste dans toute la population est `≤ 50 %` — frontière exacte sur 40 graines (max 50,0 % quand le Blanc gagne, min 51,0 % quand un candidat réel gagne, zéro chevauchement).
  - Cause racine isolée : `citizens.position_dist: uniform` disperse 100 citoyens sur 20 dimensions sans centre de gravité ; combiné à une pondération de priorités individualisée par électeur (`priority_dist: dirichlet`), quasiment aucun point n'est proche, selon la métrique propre à chaque électeur, de plus de la moitié de la population.
  - Deux leviers testés isolément contre le même pipeline : la méthode de sélection du nominee (le membre au score d'ambition le plus élevé, artefact de `ambition_threshold=0.0` forcé par tout script d'acceptance, vs le membre le plus proche du centroïde k-means du parti) fait passer le taux d'échec de 70 % à 27,5 % (5 partis, 40 graines) — un effet réel mais secondaire, qui n'élimine pas le problème. Augmenter le nombre de partis n'aide pas de façon monotone (55 % à 10 partis, remonte à 67,5 % à 15-20 partis) — la couverture s'améliore mais la fragmentation du vote s'aggrave en proportion.
  - **Le levier qui referme la chaîne** : remplacer uniquement le tirage des positions par une distribution concentrée (`position_dist: gaussian_mixture`, déjà légale dans le schéma de config mais jamais implémentée — `generate_population` la rejette avec `NotImplementedError`), tout le reste du pipeline inchangé, fait chuter l'échec à 2,5 % (gaussienne large, `std=0,30`) puis 0 % (`std≤0,20`, ou mélange à 2-3 modes) sur les 40 graines testées.
  - `THEORY.md` §10.10 et `traceability.md` réécrits pour porter cette chaîne complète, en remplacement des notes préliminaires du matin.

**Points bloquants**
- La revendication à trois ingrédients du §7bis.9e reste non testable à l'échelle actuelle (`population_size=100`, seed=42, `mobilization_only`) — pas parce que la contagion ou les événements échouent à interagir, mais parce que le poste est vacant avant qu'ils n'aient la moindre chance d'agir. Ligne du v6a Lot 4 déjà committée montrant le même `legitimacy_floor=2` sous le même menu (sans événements) suggère, sans le prouver (`office_occupancy` jamais calculée sur ce run-là), que le bras LLM ne s'en tirerait probablement pas mieux.
- La décision de corriger reste entièrement ouverte : le mécanisme est complet et fermé, mais implémenter `gaussian_mixture` dans `generate_population`, et/ou revoir le tiebreak de `select_party_nominee`, et/ou reconsidérer l'override `ambition_threshold=0.0` que tout script d'acceptance impose — touchent un mécanisme central du v0, utilisé par tous les runs du projet depuis le début. Aucune de ces pistes n'a été décidée ni commencée.
- La réécriture complète de `THEORY.md` §10.10 (chaîne causale fermée, décrite ci-dessus) n'a jamais été committée : elle existe uniquement comme diff dans l'arbre de travail au moment de la clôture de cette session (`git status` : `M THEORY.md`, 60 insertions/14 suppressions), et remplace localement la note préliminaire déjà committée dans `87d319b`/PR #188 — mais la PR elle-même porte encore cette note préliminaire, pas la version finale. La question de committer/pousser cette mise à jour vers PR #188 a été posée explicitement à l'utilisateur en fin de session ; la réponse reste en attente au moment de la rédaction de cette entrée.

**Décisions prises**
- Ne pas lancer le bras LLM une fois la barre de go/no-go pré-enregistrée manquée et l'escalade prescrite épuisée — *pourquoi* : le plan pré-enregistré ne prévoyait pas d'autre levier autorisé (le relâchement de `recall_floor` étant explicitement exclu), et le coût du bras LLM (~2,5-5h) n'aurait rien pu changer à une cause déjà tracée comme indépendante des événements.
- Documenter `office_occupancy=0.152` comme un résultat honnête de limite structurelle plutôt que de le présenter comme un échec de calibration — *pourquoi* : la cause est tracée avec preuve (byte-identité entre deux taux d'événements différents, byte-identité avec des lignes déjà committées de v4 Lot 8 et v6a Lot 4) à une propriété préexistante de la ligne de base `mobilization_only`, pas à un mauvais réglage de ce run.
- Committer et ouvrir la PR #188 sans la merger — *pourquoi* : consigne explicite de l'utilisateur (« no need to merge »), le travail est prêt pour revue mais l'intégration reste une décision séparée.
- **Revirement explicite et assumé** : l'investigation de fond, mise en attente plus tôt dans la journée (« mérite une vraie session »), a finalement été autorisée et menée le jour même sur consigne directe de l'utilisateur (« lets start the investigation ») — la décision antérieure de ne pas l'engager n'a pas été reconduite silencieusement, elle a été explicitement remplacée.
- Approfondir jusqu'à fermer la chaîne causale complète (pas s'arrêter à la première corrélation trouvée) — *pourquoi* : deux points de contrôle explicites de l'utilisateur en cours de route (« creuser le résiduel », puis « tester gaussian_mixture ») plutôt que de documenter une explication partielle après le premier résultat frappant.
- S'arrêter une fois la chaîne fermée par le test `gaussian_mixture`, sans passer à la conception d'un correctif — *pourquoi* : consigne explicite de l'utilisateur à la dernière étape de contrôle ; le mécanisme est maintenant complet et déterministe (pas une hypothèse), mais corriger touche `select_party_nominee`/`generate_population`, du code central utilisé par tout le projet, et mérite sa propre planification séparée plutôt qu'être décidé en bout d'investigation.

**Prochaines étapes**
- [x] Committer le travail du jour (`.gitignore`, `THEORY.md`, `run_cascade_acceptance.py`, `acceptance_cascade_results.md`) — fait (`87d319b`), PR #188 ouverte, non mergée.
- [x] Investigation de fond sur la représentativité des graines — faite le jour même, chaîne causale complète fermée (voir ci-dessus).
- [ ] Décider si/quand committer et pousser vers PR #188 la réécriture complète de `THEORY.md` §10.10 — actuellement diff non commité dans l'arbre de travail, décision utilisateur en attente.
- [ ] Décider si/comment corriger : implémenter `gaussian_mixture` dans `generate_population`, et/ou revoir le tiebreak de `select_party_nominee` (centroïde plutôt qu'ambition), et/ou reconsidérer l'override `ambition_threshold=0.0` de chaque script d'acceptance — non commencé, non planifié, décision et priorité restent à prendre.
- [ ] Statuer, une fois un correctif éventuel tranché, sur si/comment retenter le run cascade à trois ingrédients (§7bis.9e) avec un tirage de population plus robuste.

**Pour aller plus loin** : `fast_api_voter/scripts/run_cascade_acceptance.py` (script, docstring pré-enregistré), `fast_api_voter/scripts/acceptance_cascade_results.md` (résultat détaillé, premier sweep de graines), `THEORY.md` §10.10 (chaîne causale complète, réécrite en fin de journée — diff non commité au moment de la rédaction de cette entrée, voir Points bloquants), `docs/research/traceability.md` (autre worktree, troisième clause réécrite), PR #188 (committée, non mergée, porte encore la note préliminaire de §10.10), entrées du 19 au 23 août pour le contexte complet de la PR #184. Les scripts de l'investigation de fond (sweep à 60 graines, test `gaussian_mixture`) étaient dans le scratchpad de session, non commités — à reproduire depuis THEORY.md §10.10 si nécessaire, pas depuis un fichier existant.

---

## 2026-08-23 — Troisième run d'acceptance (electoral_only) : même maximum au bit près, et un pré-enregistrement vérifié à trois horodatages indépendants

**Contexte du jour.** Suite directe de la session de la veille (commit `ab91fa2`) : le second run d'acceptance v6b Lot 4 (`legitimacy.recall_floor=0.0`) avait éliminé le confond de vacance en gardant le président en poste sans interruption, mais via un levier qui désactive la responsabilité plutôt que de la tester — recall_floor à zéro. Objectif du jour : planifier deux chantiers de suivi, puis exécuter le plus rigoureux des deux — un troisième run résolvant le même confond via `pressure_menu.electoral_only`, un levier qui teste la responsabilité électorale sans l'éteindre.

**Ce qui a avancé**
- Deux chantiers planifiés en profondeur (mode plan, approbation utilisateur explicite) : (A) câblage en production d'une métrique de déviation "unifiée" (sans configuration, même pondération que `chamber_deviation`) dans `representative_response`/`mandate_deviation_recorded` et l'extraction `indexer.py` correspondante ; (B) un troisième run d'acceptance via `pressure_menu.electoral_only` au lieu d'un `recall_floor` mis à zéro.
- Chantier B seul autorisé et exécuté ce jour. Pré-enregistré avant lancement : hypothèse et trois branches de résultat nommées à l'avance (comparable au run 2, matériellement plus bas mais non nul, ou quasi nul) — critère de décision explicite pour éviter toute survente a posteriori.
- Run LLM lancé (~4,4h prévues, bande 3,9-5,9h), terminé proprement en ~4h38 (16670,7s, 28 replays, sain).
- Falsifiables structurels pré-enregistrés tous vérifiés : zéro rappel, occupation du poste à 1,0, mêmes élections byte-identiques entre run 2 et run 3 — même titulaire, même plateforme promise, confirmant que candidature/nomination/vote ne dépendent pas du menu de pression.
- Résultat dans la branche intermédiaire pré-enregistrée : déviation unifiée moyenne du président à 0,1017 (contre 0,1496 sur le run 2, environ un tiers de baisse), mais maximum identique au bit près entre les deux runs (0,2312481349581757).
- Ce maximum identique investigué à la demande explicite de l'utilisateur avant toute synthèse : reconstruction complète depuis les deux journaux bruts (régénération de la population, rejeu des shifts) montrant que les deux présidents (même personne dans les deux runs) saturent indépendamment les trois mêmes dimensions au plafond du clamp [0,1] — atteint au tick 27 sous pression complète, seulement au tick 30 sous `electoral_only`. Même plafond, atteint plus tard sans la pression de rue : explique la baisse de moyenne sans toucher au maximum, corrobore la découverte du plafonnement de la veille une seconde fois plutôt que de la contredire.
- Preuve matérielle du pré-enregistrement également demandée avant synthèse (pas une reconstruction a posteriori) : retrouvée dans la transcription de session avec horodatages UTC réels — édition du plan à 13:31:13Z, approbation à 13:39:09Z, édition du docstring du script à 13:45:49Z, message utilisateur de lancement à 14:04:58Z, lancement effectif vers 14:05Z — 19 à 34 minutes d'écart, vérifié à trois points indépendants, pas un simple mtime de fichier.
- `THEORY.md` §10.9/§10.10 et `fast_api_voter/scripts/acceptance_v6b_results.md` mis à jour pour raconter l'histoire à trois runs comme un seul récit continu (pas deux documents séparés) : tableau de résultats du troisième run, vérification élections/identité du maximum, synthèse de la question de départ à travers les trois runs. `traceability.md` (autre worktree) ne nécessitait aucun changement ce coup-ci — déjà à jour depuis le commit de la veille.
- Commit unique sur `feat/polity-v6b-lot4-acceptance` (`922a070`), portant exactement `THEORY.md` et `acceptance_v6b_results.md` — séparé du reste de l'arbre de travail, comme la veille.

**Points bloquants**
- Le câblage en production de la métrique unifiée (chantier A) n'a pas démarré ce jour — resté au stade plan. Le code déjà modifié lors de la session précédente pour ce chantier (`accountability.py`, `run_polity_simulation.py`, `indexer.py`, tests, `run_v6b_acceptance.py`) est présent dans l'arbre de travail mais non commité, et mélangé dans `run_v6b_acceptance.py` avec un diff préexistant sans rapport qu'il faudra démêler avant de committer proprement.
- Le clamp silencieux d'`apply_shifts`, documenté mais non corrigé, reste un défaut d'observabilité en suspens — confirmé une seconde fois ce jour comme mécanisme actif, pas résolu pour autant.

**Décisions prises**
- Traiter uniquement le chantier B (troisième run via `electoral_only`) ce jour, laisser le chantier A (câblage production) au stade plan — *pourquoi* : consigne explicite de l'utilisateur de ne pas enchaîner les deux chantiers sans autorisation séparée, l'un est une exécution d'expérience bornée dans le temps, l'autre un chantier de code à part entière.
- Préférer `pressure_menu.electoral_only` à un `recall_floor` relâché pour ce troisième run — *pourquoi* : teste la responsabilité électorale en retirant la pression de rue plutôt que de désactiver le mécanisme de rappel lui-même, un levier plus proche de la question scientifique posée par le §6bis.3.
- Investiguer le maximum identique au bit près avant toute rédaction de synthèse, plutôt que de le mentionner en passant comme curiosité — *pourquoi* : consigne explicite de l'utilisateur ; une coïncidence numérique de cette précision méritait une explication mécanique vérifiée, pas une hypothèse non testée.
- Vérifier matériellement l'antériorité du pré-enregistrement au lancement avant de synthétiser le résultat — *pourquoi* : consigne explicite de l'utilisateur ; un pré-enregistrement n'a de valeur que si son antériorité au résultat est démontrable, pas seulement affirmée.
- Committer la mise à jour documentaire (`THEORY.md`, `acceptance_v6b_results.md`) isolément du reste de l'arbre de travail — *pourquoi* : cohérent avec la discipline déjà établie sur ce projet d'un commit par préoccupation.

**Prochaines étapes**
- [ ] Démêler le diff préexistant sans rapport dans `run_v6b_acceptance.py` du code du chantier A (câblage métrique unifiée), puis committer séparément — non autorisé à démarrer.
- [ ] Câbler la métrique de déviation unifiée en production (`accountability.py`, `run_polity_simulation.py`, `indexer.py`, tests déjà modifiés dans l'arbre de travail) — non autorisé à démarrer.
- [ ] Statuer, à terme, sur une correction du clamp silencieux d'`apply_shifts` (retour/journalisation), au-delà de la documentation actuelle du défaut.

**Pour aller plus loin** : `THEORY.md` §10.9-§10.10 (récit à trois runs, commit `922a070`), `fast_api_voter/scripts/acceptance_v6b_results.md` (régénéré), `fast_api_voter/scripts/acceptance_v6b_runs_electoral_only/` (troisième run), `fast_api_voter/scripts/acceptance_v6b_electoral_only_results.md`, entrée du 2026-08-22 précédente pour le contexte des deux premiers runs et du plafonnement du clamp.

---

## 2026-08-22 — Le confond de vacance était un demi-diagnostic : bug de métrique, plafonnement du clamp, et une §10.9 réécrite en entier

**Contexte du jour.** Suite directe de la session précédente du même jour : le premier run d'acceptance v6b Lot 4 (menu `both`) s'était révélé confondu par un rappel quasi immédiat du président élu après chacune des deux élections, laissant le poste vacant l'essentiel du run et `mandate_deviation` à 0,0 par absence d'exposition plutôt que par fidélité réelle. Un second run avait été lancé avant cette session avec `legitimacy.recall_floor=0.0` pour éliminer ce confond par construction. Objectif du jour : comprendre pourquoi `mandate_deviation` restait *encore* à 0,0 dans ce second run malgré une occupation du poste à 100 %, et trancher enfin la question du §6bis.3 — la chambre de sortition est-elle sincère ou erratique, comparée au président élu ?

**Ce qui a avancé**
- Diagnostic du second run (`scripts/acceptance_v6b_runs_recallfloor0/`, `office_occupancy=1.0`, zéro rappel, 15874,6s, 28 rejeux) : `mandate_deviation` à 0,0 malgré une exposition complète n'était pas un artefact de run mais un vrai bug de conception de métrique.
- Recalcul post-hoc de `mandate_deviation` avec la même méthode déjà en service pour `chamber_deviation` (`weighted_euclidean` sur le vecteur de priorités complet, sans troncature) pour obtenir une comparaison sur la même base. Résultat mesuré : président (métrique unifiée) moyenne 0,1496 / max 0,2312, contre chambre quasi inerte moyenne 0,000036 / max 0,0353 — l'écart que le run devait révéler apparaît enfin.
- Second phénomène repéré en examinant la série recalculée : elle plafonne exactement à deux reprises (0,194070 du tick 10 à 15 ; 0,231248 du tick 27 à 31). Vérifié directement contre le journal d'événements : à chaque tick du plateau, `representative_response` continue d'émettre des `shifts` non vides (motif `302 STREET_PRESSURE_RESPONSE`, concession) sur les mêmes trois dimensions — la pression ne s'arrête jamais. Ce qui plafonne réellement, c'est le clamp `[0,1]` d'`apply_shifts` : les trois dimensions ont déjà atteint 1,0, chaque delta suivant vise une cible hors bornes absorbée silencieusement.
- Reconstruction diagnostique bâtie pour quantifier l'ampleur masquée par le clamp : mêmes shifts journalisés, rejoués sans jamais appliquer le clamp. La déviation "fantôme" non bornée atteint 0,701 en fin de premier mandat (contre 0,194 côté clampé — x3,6) et 0,642 en fin de second mandat (contre 0,231 — x2,8). Le chiffre officiellement rapporté est donc une borne inférieure de la dérive réelle, pas une mesure de son plafond — ce qui renforce la conclusion scientifique (chambre sincère, président erratique sous pression) plutôt que de la nuancer.
- Défaut d'observabilité repéré et signalé séparément, hors résultat scientifique : `apply_shifts` clampe silencieusement (aucun retour, aucun journal, aucun log) — un défaut partagé par les trois décisions qui l'utilisent (dt=5, dt=6, dt=11), pas spécifique à `mandate_deviation`. Documenté dans la docstring d'`apply_shifts` (`llm_behavior_engine.py`) et dans `traceability.md`, non corrigé à ce stade.
- `THEORY.md` §10.9 réécrite en entier (et la puce §10.10 qui la référençait, restée rédigée pour le premier run confondu, donc obsolète) pour raconter l'histoire complète en deux runs : bug de métrique, mesure corrigée, plafonnement diagnostiqué comme borne inférieure. Relecture de cohérence demandée explicitement par l'utilisateur avant commit : deux problèmes réels trouvés et corrigés — (a) l'ordre de deux paragraphes était inversé, la reconstruction non clampée citait les valeurs du plateau avant que le plateau lui-même soit expliqué, référence en avant héritée d'une version antérieure du raisonnement ; (b) un chiffre figé d'un brouillon antérieur ("99,3 % de décisions `SINCERE_POSITION`") appartenait en réalité aux statistiques du premier run, pas du second — revérifié directement contre `chamber.json` et corrigé à 99,70 %.
- `fast_api_voter/scripts/acceptance_v6b_results.md` régénéré pour raconter exactement la même histoire que `THEORY.md`, avec les chiffres relus directement dans les `metrics.json`/`chamber.json` des deux runs, pas recopiés d'un brouillon.
- Vérifications avant commit : `flake8`/`mypy` propres sur `accountability.py` et `llm_behavior_engine.py` — changements docstring-only, aucun changement de comportement.
- Commit unique sur `feat/polity-v6b-lot4-acceptance` (`ab91fa2`), portant exactement `THEORY.md`, `accountability.py`, `llm_behavior_engine.py`, `acceptance_v6b_results.md` — délibérément séparé du reste de l'arbre de travail (diff non lié dans `run_v6b_acceptance.py`, `llm_batching_determinism_results_gpu.md`, scripts supprimés, répertoires de runs non suivis), non lié à ce chantier précis.

**Points bloquants**
- Aucun nouveau, mais deux fils explicitement laissés en l'état par choix, pas par oubli : la métrique de déviation unifiée n'est câblée que dans cette analyse post-hoc, pas dans les métriques de production (`metrics.json`/`indexer.py`) ; et la question de vacance du tout premier run (menu `both`) n'a pas de run de suivi dédié.
- Le clamp silencieux d'`apply_shifts` reste un défaut d'observabilité non corrigé, documenté mais pas résolu — toute mesure future de déviation basée sur cette fonction sous-estimera potentiellement la dérive réelle sans avertissement.

**Décisions prises**
- Recalculer `mandate_deviation` post-hoc avec la méthode `weighted_euclidean` déjà en service pour `chamber_deviation`, plutôt que de retoucher le mode `top_k_priorities` en production — *pourquoi* : répondre à la question scientifique du jour sans engager un nouveau chantier de correction de métrique de production, non prévu dans ce lot.
- Quantifier explicitement l'effet du clamp via une reconstruction "fantôme" non bornée plutôt que de se contenter de signaler sa présence — *pourquoi* : donner un ordre de grandeur (x2,8 à x3,6) permet de qualifier le chiffre rapporté comme borne inférieure fiable, au lieu de laisser planer un doute non chiffré sur sa validité.
- Différer explicitement le câblage en production de la métrique unifiée et la conception d'un run de suivi pour le premier run confondu — *pourquoi* : ce sont deux nouveaux chantiers distincts, pas la suite mécanique de la correction documentaire du jour ; consigne explicite de l'utilisateur de ne pas les enchaîner sans autorisation séparée.
- Commiter la correction documentaire (`THEORY.md`, docstrings, résultats) isolément du reste de l'arbre de travail non lié — *pourquoi* : cohérent avec la discipline déjà établie sur ce projet d'un commit par préoccupation.

**Prochaines étapes**
- [ ] Câbler la métrique de déviation unifiée (pondération pleine, méthode `chamber_deviation`) dans les métriques de production (`metrics.json`/`indexer.py`) — non autorisé à démarrer.
- [ ] Concevoir et lancer un run de suivi pour trancher la question de vacance du premier run (menu `electoral_only`, ou plancher de rappel relâché, pour laisser le mandat élu survivre assez longtemps pour être comparable) — non autorisé à démarrer.
- [ ] Statuer, à terme, sur une correction du clamp silencieux d'`apply_shifts` (retour/journalisation), au-delà de la documentation actuelle du défaut.

**Pour aller plus loin** : `THEORY.md` §10.9-§10.10 (réécrites, commit `ab91fa2`), `fast_api_voter/scripts/acceptance_v6b_results.md` (régénéré), `scripts/acceptance_v6b_runs_recallfloor0/` (second run, `legitimacy.recall_floor=0.0`), docstrings `KNOWN METRIC DESIGN BUG`/`KNOWN OBSERVABILITY GAP` dans `accountability.py` et `llm_behavior_engine.py`, `docs/research/traceability.md` (autre worktree, note `apply_shifts`), entrée du 2026-08-22 précédente pour le contexte du premier run confondu.

---

## 2026-08-22 — chamber_deliberation tronqué, chunk_size réduit à 1, run d'acceptance terminé — mais la question du §6bis.3 reste ouverte

**Contexte du jour.** Prolongation directe de l'investigation bug 4 (troncature `finish_reason='length'` sur Ollama), entamée le 2026-08-19 et poursuivie le 2026-08-20/21 : après le déploiement de la mitigation cache-recycling (`49e3631`), un nouveau run d'acceptance v6b Lot 4 relancé avait planté sur `chamber_deliberation` (dt=11) au tick 18, après 1258 événements journalisés — signe que la mitigation bug 4 ne suffisait pas seule à sécuriser cette décision LLM particulière. Objectif du run : trancher, via le v6b Lot 4, si la chambre tirée au sort se comporte de façon sincère ou erratique, en la comparant au président élu sur la même durée.

**Ce qui a avancé**
- Diagnostic mené selon la méthode "Mode A vs Mode B" déjà établie sur ce projet : sur les 3 tentatives du run planté (originale + 2 replays), `n_decoded` tombait exactement et systématiquement à `10136 = compute_max_tokens(10) + _CHAMBER_THINK_TOKEN_ALLOWANCE(8000)` — signature Mode B (plafond de budget trop juste, pas une dérive sans convergence), avec 11630 tokens de marge de contexte disponible par ailleurs. Chunk_size de `chamber_deliberation` confirmé à 10 dans le code.
- Fix testé par escalade contrôlée, chaque palier validé avant le suivant plutôt qu'un saut direct à la valeur la plus prudente :
  - `_CHAMBER_MAX_CHUNK_SIZE = 5` essayé en premier (par analogie avec l'historique déjà documenté de `_VOTE_CAST_MAX_CHUNK_SIZE`) — **rejeté après validation live** : rejoué contre l'état exact du run planté (replay du journal, seed=42, sans re-run complet), un sous-groupe différent de 5 citoyens (cids [59,61,65,75,90]) a reproduit la même signature de troncature, `n_decoded=9836` = plafond exact, marge nulle.
  - `_CHAMBER_MAX_CHUNK_SIZE = 1` essayé ensuite (l'aboutissement déjà connu pour `_VOTE_CAST_MAX_CHUNK_SIZE`), revalidé sur le même groupe de 5 citoyens en individuel : 5/5 réussites, 4.3–11.7s chacune — un ordre de grandeur plus rapide que les 99–108s des tentatives échouées, marge réelle cette fois.
- Documentation (docstrings, commentaires de code, 3 fichiers de tests, `fast_api_voter/scripts/lot3_chamber_reliability_results.md`) réécrite pour refléter la chaîne complète de preuves (10 → 5 essayé et invalidé → 1 validé), pas seulement la valeur finale retenue.
- Vérifications complètes après le fix : `pytest -k "chamber"` (23 passed), mypy clean, flake8 clean, suite complète `pytest api/` (1548 passed, 41 skipped).
- **Run d'acceptance relancé, terminé avec succès (exit code 0).** Journal complet jusqu'au tick 32, 2012 événements journalisés. 38 replays au total sur tout le run — tous récupérés dès leur première tentative de retry, aucun n'a épuisé son budget de 3 tentatives. Temps réel 16384.8s (~4.55h), proche de la prévision du plan (~3.95h). La chambre de sortition est restée pleine (30 sièges) sur les 9 rotations du run — le mécanisme de bassin assoupli (v6b Lot 2) a tenu comme prévu.
- Nettoyage découvert en cours de route : `fast_api_voter/scripts/acceptance_v6b_runs/` avait accumulé 18 dossiers de runs ratés/obsolètes de sessions précédentes (déjà nommés `-failed-*`/`-stale-*`), que le script `--summarize` (glob non récursif à un niveau) ramassait quand même et mélangeait dans le rapport final. Archivés (déplacés, pas supprimés) dans `_archived_failed_runs/` pour que le résumé ne porte que sur les deux runs réels du jour (déterministe + LLM).
- Synchronisation documentaire faite : `THEORY.md` gagne une nouvelle §10.9 "La chambre de sortition — sincère ou erratique ?" (renumérote les sections suivantes : 10.9→10.10 limites, 10.10→10.11 références), avec la découverte de vacance rapportée honnêtement dans le corps du texte. `traceability.md` (autre worktree, `c:/Users/burba/Vote-App/docs/research/`) mis à jour : statut `implémenté (v4, v5, v6a, v6b)`.
- **Étape 3.1 du prompt séquencé post-harnais reprise (nettoyage de dette technique jamais fait jusqu'ici) : ajout du champ `inference_backend`/version driver-CUDA.** Nouvelle fonction `_capture_gpu_driver_info()` dans `run_polity_simulation.py` : capture best-effort (jamais fatale, dégrade à `(None, None)` sur tout échec) de la version du driver GPU et de la version CUDA via un appel `nvidia-smi` en subprocess — inspirée du même principe déjà utilisé par `llm_test_harness/environment.py`, sans adopter le harnais lui-même. Deux nouveaux champs dans `run_metadata.json` (`gpu_driver_version`, `gpu_cuda_version`), capturés **uniquement** quand `config.llm.enabled` est vrai — le GPU n'a de sens à identifier que quand un appel LLM peut réellement avoir lieu, et ça évite tout coût subprocess sur les >100 invocations déterministes de `run_simulation` dans la suite de tests. 4 nouveaux tests, mypy clean, flake8 clean, suite complète passée à 1552 passed / 41 skipped (+4).
- **Étape 3.2 reprise (audit des runs antérieurs aux correctifs), avec une découverte notable.** Aucun dossier `runs/` par défaut trouvé — tous les vrais runs du projet utilisent des `--output-dir` explicites vers `scripts/acceptance_v*_runs/`. En examinant ces dossiers, découverte que **deux résultats déjà publiés dans `THEORY.md` reposent sur des runs antérieurs à tous les correctifs de fiabilité de cette investigation** : `scripts/acceptance_v5_runs/electoral_only-llm-8y-events-r0.15-s0.25/` (2026-08-15, cité en §10.7 "l'étincelle", palier v5 Lot 5) et `scripts/acceptance_v6a_runs/contagion-llm-8y/` (2026-08-16, cité en §10.8 "la contagion", palier v6a Lot 4) — tous deux antérieurs au fix warm-up GPU (18/08), à la mitigation cache-recycling bug 4 (20/08), et au fix `vote_cast`/`chamber_deliberation` d'aujourd'hui. Constat présenté à l'utilisateur avant toute modification de `THEORY.md` (voir décisions ci-dessous).
- **Audit ciblé exécuté selon le protocole défini par l'utilisateur** : relecture directe des deux journaux existants (300 événements `vote_cast` chacun, ticks d'élection 0/16/32) contre la règle §3.6.1 exacte (`blank=1` doit avoir un `ranking` vide) — **zéro violation trouvée dans les deux cas**, cohérent avec le `replays.log` vide de chacun des deux runs.
- Conclusion appliquée selon la règle de décision de l'utilisateur (caveat suffit si audit négatif ou isolé) : deux caveats ajoutés dans `THEORY.md` (§10.7 et §10.8), datés (2026-08-22), factuels — citant l'antériorité aux correctifs, le taux d'incohérence connu (~6,7% des appels `cast_votes`, mesuré dans `cache_recycle_chunk_size_tension_findings.md`), et le résultat de l'audit, avec conclusion explicite : "le résultat n'est pas invalidé, il reste non re-vérifié sous le code corrigé." Deux marqueurs `INVALID_PRE_GPU_FIXES.md` ajoutés (non destructifs, rien supprimé) à côté des deux runs concernés, pour qu'une future analyse de sensibilité (§11) ne les utilise pas comme référence propre sans vérifier d'abord si un re-run change le résultat.
- Travail commité en quatre commits séparés au total sur la journée, comme d'habitude sur ce projet — un commit par préoccupation :
  - `ca02344` — fix(polity): LLM batch reliability, bundle le fix `chamber_deliberation` chunk_size (10→5 rejeté→1) avec les correctifs `vote_cast` de la même investigation (chunk_size 3→1, retry à température variable 0.3, `_CHAMBER_THINK_TOKEN_ALLOWANCE` 4000→8000) — regroupés parce que les deux fils partagent le même mécanisme sous-jacent (`_complete_and_decode_with_replay`) et le même fichier.
  - `44abc75` — docs(polity): v6b Lot 4 acceptance run, sync `THEORY.md` §10.9 + `scripts/acceptance_v6b_results.md`.
  - `7e13894` — feat(polity): étape 3.1 post-harnais, capture best-effort du driver GPU/version CUDA dans `run_metadata.json` (`gpu_driver_version`, `gpu_cuda_version`), déclenchée seulement quand `config.llm.enabled`.
  - `6380f05` — docs(polity): étape 3.2 post-harnais, caveats `THEORY.md` §10.7/§10.8 sur les deux runs antérieurs aux correctifs de fiabilité, + marqueurs `INVALID_PRE_GPU_FIXES.md`.
  - Vérifié avant chaque commit : mypy clean, flake8 clean, suite complète (1548 → 1552 passed après les 4 nouveaux tests de l'étape 3.1, 41 skipped).

**Points bloquants**
- **Le run a réussi techniquement mais n'a pas tranché la question scientifique du §6bis.3 — le point le plus important de la journée, à ne pas édulcorer.** Sous le menu de pression complet (`both` — pétition + mobilisation), le président élu est rappelé par le plancher de légitimité en l'espace d'un seul tick après CHACUNE des deux élections du run (`L` chute de 0,43 à 0,12, puis de 0,44 à 0,11). Le poste reste vacant l'essentiel des 33 ticks du run. Résultat : `mandate_deviation` reste exactement à 0,0 sur toute la durée — pas parce que le président serait resté fidèle à son mandat, mais parce qu'il n'a presque jamais eu l'occasion de dériver (`representative_response`/dt=6 n'a presque jamais eu de titulaire à qui s'adresser). En parallèle, `chamber_deviation` (la chambre tirée au sort) reste authentiquement quasi nulle (moyenne 0,0001, maximum 0,035, 99,3% des décisions étiquetées `SINCERE_POSITION` par le modèle lui-même). La comparaison "sincère contre erratique" que ce run devait trancher est donc confondue par un phénomène distinct et lui-même intéressant : le menu de pression complet, combiné à l'apparat de responsabilité, produit un rappel quasi immédiat plutôt qu'une dérive mesurable à comparer.
- Un second run ciblé reste à concevoir pour trancher effectivement le §6bis.3, avec un paramétrage qui permette au mandat électif de survivre suffisamment longtemps pour être réellement comparable (ex : `electoral_only`, ou un plancher de rappel relâché) — pas encore autorisé à démarrer.

**Décisions prises**
- Valider chaque palier de réduction de chunk_size (10 → 5 → 1) contre l'état réel du run planté avant d'escalader au suivant, plutôt que de sauter directement à la valeur la plus prudente connue — *pourquoi* : consigne explicite de l'utilisateur de ne pas escalader à l'aveugle ; le palier 5 semblait un choix raisonnable par analogie mais s'est révélé insuffisant à la vérification, ce qui aurait été manqué sans ce test intermédiaire.
- Regrouper le fix `chamber_deliberation` et les correctifs `vote_cast` dans un seul commit plutôt que de les séparer artificiellement — *pourquoi* : les deux fils partagent le même mécanisme sous-jacent et le même fichier ; les séparer aurait cassé la cohérence de la revue sans bénéfice réel.
- Rapporter le résultat du run tel quel (vacance dominante, comparaison confondue) plutôt que de le reformuler pour qu'il ressemble à une conclusion propre — *pourquoi* : la valeur du run est dans ce qu'il révèle sur l'interaction pression/responsabilité, pas dans une réponse artificiellement nette à la question initiale.
- Archiver (pas supprimer) les 18 runs ratés/obsolètes qui polluaient le résumé — *pourquoi* : cohérent avec la discipline déjà établie sur ce projet de préserver la trace des runs plantés plutôt que de les effacer.
- Présenter la découverte des deux runs pré-fix (§10.7/§10.8) à l'utilisateur avant de toucher aux sections `THEORY.md` elles-mêmes — *pourquoi* : la décision de comment traiter des résultats déjà publiés mais potentiellement affectés par des bugs corrigés depuis appartient à l'utilisateur, pas à un choix unilatéral pris en cours de nettoyage.
- Suivre scrupuleusement le protocole en quatre temps fixé par l'utilisateur (caveat factuel d'abord, puis audit ciblé des journaux existants contre la règle §3.6.1, re-run seulement en cas de signal de concentration autour des moments clés) plutôt que d'improviser un re-run immédiat par excès de prudence — *pourquoi* : un re-run coûte plusieurs heures de calcul GPU (cf. le run du jour, ~4,55h) ; l'audit low-cost sur les journaux déjà produits permet de vérifier s'il y a un signal réel avant d'engager cette dépense — et le résultat (zéro violation) a confirmé que le caveat suffisait sans re-run, sans que cette conclusion soit décidée à l'avance.

**Prochaines étapes**
- [ ] Concevoir un second run ciblé v6b Lot 4 permettant au mandat électif de survivre assez longtemps pour être comparable à la chambre de sortition (ex : `electoral_only`, ou plancher de rappel relâché) — non autorisé à démarrer.
- [ ] Revoir si la découverte "rappel quasi immédiat sous menu de pression complet" mérite sa propre section théorique distincte de §10.9, ou reste une note dans cette dernière.

**Pour aller plus loin** : `fast_api_voter/scripts/lot3_chamber_reliability_results.md` (historique complet 10 → 5 → 1), `fast_api_voter/scripts/acceptance_v6b_results.md` (résultats détaillés du run), `THEORY.md` §10.7/§10.8 (caveats datés 2026-08-22) et §10.9, `docs/research/traceability.md`, `fast_api_voter/scripts/cache_recycle_chunk_size_tension_findings.md` (taux d'incohérence ~6,7% cité dans les caveats), run préservé `fast_api_voter/scripts/acceptance_v6b_runs/sortition-llm-8y-failed-chamber-deliberation-truncation-20260821/`, runs archivés dans `_archived_failed_runs/`, marqueurs `INVALID_PRE_GPU_FIXES.md` dans `acceptance_v5_runs/electoral_only-llm-8y-events-r0.15-s0.25/` et `acceptance_v6a_runs/contagion-llm-8y/`, entrée du 2026-08-19 pour le contexte complet de l'investigation bug 4.

---

## 2026-08-19 — Harnais de test lancé : la piste du volume de cache se confirme en partie, et révèle un mécanisme composite à trois étages

**Contexte du jour.** Reprise du chantier bug 4 (troncature `finish_reason='length'` sur Ollama) là où la session précédente l'avait laissé : un banc d'essai de reproduction fiable restait à construire, une mitigation "nonce inerte" restait à tester sans preuve. Avant de plonger dans le bug 4, vérification de deux morceaux de travail en attente de commit — wiring `chamber_deviation` (v6b Lot 4) et le nouveau harnais de test `llm_test_harness/` construit lors d'une session antérieure — avec la suite de tests complète.

**Ce qui a avancé**
- Suite de tests complète revérifiée avant de reprendre le chantier bug 4 : 1531 passed / 41 skipped sur `api/`, mypy et flake8 clean — couvre à la fois le wiring `chamber_deviation` (v6b Lot 4) et le package `llm_test_harness/` (jamais commité), tous deux encore en attente de commit.
- Exécution du prompt séquencé `prompt-sequencement-post-harnais.md`, étape 0 : diagnostic du run d'acceptance `sortition-llm-8y` laissé en cours d'une session précédente — trouvé interrompu au tick 0 pendant une resoumission de batch `vote_cast`, cohérent avec le risque déjà documenté (pas un échec inattendu).
- Confirmation indirecte (logs Windows Defender Operational, event 5007, faute de droits admin pour `Get-MpPreference`) que l'exclusion antivirus configurée pour le conteneur Ollama et les chemins Docker est bien active — trois exclusions retrouvées (deux chemins Docker + `ollama.exe`).
- Reconstruction déterministe du prompt réel ayant déclenché le bug (via `generate_population`/`initialize_parties` au seed=42, cid des nominés vérifiés contre les événements `candidacy_declared` du run interrompu), et calcul par le harnais de la taille d'échantillon nécessaire (n=97) pour le critère de décision pré-enregistré sur le taux de succès des resoumissions avec nonce.
- Caractérisation du taux d'échec de base (hors resoumission), décidée après un échec inattendu de l'appel d'amorçage lui-même : sur 10 appels frais et distincts, 5 échecs (IC de Wilson 95% [24%, 76%]) — nettement au-dessus du seuil de 20-30% attendu, ce qui invalide en l'état le plan de test du nonce tel que conçu.
- **Découverte inattendue, faite en croisant gratuitement les timestamps des essais avec les lignes `cache state: N prompts` des logs Docker du conteneur `ollama-polity`** : le cache de prompts de llama.cpp sur ce conteneur a une capacité mesurée de 8 prompts, et les échecs par troncature corrèlent avec sa saturation (remplissage 0→8 : succès ; une fois saturé/en éviction : échecs dominants). Reformule l'hypothèse du bug — peut-être pas "resoumission d'octets identiques" comme déclencheur, mais "volume de prompts distincts accumulés dans le cache" — une piste déjà évoquée dans `llm_batching_determinism_results_gpu.md` (section cross-request prompt-cache reuse) mais jamais testée jusqu'ici.
- **Résultat de l'expérience de volume de cache (4 sessions × 15 appels, terminée).** Critère pré-enregistré satisfait : ratio taux d'échec (cache saturé ≥8 prompts) / taux d'échec (cache<8) = 2.00 exactement (seuil ≥2x). Résultat plus frappant que le critère lui-même : le pattern exact d'échecs (rangs 1, 4, 8, 10, 11 sur 15) se reproduit à l'identique sur les 4 sessions indépendantes, malgré un redémarrage à froid complet entre chacune et un contenu/ordre strictement identiques — déterministe, pas du bruit stochastique, ce qui contredit directement la "variance énorme entre essais" observée avec le protocole nonce d'une session précédente (lequel, lui, variait le contenu à chaque tentative — possible que le nonce ait lui-même été la source du bruit observé alors). Répartition par niveau de cache réel (reconstruit depuis les logs Docker horodatés, après correction d'un bug dans le script d'analyse qui incluait des entrées résiduelles d'une session précédente) : cache={0,2,4,5,6} → 0 échec sur 24 essais ; cache=7 → 8 échecs sur 20 (40%) ; cache=8 (capacité max observée) → 4 échecs sur 8 (50%) — 80% de tous les échecs par troncature concentrés aux deux derniers niveaux avant/à saturation. Réserve importante : le design confond contenu, rang et niveau de cache (même séquence à chaque session) — corrélation nette, pas une preuve causale isolée.
- **Pivot demandé par l'utilisateur : investigation d'un second bug distinct trouvé en cours de route.** Le tout premier appel de chaque session échouait systématiquement (5/5 sur les expériences précédentes) selon un mode d'échec jamais vu jusque-là : `cid` renvoyés strictement égaux aux valeurs de `motif` (`CampaignMotif` 601-604) au lieu des vrais `citizen_id` attendus — une confusion de champs par le modèle, pas une troncature. Relecture de `llm_batching_determinism_results_gpu.md` : ce phénomène est déjà documenté sous le nom "Cold start vs. warm: a second, distinct determinism gap" — le tout premier passage d'inférence après un chargement de modèle à froid emprunte un chemin d'exécution GPU différent (heuristiques de sélection de kernel) — et une fonction `_warm_up_llm_client` existe déjà en production (`run_polity_simulation.py`) pour absorber cet effet via un appel jetable avant toute vraie décision, que les scripts de diagnostic de cette investigation n'appelaient jamais, contrairement au pipeline de production. Test direct (6 redémarrages à froid, avec `_warm_up_llm_client` appelé cette fois) : corruption cid=motif disparue (0/6) — confirme un bug déjà connu et déjà corrigé en production, pas un nouveau bug.
- **Un troisième problème révélé par ce même test, non résolu.** Avec le warm-up appliqué, l'appel réel qui suit immédiatement échoue maintenant 6/6, systématiquement par troncature (`finish_reason='length'`) — un échec différent, déplacé plutôt qu'éliminé. Hypothèse testée : le warm-up de production (budget de 32 tokens seulement, garanti de tronquer lui-même sous `think=True`) laisserait une entrée de cache corrompue contaminant l'appel suivant — réfutée en donnant au warm-up un budget généreux (1500 tokens, se termine proprement 6/6) : l'appel suivant échoue quand même 6/6, à l'identique. Nouvelle hypothèse, non testée : la forme du prompt de warm-up lui-même (un stub trivial `"{}"`, structurellement sans rapport avec un vrai prompt métier de plusieurs milliers de tokens) produirait une correspondance partielle de mauvaise qualité contre le cache — mécanisme déjà évoqué ("cross-request prompt-cache reuse") mais jamais testé avec une paire de prompts aussi dissemblable en taille. Confirmé sur données réelles, pas seulement synthétiques : dans le run interrompu `sortition-llm-8y`, `candidacy_considered` et `party_nomination_choice` utilisent tous deux `think=False` (vérifié dans le code), donc `campaign_positioning` était bien le tout premier appel `think=True` réel de ce run, juste après le warm-up de démarrage — et `replays.log` montre qu'il a échoué à sa première tentative avant de réussir au retry, exactement le pattern trouvé sur le banc synthétique.

**Points bloquants**
- **Bug 4, toujours non résolu formellement — mais le dossier est maintenant beaucoup plus riche.** Un mécanisme composite se dessine : comportement de cold-start du tout premier appel, déjà connu et déjà corrigé en production ; contamination structurelle probable liée à la forme du warm-up pour le second appel (hypothèse non testée) ; corrélation nette avec la saturation du cache au-delà (causalité non isolée). Aucune mitigation nouvelle déployée en code de production à ce stade.
- Le ratio 2.00 et la répartition par niveau de cache restent des résultats intermédiaires qui affinent le dossier, pas une résolution — le design de l'expérience confond contenu, rang et niveau de cache, donc rien de tout cela n'isole encore la cause exacte.
- L'hypothèse "forme du prompt de warm-up" n'est pas testée — reste à vérifier si un warm-up avec un prompt structurellement plus proche d'un vrai prompt métier change le résultat du second appel.
- Comment clore formellement l'étape 2 du prompt séquencé (décision sur le bug 4) reste en discussion au moment de la rédaction — pas encore tranché.
- Rien commité pendant cette session : `llm_test_harness/`, le wiring `chamber_deviation` + tests, et les mises à jour de `llm_batching_determinism_results_gpu.md` / ADR-001 restent en attente — ces deux derniers documents reflètent encore l'état d'avant cette session, pas les découvertes ci-dessus.

**Décisions prises**
- Mesurer d'abord le taux d'échec de base (hors resoumission) avant de continuer le test du nonce — *pourquoi* : l'appel d'amorçage, censé toujours réussir, a échoué deux fois de suite avec un nouveau mode d'échec (cid corrompus) au lancement du test ; poursuivre sans recalibrer aurait consommé le budget d'appels GPU sur un protocole déjà suspect.
- Pivoter vers une investigation du volume de cache comme variable continue plutôt que de forcer le protocole nonce/resoumission — *pourquoi* : la corrélation cache observée, gratuite (aucun appel GPU supplémentaire, croisement de logs déjà produits), rouvre une piste plus ancienne et mieux étayée mécaniquement que l'hypothèse resoumission-à-l'identique, elle-même déjà affaiblie par un cas de contrôle qui n'avait pas reproduit le bug la session précédente.
- Pivoter vers l'investigation du bug cid=motif avant de poursuivre l'analyse fine du volume de cache, à la demande de l'utilisateur — *pourquoi* : un second mode d'échec jamais vu, découvert en cours de route sur l'appel d'amorçage lui-même, méritait d'être élucidé avant de construire davantage sur une expérience potentiellement polluée par ce bug distinct.
- Tester l'hypothèse "budget de warm-up" avant l'hypothèse "forme du prompt" — *pourquoi* : ordre du moins coûteux/plus simple à écarter vers le plus coûteux à vérifier ; le budget de tokens se règle en une ligne, la forme du prompt demande une modification plus structurelle du warm-up de production.
- Ne pas committer le travail en attente (`llm_test_harness/`, `chamber_deviation`) tant que le fil bug 4 est ouvert — *pourquoi* : éviter de mélanger un commit de fonctionnalité stable avec une investigation encore mouvante, cohérent avec la discipline déjà établie sur ce projet de garder les scripts d'investigation jetables hors dépôt.

**Prochaines étapes**
- [ ] Tester l'hypothèse "forme du prompt de warm-up" (remplacer le stub `"{}"` par un prompt structurellement plus proche d'un vrai prompt métier) et vérifier si cela change le taux d'échec du second appel.
- [ ] Trancher comment clore l'étape 2 du prompt séquencé (décision sur le bug 4) — discussion en cours au moment de la rédaction.
- [ ] Reprendre les étapes 3-4 du prompt séquencé : nettoyage des dettes techniques (champ `inference_backend`, audit des runs pré-fix), retour au travail v6/v6b.
- [ ] Committer le travail stable en attente (`llm_test_harness/`, wiring `chamber_deviation` + tests) une fois découplé de l'investigation en cours.

**Pour aller plus loin** : `fast_api_voter/scripts/llm_batching_determinism_results_gpu.md` (sections cross-request prompt-cache reuse et "Cold start vs. warm: a second, distinct determinism gap", pas encore mises à jour avec les découvertes de cette session), `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`, rapport généré `fast_api_voter/scripts/bug4_baseline_rate_20260819T235545Z-89a6b3f4.md`, scripts de diagnostic ad hoc de session (`bug4_baseline_rate.py`, `bug4_cache_volume.py`, `bug4_first_call_warmup_check.py`, `bug4_warmup_budget_check.py` — hors dépôt, scratchpad).

---

## 2026-08-17 → 2026-08-18 — Bascule GPU d'Ollama : quatre bugs, une remise en question de la reproductibilité, et une décision d'architecture

**Contexte du jour.** Passage du conteneur `ollama-polity` de CPU à GPU
(RTX 5070 Ti, 16 Go VRAM) pour accélérer l'inférence locale. Attendu : un
simple gain de vitesse. Obtenu : quatre bugs distincts, une remise en
cause sérieuse (puis partiellement rassurante) de la reproductibilité du
pipeline, et une première décision d'architecture documentée en ADR.

**Ce qui a avancé**
- Conteneur Ollama recréé avec `--gpus=all` : confirmé à 100% GPU via
  `ollama ps` (au lieu de 100% CPU).
- **Bug 1 résolu — context-shift silencieux.** Au-delà de ~1800 tokens de
  raisonnement, `num_ctx` jamais fixé par `llm_client.py` (et de toute
  façon ignoré sur l'endpoint OpenAI-compat) laissait le contexte par
  défaut à 4096, provoquant un écrasement silencieux du system prompt en
  cours de génération. Fix : `OLLAMA_CONTEXT_LENGTH=16384` au niveau du
  conteneur. Documenté dans `scripts/ollama_context_window_results.md`.
- **Bug 2 résolu — budget de tokens `decide_campaign_positioning`.**
  `_POSITIONING_THINK_TOKEN_ALLOWANCE` sous-calibré (4000 tokens,
  insuffisant pour un prompt à 5 nominees). Doublé à 8000, vérifié 5/5
  propre avec marge. Suite complète (1526 tests), mypy, flake8 passés.
- **Bug 3 (`cast_votes`) — diagnostic réorienté, pas résolu par un simple
  ajustement de budget.** Signature identique au bug 2 en apparence, mais
  170 tentatives de réplique sur d'anciens chunks dumpés ont toutes échoué
  à reproduire l'erreur — parce que ces chunks dataient d'avant le fix du
  bug 2, et que `vote_cast` dépend en entrée des sorties de
  `decide_campaign_positioning` (dépendance de pipeline jusque-là non
  versionnée dans les dumps de debug).
- **Découverte n°1 — non-reproductibilité au niveau d'un appel isolé,
  confirmée puis largement expliquée.** Un run identique rejoué deux fois
  (même seed, température=0) a divergé dès le tout premier appel LLM du
  pipeline (prompt byte-identique, réponse brute différente), avec effet
  de cascade sur le nombre de candidats retenus. D'abord attribué à un
  non-déterminisme structurel du modèle sur `think=True` (hypothèse
  sérieuse un temps), puis **largement expliqué par un phénomène de
  cold-start GPU** : le modèle est déterministe à 16/16 une fois "chaud",
  et diverge seulement sur le tout premier appel après (re)chargement.
  Confirmé par un test de causalité propre (cycles forcés à froid,
  convergence identique aux reps 2-8 du test précédent).
- **Mitigation cold-start appliquée et vérifiée.** Warm-up (appel factice
  avant la première décision réelle du run) + `OLLAMA_KEEP_ALIVE=60m` au
  niveau conteneur (contre une expiration en cours de run), les deux
  documentés comme complémentaires (fenêtres de risque différentes — l'un
  couvre le tout premier appel, l'autre les suivants). Commit isolé
  proprement du travail Lot 4 en cours (conflit de stash résolu à la
  main, suite complète revérifiée à 1531 tests après réintégration).
- **Spike `llama-server` mené à son terme (16 min, dans le budget de 3h
  alloué).** N'a jamais reproduit le bug de cache-reuse (bug 4,
  ci-dessous), ni à charge légère ni à charge lourde réaliste, avec les
  mêmes poids et le même prompt que la production. Résultat honnêtement
  qualifié d'inconclusif sur la preuve d'immunité, mais cohérent avec
  l'hypothèse que les bugs 1 et 4 sont spécifiques à la couche
  d'orchestration d'Ollama, pas au modèle ni à `llama.cpp` en général.
- **Décision d'architecture actée en ADR** (`docs/adr/ADR-001-serving-
  layer-ollama-vs-llama-server.md`) : rester sur Ollama pour l'instant, ni
  bascule `llama-server`, ni accélération du calendrier vLLM — le
  bénéfice du spike reste non confirmé face au coût d'un nouveau chemin de
  déploiement non vérifié (même calcul déjà fait pour `VllmJsonClient`).

**Points bloquants**
- **Bug 4 — cache-reuse cross-requête d'Ollama (non résolu, le plus
  sérieux actuellement).** Logs montrant un `f_keep` bas juste avant des
  générations qui partent en dérive (`finish_reason='length'` après
  9700+ tokens). Cause probable : le cache de prompt cross-requête
  interne d'Ollama, sur une correspondance partielle de faible confiance,
  semble corrompre la génération — mécanisme distinct du bug 1, non
  couvert ni par `num_ctx` ni par le warm-up. Un test de causalité a
  écarté `f_keep` bas comme cause suffisante isolée (aucun effet sur un
  prompt court `think=False`) — l'interaction avec un raisonnement long
  `think=True` reste nécessaire, mécanisme exact non isolé.
- **La mitigation `--max-batch-replays` ne protège pas contre le bug 4 —
  découverte a posteriori, après un relaunch qui a échoué 6/6.** Le
  motif observé (OK à la 1ère soumission d'un prompt donné, FAIL
  systématique aux resoumissions identiques suivantes) montre que rejouer
  des octets identiques aggrave la situation plutôt que de l'absorber par
  hasard — l'inverse de l'hypothèse sur laquelle la mitigation reposait.
- **Tentative de fiabiliser un banc d'essai de reproduction du bug 4 —
  en cours.** Un premier test de mitigation par variation (nonce inerte
  dans le payload) s'est révélé inconclusif : le cas de contrôle
  (répétition à l'identique) n'a pas reproduit le bug ce jour-là,
  contrairement à un test antérieur qui l'avait montré 2/2. Hypothèse
  actuelle, non confirmée : effet lié au volume de prompts déjà en cache
  (conteneur "chaud avec historique varié" vs conteneur frais) plutôt
  qu'à la seule identité octet-pour-octet du prompt rejoué.
- Aucun champ `inference_backend` dans les métadonnées de run — toujours
  absent.
- Runs journalisés (v6, v6b) produits avant l'ensemble de ces fixes —
  toujours pas audités/marqués comme potentiellement invalides.

**Décisions prises**
- Traiter la non-reproductibilité comme priorité bloquante avant toute
  reprise de la chasse aux bugs de budget de tokens au cas par cas —
  *pourquoi* : patcher un symptôme (bug 3) sans comprendre la cause de
  fond (reproductibilité) risquait de produire un fix qui ne tient pas
  au run suivant — confirmé a posteriori par l'échec de la mitigation
  `--max-batch-replays`.
- Ne pas basculer vers `llama-server` ni accélérer vLLM sur la seule foi
  d'un spike inconclusif — *pourquoi* : un problème partiellement
  caractérisé (Ollama) ne doit pas être échangé contre un problème pas
  caractérisé du tout, même si deux bugs sur quatre pointent vers la
  couche wrapper d'Ollama plutôt que le modèle.
- Fiabiliser un banc d'essai de reproduction du bug 4 avant d'appliquer
  une mitigation (nonce ou autre) sans preuve — *pourquoi* : éviter de
  répéter l'erreur qui vient de coûter un relaunch complet raté (mitiger
  sans avoir vérifié que la mitigation fonctionne dans les conditions
  réelles de déclenchement).

**Prochaines étapes**
- [ ] Rejouer la recette « conteneur chaud + ~9 appels d'historique varié
      + resoumission identique » 2-3 fois pour confirmer qu'elle
      déclenche le bug 4 de façon fiable.
- [ ] Si confirmée : tester le nonce inerte (ou une autre variation
      sémantiquement neutre) contre ce banc avant tout déploiement.
- [ ] Si la reproduction fiable échoue : décider explicitement entre
      repli documenté (nonce non vérifié, jugé sur le run réel) et
      creuser davantage — pas de décision par défaut.
- [ ] Ajouter le champ `inference_backend` aux métadonnées de run.
- [ ] Auditer les runs déjà journalisés (v6, v6b) produits avant ces
      fixes, et les marquer comme non valides pour une future analyse de
      sensibilité.
- [ ] Une fois le bug 4 traité : relancer l'acceptance run v6b.

**Pour aller plus loin** : `scripts/ollama_context_window_results.md`,
`llm_batching_determinism_results_gpu.md` (avec ses notes de correction
datées), `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`,
`audit-precision-plan.md` (§4 du plan de conception, prérequis de
reproductibilité).

---

## 2026-08-19 — Mise en place du journal de bord et reconstruction rétroactive de l'historique du projet

**Contexte du jour.** Réception de l'outillage du journal de bord
(sub-agent `journal-writer`, commande `/log-session`, gabarit de
reconstruction rétroactive) livré sous forme de 4 fichiers dans un
dossier `files/` à la racine du repo. Objectif : installer cet
outillage à ses emplacements définitifs, puis l'utiliser une première
fois pour reconstruire l'historique du projet depuis son tout premier
commit.

**Ce qui a avancé**
- Rangement des 4 fichiers reçus à leurs emplacements définitifs :
  `.claude/agents/journal-writer.md`, `.claude/commands/log-session.md`,
  `docs/journal/JOURNAL_DE_BORD.md` (pré-rempli avec l'entrée GPU du
  17-18/08), `docs/journal/prompt-reconstruction-retroactive-journal.md`
  — dossier `files/` supprimé une fois le rangement terminé.
- **Incohérence trouvée et corrigée** : `journal-writer.md` et
  `JOURNAL_DE_BORD.md` référençaient une commande `/journal`
  inexistante — le fichier de commande s'appelle `log-session.md`, donc
  la commande réelle est `/log-session`. Corrigé aux deux endroits.
- **Reconstruction rétroactive menée à son terme** : tentative d'accès à
  une conversation claude.ai fournie par l'utilisateur en source
  privilégiée — échec en 403 Forbidden (conversation privée, non
  accessible sans authentification). Reconstruction effectuée à la
  place à partir de `git log --all` (1177 commits sur l'ensemble du
  dépôt) et des documents datés du repo
  (`polity-simulation-design-v2.md`, `audit-precision-plan.md`,
  `dev-plan-v0-worktree.md`, `DEMARRAGE-polity-v0.md`), complétée pour
  les paliers polity récents par les notes de session conservées dans
  la mémoire de l'agent (source hors périmètre strict du prompt de
  reconstruction, mais explicitement signalée comme telle).
- **16 entrées reconstruites**, présentées à l'utilisateur pour
  validation, validées telles quelles ("appliquer tel quel"), puis
  insérées dans `JOURNAL_DE_BORD.md` en ordre chronologique inverse
  (16 août 2026 en remontant jusqu'à mars 2025), à la suite de l'entrée
  GPU déjà en place. Chaque entrée reconstruite porte la mention
  explicite de sa méthode de reconstruction en tête, conformément au
  gabarit de reconstruction rétroactive.

**Points bloquants**
- Aucun nouveau — session d'outillage et de documentation, pas de code
  modifié.

**Décisions prises**
- Poursuivre la reconstruction sans la conversation claude.ai source
  malgré l'échec d'accès, plutôt que d'attendre un export manuel —
  *pourquoi* : le git log et les documents datés du repo couvraient déjà
  la majorité des paliers avec un niveau de détail suffisant pour une
  narration honnête, et les notes de session en mémoire comblaient le
  reste pour les paliers récents.
- Ne pas rédiger d'entrée pour une éventuelle relance de l'acceptance
  run v6b après l'entrée GPU, malgré la présence de fichiers non
  trackés (`run_v6b_acceptance.py`, `acceptance_v6b_runs/`) suggérant un
  travail en cours — *pourquoi* : aucune preuve datée (commit ou
  document) ne permettait de confirmer si, quand, ni avec quel résultat
  cette relance a eu lieu ; signalé comme observation non confirmée
  plutôt que comme fait acté.

**Prochaines étapes**
- [ ] Reprendre le fil laissé en suspens par l'entrée GPU du 17-18/08 :
      fiabiliser le banc d'essai de reproduction du bug 4 (cache-reuse
      cross-requête d'Ollama).
- [ ] Clarifier le statut des fichiers non trackés liés à v6b
      (`run_v6b_acceptance.py`, `acceptance_v6b_runs/`,
      `sortition_calibration_runs/`) — travail en cours à documenter,
      ou artefacts à nettoyer.
- [ ] Utiliser `/log-session` en routine à la fin des prochaines
      sessions significatives, maintenant que l'outillage est en place.

**Pour aller plus loin** : `.claude/agents/journal-writer.md`,
`.claude/commands/log-session.md`,
`docs/journal/prompt-reconstruction-retroactive-journal.md`.

---

## 2026-08-16 — Palier v6b, Lots 1-3 : la chambre de tirage au sort, jusqu'à sa première décision LLM

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #151-153) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_v6b_lot1_sortition_config.md`, `project_polity_v6b_lot2_sortition_chamber.md`, `project_polity_v6b_lot3_chamber_deliberation.md`).

**Contexte du jour.** Immédiatement après la clôture de v6a (bloc 15), démarrage du second volet de v6 : une chambre législative tirée au sort, groupe de contrôle contre lequel comparer la dérive de mandat de l'élu.

**Ce qui a avancé**
- **Lot 1 (config+codebook)** : §6bis.3 identifié par grep comme la section la moins spécifiée de tout le plan de conception (4 mentions seulement, aucune sous-section §3.6.x, aucun concept de "loi"/proposition législative nulle part dans le code sur lequel le pouvoir de veto de la chambre pourrait s'exercer). Soumis explicitement à l'utilisateur via `AskUserQuestion` avant toute planification — **l'utilisateur choisit un MVP, le veto est différé** à un futur palier nécessitant un concept de légifération qui n'existe pas encore. Une vraie collision trouvée en implémentation : le plan proposait les codes motif 501/502, déjà utilisés par `CoalitionMotif` — corrigé vers une plage neuve 700-799 avant d'écrire quoi que ce soit.
- **Lot 2 (`sortition_chamber.py`)** : **le risque de calibration déjà signalé au Lot 1 se confirme, mesuré, pas seulement calculé à la main** — à la config par défaut, l'éligibilité stricte "jamais servi" viderait complètement la chambre à partir du tick 16 (87,5% d'un run complet). Résolu par une sélection à deux niveaux : bassin strict tant qu'il peut remplir les sièges, puis relaxation à "pas actuellement siégeant" — la relaxation s'engage *proactivement* (dès le tick 12), la chambre n'est en réalité jamais sous-dimensionnée. Un second vrai bug de signature trouvé en implémentation : `InstitutionalClock.from_config` cherchait `sortition_chamber` sous `institutions`, alors qu'il s'agit d'un champ de premier niveau — corrigé sur les quatre points d'appel concernés.
- **Lot 3 (`chamber_deliberation`, dt=11, la décision LLM)** : chaque membre siégeant reçoit une délibération LLM entièrement isolée de tout canal de pression du §7bis — aucune exposition à la dérive de mandat, ni pression de rue, ni pétition, ni plancher de légitimité. **Deux vrais bugs de fiabilité trouvés par le spike et corrigés dans le code** : la règle de cohérence shifts↔motif échouait à haut taux face au vrai modèle (9/10 rejetés sur un lot de 10) — retirée entièrement, même précédent que la décision de pression de v6a Lot 3 ; un appel de 30 (et même un chunk de 15) laissait tomber silencieusement toutes les décisions sauf les 6 dernières, cause racine tracée à deux tableaux flottants 20-dimensions envoyés en clair par membre — résolu par une constante de taille de chunk dédiée, plus petite, distincte de `MIN_SAFE_BATCH_SIZE`.

**Points bloquants**
- Aucun restant en fin de journée pour ces trois lots. v6b est 3 de 4 lots planifiés — le Lot 4 (acceptance, comparaison élu vs tiré-au-sort) n'est pas encore autorisé.

**Décisions prises**
- Différer le pouvoir de veto à un futur palier plutôt que l'implémenter en MVP — *pourquoi* : décision de l'utilisateur, faute d'un concept de "loi"/proposition législative sur lequel un veto pourrait porter dans le code existant.
- Dispatcher `chamber_deliberation` directement depuis la boucle de tick plutôt que dans la phase d'accountability — *pourquoi* : la garde de retour anticipé de cette phase n'a pas de disjonction `sortition_chamber.enabled`, et la chambre est architecturalement indépendante de la boucle d'accountability présidentielle.

**Prochaines étapes**
- [ ] v6b Lot 4 : acceptance — comparaison de trajectoire `mandate_deviation` (élu) vs `chamber_deviation` (tiré au sort), clôture du palier v6b.

**Pour aller plus loin** : `lot3_chamber_reliability_results.md`, PR #151-153.

---

## 2026-08-16 — Palier v6a complet : le graphe social et la contagion de mobilisation

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #147-150) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_v6_lot1..3_*.md`, `project_polity_v6a_lot4_acceptance.md`).

**Contexte du jour.** Les quatre lots du palier v6a (config, génération de graphe, câblage de la contagion, acceptance) tous conçus, implémentés et fusionnés dans la même journée — le graphe social (§5) et la chambre de tirage au sort (§6bis.3) sont deux fonctionnalités structurellement indépendantes que le plan de conception lui-même déconseille de valider simultanément ; scindées en v6a (ce jour) et v6b (jour suivant, bloc 16).

**Ce qui a avancé**
- **Lot 1 (config+codebook)** : parse le bloc `social_graph:` déjà réservé mais jamais consommé. `evolving` (réécâblage homophile du graphe) est parsé pour échouer bruyamment sur une faute de frappe mais rejeté purement s'il est activé — le point ouvert 🔴 du plan de conception (graphe statique ou évolutif ?) reste réellement ouvert, ceci n'est qu'une garde de parsing.
- **Lot 2 (`social_graph.py`)** : choix `networkx` vs implémentation numpy maison **tranché par mesure réelle**, pas par supposition — zéro dépendance transitive, accepte nativement le générateur RNG du projet, byte-reproductible confirmé, jamais de nœud isolé sur Watts-Strogatz à l'échelle livrée contrairement à Erdős–Rényi (confirmé, documenté comme état légitime à gérer, pas un bug). Correction en cours d'implémentation : le plan approuvé prévoyait de câbler un objet graphe inutilisé dans l'orchestration — retiré, car contrairement aux générateurs de choc (v5 Lot 2), le graphe n'a rien à observer avant le Lot 3.
- **Lot 3 (`neighbors_acting`)** : retire la garde `NotImplementedError` de la porte d'éveil. Résolution du verbe "déjà mobilisée" du plan de conception : compte uniquement le dernier acte `MOBILIZE` *appliqué* d'un voisin (jamais signature/lancement de pétition, catégorie distincte), et scopé à la même cible (un voisin mobilisé contre un élu depuis parti ne compte pas pour le nouveau). Décalage d'un tick, même registre que le décalage `street_pressure` du Lot 6 de v4 : un lot entier de décisions est figé avant que rien n'atterrisse.
- **Lot 4 (acceptance — atomisé vs contagion)** : un seul bras nouveau nécessaire (les runs "mobilisation seule" déjà commités du v4 Lot 8 servent tels quels de référence "atomisée", confirmé par inspection directe qu'ils ne touchent jamais `social_graph`/`events`). **Résultat honnête et nuancé, pas l'histoire naïve "la contagion amplifie la mobilisation"** : sur le mélange cumulé de leviers, la part `MOBILIZE` était en fait légèrement *plus basse* sous contagion (0,629 vs 0,699 atomisé) et la légitimité moyenne finale *plus haute* (0,475 vs 0,370) — la contagion n'est pas un multiplicateur d'amplitude. Ce qu'elle produit réellement : un pic de synchronisation au niveau du tick sans équivalent atomisé — jusqu'à 85 citoyens sur ~100 mobilisés au même tick sous contagion+LLM, contre un maximum de 39 sur la baseline déterministe appariée.
- **Un vrai bug attrapé par le test, pas supposé** : le script d'acceptance ne sérialisait jamais trois champs de métriques pourtant lus par `summarize()` — `KeyError` au tout premier appel, après ~2h de run LLM déjà terminé. Corrigé sans re-lancer le run coûteux, en ré-indexant directement depuis le journal déjà écrit sur disque.

**Points bloquants**
- Aucun restant — v6a est déclaré complet en fin de journée.

**Décisions prises**
- Découpler l'activation de `PressureContext.neighbors_acting` de la modulation de la porte d'éveil — *pourquoi* : le graphe peut alimenter le contexte de dt=10 comme signal d'observabilité pur sans gater mécaniquement qui est consulté, un bras expérimental réel que le Lot 1 avait explicitement préservé.
- Formuler le résultat comme "la contagion change la forme temporelle de la mobilisation (pics synchronisés), pas son volume agrégé, sur cette graine (n=1)" plutôt que revendiquer un effet d'amplification — *pourquoi* : c'est ce que les chiffres montrent réellement, et une revendication plus large ne serait pas soutenue par une seule graine.

**Prochaines étapes**
- [ ] v6b : la chambre de tirage au sort (§6bis.3), scindée de v6a dès le départ.

**Pour aller plus loin** : `THEORY.md` §10.8, PR #147-150.

---

## 2026-08-15 — Vote blanc compétitif (Lot 9) et palier v5 complet en une seule journée : événements exogènes, l'« étincelle »

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #141-146) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_lot9_blank_vote.md`, `project_polity_v5_lot1..5_*.md`), qui documentent chaque bug et chaque correction en cours de route.

**Contexte du jour.** Journée exceptionnellement dense : clôture du dernier item différé de v4 (le vote blanc compétitif), puis les cinq lots complets du nouveau palier v5 (événements exogènes, §8) — configuration, générateurs de choc, extension de la porte d'éveil, décision LLM, et acceptance — tous conçus, implémentés et fusionnés le même jour.

**Ce qui a avancé**
- **Lot 9 (§6bis.2, vote blanc compétitif)** : une élection présidentielle s'invalide quand la part de bulletins classant le blanc en tête dépasse un seuil ; un second tour est programmé, le calendrier fixe est *suspendu* (pas simplement cumulé) jusqu'à résolution ; les candidats de l'élection invalidée sont exclus du second tour (cumulatif à travers les invalidations répétées). **Un vrai bug attrapé par un test qui échouait réellement, pas juste raisonné** : les nouvelles clés `attempt`/`forced` étaient gatées uniquement sur le flag de config, ce qui changeait les octets du journal pour *chaque* élection dès l'activation du flag, même sans aucun candidat — l'hypothèse du plan ("aucun citoyen ne franchit jamais le seuil d'ambition") s'est révélée incomplète (des candidats *peuvent* exister même quand aucune élection ne produit de vainqueur). Corrigé en gatant aussi sur la non-vacuité des candidats.
- **v5 Lot 1 (config+codebook)** : décision structurante — un choc **ne touche jamais directement** la légitimité ; il perturbe la porte d'éveil via un nouveau champ `event_salience` décroissant, qui augmente la consultation — tout le reste passe par le chemin `pressure_action` déjà existant, gouverné par le LLM.
- **v5 Lot 2 (`shock.py`)** : processus de scandale (tirage Bernoulli par tick) + climat économique AR(1). Une vraie mine trouvée en planification : la garde `NotImplementedError` du Lot 1 sur `event_salience` était en fait atteignable indépendamment de `llm.enabled` — protégée seulement par une marge de sécurité étroite (le seuil d'ambition par défaut ne produit jamais de vainqueur au seed=42), pas une garantie structurelle.
- **v5 Lot 3 (`event_salience` + extension de la porte d'éveil + baseline déterministe)** : retire la garde du Lot 2. Deux vrais bugs trouvés et corrigés pendant la planification elle-même (ordre du "step 0" dans la séquence d'accountability corrigé pour matcher la roadmap littéralement ; une cible de scandale capturée une seule fois au tirage plutôt que recalculée en aval, pour éviter une désynchronisation silencieuse sur un tick où scandale et élection coïncident).
- **v5 Lot 4 (`reaction_to_event`, dt=8, la décision LLM)** : forme de message re-dérivée contre le schéma réellement livré des décisions voisines plutôt que gardée telle qu'esquissée dans la roadmap initiale — `ctx.self_gap`/`mandate_dev` abandonnés pour une raison dure (ils exigent un élu réel, qui n'existe pas en vacance présidentielle, alors que dt=8 tourne sur toute la population, vacance ou non). Spike live 12/12 sur qwen3:8b.
- **v5 Lot 5 (acceptance — l'« étincelle »)** : une vraie correction trouvée en direct pendant l'implémentation — l'arme "les deux" (menu de pression complet) faisait rappeler le président en 1-2 ticks sur presque chaque élection, laissant le poste vacant ~82% d'un run de 8 ans, écrasant justement le signal à mesurer. Basculé sur `electoral_only`. Résultat mesuré : taux de consultation 0,695 sur un tick avec choc contre 0,595 sur un tick calme — ratio 1,168, l'« étincelle » est réelle et dans le sens prédit. `mandate_deviation` n'est pas une dérive continue comme supposé mais une concession ponctuelle suivie d'un plateau — nuance honnêtement documentée dans `THEORY.md` §10.7.

**Points bloquants**
- Aucun restant en fin de journée pour le palier v5 — les 5 lots sont clos, `THEORY.md` synchronisé.
- Explicitement **pas** revendiqué : un effet de cascade (`neighbors_acting` reste structurellement `null` à travers tout v5) — scope réservé à v6.

**Décisions prises**
- Regrouper scandale (Poisson) et choc économique (AR(1)) dans un seul lot (Lot 2) plutôt que les séparer — *pourquoi* : même type de décision, même emplacement de séquencement, même point d'arrivée ; les séparer aurait produit un point d'arrêt intermédiaire ininterprétable.
- Basculer l'arme d'acceptance de "les deux" à `electoral_only` en cours de route — *pourquoi* : un dry-run de calibration a montré que l'arme initialement prévue rendait le poste vacant la majorité du temps, empêchant structurellement de mesurer le signal visé.

**Prochaines étapes**
- [ ] v6 : le graphe social (§5), prérequis explicite de l'effet de cascade que v5 ne revendique pas.

**Pour aller plus loin** : `THEORY.md` §10.7, `events_calibration_results.md`, `acceptance_v5_results.md`, PR #141-146.

---

## 2026-08-14 — Clôture du palier v4 : acceptance à 4 modalités, deux bugs LLM réels à l'échelle réelle, bascule vLLM et stockage DuckDB

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #138-140) et des notes de session contemporaines conservées dans la mémoire de l'agent (`project_polity_v4_lot8_llm_reliability.md`, `feedback_llm_reliability_investigation.md`, `project_polity_vllm_switch.md`, `project_polity_storage_duckdb.md`), qui documentent le raisonnement derrière chaque bug et chaque choix au-delà de ce que montre le diff seul.

**Contexte du jour.** Le run d'acceptance du Lot 8 (100 citoyens, 20 dimensions d'enjeu, vraie diversité de candidats, runs de 8 ans, 4 modalités de menu de pression) fait ce que les spikes de fiabilité de chaque lot précédent ne faisaient pas : tourner à échelle réelle de production. Deux bugs de qualité de contenu LLM, invisibles à tous les spikes précédents (qui ne vérifiaient que la validité du schéma, jamais la plausibilité du contenu), en sortent.

**Ce qui a avancé**
- **`indexer.py`** livré — le module de réduction de métriques par relecture du journal, nommé mais jamais construit depuis v0.
- **Bug 1 — `decide_campaign_positioning`** : produisait un lot 100% reproductible et dégénéré (un candidat dupliqué, les autres perdus) pour une combinaison de candidats réellement récurrente. Corrigé par `think=True` + un budget de tokens plus large, mesuré.
- **Bug 2 — `cast_votes`** : produisait 100% de bulletins présidentiels blancs à l'échelle réelle (100 votants × 5 candidats × 20 dimensions). Cause racine : le modèle devait juger l'acceptabilité d'un candidat à partir de vecteurs bruts sans définition opérationnelle — exactement le calcul de distance pondérée que la baseline déterministe effectue déjà. Corrigé en précalculant cette distance et en la fournissant au modèle comme un nombre simple, plus une règle mécanique explicite ; ajout de `VoteMotif.ACCEPTABLE_MATCH` (105), aucun motif existant ne décrivant un vote sincère pour un candidat imparfait mais tolérable.
- **Décision méthodologique explicite de l'utilisateur, actée ce jour-là** : face à une sortie suspecte (100% de blanc), investiguer la cause racine plutôt que mitiger rapidement (augmenter les répétitions, raccourcir les délais) — même au prix d'un temps significatif. Le vote blanc doit rester un dernier recours pour le citoyen simulé, jamais une valeur par défaut quand le modèle est incertain.
- Les 4 modalités tournent proprement : 12/12 élections présidentielles remportées, zéro répétition nécessaire, zéro erreur.
- **Bascule vLLM** (`VllmJsonClient`, dispatch par `provider`) livrée en code/config, **jamais vérifiée en direct** faute de serveur GPU disponible dans cet environnement — le `provider` par défaut reste `ollama` explicitement pour cette raison, et parce que `qwen3:8b` sur Ollama est un GGUF quantisé alors que `Qwen/Qwen3-8B` sur vLLM serait en bf16 — poids différents, aucun résultat déjà commité ne transfère.
- **Stockage DuckDB** (`compaction.py`) : résolution du point ouvert §16.6 (DuckDB plutôt que Postgres — aucune stack SQL préexistante, DuckDB embarqué = zéro nouvelle infrastructure). Décodage volontairement restreint au seul champ `motif` (jamais de réécriture du journal brut). Un gotcha DuckDB réel documenté : `x = 'a' AND payload ->> '$.k' = 'b'` non parenthésé mixe mal la précédence et tente de caster tout le payload JSON en nombre.

**Points bloquants**
- Aucun bloquant restant en fin de journée pour le palier v4 lui-même. La bascule vLLM reste **non vérifiée en direct** — reportée explicitement jusqu'à ce qu'un hôte GPU soit disponible.

**Décisions prises**
- Root-cause complet plutôt que mitigation rapide sur les deux bugs de qualité LLM — *pourquoi* : décision explicite de l'utilisateur, motivée par une opinion de modélisation substantielle (le vote blanc doit représenter un vrai désaveu, pas un artefact d'incertitude du modèle).
- Le `provider` par défaut reste `ollama` malgré la bascule vLLM livrée — *pourquoi* : rien n'a été vérifié en direct côté vLLM, et les poids diffèrent (GGUF quantisé vs bf16) — aucun résultat déjà mesuré ne transfère sans nouvelle vérification.

**Prochaines étapes**
- [ ] Lot 9 : vote blanc compétitif (§6bis.2), seul item du palier v4 explicitement différé.
- [ ] Si un hôte GPU devient disponible : vérifier vLLM en direct avant de basculer le `provider` par défaut.

**Pour aller plus loin** : `acceptance_v4_results.md`, PR #138-140, mémoire `project_polity_v4_lot8_llm_reliability.md`.

---

## 2026-08-11 → 2026-08-12 — Polity v4 Lots 6-7 : les deux premières décisions LLM du palier — le mandat peut enfin dériver

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #136-137).

**Contexte du jour.** Après cinq lots de substrat purement déterministe (bloc 11), branchement des deux premières décisions LLM du palier v4 : `representative_response` (l'élu répond à la pression) et `pressure_action` (le citoyen choisit sa pression). À partir d'ici, toute déviation de mandat mesurée est attribuable au LLM.

**Ce qui a avancé**
- **Lot 6 — `representative_response` (dt=6)** : "schéma central de la révision 2" du plan de conception. Spike de fiabilité préalable (16/16 propre sur des lots de 1/3/5/10, via `think=False` sur l'endpoint natif Ollama plutôt que `/v1`) — a aussi révélé honnêtement un défaut d'alignement préexistant sur `decide_campaign_positioning`, déjà livré, sous les mêmes conditions. Le décalage d'un tick (§7bis.7) est réalisé par position d'appel : un appel batché unique tout en haut de la phase d'accountability, avant que la boucle par élu ne mute `street_pressure` — vérifié par un test structurel (muter `street_pressure` après construction du contexte ne peut pas atteindre le prompt). Aucune fonction de repli déterministe : sans LLM, rien ne peut jamais faire diverger `revealed_position` de `pledged_platform`, l'absence d'appel EST le repli.
- **Lot 7 — `pressure_action` (dt=10)** : remplace la baseline déterministe derrière `config.llm.enabled` pour chaque citoyen "éveillé". Réconciliation d'un appel batché figé par tick avec l'état de pétition vivant intra-tick du Lot 5 via un découpage à deux niveaux : le menu constitutionnel est validé et peut rejeter tout le lot (contrainte dure) ; l'état de pétition réel (peut-on signer/lancer *maintenant*) est résolu à l'application, en dégradant un acte devenu caduc plutôt qu'en avortant tout le lot. Spike de confirmation contre le vrai schéma de production (tailles 1/5/20/25, deux modalités de menu, 16/16 propre) puis vérifié live.

**Points bloquants**
- Aucun bloquant restant — les deux lots passent en test hors-ligne (1030 puis suite étendue) et en test live contre le vrai modèle.

**Décisions prises**
- Activer `representative_response` sur `config.llm.enabled ET config.mandate.enabled`, sans nouvelle clé de config — *pourquoi* : garde les deux tests de reproductibilité byte-à-byte LLM existants inchangés, et offre au Lot 8 (acceptance) un bras de contrôle gratuit (leviers de pression actifs, mandat désactivé = le contrôle pur du §7bis.5).
- `revealed_position` accumule la dérive à partir de sa propre valeur courante, jamais de `pledged_platform` — *pourquoi* : c'est ce qui rend `mandate_deviation` non-nul pour la première fois de l'histoire du projet, et fait volontairement diverger l'identité `keep_ratio == mandate_strength` du Lot 5.

**Prochaines étapes**
- [ ] Lot 8 : acceptance, comparaison des 4 modalités de pression, clôture du palier v4.

**Pour aller plus loin** : PR #136-137, `lot6_batch_reliability_results.md`.

---

## 2026-08-09 → 2026-08-10 — Polity v4 Lots 1-5 : légitimité, mandat, pression citoyenne — le substrat déterministe avant tout LLM

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #131-135).

**Contexte du jour.** Premier tiers du palier v4 (légitimité/accountability/pression, §7bis) : cinq lots construisent l'ensemble du substrat mécanique — `L(t)`, écart de mandat, porte d'éveil, action de pression, pétition, vote de confiance — entièrement sans LLM, pour que toute dérive observée à partir du Lot 6 soit imputable au LLM et à rien d'autre.

**Ce qui a avancé**
- **Lot 1** : surface de config (5 nouvelles dataclasses) + réservations codebook (dt=6/dt=10), zéro changement de comportement.
- **Lot 2** : champs `Citizen` (`base_threshold`, `legitimacy_capital`), `accountability.py` (mandate_deviation, self_gap — primitive de distance pondérée réutilisée du vote), phase d'accountability par tick (mesure seule, aucune mutation encore).
- **Lot 3** : `legitimacy.py` — `L(t)` réel. Point de conception central : `L0 = f(force du mandat) = identité` — le seul choix sous lequel `update_legitimacy`, appliqué chaque tick y compris celui de l'élection, garde `L(t) == m` pour tout le mandat quand `écart == 0` (un vrai point fixe, pas une approximation). Test central : la série de légitimité reste exactement plate à `m` sur un run complet de 30 ans, vérifié `m` indépendant de la méthode électorale (deux-tours, IRV, Borda, Schulze).
- **Lot 4** : porte d'éveil (§7bis.9d — qui est consulté chaque tick), baseline déterministe `deterministic_pressure_action`, agrégation de la mobilisation en `street_pressure` réel (remplace le stub à 0.0 du Lot 3). Vérifié numériquement qu'une mobilisation systématique amplifierait `L` de 33,3× à la config par défaut — la baseline gate donc la mobilisation sur le seuil de tolérance du citoyen plutôt que de mobiliser sans condition, sous peine de faire s'effondrer `L` au premier tick de chaque mandat.
- **Lot 5** : levier de pétition (lancement/signature/expiration) + vote de confiance binaire déterministe — ferme le dernier stub de `écart(t)`, rendant les quatre modalités du menu de pression (électoral seul, pétition seule, mobilisation seule, les deux) toutes atteignables pour la première fois.

**Points bloquants**
- Un point documenté sans être corrigé dans ce lot : sous la modalité "les deux" (pétition + mobilisation), l'amplification de la mobilisation (Lot 4) éclipse la mécanique de pétition — noté comme découverte, pas traité dans ce palier.

**Décisions prises**
- `self_gap` reste une pure primitive à ce stade, sans premier appelant réel avant la porte d'éveil du Lot 4 — *pourquoi* : éviter d'exposer une fonctionnalité à moitié câblée avant que son consommateur naturel n'existe.
- Les limites de mandat ne sont appliquées que sur la voie déterministe de candidature, pas sur la voie LLM déjà livrée (v2 incrément 4) — *pourquoi* : `decide_campaign_positioning` calcule une moyenne électorale sur la liste complète des citoyens ; la pré-filtrer changerait silencieusement le contexte d'un incrément déjà livré et vérifié. Fermé plus tard, aux Lots 6/7, une fois `lame_duck` intégré au contexte de dt=6 de toute façon.

**Prochaines étapes**
- [ ] Lots 6-7 : les deux premières décisions LLM du palier v4 (`representative_response`, `pressure_action`).

**Pour aller plus loin** : PR #131-135.

---

## 2026-08-06 → 2026-08-09 — Polity v2 incréments 2-5 : candidature, nomination de parti, positionnement de campagne, coalition — et un vrai bug d'état président sortant

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #123-127, #130).

**Contexte du jour.** Extension du pattern LLM additif inauguré par le vote (bloc 9) à quatre décisions citoyennes supplémentaires, chacune avec ses propres surprises de fiabilité face au modèle réel.

**Ce qui a avancé**
- **Résolution de la question ouverte du bloc 9** : un balayage live de 20 à 25 citoyens (2 répétitions chacun) sur le vrai chemin de production ne reproduit la corruption observée à aucune taille — `MIN_SAFE_BATCH_SIZE=20` inchangé, l'hypothèse retenue est un incident isolé de non-déterminisme d'ordre de réduction flottante en inférence CPU multi-thread, pas une frontière liée à la taille.
- **Incrément 2 — `candidacy_considered`** : seuil `ambition_score` de la voie dominante devient un jugement LLM (la voie de rupture reste déterministe). Bug de fiabilité trouvé en test live : le cadrage subjectif du prompt ("ce citoyen devrait-il se présenter ?") pousse qwen3:8b à consommer tout son budget en raisonnement `<think>` invisible, quel que soit le budget (jusqu'à 6144 tokens) — `think=False` sur l'endpoint natif `/api/chat` d'Ollama (pas `/v1`) résout le problème et est ~7× plus rapide (~35s vs 4+ min pour un lot de 20).
- **Incrément 3 — `party_nomination_choice`** : arbitrage LLM du départage entre candidats déclarés d'un même parti (unité de décision = un parti, pas un citoyen). L'hypothèse initiale (`think=True`, en cohérence avec le vote) était fausse — le même échec `finish_reason='length'` survient indépendamment de la taille de lot ; cause tracée au cadrage subjectif/comparatif du prompt, pas à la taille ; corrigé en `think=False` avant merge.
- **Incrément 4 — `campaign_positioning`** : premier incrément LLM à changer un intrant réel du vote (pas seulement qui est éligible ou comment un bulletin est formé) — un candidat peut décaler stratégiquement sa position affichée. Deux bugs trouvés et corrigés avant le premier run live : les bornes réelles (`max_positioning_delta`/`shifts`) n'étaient pas énoncées dans le prompt (seul un plafond structurel lâche l'était) ; un tri incohérent entre prompt utilisateur et vérification d'alignement faisait échouer tout appel réaliste.
- **Incrément 5 — `coalition_decision`** : décision LLM join/leave par parti non-initiateur après une élection législative ; désignation de l'initiateur reste déterministe. Premier schéma à utiliser un validateur croisé action↔motif Pydantic.
- **Fix hors incréments — président sortant** : `_hold_presidential_election` ne réinitialisait jamais le rôle/office d'un président sortant non réélu, ce qui pouvait laisser deux citoyens simultanément "en fonction" de président. Sans effet observable en v0-v2 (rien ne lisait encore ce champ), mais bloquant pour tout travail futur en dépendant (limites de mandat, légitimité, réponse représentative) — corrigé, test de régression confirmé en échec sans le fix.

**Points bloquants**
- Aucun restant en fin de période — la suite live complète des 5 incréments tourne en ~77 min avec seulement deux échecs, tous deux déjà documentés comme flakiness connue et sans lien avec le code de cet incrément.

**Décisions prises**
- Garder trois fonctions `decode_*_batch` quasi-identiques plutôt que les généraliser prématurément — *pourquoi* : une tentative antérieure de version générique avait concrètement échoué au typage mypy strict, rien n'a changé depuis.
- `party_nomination_choice` et `coalition_decision` ne passent pas par `chunk_voters`/`MIN_SAFE_BATCH_SIZE` — *pourquoi* : ces gardes protègent des lots de *citoyens* (dizaines à centaines), pas des lots de *partis contestés* (une poignée au plus, souvent zéro) ; les y forcer rendrait la fonctionnalité définitivement inatteignable.

**Prochaines étapes**
- [ ] Palier v4 (légitimité/accountability/pression citoyenne).

**Pour aller plus loin** : `ollama_structured_output_results.md`, PR #123-127, #130.

---

## 2026-07-31 → 2026-08-01 — Polity v2 incrément 1 : le premier vote gouverné par un LLM

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (PR #120-122).

**Contexte du jour.** Premier branchement d'un LLM local (qwen3:8b via Ollama) sur une décision citoyenne réelle — le vote — en gardant candidature/parti/coalition sur `simple_rules.py`, additif et jamais une modification de la baseline déterministe.

**Ce qui a avancé**
- **PR A** : fondations hors-ligne (`LlmConfig`, `codebook.py`, schémas Pydantic `VoteCastDecision`/`VoteCastBatch`) — entièrement testables sans Ollama.
- **Lot 0, spike bloquant** : deux problèmes réels trouvés et corrigés avant tout code client.
  - **Finding A** : la sortie structurée d'Ollama ne gère pas l'imbrication `$defs`/`$ref` de Pydantic — un schéma avec un `BaseModel` imbriqué consomme silencieusement tout le budget de tokens sans jamais produire de contenu visible. Fix : déréférencer (`$ref` inlinés) avant envoi.
  - **Finding B** : une instruction "retourne exactement N décisions" seule est insuffisante — le modèle laisse tomber le dernier élément d'un lot de 25 de façon reproductible, quel que soit le budget de tokens. Fix : énumérer explicitement la liste complète des cids attendus dans le prompt système, plus une auto-vérification.
  - Risque ouvert, non résolu ce jour-là : un petit lot de 3 citoyens échoue systématiquement quel que soit le budget de tokens, cause racine inconnue.
- **PR C** : client Ollama synchrone (jamais async — un appel batché est une seule requête/réponse), vote LLM live-vérifié contre le vrai modèle de bout en bout, pas seulement contre le script de spike.
- **Root-cause du petit lot** : en isolant uniquement le nombre de citoyens (dimensions et candidats fixés à la config connue-bonne), 1/3/8/10/12 citoyens échouent tous identiquement, 15 et 25 fonctionnent — attribution propre au nombre de citoyens seul, mécanisme sous-jacent non déterminé (aurait nécessité de comparer quantisations/backends de serving, jugé disproportionné). Recommandation : `MIN_SAFE_BATCH_SIZE = 20`, chunking proche-égal plutôt que taille fixe avec petit reliquat.
- **Consolidation post-merge** : le test live a révélé des bugs invisibles hors-ligne — budget de tokens trop serré pour le raisonnement `<think>` de Qwen3, timeout client sans marge réelle (les deux relevés) ; collision de cid entre candidats et votants (les candidats sont aussi des citoyens, partagent le même espace de numérotation) — corrigée en indexant `ranking` par position 1-indexée dans la liste de candidats plutôt que par cid brut, traduit en cid réel seulement à la frontière bulletin/journal.

**Points bloquants**
- Un lot de 20 citoyens (exactement `MIN_SAFE_BATCH_SIZE`) a corrompu deux fois les mêmes citoyens en test live (blanc=0 avec ranking vide, auto-contradictoire) — marge de sécurité jugée potentiellement insuffisante, question laissée ouverte pour une investigation ultérieure (résolue le 06/08, cf. bloc suivant).

**Décisions prises**
- Client Ollama toujours synchrone, jamais async — *pourquoi* : le script de mesure du déterminisme est délibérément async pour prouver que des requêtes concurrentes divergent (bloc 8) ; ce pattern ne doit pas fuiter dans le code de production, où un appel batché est un seul aller-retour.
- `LlmResponseError` jamais réessayée, `LlmTransportError` réessayée jusqu'à 3 tentatives sans backoff — *pourquoi* : température=0 + seed fixe rend un nouvel essai après une erreur de réponse un no-op garanti ; l'absence de concurrence rend le backoff inutile.

**Prochaines étapes**
- [ ] Résoudre la question ouverte de la frontière de taille de lot (20 citoyens).
- [ ] Étendre le pattern LLM additif aux décisions suivantes (candidature, nomination de parti, positionnement, coalition).

**Pour aller plus loin** : `ollama_structured_output_results.md`, PR #120-122.

---

## 2026-07-31 — Polity v0 : squelette mécanique pur, puis v1 (candidature de rupture) — et une première preuve empirique que le batching LLM casse le déterminisme

> Entrée reconstruite a posteriori le 2026-08-19, à partir des corps de commit détaillés de `git log` (9 lots v0 + v1 + protocole §5, tous mergés le 31/07/2026 via les PR #117-119).

**Contexte du jour.** Premier jour de code du chantier polity : construire, lot par lot, le squelette mécanique pur défini le 30/07 — 100 citoyens, calendrier électoral, agrégation des scrutins, journal append-only, orchestration — sans aucun appel LLM, pour disposer d'une baseline connue-bonne avant que le risque de non-déterminisme n'existe.

**Ce qui a avancé**
- **Lots 1-3** : chargeur de config typé, entité `Citizen` + génération de population déterministe, initialisation des plateformes de partis par k-means (Lloyd's algorithm déterministe — clusters vides gardent leur centroïde précédent plutôt que d'être réamorcés).
- **Lot 4** : `institutional_clock.py` — un vrai bug de borne trouvé et corrigé : un intervalle de ticks valides *demi-ouvert* (plus « pythonique ») perdait silencieusement la 8ème élection législative avec la config par défaut, parce que 120 partage le même résidu modulo la durée de mandat que le décalage d'assemblée ; corrigé en intervalle *fermé* des deux côtés, vérifié contre les deux exemples travaillés du plan de conception.
- **Lot 5** : `ballot_and_aggregation.py`, adaptateur pur au-dessus du moteur de vote existant (17 méthodes) — un test verrouille la table de dispatch contre l'énumération de `config.py` pour qu'une méthode non supportée échoue au chargement de la config, pas en cours de run.
- **Lot 6** : `simple_rules.py`, la baseline déterministe v0 (règle de vote par distance pondérée aux enjeux, candidature par seuil d'ambition, coalition par plus proche voisin idéologique) — tous les départages explicites (jamais de `max()`/`min()` implicite sur l'ordre d'insertion), pour que le test de reproductibilité byte-à-byte du Lot 8 ne dépende jamais d'un accident d'implémentation.
- **Lot 7** : `journal.py` — écriture flush après chaque événement (un crash ne peut tronquer que la *prochaine* ligne, jamais corrompre une déjà écrite, vérifié par un test qui ajoute une ligne tronquée après 5 écritures propres) ; clés de payload sérialisées avec `sort_keys=True` pour que deux runs produisant un dict équivalent dans un ordre d'insertion différent restent byte-identiques.
- **Lot 8** : `run_polity_simulation.py` — orchestration pure. Le test central : deux runs complets à seed identique produisent des journaux byte-identiques ("le test qui compte le plus"), vérifié maintenant, sur du code purement mécanique, précisément pour disposer d'une baseline connue-bonne avant que le risque LLM (v2) n'existe.
- **Lot 9** : `metrics.py` — les trois seules lignes du §10 calculables sans LLM ni légitimité (nombre effectif de partis de Laakso-Taagepera, taux de cohabitation, durée de vie des coalitions).
- **v1** : candidature de rupture (§2.4, voie rare) — probabilité plate par tick indépendante de la distance idéologique (choix explicite de l'utilisateur), seuil de signatures simulé via un proxy de ratio de sympathisants. Reproductibilité byte-à-byte étendue et vérifiée avec la voie de rupture activée, pas seulement dans la config par défaut.
- **Protocole §5** : vérification empirique, avant même que `llm_behavior_engine.py` n'existe, que des appels LLM séquentiels sont byte-identiques (10 répétitions, redémarrage complet du conteneur inclus) mais que 5/25/50 appels *concurrents* identiques divergent entre eux et de la référence non-batchée — confirmation empirique, quasi certainement liée à la non-associativité en virgule flottante du batching matriciel, que `batch_sharding` doit rester statique et `intra_run_workers` rester à 1.

**Points bloquants**
- Aucun bloquant v0 restant en fin de journée — les 9 lots de `dev-plan-v0-worktree.md` sont clos, 93 tests, mypy strict et flake8 propres. La CI reste rouge un moment sur `develop` après le merge du Lot 9 (mypy 1.16.0 pinné trouve deux erreurs de narrowing invisibles avec un mypy local non pinné 2.1.0) — corrigé le jour même.

**Décisions prises**
- Garder les deux premiers paliers (v0/v1) sur des décisions déterministes explicites plutôt que reporter au LLM — *pourquoi* : elles deviennent le baseline de comparaison contre lequel mesurer ce que le LLM apportera réellement en v2 (sans elles, impossible de dire si le LLM change quoi que ce soit).
- Vérifier le déterminisme du batching LLM *avant* d'écrire le premier module qui en dépend — *pourquoi* : évite de découvrir un problème structurel après coup, une fois le code de production déjà construit dessus.

**Prochaines étapes**
- [ ] v2 : router la première décision citoyenne (le vote) à travers un LLM local.

**Pour aller plus loin** : `dev-plan-v0-worktree.md`, `llm_batching_determinism_results.md`.

---

## 2026-07-30 — Cadrage du chantier Polity : plan de conception, audit de précision, périmètre v0 figé

> Entrée reconstruite a posteriori le 2026-08-19, à partir des documents datés du repo (`polity-simulation-design-v2.md` révision 2c, `audit-precision-plan.md`, tous deux explicitement datés du 30/07/2026 dans leur en-tête) et de `dev-plan-v0-worktree.md`/`DEMARRAGE-polity-v0.md`. Ces documents sont gitignorés (non versionnés) — leur contenu ne peut être cité que verbatim ici, pas diffé.

**Contexte du jour.** Avant d'écrire une ligne de code, rédaction d'un plan de conception complet pour un nouveau chantier : simuler une population de plusieurs milliers de citoyens sur 30 ans (élections présidentielles/parlementaires imbriquées, partis, coalitions, pression citoyenne), où un LLM gouverne l'ensemble des comportements citoyens et seuls le format du bulletin, la méthode d'agrégation et les déclencheurs institutionnels durs restent déterministes.

**Ce qui a avancé**
- `polity-simulation-design-v2.md` (révision 2c) : résolution du bloquant A6 (formule de `écart(t)`), refonte de la pression citoyenne en leviers actionnables (§7bis) plutôt qu'accumulateurs mesurés, schéma de sortie LLM (§3.6) et son codebook de compression (§3.7), reformulation du coût en temps d'horloge (§15bis).
- `audit-precision-plan.md` : passe de relecture systématique identifiant tout ce qui est trop imprécis pour être codé — classé par criticité, avec des bloquants v0 explicites (A1 : granularité du tick tranchée à un trimestre — A2 : origine des partis tranchée à N partis fixes initialisés par k-means — A3 : distinction président/député — A4 : taille/méthode d'attribution des sièges — A5 : règles déterministes v0/v1 spécifiées, futur baseline de comparaison contre le LLM — A6 : formule de `L(t)`).
- Périmètre v0 figé dans `DEMARRAGE-polity-v0.md` : squelette mécanique pur, 100 citoyens, 120 ticks (30 ans × trimestre), décisions déterministes, aucun appel LLM.
- Mise en place d'un worktree Git dédié (`Vote-App-polity`, branché sur `develop`) pour isoler le chantier sans dupliquer le clone.

**Points bloquants**
- Aucun bloquant v0 restant à l'issue de cette journée — c'est précisément l'objet de l'audit de précision : ne rien laisser d'ouvert qui empêcherait d'écrire la première ligne de code.

**Décisions prises**
- Trimestre comme granularité de tick (120 ticks sur 30 ans) plutôt qu'année ou mois — *pourquoi* : compromis entre coût LLM (×3 vs annuel), volume du journal, et finesse de `L(t)`, en gardant la possibilité de raffiner plus tard.
- N partis fixes à `t=0`, plateformes initialisées par k-means sur les positions citoyennes, ni naissance ni mort de parti en v0 — *pourquoi* : la dynamique partisane (naissance/mort) est un trou majeur du document initial, mais ouvrir cette question en v0 aurait bloqué tout le reste ; reportée à un palier ultérieur explicite.
- Remplacer `polity-simulation-design.md` par sa révision v2 plutôt que les faire coexister — *pourquoi* : documenté dans `DEMARRAGE-polity-v0.md` comme le mode de défaillance que le plan lui-même identifie (un concept vivant dans deux documents jamais réconciliés).

**Prochaines étapes**
- [ ] Ouvrir le chantier v0 : squelette mécanique pur, 100 citoyens, sans LLM.

**Pour aller plus loin** : `polity-simulation-design-v2.md`, `audit-precision-plan.md`, `dev-plan-v0-worktree.md`, `DEMARRAGE-polity-v0.md`.

---

## 2026-06-10 → 2026-07-30 — Playground/Laboratoire : consolidation UX, pédagogie, jeu — jusqu'au seuil du chantier polity

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all`. Période dense (près de 400 commits) résumée par motif plutôt que fonctionnalité par fonctionnalité.

**Contexte du jour.** Sur cette période de sept semaines, l'application bascule d'une collection de dizaines de pages/onglets de recherche vers une expérience unifiée : le "Playground" (un instrument de simulation unique, en cinq moments) absorbe progressivement le "Election Lab" et les 40 phénomènes qu'il hébergeait, avant que le tout ne se réorganise encore autour de la pédagogie et de la découverte grand public.

**Ce qui a avancé**
- Playground P0-P5 : canevas d'élection unique, canevas d'assemblée, dynamique temporelle, "banded scorecard", raccords bidirectionnels Lab ↔ Playground.
- Absorption complète du Election Lab (40 phénomènes en 6 familles repliables), puis retrait pur et simple de la page `/election-lab` (redirection).
- Extension des dimensions du modèle d'électorat (3ème axe, bruit de mesure, import/export JSON, vue orbitale 3D).
- Découpage en "moments" narratifs (Électorat → Méthode → Stratégie → Campagne → Bilan), et extraction d'un `/laboratoire` séparé pour l'analyse avancée — séparant délibérément l'instrument pédagogique (Playground) de l'outil d'exploration (Laboratoire).
- Identité visuelle dédiée ("instrument-lab"), i18n complet FR/EN du Playground.
- Harnais de parité moteur client ⇄ backend sur 14 règles de vote — a mis au jour 4 bugs réels côté backend (Bucklin non cumulatif, élimination IRV/Coombs incorrecte, chemin de Schulze erroné, égalité de départage STAR) et 1 défaut côté client, tous corrigés.
- Volet grand public : `/decouvrir` (méthodes de vote pour néophytes), `/campagne` (dynamiques électorales), "À vous de jouer" (bulletin interactif, cinq langages de bulletin), retrait de l'authentification/communauté pour rendre l'application entièrement anonyme et sans état.
- Déploiement public mono-conteneur (Fly.io), analytics anonymes sans cookies (Umami auto-hébergé).
- Rédaction de `THEORY.md` (référence théorique complète, 17 méthodes) et nettoyage de la documentation en amont du pivot suivant (`GUIDE_UTILISATEUR.md`, `README.md`).

**Points bloquants**
- Plusieurs correctifs 422 répétés sur `/simulate` (payload contenant des métadonnées UI, cap de candidats trop bas) — résolus au fil de l'eau, sans qu'un blocage de fond ne persiste.

**Décisions prises**
- Retirer entièrement le Election Lab plutôt que le faire cohabiter avec le Playground une fois l'absorption complète — *pourquoi* : éviter la duplication de state et les "drill-downs circulaires" entre deux surfaces qui montrent la même donnée (mentionné explicitement dans le message du commit de retrait).
- Rendre l'application anonyme (suppression auth/communauté) — *pourquoi* : non détaillé dans les messages de commit au-delà de "backend stateless" ; cohérent avec l'orientation outil de recherche public plutôt que plateforme communautaire.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet ; le chantier suivant, le 30/07, est le cadrage du simulateur polity)

**Pour aller plus loin** : `git log` entre `bf21e83` (2026-06-10) et `6895d21` (2026-07-30) ; `THEORY.md`.

---

## 2026-05-23 → 2026-06-09 — Refonte d'architecture : Flask → FastAPI, Pydantic, TanStack Query/Zustand, Tailwind

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all` (les messages de commit de cette période, structurés en phases numérotées, documentent explicitement l'intention de chaque étape).

**Contexte du jour.** Après trois semaines de sprint fonctionnel pur, une refonte technique en profondeur — menée en phases nommées et séquentielles (Phase 0 à 7) — consolide la base de code avant de continuer à empiler des fonctionnalités.

**Ce qui a avancé**
- **Phase 0-1** : logs structurés (structlog), schémas Pydantic générant des types TypeScript.
- **Phase 2-4** : backend FastAPI monté en parallèle de Flask (`/api/v2/`), puis migration endpoint par endpoint (35 endpoints d'élection, 52 endpoints de théorie, CRUD scénarios, auth via `fastapi-users` + OAuth Google/GitHub, streaming Monte-Carlo Socket.IO) — chaque lot vérifié et fusionné indépendamment.
- **Phase 4.5** : suppression complète de Flask, `api_v2` renommé `api` — le backend est désormais 100% FastAPI.
- **Phase 5** : couche de données frontend réécrite — client `openapi-fetch` typé + TanStack Query, remplacement des Context React par des stores Zustand (auth, UI, lab, élection), suppression d'axios.
- **Phase 6** : `response_model` Pydantic sur tous les endpoints, migration Jest → Vitest, Bootstrap → Tailwind v4 + shadcn/ui (migration fichier par fichier, une soixantaine de PRs).
- **Phase 7** : nettoyage des pages secondaires, ADRs, `security.txt`.
- Durcissement CI continu : mypy strict de bout en bout (26 modules retirés de la liste d'exclusion), flake8 bloquant, ESLint bloquant (0 warning), plusieurs itérations pour stabiliser la couverture de tests sous CI Linux (istanbul ↔ v8, alias `@/`).

**Points bloquants**
- Une série de faux départs sur la configuration de couverture de tests frontend sous CI Linux (alternance istanbul/v8, plusieurs tentatives de résolution de l'alias `@/`) — résolue après plusieurs itérations, documentée dans les messages de commit successifs plutôt que dans un doc dédié.

**Décisions prises**
- Migrer Flask → FastAPI par lots indépendants plutôt qu'en une seule bascule — *pourquoi* : chaque lot de migration (`phase3-batchN`) est fusionné et vérifié séparément, réduisant le risque d'une régression massive difficile à isoler.
- Retirer les Context React au profit de Zustand plutôt que les faire coexister durablement — *pourquoi* : les contextes ont été conservés un temps comme "shims" (facade de compatibilité) avant suppression définitive, seulement une fois tous les consommateurs migrés — logique de bascule progressive et vérifiée déjà observée sur la migration backend.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet, cf. bloc suivant)

**Pour aller plus loin** : `git log` entre `1946395` (Phase 0) et `0dfa354` (2026-06-09).

---

## 2026-05-03 → 2026-05-23 — Sprint « Vote Lab » : des dizaines de méthodes de vote, théorèmes et visualisations

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all`. Le volume de commits sur cette période (plusieurs centaines) rend une reconstruction commit-par-commit disproportionnée ; cette entrée résume le motif plutôt que chaque fonctionnalité individuellement.

**Contexte du jour.** Dans la foulée du pivot du 3 mai, un sprint continu de trois semaines ajoute méthode après méthode, théorème après théorème, à un rythme d'une à plusieurs fonctionnalités par jour.

**Ce qui a avancé**
- Extension du nombre de méthodes de vote comparées de 19 à plus de 30 (Majority Judgment, STV, Copeland, Nanson, Baldwin, Evaluative, SPAV, Phragmén, Quadratic Voting, etc.).
- Une vingtaine de modèles/paradoxes de théorie du choix social implémentés en pages interactives dédiées : théorème d'Arrow, chaos de Plott, paradoxe de Sen, apportionment de Balinski-Young, indices de pouvoir de Shapley-Shubik/Banzhaf, manipulation de Gibbard-Satterthwaite, bulle épistémique (Epistocracy), cascades d'information, biais comportementaux, vote liquide, Conviction Voting, sortition, Duverger, deliberation à la DeGroot, etc.
- Nombreuses visualisations (carte d'idéologie, radar, Voronoi, courses Monte-Carlo, heatmaps, graphes de similarité D3).
- Durcissement sécurité/production en parallèle (CORS, rate limiting, migration CRA → Vite, correctifs CVE Dependabot répétés).
- Fusion des 35 onglets de comparaison en un seul "Election Lab", avant d'être lui-même absorbé plus tard par le "Playground" (cf. bloc suivant).

**Points bloquants**
- Non documentés individuellement à cette échelle — la vélocité du sprint (une fonctionnalité fusionnée toutes les quelques heures) ne laisse pas de trace de blocage au niveau des messages de commit.

**Décisions prises**
- Empiler les fonctionnalités de recherche en pages dédiées plutôt que dans un cœur de moteur unique dès le départ — *pourquoi* : non documenté explicitement, mais cohérent avec l'exploration rapide d'un large espace de sujets avant consolidation (cf. blocs 5-6, qui refondent ensuite l'architecture ET l'UX).

**Prochaines étapes**
- (reconstruction rétroactive — sans objet, cf. blocs suivants)

**Pour aller plus loin** : `git log` entre `e7b3f91` (2026-05-04) et `f484ec9` (2026-05-17), et entre `8c2bc52`…`50db12e` (théorie/recherche, 18-19 mai).

---

## 2026-05-03 — Pivot : abandon du système d'élection, naissance de la plateforme de recherche en simulation

> Entrée reconstruite a posteriori le 2026-08-19, à partir de `git log --all` (messages de commit détaillés de cette journée).

**Contexte du jour.** Un seul jour de travail, mais une bascule complète d'orientation : le projet cesse d'être une application de vote électronique pour devenir un outil de recherche/pédagogie sur les méthodes de vote elles-mêmes.

**Ce qui a avancé**
- Remplacement du modèle d'utilité par un modèle de vote spatial explicite (positions idéologiques `[0,1]` par enjeu, distributions centriste/polarisée/gauche/droite), 5 stratégies de vote stratégique (Duverger, enterrement Borda, compromis IRV, vote utile en approbation, exagération en score), moteur de comparaison (regret bayésien, satisfaction majoritaire, vulnérabilité stratégique, cohérence de Condorcet).
- **Suppression complète du système d'élection** : tables `Election`/`Vote`/`Result`, routes, services, pages associées — remplacées par un sandbox de simulation. Conservation de `User`/`Party`/`SimulationScenario`.
- 67 tests unitaires écrits pour les 19 méthodes de vote — l'écriture des tests a révélé deux bugs réels (Minimax et Schulze ne comptaient l'opposition par paire que dans un seul sens, rendant le vainqueur dépendant de l'ordre d'itération Python plutôt que déterministe) — corrigés le jour même.
- Vérificateur empirique des critères d'Arrow, interface de comparaison en sandbox côté frontend.

**Points bloquants**
- Non documentés au-delà des deux bugs Minimax/Schulze, résolus le jour même.

**Décisions prises**
- Retirer entièrement le système d'élection plutôt que le faire coexister avec le sandbox — *pourquoi* : le message de commit documente une restructuration complète du code autour du sandbox de simulation, pas une addition en parallèle.

**Prochaines étapes**
- (reconstruction rétroactive — sans objet, cf. bloc suivant)

**Pour aller plus loin** : commits `a093a15`, `7b0bebd`, `3524b9a`, `4777ec0` (`CLAUDE.md` réécrit pour le nouveau focus).

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
