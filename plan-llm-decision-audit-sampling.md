# Point ouvert #3 — fréquence et taille de l'audit d'échantillon des décisions LLM

Document de cadrage, même discipline que
`plan-rupture-candidacy-threshold.md`. Pas de LLM impliqué dans le
mécanisme lui-même (c'est un outil de lecture de journal), donc pas de
palier de fiabilité live.

## 1. Ce que dit le texte de conception (§11, point 3)

> **Audit d'échantillon des décisions LLM** : vérifier périodiquement que
> le raisonnement reste dans des bornes plausibles.
>
> **🔴 Ouvert** : fréquence et taille de l'audit d'échantillon.

§11 (« Stratégie de validation ») est marqué 🔴, le niveau d'urgence le
plus élevé utilisé dans ce document — contrairement à la plupart des
autres sections (🟢/🟡). Les trois autres points de §11 (analyse de
sensibilité, calibration sur cas réels, comparaison baseline vs LLM) sont
déjà substantiellement couverts par la pratique déjà établie de ce projet
(sweeps de calibration `w_pet`/`w_mob`/`base_threshold`, chaque run
d'acceptance compare un bras `deterministic` et un bras `llm`). Seul le
point 3 (audit du raisonnement) n'a strictement aucun code.

## 2. Ce qui est réellement disponible à auditer — correction d'une
   prémisse implicite

En cadrant ce point, vérification directe du code : **aucun raisonnement
brut n'est persisté nulle part pour un appel réussi.** Seul le JSON
structuré final (motif codé + champs de décision) atteint le journal.

- `llm.rationale_mode` (config) accepte `codes | free_text | hybrid`,
  mais `llm_behavior_engine.py:451-452` lève `NotImplementedError` pour
  tout sauf `codes` — la piste « texte libre » que le Points ouverts #7
  du document de conception annonçait comme déjà tranchée
  (« codes partout + texte libre borné aux pivots ») n'a jamais été
  implémentée. Corrigé dans `polity-simulation-design-v2.md` en même
  temps que ce cadrage.
- Le contenu `<think>` du modèle (quand `think=True`) n'est capturé nulle
  part de façon durable — seuls les échecs/replays sont journalisés via
  `logging` standard (niveau WARNING, `llm_behavior_engine.py:579`), pas
  dans un fichier structuré, et jamais pour un appel réussi.

**Conséquence directe pour le scope** : un audit du *raisonnement* au
sens strict (le texte que le modèle a produit pour arriver à sa décision)
n'est pas possible aujourd'hui sans un chantier de capture séparé,
potentiellement coûteux (logger le raisonnement brut de chaque appel
`think=True` change le volume de données par run de façon significative).
Ce que ce lot peut réellement auditer : **le motif codé et les champs de
décision**, mis en regard de l'état du citoyen qui a pris la décision —
un audit de *cohérence*, pas de *raisonnement*.

## 3. Ce qui existe déjà et doit être réutilisé, pas reconstruit

- `codebook.motif_labels() -> dict[int, str]` (`codebook.py:425`) :
  traduction code → nom humain pour TOUS les motifs de tous les types de
  décision, déjà construite pour l'injection dans les prompts. Directement
  réutilisable pour rendre un motif codé lisible dans un export d'audit.
- `indexer.read_journal(path: Path) -> Iterator[dict[str, Any]]`
  (`indexer.py:173`) : lecteur de journal déjà existant, déjà utilisé par
  `index_events`/`index_run` et par les scripts d'acceptance. Pas de
  nouveau lecteur à écrire.
- Des checks de cohérence *automatiques* existent déjà, mais localisés et
  au moment de la validation du schéma, pas comme balayage périodique
  post-run : `ACCEPTABLE_MATCH` (codebook.py, vote_cast) et
  `ResponseDecision._check_stance_coherence` (llm_schemas.py, C-13 au
  radon — déjà le plus complexe de son fichier). Ce lot ne duplique pas
  ces checks ; il donne à un humain de quoi juger ce qu'ils ne couvrent
  pas (la plausibilité sémantique, pas la validité structurelle).

## 4. Ce que « bornes plausibles » signifie ici — et ce que ce lot ne fait pas

**Décision explicite : pas de vérification automatisée du type « le LLM
juge le LLM ».** Rien dans ce projet ne fait ça ailleurs — chaque check
existant est mécanique (comparaison de valeurs déjà calculées,
`ACCEPTABLE_MATCH`, `_check_stance_coherence`). Construire un juge
automatisé introduirait exactement le type de critère théorique
prescriptif que §3.3 refuse explicitement (« le LLM ne reçoit aucun
critère théorique prescriptif... observer quelles stratégies émergent
spontanément ») — un juge automatisé serait lui-même un critère
prescriptif imposé après coup.

**Ce lot construit un outil d'échantillonnage et d'export, pas un
vérificateur.** Le jugement de plausibilité reste humain ; l'outil rend
cette lecture humaine bon marché et reproductible (même échantillon à
chaque relecture d'un même run) plutôt que de l'automatiser.

## 5. Taille de l'échantillon

Pas de calcul de puissance statistique — ce n'est pas un test
d'hypothèse, c'est une relecture qualitative de type spot-check. Ancrage
sur la pratique déjà établie de ce projet : chaque spike de fiabilité
live (Lot 3 de chaque palier LLM) a utilisé un ordre de grandeur de 25-30
essais comme « assez pour révéler un mode de défaillance courant, pas
assez pour être coûteux » (v7 Lot 3 : 30 essais / 0 échec ; v6b dt=11 :
même ordre de grandeur).

**Taille retenue : 30 décisions par `decision_type` présent dans le run
audité** (ou la totalité si moins de 30 existent pour ce type — par
exemple `coalition_decision`, rare par construction). Tirage stratifié
par `decision_type`, pas un échantillon global uniforme : sinon
`vote_cast` (le type de loin le plus fréquent) écraserait les types plus
rares dans l'échantillon, qui sont pourtant ceux où une dérive serait la
moins visible ailleurs (peu d'occurrences → peu de chances qu'une anomalie
saute aux yeux dans les métriques agrégées).

**Tirage reproductible** : seedé explicitement (paramètre `--seed`).
**Simplifié en implémentant** : défaut fixe (`0`), pas dérivé du run
audité comme envisagé ci-dessus — dériver le seed du run n'apporte rien
de plus que le défaut fixe pour l'objectif visé (deux relectures du même
journal avec le même `--seed` donnent déjà le même échantillon, et deux
journaux différents produisent de toute façon des échantillons différents
puisque leurs pools d'événements diffèrent), au prix d'une complexité
inutile (hacher un run_id ou un chemin pour en tirer un entier). Plus
simple à retenir et à reproduire pour quiconque relit ce script plus
tard.

## 6. Fréquence

« Périodiquement » est une cadence humaine/de projet, pas quelque chose
que du code peut imposer — rien ne force qui que ce soit à relire un
export généré. Plutôt que d'inventer une cadence calendaire arbitraire
(hebdomadaire ? mensuelle ?) sans justification, **rattacher l'audit au
rituel déjà existant de ce projet** : chaque nouveau type de décision LLM
passe déjà par un spike de fiabilité live avant tout run d'acceptance
(Lot 3 de chaque palier). Ce lot ajoute l'échantillon d'audit comme
**une sortie supplémentaire de ce même rituel**, pas une cadence
séparée à retenir et à honorer indépendamment — le spike produit déjà un
run réel dont l'échantillon peut être tiré immédiatement, à coût marginal
nul par rapport à écrire un script séparé qu'il faudrait se souvenir de
relancer.

## 7. Surface

Nouveau script `scripts/sample_llm_decisions_for_audit.py` :
- Entrée : chemin d'un journal de run existant, `--seed` optionnel.
- Lit via `indexer.read_journal`, groupe par **`event_type` filtré sur un
  `motif` non-vide** — pas par `event_type` seul. Affinement fait en
  implémentant : `pressure_action` (et potentiellement d'autres types) est
  écrit à la fois par le chemin déterministe (`motif=None`, initialisé
  ainsi dans `run_polity_simulation.py`) et par le chemin LLM
  (`motif=str(decision.motif)`), selon `config.llm.enabled` — filtrer sur
  `event_type` seul aurait mélangé des décisions non-LLM dans un
  échantillon censé auditer spécifiquement le LLM, sur un run mixte ou à
  LLM désactivé.
- Tire un échantillon stratifié de taille `min(30, n_disponible)` par
  type avec `np.random.default_rng(seed)`.
- Rend chaque décision échantillonnée en markdown lisible : `tick`,
  `citizen_id`, `event_type`, motif traduit via `codebook.motif_labels()`
  (repli `"UNKNOWN"` si le code n'est pas reconnu — délibéré, cet outil
  est une lecture au mieux-effort pour revue humaine, pas un validateur ;
  `check_codebook_version` gate déjà un run réel au démarrage, et chaque
  évènement porte son propre `codebook_version` pour qu'un relecteur
  vérifie lui-même), et les champs de décision bruts (`payload`).
- Pas de nouveau champ de config, pas de nouveau paramètre dans
  `PolityConfig` — cet outil lit un journal déjà produit, il ne change
  rien au comportement d'un run.

## 8. Vérification

**Corrigé en implémentant** : pas de test unitaire pytest formel — vérifié
que ce projet ne teste aucun de ses scripts d'acceptance/calibration
existants via pytest (`pyproject.toml`'s `testpaths = ["api/tests"]`
n'inclut même pas `scripts/`, et aucun `run_v*_acceptance.py`/
`*_calibration*.py` n'a de fichier de test associé). Écrire un test
pytest orphelin ici aurait été inconsistant avec la pratique réelle du
projet, pas plus rigoureux. Vérifié à la place par exécution directe sur
un journal fixture construit à la main (50 `vote_cast` avec motif, 5
`coalition_decision` avec motif, 10 `pressure_action` sans motif) :
- Échantillon exact : 30/50 pour `vote_cast` (plafond respecté), 5/5 pour
  `coalition_decision` (tous pris, sous le plafond), `pressure_action`
  totalement absent de l'échantillon (confirmé : le filtre motif exclut
  bien les décisions non-LLM).
- Même `--seed` sur le même journal → sortie markdown strictement
  identique (`diff` vide) ; `--seed` différent → sortie différente.
- Traduction motif → nom humain confirmée correcte (`501` →
  `IDEOLOGICAL_PROXIMITY`, une vraie valeur de `CoalitionMotif`).
- Pas de run d'acceptance nécessaire : outil de lecture pure, aucun
  comportement de simulation n'est modifié.
