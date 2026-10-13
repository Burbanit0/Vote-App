# Journal de bord — Vote-App / La Fourmilière

> **Rouvert le 2026-10-12.** Retiré le 2026-10-08 (`docs/plan/PLAN_BEYOND_CI.md`,
> décision D7), puis rouvert par le propriétaire le 2026-10-12. Les journées
> restées sans entrée sont reconstruites a posteriori depuis le git log et les
> descriptions de PR, et chaque entrée reconstruite le dit en tête. L'état
> courant et les prochaines étapes restent dans [`docs/STATUS.md`](../STATUS.md).

> Une entrée par session de travail significative, la plus récente en
> haut. Objectif : raconter l'histoire du projet au jour le jour — ce qui
> avance, ce qui bloque, les décisions prises — pour soi-même en
> relecture, et pour pouvoir reprendre le contexte facilement dans une
> autre conversation. Rédigé via le sub-agent `journal-writer` (commande
> `/log-session`), toujours en proposition avant application.
>
> **Historique archivé** (Lot 12.2, `PLAN_SOLIDITE_TECHNIQUE.md`) : ce
> fichier ne garde que les entrées récentes, pour rester petit
> d'une session à l'autre. L'historique reconstruit rétroactivement (genèse
> du projet en mars 2025 jusqu'à la mise en place de ce journal le
> 2026-08-19) vit dans [`docs/journal/archive/`](./archive/) :
> [`JOURNAL_2026.md`](./archive/JOURNAL_2026.md) (2026-05-03 → 2026-09-14)
> et [`JOURNAL_2025.md`](./archive/JOURNAL_2025.md) (2025-03-01 →
> 2026-01-13). Depuis les rotations du 2026-09-27 et du 2026-10-12,
> `JOURNAL_2026.md` garde aussi les entrées du 2026-08-17 au 2026-09-14,
> écrites en temps réel ou reconstruites le 2026-10-12 (marquées en tête).
> Ce fichier commence donc au 2026-09-16.
>
> **Règle de rotation** : quand ce fichier dépasse à nouveau ~100 Ko,
> déplacer ses entrées les plus anciennes vers `archive/JOURNAL_<année>.md`
> (créer le fichier de l'année si besoin) et mettre à jour les liens
> ci-dessus.

---

## 2026-10-10 → 2026-10-12 — Hébergement statique W6 (le moteur tourne dans la page), brouillon de preprint, graine des tirages d'égalité, et Mutation Testing au rouge

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Une fois W3.6 clos, `STATUS.md` met en tête W6 (« Hosting, revisited ») et le preprint D5 de `PLAN_BEYOND_CI.md` (#907). Le spike W6 rend son mémo le 10-10 au soir. Le 10-11, le propriétaire choisit l'option A (« I don't mind of the phone right now, go for A », #914), puis les cinq étapes passent en un peu plus de 24 h.

**Ce qui a avancé**
- **Mémo W6, EXP-023** (#908) : le moteur hors Polity tourne dans Pyodide, dans un Web Worker (fiches Polis, STV et Polarisation), avec les mêmes résultats que CPython, comparés valeur par valeur. Coût pour un visiteur : 11,9 Mo à la première visite, environ 2 s de démarrage, un calcul 1,3 à 2× plus lent qu'en natif. En face, le conteneur Fly sature vers 1 requête/s, et 8 utilisateurs attendent 25 à 30 s. Recommandation : hébergement statique avec Pyodide. La branche du spike n'est pas destinée à être fusionnée.
- **Les deux bugs trouvés par le spike sont corrigés.** La fiche STV renvoyait 400 sur l'électorat par défaut : elle demandait 3 sièges pour 3 candidats (#910). Le signe des axes PCA dépendait du build LAPACK, et l'axe 2 de Polis sortait inversé sous Pyodide : un `orient_axes` partagé corrige Polis, la carte des profils et la projection Polity, et les étiquettes Polis reviennent sur leurs clusters (#911).
- **Option A, étapes 1 à 5** :
  - #914 : le backend répond sans serveur (`api/browser.py`, `handle()` en ASGI). Le rate limiter passe dans `main.py`, avec la règle Semgrep. Le bundle fait 650 Ko, et deux builds sont identiques à l'octet.
  - #916 : `npm run build:static`. Chaque appel `/api/v2` part vers un worker Pyodide 314.0.7, avec les codes 503/500 du serveur. La fiche Monte Carlo passe en HTTP. Le bundle reste à 722,74 kB brotli.
  - #917 : un contrôle CI compare 60 requêtes sous Pyodide et sous CPython, puis fait tourner le site statique sans aucun serveur. Aucun workflow n'est modifié.
  - #921 : l'explorateur Polity lit un export des trois runs complets de 30 ans (2,1 Mo, 19 fichiers, reproductible à l'octet). Il remplace #919, fermée : gitleaks avait pris une constante de test pour un secret dans un commit qu'un agent ne peut pas réécrire (pas de force-push).
  - #924 : GitHub Pages sous `/Vote-App/`, avec le tableau de bord CI déplacé sous `/ci/`, un `404.html` pour les liens profonds, et un service worker qui laisse `ci/` tranquille.
  - #925 : mise à jour de `STATUS.md`.
- **Preprint D5 en brouillon** (#913) : *Confidently Constant*, 12 pages LaTeX tirées de l'article W2.6 (#879), avec 17 références vérifiées sur leur éditeur ou sur arXiv. Le dossier de preuves resserre l'article sur deux points : le modèle servi est la version AWQ 4 bits, et deux des trois balayages faisaient varier plusieurs entrées à la fois. Rien n'est soumis.
- **Égalités, suite de W5** : #927 transmet la graine de la requête aux tirages d'égalité des règles à score sur les endpoints qui en ont une (environ 25 sites d'appel). `/profile-simulate` reste à 0, volontairement. Le reste de la décision du 10-09 est regroupé dans l'issue #926.
- **Sync `polity → develop`** (#928, commit de merge réel) : 65 PR (#845–#927) sans conflit. Elle ferme #662 à #667.

**Points bloquants**
- **Mutation Testing au rouge.** Le job Stryker échoue dès le run initial : `ENOENT … voter-app/.stryker-tmp/docs/research/bibliography.bib`. En cause, le test `cite: … bibliography.bib gives every source the registry uses`, arrivé avec 73974e21 (#899) : il lit un fichier hors du bac à sable de Stryker. Dernier run vert sur `polity` le 10-10 à 12:05 UTC (7b02c781, avant #899). Runs rouges : le planifié du 10-12 à 12:00 (38246263308, qui teste `polity`), puis les pushes ce0e674 et 5b7968b1 (38320303209, 38323567330). Toujours pas corrigé le 10-12, et absent de `STATUS.md`.
- **W6 n'est pas en ligne.** Il faut deux modifications de workflow que le jeton de push ne peut pas pousser (pas de scope `workflow`) : un job `static-site` dans `release.yml` et l'étape « Assemble the site » de `ci-dashboard.yml`. Il faut ensuite une release (#924, #925). Le filtre de chemins e2e de #917 attend lui aussi le propriétaire.
- **Égalités** : le client, et avec lui `/profile-simulate`, tire encore avec la graine 0. Un tirage à deux suit la parité de la graine (faiblesse de FNV-1a), renvoyée à #926 parce que la corriger régénère la fixture de parité (#927).
- Le preprint attend sa ligne d'auteur et sa déclaration (#913, #925).

**Décisions prises**
- **Option A, site statique avec Pyodide** (2026-10-11) — *pourquoi* : c'est la recommandation du mémo pour une classe qui manipule elle-même (EXP-023). Le propriétaire met le téléphone de côté pour l'instant.
- **GitHub Pages, publié à chaque release, tableau de bord sous `/ci/`** (#924) — *pourquoi* : un dépôt n'a qu'un site Pages, déjà occupé par le tableau de bord CI, et chaque déploiement le remplace en entier. Pages et la cadence « à chaque release » sont les options marquées « Recommended » que le propriétaire a retenues. Pas d'autre raison consignée.
- **Exporter les trois runs complets** (graines 1, 2 et 42) pour l'explorateur statique (#921) — choix du propriétaire, raison non consignée.
- **`/profile-simulate` garde la graine 0** (#927) — *pourquoi* : il alimente le playground, dont le moteur client tire encore avec 0. Faire passer `config.seed` dans ses ~20 points d'entrée est un chantier à part.

**Prochaines étapes** (selon `STATUS.md` au 2026-10-12)
- [ ] Playwright 1.64 le 2026-10-14, une fois passé le délai de 7 jours de npm : lockfile, pin d'image et baselines visuelles dans une seule PR.
- [ ] Première release avec le site statique, une fois les modifications de workflow faites. À vérifier : `/Vote-App/`, un lien profond comme `/polity?citizen=3`, et `/ci/`.
- [ ] Clore le plan : le gel CI se lève à la fin de la Phase 4. W3.5 attend un enseignant, le preprint sa ligne d'auteur.
- [ ] (Absent de `STATUS.md`) Réparer Mutation Testing : le test de `cite()` ne doit plus lire `bibliography.bib` hors du bac à sable de Stryker.

**Pour aller plus loin** : `docs/exploration/EXP-023-pyodide-web-worker-vs-fly-container.md`, `docs/plan/PLAN_BEYOND_CI.md` (W6), `docs/preprint/`, `docs/plan/vote-app/LISTING_ORDER_TIES.md`, issue #926.

---

## 2026-10-10 → 2026-10-12 — Polity : sortie de Phase 4 redéfinie (D11), abstention et vote stratégique aux législatives, rappel majoritaire, présidents qui calculent (ADR-024 à ADR-028)

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** L'expérience du seuil s'est arrêtée à sa porte (OBS-045, entrée du 10-09). Le travail Polity repart donc des constats de phase11 : la fragmentation (OBS-040), les mandats éclair (OBS-041) et les rappels. La consigne du propriétaire : « let's continue we will adjust in a second time, continue building » (#904, #905). Tout ce qui suit est du code noyau, des sondes sur des états finaux et des ADR. Aucun nouvel ensemble n'est consigné dans un document de la fenêtre.

**Ce qui a avancé**
- **Le noyau consigne la réponse d'un président à l'acte extra-légal** (#884). Ce changement attendait que W2.1 ne lance plus de runs appariés, parce qu'`events.py` entre dans l'empreinte du prompt. L'empreinte change pour les runs suivants.
- **Règle du demi-mandat** (#891, OBS-041) : un mandat ne compte pour la limite que s'il a été gagné avec au moins la moitié de sa durée devant lui. Le nouveau champ `Citizen.short_terms` laisse `mandates_served` intact : `/code-review high` avait relevé l'effet sur `keep_record`.
- **D11, la sortie de Phase 4 redéfinie** (#892). Le nombre de partis doit changer dans au moins 30 % des graines, et dans au moins 30 % une amendement sur l'entrée des partis ou les sièges doit être ratifié. Le nombre effectif de partis est rapporté, plus bloquant. Critère atteint en phase11 (4 graines sur 10). OBS-040 passe à « decided ».
- **Le balayage de graines ne fait plus de moyenne d'une constitution à l'autre** (#896) : les 10 graines de phase11 ont tourné sous 8 histoires constitutionnelles. Un vrai balayage a montré qu'une note de #896 se trompait : seul le troisième signal S0.7 mélange ces histoires. #901 corrige la note.
- **OBS-045, la suite** (#902) : la porte relancée en consignant chaque réponse. Les 14 fondateurs qu'une barre à 7 % aurait dû arrêter ont tous fondé, quelle que soit la formulation, et aucune des 240 réponses ne cite la barre des sièges. OBS-045 reste ouverte.
- **OBS-046** (#904) : les citoyens qui ont décroché votaient encore aux législatives et aux votes de confiance, contre ADR-021. En phase11, 8 à 28 sur 100 avaient décroché à chaque législative (moyenne 17,2), et les 20 élections comptaient pourtant 100 bulletins. Un helper `_voters` s'applique désormais à tous les bureaux de vote.
- **ADR-024, vote utile aux législatives** (#905, Cox 1997). Le paramètre `vote.strategic_margin` vaut 0 par défaut et 0,07 dans le profil d'exploration. Appliqué à froid aux populations finales de phase11, le nombre effectif de partis par voix passe de 18,86 à 11,02, et par sièges de 7,58 à 7,33 : les partis abandonnés n'avaient déjà pas de sièges.
- **OBS-047** (#912) : 41 des 70 présidences de phase11 finissent par un rappel au plancher de légitimité, avec une approbation toujours majoritaire (0,54 à 0,80, médiane 0,71). Seules 3 vont au bout. Deux causes : le modèle se mobilise sur 33,3 % des actes de pression (1,5 % sans émotions, OBS-019), et `update_legitimacy` amplifie la pression d'un facteur dix. Le rejeu des 41 présidences sous six règles ne tranche pas.
- **ADR-025, le rappel majoritaire** (#915) : la pression pèse comme le soutien, et le plancher déclenche un vote de confiance où seule une majorité peut révoquer. Les deux interrupteurs sont coupés par défaut et activés en exploration. Sur le jumeau déterministe (10 graines × 8 ans) : 49 rappels sans eux, 0 avec les deux.
- **ADR-026, les enjeux d'un amendement** (#918). D'après le contexte de l'ADR, dans phase12 trois graines sur cinq ont ratifié un troisième mandat, chaque fois proposé par le président en place. Le briefing montre désormais au président ce que donnerait chaque méthode de vote et chaque répartition des sièges, et le champ d'amendement devient obligatoire mais annulable. Sonde 2 × 2 : 33 propositions sur 7 articles avec le champ obligatoire sans les enjeux, contre 27 sur 5 avec ; 16 des 27 sont des changements de seuil.
- **ADR-027 et ADR-028** (#923). D'après ADR-027, phase13 a produit 31 amendements et pas une seule méthode de vote. Les enjeux portent désormais sur la prochaine élection (`ballots_today`), et l'objectif du président dépend de son ambition. Sonde sur 39 présidents : les tours à forte ambition avec proposition passent de 7/15 à 12/15, et les propositions de méthode qui élisent leur auteur de 7/10 à 12/13.

**Points bloquants**
- **Aucune des ADR-024 à 028 n'a été mesurée sur un run LLM entier.** Chaque PR renvoie la mesure « au prochain ensemble » (#905, #915, #918, #923). Les sondes portent sur des états finaux, avec peu de présidents.
- **OBS-045** : on ne sait toujours pas pourquoi la règle des sièges n'apparaît jamais dans les réponses (#902).
- **OBS-047 et OBS-015 se contredisent sur le levier de décroissance de la légitimité.** Sur le jumeau, OBS-015 trouvait encore 71 à 74 % de présidents rappelés avec une décroissance de 0,5 ; le rejeu d'OBS-047 n'en laisse que 4 sur 41 sous le plancher. Raison non testée (#912).
- Les nombres effectifs de partis d'OBS-040 et d'OBS-044 ne sont pas recalculés après OBS-046 : le journal dit combien ont décroché, pas qui (#904).
- Un run repris depuis un ancien checkpoint garde l'ancien décompte des mandats (#891).

**Décisions prises**
- **D11** (2026-10-10) — *pourquoi* : aucun des leviers essayés n'a fait bouger la fragmentation (OBS-043, OBS-044, OBS-045). Dans la littérature, la fourchette 1,5–8 doit beaucoup au vote stratégique, que le modèle n'avait pas (feuille de route, D11).
- **« Au moins la moitié » du mandat** (#891) — *pourquoi* : c'est la règle approuvée par le propriétaire. Un commit intermédiaire qui appliquait la règle américaine stricte a été annulé, parce que le spec-checker l'a jugé contraire à l'approbation.
- **ADR-025, les deux interrupteurs ensemble** — *pourquoi*, selon le propriétaire : « a president should be recall[ed] when the population is against him not a few of them ».
- **ADR-026, champ obligatoire et enjeux**, choisi après la sonde 2 × 2 — *pourquoi* : le propriétaire veut garder les prolongations de mandat intéressées et voir les présidents essayer d'autres règles (méthode de vote, institutions).
- **ADR-027 et ADR-028** — *pourquoi*, selon le propriétaire : un président peut faire passer son intérêt avant celui du pays et anticiper la tendance de l'opinion.
- **Marge stratégique de 0,07** (#905) — *pourquoi* : c'est le coût médian de la défection pour les électeurs bloqués à la fin de phase11. La PR la présente comme une première estimation.

**Prochaines étapes**
- [ ] `STATUS.md` (2026-10-12) ne range aucune étape Polity dans ses trois prochaines étapes. Il garde OBS-045 en question ouverte et l'upload Zenodo dans « Waiting on the owner ».
- [ ] D'après les PR, et non d'après `STATUS.md` : un ensemble LLM pour mesurer ADR-024 à 028 sur des runs entiers (#905, #915, #918, #923).

**Pour aller plus loin** : `docs/plan/polity/observations.md` OBS-044 à OBS-047, `docs/adr/ADR-024` à `ADR-028`, la feuille de route Polity (D11, ligne 4.5).

---

## 2026-10-09 → 2026-10-10 — Vote Lab : registre des critères, « pourquoi » dans le Bilan, accessibilité, et fin des égalités par ordre de listing (W1, W3, W5)

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** On exécute `PLAN_BEYOND_CI.md` (fusionné dans #858 le 2026-10-08) sur la demande « execute the plan ». Trois chantiers côté Vote Lab : W1 (ce que l'app enseigne doit être vrai et sourcé), W3 (le playground) et W5 (les issues #662 à #667 sur les égalités par ordre de listing).

**Ce qui a avancé**
- **W1, le contenu** :
  - #859 : l'histoire « paradoxe » est un cycle de Condorcet (Alice > Bob 402–198, Bob > Carol 401–199, Carol > Alice 386–214), alors que le texte en faisait la gagnante de Condorcet. Neuf cellules de critères sont corrigées par recherche de contre-exemples sur 60 000 profils. THEORY.md est corrigé : 1/18 pour 3 électeurs, McKelvey 1976, Londres n'a jamais utilisé IRV.
  - #868 : chaque nom et chaque chiffre des histoires est vérifié contre le moteur. Deux erreurs de texte trouvées : Clones 54 % → 56 %, Structures 41 % → 44 % des sièges.
  - #869 (fusionnée le 10-10) : un seul registre, `method_criteria.json`. 80 cellules sont testées par les deux moteurs, 4 sont des « variantes » (D8) et 148 viennent de la littérature, dont 110 sans source, sous un plafond qui ne peut que baisser. Le `condorcet` du backend devient Copeland.
  - #875 et #899 : un formulaire « report a content error » sur les histoires, les fiches et chaque cellule de la matrice, un oracle e2e des gagnants, et une infobulle par cellule qui donne la base et la source du verdict.
  - #900 : un dossier de relecture pour un chercheur, généré par `gen_review_packet.py`.
- **W3, le playground** :
  - #860 : une seule palette (Carol était verte sur la carte et rouge à côté). La visite guidée et `react-joyride` sont retirés. Le JS chargé au premier affichage de l'accueil passe de 345 à 194 KB gzip.
  - #874 : un bandeau du gagnant sur chaque moment et 5 méthodes cochées par défaut. La loterie n'a plus de « gagnant fixe ».
  - #885 : le Bilan explique pourquoi chaque gagnant gagne et pourquoi deux méthodes divergent. Beaucoup des phrases affichées jusque-là étaient fausses pour leur méthode.
  - #883 : sur téléphone, la narration reste collée sous la barre de navigation. Le test flaky que cela a créé (0,974 contre 0,99) est corrigé à la source dans #888 : la valeur de paradoxe passait d'une ligne à deux, de 15 à 31 px.
  - #903 et #906 : des annonces `aria-live`, une description des cartes, des cibles tactiles d'au moins 44 px, et une mesure du jank au glisser : aucune tâche longue pendant un glisser, alors que le plan estimait environ 800 ms par seconde.
- **W5, les égalités**, selon la politique tranchée le 10-09 :
  - #880 (#666) : un électorat à égalités exactes. 25 méthodes sur 34 résistent à l'inversion des candidats ; 9 sont marquées xfail strict.
  - #887 (#667) : un tirage FNV-1a jumeau des deux côtés (`tie_lot.py` et `tieLot.ts`). Le bloc de parité exhaustif de maximin vérifie désormais le gagnant exact sur 6 060 profils.
  - #890 (#662) : l'égalité propre à un électeur se tire avec son id comme graine.
  - #894 (#663, #665) : l'option la plus proche et le favori sont tirés par électeur, avec une finalisation fmix32 (51,7 / 48,3 sur 4 000 électeurs).
  - #895 (#664) : le bruit de campagne suit le candidat, plus sa position dans la liste.
- **CI** :
  - #886 : les shards e2e tournent dans l'image Playwright épinglée. Un `apt-get update` bloqué avait touché 4 runs E2E sur 8 le 10-07.
  - #897 : retire, côté test, le déclencheur du crash WebKit sur `page.goto` (2 runs sur 262).
  - Dependabot : #871, #873 ; #845 (deprecated 1.3.1 → 3.0.0) fusionnée le 10/10, alors que #855 avait déjà livré cette montée de version le 08/10.
  - `STATUS.md` : #898, #907.

**Points bloquants**
- Le filtre de chemins CI de #869 n'est pas poussé (pas de scope `workflow`) : une modification du registre ou de la bibliographie seule ne lance pas le contrôle backend.
- 110 cellules de la littérature restent sans source. Le dossier de relecture ne peut partir qu'après la prochaine sync de release, parce que GitHub lit les formulaires d'issue sur la branche par défaut (#900).
- Le tirage de #887 utilisait toujours la graine 0. Les deux revues l'ont jugé proche de la dépendance au nom refusée par le propriétaire. #927 le corrige en partie (entrée du 10-12).
- Le correctif amont du crash WebKit (Playwright 1.64) est bloqué par le délai de 7 jours de npm jusqu'au 10-14 (#897, #898).
- Rien n'a été vérifié avec un vrai lecteur d'écran ni sur un vrai téléphone (#903, #906). La palette des fiches Monte Carlo et campagne attend un choix de design (#860, C1b).

**Décisions prises**
- **Les égalités se tirent par un tirage au sort avec graine, sur les deux moteurs** (2026-10-09, consigné dans `LISTING_ORDER_TIES.md` via #880) — *pourquoi* : le propriétaire avait rejeté un départage par nom (#887).
- **MJ × majorité classé « conditional »** (#859) — *pourquoi* : même raisonnement que pour l'approbation. La PR le présente comme un jugement que le propriétaire peut renverser.
- **110 sources à `null` sous plafond, plutôt que des citations non vérifiées** (#869) — *pourquoi* : une source vide vaut mieux qu'une citation que personne n'a vérifiée, et un plafond l'oblige à baisser.
- **Conteneur Playwright plutôt qu'un `apt` borné** (#886) — *pourquoi* : `/code-review max` a montré qu'un `timeout` laisse l'apt lancé via `sudo` orphelin, et que cet orphelin garde le verrou.
- **Pas de mise en page « carte d'abord » sur téléphone** (#883) — *pourquoi* : l'ordre du DOM et du focus ne correspondait plus à l'écran (WCAG 2.4.3).

**Prochaines étapes** (selon `STATUS.md` au 2026-10-10, #907)
- [ ] Playwright 1.64 le 2026-10-14.
- [ ] Le spike d'hébergement W6 et son mémo.
- [ ] Le preprint (D5), à partir de l'article W2.6. W3.5 attend la prise de contact avec un enseignant.

**Pour aller plus loin** : `docs/plan/PLAN_BEYOND_CI.md` (W1, W3, W5), `docs/plan/vote-app/LISTING_ORDER_TIES.md`, `docs/research/expert-review-packet.md`, `voter-app/src/data/method_criteria.json`.

---

## 2026-10-09 — PLAN_BEYOND_CI démarre côté Polity : l'expérience du seuil s'arrête à sa porte (OBS-045), phase11 analysée (OBS-044), et le journal est retiré

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** `PLAN_BEYOND_CI.md` (fusionné dans #858 le 10-08) ouvre sur une expérience Polity, W2.1 / D1 : le seuil électoral change-t-il la fréquence de fondation des partis ? Le plan prévoit d'abord une sonde de « porte » peu coûteuse, qui arrête tout si la fondation ne réagit pas. Le même plan retire le journal (D7) et fait passer le processus en anglais (D3).

**Ce qui a avancé**
- **D2** (#861) : les fondateurs connaissent maintenant le seuil des sièges, lu dans la constitution en vigueur. Avant, aucun agent ne le voyait. La PR ajoute aussi l'outil de la porte (`--probe threshold`, test de McNemar exact apparié) et amende ADR-018.
- **Instrumentation W2.2** :
  - #862 : un contraste apparié à deux bras (permutation par inversion de signe, intervalle BCa).
  - #863 : le nombre effectif de partis (sièges et voix) dans `digest.json`.
  - #864 : `reseat` refait la répartition des votes enregistrés à un autre seuil, sur CPU. Au seuil en vigueur, il retrouve les sièges enregistrés.
  - #865 : `--threshold` et `--freeze-amendments`, avec un dossier de sortie par bras.
- **W2.3** (#866) : un tableau « fit for inference » donne un verdict par type de décision LLM. `vote_cast` est validé « à la barre » (36/40 = 90,0 %). #879 corrige plus tard la ligne `pressure_action` : de « Collapsed » à « Unverified », parce que la preuve datait d'avant le prompt du 2026-09-10.
- **La porte a dit STOP** (#877, OBS-045). Run du 10-09 après redémarrage : vLLM 0.31.0, `qwen3:8b`, température 0,6. 59/60 fondations à 3 % comme à 7 %, McNemar p = 1. Au moins 13 des 14 fondateurs trop peu soutenus pour un seuil de 7 % fondent quand même. W2.4 est abandonné, et le temps des phases 2–3 de Polity passe à W2.6.
- **OBS-044** (#876) : phase10 et phase11 comparées. L'abstention médiane passe de 66 à 15 sur 100, la fragmentation ne bouge pas (médiane 8,42 → 8,47), et les amendements ratifiés passent de 6 à 11, dont 6 sur le seuil. L'acte extra-légal est accessible mais jamais choisi (0 tour présidentiel sur 350).
- **W2.6** (#879) : un article de `docs/stories/` sur l'instrument logprob, plus étroit que la ligne du plan : trois types de décision sont plats, pas tous.
- **W2.5, archive** (#878, #882) : un `CITATION.cff`, signé du seul alias Burbanit0. Les trois runs de 30 ans ont été vérifiés : aucun token ni aucune clé dedans.
- **W4, processus** :
  - #867 : le gabarit de PR, `/verify` et CLAUDE.md passent en anglais dans une seule PR, et `/log-session` et `journal-writer` sont supprimés.
  - #870 : chacun des 40 plans porte une ligne de statut, et `docs/README.md` gagne un index des plans.

**Points bloquants**
- Il a fallu un redémarrage de la machine avant de lancer la porte (#861 C6, #870). Elle a tourné le 10-09 (#877).
- Le décompte exact parmi les 14 fondateurs (13 ou 14) n'était pas connu. #902 le donne le 10-10 : 14 sur 14.
- Les données de phase11 vivent hors du dépôt (`~/Documents/Dev/polity-runs/`), et OBS-044 n'attribue de cause qu'au changement de participation (#876).
- L'épinglage de vLLM par digest est reporté : changer l'image recréerait le conteneur `vllm-polity` dont d'autres sessions se servent (#878).

**Décisions prises**
- **STOP, sans pilote, sans run principal, sans pré-enregistrement** (#877) — *pourquoi* : c'est la règle du plan, « If founding does not respond, stop. That is the finding, and it is cheap. »
- **Dire le seuil aux fondateurs (D2)** — *pourquoi* : sans lui, l'expérience ne pouvait trouver que « pas d'effet » (#861).
- **Un dossier par bras plutôt qu'un drapeau `--arm`** (#865) — *pourquoi* : les identifiants de run ne portent pas le bras, donc deux bras dans un même dossier se marcheraient dessus.
- **OBS-044 en documentation seulement** (#876) — *pourquoi* : le propriétaire ne voulait pas couper le GPU, qu'un plan utilisait dans un autre worktree.
- **Garder la phrase du seuil dans le prompt du forum** : la question est laissée au propriétaire (#877).
- **Les plans finis restent en place, au lieu d'aller dans `archive/`** (#870) — *pourquoi* : environ 300 références y pointent. La PR demande au propriétaire de confirmer.
- **Journal retiré (D7) et outillage supprimé** (#858, #867) — *pourquoi*, d'après le bandeau du journal : l'état courant vit dans `STATUS.md` et l'histoire de chaque changement dans sa PR.

**Prochaines étapes** (selon `STATUS.md` au 2026-10-09, 984434c8)
- [ ] W5 : les correctifs d'égalités #667 et #662, maintenant que #666 leur fournit un test.
- [ ] W3.3 : le « pourquoi » dans le Bilan, après la fusion de #874.
- [ ] W1.4, seconde moitié, après #869 : les infobulles par cellule et le dossier de relecture.

**Pour aller plus loin** : `docs/plan/PLAN_BEYOND_CI.md` (W2, W4), `fast_api_voter/scripts/check_agent_prompt_neutrality_d2_results.md`, `docs/plan/polity/fit-for-inference.md`, `docs/plan/polity/observations.md` OBS-044/OBS-045, `docs/stories/the-answer-that-did-not-depend-on-the-question.md`.

---

## 2026-10-08 — Le plan « au-delà de la CI », une page STATUS d'une page, et le journal mis à la retraite (D7)

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Après dix jours où la CI et l'outillage avaient pris l'essentiel du travail (le plan mesure 61 % des lignes modifiées en octobre côté CI/process, 23 % Polity, 5 % frontend), une session d'audit du 2026-10-08 répond à la question « à part la CI, qu'est-ce que je devrais améliorer ? ». Constat du plan : le projet vérifie très bien le code contre le code, mais rien ne vérifie ce qu'il *affirme*, et aucune des trois parties (Vote Lab, Polity, le process) n'a de ligne d'arrivée ni de lecteur extérieur.

**Ce qui a avancé**
- **`docs/plan/PLAN_BEYOND_CI.md`** commité (#858) : chantiers W0–W6 (W1 affirmations de Vote Lab, W2 l'expérience Polity jamais lancée — deux constitutions comparées sur plusieurs graines, W3 playground, W4 docs, W5 bugs d'égalités du moteur, W6 hébergement), dix décisions D1–D10 prises avec le propriétaire, objectif à ~12 semaines.
- **Règles pendant le plan** : Vote Lab et Polity alternent (runs GPU en fond pendant les PR Vote Lab) ; **travail CI/process gelé en maintenance** (correctifs de build rouge, sécurité, Dependabot, et les checks qu'une étape du plan exige ; plus de nouveaux workflows, gates, agents ou hooks) ; pas d'instance hébergée tant que W6 n'a pas rouvert la question.
- **`docs/STATUS.md`** créé (#858) : une page avec l'état des trois parties, les 3 prochaines étapes, ce qui attend le propriétaire et les questions ouvertes. Il y note que l'ensemble phase11 (10 graines × 8 ans) a fini le 2026-10-07 — fait tiré des répertoires de run sur la machine du propriétaire, rien dans le dépôt ne le montre (dit dans le « Non vérifié » de #858).
- `docs/README.md` réécrit en anglais (D3) et corrections de dérive : README (PR vers `polity`, 22 essais d'outils et non 14), `traceability.md`, statut de `PLAN_SURFACE_EXTERIEURE` §2.B, deux plans qui se disaient à tort gitignorés, quatre fichiers d'instantané mémoire marqués périmés (#858).
- Le même jour : #851 trouve pourquoi le groupe Dependabot #846 échouait (FastAPI 0.142 ouvre un span OpenTelemetry par requête, et le générateur d'ids du SDK tire dans le `random` global, ce que `test_no_global_rng.py` interdit) → générateur d'ids privé sur `SystemRandom` ; #855 fusionne ensuite #846 et `deprecated` 3.0.0 ; #850 fait ignorer `multidict >= 7` à Dependabot ; #854 groupe npm ; sync `develop` #853.

**Points bloquants**
- La suppression de `/log-session` et de l'agent `journal-writer` est un changement `.claude/`, reportée à une PR suivante (#858 ; faite par #867 le 2026-10-08 au soir).
- L'agent `doc-drift` n'a pas été lancé sur la branche (« Non vérifié » de #858).

**Décisions prises** (tableau « Decisions (taken 2026-10-08) » du plan)
- **D7 — le journal (`docs/journal/`) est retiré**, avec une note de clôture : sa dernière entrée datait du 2026-09-27 et 124 PR avaient été fusionnées depuis sans entrée ; `STATUS.md` et les corps de PR portent désormais l'état — *pourquoi* : le plan ne le développe pas au-delà de ce constat de retard. **Décision inversée par le propriétaire le 2026-10-12** (la présente reconstruction en découle ; le revirement est consigné dans la ligne D7 de `PLAN_BEYOND_CI.md` et dans `STATUS.md`, #930).
- **D1** — première expérience Polity : l'effet d'entrée du seuil électoral, 3 % contre 5 %, sur la fondation de partis — *pourquoi* : à 7 % l'assemblée se vide (OBS-040, médiane 2 partis siégeant).
- **D2** — dire aux fondateurs de partis le seuil (aucun agent ne le voit), comme changement de modèle pré-enregistré avec amendement d'ADR-018 et harnais de neutralité avant/après.
- **D3** — anglais pour les docs nouvelles et vivantes ; une correction d'une ligne garde la langue du doc ; THEORY.md et GUIDE_UTILISATEUR non traduits.
- **D5** — l'effondrement LLM raconté dans `docs/stories/` puis en preprint arXiv ; **D6/D10** — un mode `?niveau=intro` et une démo projecteur locale pour l'enseignant ; **D8** — IRV, Coombs, Benham et Raynaud peuvent échouer au critère du perdant de Condorcet dans nos moteurs (derniers ex aequo éliminés ensemble) : on montre le verdict de manuel plus une note de variante, moteurs inchangés ; **D9** — le registre des critères vivra dans `voter-app/src/data/method_criteria.json`.

**Prochaines étapes** (les « Next 3 steps » de STATUS au 2026-10-08)
- [x] W1.1 : corriger les erreurs d'enseignement confirmées (histoire du paradoxe qui nomme un gagnant de Condorcet dans un cycle, STAR marqué comme respectant la majorité, trois faits de THEORY.md) — #859 (fusionnée le 2026-10-08 au soir).
- [x] W3.1 : correctifs rapides du playground (une palette de candidats, remise à zéro du défilement, visite guidée cassée retirée, fuites en mode anglais, recharts hors du bundle initial) — #860 (fusionnée le 2026-10-08 au soir).
- [x] W2.2 item 5 puis la sonde de la porte W2.1 : dire le seuil aux fondateurs (D2) — #861 ; la porte a dit STOP, la fondation ne suit pas le seuil annoncé — #877 (OBS-045).
- [x] Question ouverte « phase11 atteint-elle la sortie de Phase 4 ? » — analysée par #876 (OBS-044), sortie reformulée par D11 (#892, 2026-10-10).

**Pour aller plus loin** : `docs/plan/PLAN_BEYOND_CI.md`, `docs/STATUS.md` (et son historique `git log -p`).

---

## 2026-10-05 → 2026-10-07 — L'ensemble à dix graines : sortie de Phase 4 non atteinte, le mandat anticipé mal daté, l'abstention par indifférence, et vLLM 0.31.0

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** L'ensemble à dix graines qu'OBS-034 jugeait dû (`phase10`, 8 ans, 100 citoyens, profil exploration) se termine. Il doit confirmer que la sortie de Phase 4 (fragmentation partisane convergente, déclarée atteinte le 2026-10-02) tient sur plus de trois graines. En parallèle, le bump vLLM attend la fin de l'ensemble pour pouvoir prendre le GPU.

**Ce qui a avancé**
- **OBS-039 (fixée, #781)** : `PartyFounded` et `PartyDissolved` (#705) n'avaient jamais été ajoutées au tuple `EVENT_CLASSES`, d'où dérivent tous les types d'événements. Conséquence : l'explorateur ne voyait aucune des 70 fondations/dissolutions d'un run réel, et **aucun agent n'avait vu une fondation de parti dans sa mémoire publique depuis #705** — OBS-029 et OBS-034 ont donc été mesurées avec une mémoire aveugle aux partis. Garde par introspection, `events.py` ajouté aux sources du tampon de prompt, glyphe de parti dans la chronologie.
- **OBS-040 — sortie de Phase 4 non atteinte** (#800) : le nombre effectif de partis (en sièges) est dans la bande 1,5–8 à la dernière élection dans 5 graines sur 10, à la première dans 1, aux deux dans aucune (médiane 8,42) ; les graines 1–3 d'OBS-034 rejouées sur le code récent passent de 7,29 à 10,54 en moyenne. Cause : fonder un parti et gagner un siège demandent tous deux 5 citoyens sur 100, et rien ne pousse les petits partis à se regrouper. #808 montre que le seuil est une falaise, pas un réglage : à 0,07 la médiane tombe à 2 partis siégeant, à 0,10 aucun parti ne passe dans 9 graines sur 10 — la fragmentation est dans le vote.
- **OBS-041 — le mandat d'un président élu hors calendrier mal daté** (#800, corrigé par #801) : 54 des 57 présidents élus lors d'élections anticipées croyaient leur mandat finir jusqu'à 15 ticks trop tard ; la fausse date atteignait le briefing, le bulletin d'amendement, la pression, et fermait `refuse_to_leave` (ADR-022) aux cinq présidents limités en mandats qui arrivaient au tick où l'acte est offert. `InstitutionalClock.next_presidential_election` devient la seule source de `term_end_tick` ; golden polity et fixture de l'explorateur régénérés (oracles retenus par la gate de revue).
- **OBS-042 — deux citoyens sur trois s'abstiennent** (#800), cause trouvée par #808 : la règle comparait le meilleur candidat au suivant, ce qui fait monter l'abstention avec la taille du champ (27 % à 2 candidats, 80 % à 20). **#819 change la règle** : on reste chez soi quand son favori vaut à peu près un vote blanc (≈ 10 % quel que soit le champ), coût de participation gardé à 0,04 ; ADR-011 amendée.
- **OBS-043 (#849)** : deux prompts disaient qu'un candidat de son propre parti « compte davantage », alors que `vote.partisanship` vaut 0 dans toutes les configs du dépôt. La phrase n'apparaît plus que si c'est vrai ; à n=80 elle ne changeait pas mesurablement les choix ; la table de campagne d'ADR-023 (un seul run à n=40) est re-mesurée.
- **OBS-035** : le journal des limites de l'ensemble (322 entrées, toutes de candidats) ne demande rien d'extra-légal ni d'institutionnel — pas de nouveau mécanisme à construire (#808).
- **vLLM 0.31.0** (#789, fusionnée le 2026-10-05 au soir) : tous les profils compose bougent, y compris le profil 4B resté sur 0.28.0. Protocole de bump lancé après l'ensemble, contre un témoin 0.30.0 re-mesuré avec EAGLE-3 : rien de cassé, vitesse indiscernable du bruit, **cache KV +34 %** au démarrage à froid ; 162 réponses sur 174 identiques, les 12 qui changent dans les familles qui bougent à chaque bump.

**Points bloquants**
- OBS-040 : les leviers (la bande elle-même, `founding_ratio`, le seuil, l'exemption des partis siégeants, ou rien) sont listés pour le propriétaire, non tranchés à ce moment (#800).
- OBS-041 laisse deux questions au propriétaire : un mandat anticipé d'un tick compte-t-il dans la limite de mandats, et faut-il une durée minimale avant `refuse_to_leave` (#801).
- Turnout des runs LLM sous la nouvelle règle d'abstention non mesuré : les « environ 70 % » d'#819 sont une estimation ; un run repris à travers le changement change de règle en cours de route sans que le hash de config le voie (« Non vérifié » d'#819).

**Décisions prises**
- Coût de participation gardé à 0,04 plutôt que 0,15 (#819) — *pourquoi* : 0,04 garde la propriété approuvée (≈ 10 % d'abstention quelle que soit la taille du champ) ; 0,15 satisfait les quatre faits d'ADR-011 sur le jumeau déterministe mais fait dépendre l'abstention du champ (44 % → 28 %). Pris sur le « continue » du propriétaire après recommandation.
- La ligne de prompt partisane corrigée même sans effet mesuré (#849) — *pourquoi* : on ne dit pas aux agents des règles fausses (contrat C3), qu'ils agissent dessus ou non.

**Prochaines étapes**
- [x] Relancer l'ensemble sur le noyau corrigé (OBS-041/042/043) — phase11, analysée par #876 (OBS-044, 2026-10-09).
- [x] Trancher OBS-040 — D1 (expérience de seuil 3 % contre 5 %, 2026-10-08) puis D11 : la bande est rapportée, pas une porte (#892, 2026-10-10).
- [x] Trancher les questions d'OBS-041 — un mandat compte s'il est gagné avec au moins la moitié restante, pas de durée minimale séparée (#891, 2026-10-10).

**Pour aller plus loin** : `docs/plan/polity/observations.md` OBS-039 à OBS-043, `docs/plan/polity/plan-polity-agency-roadmap.md` (ligne de sortie de Phase 4), `fast_api_voter/scripts/check_vllm_031_bump_results.md`, `docs/adr/ADR-011-utility-vote-with-turnout.md`, `docs/adr/ADR-023-campaigning.md`.

---

## 2026-10-04 → 2026-10-08 — La CI resserrée de bout en bout : tests profonds sur polity, tableau de bord, /verify, audit en cinq lots, e2e en deux shards

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Les PR de cette période exécutent pas à pas un « plan CI » à phases numérotées (Phase 2, 5, 6, 7, 12, 13, 14 dans les corps de PR) puis un audit CI du 2026-10-06 découpé en lots A à E. Ce plan n'est pas versionné dans `docs/plan/` : on ne le connaît que par les citations des PR. C'est cette période que le plan du 2026-10-08 gèlera (entrée ci-dessus).

**Ce qui a avancé**
- **`polity` surveillée comme `develop`** : les tests profonds (mutation, Schemathesis, fuzzing atheris, chasse aux flakys, DAST, GuardDog, scan d'image) tournent enfin sur `polity`, et une issue `polity-red` unique s'ouvre tant qu'un workflow y est rouge — `polity` était déjà restée rouge trois jours sans que personne ne le voie (#747) ; le watchdog ci-health regarde aussi `polity` et y devient requis (#754).
- **Tableau de bord CI sur GitHub Pages** (Phase 14a, #763) : collecte de chaque tentative de run sur une branche `ci-data`, puis une série de correctifs (#775, #776, #778, #779, #780, #785) pour lire les logs malgré les codes couleur et regrouper les échecs par leur vraie erreur. Agent `ci-doctor` et rapport hebdomadaire en issue (Phase 14b, #771).
- **« Le changement fait-il ce qui a été demandé ? »** : agent `spec-checker` en lecture seule, commande `/verify`, sections `## Demande` / `## Critères d'acceptation` / `## Preuves` dans le gabarit de PR, définition de « fini » dans `CLAUDE.md` (#788). Les PR suivantes l'emploient (#819, #849, #858).
- **Tests qui ne testent rien** : check consultatif « rouge sur la base » (les nouveaux tests d'une PR `fix`/`feat` doivent échouer sur l'ancien code, #792) ; mutation des seules lignes modifiées (#793 — premier passage : 17 mutants, 2 survivants), survivants ensuite couverts (#798) ; le log de mutmut enfin téléversé (#810), ce qui permet de relever la baseline de mutation backend de 66,02 % à 68,17 % (#811).
- **Scripts `fast_api_voter/scripts` sous les gates** : le harnais de tests LLM sous mypy strict et pytest (#794), chaque script doit encore s'importer (#795), dette mypy des scripts plafonnée à 150 erreurs par ratchet (#796), fast-gate qui saute les checks backend sur un interpréteur trop ancien au lieu d'échouer (#797), 41 scripts d'expérience terminés archivés (#818). Catalogue numéroté de 40 invariants polity (`docs/spec/behaviors.md`, #816) et vérificateur d'invariants du journal sur des runs tirés par Hypothesis (#817).
- **Hygiène des workflows** : job requis `Workflow lint` (actionlint, zizmor — 0 finding, la plupart corrigés plutôt que tolérés —, tests des hooks) (#799, #805) ; nombres de workflows et de checks requis générés pour ne plus dériver (#807, #809).
- **e2e en deux shards** (#812) : ~11 min → **6 min 37 s** sur le run de la PR, le nom requis `Playwright E2E` gardé par un job agrégateur ; cible de 5–6 min manquée car les shards sont répartis par nombre de tests, pas par durée.
- **Audit CI du 2026-10-06, lots A–E** (2026-10-07) : Secret Scan hebdomadaire réparé (3 faux positifs) et surveillé (#820) ; un job `changes` en échec ne peut plus rendre vert un check requis, et la gate ne peut plus rester pendante (#821) ; le garde-fou bash ferme d'autres routes de merge/approbation (#822) ; semgrep et jscpd épinglés, jeton SARIF par job (#823) ; dérive des docs CI corrigée (#824). Puis les cinq points différés : jeton d'écriture hors du collecteur du tableau de bord (#826), Codecov par OIDC sans jeton stocké (#827, #840), commentaire de mutation posté depuis un job `workflow_run` (#828), audits zizmor en ligne hebdomadaires (#831), image Playwright épinglée par digest (#832).
- **Gate de revue et branches** : épingles Python retenues pour revue (#757), réponse `/reviewed` postable sur une PR (#758), ci-health attend la gate dans les checks requis de `develop` (#749) ; la gate `High-risk review gate` postée par une GitHub App et épinglée dans la protection, parce qu'un workflow de PR pouvait poster un statut du même nom (#847) ; diff-cover vérifie aussi les branches sur les lignes modifiées (#848) ; `main` rendue protégeable — la release ne pousse plus qu'un tag (#836) — et sa protection surveillée (#839).
- **Dépendances** : groupes Dependabot (#790, #829, #843), alignement des épingles Python (#753), règles d'ignore (`jsonschema-rs >= 0.58` bloqué par schemathesis #786, `graphql-core >= 3.3` #841), exceptions d'audit npm datées pour seroval/source-map-js (#803, #814, retirée pour source-map-js par #837), devtools react-query passées en devDependency chargée en dev seulement (#815). Instantanés ci-health (#756, #838, #852).
- **Syncs vers `develop`** (vrais merges) : #751, #755, #765, #772, #782, #787, #806, #813, #825, #834, #842 (et #853, le 10-08).

**Points bloquants**
- Shards e2e déséquilibrés (3 min 14 s contre 6 min 02 s) : un troisième shard ou une autre répartition est laissé en suite (#812).
- `main` n'est protégée qu'une fois `setup-branch-protection.sh main` lancé à la main après #836 ; que ce soit fait n'est pas établi par les sources lues.

**Décisions prises**
- **`/code-review high` avant toute PR, moteur de vote compris**, à la place de `max` réservé au moteur — décision du propriétaire du 2026-10-07 (#835 ; #824 avait laissé le niveau inchangé, en le renvoyant au propriétaire) ; *pourquoi* : raison non consignée au-delà de la demande ; les syncs de release en sont exemptées parce que chaque PR qu'elles portent a déjà été revue.
- **`strict: true` gardé** sur la protection de branche (#835) — *pourquoi* : un merge manuel hors file doit aussi être à jour ; coût accepté, Mergify teste une PR à la fois.
- **Protéger `main`** (#836) — demande du propriétaire ; `release.yml` poussait directement sur `main`, ce qu'une protection aurait refusé.

**Prochaines étapes** (ce que disaient les PR)
- [ ] Rééquilibrer les shards e2e si le temps mesuré déçoit (#812).
- [x] Faire passer le groupe Dependabot #846 une fois la cause trouvée — #851 puis #855 (2026-10-08).
- [ ] Le reste est suspendu par le gel « maintenance seulement » du plan du 2026-10-08.

**Pour aller plus loin** : `CONTRIBUTING.md`, skill `voter-ci`, `docs/spec/behaviors.md`, `scripts/ci_dashboard/`.

---

## 2026-10-04 → 2026-10-05 — L'intérêt personnel sur le bulletin d'amendement (OBS-038) et la revue de l'explorateur /polity sur 141 runs réels

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Deux fils. D'un côté OBS-038 (2026-10-03) : la chambre tirée au sort juge la formulation d'un amendement autant que le président — un troisième mandat présenté comme « stabilité et continuité » passe là où la version franche échoue. De l'autre, une revue de l'interface `/polity` contre 10 des 141 runs réels de la machine, plus une revue anti-sur-ingénierie, transformée en un plan en étapes 0 à 4 et exécutée dans la journée.

**Ce qui a avancé**
- **OBS-038, en trois temps.** #748 ajoute au bulletin une ligne de conséquence quand l'amendement desserre une règle qui lie son auteur (limite de mandats, plancher de révocation, seuil de pétition) ; mesuré seulement pour la limite de mandats. #750 corrige l'outil de mesure (il composait son propre bulletin, différent de celui du noyau, et testait le cas facile) : mesuré sur le cas dur, le troisième mandat bien formulé obtient encore **57 % de oui — l'exploit est réduit, pas fermé**, et OBS-038 est corrigée en conséquence. #784 inscrit alors la limite de mandats présidentiels comme article **verrouillé à 75 %** : à ce seuil, le troisième mandat formulé passe ≤ 6 % du temps, un changement largement soutenu ~65 % ; mesuré en direct, afficher le seuil plus élevé ne pousse pas les membres à voter oui plus facilement.
- **Vue Phase 5 dans la chronologie** (#752) : actes extra-légaux et campagnes ont leurs glyphes et leurs couloirs ; une vérification au navigateur a trouvé que les piles de campagnes débordaient sur trois autres couloirs (bug latent, corrigé).
- **Revue de l'explorateur, étapes 0 à 4** : légende des glyphes (#759) ; runs nommés par répertoire et runs inachevés signalés — 103 des 141 partageaient leur libellé avec un autre (#760) ; lentilles Vote/Candidature qui disent qu'un tick n'a pas d'élection (#761) ; code allégé de 227 lignes nettes sans changer le comportement (#762, #764) ; récit du citoyen sélectionné à côté de la carte (#767), répétitions regroupées (#768) ; présidence vacante marquée (#769) ; le gagnant d'une élection ouvre son récit (#770) ; chronologie défilante sur écran étroit, événements repliés par couloir (#774) ; au-delà de six partis, la forme distingue les partis, par coloration gloutonne d'intervalles (#777).
- **Le vrai bug de la revue** (#766) : depuis les partis mutables (#705), l'explorateur dessinait les partis du dernier checkpoint à chaque tick et attribuait à chaque citoyen son parti de l'année 0. Les partis sont maintenant reconstruits (k-means sur le recensement de l'année 0 + les événements `party_founded`), ce qui reproduit exactement chaque parti de checkpoint sur 140 runs ; affiliation par année de recensement.
- **Palette sombre de la carte** (#783) : trois couleurs de parti hors de la bande de luminosité sombre, vote blanc invisible (1,23:1), hiérarchie inversée ; une palette sombre choisie (pas inversée) et validée sur toutes les paires, mêmes teintes dans les deux thèmes.

**Points bloquants**
- Le glyphe d'acte extra-légal n'a jamais été vu dans un run réel : `extra_legal_act` n'y a jamais eu lieu (#752).
- La liste des événements institutionnels côté tests reste tenue à la main — c'est ce qui a laissé passer les événements de parti (#752, puis OBS-039 dans l'entrée ci-dessus).
- Les lignes de conséquence « plancher de révocation » et « seuil de pétition » sont testées unitairement mais pas mesurées en direct (#748).

**Décisions prises**
- Verrouiller la limite de mandats à 75 % plutôt que s'en tenir à la ligne d'intérêt personnel — choix du propriétaire, « le correctif le plus fort » (#784) — *pourquoi* : 0,75 est la seule valeur testée qui bat l'exploit formulé tout en laissant passer un soutien large, et c'est déjà le verrou de la procédure d'amendement elle-même.
- Plusieurs partis au-delà de la palette : une forme en plus de la couleur plutôt que des teintes recyclées ou générées — choix du propriétaire (#777).
- Écartés, raisons dans les PR : imbriquer les clés i18n des lentilles et couloirs (plus de lignes de locale que de code gagnées, #764), supprimer `xyOf` (#762).

**Prochaines étapes**
- [x] Une vue pour les fondations et dissolutions de partis de Phase 4, absentes de la chronologie (#752) — #781 (2026-10-05).
- [x] Palette sombre de la carte, signalée hors périmètre par #777 — #783 (2026-10-05).
- [ ] Voir si `refuse_to_leave` finit par se déclencher maintenant que la voie légale vers un troisième mandat est fermée ; l'ensemble à dix graines en cours précède ce changement (#784).

**Pour aller plus loin** : `docs/plan/polity/observations.md` OBS-038, `docs/plan/polity/polity-run-explorer.md`.

---

## 2026-10-02 → 2026-10-03 — Sortie de Phase 4 mesurée, la campagne ciblée (5.2) et son plafond de portée, la chambre sensible à la formulation

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Après la réparation du prompt du forum (#714), il restait à savoir si la fondation de partis s'emballait ou se stabilisait, et ce que les agents réclamaient vraiment dans le journal des tentatives hors règles (`other_initiative`). Les réponses ont réordonné la Phase 5.

**Ce qui a avancé**
- **Sortie de Phase 4 atteinte** (#729, OBS-034) : trois graines de 8 ans (p100, 15 sièges, profil exploration). Le nombre de partis converge vers l'an 4 (21–23) ; le nombre effectif de partis par sièges tombe de 9,6–10,6 à la première élection législative à 5,8–8,5 à la seconde (moyenne 7,29) : deux graines sur trois dans la bande 1,5–8 visée, la troisième juste au-dessus (8,50). La lecture « croissance sans fin » du run de 3 ans (#716) venait d'un run arrêté dans le transitoire. `parties.founding_ratio` n'a pas eu besoin d'être réglé.
- **OBS-035** (#730) : sur 399 tours d'agents, 101 entrées `other_initiative`, dont 56 demandent un moyen d'atteindre les électeurs (campagne, publicité, débat) ; aucun acte extra-légal tenté, `extra_legal_act` n'a jamais tiré (troisième série de runs sans). La roadmap réordonne la Phase 5 : la campagne ciblée passe avant `postpone_election`/`insurrection`.
- **5.2, campagne ciblée** (#734, ADR-023) : un candidat fait campagne sur un enjeu ; les citoyens atteints pondèrent davantage cet enjeu (saillance, pas persuasion), via `weighted_distance` existant. Forme du champ mesurée en direct sur trois variantes : seul l'objet imbriqué *requis et nullable* est toujours pesé (22–60 % d'usage, 2 % de relances), l'optionnel n'est utilisé qu'une fois sur 160 (OBS-031 qui se reproduit). Sonde de neutralité : les trois contrôles passent.
- **OBS-036 puis plafond de portée** (#735) : sans plafond, 91 % des citoyens deviennent quasi mono-enjeu en 8 ans (attention médiane sur l'enjeu principal 0,56 contre 0,17), avec plus de révocations dans chaque graine (2→4, 4→8, 6→10). Cause : l'audience `undecided` couvre la majeure partie de l'électorat, 45–54 contacts par citoyen. `campaign.max_reached` (12 dans le profil exploration) tire l'audience au sort sur un `campaign_rng` checkpointé.
- **Vérification du plafond** (#744, OBS-037) : la concentration tombe à 0,34 (34 % au-dessus de 0,40), les révocations à 3/6/9 — mais la prédiction de 0,19 échoue : les candidats convergent sur un même enjeu (34–48 % des campagnes). Les 18,2 partis effectifs de la graine 2 viennent d'un auto-amendement du seuil électoral (0,05 → 0,03 → 0,02), pas de la campagne.
- **OBS-038** (#744, #746) : la chambre a ratifié un troisième mandat 14 contre 15. Mesuré hors ligne : la justification (intérêt personnel vs bien public) et l'approbation déplacent chacune le vote d'environ 25 points, et chaque « oui » reprend les mots du proposant. Corrige l'ampleur d'OBS-030 (80 % → 7 % mesuré contre une justification irréalistement franche).

**Points bloquants**
- `refuse_to_leave` n'a jamais tiré ; #746 avance une explication candidate (la voie légale vers un troisième mandat est trop ouverte), non démontrée. Reste ouvert dans OBS-035 si les agents ne veulent pas d'actes extra-légaux ou ne les voient pas.
- Deux OBS (#716, #730) ont été poussées sur la branche d'une PR déjà fusionnée par la file en quelques minutes, d'où des PR séparées.
- Trois graines restent une étude de cas ; la roadmap en veut dix pour une affirmation de résultat (#729).

**Décisions prises**
- Campagne ciblée avant les autres actes extra-légaux (#730, roadmap §Phase 5 « Reordered 2026-10-02 ») — *pourquoi* : la règle de la roadmap construit d'abord les actes que les agents tentent, et le journal n'en demande pas d'autre.
- OBS-037 acceptée, pas de décroissance ajoutée (#745, décision du propriétaire) — *pourquoi* : la convergence d'agenda est jugée un comportement de campagne plausible plutôt qu'un défaut prouvé ; coût à mentionner dans toute affirmation de résultat (concentration ×2, révocations ~+50 %).
- Correctif d'OBS-038 décrit mais pas construit (#746) — *pourquoi* : une chambre sensible à la rhétorique est un choix de modélisation laissé au propriétaire.

**Prochaines étapes**
- [x] Ligne factuelle sur le bulletin quand un amendement servirait son proposant (OBS-038) — #748, #750.
- [x] Ensemble à dix graines pour la sortie de Phase 4 — #800 (conclut : sortie *non* atteinte, OBS-040..042).
- [ ] Rouvrir OBS-037 si un run de 30 ans montre la concentration qui monte avec la durée (#745).
- [ ] `postpone_election`, `insurrection`, dérive de Λ et sortie d'un régime irrégulier : en attente d'un journal qui les demande (roadmap Phase 5).

**Pour aller plus loin** : `docs/plan/polity/plan-polity-agency-roadmap.md` (Phase 4 « Exit », Phase 5), `docs/adr/ADR-023-campaigning.md`, `docs/plan/polity/observations.md` OBS-034 à OBS-038.

---

## 2026-10-02 → 2026-10-03 — Durcissement CI : gate npm audit daté, Dependabot vers polity, garde-fous d'agent et revue humaine obligatoire

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** `polity` était rouge au push depuis le 2026-09-30 sans changement de code (une nouvelle alerte `brace-expansion` via eslint), et Mergify fusionnait toute PR verte sans aucune approbation. Une série de PR, numérotées par phases d'un « plan de durcissement CI », a transformé les règles en prose de `CLAUDE.md` en contrôles qui tournent.

**Ce qui a avancé**
- **Gate `npm audit` sur tout l'arbre** (#721) : `check-npm-audit.mjs` bloque high/critical, y compris en dev (`workbox-*` est livré dans le bundle) ; exceptions dans `.github/npm-audit-allowlist.json`, chacune datée (≤ 90 jours), motivée et limitée aux chemins revus ; 12 tests `node:test`. Lockfile corrigé avec npm 11 pour respecter `min-release-age=7`. Le 10-03, deux nouvelles alertes sans version corrigée (`braces`, `http-cache-semantics`, dev uniquement) re-rougissent `polity` → deux exceptions jusqu'au 2026-11-02 (#738).
- **Dependabot cible `polity`** (#722, synchro `develop` #723) : jusque-là ses PR visaient `develop`, qui ne reçoit que des synchros de release ; `pymdown-extensions >= 12` ignoré (plafonné par `marimo`, #720 insoluble).
- **Retenue des PR à haut risque** (#724, synchro #725) : 55 chemins protégés (moteur de vote, workflows, `.claude/`, oracles de test) exigent un `/reviewed <sha>` du propriétaire sur le commit de tête. **Elle n'a rien retenu** : #731 est passée dans la file en 16 secondes sans revue, le bloc `merge_protections` n'étant jamais évalué (#732). #732 (synchro #733) la fait appliquer par un statut requis, `High-risk review gate`, posté par un job `pull_request_target` ; #740 corrige le script `setup-branch-protection.sh` qui refusait à tort (`curl | grep -q` sous `pipefail`).
- **Garde-fous de session agent** (#731) : `scripts/fast-gate.sh` (les outils de CI sur les fichiers modifiés, lancé avant chaque push) et des hooks Claude Code qui refusent force-push, push vers les branches protégées, `--no-verify`, `gh pr merge` et l'auto-approbation ; 23 tests ; une revue `/code-review medium` a trouvé et fait fermer 5 contournements.
- **Intégrité des tests** (#736, synchro #737) : une PR qui retire des tests ou ajoute skip/only/xfail est retenue comme un chemin protégé (`check_test_integrity.py`, statique, 20 tests). Lint des tests backend (#741, ruff sur `api/tests`, `strict_markers`, `xfail_strict` ; 13 constats corrigés, aucun test retiré) et frontend (#742, `@vitest/eslint-plugin`, compte sonarjs inchangé à 264).
- **Rapport de diff d'oracle** (#743) : `oracle_diff_report.py` traduit un oracle régénéré (fixture de parité, golden, contrat OpenAPI, baselines, snapshots) en changement lisible (« `majority_judgment`: 8 scénarios changent de gagnant »).
- Dépendances : Dependabot #718, #719 (vers `develop`), #726, #728 ; snapshot ci-health #739.

**Points bloquants**
- Un statut GitHub reste falsifiable par une PR qui ajoute son propre job (#724) ; seul le fait que `.github/workflows/` soit lui-même protégé le rend coûteux.
- Un `gh pr merge` manuel contourne Mergify (#724) ; le hook #731 ne lie que les sessions Claude Code.
- Les specs e2e Playwright ne sont pas couvertes par le lint de tests (#742).

**Décisions prises**
- Exceptions d'audit datées plutôt qu'un gate affaibli (#721, #738) — *pourquoi* : un check requis ne doit pas rougir quand le code n'a pas changé, mais chaque exception est re-revue au moins tous les 90 jours.
- `no-conditional-expect` laissé désactivé (#742) — *pourquoi* : les 13 cas signalés sont des vérifications pilotées par les données, et la règle ferait monter le compte sonarjs du ratchet.
- Les fichiers de contrôle (`.mergify.yml`, `dependabot.yml`, workflows `issue_comment`) sont synchronisés vers `develop` par PR dédiée (#723, #725, #733, #737) — *pourquoi* : GitHub et Mergify ne les lisent que sur la branche par défaut.

**Prochaines étapes**
- [x] App GitHub dédiée pour poster le gate de revue (« Phase 3b », #724) — #847.
- [ ] Supprimer les deux exceptions `braces`/`http-cache-semantics` dès qu'une version corrigée sort (échéance 2026-11-02, #738).
- [ ] Faire passer le contrôle de licences hors `--production` pour couvrir `workbox-*` (#721).

**Pour aller plus loin** : `CONTRIBUTING.md` (retenue de revue), `CLAUDE.md` (Gate commands, Workflow), `.claude/hooks/`, `scripts/fast-gate.sh`.

---

## 2026-09-29 → 2026-10-02 — Aucun parti fondé : les prompts d'agents mesurés et réparés, `refuse_to_leave` (5.1), sonde Qwen3.8-27B

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Les Phases 1 à 4 étaient fusionnées (entrée suivante). Le premier test du critère de sortie de Phase 4 a échoué, et la cause s'est révélée côté prompts plutôt que côté noyau.

**Ce qui a avancé**
- **OBS-029** (#709) : trois graines d'exploration (8 ans, p100, Qwen3-8B), aucun parti fondé ; 99 % des tours de forum répondent `party_move: none`. #710 retire deux tournures qui en dissuadaient : la variante `neutral` fonde un parti dans 2 graines sur 3 (contre 0 sur ~1 590 posts avant), la variante `invite` (1/3) n'est pas retenue.
- **5.1, `refuse_to_leave`** (#711, ADR-022) : un président limité en mandats peut refuser de partir ; le noyau tire le succès une fois avec un `regime_rng` (logistique de l'approbation, de la loyauté, de la sévérité). Succès : pas d'élection, régime irrégulier, révocations suspendues ; échec : destitution.
- **Provenance** (#712) : `agents.py` et `amendments.py` ajoutés à `PROMPT_SOURCE_FILES` — un changement de prompt d'agent ne changeait pas l'empreinte du run, et les statistiques de balayage pouvaient moyenner des runs de prompts différents.
- **OBS-030** (#713) : la chambre votait oui à 95 % des amendements, y compris ceux du président. Une ligne factuelle sur le proposant (parti, approbation, possibilité de se représenter) fait tomber les oui aux propositions intéressées de 74 % à 47 % en A/B hors ligne (troisième mandat 80 % → 7 %). Le prompt présente désormais `refuse_to_leave` comme un acte que la constitution interdit.
- **Mesure de neutralité des prompts** (#714, OBS-031..033) : `check_agent_prompt_neutrality.py` compare chaque prompt à une paraphrase, avec le bruit binomial comme barre. Quatre défauts trouvés et corrigés : `extra_legal` optionnel jamais rempli (0 sur 98 tours ; requis désormais), journal `other_initiative` qui ne contenait que des actes déjà disponibles, prompt du forum qui plaidait pour une option, et un président incapable de proposer l'abolition de la limite de mandats (`"null"` contre `null`, réglé dans `AmendmentProposal`).
- **OBS-034** (#716) : premier run complet après #714 (3 ans) — la fondation se stabilise vers 12 % des tours, 5 → 19 partis sans plateau en 3 ans ; le texte argumente contre un réglage de `founding_ratio` sur cette seule preuve.
- **Profil Qwen3.8-27B pour H100 louée** (#715) : profil non mesuré, `docker-compose.llm-h100.yml`, option `--base-url` pour un serveur tunnelé ; réservé au bake-off tant qu'aucune mesure n'existe.

**Points bloquants**
- Une limite qu'aucune formulation ne lève (OBS-031) : un acte pris moins d'une fois sur dix ne laisse pas l'état dominer le bruit de formulation ; un taux de refus est donc aussi un fait sur la version du prompt.
- L'option `leave` du forum restait morte à la mesure (#714).
- Aucun serveur vLLM n'avait encore chargé Qwen3.8-27B (#715).

**Décisions prises**
- Garder la formulation `neutral` du forum, écarter `invite` (#710) puis une formulation énonçant la règle des cofondateurs (0 fondation sur 100, #713) — *pourquoi* : mesurées moins efficaces sur les mêmes graines.
- N'implémenter que `refuse_to_leave` en 5.1 (#711, ADR-022) — *pourquoi* : c'est le seul acte vers lequel pointait le journal des tentatives (présidents proposant de lever la limite de mandats) ; #714 a ensuite montré que ce journal était plus faible qu'annoncé.

**Prochaines étapes**
- [x] Run long pour voir si `found` fait exploser le nombre de partis — #716, puis #729 (convergence vers l'an 4).
- [x] Un run en direct pour voir si un président tente `refuse_to_leave` — #730 (jamais en 399 tours).
- [x] Vérifier que de vrais besoins atteignent désormais `other_initiative` — #730 (56 demandes de campagne).
- [ ] Premier test (« smoke test ») de Qwen3.8-27B sur une H100 louée (#715) — non vérifié depuis.

**Pour aller plus loin** : `docs/plan/polity/observations.md` OBS-029 à OBS-034, `docs/adr/ADR-022-extra-legal-acts.md`, `fast_api_voter/scripts/check_agent_prompt_neutrality.py`.

---

## 2026-09-28 → 2026-09-29 — La feuille de route « agency » et ses Phases 0 à 4 en une journée : président agent, constitution amendable, forum, partis mutables

> Entrée reconstruite a posteriori le 2026-10-12, à partir du git log, des descriptions de PR et des documents datés.

**Contexte du jour.** Le 2026-09-27, le propriétaire fixe la nouvelle direction de polity : des citoyens et des dirigeants qui agissent, débattent, s'organisent et changent les règles, le noyau restant arbitre. La feuille de route est fusionnée dans la nuit, puis une trentaine de PR la déroulent jusqu'à la Phase 4.

**Ce qui a avancé**
- **Feuille de route** (#678, `plan-polity-agency-roadmap.md`) : état de l'art à `7c2adf37`, Phases 0 à 5, décisions D1–D10, et un tableau « laissé de côté, ajouter quand » qui borne ce qu'on construit.
- **Phase 0** : #679 valide chaque réponse LLM *dans* la boucle de relance (OBS-021) — sur les 8 premiers ticks d'un run p500, la chambre passe de 7,5–8,3 % d'unités en repli à 0/675. #680 ajoute le profil `--profile exploration`.
- **Phase 1, dirigeants et popularité** : approbation qui nourrit la légitimité, sortant jugé sur son bilan (#680), courbe dans l'explorateur (#688) ; **le président devient un agent** — persona, mémoire reconstruite depuis le journal, un tour par tick (#689, ADR-014) ; température de tour 0,6 (#695) ; journal du dirigeant dans la biographie de l'explorateur (#696) ; candidats agents qui font campagne face à un sondage d'intentions de vote (#698).
- **OBS-028** (#695, #697) : le président répétait mot pour mot ses discours ; la température 0,6 ne suffit pas (#695). Cause trouvée sur 3 graines × 2 bras : la mémoire lui renvoyait ses propres discours. Les retirer donne 13 discours distincts sur 13 dans chaque graine (#697).
- **Phase 2, constitution typée** : 7 articles amendables et règles en vigueur reconstruites à chaque tick (#699, ADR-015, remplace ADR-008 §2) ; le président propose, la chambre tirée au sort vote, avec retranchement par article (#700) ; amendements visibles dans le digest et la timeline (#701). Démonstration : passer à Borda au tick 16 change les élus des ticks 32 et 48.
- **Phase 3, forum** : membres de la chambre et pétitionnaires récents postent (#702, ADR-016), un post peut faire changer d'avis son auteur (#703, ADR-017), posts lisibles dans la biographie (#704).
- **Phase 4** : adhérer, quitter ou fonder un parti (#705, ADR-018), coalition négociée par les chefs de parti (#706, ADR-019), référendum sur un changement de mode de scrutin (#707, ADR-020), désengagement et départ des citoyens selon leur colère (#708, ADR-021).
- À côté : docs de release alignées sur v0.2.0 (#685, prévu par l'entrée précédente), journal du 13 au 27/09 et EXP-018 à 022 (#686), rotation des entrées d'août vers l'archive (#687), `curl` retiré de l'image de production pour 2 alertes Trivy (#693).

**Points bloquants**
- La boucle approbation → légitimité est vivante mais faible : approbation 0,690–0,700 contre un mandat de 0,699 sur 2 ans (#680).
- Le projet de loi de l'agent n'est pas exercé en direct à la graine 42 (cohabitation, #689) ; il l'est aux graines 1 et 2 (#697).
- Effet secondaire de #697 : sans ses discours, le président bouge moins (0 mouvement à la graine 1), à surveiller (OBS-028).
- Pensée des agents : 21 tours de président sur 22 et 9 de candidat sur 10 atteignent le plafond de 2 048 tokens ; ajouté à OBS-023, l'effet d'un plafond plus haut reste ouvert (#698).

**Décisions prises**
- D1–D10 avec le propriétaire, le 2026-09-27 (#678, roadmap §2) — notamment constitution typée (D2), profil exploration où tout nouveau mécanisme est activé (D4), poids ouverts uniquement (D5), dirigeants d'abord (D7), objectif du dirigeant implicite (D8), actes extra-légaux en dernier (D10) ; *pourquoi* : raison non consignée au-delà du texte des décisions.
- Tout nouveau mécanisme livré désactivé dans `polity_config.yaml`, activé dans le profil exploration (D4, chaque PR de #680 à #708).
- Le forum dérive l'ensemble de ses agents du journal plutôt que de stocker un état de promotion (#702) — *pourquoi* : le checkpoint ne gagne rien ; `forum_size` (30) plafonne les tokens à la place.
- Changement d'avis porté par le tour de forum, sans tour de réflexion séparé (#703) — *pourquoi* : aucun n'avait été construit en Phase 1, et le tour de forum lit déjà le fil et les notes de l'agent.

**Prochaines étapes**
- [x] Mesurer le critère de sortie de Phase 4 (nombre de partis, nombre effectif 1,5–8) — #709 (échec), #729 (atteint sur 3 graines), puis #800 (non atteint sur 10).
- [x] Phase 5.1 — #711.
- [ ] Lire les déclarations `coalition_decision` du premier run d'exploration : les réponses s'effondrent-elles encore ? (case non cochée de #706).

**Pour aller plus loin** : `docs/plan/polity/plan-polity-agency-roadmap.md`, `docs/adr/ADR-014` à `ADR-021`, `docs/plan/polity/observations.md` OBS-028.

---

## 2026-09-24 → 2026-09-27 — Audit des égalités par ordre de listing, première release v0.2.0, polity devient la seule branche de travail

**Contexte du jour.** Plan d'audit approuvé en amont : finir `develop`, sortir la première release `develop→main`, fusionner `develop↔polity` dans les deux sens, puis continuer sur `polity` seule. L'invariant visé sur tout `develop` : réordonner les candidats d'une requête ne doit jamais changer le résultat — une égalité exacte se tire au sort avec la graine de l'endpoint, jamais par ordre de listing ou par plus petit id.

**Ce qui a avancé**
- **Phase A (develop) — fin de la série « égalités par ordre de listing »** : #640 (Hamilton compare les restes exacts, une égalité de reste va au nom), #643 (multi-gagnants : lignes FPTP, complétion Equal Shares, ancre de coalition), #657 (cause racine trouvée : les utilités étaient arrondies à 4 décimales avant classement, ce qui inventait des égalités — arrondi retiré), #659 (playground : assemblée, équité structurelle, no-show), #661 (la transformation stratégique du profile engine inventait une égalité en tête de classement — remplacée par un échange de valeurs), #660 (cache Redis : `GIT_SHA` n'était jamais défini au déploiement, chaque déploiement réutilisait l'espace de cache « dev » — espace de cache par processus désormais).
- **CI** : #641 (watchdog ci-health sur une branche fixe, `pipefail`, groupes Dependabot), #649 (e2e servi sur un build de production `vite build`+`vite preview` plutôt que le serveur de dev — tue les flakes WebKit de modules perdus, proxy `ws: true`), #651 (un corps de réponse d'erreur vide déclenche une alerte), #650 (`quota_type` STV validé — `droop`/`hare`, pas n'importe quel nom renvoyé), #644 (plafonds sur `profile-simulate`, l'électorat capé à 500). Dependabot : #632, #636, #637, #645 (size-limit 14, groupé), #646.
- **Release** : #669 fusionne `develop→main` (470 PR, première release depuis juillet). Titre « Release: … » rejeté par la politique de branche (Conventional Commits requis) ; `diff-cover` rouge par construction (`main` très en retard, 55 lignes déjà passées au gate sur `develop`) ; `main` sans protection → fusion manuelle. Premier vrai dispatch de `release.yml` (run `36292989132`) : **échec** — le job backend n'installait que `requirements.txt` + pytest, jamais `hypothesis`/`schemathesis`/`z3`, un chemin jamais exercé avant. #672 corrige (lockfile dev, plafonds de perf, `test:coverage`+`build` côté front) ; un `/code-review max` sur la branche trouve surtout que la garde de `release.yml` acceptait n'importe quel ancêtre de `main` (un double dispatch aurait pu re-publier une release) → garde « commit exact » + `push --atomic`. #673 porte le correctif sur `main` (Mergify ne file pas les PR vers `main`, fusion manuelle) ; nouveau dispatch → **v0.2.0 taguée et publiée le 2026-09-27** (`git tag` le confirme), premier tag du dépôt.
- **Phase C** : #671 fusionne `develop→polity`, 10 conflits (`main.py`, i18n, un EXP-015 en double → hook renuméroté EXP-017) et plusieurs casses silencieuses corrigées après coup (imports `lazyWithPreload`, `d3-delaunay`→`d3`, `scipy` réajouté, lockfiles régénérés, un ternaire imbriqué sonarjs dans `RunFacts` pour tenir la barre à 264). OBS-026 enregistre que Kemeny-Young et le jugement majoritaire changent de comportement via ce merge (fixes venus de `develop`, pas une anomalie). Le snapshot visuel du Laboratoire a été remplacé par le rendu du job CI (seul diff réel : le lien Polity de la navbar). `polity` avait bougé entre-temps (#670 avait pris OBS-024/025) → renumérotation nécessaire.
- **Phase D** : #674 fusionne `polity→develop` ; `diff-cover` y trouve 5 branches d'erreur polity jamais testées → 5 petits tests ajoutés. #675 est la dernière convergence : `develop` et `polity` identiques. #676 met à jour `CLAUDE.md` et le skill `voter-ci` — **`polity` devient la branche de travail**.
- **E1** : #677 — une égalité de sièges législatifs se tire désormais au sort (`Random("legislative-seats:<seed>:<tick>")`, sans état checkpointé) au lieu d'aller au plus petit `party_id`. Golden et fixture explorer inchangés (aucun run enregistré ne tombait sur une égalité). OBS-027 ; la revue a fait préciser que `choose_party` et le formateur de coalition départagent toujours par `party_id` — des règles propres à polity, laissées telles quelles délibérément.
- **Ajout reconstruit a posteriori le 2026-10-12 (git log et descriptions de PR), 25 et 26/09.** #638 clôt l'étape 3 du plan d'audit des égalités : une égalité exacte de quotient (D'Hondt, Sainte-Laguë, plus forts restes, SPAV et les quatre méthodes à diviseurs de `/theory/apportionment`) allait au parti listé en premier. Une égalité n'a rien d'exotique : 100/2 = 50/1. Sur `/assembly` (graine 2), le parti Vert obtenait 2 sièges listé en premier et 1 listé en dernier. Polity n'est pas touché.
- **CI health** : « CI health check » était rouge sur `develop` et sur toutes les PR depuis le 21/09, sans que rien ne soit cassé. Le battement de cœur hebdomadaire (7 jours) et la limite d'obsolescence (36 h) se contredisaient ; #639 les aligne. Snapshot mis à jour par #652.

**Points bloquants**
- Un départage par nom pour les égalités d'utilité a été codé puis **mis de côté** (jamais ouvert en PR) : il échange la dépendance à l'ordre de listing contre une dépendance au nom, et casserait la parité avec le moteur client — à trancher sur les deux moteurs à la fois, pas en urgence.
- Le reste de la série reste ouvert : issues #662 à #667, suivies dans `docs/plan/vote-app/LISTING_ORDER_TIES.md` (#668).
- Mergify a cessé d'auto-mettre les PR en file (probable désactivation côté Mergify, cause non confirmée) : l'utilisateur coche les cases à la main depuis.
- Une demande de suppression des branches distantes fusionnées a été bloquée par le classificateur de permissions (portée jugée non vérifiable) ; les commandes ont été laissées à l'utilisateur.
- #681 (le flaky-check nocturne masque 28 tests de benchmark en échec permanent), #682 (le plancher de couverture backend annoncé à 90 % passe en réalité dès 89,5 %), #683 (`release.yml` devrait réutiliser les CI Backend/Frontend via `workflow_call` plutôt que dupliquer leurs jobs à la main), #684/#685 (les docs de release avaient déjà dérivé de ce qui s'est réellement passé — #685 en cours de correction).

**Décisions prises**
- Départage par nom mis de côté plutôt que shippé — *pourquoi* : trancher sur les deux moteurs (client et backend) en même temps évite de rouvrir un écart de parité pour en refermer un autre.
- Fusion manuelle de `main` (release et correctif) — *pourquoi* : `main` n'a pas de protection de branche et la file Mergify ne fusionne pas vers `main`.
- Garde « commit exact » + `push --atomic` sur `release.yml` — *pourquoi* : la garde précédente acceptait tout ancêtre de `main`, ouvrant la porte à une release dupliquée sur double dispatch.
- `polity` devient l'unique branche de travail à partir de maintenant — *pourquoi* : décision de l'utilisateur une fois `develop` et `polity` convergées juste après la première release taguée.

**Prochaines étapes**
- [ ] Traiter les issues #662–#667 (`docs/plan/vote-app/LISTING_ORDER_TIES.md`).
- [ ] #681 : sortir les 28 tests de benchmark en échec permanent du flaky-check nocturne qui les masque.
- [ ] #682 : faire que le plancher de couverture soit vraiment 90 % (precision=2).
- [ ] #683 : faire réutiliser Backend/Frontend CI par `release.yml` via `workflow_call`.
- [ ] Merger #685 (docs de release remises à jour).

**Pour aller plus loin** : `docs/plan/vote-app/LISTING_ORDER_TIES.md`, `docs/plan/polity/observations.md` OBS-026/OBS-027, `CLAUDE.md` (section Workflow).

---

## 2026-09-20 → 2026-09-26 — vLLM 0.29 puis 0.30, EAGLE-3 adopté, sonde NVFP4, et le premier run complet (30 ans / 500 citoyens)

**Contexte du jour.** Entrée reconstruite depuis les commits/PR, les résultats des scripts de bake-off et les mémoires `vllm-bump-recipe`/`vllm-experiment-queue`/`polity-full-run-prep` (pas de transcript de session associé). Plusieurs sessions se sont enchaînées sur le moteur d'inférence LLM de polity : bump de version, sonde de précision, adoption d'un décodage spéculatif, puis le premier vrai run à grande échelle et sa réplique sur trois graines.

**Ce qui a avancé**
- **vLLM 0.29.0 adopté** (#629, 09-21) : un A/B réel (12 workers, trafic réel) montre 0 gain de la spéculation n-gram en production (0.28.0+n-gram : 323 s/352 s ; 0.29.0 sans spéculation : 310 s/299 s), et un décodage 24-28 % plus lent par appel avec spéculation activée. Coût accepté : les sessions séquentielles (bake-off) ~43 % plus lentes (15,9→22,7 min), 13 réponses sur 174 changent (familles à pensée longue seulement), et la byte-identité à graine égale n'est plus garantie sans spéculation → **OBS-020** ouverte.
- **Sonde de précision NVFP4** (#630, 09-21) : Qwen3-8B en NVFP4 contre l'AWQ shippé — l'effondrement de `representative_response` et `coalition_decision` persiste identique (donc pas un artefact propre au format AWQ), mais le format 4 bits compte ailleurs (`candidacy` 351/500 contre 314 en AWQ, Holm p=0,028) ; coûte 1,8× plus cher — non adopté.
- **vLLM 0.30.0** (#631, 09-24/25).
- **OBS-021** (#642, 09-25) : fallback de `chamber_deliberation` à 5-12 % sur les seeds 1-3, cause trouvée — la validation rejette toute décision à plus de 3 shifts et rien n'est retenté ; ce n'est pas le serveur (le taux est le même sur 0.29.0 à code identique).
- **EAGLE-3** : sonde (#647, 09-25) puis adoption sur le serveur de production (#656, 09-26) — -32 % de temps mur sur 12 workers, -38 % sur deux runs réels 8 ans/p100 à un worker, byte-identique au bake-off plafonné en pensée. L'utilisateur accepte explicitement de perdre la garantie de reproductibilité contre la vitesse et le volume de logs.
- **Sidecar `llm_prompts.jsonl`** opt-in (#655, 09-26) pour pouvoir relire les prompts en détail après coup.
- **S2.4, première vague** (#648, 09-26) : Granite 4.2 8B et Gemma 4 12B testés contre l'effondrement de `coalition_decision` — reste plat sur les deux (Granite -0,033, Gemma +0,000) ; aucun des deux n'est un remplacement direct.
- **Préparation du run complet** (#654, 09-26) : plan, pré-vol, lanceur `systemd-run --user` avec veille désactivée et watchdog de plancher disque.
- **Premier run complet** (30 ans, 500 citoyens, 75 sièges, EAGLE-3, 12 workers relâchés, graine 42, 09-26) : 2 h 08, 11 mandats, 8 présidents, occupation 0,967, replay byte-identique (86 s). Résultats (#658) : OBS-021 confirmée à l'échelle (7,05 % de fallback chambre, cause = dépassement du plafond de shifts), **OBS-022** nouvelle (le positionnement de campagne tourne jusqu'à la limite de tokens sur 3 élections sur 11, seule la relance répond), **OBS-023** nouvelle (le budget de pensée de `vote_cast` sature à 86 % à population 500 contre 25 % à population 100).
- **Réplique sur les graines 1 et 2** (#670, 09-27) : confirme le structurel (fallback chambre 5,8-7,1 %, saturation `vote_cast` 72-86 %), isole ce qui est spécifique à la graine 42 (le positionnement qui tourne en boucle) et découvre deux nouveaux motifs — **OBS-024** (un lot de 3 votes ne répond que pour 1 électeur, identique sur les 3 tentatives) et **OBS-025** (un lot de 25 réactions tombe en entier si une seule dérive dépasse le plafond).
- **Ajout reconstruit a posteriori le 2026-10-12 (description de PR), 26/09.** #653 ouvre `docs/plan/polity/tech-radar.md`, un registre de veille récurrent sur ce qui pourrait compter pour l'objectif des runs de 30 ans. Il est amorcé à partir des conditions de réouverture déjà écrites dans le projet (coût de la batch-invariance, fiabilité AWQ, sondes NVFP4 et EAGLE-3, effondrements de `representative_response` et `coalition_decision`). Deux premières entrées : l'aperçu Qwen4 annoncé le 22/09, et « Jev ».

**Points bloquants**
- OBS-020 (byte-identité à graine égale) reste ouverte ; la cause suspectée (Model Runner V2) n'est pas confirmée.
- OBS-021/024/025 partagent le même défaut structurel : une seule réponse invalide fait tomber tout son lot (5 à 25 décisions). Retenter par décision plutôt que par lot n'est pas décidé — c'est un choix de l'utilisateur, pas encore fait.
- OBS-022 : pourquoi ce jeu de partis précis (graine 42 uniquement) fait tourner le modèle en boucle de pensée reste sans cause déterminée.

**Décisions prises**
- Abandon de la spéculation n-gram malgré le coût sur les sessions séquentielles — *pourquoi* : aucun gain sur le trafic réel à 12 workers, qui est le mode de production.
- Sonde NVFP4 non adoptée — *pourquoi* : 1,8× plus lente sans lever l'effondrement des deux types de décision visés.
- EAGLE-3 adopté en sacrifiant la garantie de reproductibilité — *pourquoi* : le call log détaillé suffit à l'objectif d'analyse, la vitesse compte davantage pour un run de cette taille.
- Run lancé « relâché » à 12 workers plutôt que « strict » — *pourquoi* : cohérent avec le choix ci-dessus (vitesse et volume de logs plutôt que reproductibilité).

**Prochaines étapes**
- [ ] Décider comment traiter « une réponse invalide fait tomber tout son lot » (retry par décision, ignorer les shifts nuls avant de compter le plafond, etc.) — OBS-021/024/025.
- [ ] Rouvrir OBS-020 si la reproductibilité redevient un objectif.
- [ ] Étendre un budget de pensée à `campaign_positioning` (aucun bras de bake-off n'existe encore pour ce type — seuls `vote_cast` et `chamber_deliberation` sont couverts).

**Pour aller plus loin** : `fast_api_voter/scripts/check_vllm_speculation_ab_results.md`, `check_nvfp4_precision_probe_results.md`, `check_vllm_eagle3_results.md`, `bakeoff_s24_first_wave_results.md`, `docs/plan/polity/plan-full-run.md`, `docs/plan/polity/observations.md` OBS-020 à OBS-025.

---

## 2026-09-16 → 2026-09-20 — Stage 4 sur le chemin LLM, l'explorateur de runs polity-ui, et le grand ménage anti-sur-ingénierie sur develop

**Contexte du jour.** Entrée reconstruite depuis les commits/PR et `docs/plan/polity/observations.md` (pas de transcript de session associé). Trois chantiers en parallèle : fermer les derniers calibrages Stage 4 du chemin LLM de polity, construire un explorateur visuel des runs, et un audit « sur-ingénierie » du Laboratoire qui débouche, en fin de période, sur la toute première série de correctifs d'égalités par ordre de premier-listé — le point de départ de ce qui deviendra la « Phase A » de l'audit du 24-27/09.

**Ce qui a avancé**
- **OBS-016** (09-14/15) : le disque racine se remplit, le run p500 graine 42 meurt au tick 13, toute la chaîne GPU qui suit échoue en cascade sur écriture impossible. Cause exacte non trouvée (ce qui a rempli le disque avait disparu au moment de l'inspection) ; absence confirmée d'un garde-fou sur le disque libre (seule la mémoire libre était vérifiée avant un run).
- **polity-ui** (#489 à #514, 09-15/16) : un nouvel explorateur qui rejoue un run tick par tick sur une carte (Canvas 2D, ADR-013 adoptée), biographies de citoyens, courbes macro à la demande, API dédiée `/api/v2/polity` — fusionné dans `polity` le 16/09 (#514). **OBS-017** le même jour : WebKit plante une fois en CI en pleine navigation vers `/polity`, non reproduit en isolation, imputé à la contention CPU du runner (2 workers Playwright en parallèle) plutôt qu'à la page.
- **Stage 4 sur le chemin LLM** : pilote (#536), pré-registration (#537), steps 1 à 5 (#539, #540, #542, #549, #550, #552, #569, #572). **OBS-018** : le contrat de réponse (pas le modèle) fixe la position présidentielle dans 22 des 650 réponses observées — corrigé par #545 (« le silence peut citer le motif 303 »). **OBS-019** : montrer au modèle les émotions de ses citoyens, même à poids nul, multiplie la mobilisation par 14 — c'est la présence du champ dans le prompt qui agit, pas un mécanisme de poids. D9 (mobilisation du jumeau déterministe) pré-registrée puis recalibrée (#524, #529, #530) : aucun niveau testé ne qualifie, D9 reste ouvert. S4.1 : `turnout_cost` 0,04 sélectionné et adopté (#570).
- **Audit extérieur du Laboratoire** (#515, `PLAN_SURFACE_EXTERIEURE.md`, 09-16) débouche sur un grand ménage « sur-ingénierie » (#553 à #586, 09-17/18) : code frontend mort supprimé, endpoints API sans appelant supprimés, clés i18n mortes retirées, dépendances front/back inutilisées abandonnées, doublons de helpers/labels/couleurs/popovers fusionnés en une seule source, une image de production unique construite depuis les lockfiles, scanners CI redondants supprimés.
- Scission du contexte Playground en quatre par fréquence de changement (#532, 09-16) et extension de la parité moteur client/backend à l'approbation et au jugement majoritaire (#534, #543, #546, #548).
- **Origine de la série « égalités par ordre de listing »** (#605 à #628, 09-19/20) : Kemeny-Young rendu exact et indépendant de la graine de hash de l'interpréteur (#604, #605), une table de règles unique (#608), fin du « le premier de la liste gagne » sur primaires, districts, assemblée, tallies, Monte-Carlo et théorie (#609, #615 à #618, #621 à #624), RNG global retiré des workers au profit d'un RNG par appel (#619, #625), catalogue de méthodes v1 dérivé de ce que le moteur calcule réellement plutôt que d'une liste à part (#626).
- **Ajout reconstruit a posteriori le 2026-10-12 (git log et descriptions de PR) : 15/09, CI côté `develop`.** C'est l'item 2.C de `PLAN_CI_STRUCTURAL_GAPS.md`, suite directe des lockfiles de #484.
  - #490 ajoute un check informatif : chaque version épinglée en direct (`==`) dans `requirements*.txt` doit apparaître à l'identique dans le lockfile. Ce n'est volontairement pas un `uv pip compile` suivi d'un diff, qui re-résoudrait tout contre PyPI. Brancher ce check dans `ci-local` a révélé un artefact mutmut local (`fast_api_voter/mutants/`) qui fuyait dans le contexte Docker et faisait échouer Ruff. La correction passe par `.dockerignore`, plus un `rm -rf` de secours ; la cause n'est pas entièrement élucidée.
  - #498 : Backend CI (le check requis) et son miroir `ci-local` installent désormais depuis `requirements-dev.lock.txt`.
  - #506 : l'image réellement livrée (`Dockerfile.prod`, dans ses deux étages) installe depuis `requirements.lock.txt`.
  - #497 : la PR de snapshot ci-health #493 ne pouvait jamais passer son propre check requis, qui lit le `develop` d'avant le correctif. Elle a dû être fusionnée en forçant avec `--admin`. Une exception est ajoutée pour ce cas. Un `/code-review ultra` a ensuite montré que n'importe quelle branche pouvait ainsi s'auto-attester un snapshot « sain ». L'exception est donc restreinte au préfixe `chore/ci-health-snapshot-*`.
  - Le même jour : #491 corrige le flake des lentilles et le diagnostic de #236, #501 corrige 6 dérives de documentation trouvées par un vrai passage de `doc-drift`, et #504 met à jour le snapshot ci-health.
- **Ajout reconstruit a posteriori le 2026-10-12 (git log et descriptions de PR) : ce que la puce Stage 4 ne cite pas, côté `polity`.**
  - #516 consigne les verdicts de la file GPU du 15/09 :
    - S1.2 (grammaire `vote_cast`) : 14/14 réponses valides contre 13/14 ;
    - S1.3 : budget de pensée 2048, sans perte d'accord, et `chamber_deliberation` deux fois plus rapide (9,8 s contre 19,9 s) ;
    - S1.4 : non adopté ;
    - S2.1 : la moitié « kv auto » tient, ×3,53 à 12 workers ;
    - S2.4 : non commencé.
  - #528 adopte S1.2 et S1.3 comme défauts. Le budget est limité à `vote_cast` et `chamber_deliberation`, les seuls types mesurés.
  - #517 corrige deux mémoires qui disaient encore vLLM bloqué alors qu'il est le moteur depuis septembre.
  - #535 corrige E3 (ADR-012) : un vainqueur d'élection anticipée remplacé à l'élection suivante comptait comme un mandat complet.
  - #541 et #547 construisent le prérequis d'ADR-012 : une banque de bake-off de 68 cas dont les cas de pression portent des émotions, et son lecteur conforme aux critères signés. #541 est ouverte en brouillon, en attente de la validation des critères par le propriétaire.
- **Côté `develop`, 16/09 : les premiers correctifs de l'audit extérieur (#515)**.
  - #518 borne les 23 champs de requête de simulation sans validation : `num_voters: 50000000` allouait jusqu'à l'OOM.
  - #519 corrige Copeland marqué « participation : oui », contraire au théorème de Moulin, avec un test qui encode le théorème. Le Laboratoire n'avait pas régénéré sa référence visuelle après ce changement, d'où un check rouge sur toutes les PR jusqu'à #523.
  - #520 donne au test e2e de la Méthode un vrai oracle de résultat, là où il ne vérifiait qu'un vainqueur non vide.
  - #521 dit clairement qu'aucune instance de Vote Lab n'est hébergée ; #522 précise la branche de la mesure radon.
  - #525 restaure le théorème d'Arrow en fiche du Laboratoire, supprimé par erreur avec l'arbre `Simulation/`.
  - #526 regroupe les petits restes du §2.L : namespace i18n `auth` mort, et les chunks pseudo-locale sortis du budget de taille (810 → 739 kB brotli).
  - #527 révèle que `react-hooks/exhaustive-deps` n'avait jamais été activé. Il passe en avertissement, et `/code-review ultra` trouve deux vraies dépendances périmées dans `PlaygroundController`, corrigées par #531.
  - #538 implémente le vrai départage de Balinski-Laraki pour le jugement majoritaire, à la suite de l'écart de parité trouvé par #534 (6 scénarios sur 58).
  - #544 diffère l'écriture `localStorage` pour qu'elle ne se fasse plus à chaque image de glissement, et mémoïse `LeaderCanvas` et `ParliamentCanvas`.
  - #551 retire une branche `manualChunks` morte.
- **Les PR 21 à 23 du grand ménage et la famille du « repli silencieux sur plurality » (17-18/09)**, suite directe de #553-#586.
  - #587 remplace par des réexportations 38 wrappers qui ne faisaient rien (286 → 72 lignes).
  - #588 supprime le réexport en double des 128 modèles.
  - #589 réunit en une seule fonction trois copies de `bayesian_regret`.
  - **Puis de vrais bugs** :
    - #591 : `/collective-will` inventait le vainqueur de quatre méthodes sur dix (médiane changée dans 70 scénarios sur 80) ;
    - #592 : trois endpoints répondaient le vainqueur de plurality pour un nom de règle inconnu ;
    - #593 : un seul dispatcher utilités → vainqueur, et 422 sur un nom de méthode invalide.
  - Frontend : #594 retire 36 `useCallback` qui ne mémoïsaient rien. #596 crée un seul hook de debounce ; dix panneaux continuaient de tirer après démontage.
  - #597 : `/simulate` n'avait jamais été mis en cache, car le décorateur était posé sur une fonction que rien n'importait.
  - #602 désactive par défaut la vulnérabilité stratégique, qui coûtait 99,4 % du temps de `/simulate` (97,9 s au maximum du schéma).
  - #603 : `/campaign-sensitivity` et `/combined-effects` répondaient avec 14 règles au lieu de 34.
  - #601 réunit 15 copies de `candColor`.
  - #598 débloque Dependabot #574 et ignore deux épinglages imposés par un paquet parent.
  - Dependabot : #590, #599. Snapshots ci-health : #533, #595.

**Points bloquants**
- OBS-016 : cause exacte de ce qui a saturé le disque non trouvée ; aucun garde-fou disque n'a encore été ajouté aux runs longs ou aux chaînes GPU.
- OBS-017 : un seul cas observé, pas reproduit isolément — en observation, sans correctif.
- D9 reste ouvert : aucune recalibration de la mobilisation du jumeau déterministe testée jusqu'ici ne qualifie.
- *(15/09)* Une dizaine d'autres workflows et 3 Dockerfiles résolvent encore `requirements*.txt` en direct. C'est explicitement hors du périmètre de #498 et #506, et suivi dans `PLAN_CI_STRUCTURAL_GAPS.md`.
- *(16/09)* #541 attend la signature du propriétaire sur ses critères d'acceptation avant que la session de bake-off ne tourne.

**Décisions prises**
- « Émotions à poids nul » documenté comme non neutre plutôt que corrigé dans l'immédiat — *pourquoi* : établir d'abord ce que révèle OBS-019 avant de décider quel taux de mobilisation est la cible, question renvoyée à une nouvelle pré-registration plutôt que tranchée dans l'urgence.
- Sur-ingénierie traitée par suppression plutôt que dépréciation — *pourquoi* : code sans appelant réel trouvé par l'audit, moins de surface à maintenir en le retirant plutôt qu'en le marquant obsolète.

**Prochaines étapes**
- [ ] Poursuivre la série de correctifs d'égalités par ordre de listing entamée par #605-628 (suite directe : Phase A du 24-27/09).
- [ ] Ajouter un garde-fou de disque libre aux runs longs et aux chaînes GPU (OBS-016).
- [ ] Rouvrir D9 avec un nouveau niveau de recalibration si un besoin se présente.

**Pour aller plus loin** : `docs/plan/polity/observations.md` OBS-016 à OBS-019, `docs/plan/PLAN_SURFACE_EXTERIEURE.md`, `docs/adr/ADR-013-*.md`.

---
