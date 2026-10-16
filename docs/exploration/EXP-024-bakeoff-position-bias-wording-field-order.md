# EXP-024 — Bake-off : le modèle suit-il la position ou le candidat, et que changent le vocabulaire et l'ordre des champs

- **Date** : 2026-10-16 · **Statut** : suspendu (l'ordre des candidats et l'ordre des champs sont des décisions
  du propriétaire ; OBS-013 et OBS-049) · **Coût réel** : environ trois heures en une séance, sur le GPU
  partagé, une requête à la fois (quatre sessions de 81 requêtes, une de 138) · **Coût en tokens** : non
  mesuré
- **Verdict en une phrase** : à partir de cinq candidats dans une liste, le modèle penche vers le dernier
  listé (54 choix sur 198 pour 34 attendus au hasard) ; retirer le mot « simulation » des prompts ne change
  rien ; et le test de l'ordre des champs a révélé que le client trie les clés du schéma, de sorte que l'ordre
  déclaré n'est jamais celui que le modèle écrit.

## Hypothèse de départ

Les deux radars du 2026-10-03 et du 2026-10-10 proposaient trois contrôles bon marché :

1. **L'ordre des candidats** (OBS-013) : les propositions de parti penchent vers le dernier candidat listé,
   toujours le plus récent citoyen puisque `sorted_candidates` trie par id. Cinq populations ne suffisaient pas
   à trancher entre « suit la position » et « suit le candidat ».
2. **Le vocabulaire** (PIMMUR, « Unawareness ») : les 174 prompts système commencent par « Tu es un moteur de
   simulation ». Le mot change-t-il les décisions ?
3. **L'ordre des champs** (Structure Tax) : « raisonnement d'abord » égalerait le texte libre, « réponse
   d'abord » perdrait en exactitude. Le code `motif` est la seule raison que portent les décisions par lot
   (`rationale_mode` hors `codes` n'est pas construit).

## Protocole

Qwen3-8B-AWQ sur le vLLM 0.31.0 partagé (`vllm-polity`), une requête à la fois, serveur au repos avant et
après chaque session. Les sessions sont dans `scripts/bakeoff_runs/` (hors git).

- **Position ou candidat** : un bank à part de 60 populations (graines 101 à 160), chacune rendue deux fois
  (ordre de production, puis liste inversée), 254 unités parti. `NOMINATION_SEEDS` est devenue une constante
  pour le générer ; le bank gelé de 174 cas est inchangé. Lecture : `scripts/check_nomination_position_bias.py`
  (probabilité exacte contre un choix uniforme, par simulation, et intervalle de Wilson).
- **Vocabulaire** : le bras `neutral_wording` remplace « Tu es un moteur de simulation » par « Tu es un moteur
  de decision » et « dans cette simulation » par « ici », dans le prompt système, et rien d'autre.
- **Ordre des champs** : les bras `reason_first` et `answer_first` envoient la clé `motif` sous le nom `0motif`
  (elle trie la première) ou `zmotif` (la dernière), puis la remettent à `motif` avant le décodage. Le premier
  essai, qui réordonnait seulement les propriétés du schéma, n'a rien changé : 81 sorties identiques au
  contrôle, à l'octet.
- **Familles lues** : `vote_first_choice`, `candidacy_p500`, `pressure_act`, `nomination_permutation`, avec
  leurs vérités ; contrôle et bras sur les mêmes cas, comparés par paires (McNemar, Holm).

## Ce que ça a trouvé

**1. La position pèse, et d'autant plus que la liste est longue** (254 unités ; OBS-013, mise à jour) :

| candidats listés | unités | derniers choix | premiers choix | même citoyen dans les deux ordres |
|---|---:|---:|---:|---:|
| tous (2 à 11) | 254 | 167 sur 508, 142,4 attendus, P = 0,007 | 129 | 63,4 % [57,3 ; 69,1] |
| 2 à 4 | 155 | 113 sur 310, 108,3 attendus, P = 0,30 | 103 | 69,7 % |
| 5 ou plus | 99 | 54 sur 198, 34,0 attendus, **P = 0,0003** | 26 | 53,5 % [43,8 ; 63,0] |

Le premier rang n'est jamais favorisé. Inverser la liste change le choix dans 37 % des unités (46 % à partir de
cinq). Les listes du p500 (24 à 41 candidats) sont bien au-delà de ce qui est mesuré ici.

**2. Le vocabulaire ne change rien** (`neutral_wording` contre contrôle) : `candidacy_p500` 62,6 % contre 63,6 %
(McNemar p = 0,51), `pressure_act` 66,7 % contre 62,5 %, `vote_first_choice` 92,5 % contre 90,0 %, validité
inchangée partout. Le bras fait échouer la porte des logprobs (13 sur 16 alignés) : ses probabilités ne sont
pas lisibles, ses décisions le sont.

**3. L'ordre des champs : une anomalie plus qu'un résultat** (OBS-049). Le client envoie le corps de la requête
avec ses clés triées (`sort_keys=True`, « octets canoniques pour une clé de cache future »), schéma compris :
tout objet sort en ordre alphabétique. Les sorties du contrôle : `blank, cid, motif, ranking` (déclaré :
`cid, blank, ranking, motif`), `act, cid, motif, target`, `motif, party_id, winner_position`. Les tours
d'agents d'une vraie exécution (phase15) : `rationale` sort après `amendment`, `bill`, `campaign`,
`extra_legal` et `positions`, alors que `llm_schemas.py` annonce « le raisonnement vient avant les mouvements
qu'il justifie ».

Avec la clé renommée pour trier la première ou la dernière :

| bras | `candidacy_p500` (500) | `vote_first_choice` (40) | `pressure_act` (24) |
|---|---:|---:|---:|
| contrôle (ordre alphabétique) | 63,6 % | 90,0 % | 62,5 % |
| `motif` dernier | 66,8 % (Holm p = 0,85) | 90,0 % | 62,5 % |
| `motif` premier | **76,0 %** (98 contre 36 changements, Holm p = 2e-6) | 97,5 % (3 contre 0, p = 0,25) | 58,3 % (3 contre 4) |

`motif` après la décision ne change rien de significatif. `motif` en tête, avant l'id de l'unité, accorde 12
points de plus à `candidacy_p500` (accord avec la règle de seuil), et rien d'autre de significatif. Dans le
contrôle, `motif` précède déjà la décision pour la candidature (`cid, motif, outcome`) et la proposition de
parti, et précède `ranking` mais suit `blank` pour le vote ; seul `pressure_action` met `act` avant lui. Le
contraste « raison avant décision » n'est donc pas ce qui a bougé pour la candidature, et un code est une
étiquette, pas un raisonnement : lire l'écart de 12 points comme un effet à répliquer, de mécanisme inconnu.

## Ce que ça a coûté

- Des sessions courtes sur le GPU partagé : 81 requêtes en 4 à 5 minutes par bras, 138 pour le bank de 60
  graines, aucun redémarrage du serveur.
- Un faux départ : le premier bras d'ordre de champs, sans effet par construction (clés triées), a coûté une
  session et révélé l'anomalie du point 3. Une assertion de test qui ne pouvait pas échouer a été retirée avant.
- Deux fonctions passées rang C au ratchet radon, scindées avant le push.

## Verdict et pourquoi

**Suspendu.** Rien n'est adopté, parce que les deux changements possibles sont des décisions du propriétaire
avec un coût de régénération :

- **Ordre des candidats** (OBS-013) : la preuve est là, à partir de cinq candidats. Une tentative d'ordre par
  hachage (`fix/polity-candidate-order`, `fa78d71a`, non poussée) casse le contrôle d'inversion du bake-off, trois
  tests de scénario et les références golden.
- **Ordre des champs** (OBS-049) : envoyer le schéma dans l'ordre déclaré change chaque hash de requête (golden,
  journaux de relecture) et demande une autre canonicalisation pour la clé de cache.

Le vocabulaire est **rejeté** : aucun effet mesuré.

## Ce que j'en retiens (transférable à un autre projet)

- **Un bras qui ne change rien à l'octet n'est pas un résultat nul : c'est un bras qui n'a pas été envoyé.**
  Comparer les hashes des sorties avant de lire les moyennes a évité de conclure « l'ordre n'a pas
  d'importance » sur un test sans effet.
- **Un ordre de champs déclaré n'est un ordre de génération que si le client le conserve.** Toute
  canonicalisation faite pour un cache (clés triées) change ce que le modèle voit.
- **Deux écarts qui se ressemblent ne se lisent pas pareil** : la longueur de liste a un effet net et dose-dépendant
  (cinq candidats et plus), l'ordre des champs un effet isolé sur une famille, sans mécanisme : le premier se
  corrige, le second se réplique d'abord.
