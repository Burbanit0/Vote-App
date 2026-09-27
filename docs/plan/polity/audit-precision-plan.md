# Audit de précision — Plan de conception Polity

> **Trace historique.** Les bloquants listés ici ont été tranchés dans
> `polity-simulation-design-v2.md`, dont le tableau « État des bloquants de
> l'audit de précision » fait désormais autorité — s'y référer en cas de
> divergence avec les recommandations ci-dessous.
>
> Passe de relecture du 30/07/2026 sur `polity-simulation-design.md`.
> Objectif : identifier tout ce qui est trop imprécis pour être codé tel
> quel. Classé par criticité — un point « bloquant v0 » empêche
> littéralement d'écrire la première ligne de code.

---

## A. Bloquants v0 — à trancher avant d'ouvrir l'éditeur

### A1. L'unité de temps n'est jamais définie 🔴

Le document mélange les échelles sans jamais poser la granularité du tick :
- §6 raisonne en **années** (`t = 0, 4, 8...`)
- §16.0 évoque « 360 pas de temps » (⇒ **mois** sur 30 ans)
- §14.6 parle d'échantillonnage « annuel »

**À trancher** : un tick = 1 mois (360 ticks) ou 1 trimestre (120 ticks) ?
Impact direct sur le coût LLM (×3), le volume du journal, et la finesse
de `L(t)`. **Recommandation** : trimestre pour la v0-v2 (120 ticks,
suffisant pour un mandat de 4 ans = 16 ticks), quitte à raffiner ensuite.

### A2. Rien ne dit d'où viennent les partis 🔴

Aucune section ne décrit l'**état initial du système partisan** :
- Combien de partis à `t=0` ?
- Leurs plateformes initiales : tirées au hasard, ou dérivées de clusters
  d'opinion de la population ?
- Un parti peut-il **naître** en cours de simulation (30 ans, c'est long) ?
- Un parti peut-il **mourir** (score nul plusieurs scrutins de suite) ?

C'est un trou majeur : le §10 mesure le « nombre effectif de partis »
comme métrique centrale, mais le modèle ne dit pas comment ce nombre peut
varier. **Recommandation v0** : N partis fixes (ex. 5), plateformes
initialisées par k-means sur les positions citoyennes, ni naissance ni
mort — et ouvrir la dynamique partisane comme palier ultérieur explicite.

### A3. `role` ne distingue pas président et député 🔴

§2.1 pose `role ∈ {électeur, candidat, élu}`, mais un « élu » peut être
président *ou* député — deux mandats aux règles, durées et mécaniques de
rappel différentes. Le champ tel quel est inutilisable.

**Recommandation** : `role ∈ {électeur, candidat, élu}` +
`office ∈ {aucun, président, député}` + `term_end_tick`.

### A4. La taille et l'attribution des sièges ne sont pas spécifiées 🔴

§6 mentionne une élection parlementaire, mais jamais : combien de sièges ?
Quelle méthode d'attribution proportionnelle (D'Hondt, Sainte-Laguë,
plus forts restes) ? Y a-t-il un seuil d'accès (5% ?) ?

Ces choix ont un effet **direct et documenté** sur le nombre effectif de
partis — la métrique centrale du §10. Les laisser implicites, c'est
laisser un artefact d'implémentation contaminer le résultat scientifique.

### A5. Les « décisions simplifiées » de la v0/v1 ne sont définies nulle part 🔴

§13 fait reposer les deux premiers paliers sur des « décisions simplifiées
et déterministes » — c'est *littéralement la première chose à coder*, et
le document n'en donne aucune. Il faut spécifier, pour la v0 :
- règle de vote (ex. vote pour le candidat le plus proche en distance
  pondérée par `issue_priorities`, blanc si distance > seuil) ;
- règle de candidature (ex. seuil sur `ambition_score`) ;
- règle de coalition (ex. plus proche voisin idéologique jusqu'à majorité).

Ces règles ont un second rôle, plus important : elles deviennent le
**baseline de comparaison** contre lequel mesurer ce que le LLM apporte
réellement en v2. Sans elles, impossible de dire si le LLM change quoi que
ce soit.

### A6. La formule de `L(t)` a disparu du document 🔴

§7.1 renvoie à « la version précédente du modèle » pour l'EWMA, et §7.2
mentionne `L₀` — mais ni la formule ni `L₀` ne figurent dans le document
actuel. Référence pendante.

**À réintégrer explicitement** :
```
L(t) = decay · L(t-1) + support(t) − écart(t)
L₀   = f(force du mandat initial)
```
avec la définition opérationnelle de `support(t)`, `écart(t)`, `decay`, et
la valeur du plancher de rappel (déjà listé comme point ouvert n°2).

---

## B. Bloquants v2 (bascule LLM) — à trancher avant le module LLM

### B1. Le schéma de sortie du LLM n'est jamais défini 🔴

§3.2 dit que « le LLM produit des préférences », §3.5 qu'il « retourne un
tableau structuré » — mais aucun schéma JSON n'existe dans le document.
Or c'est le contrat d'interface central de tout le système.

Il faut un schéma par type de décision, par exemple pour un vote :
```json
{"citizen_id": 412, "ballot": [3, 1, 4], "blank": false, "motif": "NO_MATCHING_PRIORITY"}
```
Question corollaire non traitée : avec 20 candidats, demande-t-on un
classement **complet** (coûteux en tokens, et peu réaliste — un électeur
réel n'ordonne pas 20 noms) ou **tronqué au top-k** ? Le choix doit être
cohérent avec la méthode d'agrégation active (§3.2).

### B2. Le déterminisme du LLM n'est pas garanti 🔴

§4.2 fonde la reproductibilité sur un cache par hash, mais ne dit rien de
deux conditions nécessaires :
- **température = 0** (sinon deux appels identiques divergent avant même
  d'atteindre le cache) ;
- **version du modèle épinglée** (un `latest` qui change casse
  silencieusement la reproductibilité entre deux sessions de travail).

À ajouter comme contraintes dures dans `llm_client.py`.

### B3. La composition des cohortes de batch n'est pas spécifiée 🟡

§3.5 dit de regrouper « par `archetype_id` et situation similaire », sans
préciser la taille de batch ni le critère exact de similarité. Un batch de
5 citoyens et un batch de 200 n'ont ni le même coût, ni la même qualité de
sortie (risque de dégradation sur les longues listes).

### B4. Aucun budget de coût n'est estimé 🟡

Rien dans le document ne chiffre le nombre d'appels LLM d'un run complet.
Ordre de grandeur à établir avant de lancer la v2 : `ticks × cohortes ×
types de décision`. C'est le paramètre qui décide si l'auto-hébergement
(§15) est optionnel ou obligatoire.

---

## C. Incohérences internes à résoudre

### C1. Contradiction §2.3 ↔ §2.4 🔴

§2.3 borne le nombre de candidats par un **seuil de signatures** pour les
indépendants. §2.4 précise que le chemin de rupture « ne dépend pas du
seuil de signatures classique ».

⇒ Un candidat protestataire contourne donc entièrement le filtre d'accès
au bulletin, ce qui **annule le mécanisme de bornage** du §2.3 : rien ne
limite plus le nombre de candidats de rupture. À réconcilier — soit le
chemin rare passe aussi par un seuil (plus bas), soit sa probabilité est
assez faible pour que ça n'ait pas d'importance, mais il faut le dire.

### C2. §14.6 et §16.0 se contredisent (partiellement résolu) 🟡

§16.0 révise bien §14.6, mais §14.6 n'a pas été réécrit — un lecteur qui
lit le document dans l'ordre reçoit deux consignes opposées avant
d'arriver à la révision. À harmoniser par une note dans §14.6.

### C3. Le §1 (architecture) ne liste pas les modules de données 🟡

L'arborescence du §1 date d'avant les §14/§15/§16. Il manque au minimum :
`journal.py` (écriture append-only), `snapshots.py`, `indexer.py`
(compaction post-run), `viz_export.py`.

---

## D. Imprécisions non bloquantes (à préciser avant le palier concerné)

| # | Section | Point imprécis |
|---|---|---|
| D1 | §2.2 | Pas d'`id` citoyen dans le schéma d'état ; pas d'âge, pas de mortalité/natalité — la population est-elle figée sur 30 ans ? |
| D2 | §5 | Type de graphe non tranché (Watts-Strogatz ? degré moyen ? paramètre de rewiring ?) |
| D3 | §6 | Durée du mandat parlementaire vs présidentiel ; limitation du nombre de mandats ? |
| D4 | §8 | Taux du processus de Poisson et paramètres de l'AR(1) non chiffrés |
| D5 | §9 | Schéma d'un persona non défini (quels champs ? quelle longueur ?) |
| D6 | §10 | « Polarisation affective » listée comme métrique mais aucune formule donnée |
| D7 | §11 | Fréquence/taille de l'audit (déjà point ouvert n°3) |
| D8 | §16.3 | Pas d'`event_id` ni de garantie d'ordre dans le journal |
| D9 | global | Aucun schéma de fichier de configuration, alors que tout est « paramétrable » — il faut une source unique de vérité (`polity_config.yaml`) |

---

## Synthèse — ordre de résolution recommandé

**Avant d'écrire du code (bloquants v0)** : A1 (tick), A2 (partis), A3
(office), A4 (sièges), A5 (règles simplifiées), A6 (formule `L`), C1
(contradiction candidature), D9 (fichier de config).

**Avant le module LLM (v2)** : B1 (schéma JSON), B2 (déterminisme), B3
(cohortes), B4 (budget).

**Au fil de l'eau** : le reste du bloc D, à traiter au moment d'aborder le
palier concerné — pas besoin de tout trancher maintenant.
