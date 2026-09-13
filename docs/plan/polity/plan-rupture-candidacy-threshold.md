# Point ouvert #1 — seuil de la candidature de rupture : quelle fonction de l'écart idéologique ?

Document de cadrage, même discipline que `plan-coalition-negotiation-v7.md` :
document avant implémentation, un seul lot (pas de LLM ici, donc pas de
palier de fiabilité live à part).

## 1. Comportement actuel (cité, `simple_rules.py`)

```python
def attempt_rupture_candidacy(
    citizen: Citizen,
    population: list[Citizen],
    config: CandidacyConfig,
    rng: np.random.Generator,
) -> bool:
    """... gated only by a flat per-tick draw (rupture_base_probability)
    and a reduced signature bar (rupture_signature_ratio) — never by
    ambition_score or by decide_candidacy. ...

    The "quelle fonction de l'écart idéologique" question left open in the
    design doc (§2.4, Points ouverts #1) is deliberately NOT answered here:
    eligibility does not depend on ideological distance to any incumbent
    or party — only on the flat probability already pinned in config."""
    if not config.rupture_path_enabled:
        return False
    if rng.random() >= config.rupture_base_probability:
        return False
    return ballot_access_signature_ratio(citizen, population) >= config.rupture_signature_ratio
```

Le docstring nomme déjà précisément ce point ouvert — l'implémentation v1
l'a délibérément laissé de côté plutôt que de deviner une réponse.

Config actuelle (`polity_config.yaml`, section `candidacy`) :

```yaml
rupture_path_enabled: false         # [v1] chemin rare (§2.4)
rupture_base_probability: 0.001     # [v1] proba par tick et par citoyen
rupture_signature_ratio: 0.005      # [v1] RÉSOLUTION C1 : seuil réduit
```

**`rupture_path_enabled` reste `false` par défaut** — le mécanisme n'est
pas actif dans une run livrée standard. Il a été activé ponctuellement
pour la mesure ADR-003 du 2026-08-29 (40 graines, à n=100 et n=1000), qui
a confirmé le seuil de signatures franchissable mais n'a rien mesuré sur
la fonction d'écart elle-même.

## 2. Ce que dit le texte de conception (§2.4), et ce qu'il ne dit pas

> Chemin rare — candidature de rupture : un citoyen en désaccord marqué
> peut se présenter indépendamment du soutien perçu, avec une probabilité
> volontairement très faible — parce que la majorité des citoyens en
> désaccord n'agit pas.

« En désaccord marqué » est la justification narrative du chemin — mais
rien dans le mécanisme actuel ne mesure de désaccord. `rupture_base_probability`
est un tirage uniforme, identique pour un citoyen parfaitement aligné
avec son parti et pour un citoyen totalement désaffilié. Le nom du
paramètre (« rupture ») et son taux volontairement bas ne suffisent pas à
implémenter la sélection qualitative que le texte décrit.

## 3. Périmètre de ce lot

**Dans le scope** : donner une réponse concrète et minimale à « quelle
fonction de l'écart idéologique » — assez pour que l'éligibilité au
chemin de rupture dépende réellement du désaccord du citoyen, pas
seulement de son nom.

**Hors scope, explicitement** :
- Activer `rupture_path_enabled` par défaut. C'est une décision séparée
  (le régime livré change), pas une conséquence automatique d'avoir une
  fonction d'écart correcte. Ce lot répond à #1 ; il ne rouvre pas la
  question de l'activation.
- Toucher `rupture_signature_ratio` ou la logique ADR-003
  (`ballot_access_signature_ratio`) — déjà mesurée et corrigée le
  2026-08-29, hors sujet ici.
- Le chemin dominant (`decide_candidacy`, `ambition_score`) — inchangé.

## 4. Point de référence pour « l'écart »

Écart par rapport à quoi ? Le texte ne le dit pas. Trois candidats
possibles existent dans le modèle :

1. **Distance au parti affilié** (`citizen.party_affiliation`, déjà
   calculée par `assign_party_affiliation` via `weighted_distance`) :
   à quel point ce citoyen est mal représenté même par le parti dont il
   est le plus proche.
2. Distance à l'élu/titulaire en poste — pertinent seulement après une
   élection, absent avant la première ; introduit une dépendance
   temporelle que le chemin dominant n'a pas.
3. Distance au centre de gravité de la population (moyenne/médiane des
   positions) — mesure une extrémité générale, pas un rapport au système
   partisan.

**Choix retenu : option 1**, distance au parti affilié, réutilisant
`weighted_distance` — le même primitif déjà utilisé partout ailleurs
dans ce module pour la distance en espace des enjeux (acceptabilité de
vote, `sympathizer_ratio`, `ballot_access_signature_ratio`,
`assign_party_affiliation` lui-même). Justification : « en désaccord
marqué » se lit naturellement comme *mal représenté par le système
partisan existant*, pas comme *extrême dans l'absolu* (option 3) ni
comme *dépendant du résultat d'une élection passée* (option 2, qui
casserait la symétrie temporelle du chemin — actuellement identique à
chaque tick).

**Correction en implémentant (2026-08-29)** : le cas `party_affiliation is
None` envisagé ci-dessous n'existe pas en pratique et a été retiré de
l'implémentation. `party_affiliation` est assigné une seule fois, à
l'initialisation de la population (`run_polity_simulation.py`), via
`assign_party_affiliation` — qui utilise `math.dist` (pas
`weighted_distance`) et retourne **toujours** un `party_id` concret,
jamais `None` (c'est `choose_party`, une fonction différente pour le
choix de vote législatif, qui peut retourner `None` au-delà de la
tolérance). Traiter un cas `None` dans `attempt_rupture_candidacy` aurait
été du code mort pour un état inatteignable. La fonction résout donc
`party_affiliation` directement sans branche de secours.

## 5. Forme de la fonction

Aucune littérature citée dans `THEORY.md` ne répond directement à cette
question (Superti 2020, seule citation adjacente, porte sur le vote
blanc/nul comme signal, pas sur l'éligibilité à candidater) — même
situation que `coalition_max_negotiation_rounds` : pas de dérivation
théorique disponible, donc choix pragmatique explicite plutôt qu'une
fausse citation.

**Ce qui est modulé : la probabilité de tirage, pas le seuil de
signatures.** `rupture_signature_ratio` reste la barrière d'accès
institutionnelle générique (ADR-003, déjà calibrée) ; la faire dépendre
du désaccord idéologique mélangerait deux mécanismes distincts du §2.3
(accès au bulletin) et du §2.4 (probabilité de tenter). La fonction
d'écart module uniquement `rupture_base_probability`.

**Forme retenue : un multiplicateur affine borné**, appliqué à la
probabilité de base :

```
p(citizen) = rupture_base_probability × (1 + k × weighted_distance(citizen, affiliated_platform))
```

`weighted_distance` est déjà borné dans `[0, 1]` par construction
(positions dans `[0, 1]` par dimension, priorités sommant à 1 — voir son
propre docstring, `simple_rules.py`) : pas de normalisation séparée à
écrire, contrairement à ce qui était anticipé ci-dessous en §6. `k` est un
paramètre de config (`rupture_distance_multiplier`, proposé à `2.0` : un
citoyen en désaccord maximal a 3× la probabilité de base, un citoyen
parfaitement aligné garde exactement le taux actuel — le comportement à
distance nulle reste byte-identique à v1, changement strictement
additif).

Alternative considérée et écartée : une marche en escalier (deux paliers,
comme `rupture_signature_ratio` l'est vis-à-vis du seuil indépendant
classique). Écartée parce qu'elle introduirait un troisième paramètre
arbitraire (le point de coupure) sans que rien ne le justifie mieux
qu'un multiplicateur continu — un affine borné a un seul degré de
liberté pragmatique (`k`), pas deux.

## 6. Surface de config et de signature

- `CandidacyConfig` gagne `rupture_distance_multiplier: float` (défaut
  `2.0`).
- `attempt_rupture_candidacy` gagne un paramètre `parties: list[Party]`
  (nécessaire pour résoudre `citizen.party_affiliation` → `Party.platform`)
  — signature actuelle `(citizen, population, config, rng)` devient
  `(citizen, population, parties, config, rng)`. Seul appelant à mettre à
  jour : le site qui invoque `attempt_rupture_candidacy` dans
  `run_polity_simulation.py` (a déjà `parties` en portée à ce point du
  tick).
- ~~`max_possible_distance`~~ : inutile, voir correction §5 —
  `weighted_distance` est déjà borné dans `[0, 1]`.

## 7. Vérification

Pas de LLM impliqué — fonction déterministe pure, donc pas de palier de
fiabilité live comme v7 Lot 3. Suffit :
- Tests unitaires (`test_polity_simple_rules.py`) : probabilité à distance
  0 identique qu'avec le multiplicateur à `0.0` ou `2.0` (non-régression
  v1, byte-identique) ; probabilité à distance maximale (1.0) démontrée
  strictement supérieure à distance 0, sur le même tirage RNG, avec des
  valeurs choisies pour croiser exactement le seuil de coin-flip
  (`np.random.default_rng(0).random() == 0.6369616873214543`, vérifié
  directement plutôt que deviné).
- Un test de replay (comme les autres `_replay_cases`) confirmant que le
  RNG est toujours consommé dans le même ordre qu'avant (le tirage
  `rng.random()` doit rester à la même place dans la séquence — seule la
  probabilité *comparée* au tirage change, pas le fait de tirer).
- Pas de run d'acceptance nécessaire pour ce lot seul : le mécanisme
  reste `rupture_path_enabled: false` par défaut, donc aucun run livré
  n'est affecté tant que ce paramètre n'est pas activé (décision séparée,
  §3 ci-dessus).
