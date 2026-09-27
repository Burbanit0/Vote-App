# Mémoire de l'agent de code — copie versionnée

Ce répertoire est une copie de la mémoire persistante de Claude Code pour ce
projet. En fonctionnement normal elle vit **hors du dépôt**, dans
`~/.claude/projects/<slug>/memory/`, ce qui veut dire qu'elle n'existe que sur
la machine qui l'a écrite. Elle est versionnée ici pour la même raison que
`docs/adr/` et `docs/journal/` : c'est du contexte de décision que rien
d'autre ne porte — l'historique des lots v4→v7, l'enquête sur l'effondrement
de `pressure_action`, les conventions de travail (branche `polity` comme base
de PR, méthode de diagnostic des troncatures Mode A).

`MEMORY.md` est l'index chargé au début de chaque session ; les autres
fichiers sont un fait par fichier.

## Restaurer sur une autre machine

Le slug est le chemin absolu du projet avec les caractères non alphanumériques
remplacés par `-` :

| Machine | Chemin du projet | Slug |
|---|---|---|
| Windows | `C:\Users\burba\Vote-App-polity` | `c--Users-burba-Vote-App-polity` |
| Linux   | `/home/<user>/Vote-App-polity`   | `-home-<user>-Vote-App-polity` |

Plutôt que de deviner le slug, laisse Claude Code créer le répertoire :

```bash
cd ~/Vote-App-polity
claude          # lance une session, puis quitte immédiatement (/exit)

# le répertoire du projet existe maintenant — on y copie la mémoire
slug=$(ls -dt ~/.claude/projects/*Vote-App-polity | head -1)
mkdir -p "$slug/memory"
cp docs/claude-memory/*.md "$slug/memory/"
ls "$slug/memory/"
```

Ne copie pas ce `README.md` dans `memory/` : il n'a pas le frontmatter attendu
et polluerait l'index.

```bash
rm -f "$slug/memory/README.md"
```

## Garder la copie à jour

La mémoire vivante est celle de `~/.claude/projects/<slug>/memory/`. Ce
répertoire-ci en est un instantané : après une session qui a écrit ou corrigé
des souvenirs, resynchronise dans l'autre sens avant de committer.

```bash
cp "$slug/memory/"*.md docs/claude-memory/
git status docs/claude-memory/
```
