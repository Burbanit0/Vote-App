# PLAN — Accessibilité des notions (enrichissement UX)

Plan d'exécution auto-suffisant. Une branche `feat/*` + une PR par phase.
Écrit pour être exécuté phase par phase (par moi ou un autre agent), sans
contexte préalable. Fichier local, hors repo (gitignoré).

## Mission

Vote-App fait déjà **ressentir** les notions de théorie du vote (sa force). Mais
le coût d'entrée vers ce ressenti est trop élevé pour un néophyte : le jargon
(Condorcet, IRV, centre squeeze, VSE, valence, dépouillement…) n'a aucun point
de consultation, l'entrée se fait par mécanisme et jamais par curiosité, et les
résultats se donnent en chiffres sans être *nommés*.

Ce plan abaisse ce coût **sans ajouter de mur de texte** : chaque phase reste
dans le registre « je manipule, je ressens » ; le texte reste **contextuel et à
la demande** (survol/clic), jamais une page qu'on lit d'abord.

## Cibles (priorité)

1. **Citoyen curieux** (a voté, zéro théorie) — décroche sur le jargon → Phases 1, 4.
2. **Le faire *comprendre*** (voit le résultat, pas le pourquoi) → Phases 2, 3.
3. Journaliste / connaisseur — déjà servis (élections réelles, Laboratoire).

## Règles du jeu (CLAUDE.md fait foi)

- Une branche `feat/*` par phase **depuis `develop`**, une PR, merge `--no-ff`.
- Portes : `npx tsc --noEmit` · `npx vitest run` · `npm run lint` (0 erreur) ·
  `npx prettier --config .prettierrc --write <files>` · `npm run build`.
- i18n : `playground.fr.ts` source de vérité ET type ; `.en.ts` miroir
  clé-pour-clé (tsc l'impose). **Les tests tournent en anglais** — asserter EN.
- **Pas de nouvelle dépendance. Pas de nouvelle destination de navigation** →
  ancres du Laboratoire, modales, ou inline. **Ne pas dénaturer le playground.**
- Tout est **côté client, au-dessus de `ruleWinnerFromRanks`** → aucun impact
  parité (ne jamais toucher la logique des règles).
- Logique = **lib pure + test unitaire + un composant mince** (le split maison).
- Auteur des commits = forme `noreply` ; `Co-Authored-By: Claude Opus 4.8`.

## À réutiliser (ne rien réinventer — grep avant de construire)

| Besoin | Existe déjà |
|---|---|
| Affordance ⓘ (popover a11y) | `components/playground/InfoPopover.tsx` (+ `InfoLine`) |
| Registre bilingue typé | `lib/methodInfo.ts`, `lib/scenarioInfo.ts` (le pattern) |
| Dépouillement / vainqueur autoritaire | `lib/voteTrace.ts` (`VoteTrace`, `buildTraceFromBallots`, `FAMILY_OF`) |
| Révélation animée | `components/playground/FlipReveal.tsx` (`{modeKey, caption, children}`) |
| Histoires + deep-link | `lib/stories.ts` (`STORIES`, `?story=`), `StoryPlayer.tsx` |
| Analytics | `lib/analytics.ts` (`track(name, props)`, 10 événements existants) |
| Persistance de préférence | `useUIStore` (thème `votelab_theme`, `initUITheme()`) |
| Quiz **orphelin** à ranimer | `data/quizQuestions.ts` (plus référencé nulle part) |
| Page play (tunnel) | `pages/AVousDeJouerPage.tsx` |

Événements analytics existants : `moment_changed`, `rule_changed`,
`preset_applied`, `mode_toggled`, `story_started`, `story_completed`,
`real_election_selected`, `campaign_scenario_selected`, `lab_compare_opened`,
`lab_fiche_opened`. **Aucun sur la page play.**

---

## Phase 0 — Instrumenter le tunnel *(mesurer avant d'élargir)*  — branch `feat/play-analytics`

**But** : savoir où les vrais visiteurs décrochent avant de sur-investir.

**Faire** : `track()` sur le tunnel de « À vous de jouer » — `play_ballot_cast`
(langage, posture), `play_depouille_played`, `play_register_opened`,
`play_weight_explored`. Même pattern que les 10 événements existants.

**Tests** : n/a lourd ; vérifier qu'aucune donnée personnelle ne part.

**Fini quand** : événements visibles dans Umami (dev), zéro PII, portes vertes.
*Retour différé (il faut du trafic) — on instrumente maintenant, on lit dans ~1
semaine. Ne bloque aucune autre phase.*

## Phase 1 — Lexique interactif « voir en action » 🟢 *(pièce maîtresse)* — branch `feat/glossary-lexique`

**But** : aucun terme ne laisse un néophyte en plan ; chaque terme mène à la
**démo vivante** qui le montre.

**Faire** :
- `lib/glossary.ts` — registre bilingue (~25 entrées) façon `methodInfo.ts` :
  `{ short: une ligne, plain: une phrase, seeInAction?: {kind:'story'|'preset'|'real'|'route', ref} }`.
  Termes : Condorcet, IRV, spoiler, centre squeeze, VSE, valence, dépouillement,
  Gallagher, quota, vote utile, monotonie, bulletin/langage, approbation, note,
  points, Borda, Copeland, minimax, Schulze, majorité relative, second tour,
  paradoxe de Condorcet, abstention, pivot/poids…
- `<Term id="condorcet">Condorcet</Term>` — composant mince qui enrobe un mot
  d'un `InfoPopover` (short + plain + bouton **« voir en action »** qui deep-linke
  via `?story=`, un preset playground, une élection réelle, ou une route).
  Événement `term_opened` (id).
- Index consultable (recherche) monté en **ancre du Laboratoire** ou modale —
  **pas** de nouvelle nav.

**Tests** : intégrité du registre (chaque `seeInAction.ref` résout vers un vrai
`STORIES` id / preset / route ; deux locales — tsc l'impose). Composant : ⓘ
ouvre, « voir en action » navigue. Asserter EN.

**Fini quand** : ~25 termes, `<Term>` posé sur les surfaces les plus denses, les
deep-links atterrissent sur la bonne démo, portes vertes.

## Phase 2 — « Pourquoi ce gagnant ? » 🟢 — branch `feat/explain-winner`

**But** : chaque résultat dit, en une phrase claire, *pourquoi* ce candidat gagne.

**Faire** : `lib/explainWinner.ts` — fonction **pure du `VoteTrace`** :
`switch(trace.family)` → *count* « le plus de premiers choix » · *elim* « a
résisté aux reports quand les autres tombaient » · *pairwise* « bat chaque rival
en duel » · *twophase* « l'emporte au second tour » · *lottery* « tiré au sort,
pondéré par les voix » — nommant vainqueur + dauphin depuis la dernière frame.
Bilingue par clés i18n à paramètres. Rendu sous le dépouillement (page play) et
dans le Bilan.

**Tests** : une assertion par famille (bon vainqueur + bon mécanisme), EN. Pure.

**Fini quand** : une phrase juste pour chaque règle/famille, portes vertes.

## Phase 3 — « Devine d'abord » 🟡 — branch `feat/predict-reveal`

**But** : transformer le spectateur en parieur ; l'écart prédiction↔réel *est* la
leçon.

**Faire** : étape de pari **optionnelle** avant révélation (page play avant
dépouillement ; histoires ; élections réelles) : « Qui gagne, selon toi ? » →
tap candidat → révélation (`FlipReveal`) → juste/faux + le « pourquoi » (Phase
2). Ranimer `quizQuestions.ts` comme contenu de départ (sinon le jeter et
n'utiliser que la prédiction en direct). Événement `guess_made`.

**Tests** : pari enregistré, juste/faux calculé contre le vainqueur **du moteur**
(jamais re-dérivé), désactivé par défaut. EN.

**Fini quand** : pari disponible et scoré sur au moins page play + histoires,
portes vertes.

## Phase 4 — Mode « sans jargon » 🟡 — branch `feat/plain-language-mode`

**But** : un niveau de lecture ; libellés simples pour le néophyte, techniques
pour l'expert.

**Faire** : interrupteur global (persisté comme le thème via `useUIStore`) qui
**échange un jeu ciblé de libellés** (« Condorcet » → « le préféré en duel ») via
des clés `plain.*`. Portée bornée : noms de méthodes + libellés de
moments/métriques, **pas tout** (YAGNI). Défaut = technique (l'app enseigne le
vrai vocabulaire ; le mode simple est l'assistance).

**Tests** : le toggle échange un libellé connu, persiste, défaut technique. EN.

**Fini quand** : toggle opérant sur le set ciblé, persistant, portes vertes.

## Phase 5 — Entrée par question de curiosité 🟡 — branch `feat/curiosity-questions`

**But** : entrer par ce qu'on se demande, pas par le mécanisme.

**Faire** : index de ~6 questions (homepage + affordance d'en-tête) → carte
`question → {storyId | route}` réutilisant `STORIES` + `?story=`. Ex. : « Pourquoi
mon vote ne "sert à rien" ? », « Comment un perdant fait-il gagner un autre ? ».

**Tests** : chaque question mappe un vrai id/route ; deux locales.

**Fini quand** : les questions routent vers la bonne démo, portes vertes.

## Phase 6 *(optionnel)* — Analogies + micro-animations 🔵 — branch `feat/analogies-motion`

Cartes « comme dans la vie » par méthode (champ `analogy` ajouté à
`methodInfo.ts`) + micro-animations de mécanisme réutilisables (report IRV, duels
Condorcet). En dernier, polish.

---

## Ordre d'exécution

**0** en parallèle (instrumenter maintenant, lire plus tard). **1 → 2 → 3** = la
colonne vertébrale (chercher un mot → narrer le résultat → le faire prédire).
**4** et **5** indépendantes, à intercaler. **6** en dernier.

Définition de « fini » par phase (toutes) : portes vertes, FR+EN synchro, tests
en EN, zéro dépendance nouvelle, aucune logique de règle touchée, PR contre
`develop` liant la phase de ce plan.

## Statut

- Phase 0 — feat/play-analytics — ✅ MERGED (PR #83)
- Phase 1 — feat/glossary-lexique — ✅ MERGED (PR #84) — 26 termes, <Term> inline + LexiquePanel (?exp=lexique), term_opened event
- Phase 2 — feat/explain-winner — ✅ MERGED (PR #85) — explainWinner (pure, par famille) + WinnerExplanation sous le dépouillement ; Bilan volontairement laissé (vue multi-règles, pas de trace unique)
- Phase 3 — feat/predict-reveal — ✅ MERGED (PR #86) — pari saisi dans l'isoloir (non-peekable), badge juste/faux vs trace.winner, event guess_made ; quiz orphelin PAS ranimé (trivia FR MCQ, mauvaise forme) ; stories/élections réelles reportées
- Phase 4 — feat/plain-language-mode — ✅ MERGED (PR #88) — flag useUIStore votelab_plain + usePlainLanguage ; seam useVotingLabels → rulesPlain (borné ~10 méthodes, fallback technique) ; toggle navbar « Sans jargon » ; défaut OFF
- Phase 5 — feat/curiosity-questions — ✅ MERGED (PR #87) — 6 questions sur /decouvrir → stories
- Phase 6 — feat/analogies-motion — ✅ MERGED (PR #89) — METHOD_ANALOGY (« comme dans la vie », ~10 méthodes) dans le popover MethodInfo ; micro-animations NON refaites (déjà couvertes par ReplayStage/AnimatedVoteCount/FlipReveal, reduced-motion respecté)

**PLAN COMPLET — les 6 phases (0-6) mergées le 2026-07-27, PRs #83-89.**
