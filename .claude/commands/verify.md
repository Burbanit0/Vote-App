---
description: Vérifie que la branche fait ce qui a été demandé (fast-gate + agent spec-checker) et prépare la section « Preuves » de la PR
argument-hint: "<la demande d'origine, mot pour mot>"
---

Vérifie la branche courante avant d'ouvrir sa PR.

0. **Ce qui est vérifié, c'est ce qui est commité.**
   - fast-gate et spec-checker comparent tous deux la base à `HEAD`.
   - Si `git status --porcelain` montre des changements suivis non commités, arrête-toi : dis-le et propose de commiter d'abord.
   - Sinon, le contrôle porterait sur un autre code que celui de la PR, et un « aucun changement » de fast-gate passerait pour un succès.
   - **La base**, notée `<base>` ci-dessous, est celle de la future PR : `origin/polity` par défaut, ou `origin/develop` pour une synchronisation. Les deux contrôles reçoivent la même.
1. **La demande.**
   - Prends `$ARGUMENTS` comme demande d'origine, mot pour mot.
   - Sans argument, reprends le message de l'utilisateur qui a lancé ce travail, tel quel, sans le résumer ni le reformuler.
   - S'il n'est plus disponible, demande-le. Une paraphrase écrite par l'auteur du changement ne vaut pas preuve.
2. **Les contrôles rapides.**
   - Lance `scripts/fast-gate.sh <base>` et garde son résumé.
   - Une section `SKIPPED` n'est pas un succès : note-la.
3. **La conformité à la demande.**
   - Lance l'agent `spec-checker` en lui donnant la demande exacte et la même `<base>`.
   - Ne lui donne ni ton propre résumé du changement, ni les messages de commit.
   - Montre son rapport tel quel.
4. **Le bloc « Preuves ».** Imprime un bloc prêt à coller dans la section `## Preuves` du modèle de PR :
   - les commandes réellement lancées, avec leur résultat (dernières lignes utiles) ;
   - le verdict du spec-checker et ses critères (C1, C2…) ;
   - une ligne **Non vérifié**, obligatoire et jamais vide : écris « rien » seulement si c'est vrai.

Si le verdict est `FAIL`, ou si un critère est manquant, n'ouvre pas la PR. Dis ce qui manque et propose la suite.

Si le verdict est `GAPS`, ouvre-la seulement si les écarts sont écrits dans la PR.

Ne corrige rien de toi-même sur la seule foi du rapport.
