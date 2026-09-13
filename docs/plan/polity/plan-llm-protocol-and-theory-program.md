# Réflexion — programme scientifique et programme LLM, comme un seul chantier

## Context

Two questions, asked together while the Phase 7 flagship run executes in the
background:

1. **La partie scientifique et théorique** — the theses this project has defined
   about how individuals behave with each other.
2. **Comment optimiser l'usage du LLM d'après les travaux de recherche** — long
   term, every available technique, not just the big obvious wins.

They turn out to be the same question, for a reason nobody has written down yet.
That finding is §1 below; everything after it is the program that follows from
it.

Two exhaustive inventories were built first (read-only, ~35 files each): the
behavioural theses embedded in the design doc + code, and every LLM technique
this project has already tried. Both are summarised inline where relevant.
Nothing here proposes re-treading ground already covered — the point of the
inventories was to avoid exactly that.

**Decisions taken before writing this**: all three theory angles are in scope
(audit / validity / extension); both topics run as one program with an explicit
dependency graph; the flagship run continues (its data stays useful, with the
`unverified` labelling Phase 1 already decided).

### Contrainte opérationnelle pendant l'exécution de Phase 7

**Rien de ce programme qui touche aux prompts ou au serveur ne peut démarrer
tant que le run flagship est en vol.** Two concrete hazards, both real:

- Changing any `build_*_user_prompt` (§5.B float precision, §5.E TOON) changes
  the bytes sent to the model. The run is checkpoint/resumable and *has already
  been resumed twice* this session — a resume after a prompt change would
  continue the same journal with a different prompt shape, and `config_hash`
  does **not** cover prompt-builder code, so the inconsistency would be silent.
- Restarting vLLM to change server flags (§3.B.6 speculative decoding, §3.B.7
  prefix-cache tuning) kills the in-flight run's connection.

What *is* safe while it runs: **§5.D** (read-only analysis of already-completed
journals) and documentation. That is where execution starts, and it is why the
ordering table's step 0 is gated below rather than started immediately.

---

## 1. The finding that binds the two topics

The project has 9 LLM decision types. Their measured reliability splits cleanly
— and the split runs exactly the wrong way for the science.

| Decision type | What it carries | Measured status |
|---|---|---|
| `pressure_action` (dt=10) | **Citizen chooses a lever against an officeholder** | **60,0 % agreement (open menu), bar is 80 %** — every remediation lever exhausted; **collapse confirmed on the SHIPPED closed menu** (2026-09-10, logprobs: P(act=4) ≥0,976 for every self_gap tested, +0,004 separation, not a batching artifact) — the one config every real run ships |
| `representative_response` (dt=6) | **Officeholder responds to citizen pressure** | **Collapse confirmed** (4/4 identical) — **sharpened 2026-09-10** (logprobs, 9-point continuous sweep across the same two poles): P(stance=1)=1,000000±0,000001 EVERYWHERE, no detectable gradient at all |
| `coalition_decision` (dt=9) | **Party joins/refuses a coalition** | **Collapse confirmed** (6/6 identical) — **sharpened 2026-09-10** (logprobs, real batch size): P(action=1)=0,965-0,999 EVERYWHERE, batching does not rescue any signal |
| `reaction_to_event` (dt=8) | **Citizen reacts to a shared event** | SCANDAL : **collapse RÉSOLU sur vLLM** (2026-09-06, avant cette session — la ligne « 6/6 identiques » était Ollama-only, obsolète) ; ECONOMIC_SHOCK : **mesuré 2026-09-10**, pas de collapse détecté sur le choix catégoriel (P(motif=402)=1,0 partout), intensité `salience_delta` non testée |
| `chamber_deliberation` (dt=11) | Member adjusts own position | Non tranché |
| `campaign_positioning` (dt=5) | Nominee adjusts own platform | No collapse (separate 50-66 % failure defect) |
| `candidacy_considered` (dt=2) | Citizen evaluates own ambition | **No collapse** (5/5) |
| `party_nomination_choice` (dt=4) | Party compares its own aspirants | **No collapse** (4/5) |
| `vote_cast` (dt=1) | Citizen ranks candidates | **Reliable** — 23/24 at chunk=3, real ground truth |

**Correction, 2026-09-10 (post-§5.C measurement):** this section originally claimed
*"the four compromised types are precisely the four inter-individual ones"* — a clean
biconditional that no longer holds as stated. `reaction_to_event`'s own row above was stale
when this was first written: its SCANDAL branch was already RESOLVED on vLLM before this
session started (2026-09-06, predating this document), and its ECONOMIC_SHOCK branch, now
measured for the first time, shows no collapse on the tested categorical axis either. So only
**three** of the four inter-individual types (`pressure_action`, `representative_response`,
`coalition_decision`) carry a CONFIRMED collapse — `reaction_to_event` does not, on either
branch, on what has been tested. The one-directional half still holds and is the part worth
keeping: every CONFIRMED collapse found so far is inter-individual (no self-referential/
intra-group type has ever collapsed) — but inter-individual does not, by itself, imply
collapse. The three reliable self-referential/intra-group types remain: *do I have enough
ambition*, *which of our own members is strongest*, *how far is each candidate from me*.

The consequence is not abstract. §7bis.9's social-contagion thesis — the
project's most ambitious claim, the Granovetter threshold mechanism, the
"bandwagon moment" — is implemented as `neighbors_acting` lowering an awakening
threshold that gates **`pressure_action`**. The contagion channel's output stage
is the decision type sitting at 60 %. Same for the elected-vs-sortition
comparison: the elected side's behaviour comes from `representative_response`
(collapse confirmed), the sortition side from `chamber_deliberation` (non
tranché).

So: *"les comportements des individus entre eux"* is currently the least
instrumented part of the simulation, not because it wasn't built, but because
every confirmed LLM unreliability found so far sits **exactly there** (see the
correction above: inter-individual is necessary but not sufficient for a
confirmed collapse). That is why the two topics are one program — LLM decision
quality is not an engineering concern
sitting beside the science, it is the binding constraint *on* the science.

---

## 2. A refinement of the project's own collapse hypothesis

§3.6.0 currently records the hypothesis as: *act/response framing collapses,
self-evaluation-against-threshold does not*. The project itself flags one
genuine exception it could not absorb — `campaign_positioning` is act/response
by form and does **not** collapse — and downgraded the title from "4/4" to
"3/5 + 2 exceptions" rather than force it.

**Proposed refinement (hypothesis, not established): the discriminating axis is
not act-vs-evaluation, it is whether the decision commits an action that lands
on another agent.**

| Type | Lands on another agent? | Collapse? |
|---|---|---|
| `pressure_action` | Yes — acts against an officeholder | Yes (quality failure) |
| `representative_response` | Yes — responds to citizens | Yes |
| `coalition_decision` | Yes — binds with other parties | Yes |
| `reaction_to_event` | Yes — reacts to another's conduct | Yes |
| `campaign_positioning` | **No — adjusts own platform** | **No** |
| `chamber_deliberation` | **No — adjusts own position** | Non tranché (consistent) |
| `candidacy_considered` | No — own ambition | No |
| `party_nomination_choice` | No — comparative judgement, no act | No |

This absorbs all eight data points **including the exception that broke the
current formulation**, and it stops `campaign_positioning` being an anomaly.

### Why this matters beyond tidiness: a named mechanism, and a decisive test

The current hypothesis has no mechanism ("mécanisme réel non identifié", stated
repeatedly). The refined axis suggests one, and it comes from outside this
project's literature: **RLHF alignment training.** Instruct-tuned models are
optimised to avoid committing consequential actions on a person's behalf; asked
to *do something to someone*, they fall to a safe fixed attractor. Asked to
*compute a judgement*, no such pressure applies. The corroborating detail is
already in this project's own data and was never read this way: the
schema-embedded `a_reasoning` experiment found the reasoning **genuine and
content-sensitive** while the decision still collapsed — a reasoning-to-decision
translation failure, which is what an output-side alignment prior looks like,
not a comprehension failure. The cross-model check fits too: `mistral:7b`
collapsed to the *opposite* pole (always MOBILIZE) — a different attractor, same
attractor-shaped failure.

**Decisive, cheap test nobody has run: base vs instruct.** `Qwen3-8B-Base`
against the shipped instruct model, same prompts, same four collapsed types. If
the collapse is alignment-induced, the base model shows materially more
content-sensitivity. Format compliance will be worse — irrelevant, constrained
decoding (xgrammar, already shipped) handles format. This is one GPU afternoon
and it either identifies the mechanism the project has been chasing for weeks or
eliminates the most plausible remaining candidate.

> **RÉSULTAT, 2026-09-10 — l'hypothèse alignement ne tient pas comme explication
> générale** (`check_base_vs_instruct_results.md`, protocole cadré en §2bis,
> exécuté sur la paire bf16 `Qwen3-4B`/`Qwen3-4B-Base` : même famille, même
> taille, même précision, même template, mêmes flags de service — seul le
> fine-tuning d'instruction diffère).
>
> | type de décision | ce qui a été trouvé | portée sur l'hypothèse |
> |---|---|---|
> | `representative_response` | **aucun collapse** sur le bras 4B *instruct* (porte préalable) | alignement insuffisant : un modèle instruct traite le cas correctement |
> | `coalition_decision` | collapse **identique** sur instruct ET base | **contredit** : retirer l'alignement ne change rien |
> | `pressure_action` | collapse sur instruct, récupération **partielle et faible** sur base | seule preuve à l'appui — sous la barre pré-enregistrée, et non significative |
>
> Le seul signal positif (`pressure_action` : séparation **+0,089** et r=**+0,378**
> contre −0,029/−0,117 sur instruct) est **en dessous de la barre pré-enregistrée
> de 0,10** sur la statistique primaire, et **non significatif** (n=17, t=1,58,
> df=15, **p ≈ 0,134**). Une distribution simplement plus diffuse sur le bras base
> (P ≈ 0,85 au lieu de ≈1,0 sur coalition) peut produire un gradient apparent sans
> rien « suivre » : cette explication alternative n'est pas écartée.
>
> §2 annonçait un test qui « identifie le mécanisme ou élimine le candidat le plus
> plausible ». **Il l'a largement éliminé.** La conformité de format sur le bras
> base était par ailleurs bonne (17/17 et 5/5 décisions structurellement valides) —
> xgrammar a absorbé le problème exactement comme §2 le prévoyait.
>
> **Réplique faite, 2026-09-10** (`check_pressure_gap_tracking_geometry_b_results.md`) —
> géométrie B (autres cids, autres valeurs de self_gap sur le même span, autre
> mandate_dev/ticks/target, ordre de batch **inversé**), les DEUX bras testés.
> Le signal du bras base ne se dissout pas, il se **renforce** (r passe de +0,378
> p=0,135 à **+0,685 p=0,0024**). Mais le contrôle retire l'interprétation : le
> bras **instruct** produit lui aussi une corrélation positive significative sous
> géométrie B (r=**+0,494**, p=0,044). « Le base suit self_gap, l'instruct non »
> n'est donc **pas** soutenu. Ce qui survit : le bras base est *un peu* plus
> sensible que l'instruct dans les deux géométries (r et séparation), mais
> **aucun bras ne franchit la barre pré-enregistrée de 0,10** et, dans les quatre
> cellules, **la décision émise reste totalement collapsée** (toujours la même
> constante) — seule la probabilité sous-jacente bouge.
>
> Contrôle offert par la paire de géométries : A batchait en ordre croissant, B en
> décroissant, donc un artefact de position aurait **changé de signe**. Il n'en a
> rien fait → la corrélation est un effet self_gap réel, pas un artefact de position.
>
> **Trouvaille latérale, plus intéressante que ce qui était cherché** : le NIVEAU
> global de probabilité est dominé par les constantes de niveau appel, pas par le
> signal par citoyen (P(act=4) ≈0,53-0,99 en géométrie A contre ≈0,007-0,47 en B
> sur le même bras base ; jusqu'à deux ordres de grandeur d'écart), alors que
> self_gap le déplace bien moins à l'intérieur d'un appel. Attribution prudente
> (plusieurs constantes ont changé à la fois), mais cela caractérise l'échec plus
> finement que « collapse » et pointe exactement là où §3.A.1/§3.A.2 pointent déjà.
>
> Conséquence pour la suite : `coalition_decision` qui collapse identiquement avec
> et sans fine-tuning d'instruction pointe vers la construction du prompt/de la
> tâche plutôt que vers le post-training. **§3.A.1 (échantillonnage déterministe
> par citoyen) et §3.A.2 (décomposition en deux étapes), tous deux intouchés,
> deviennent les candidats les mieux motivés.** Réplique préalable recommandée du
> seul signal positif avant de lui accorder le moindre poids — en variant la
> **géométrie de la sonde** (cids, valeurs de self_gap, ordre), **pas la graine** :
> à temperature=0 l'échantillonnage est un argmax, une graine différente
> reproduirait une sortie octet pour octet identique et ne confirmerait rien.

### 2bis — Cadrage technique, 2026-09-10 (mesuré, pas supposé)

Le paragraphe ci-dessus dit « one GPU afternoon » ; le cadrage montre que la
version littérale (`Qwen3-8B-Base` contre le modèle shippé) **ne tient pas sur ce
matériel**, et qu'une variante propre existe. Tout ce qui suit est vérifié
(`nvidia-smi`, `df`, l'API HF directement — la convention du projet), jamais
supposé.

**Contraintes dures :**

- **VRAM** : 16303 MiB au total, 12378 MiB pris par le serveur instruct en cours,
  **3443 MiB libres** — deux modèles ne peuvent pas coexister. Tout protocole est
  donc *séquentiel* (arrêter un serveur, démarrer l'autre), ce qui implique
  qu'aucun run flagship ne peut être en vol pendant l'expérience.
- **Disque** : 17 G libres (87 % utilisé), volume de cache HF à 6,1 G, plus 8,3 G
  de build cache Docker récupérables par `docker system prune`.
- **Il n'existe AUCUN modèle de base quantifié officiel dans toute la famille
  Qwen3.** Vérifié via l'API HF : la famille entière ne compte qu'un seul AWQ
  officiel, `Qwen/Qwen3-8B-AWQ` — précisément le modèle instruct déjà shippé. Le
  seul AWQ de `Qwen3-8B-Base` est `Siddharth63/Qwen3-8B-Base-AWQ`, **5
  téléchargements** : un requant communautaire.
- `Qwen3-8B-Base` n'existe qu'en bf16, ~16 GB de poids — ce que le commentaire de
  `docker-compose.llm.yml` établit déjà comme ne rentrant pas sur cette carte de
  16,3 GB (c'est exactement la raison pour laquelle l'instruct est en AWQ).

**Le déblocage, et c'est la découverte qui change la forme de l'expérience :**
les modèles de base Qwen3 **embarquent le même chat template que les instruct**,
`enable_thinking` et balises `<think>` incluses (vérifié sur `Qwen3-8B-Base`,
`Qwen3-4B-Base` et `Qwen3-4B`). Un bras « base » ne demande donc **aucune**
modification du client : ni chemin `/v1/completions` brut, ni prompt reconstruit
à la main, ni variante de `VllmJsonClient`. Les scripts de sonde §5.C déjà
écrits et déjà validés tournent tels quels contre un bras base, en ne changeant
que le modèle servi. Cela supprime ce qui aurait été le plus gros facteur de
confusion : un mécanisme de livraison de prompt différent entre les deux bras.

**Options, avec le compromis énoncé :**

| Option | Tient ? | Facteur de confusion |
|---|---|---|
| A. `8B-Base` bf16 vs instruct AWQ | **Non** (~16 GB de poids sur 16,3 GB) | — |
| B. `8B-Base` requant communautaire vs AWQ officiel | Oui | **Qualité du requant confondue avec la variable base/instruct** — exactement la « seconde variable » que ce projet refuse ailleurs |
| C. Paire AWQ officielle à une taille plus petite | **N'existe pas** | — |
| D. FP8 à la volée sur les deux bras (sources bf16 8B) | VRAM oui (~8 GB), **disque non** (32 GB à télécharger contre ~25 GB libres après prune) | Symétrique, mais aucun bras n'est la config AWQ shippée ; forte rotation disque |
| **E. `Qwen3-4B` vs `Qwen3-4B-Base`, bf16 tous les deux** | **Oui** (8,0 GB chacun, ~8 GB de marge KV) | **Aucun sur l'axe testé** : même famille, même taille, même précision, même template — seul le fine-tuning d'instruction diffère |

**Recommandation : E**, avec une porte préalable obligatoire.

**La porte préalable (peu coûteuse, décisive).** Le banc 4B n'est valide que si
le collapse **se reproduit sur `Qwen3-4B` instruct**. Rejouer d'abord les trois
sondes §5.C déjà écrites et validées contre le 4B instruct :
`check_logprob_pressure_action_gap_tracking.py`,
`check_logprob_response_stance_tracking.py`,
`check_logprob_coalition_action_tracking.py`. Si le collapse se reproduit → banc
légitime, on enchaîne sur le bras base. S'il **ne** se reproduit **pas** → c'est
en soi un résultat réel (le collapse dépend de l'échelle ou du modèle), et le
banc 4B ne peut pas répondre à la question de §2 : on retombe alors sur
l'option B en étiquetant explicitement le facteur de confusion du requant, ou on
diffère.

**Critère pré-enregistré** (discipline du projet : énoncé avant tout appel
live). Si l'alignement cause le collapse, le bras base doit montrer une
sensibilité au contenu **matériellement** plus grande. Concrètement, en reprenant
les écarts déjà mesurés sur le bras instruct shippé — `pressure_action` +0,004,
`representative_response` 0,000001, `coalition_decision` 0,035 — le seuil
pré-enregistré est : **le bras base montre un écart ≥ 0,10 sur au moins une sonde
où l'instruct montrait < 0,05**. En dessous, l'hypothèse alignement est affaiblie,
pas confirmée. La conformité de format sera pire sur le bras base : c'est attendu
et hors sujet (xgrammar s'en charge) — les échecs de décodage se rapportent
**séparément** de la lecture du gradient P, jamais confondus avec elle.

**Notes opérationnelles :**

- Service : un profil/override compose avec `--model Qwen/Qwen3-4B[-Base]`,
  `--served-model-name qwen3:4b[-base]` (doit contenir « : » — règle de pinning de
  `config.py` ligne 847, vérifiée), **sans** `--quantization` (bf16), même
  `--reasoning-parser qwen3` et même `--structured-outputs-config` xgrammar/
  `disable_any_whitespace` que le serveur shippé.
- Révisions à épingler (convention du projet, récupérées via l'API HF) :
  `Qwen3-4B` `1cfa9a720891…`, `Qwen3-4B-Base` `906bfd4b4dc7…`,
  `Qwen3-8B-Base` `49e3418fbbbca6…` si l'option B est un jour reprise.
- Les scripts de sonde surchargent déjà `provider`/`base_url` via
  `dataclasses.replace` ; il leur faut une surcharge `model=` de plus —
  changement mécanique, pas structurel.
- Disque : `docker system prune` d'abord (8,3 G récupérables), puis 8 G + 8 G de
  téléchargements contre 17 G libres. Les deux modèles peuvent coexister **sur
  disque** ; un seul est chargé en VRAM à la fois.

---

## 3. Programme LLM

The inventory found **33 distinct avenues already explored**. Every one is
reactive: a bug fixed, a failure worked around, a constant recalibrated. There
is no proactive performance engineering anywhere, and **zero citations of LLM/ML
systems research** in a repo that cites political science meticulously. The
instinct behind the question is correct.

### 3.A — Décision: qualité (le goulot)

Ordered by expected value, all untried:

1. **Per-citizen deterministic sampling** — *the highest-value idea here.*
   Everything runs at `temperature=0`, i.e. greedy argmax. When prompt
   differences are small relative to the model's prior, greedy decoding gives
   *every citizen the same token* — content-blind collapse is, mechanically,
   what greedy decoding does to a weakly-discriminated distribution. The fix
   used everywhere in the silicon-sampling literature is temperature > 0 with
   multiple samples, which this project cannot afford and which breaks
   reproducibility. **But a per-citizen seed derived deterministically from
   `(run_seed, citizen_id, tick, decision_type)` at temperature > 0 gives
   variance across citizens while remaining exactly reproducible.** Same run,
   same seeds, same output — different citizens, different draws. This directly
   attacks the collapse without giving up the property the project has spent
   months defending. Tradeoff to state honestly: it adds noise to each
   *individual* decision while restoring *population* variance — for an ABM,
   population variance is the scientifically load-bearing quantity.

   > **PRÉMISSE RÉFUTÉE, 2026-09-10 — à ne pas construire tel quel**
   > (`check_per_citizen_sampling_premise_results.md`, vérifié avant construction).
   > Deux problèmes, tous deux mesurés :
   > - **Architecture** : `seed` et `temperature` sont des champs par *requête*, or
   >   `decide_pressure_actions` batche jusqu'à 25 citoyens par requête. Une graine
   >   par citoyen impose `chunk_size=1`, soit **25× les appels** sur le type de
   >   décision au plus fort volume du projet.
   > - **Prémisse fausse** : un tirage ne peut exprimer que le signal déjà présent
   >   dans P. Or sur le modèle shippé, P(act=4) moyen = **0,998** et la variance de
   >   Bernoulli moyenne p(1−p) = **0,0018** → un tirage par citoyen changerait
   >   **0,03 décision sur 17**. Dans la configuration la plus favorable jamais
   >   mesurée (bras 4B base), il en changerait ~6 %. La distribution n'est pas
   >   « faiblement discriminée » : elle est **quasi déterministe, confiante et
   >   fausse**, et les configurations diffèrent surtout par le *pôle* dont elles
   >   sont sûres.
   >
   > Corollaire : il faut **changer la distribution**, pas la rééchantillonner —
   > ce qui désigne §3.A.2 ci-dessous. Monter la température au-delà de 1
   > fabriquerait de la variance *décorrélée* de l'état du citoyen : pour un ABM
   > c'est pire que l'échec actuel, pas mieux.

2. **Two-stage decomposition** — already named by the project for
   `pressure_action` (binary act/don't-act, then lever choice), never tested.
   The refined axis in §2 says it should generalise to all four
   lands-on-another-agent types. Research grounding: least-to-most and
   decomposed prompting.
3. **Grammar-level invariant enforcement** — `blank=1 ⟹ ranking=[]` (§3.6.1) is
   currently a Pydantic validator that *rejects after the fact*, and is the
   single most frequent `vote_cast` failure (~6,7 %, deterministic, and the
   reason `_VOTE_CAST_RETRY_SEED_BASE` had to be invented). Encoded into the
   xgrammar schema instead, the violation becomes **unreachable**. Kills a whole
   failure class rather than retrying it.
4. **Base vs instruct** — §2 above.
5. **DeepSeek-R1 distillations** — already on the backlog, flagged there for
   native explicit chain-of-thought; §2's reasoning-to-decision framing makes
   them a targeted candidate rather than a generic model swap.

### 3.B — Débit (levers jamais touchés)

6. **Speculative decoding** — **zero mentions anywhere in the repo.** vLLM
   supports n-gram speculation natively (`--speculative-config`). Structured
   JSON emission is highly predictable (field names, delimiters, the codebook's
   own integer motifs); `<think>` is less so. Expected: real gains on the
   visible-output portion, unknown on reasoning. Cheap to measure, nothing to
   lose — and it is the single largest untapped standard technique.
7. **Prefix-cache tuning** — enabled by default, and *only ever reliability-
   tested, never tuned*. Live logs during the parity run showed **57,9 % hit
   rate**, i.e. real headroom. Levers: order every prompt invariant-first
   (system prompt + codebook tables byte-identical, variable citizen data last),
   and order chunks so consecutive calls share the longest possible prefix.
   Pure win, no behavioural risk, no determinism cost.

   **Implémenté et vérifié en direct, 2026-09-10, pour `vote_cast` ET
   `chamber_deliberation`.** Mesuré directement (pas estimé) : le
   `cid_list` par chunk, jusque-là embarqué en fin de system prompt, brisait
   la continuité du cache pour chaque nouveau chunk — deux chunks de la
   même élection divergeaient dès 84,4 % de la longueur du system prompt.
   Déplacé vers un champ `expected_cids` dans le user prompt (les données
   qui varient par chunk appartiennent au message de données, pas au
   message d'instruction). Aucun changement sémantique à l'instruction
   elle-même.
   - `vote_cast` : hit rate en direct montant de 65,2 % à 73,0 % sur une
     rafale de 8 appels d'une même élection ; 14/15 décisions non-fallback
     correctes contre `simple_rules.build_ranking` (voir
     `check_vote_cast_prefix_cache_fix_results.md`).
   - `chamber_deliberation` : le system prompt ne dépend plus DU TOUT des
     membres (`build_chamber_system_prompt` ne lit même plus son propre
     paramètre `members`) — il devient une constante pour toute la durée
     d'un run à config fixée, pas seulement stable au sein d'un chunk.
     30/30 décisions sincères correctes, 0 fallback, 0 retry, y compris en
     forçant délibérément l'état déclencheur historique du mode A
     (`chamber_position == issue_positions` pour chaque membre synthétique)
     — zéro récurrence. Hit rate déjà haut (68-70 %) et stable dès le
     premier échantillon de la rafale, cohérent avec un cache déjà chaud
     depuis un appel chamber antérieur dans la même session serveur (voir
     `check_chamber_prefix_cache_fix_results.md` pour la réserve sur cette
     interprétation — non isolée avec un contrôle cache-froid dédié).
8. **Reasoning-budget control** — `<think>` tokens dominate cost. The project
   checked for a `budget_tokens` equivalent, found none exposed, and stopped.
   Worth revisiting: budgets are currently sized against *worst case*
   (`_dynamic_max_tokens` now requests the maximum the window allows), never
   against the measured distribution. The 30-year run will produce that
   distribution for free.
9. **Model routing / cascade** — `candidacy_considered` is a threshold
   comparison; it does not need an 8B model. Route simple types to a small
   model, escalate on disagreement. Research: FrugalGPT, model cascades. Note
   §12's "un seul modèle fine-tuné généraliste" — a routing architecture is a
   deliberate departure from that and needs an explicit decision, not a silent
   one.

### 3.C — Long terme (v8, §12)

10. **Fine-tuning is already correctly scoped and correctly blocked.** §12 is
    resolved in favour of auto-distillation on the model's own successful
    trajectories; `plan-decision-quality-validation.md` establishes that
    "successful" has only ever meant *structurally valid* for 8 of 9 types, and
    that curating training data on that basis would engrave a demonstrated
    silent corruption. **That ordering is right and this program keeps it**:
    §3.A must land before any distillation data is curated.

---

## 4. Programme scientifique

### 4.A — Audit contre la littérature

The polity model has **no single academic reference** — `traceability.md` records
it as *"modèle propre au projet"*. Citations exist but are scattered and
one-directional (Granovetter for thresholds, Downs for spatial competition,
Superti for blank-vote protest, Shugart & Carey for calendars, Laakso &
Taagepera for fragmentation). The audit worth doing:

- **Ground the ungrounded.** `L(t)`'s decay-accumulator form, `écart(t)`'s
  weighting, the awakening-threshold shape (`beta(3,5)`, open point #13, flagged
  as the *most structurally important uncalibrated parameter* in the project),
  and the two-tier menu/choice separation are all project-invented. Each needs
  either a literature anchor or an explicit "this is ours" label.
- **Test the theses that are already contradicted by the project's own data.**
  The clearest: §7bis.6's purely-actional legitimacy model predicts a
  representative facing a passive population loses nothing — yet a president
  **conceded 13 times to a population with `inaction_rate=1.0`**. The design
  doc's own open question. §2's collapse mechanism is a candidate explanation
  (a collapsed `representative_response` concedes regardless of input) that
  would resolve it as an *instrumentation artefact rather than a finding* —
  which is exactly why §3.A must precede any theoretical interpretation here.
- **Add the missing literature: LLMs as human proxies.** Zero citations today.
  The relevant body (Argyle et al. 2023 on silicon sampling and algorithmic
  fidelity; Park et al. 2023 generative agents; Santurkar et al. 2023 on whose
  opinions models reflect; Bisbee et al. 2024 on LLM survey responses having
  *systematically lower variance than humans*) reports one consistent failure
  mode: **LLM populations are mode-collapsed and caricatured relative to real
  ones.** This project has independently rediscovered that phenomenon four times
  and called it a bug each time. Naming it correctly turns four scattered bug
  reports into one documented, literature-backed limitation — and points
  directly at §3.A.1 as the standard mitigation.

### 4.B — Validité et méthodologie

- **Single-seed is the project's largest standing methodological risk, and it
  has already fired once.** `seed=42` was used by every acceptance run since v4
  Lot 8 and was never validated; the Blank vote turned out to win 68 % of seeds
  under the shipped distribution. Every results doc says "n=1, une graine".
  The ABM standard is multi-seed with confidence bands.
- **Deterministic probes are optimistic ~2× on citizen-arbitrated quantities**
  (measured: 63,6 % predicted vs 33,3 % actual office occupancy) — currently a
  "working hypothesis, must not be cited as acquired". It needs either
  promotion to a validated rule or retirement.
- **The determinism question deserves reopening, on the project's own terms.**
  Byte-reproducibility has cost a great deal: concurrency rejected (a measured
  **5,84×**), `VLLM_BATCH_INVARIANT` rejected (11,3× slower). Yet the shipped
  flagship config runs `max_batch_replays: 2`, **which the plan itself documents
  as non-byte-reproducible**. The gate that rejected concurrency was applied at
  `replays=0` — a configuration that is not the one being shipped. This is worth
  stating plainly because it is a real inconsistency, *not* because the
  conclusion is obviously wrong: concurrency also **raised the failure rate
  30 % → 39 %**, which is a quality objection, not merely a reproducibility one.
  The honest position: that quality objection is a consequence of §3.A's
  problem, so **fixing decision quality is what would unlock this**, and the
  dependency runs quality → concurrency → multi-seed → real statistics.

### 4.C — Extension

Only after the above; listed so they are not lost:
- **The missing "law" concept** — blocks the sortition chamber's veto (open
  point #11) and, per the project's own note, is a chantier the size of v7.
- **Persona library (§9) is designed but never built.** Citizens are currently
  a 20-dim vector plus scalars. The silicon-sampling literature ties behavioural
  fidelity directly to conditioning richness — so this is not decoration, it is
  §3.A.1's natural complement for restoring population variance.
- **Conviction voting** — flagged as a fourth competing recall mechanism that
  would need to route through `écart(t)`; explicitly undecided.
- **Static-only social graph** — `evolving: true` is parsed then rejected at
  config load; homophily has never been tested.

---

## 5. Le format d'échange — la réponse honnête est contre-intuitive

### 5.A — Ce que dit la littérature, et ce qui s'applique vraiment ici

Two real findings, and only one of them applies to this project.

**Finding 1 — format restriction can degrade reasoning.** *"Let Me Speak
Freely?"* (Tam et al., 2024) measured constrained decoding hurting reasoning on
several tasks. Real, contested in magnitude, and **already partly mitigated
here**: `--reasoning-parser qwen3` exists precisely so the grammar does not
swallow the `<think>` block, and the project already caught the failure mode it
protects against (a silent `enable_thinking` no-op under grammar constraint).

**Finding 2 — JSON is token-expensive.** Also true in general: every key is
repeated for every array element, plus quotes, braces, commas. TSV/CSV states
keys once in a header; a minimal DSL (`1|0|4,2,1|101`) costs almost nothing.

**But finding 2 barely applies here, and it is worth saying so plainly rather
than shipping a satisfying-looking change with no effect.** Measured in this
session: a `vote_cast` decision's raw output was **81 characters** (~25 tokens),
against `think=True` budgets of 8 000–12 000 and actual generation of
~300–1 400 tokens per call. **The JSON output is under 5 % of what gets
generated; the reasoning is essentially all of it.** Converting JSON→TSV would
save on the order of 20 tokens out of 1 000. That is not where the cost is.

### 5.B — Où le format compte réellement ici : l'entrée, pas la sortie

The prompts are the part that hurts, and they are large: measured **2 242
tokens** (chamber, chunk=5) and **3 000 tokens** (vote_cast, chunk=5). Prompt
size is exactly what constrains chunk size — the entire `_dynamic_max_tokens`
saga was a fight for context headroom. Two untouched levers:

1. **Float precision.** Every numeric field is `round(x, 4)` — verified across
   `llm_behavior_engine.py` (positions, priorities, distances, platforms,
   thresholds, scores). `build_chamber_user_prompt` sends 3 arrays × 20 dims × 5
   members = **300 floats per call**; vote_cast sends ~330. Rough estimate: the
   last two decimals are ~10-20 % of prompt tokens — spent on precision the
   model cannot plausibly use for a coarse categorical judgement. Dropping to 2
   decimals is free, and the exact figure is **one cheap probe away** using the
   `count_prompt_tokens` method just built for `_dynamic_max_tokens`.
2. **Redundant payload at the exact point of a known bug.**
   `build_chamber_user_prompt` sends both `sincere_position` and
   `chamber_position` — 40 floats — and at seating time **they are identical by
   construction**. That is precisely the state that triggers the documented
   2,6 % Mode-A reasoning loop, currently patched by a sentence in the system
   prompt telling the model this case is trivial. Sending
   `position_unchanged: true` instead would halve that payload *and* remove the
   ambiguity structurally rather than verbally.

Why this compounds: smaller prompts → more context headroom → larger chunks
legal → fewer calls. It multiplies with §3.B rather than adding to it.

**Point 1 implémenté, 2026-09-09, scope volontairement restreint au moment de
l'écriture** (`_PROMPT_VECTOR_PRECISION = 2`, `llm_behavior_engine.py`).
**Vérifié en direct, 2026-09-10** — vote_cast via
`check_vote_cast_truncation_fix.py` (3 runs indépendants, 0 échec attribuable
à la précision) et le smoke run du flagship ; chamber via
`check_precision_and_logprobs_live.py` (10/10 sincere, 0 fallback). Deux
restrictions découvertes en implémentant, pas anticipées en écrivant ce
paragraphe :

- **`distances`/`blank_threshold` (vote_cast) restent à 4 décimales.** Ce ne
  sont pas des vecteurs lus holistiquement — c'est la comparaison seuil-à-seuil
  exacte qui a déjà produit un collapse à 100 % blanc une fois ; coarsir cette
  précision sans A/B en direct risquerait de déplacer des décisions
  limitrophes sans que rien ne le détecte avant un run complet.
- **Seuls `vote_cast` et `chamber_deliberation` sont touchés pour l'instant.**
  `campaign_positioning` porte son propre défaut actif non résolu (50-66 %
  d'échec, troncature + fuite motif→cid) ; `representative_response`,
  `coalition_decision` et `reaction_to_event` (branche SCANDAL) ont un collapse
  confirmé. Changer leur prompt maintenant contaminerait toute future
  investigation sur CES défauts précis — même discipline « une variable à la
  fois » que le projet applique déjà partout ailleurs. Ces trois/quatre types
  restent candidats pour ce même changement, mais après que leurs propres
  chantiers de fiabilité aient conclu, pas en même temps.

Point 2 (`position_unchanged`) reste non implémenté — restructuration du
format d'entrée plus profonde que la précision seule, à ne pas faire sans A/B
en direct disponible dès le départ.

### 5.C — Lire les logprobs au lieu d'échantillonner (le vrai levier de format)

For any binary decision, the model does not need to *emit* a token — vLLM
exposes `logprobs`, so you can read **P(act)** directly. This is a different
protocol, not a different serialization, and it solves four problems at once:

- a **graded, continuous** signal instead of a single categorical draw;
- **calibration for free** — a threshold you can tune, rather than a coin flip;
- **collapse becomes measurable instead of inferred**: if P(act) is near-identical
  across wildly different citizens, that *is* the collapse, quantified on every
  call, rather than deduced from 4–6 hand-built extreme cases;
- determinism preserved exactly.

It composes directly with §3.A.2: the two-stage split's first stage (act /
don't-act) becomes a logprob read rather than a generation — cheaper *and*
better instrumented than what it replaces.

**Primitive implémenté, 2026-09-09** (`VllmJsonClient.complete_with_logprobs`,
`llm_client.py`, offline-verified — mypy/flake8/1313 tests green, 7 new
mocked-transport tests). Live-confirmé le même jour (avant l'implémentation),
via un probe forced-choice brut : P(yes)=0.962, P(no)=0.038. **La méthode
elle-même vérifiée en direct le 2026-09-10** une fois le serveur libéré
(`check_precision_and_logprobs_live.py`) : P(oui)=0.999994 vs P(non)=5.1e-6
sur un probe trivial, contre le vrai serveur, pas un mock. Une chose reste
**non résolue, délibérément pas attaquée par ce premier incrément** :

1. **Le vrai problème dur : localiser le bon token dans une sortie JSON
   contrainte par xgrammar.** Le probe déjà vérifié pose la question en
   forced-choice nu (le PREMIER token généré EST la réponse) — une décision
   de production réelle (`"act":3` quelque part dans un objet JSON) n'a pas
   cette propriété : le token qui compte est enterré après le boilerplate
   du schéma, à une position qui varie par prompt. `complete_with_logprobs`
   expose la matière première (un `TokenLogprob` par position générée) mais
   ne résout PAS cet alignement — c'était un problème séparé, pas encore
   attaqué, et la prochaine étape réelle avant d'instrumenter un type de
   décision de production.

   **Résolu et vérifié en direct, 2026-09-10.** Deux ajouts : `VllmJsonClient.
   complete_json_with_logprobs` (`llm_client.py`, une méthode distincte de
   `complete_with_logprobs`, pas un paramètre — même discipline « une forme
   d'appel = une fonction totale de ses propres arguments » déjà appliquée
   partout ailleurs sur cette classe) envoie la VRAIE forme de production
   (`response_format`/xgrammar, `think=True` par défaut) tout en demandant
   `logprobs`/`top_logprobs` ; le nouveau module `llm_logprob_instrumentation.
   py` (`locate_decision_field_logprobs`, `binary_probability`) résout
   l'alignement lui-même en reconstruisant le texte brut généré (concaténation
   de tous les tokens, PAS `content` seul — `content` est amputé du bloc
   `<think>` par le reasoning parser, `tokens` non) puis en localisant `content`
   comme sous-chaîne de ce texte brut avant de chercher, dans cet espace
   d'offsets bruts, le token qui couvre la valeur du champ visé pour chaque
   décision du batch (appariées à leur `cid` via `json.loads(content)`, même
   ordre documentaire). 13 tests offline (`test_polity_llm_logprob_
   instrumentation.py`) couvrent délibérément des frontières de token
   adverses, y compris une qui chevauche `</think>` lui-même.

   **Vérifié en direct contre le seul type avec vérité terrain**
   (`check_logprob_blank_calibration.py`, §5.C's own Verification bar) :
   16 votants réels (8 vérité-terrain blanc, 8 non-blanc, sélectionnés sans
   biais dans un pool de 200), à travers les VRAIS `build_system_prompt`/
   `build_user_prompt` de `vote_cast`, `think=True`, chunk_size=3 (la valeur
   shippée). Alignement du localisateur : **16/16**, zéro `LogprobAlignmentError`
   malgré un bloc `<think>` réel de longueur imprévisible à chaque appel.
   Précision de l'appel à seuil (P(blank=1)>0.5) : **16/16**. Séparation
   moyenne P(blank=1) : **0,997 (vérité=blanc) vs 0,049 (vérité=non-blanc)**.
   Réserve honnête : cet échantillon est équilibré par résultat, pas par
   difficulté — aucun des 16 votants n'est proche de son propre seuil
   `blank_threshold`, donc cette séparation nette valide la technique
   d'ALIGNEMENT et le SENS de la corrélation, pas encore la valeur du signal
   gradué sur un cas limite genuinely ambigu (voir
   `check_logprob_blank_calibration_results.md` pour le détail).

   Le signal est donc licencié pour un usage sur des types sans vérité
   terrain (`pressure_action`, la cible nommée par §5.C lui-même) —
   **pas encore appliqué là**, prochaine étape distincte, pas supposée
   par analogie.

   **Appliqué et mesuré en direct, 2026-09-10**
   (`check_logprob_pressure_action_gap_tracking_results.md`) : la question
   restée explicitement ouverte dans le docstring de `decide_pressure_
   actions` lui-même — *« under the SHIPPED (closed) menu ... whether it
   tracks self_gap across that pair [0 vs 4] has not been measured
   either »* — a maintenant une réponse claire et négative. 17 citoyens
   réels, self_gap 0,02→2,20, prompt/schema/think=False de production
   inchangés, menu fermé shipped (`electoral_only=true`, {0,4} seuls
   légaux) : **P(act=4) reste ≥0,976 pour CHAQUE citoyen**, y compris le
   plus satisfait possible (self_gap=0,02) — séparation moyenne
   satisfait/mécontent : **+0,004**, négligeable. **Exclu explicitement
   comme artefact de batching** : les deux valeurs extrêmes rejouées
   totalement seules (chunk_size=1) donnent une séparation encore plus
   plate (+0,000008). C'est un collapse réel, quantifié en continu plutôt
   qu'inféré, précédemment invisible car un taux plat d'act=4 sous menu
   fermé produit exactement le `mobilization_rate` agrégé que le menu
   prédit déjà par construction — il n'aurait jamais émergé comme anomalie
   dans une métrique agrégée, seulement dans une lecture P(act) au niveau
   citoyen. Chaque run flagship réel utilise ce menu fermé : ce collapse
   touche donc le SEUL cas que toute production exerce réellement,
   auparavant le moins testé de tous parce qu'il semblait le plus simple
   (un choix à 2 options). Mécanisme non établi — ne correspond pas
   proprement au cadre §2 existant (« atterrit sur un autre agent ») : les
   deux options {0,4} sont non-assertives, la préférence mesurée est pour
   l'option qui SONNE la plus institutionnellement légitime parmi deux
   options passives, pas pour l'inaction en général. Voir le results doc
   pour la réserve complète.

   **Deuxième application, 2026-09-10**
   (`check_logprob_response_stance_tracking_results.md`) :
   `representative_response`, dont le collapse n'était établi que par un
   signal 2-points/4-échantillons (les deux pôles opposés de
   `plan-adversarial-framing-collapse.md`). Rejoué en continu : les
   MÊMES deux pôles, 9 points interpolés entre eux, P(stance=1,
   CONCESSION) lue directement. Résultat encore plus net que
   `pressure_action` : **P(stance=1) = 1,000000 ± 0,000001 SUR TOUS LES
   9 POINTS**, y compris les deux pôles d'origine — aucun gradient
   détectable entre un élu à légitimité quasi parfaite/rue à zéro et un
   élu en crise profonde (L=0,05, mandat dévié de 0,8, mobilisation
   soutenue). Confirme et affine le signal-collapse déjà établi plutôt
   que de le contredire ou le nuancer — exclut explicitement l'hypothèse
   qu'une zone de sensibilité réelle aurait pu se cacher entre les deux
   points d'origine.

   **Troisième application, 2026-09-10**
   (`check_logprob_coalition_action_tracking_results.md`) :
   `coalition_decision`, dont le docstring nommait DEUX lacunes explicites
   — un signal catégoriel 2-points/6-échantillons, et « not tested at
   real production batch size ... an open gap » (le diagnostic d'origine
   utilisait size=1, jamais un batch reel de plusieurs partis). Les deux
   fermées ensemble : 5 points le long des MÊMES deux pôles (distance de
   plateforme 0→√20, déficit institutionnel de l'initiateur 25→0, les deux
   axes bougeant ensemble comme dans le diagnostic d'origine), CHAQUE
   appel regroupant les 5 partis répondants ensemble (taille de batch
   réelle de production, jamais exercée avant pour ce type). Résultat :
   **P(action=1, JOIN) reste entre 0,965 et 0,999 partout**, y compris aux
   deux pôles d'origine (différence pôle-à-pôle : -0,0026, négligeable).
   Le batching ne restaure aucun signal qu'une décision réellement
   sensible au contenu montrerait — confirme et étend le « 6/6 identiques
   » d'origine plutôt que de le nuancer.

   Trois des quatre types « collapse confirmé » d'origine
   (`pressure_action`, `representative_response`, `coalition_decision`)
   sont maintenant mesurés en continu via logprobs ; `reaction_to_event`
   (branche SCANDAL) reste le seul non encore rejoué ainsi.

   **Quatrième application, 2026-09-10**
   (`check_logprob_reaction_economic_shock_tracking_results.md`) — PAS
   une remesure de SCANDAL (déjà résolu sur vLLM avant cette session, une
   remesure aurait eu la plus faible valeur des quatre types d'origine),
   mais la lacune réellement ouverte que `decide_reaction_to_event`
   nomme lui-même : la branche ECONOMIC_SHOCK, « still untested, either
   backend ». Résultat : **P(motif=402, réagit) = 1,000000 à CHAQUE
   magnitude testée** (0,05→1,50, traversant le seuil « majeur » à 0,5) —
   motif=403 (non pertinent) jamais choisi une seule fois. Ne teste que
   le choix catégoriel, pas l'intensité graduée de `salience_delta` (un
   champ flottant, hors de portée de cette technique) ; et contrairement
   aux trois autres, « toujours pertinent » pour un choc économique
   systémique n'est pas manifestement un défaut de la même façon que
   « toujours céder » en est un — voir le results doc pour la réserve
   complète avant de compter ceci comme un cinquième collapse confirmé.

   **Un bug d'instrumentation réel trouvé et corrigé au passage, à portée
   générale** : la première tentative a donné `P(motif=402)=0,5` partout
   — un signal plat suspect, pas une vraie mesure. Cause : le codebook de
   motifs entier de ce projet groupe ses codes par chiffre de tête partagé
   (401/402/403, 501/502/504/505, etc.) — l'ancrage « premier caractère de
   la valeur » par défaut de `locate_decision_field_logprobs` localise
   alors un token IDENTIQUE quelle que soit la valeur en cours de
   génération, pas faux, juste non informatif, et `binary_probability`
   retourne son propre 0,5 « ni candidat capturé » documenté — qui
   RESSEMBLE à une vraie mesure. Corrigé par un nouveau paramètre
   `value_char_offset` (défaut 0, rétrocompatible, 4 nouveaux tests
   offline) permettant de cibler le chiffre réellement discriminant.
   Disponible pour toute future instrumentation d'un champ motif
   multi-chiffres.

### 5.E — TOON : bon outil, mais pas sur les prompts qu'on croit

TOON (Token-Oriented Object Notation, fin 2025) declares keys once as a header
and then emits rows, CSV-style, for uniform arrays of objects — plus explicit
length/field markers (`users[3]{id,name,role}:`) that double as a self-check for
the model. Its sweet spot is **many records × many scalar fields**, which is
exactly the shape of a batched decision prompt. So the fit is real here, unlike
generic "use YAML" advice.

**But the payoff splits sharply by decision type, and the split is measurable
from the code, not guessed:**

| Prompt | Shape per record | Ce qui domine | Levier qui paye |
|---|---|---|---|
| `vote_cast` | 5 clés, **47 nombres** (`positions` 20, `priorities` 20, `distances` 5, +2 scalaires) | Les **nombres** (~90 %) | **§5.B précision** (~25 %) ≫ TOON (~8 %) |
| `chamber_deliberation` | 4 clés, **60 nombres** (3 × 20 dims) | Les **nombres** | **§5.B précision + dédup** ≫ TOON |
| `pressure_action` | ~8-12 clés, **quasi que des scalaires** (docstring : « Deliberately NO 20-dim position vectors »), **jusqu'à 25 citoyens par chunk** | Les **clés répétées** | **TOON (~30-40 %)** ≫ précision |
| `candidacy_considered` | cid + 2-3 scalaires, chunks de 20+ | Les **clés répétées** | **TOON** ≫ précision |

So the two levers are **complementary, not competing**: float precision pays on
the vector-heavy types, TOON pays on the scalar-heavy high-volume ones. And
`pressure_action` — the single highest-volume decision type in the project — is
squarely in TOON's zone.

**Trois réserves, dont une bloquante pour l'ordonnancement :**

1. **Ne pas toucher à la sortie.** JSON-schema constrained decoding is
   load-bearing here: xgrammar, the `disable_any_whitespace` fix, `_inline_refs`,
   nine `decode_*_batch` functions and their Pydantic validators all hang off it.
   A TOON grammar is writable, but you would trade the entire structural-validity
   pipeline for the ~20 tokens §5.A already showed are negligible. **Input only.**
2. **Token count ≠ comprehension.** TOON is recent; these models have seen
   overwhelmingly more JSON in training. The published claims are largely about
   token count and retrieval benchmarks — not about numeric reasoning over
   positions and thresholds, which is what this project actually asks for. This
   demands an A/B on **decision quality**, not just a token count, exactly as
   this project demands for everything else.
3. **Bloquant : `pressure_action` est le cobaye idéal *et* le malade.** Changing
   its prompt format invalidates every prior collapse measurement on it — the
   61 % agreement figure, the ablations, the cross-model checks were all measured
   against the JSON prompt. So the TOON test there must be **paired with §5.C's
   logprob instrumentation** (measure P(act) before and after), or it produces a
   new prompt with no comparable baseline. One more reason instrumentation comes
   first.

**`candidacy_considered` fait et vérifié en direct, 2026-09-10**
(`check_toon_candidacy_ab_results.md`) — le point de départ mandaté ci-dessus (vérité
terrain réelle, pas de défaut de collapse connu). Deux nouveaux prompt builders
diagnostiques (`build_candidacy_system_prompt_toon`/`_user_prompt_toon`, ne diffèrent
du JSON shippé QUE par un paragraphe d'explication du format, testé offline), sortie
JSON inchangée, `think=False` de production, 25 citoyens (le `llm.max_batch_size`
shippé, un chunk réel de taille pleine). Les deux portes tiennent : **économie de
tokens réelle (853→794, -6,9 %)**, et **précision identique, pas seulement proche**
(16/25 pour les deux formats — les mêmes décisions, pas juste le même compte).
Trouvaille séparée, hors périmètre de ce gate : 16/25 = 64 % est en dessous de la
barre ≥80 % habituelle du projet, **sur les deux formats identiquement** — donc pas
un défaut introduit par TOON, mais une question de fiabilité de `candidacy_considered`
lui-même (distincte du collapse), pas encore investiguée. Pas encore shippé dans
`decide_candidacies` — décision séparée, pas automatique après un seul A/B propre.
`pressure_action` est la prochaine cible, débloquée depuis que son propre baseline
P(act) a été capturé (`check_logprob_pressure_action_gap_tracking_results.md`).

**`pressure_action` fait et vérifié en direct, 2026-09-10**
(`check_toon_pressure_action_ab_results.md`) — la même sonde à 17 points rejouée
verbatim, appariée avec la lecture logprob comme exigé ci-dessus (réserve n°3).
**Économie de tokens réelle et plus grande que candidacy_considered : -44,0 %
(1743→976)**, cohérent avec l'estimation du plan (« TOON ~30-40% » pour ce type).
Mais **la porte qualité NE tient PAS** : TOON ne restaure pas la sensibilité à
self_gap — il fait basculer la constante vers laquelle le modèle collapse (JSON :
toujours act=4, P≥0,976 partout ; TOON : toujours act=0 par la même lecture à
seuil >0,5, chaque point tombant sous 0,5, de façon non-monotone entre 0,003 et
0,30). Sur le même proxy faible déjà utilisé ailleurs dans ce docstring : la
constante de JSON coïncide avec la classe majoritaire de cet échantillon
(9/17=52,9%) ; celle de TOON est la classe minoritaire (8/17=47,1%, pire qu'une
base triviale « toujours prédire la majorité »). Confirme concrètement la réserve
n°2 écrite avant tout test live : le risque « token count ≠ comprehension » n'est
pas hypothétique ici. **Pas shippé, pas recommandé pour ce type malgré le gain de
tokens** — un seul run par format, pas encore répliqué avec une deuxième graine.

### 5.D — Autres axes de la littérature

- **"Lost in the middle"** (Liu et al., 2023) — models attend unevenly across a
  context. **Already run** (2026-09-09,
  `check_positional_bias_within_chunk.py`/`_results.md`, read-only against the
  completed parity run, zero GPU): `chamber_deliberation` position 0 produced a
  deliberative shift **0/495** times across the whole run, while positions 1-4
  did so consistently at 1.6-2.4 % — not the known truncation mode (fallback
  flat and near-zero throughout), a real behavioural asymmetry isolated to
  primacy. `vote_cast` showed a similar-looking gradient but on a small,
  fallback-diluted sample — re-run once the scale-probe journal (5x the volume)
  completes before trusting it. This is now a concrete lead, not a hypothesis:
  worth folding into §3.A's decision-quality work rather than treated as a
  separate literature check.
- **Prompt compression** (LLMLingua) — moderate value; prompts are ~25 % of the
  token budget, so the ceiling is bounded.
- **XML tags for delimitation** rather than nested JSON — models are heavily
  trained on them; cheap to A/B if §5.A finding 1 ever looks binding here.
- **Field order in the schema** — partially explored already (`a_reasoning`
  first); worth completing rather than restarting.

---

## 6. Multi-agents — le projet en est déjà un, mais pas au sens LLM

### 6.A — La distinction qui compte

This simulation is already multi-agent in the **ABM** sense: 500 citizens, each
deciding. It is not multi-agent in the **LLM** sense: each citizen is a
*stateless prompt*, not a persistent agent. Every decision is computed fresh
from the current context, with no thread of identity across ticks.

### 6.B — Les trois couches manquantes (référence : Park et al., 2023, *Generative Agents*)

1. **Mémoire.** Citizens have no recollection. A citizen who petitioned three
   times and was ignored carries nothing forward. `event_salience` is a scalar
   decay — a crude proxy for memory. For a project whose core question is about
   *cumulative* political disaffection, this is a substantive theoretical gap,
   not just an engineering one.
2. **Réflexion.** No synthesis of experience into higher-level belief.
3. **Interaction.** **Citizens never communicate with each other.** Social
   influence is `neighbors_acting` — a *count* of how many neighbours mobilised.
   This is worth stating precisely, because it is the direct answer to the
   original question: *"les comportements des individus entre eux"* is currently
   modelled **entirely through numeric aggregates, never through exchange**.
   That is a defensible, cheap modelling choice — but it should be a stated one,
   because it bounds what the simulation can claim about inter-individual
   dynamics.

### 6.C — Le constat le plus net : la chambre délibérative ne délibère pas

§6bis.3's sortition chamber is the project's deliberative-democracy arm — the
whole control group for "does removing electoral pressure produce more sincere
decisions". But `decide_chamber_deliberation` asks **each member independently**
whether to adjust their own position. No member ever sees another member's
argument. That is parallel introspection, not deliberation.

The literature the chamber invokes (deliberative mini-publics; Fishkin is
already listed in `traceability.md` §7.5 as *prévu*) is *about the exchange* —
modelling it as independent introspection removes the very mechanism under
study. And it is tractable: 75 members is far too many for genuine deliberation,
but mini-publics in the literature run at 5–15. A real multi-agent exchange
inside a small subgroup is affordable.

There is a second reason to want this, from §2: a deliberating agent has
*another agent's argument* in its context — a far richer, more discriminating
input than a scalar. A decision that collapses when asked "should you adjust?"
in a vacuum may not collapse when asked to respond to a specific argument.

### 6.D — Le coût, honnêtement

Multi-agent debate multiplies calls by k. At 35 h per run, that is a non-starter
population-wide, and should not be proposed as one. Where it is genuinely
affordable:

- **the chamber subgroup above** — small n, high theoretical payoff;
- **as a diagnostic on the four collapsed types** — does the collapse break when
  two instances must argue? Small sample, cheap, and it directly probes §2's
  mechanism.

If the full architecture is ever wanted, **Concordia** (DeepMind) is the
reference library for generative agent-based social simulation and is worth
reading before building anything bespoke.

---

## 7. Graphe de dépendances et séquencement

The whole program has one spine, and §5.C changes where it starts: **you cannot
fix a collapse you can only detect with 4–6 hand-built extreme cases.**
Instrumentation comes first.

```
    §5.C  logprobs — la mesure continue de P(act)
      │      (transforme "collapse" d'une inférence en une quantité mesurée à chaque appel)
      │
      ▼
    §3.A  décision quality
      │      (per-citizen seeds · 2-stage split · grammar invariants · base-vs-instruct)
      │
      ├──► §4.A  interprétation théorique enfin défendable
      │           (le président qui concède à une population passive :
      │            vrai résultat, ou artefact d'un type collapsé ?)
      │
      └──► objection qualité de la concurrence levée (30 %→39 %)
             │
             └──► concurrence ré-autorisable (5,84× mesuré)
                    │
                    └──► §4.B  multi-graines, bandes de confiance
                           │
                           └──► §4.C extensions · §6.C chambre délibérante · §3.C fine-tuning (v8)
```

**Hors-spine, sans dépendance, exécutables immédiatement** — including *while*
the flagship runs, precisely because none can perturb it:

- **§3.B.6/7** speculative decoding + prefix-cache tuning (pure throughput);
- **§5.B** float precision + redundant-payload removal (pure prompt size, and it
  compounds: smaller prompts → more headroom → larger chunks → fewer calls);
- **§5.D** "lost in the middle" — per-position accuracy within a chunk, and the
  flagship is generating exactly that data right now, for free.

### Ordre proposé

| # | Travail | Coût | Pourquoi ici |
|---|---|---|---|
| 0 | §5.B précision des flottants + payload redondant · §3.B.6/7 prefix-cache + speculative decoding | heures | Zéro risque, zéro dépendance, gain immédiat sur tous les runs suivants ; se fait pendant que le flagship tourne |
| 1 | **§5.C logprobs — instrumenter la décision binaire** | 1 jour | **Passe avant tout le reste** : rend le collapse mesurable en continu au lieu d'inféré sur 4-6 cas construits à la main |
| 1bis | ~~§5.E TOON en **entrée seulement**, sur `pressure_action`/`candidacy_considered`~~ **FAIT 2026-09-10, puis SHIPPÉ 2026-09-10 (commit `1223c3c`)** | 1 jour | `candidacy_considered` : -6,9%, qualité identique (16/25=16/25) → **shippé** (`build_candidacy_system_prompt_toon`/`_user_prompt_toon`, décision séparée prise après la mesure — cette ligne disait « non shippé », c'était exact à l'écriture et périmé le jour même). `pressure_action` : -44,0%, qualité pas au rendez-vous (bascule de collapse, pas de sensibilité restaurée) → **non shippé**, et toujours pas |
| 2 | ~~§2 base-vs-instruct~~ **FAIT 2026-09-10** (§2bis pour le cadrage, `check_base_vs_instruct_results.md` pour le résultat) — paire bf16 `Qwen3-4B`/`Qwen3-4B-Base` | 1 après-midi GPU | **Hypothèse alignement largement éliminée** : contredite sur `coalition_decision` (collapse identique base et instruct), inutile sur `representative_response` (aucun collapse au 4B instruct), soutenue seulement faiblement et non significativement sur `pressure_action` (+0,089 < barre 0,10 ; p≈0,134). Renvoie vers §3.A.1/§3.A.2 |
| 3 | §3.A.1 per-citizen deterministic sampling | 1-2 jours | Le levier le plus prometteur, compatible avec la reproductibilité |
| 4 | §3.A.3 grammar-level invariants (`blank`/`ranking`) | 1 jour | Supprime une classe d'échec entière au lieu de la réessayer |
| 5 | §3.A.2 décomposition en deux étapes, `pressure_action` d'abord | pré-enregistrement + cycle de validation | Candidat déjà nommé par le projet ; §2 dit qu'il généralise ; §5.C fournit son étage 1 |
| 6 | §6.D multi-agents en diagnostic sur les types collapsés | petit échantillon | Sonde directe du mécanisme §2, coût borné |
| 7 | Re-mesurer les 4 types contre le protocole complet | selon §3 | Seulement une fois qu'il y a quelque chose à mesurer |
| 8 | Rouvrir la concurrence | proof existante à rejouer | L'objection qualité aura changé de valeur |
| 9 | §4.B multi-graines / bandes de confiance | GPU × N | Devient abordable une fois 0+8 acquis |
| 10 | §6.C faire délibérer réellement la chambre | chantier de conception | Extension théorique — après que la mesure et la qualité tiennent |

---

## Verification

- **§3.B.6/7** — measure against the existing harness shape
  (`check_vllm_chunk_size_throughput.py` is the template): tokens/s and
  wall-clock on identical prompts, before/after, plus vLLM's own logged prefix
  hit rate as the second signal. Determinism check: the byte-identical journal
  proof already built (`check_intra_run_concurrency_determinism.py`) re-run at
  `workers=1` must still pass — neither technique may perturb output.
- **§2 base-vs-instruct / §3.A.1 per-citizen seeds** — reuse the collapse-
  signature protocol already established (`plan-adversarial-framing-collapse.md`:
  extreme cases at both poles, 4-6 trials, content verified not just structure).
  Pre-register the criterion before any live call, as this project does.
- **§3.A.3 grammar invariants** — the existing polity suite (1304 tests) plus a
  targeted test that a `blank=1, ranking=[…]` response is now *ungenerable*
  rather than merely rejected.
- **§5.B prompt-size levers** — exact before/after token counts via the
  `count_prompt_tokens` probe already built for `_dynamic_max_tokens` (no
  estimation needed). Behaviour gate: decision output must be **unchanged** on a
  fixed sample when only precision drops — if 2-decimal positions change
  decisions, that is itself a finding worth stopping on, not a regression to
  paper over.
- **§5.C logprobs** — validate against the one decision type with real ground
  truth (`vote_cast`, `simple_rules.build_ranking`): does P(chosen) correlate
  with correctness? A calibration curve there licenses using the same signal on
  types that have no ground truth.
- **§5.E TOON** — two gates, not one. (a) token count before/after via
  `count_prompt_tokens`; (b) **a decision-quality A/B**, since token savings are
  worthless if comprehension drops — run it on `candidacy_considered` first,
  which has real ground truth (`simple_rules.decide_candidacy`) *and* no known
  collapse defect, so a quality regression is attributable to the format rather
  than confounded with an existing failure. Only then consider
  `pressure_action`, and only with §5.C's P(act) baseline captured first.
- **§5.D lost-in-the-middle** — read-only analysis of the flagship journal, no
  GPU: group decisions by position-within-chunk, compare accuracy/act-rate.
  Costs nothing and needs no new run.
- **§6.C/D multi-agent** — cost must be measured before scope: one deliberating
  subgroup of 5, wall-clock per exchange round, extrapolated before anything is
  wired into the tick loop.
- **Anything touching decision quality** — must clear
  `plan-decision-quality-validation.md`'s own bar (≥90 % agreement on unambiguous
  cases for Group A/B types), with the same pre-registration discipline, before
  it counts as resolved.

## Hors scope

- Changing anything about the flagship run currently executing.
- Curating fine-tuning data (blocked by §3.A, deliberately).
- Implementing §4.C / §6.C extensions before the spine lands.
- **Switching the output serialization away from JSON** — §5.A measured why:
  the output is under 5 % of generated tokens, so it is a satisfying-looking
  change with no effect. Revisit only if §5.A's finding-1 (grammar interfering
  with reasoning) ever measures as binding here.
