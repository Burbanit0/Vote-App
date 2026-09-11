# EXP-002 — Hook `TaskCompleted` pour générer automatiquement le récit d'un run

- **Date** : 2026-09-11 · **Statut** : rejeté (pour `TaskCompleted` — nuance : `SessionStart` adopté comme jambe de confort, voir « Verdict ») · **Coût réel** : ~30-45 min pour la sonde elle-même (estimation imprécise, non chronométrée isolément), à l'intérieur d'un chantier « récit de run » d'environ 4h
- **Verdict en une phrase** : le hook `TaskCompleted` ne se déclenche pas pour une tâche Bash lancée en arrière-plan (`run_in_background: true`) — confirmé comme vrai négatif grâce à un hook témoin qui, lui, s'est déclenché dans la même session — donc la garantie de durabilité a été déplacée hors du système de hooks, dans du Python autonome, et `SessionStart` n'a gardé qu'un rôle de confort.

## Hypothèse de départ

Un run de simulation polity (`fast_api_voter/scripts/run_polity_flagship.py`)
dure 4 à 14h et peut finir de trois façons : succès, crash, interruption
(Ctrl-C, SIGTERM, reboot de la machine). Avant cette expérience, seul un
succès propre produisait quelque chose de lisible : `export_run`/
`viz_export.json` et `metrics.json` étaient écrits **après** le
`try`/`finally` entourant `run_simulation` dans `run_polity_flagship.py` —
vérifié sur le commit précédent (`658b3e7^`) : le `finally` ne fait que du
nettoyage de logger, `export_run` et l'écriture de `metrics.json` sont des
appels de code normal placés après le bloc, donc toute exception, tout
`KeyboardInterrupt` et tout SIGTERM les sautait entièrement. Constat mesuré
sur disque à ce moment-là (cité dans le message du commit `658b3e7`) :
seulement 3 des 8 répertoires de run flagship contenaient un
`viz_export.json`. Le même jour, un reboot de l'hôte avait tué un run à
07:14.

L'hypothèse testée : un hook `TaskCompleted` de Claude Code pourrait générer
automatiquement le récit d'un run dès qu'il se termine — y compris quand il
crashe ou est interrompu — sans dépendre de la mémoire d'un humain pour
lancer la commande de narration. Cette hypothèse était posée en territoire
explicitement non documenté : on ne savait pas si `TaskCompleted` se
déclenche pour une tâche Bash lancée avec `run_in_background: true`, la
forme de son payload était inconnue, et la documentation de Claude Code
semblait contredire la skill `/update-config` sur la question de savoir si
les hooks de type `agent` fonctionnent sur des événements non liés à un
outil.

## Protocole

Le test sentinelle que prescrit la skill `/update-config` :

1. Brancher un hook `TaskCompleted` sur un script qui ajoute `date` + le JSON
   reçu sur stdin à un fichier sentinelle dans `/tmp`.
2. Lancer une tâche Bash triviale en arrière-plan (`run_in_background: true`).
3. Inspecter le fichier sentinelle.
4. **Un témoin (control), point décisif du protocole** : un hook
   `PostToolUse` ajouté dans la **même** édition de `.claude/settings.json`,
   pour prouver que les nouveaux hooks se chargeaient bien dans cette
   session. Sans ce témoin, un hook qui ne se déclenche pas est
   indiscernable d'une configuration jamais chargée — un piège documenté par
   ailleurs pour le settings-watcher de Claude Code, qui ne surveille
   `.claude/` que si un fichier de settings y existait déjà au démarrage de
   la session.

Le fichier sentinelle lui-même vivait dans `/tmp` et a disparu depuis — il
n'est donc pas citable directement. Le résultat est en revanche corroboré
par deux artefacts écrits dans le dépôt le jour même, indépendamment l'un de
l'autre : le message du commit `0454010` et le docstring du hook livré dans
ce même commit (`.claude/hooks/notify_run_digest.py`), qui rapportent tous
les deux la même conclusion avec la même méthode de contrôle.

## Ce que ça a trouvé

**`TaskCompleted` ne s'est pas déclenché** pour la tâche Bash en arrière-plan.
**Le hook témoin `PostToolUse` s'est déclenché, lui, dans la même session** —
c'est donc un vrai négatif, pas un artefact de configuration périmée. Cité
tel quel dans le message du commit `0454010` :

> TaskCompleted was tested first and does NOT fire for run_in_background Bash
> tasks. That is a real negative, not a stale-config artifact: a control
> PostToolUse hook added in the same edit DID fire in the same session, so
> new hooks were loading.

Le docstring de `.claude/hooks/notify_run_digest.py` (85 lignes, vérifiées
par comptage) reformule la même mesure et ajoute une hypothèse prudente sur
la cause : « TaskCompleted appears to be tied to the task tool, not to
backgrounded shell commands » — présentée comme une observation, pas comme
un fait documenté par ailleurs.

**Conséquence sur la conception**, qui est le cœur de l'intérêt de cette
expérience : la garantie de durabilité a été déplacée **hors** du système de
hooks, dans du Python maîtrisé qui fonctionne sans aucune session Claude
vivante :

- `api/domain/polity/run_digest.py` (introduit par `658b3e7`) : écrit un
  `digest.json` à **chaque** fin de run.
- Dans `run_polity_flagship.py`, le `try`/`finally` autour de
  `run_simulation` est devenu un `try`/`except BaseException` (vérifié dans
  le diff de `658b3e7`), avec une classe `_Terminated(BaseException)` levée
  par un handler SIGTERM installé dans `main()`
  (`signal.signal(signal.SIGTERM, _raise_terminated)`) — parce que la
  disposition par défaut de SIGTERM tue le processus sans exécuter aucun
  `finally`, exactement ce qui avait fait disparaître les traces du run tué
  par le reboot de 07:14.

Le hook `TaskCompleted` a donc été abandonné, et `SessionStart` (dont
l'injection de stdout dans le contexte du modèle est, elle, documentée) a
pris un rôle de simple confort : au démarrage de session, il liste les runs
qui ont un `digest.json` sans `TIMELINE.md`, ou avec un `TIMELINE.md` plus
ancien que le digest (`.claude/hooks/notify_run_digest.py`, logique
`pending_narratives`). Vérifié directement dans `.claude/settings.json` : il
n'existe **aucune** entrée `TaskCompleted` — seulement `PreToolUse`,
`PostToolUse` et `SessionStart`. C'est l'artefact tangible du résultat
négatif. `/log-run` reste le repli toujours disponible, indépendant du
hook.

**Également rejetés dans la même passe, explicitement**, selon le même
message de commit (`0454010`) :

- `Stop` — se déclenche à chaque tour, jugé beaucoup trop bruyant pour cet
  usage.
- Appeler `claude -p` en sous-processus — non documenté, dépense non
  surveillée.
- Un hook de type `agent` sur un événement non lié à un outil — doc de
  Claude Code et skill `/update-config` se contredisent sur ce point, donc
  jugé non porteur sans sonde supplémentaire.

**Confirmation a posteriori, 2026-09-11 — observation opportuniste, pas une
mesure prévue par le protocole initial.** Pendant la rédaction même de ce
carnet, un run Stage 3 en cours (`scaleprobe-8y-p500-v2-postfix`) s'est
révélé bloqué : 1,92 s de CPU consommée en 1h59 d'horloge murale, une socket
établie mais inerte vers un vLLM par ailleurs parfaitement sain (répondant
en 4 ms), largement au-delà de son propre timeout (600 s × 3 tentatives).
Aucune exception n'a été levée, donc aucun repli ne s'est déclenché et aucun
crash n'a été enregistré — le run avait cessé d'être un run tout en ayant
l'air vivant. Il a été arrêté par SIGTERM ; la jambe Python a fonctionné
exactement comme conçu : `digest.json` écrit avec `"outcome": "interrupted"`,
`"error": {"type": "_Terminated", "message": "received signal 15"}`, 7447,8 s
écoulées, 16/32 ticks journalisés, checkpoint au tick 15, 4624 événements, 0
ligne malformée — vérifié directement dans
`fast_api_voter/scripts/flagship_runs/scaleprobe-8y-p500-v2-postfix/run/scaleprobe-8y-p500-v2-postfix/digest.json`.

C'est la première mise à l'épreuve en conditions réelles de la conception
issue de cette expérience, et elle en valide le point central d'une manière
que le protocole initial n'avait pas anticipée : un hook `TaskCompleted`
n'aurait de toute façon rien produit ici, puisque la tâche ne s'est jamais
*terminée* — elle s'est figée, socket ouverte, sans exception et sans fin
observable par un mécanisme qui n'écoute que les fins.

## Ce que ça a coûté

La sonde elle-même (les 4 étapes du protocole) est modeste — de l'ordre de
30 à 45 minutes — mais ce chiffre est imprécis : il n'a pas été chronométré
isolément, il est situé à l'intérieur d'un chantier « récit de run » plus
large d'environ 4h (digest, agent `run-narrator`, commande `/log-run`, hook
`SessionStart`). Aucun temps CI ajouté : le hook adopté tourne au démarrage
de session locale, ce n'est pas une porte de CI.

Coût de maintenance résiduel, mesuré directement dans le dépôt : un script
de hook de 85 lignes (`.claude/hooks/notify_run_digest.py`, compté par
`wc -l`) et une entrée `SessionStart` de sept lignes dans
`.claude/settings.json`. Le hook a été « vérifié contre les trois états »
(complété/crashé/interrompu) selon le message du commit `0454010` — aucun
faux positif rapporté sur cette vérification. Aucun coût d'installation
au-delà de la configuration déjà présente (le mécanisme de hooks lui-même
était déjà utilisé pour `engineParity.json`, cf. `CLAUDE.md`).

## Verdict et pourquoi

**`TaskCompleted` rejeté** pour cet usage : le résultat est un vrai négatif,
confirmé par un témoin déclenché dans la même session — pas une
configuration jamais chargée. **`SessionStart` adopté**, mais explicitement
rétrogradé au rang de confort, pas de garantie : il ne fait que rappeler
qu'une histoire reste à écrire, jamais qu'il l'écrit lui-même.

La vraie garantie a été placée délibérément **hors** du système de hooks,
dans du Python que l'équipe contrôle entièrement
(`run_digest.py` + `except BaseException` + handler SIGTERM). C'est aussi,
et ce n'est pas un hasard, la seule conception qui couvre le cas qui avait
motivé tout le chantier : quand la machine reboote, aucun hook — quel qu'il
soit — ne peut se déclencher, parce qu'aucune session Claude n'est vivante
pour l'exécuter. Un hook a structurellement besoin d'un processus hôte en
vie ; une garantie de durabilité ne peut donc pas reposer dessus seul.

## Ce que j'en retiens (transférable à un autre projet)

1. **Quand le comportement d'un événement de hook (ou de tout déclencheur
   d'automatisation tiers) n'est pas documenté, sonde-le avec une sentinelle
   ET un témoin (control) déclenché dans la même édition de configuration.**
   Un hook silencieux qui ne se déclenche pas est indiscernable d'une
   configuration jamais chargée. Sans témoin, on conclut faux dans les deux
   sens possibles : un vrai négatif prend l'apparence d'un bug de
   configuration, et un bug de configuration prend l'apparence d'un vrai
   négatif.
2. **Ne jamais faire reposer une garantie de durabilité sur un déclencheur
   d'automatisation non documenté et dépendant d'un processus vivant.**
   Place la garantie dans du code que tu contrôles et qui s'exécute sans
   dépendance externe ; laisse le hook (ou toute automatisation d'agent)
   n'être qu'une couche de confort par-dessus. C'est souvent, comme ici,
   aussi la seule conception qui couvre le cas limite qui avait motivé le
   chantier au départ — un hôte qui s'éteint sans prévenir, où rien de ce
   qui dépend d'un processus vivant ne peut plus jouer son rôle. Plus
   généralement : **un déclencheur fondé sur la fin d'une tâche ne couvre
   structurellement pas le cas où la tâche ne se termine jamais** — un
   blocage silencieux, socket ouverte, zéro exception, zéro crash — alors
   qu'un artefact écrit par le processus lui-même, ou par le signal qui
   l'interrompt de force, couvre ce cas-là aussi bien que les autres.
