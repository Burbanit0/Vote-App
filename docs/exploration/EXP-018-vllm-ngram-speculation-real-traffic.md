# EXP-018 — Spéculation n-gram sur vLLM : la spéculation gagne-t-elle sa place sur du trafic concurrent réel ?

- **Date** : 2026-09-20 (mesure) · **Statut** : rejeté (spéculation retirée) ; le passage de vLLM 0.28.0 à 0.29.0 associé est adopté comme effet de bord, ce n'est pas la question posée · **Coût réel** : ~50 min de calcul GPU mesuré et documenté dans le protocole (voir « Ce que ça a coûté ») ; durée de séance humaine non isolable au-delà de cette fenêtre · **Coût en tokens** : ~559 k tok de sortie + ~3,59 M tok nouvellement mis en cache sur 389 tours modèle datés du 2026-09-20 (session `799990d2`, lignes 21025-22393 du transcript ; cache-read cumulé ~169 M tok — non marginal, même réserve que EXP-016 : c'est le contexte de séance renvoyé à chaque tour, pas un coût propre à cette expérience) ; `/cost` non relevé en séance
- **Verdict en une phrase** : la spéculation n-gram, mesurée ~2,5× plus rapide sur des fixtures synthétiques trois jours plus tôt, ne réduit le temps mur d'aucune fraction mesurable sur du trafic de simulation réel à 12 workers concurrents, et ralentit le débit par appel de 24 à 28 % sur deux types de décision sur trois — retirée.

## Hypothèse de départ

Le stack LLM de Vote-App (moteur de décision de Polity) sert des requêtes à un modèle Qwen3-8B via vLLM. La spéculation n-gram avait été activée le 2026-09-10 sur la seule base de deux fixtures synthétiques (`check_vllm_speculative_decoding_results.md`) : environ 2,5× plus rapide sur une fixture de délibération de chambre uniforme, neutre sur une fixture `vote_cast` variée. Ce carnet documente l'expérience du 2026-09-20 qui pose explicitement, avant de lancer quoi que ce soit, la question que ces fixtures synthétiques ne pouvaient pas trancher : **la spéculation gagne-t-elle sa place sur du trafic réel (12 workers concurrents, la config de simulation de production), et la version 0.29.0 de vLLM (alors disponible) est-elle une amélioration en soi ?** Rien ne présupposait la réponse : la fixture synthétique donnait un signal positif fort, et le protocole a été construit pour le confirmer ou l'infirmer sur un trafic représentatif plutôt que de généraliser depuis la fixture.

## Protocole

Mesuré le 2026-09-20 avec `scripts/check_vllm_speculation_ab.py` et le harnais bake-off (`scripts/bakeoff_report.py`, `scripts/run_bakeoff.py`), depuis `fast_api_voter/`.

1. **A/B en charge concurrente** — config flagship (population 100, 30 sièges, seed 1, 2 ans simulés, 12 workers relaxés, une élection), un échauffement non chronométré d'un an avant chaque bras, puis `python scripts/check_vllm_speculation_ab.py <label> 2 <out_dir>` :
   - A1/A2 : `vllm/vllm-openai:v0.28.0` + n-gram (l'ancien pin, deux répétitions)
   - B1 : 0.28.0, spéculation retirée (« Using V2 Model Runner »)
   - C1 : 0.29.0, spéculation retirée
   - R1 : 0.29.0, sans spéculation, après trois redémarrages propres
2. **Bake-off séquentiel** — la banque figée complète (174 cas, `case_bank.jsonl`), une requête à la fois, comparée à la session de contrôle déjà enregistrée `qwen3-8b-awq-control` (0.28.0 + spéculation) via `bakeoff_report.py --control qwen3-8b-awq-control`.
3. **Reproductibilité (OBS-020)** — 3 paires de runs strictes (4 ans, 100 citoyens, 1 worker, même seed) sur 0.29.0 sans spéculation, comparées aux paires déjà enregistrées avec spéculation.
4. **Vérifications de non-régression** sur le nouveau setup : `check_llm_stack_versions.py`, `check_thinking_token_budget.py`, `check_vllm_batching_determinism.py`, trois redémarrages `compose restart` consécutifs, `test_polity_vllm_live.py`, re-run du 2 ans/12 workers.

Rejouable à l'identique avec les mêmes scripts sur un serveur vLLM 0.28.0/0.29.0 démarré avec/sans `--speculative-config`.

## Ce que ça a trouvé

**Aucun gain mesurable en charge concurrente (celle qui compte pour la production) :** A1 323 s, A2 352 s (0.28.0 + n-gram) contre B1 332 s (0.28.0 sans spéculation) et C1 310 s / R1 299 s (0.29.0 sans spéculation) — les deux runs *avec* spéculation diffèrent déjà de 9 % entre eux, autant que l'écart entre bras. **Débit par appel, avec 12 requêtes en vol : spéculation 28 % plus lente sur `pressure_action`, 24 % sur `vote_cast`, 4 % sur `chamber_deliberation` ; 9 % plus rapide sur `representative_response`** (bras batch-bound par construction, la spéculation n'aide pas quand le serveur sert déjà 12 flux).

**Gain net réel, mais seulement en séquentiel (le cas que la production ne fait jamais)** : sur la banque figée envoyée un cas à la fois, sans spéculation le débit décodé tombe à un plateau de 113-131 tok/s quelle que soit la famille de contenu ; avec spéculation, du JSON structuré répétitif (candidature, réactions) monte à 300-376 tok/s — un gain moyen ×1,43 sur l'ensemble de la banque (15,9 min contre 22,7 min), concentré sur les familles les plus répétitives.

**Coût qualité, sans lien direct avec la spéculation elle-même** : 160/174 réponses de la banque figée identiques entre 0.28.0+spéc et 0.29.0 sans spéc ; les 14 qui diffèrent sont toutes dans les familles à réflexion longue (`positioning_poles` 9/10, `chamber_poles` 3/10) ou un cas de réponse frontière, imputables au changement de version de serveur, pas à la spéculation retirée.

**Reproductibilité inchangée par cette décision, mais dégradée par autre chose** : sur 0.29.0 sans spéculation, seulement 1 des 3 paires même-graine est identique octet pour octet (2 diffèrent, dont une sur 15/312 lignes), contre paires identiques avec spéculation activée (0.28.0 et 0.29.0). Cause suspectée mais non tranchée : le Model Runner V2, qui ne s'engage que quand la spéculation est désactivée — ouvert comme OBS-020, pas résolu par cette expérience.

## Ce que ça a coûté

Mesuré directement dans le résultat (`check_vllm_speculation_ab_results.md`) : A/B concurrente (5 runs, 2 ans/100 citoyens/12 workers) ≈ 1616 s (27 min) de calcul GPU cumulé ; session bake-off séquentielle nouvelle (174 cas) 22,7 min (1362 s) — la session de contrôle 0.28.0 était déjà enregistrée, pas rejouée ce jour-là. Total machine documenté et chronométré : **≈ 50 min**. Les trois redémarrages consécutifs et la suite `test_polity_vllm_live.py` ont été exécutés mais leur durée n'est pas chiffrée dans ce document précis (elle l'est dans le document du bump suivant, 0.30.0, qui donne 15 min 41 s pour cette même suite — pas rejoué ici, cité seulement comme ordre de grandeur voisin).

Aucun temps CI ajouté : script de vérification manuelle avant décision, jamais branché sur une porte CI. Pas de faux positif rencontré — le protocole a plutôt trouvé un faux signal *antérieur* (la fixture synthétique du 2026-09-10, qui ne s'est pas généralisé).

Coût en tokens : voir l'en-tête — estimation de transcript isolée sur la fenêtre calendaire du 2026-09-20 dans une session par ailleurs longue (13 au 23 septembre), donc probablement légèrement gonflée par du travail voisin non lié à cette expérience précise dans ce même intervalle d'une journée ; pas de découpage plus fin tenté.

## Verdict et pourquoi

**Rejeté.** Le signal positif de la fixture synthétique (×2,5) ne s'est pas généralisé au trafic réel de simulation, qui est justement le cas d'usage de production (12 workers concurrents) — pire, la spéculation y coûte du débit par appel sur deux types de décision majoritaires (`vote_cast`, `pressure_action`). Le seul régime où elle gagne (session séquentielle, une requête à la fois) n'est pas un mode que Vote-App/Polity utilise en production. `--speculative-config` est retiré ; `vllm/vllm-openai:v0.29.0` est adopté séparément (aucune régression détectée, la dernière version stable au moment du bump), acceptant deux coûts documentés : les sessions séquentielles (bake-off, bancs de comparaison de modèles) coûteront environ 43 % de temps GPU en plus sans spéculation, et la reproductibilité même-graine reste incertaine (OBS-020, cause non éclaircie par cette expérience).

## Ce que j'en retiens (transférable à un autre projet)

1. **Un gain mesuré sur une fixture synthétique construite pour isoler un mécanisme (ici : contenu très répétitif, une requête à la fois) ne dit rien sur son comportement en charge concurrente réelle** — les deux régimes sollicitent des ressources différentes (débit d'un flux isolé vs partage d'un batch GPU), et un gain dans l'un peut devenir un coût dans l'autre. Avant d'adopter une optimisation de service depuis un micro-benchmark, la rejouer sous la charge et la concurrence réelles de l'usage visé, pas une extrapolation.
2. **Une même intervention peut être un gain net dans un régime d'usage et une régression dans un autre, sans que l'un annule l'autre** : ici, la spéculation reste une vraie option future utile si ce projet fait un jour tourner des sessions séquentielles à fort volume (elle ne l'a pas retenue seulement parce que ce n'est pas son usage actuel). Documenter le compromis par régime plutôt que de rendre un verdict binaire évite de refermer une porte qui pourrait rouvrir avec un usage différent.
3. **Chronométrer un run de comparaison unique par bras ne sépare pas un vrai effet du bruit** : les deux runs *du même bras* (A1/A2, avec spéculation) différaient déjà de 9 % l'un de l'autre — un écart de cet ordre entre bras différents n'aurait rien prouvé sans cette référence de bruit intra-bras mesurée en même temps.
