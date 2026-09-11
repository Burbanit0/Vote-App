# EXP-008 — cosign + provenance SLSA : signer quoi, quand aucune image n'est jamais publiée ?

- **Date** : 2026-09-11 · **Statut** : adopté (périmètre réduit — SBOM signé, pas l'image) · **Coût réel** : ~1h30
- **Verdict en une phrase** : aucun des deux `Dockerfile` (backend, frontend) n'est jamais poussé vers un registre — `audit.yml` les construit avec `load: true` (démon local, jamais publié) et `release.yml` ne construit ni ne pousse la moindre image — donc « signer l'image » au sens OCI natif (`cosign sign`, qui pousse un artefact `.sig` *à côté de l'image dans un registre*) n'a nulle part où signer ; le seul artefact réellement publié par ce job est le SBOM (`upload-artifact`), donc c'est lui qui est signé (`cosign sign-blob`, keyless) + attesté en provenance SLSA (`actions/attest-build-provenance`), les deux mécanismes vérifiés en direct en local (signature + attestation, cas positif et cas de sabotage) avant d'écrire la moindre ligne de YAML CI.

## Hypothèse de départ

L'item du plan (Lot 9, « Signature d'images + provenance SLSA (cosign/sigstore) »)
se présente comme la suite logique du SBOM + Scorecard déjà en place
(`audit.yml`'s job `image-scan`, `scorecard.yml`) : signer les deux images
Docker du repo (`fast_api_voter/Dockerfile.prod`, `voter-app/Dockerfile`) et
attacher une attestation de provenance SLSA. Avant d'écrire quoi que ce soit,
deux questions à trancher par lecture directe, pas par supposition : ces
images sont-elles *réellement* publiées quelque part (une image jamais
publiée ne peut être signée pour personne), et `slsa-framework/
slsa-github-generator` est-il toujours l'outil de référence pour la
provenance SLSA sur GitHub Actions, ou a-t-il été supplanté par l'offre
native de GitHub ?

## Protocole

### 1. Les images sont-elles publiées quelque part ?

`grep -rniE "ghcr|docker/login-action|docker push|registry|docker/build-push-action"`
sur tout `.github/workflows/` : une seule occurrence de
`docker/build-push-action`, dans `audit.yml`'s job `image-scan`, avec
`load: true` — chargé dans le démon Docker local du runner pour que
Trivy/SBOM puissent le scanner, jamais poussé. `release.yml` lu en entier :
bump de version, tag git, `GitHub Release` avec notes — zéro étape de build
ou de push d'image. Conclusion vérifiée, pas supposée : **aucune des deux
images n'existe jamais en dehors du job éphémère qui la construit pour la
scanner.** Signer « l'image » au sens `cosign sign`/`cosign attest` OCI
natif — qui poussent un artefact de signature *dans le même registre que
l'image* — n'a littéralement aucune destination. Le seul artefact que ce job
publie réellement est le SBOM (`actions/upload-artifact`, déjà en place) :
c'est lui qui devient le sujet à signer.

### 2. cosign — toujours l'outil de référence, vérifié en l'installant

`sigstore/cosign-installer` reste l'action officielle. Plutôt que de
supposer la version depuis la mémoire d'entraînement (le risque explicite de
ce genre de tâche), installation directe du binaire officiel en local
(`cosign-linux-amd64`, sans sudo) : **v3.1.3**, `BuildDate: 2026-08-05` — un
projet activement maintenu, release récente au moment de l'investigation.
Signature keyless (OIDC, sans clé privée à gérer) confirmée comme
recommandation standard actuelle, pas une nouveauté à vérifier — le seul
point réellement neuf à trancher était *quel verbe* (`sign` vs `attest`) et
*sur quel sujet*, ce que l'absence de registre (§1) a déjà largement
répondu : `sign-blob`/`attest-blob` (mode fichier, aucun registre requis),
pas `sign`/`attest` (mode image OCI).

Version épinglée à l'identique de la convention du repo (`uses:
owner/repo@<sha complet> # vX.Y.Z`, cf. `audit.yml`) : résolution du tag
`v4.1.2` en commit via l'API GitHub →
`sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2`.

### 3. SLSA provenance — `attest-build-provenance` vs `slsa-github-generator`, vérifié en lisant les deux dépôts

Les deux chemins nommés par la consigne, lus directement (README des deux
dépôts, pas résumés de mémoire) :

- **`slsa-framework/slsa-github-generator`** : son propre README indique
  *« This project is no longer actively maintained. We are working on
  guidance and simpler tooling to replace it »* — dernière release
  **février 2025**, et pointe explicitement vers les *GitHub artifact
  attestations* comme remplacement. Sa garantie la plus forte (SLSA Build
  L3) exige en plus de restructurer le build en workflow réutilisable isolé
  que l'outil contrôle — ce job `image-scan` est un `docker build` ordinaire
  dans un job normal, pas un workflow réutilisable, et la restructuration
  n'est pas justifiée pour un item budgété `M`.
- **`actions/attest-build-provenance`** : activement maintenu, mais son
  propre README précise *« As of version 4,
  `actions/attest-build-provenance` is simply a wrapper on top of
  `actions/attest`… existing applications may continue to use
  `attest-build-provenance`, but new implementations should use
  `actions/attest` instead »*. Comme le besoin ici est exactement de la
  provenance de build (pas un SBOM ou un prédicat sur mesure — les deux
  autres cas d'usage où `actions/attest` généraliste a un avantage réel),
  `attest-build-provenance` reste l'entrée directe et la plus simple pour
  ce cas précis — et génère automatiquement un prédicat SLSA correct depuis
  le contexte réel du run, ce qu'un `cosign attest-blob` à prédicat écrit à
  la main (essayé en local, §4) ne peut qu'approximer.

Verdict : **`actions/attest-build-provenance`**, pas
`slsa-github-generator`. Épinglé à l'identique :
`actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2`.

### 4. Vérifier que ça marche vraiment, en local, avant le YAML

Cette session n'a pas le droit de pousser une branche ni d'ouvrir une PR (le
diff est revu et poussé par l'utilisateur) — le chemin OIDC keyless
spécifique à GitHub Actions (jeton ambiant fourni par le runner) ne peut
donc être exercé pour de vrai qu'au premier run réel après merge. Tout ce
qui ne dépend PAS de cet OIDC ambiant a été vérifié pour de vrai en local,
avec les vrais outils (pas de simulation) :

- `cosign` v3.1.3 et `syft` v1.51.1 (le moteur que `anchore/sbom-action`
  encapsule) installés depuis leurs binaires GitHub officiels, sans sudo.
- **Vraie image construite** : `docker build -f voter-app/Dockerfile .` →
  95,2 MB, succès.
- **Vrai SBOM généré** depuis cette vraie image : `syft scan docker:… -o
  spdx-json=…` → 1 038 650 octets, 71 paquets — pas un fichier de test
  inventé.
- **`cosign sign-blob`** (clé locale — le mode keyless nécessite l'OIDC
  ambiant indisponible ici ; `--tlog-upload=false` pour ne pas polluer le
  vrai journal de transparence Rekor public avec une clé jetable de test) →
  **`cosign verify-blob`** : `Verified OK`, code de sortie 0.
- **Cas négatif, réellement provoqué** : injection d'un faux paquet
  (`evil-backdoor-package`) dans le SBOM signé, puis re-vérification →
  `Error: failed to verify signature… invalid signature`, code de sortie 1.
  Le signal de sabotage détecte vraiment quelque chose, pas supposé.
- **`cosign attest-blob --type slsaprovenance`** (prédicat écrit à la main,
  clé locale) → **`cosign verify-blob-attestation`** : `Verified OK`, code 0.
- **Piège trouvé en vérifiant, pas en lisant la doc** : le premier essai du
  cas négatif (même SBOM saboté) avec `--check-claims=false` a renvoyé
  `Verified OK` — un faux positif silencieux. En retirant ce flag (qui
  désactive en réalité la vérification que le hash du sujet dans
  l'attestation correspond au fichier fourni, pas une option cosmétique
  comme son nom le suggère), la même vérification échoue correctement :
  `Error: provided artifact digests do not match digests in statement`,
  code 1. Sans ce test, le pipeline final aurait pu utiliser ce flag par
  réflexe (il apparaît dans plusieurs exemples de doc pour ignorer des
  contraintes de type GitHub-spécifiques non pertinentes ici) et rester
  vert face à un contenu modifié.

### 5. Câblage CI

Étendu `audit.yml`'s job `image-scan` (déjà le job qui construit + scanne +
génère le SBOM des deux images, non-gating, cron hebdo + push sur
`develop` seulement) plutôt que d'ouvrir un nouveau job : deux étapes après
la génération du SBOM, par entrée de matrice (`backend`/`frontend`) —
`sigstore/cosign-installer` puis `cosign sign-blob --yes --bundle
sbom-${{ matrix.name }}.spdx.json.cosign.bundle sbom-${{ matrix.name
}}.spdx.json` (keyless, jeton OIDC ambiant du job), puis
`actions/attest-build-provenance` avec `subject-path:
sbom-${{ matrix.name }}.spdx.json`. Le bundle cosign rejoint le SBOM dans
l'artefact déjà uploadé.

Permissions : bloc `permissions:` ajouté **au niveau du job** (comme
`scorecard.yml` le fait déjà pour son propre `id-token: write`, plutôt qu'au
niveau du workflow) — remplace entièrement l'héritage du workflow pour ce
job (sémantique GitHub Actions : non additif), donc réécrit `contents:
read`, `security-events: write` et `actions: read` déjà hérités (dont
dépend l'étape d'upload SARIF Trivy existante), plus les deux nouveaux
octrois `id-token: write` (jeton OIDC pour la signature keyless) et
`attestations: write` (API Attestations du repo, utilisée par
`attest-build-provenance`).

Validé avec `actionlint` v1.7.12 (installé en local, sans sudo) sur
`audit.yml` et sur l'ensemble de `.github/workflows/` : aucune erreur.

## Ce que ça a trouvé

- **Aucune des deux images n'est jamais publiée** — la vraie trouvaille de
  cette investigation, qui redéfinit le périmètre de l'item lui-même : pas
  « signer les images », mais « signer ce qui existe réellement en dehors du
  job qui le construit », c'est-à-dire le SBOM.
- **`slsa-framework/slsa-github-generator` est non maintenu depuis ~février
  2025**, confirmé en lisant son propre README, pas supposé depuis la
  mémoire d'entraînement — l'outil que l'énoncé nommait comme un des deux
  chemins principaux est en réalité écarté par ses propres mainteneurs au
  profit de l'option native GitHub.
- **`--check-claims=false` désactive silencieusement la vérification de
  hash du sujet** sur `cosign verify-blob-attestation` — un piège
  méthodologique réel, trouvé en testant le cas négatif plutôt qu'en faisant
  confiance à la doc, et qui aurait produit un pipeline de signature
  toujours vert même face à un contenu modifié si le premier essai n'avait
  pas été remis en question.
- **La mécanique cosign (signature + attestation, positif et sabotage)
  fonctionne exactement comme documenté** une fois le bon flag retiré — zéro
  surprise côté outil lui-même, une fois le vrai piège d'usage écarté.

## Ce que ça a coûté

~1h30 : ~35 min d'investigation (grep exhaustif des workflows pour confirmer
l'absence de publication, lecture des deux README SLSA, résolution des SHA
d'épinglage via l'API GitHub) ; ~15 min d'installation d'outils locaux sans
sudo (cosign, syft, actionlint — trois binaires GitHub Releases) ; ~20 min
de vérification réelle (build d'image, génération SBOM, signature/
vérification, sabotage, attestation, découverte + correction du piège
`--check-claims`) ; ~20 min d'écriture et de validation du YAML
(`actionlint` propre du premier coup grâce à la vérification préalable du
verbe/sujet). Zéro nouvelle dépendance de production ; deux actions
GitHub/sigstore officielles ajoutées à `audit.yml`, toutes deux épinglées au
commit comme le reste du fichier.

## Verdict et pourquoi

**Adopté, périmètre réduit à ce qui existe réellement.** Câblé dans le job
`image-scan` existant (non-gating au sens où il ne devient pas un check
requis — ce job ne tourne déjà pas sur les PR, cron + push `develop`
seulement), mais chaque étape de signature elle-même n'a pas de
`continue-on-error` : un échec de signature est un vrai bug d'infrastructure
(jeton OIDC mal scopé, action cassée), pas de la dette CVE à mettre en
liste d'attente comme le Trivy de ce même job. Le chemin OIDC ambiant
spécifique à GitHub Actions n'a pu être vérifié que structurellement
(`actionlint`, comparaison directe aux exemples officiels actuels) — sa
première exécution réelle aura lieu au premier run après merge sur
`develop`, documenté honnêtement plutôt que présenté comme déjà prouvé de
bout en bout.

Si ce repo commence un jour à publier ses images (GHCR ou autre), les deux
étapes ajoutées ici n'ont pas besoin d'être réécrites : `subject-path`
deviendrait `subject-name`/`subject-digest` sur l'image poussée, et `cosign
sign-blob` deviendrait `cosign sign` sur la référence de registre — le
même job, la même identité OIDC, le même principe, juste un sujet différent.

## Ce que j'en retiens (transférable à un autre projet)

1. **Vérifier que la destination existe avant de signer quoi que ce soit.**
   Tous les tutoriels cosign supposent un `docker push` juste avant l'étape
   de signature — un projet qui ne publie pas d'image doit vérifier cette
   hypothèse contre son propre pipeline réel avant de copier l'exemple, pas
   après.
2. **Un flag qui semble assouplir une vérification annexe peut en réalité
   désactiver la vérification centrale.** `--check-claims=false` a un nom
   qui suggère « ignorer des métadonnées GitHub non pertinentes » ; il
   désactive en fait la correspondance de hash sujet↔fichier, c'est-à-dire
   la seule chose que la commande est censée prouver. Le vérifier avec un
   vrai cas de sabotage, pas seulement un cas positif, est ce qui l'a
   révélé.
3. **Quand l'outil « plus élaboré » est explicitement désavoué par ses
   propres mainteneurs au profit de l'option native de la plateforme, c'est
   généralement tranchant en soi** — pas la peine de comparer les garanties
   sur le papier si l'un des deux candidats est abandonné.
