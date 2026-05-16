# PWA Checklist — Vote Lab

## Prérequis

```bash
# Build production + serve local
cd voter-app
npm run build
npx serve -s build -l 5000
# Ouvrir http://localhost:5000 dans Chrome/Edge
```

---

## 1. Lighthouse PWA

1. Ouvrir Chrome DevTools (`F12`) → onglet **Lighthouse**
2. Sélectionner **Progressive Web App** (et Performance si désiré)
3. Cliquer **Analyze page load**
4. **Attendu** : score PWA ≥ 90 (critères Google : manifest valide, SW enregistré, HTTPS ou localhost, icons déclarées)

> Note : Lighthouse requiert HTTPS en production. Sur `localhost`, certains critères sont exemptés automatiquement.

---

## 2. Installation depuis Chrome / Edge

1. Naviguer vers `http://localhost:5000`
2. Dans Chrome : l'icône **Installer** (⊕) apparaît dans la barre d'adresse
3. Dans Edge : `…` → **Applications** → **Installer ce site en tant qu'application**
4. **Attendu** : une fenêtre standalone s'ouvre avec Vote Lab, sans barre d'adresse du navigateur
5. L'app apparaît dans le menu Démarrer (Windows) ou le Launchpad (Mac)

---

## 3. Mode hors-ligne — Quiz

1. Visiter `http://localhost:5000/quiz` une première fois (met en cache le SW)
2. Ouvrir DevTools → onglet **Network** → activer **Offline**
3. Recharger la page
4. **Attendu** : la page `/quiz` se charge depuis le cache Workbox sans erreur réseau
5. Vérifier que les 20 questions s'affichent correctement

---

## 4. Mode hors-ligne — Régimes internationaux

1. Visiter `http://localhost:5000/regimes-internationaux` en ligne
2. Passer en mode Offline (DevTools → Network)
3. Recharger
4. **Attendu** : page chargée depuis le cache (données statiques, pas d'API)

---

## 5. Mode hors-ligne — Galerie (partiel)

1. Visiter `http://localhost:5000/galerie` en ligne (les scénarios vedette se mettent en cache via StaleWhileRevalidate)
2. Passer en mode Offline
3. Recharger
4. **Attendu** : le banner "Mode hors-ligne" apparaît en haut de page
5. La galerie peut afficher un message d'erreur (les POST/simulations dynamiques ne sont pas cachés — comportement attendu)

---

## 6. Banner hors-ligne

1. DevTools → Network → **Offline**
2. N'importe quelle page de l'app
3. **Attendu** : banner jaune en haut de page :
   > "Mode hors-ligne — certaines simulations peuvent être indisponibles. Les pages Quiz, Régimes internationaux et Galerie fonctionnent sans réseau."
4. Repasser **Online** : le banner disparaît automatiquement

---

## 7. Toast de mise à jour

1. Construire une nouvelle version (`npm run build`)
2. L'app est déjà ouverte dans le navigateur avec l'ancienne version
3. **Attendu** : un toast bleu apparaît en bas à droite :
   > "Vote Lab a été mis à jour. [Recharger]"
4. Cliquer **Recharger** : la page se recharge avec la nouvelle version

> En développement (`npm start`), le SW est désactivé (`devOptions.enabled: false`) — tester uniquement en mode `npm run build + serve`.

---

## 8. DevTools — Application

1. DevTools → onglet **Application** → **Service Workers**
2. **Attendu** : `sw.js` apparaît avec statut "Activated and running"
3. **Application** → **Manifest** : toutes les propriétés correctes (name, icons, display: standalone)
4. **Application** → **Cache Storage** → `workbox-precache-*` : liste les assets statiques pré-cachés

---

## Critères de validation

| Critère | Attendu | Statut |
|---------|---------|--------|
| Lighthouse PWA score | ≥ 90 | ☐ |
| Installation Chrome/Edge | Icône d'install visible | ☐ |
| Quiz hors-ligne | Fonctionne sans réseau | ☐ |
| Régimes internationaux hors-ligne | Fonctionne sans réseau | ☐ |
| Banner hors-ligne | Visible quand offline | ☐ |
| Toast mise à jour | Visible après rebuild | ☐ |
| SW activé | Statut "running" dans DevTools | ☐ |
| Manifest valide | Toutes propriétés présentes | ☐ |
