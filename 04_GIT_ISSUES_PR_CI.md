# Protocole Git, Issues et Pull Requests

## Dépôts et permissions

- Deux **dépôts GitHub privés distincts**, créés depuis le même état initial. Aucun accès des agents de A au repo B et inversement.
- Branche `main` protégée : PR obligatoire, suppression du push direct, au moins une approbation de revue (via mécanisme GitHub si possible ; sinon review agent tracée et merge effectué par une identité autorisée distincte), CI verte. Un compte agent n'a pas de rôle admin.
- Identités et secrets de développement propres à chaque équipe ; mêmes capacités et restrictions. Aucun token avec permissions globales inutilement élevées.
- Les tests privés et l'évaluation finale ne doivent exister dans **aucun** dépôt d'implémentation.

## Convention

- Branches `feature/<ticket>-slug`, `fix/<ticket>-slug`, `security/<ticket>-slug`, `test/<ticket>-slug`.
- Commits ciblés et explicites (conventional commits recommandé : `feat:`, `fix:`, `test:`, `docs:`, `security:`).
- Une Issue par fonctionnalité significative, avec critères d'acceptation. La PR référence l'Issue et annonce les fichiers modifiés, tests réellement lancés, effets de bord, captures UI et questions non résolues.
- Pas de merge de PR avec tests cassés connus ; si une exigence non satisfaite est explicitement hors périmètre de la PR, elle doit rester suivie dans une Issue, pas être masquée.
- Chaque équipe peut choisir sa granularité de PR, mais une seule PR géante sans revue documentée sera pénalisée dans la qualité d'ingénierie.

## CI minimale à implémenter par les agents

- GitHub Actions sur PR et `main` : tests backend pytest, tests frontend Vitest, typecheck/build, tests d'intégration API avec Postgres, et contrôles de format/lint si installés.
- Playwright end-to-end dans une étape documentée, exécutée au moins avant clôture finale (CI ou script local reproductible).
- Échec de CI = PR non fusionnée, avec log et correction. Les deux équipes disposent d'un environnement et de délais similaires pour régler les erreurs d'environnement.
- Les agents peuvent utiliser des caches de dépendances, mais pas de services SaaS payants non communs ni de secrets externes.

## Audit à la fin

Relever : nombre d'issues, branches, PR ouvertes/fusionnées, nombre de retours review et corrections, taux de CI réussie, commits significatifs, changements non revus, conflits, branche finale, temps passé et rapport de dépendances.

## Pourquoi on mesure Git

La qualité de la production ne se limite pas à « faire fonctionner un code ». Elle inclut la capacité à travailler dans un processus reproductible où les changements sont relus, expliqués et traçables.
