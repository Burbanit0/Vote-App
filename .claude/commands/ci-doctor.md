---
description: Diagnostic d'un échec CI (run, PR ou branche) par l'agent ci-doctor
argument-hint: "[run id | n° de PR | branche]"
---

Lance l'agent `ci-doctor` sur `$ARGUMENTS` (sans argument : la pointe de `polity`).
Montre son rapport tel quel : catégorie, preuve tirée du vrai log, « est-ce la faute de cette PR ? », cause, correction, et ce qui n'a pas pu être vérifié.
Ne relance aucun job et ne modifie rien sur la seule foi du rapport : propose la correction et attends.
