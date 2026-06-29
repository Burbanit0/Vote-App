# Plan : Simplification du Playground — recentrer sur la thèse

## Contexte

Le playground a accumulé trop de couches sur chaque moment. Le message central — *mêmes bulletins, méthode différente = vainqueur différent* — se perd dans la quantité de contrôles et d'explorations. L'objectif est de retrouver un parcours qui démontre cette thèse en < 2 minutes, tout en gardant le contenu avancé accessible sur une page dédiée.

**Architecture cible** : deux surfaces.
- **`/playground`** — le parcours épuré. Cinq moments, chacun avec les contrôles essentiels. Pas de Collapsibles imbriqués, pas d'explorations lourdes.
- **`/laboratoire`** — une page dédiée regroupant tout le contenu avancé par thème (paradoxes, théorie, mécanismes, réalisme comportemental, vulnérabilité stratégique…). Le playground pointe vers le labo, pas l'inverse.

Aucun composant n'est supprimé — tout est réorganisé entre les deux surfaces.

---

## `/playground` — Le parcours épuré

### Moment ① — Électorat

**Visible :**
1. **Presets** — les 4 boutons "Point de départ" en grille 2×2 (entrée principale, "Polarisé" rentre)
2. **Résumé** — N votants · M candidats · idéologie
3. **Contrôles de base** :
   - Nombre de votants (slider)
   - Seed + re-tirer (une ligne)
   - Idéologie (dropdown : aléatoire / centriste / polarisé) — mode simple
   - Composer (communautés) en version compacte : les modèles deviennent un **dropdown**, le détail des communautés reste accessible mais plus compact

**Retiré → `/laboratoire`** :
- Dimensions (1D/2D/3D) — défaut 2D, verrouillé
- Source des préférences (5 options) — défaut spatial, verrouillé
- Valence (checkbox + sliders)
- Corrélation, bruit de mesure
- Import/export JSON

**Déplacé → Moment ③ Stratégie** :
- Comportement (sincère/stratégique/mixte)
- Participation / abstention (modèle, intensité, note Downs, panel abstention)

**Corrections layout** :
- Presets en grille 2 colonnes
- Panneau gauche utilise toute sa largeur

---

### Moment ② — Méthode

**Visible :**
1. **Multi-select méthodes** — checkboxes, toutes cochées par défaut. On décoche pour exclure. Regroupées par famille (ordinal, cardinal, jugement…)
2. **Assemblée (parlement)** — structure + nombre de sièges

**Retiré → `/laboratoire`** :
- Type de bulletin (8 types) — défaut "information complète" (permet toutes les méthodes)
- Prévisualisation du bulletin, barres expressivité/charge cognitive
- Divergence vote blanc
- Seuil + mode de répartition (assemblée avancée)
- MechanismsAnchor (8 panels) / SystemsAnchor (7 panels)

---

### Moment ③ — Stratégie

**Visible :**
1. **Comportement** (dropdown absorbé de l'Électorat) — sincère / stratégique / mixte
2. **Participation** (absorbée de l'Électorat) — modèle + intensité slider
3. **Vote utile** — verdict compact par méthode : safe ✓ / tempting ⚠ (SincerityModule simplifié, sans les sliders de position ni le scan)
4. **Vote blanc** — impact résumé par méthode

**Retiré → `/laboratoire`** :
- SincerityModule complet (sliders position, bloc de conviction, scan électorat)
- Vulnérabilité Gibbard-Satterthwaite
- Équilibre stratégique
- Manipulation détaillée
- Panel abstention différentielle

---

### Moment ④ — Campagne

**Visible :**
- **CampaignTimeline** — scénario + méthode + scrubber + carte. Tel quel, il compare les méthodes dans le temps

**Retiré → `/laboratoire`** :
- Les 15 panels d'explorations (trajectoire, dynamiques temporelles, réalisme comportemental)

---

### Moment ⑤ — Bilan

**Visible :**
1. **Épreuve du réel** (RealElectionPanel) — **promu en tête**. Burlington 2009 : pluralité/IRV/Condorcet → 3 vainqueurs différents. C'est le climax
2. **Scorecard** — les 4–5 axes principaux avec bandes de confiance
3. **Résultats complets** — tableau de toutes les méthodes et leurs vainqueurs (ResultsAnchor simplifié)

**Retiré → `/laboratoire`** :
- Cadran Lijphart + ValuesPanel (frontière Pareto)
- AnalysisAnchor (6 panels : Monte-Carlo, manipulabilité, volonté collective…)
- TheoryAnchor (9 panels : Sen, jugement, agenda, tyrannie…)

---

## `/laboratoire` — Page dédiée au contenu avancé

### Structure proposée

Page organisée par **thème**, pas par moment. Chaque thème est un Collapsible avec ses panels lazy-loaded (réutilise les composants existants tels quels).

1. **Paramètres avancés de l'électorat**
   - Dimensions de l'espace (1D/2D/3D)
   - Source des préférences (spatial / impartial / mallows / urn / handcrafted)
   - Valence (checkbox + sliders par candidat)
   - Corrélation inter-axes, bruit de mesure
   - Import/export JSON

2. **Le bulletin de vote**
   - Type de bulletin (8 types) avec preview
   - Expressivité, charge cognitive
   - Divergence vote blanc

3. **Analyse stratégique approfondie**
   - SincerityModule complet (position, conviction, scan)
   - Vulnérabilité Gibbard-Satterthwaite
   - Équilibre stratégique
   - Manipulation détaillée
   - Abstention différentielle

4. **Mécanismes & systèmes alternatifs**
   - MechanismsAnchor (jury, NOTA, démocratie liquide, sortition…)
   - SystemsAnchor (coalitions, STV, circonscriptions, charcutage…)

5. **Dynamiques & campagne**
   - CampaignAnchor (trajectoire, sondages, polarisation)
   - TemporalDynamicsAnchor (vote adaptatif, replay, primaires…)
   - BehavioralRealismAnchor (biais, électeur timide, surcharge…)

6. **Théorie & paradoxes du choix social**
   - TheoryAnchor (Sen, jugement, agenda, tyrannie, apportionnement…)
   - AnalysisAnchor (Monte-Carlo, manipulabilité, volonté collective…)

7. **Valeurs & sensibilité**
   - Cadran Lijphart
   - ValuesPanel (frontière Pareto)

### Données

La page `/laboratoire` lit le **même état** que le playground (via `usePlaygroundCtx` ou le store Zustand). L'utilisateur configure une élection dans le playground, puis explore en détail dans le labo. Pas de double state.

---

## Fichiers critiques

| Fichier | Modification |
|---------|-------------|
| `moments/ElectorateMoment.tsx` | Épurer : presets 2×2 → résumé → base uniquement |
| `ElectorateComposer.tsx` | Modèles : boutons → dropdown |
| `moments/MethodMoment.tsx` | Remplacer par multi-select checkboxes |
| `moments/StrategyMoment.tsx` | Absorber comportement + participation, simplifier vote utile/blanc |
| `moments/CampaignMoment.tsx` | Retirer explorations (juste CampaignTimeline) |
| `moments/BilanMoment.tsx` | Promouvoir RealElection, retirer Lijphart/theory/analysis |
| `MomentExplorations.tsx` | Vider (le contenu migre vers /laboratoire) |
| `pages/LaboratoirePage.tsx` | **Nouvelle page** — regroupe tout le contenu avancé par thème |
| `App.tsx` | Ajouter route `/laboratoire` |
| `PlaygroundController.tsx` | Inchangé (state partagé via context/store) |
| `i18n/locales/playground.fr.ts` + `.en.ts` | Nouveaux labels pour le labo |

---

## Séquence de PRs

1. **feat/laboratoire-page** — créer la page `/laboratoire` vide avec la structure thématique + route + lien dans la navbar. Les composants existants sont importés tel quels (lazy)
2. **feat/simplify-electorate** — épurer Électorat : presets 2×2, dropdown modèles, retirer avancé vers labo
3. **feat/simplify-method** — remplacer par multi-select checkboxes, retirer bulletin avancé vers labo
4. **feat/simplify-strategy** — absorber comportement + participation, recentrer vote utile/blanc
5. **feat/simplify-campaign** — retirer explorations (→ labo), garder juste CampaignTimeline
6. **feat/simplify-bilan** — promouvoir RealElection, retirer Lijphart/theory/analysis (→ labo)
7. **feat/simplify-layout** — largeur panneau, polish, vérification globale

Chaque PR est autonome. Le labo est créé en premier pour que les PRs suivantes aient une destination pour le contenu déplacé.

---

## Vérification

- `npx tsc --noEmit` + `npm run lint` + `npx vitest run` après chaque PR
- Playwright : chaque moment du playground simplifié tient dans le viewport
- `/laboratoire` charge tous les panels correctement (lazy-load)
- Aucun composant n'est supprimé, seulement réorganisé
- Parity engine inchangée (aucune modification de `playgroundVoting.ts` ni du backend)
- Les tests qui testent des contrôles déplacés doivent être adaptés (nouveau chemin d'accès)
