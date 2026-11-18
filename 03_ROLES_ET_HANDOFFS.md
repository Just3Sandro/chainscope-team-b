# Organisation agentique : cinq rôles obligatoires

Les cinq rôles sont **conceptuellement identiques** pour les deux équipes. Ils peuvent être implémentés par des sous-agents, instructions de dossiers ou sessions distinctes du même modèle. Il n'est **pas exigé** cinq modèles en mémoire. **Toute intervention d'un modèle externe de secours doit être consignée** ; à défaut elle n'entre pas dans le score autonome de l'équipe.

| Rôle | Missions | Livrables vérifiables | Restriction |
|---|---|---|---|
| Tech Lead / PM | Convertir la spec en épics/issues, ordre critique, dépendances, décisions, arbitrages | `docs/PLAN.md`, issues reliées aux PR, `docs/DECISIONS.md` | Ne peut assouplir les exigences métier/sécurité |
| UX/UI Designer | Définir la marque, navigation et système visuel, states/loading/errors/accessibilité ; proposer un bonus | `docs/DESIGN.md`, design tokens, captures d'écran et justification | Doit conserver tous les parcours obligatoires |
| Développeur | Implémentation backend/frontend, migrations, Docker, tests, commits et PR | Code compilable, migrations et tests, PR descriptives | Pas de merge sans review/CI |
| Expert Cyber | Threat model, RBAC, isolation, auth, uploads, sessions, contrôles ASVS, review sécurité | `docs/THREAT_MODEL.md`, résultats et issues sécurité, review Git | Pas d'affirmation de conformité sans preuves |
| QA / Reviewer | Plan de tests, tests E2E, validation fonctionnelle, revue indépendante des PR | `docs/QA_REPORT.md`, logs des commandes, verdict PR | Ne peut déclarer réussi un test non exécuté |

## Règles de collaboration

1. Le Tech Lead décompose le travail. L'UX Designer propose les parcours et le design ; l'Expert Cyber formalise les risques avant les endpoints sensibles.
2. Le Développeur travaille par branche avec tests. Chaque PR reçoit un regard QA et, pour les changements sensibles, un regard Cyber. Les agents peuvent s'autocorriger.
3. Les reviews sont effectuées par **un rôle distinct du rôle auteur**. Si le même LLM représente plusieurs rôles, les contexts et prompts restent séparés ; cette revue n'est pas considérée aussi indépendante qu'une revue humaine ou multi-modèle.
4. Les décisions non prescrites sont consignées avec compromis, alternatives et impact dans `docs/DECISIONS.md`.
5. Pas de modification directe de `main` par les agents. Une branche non prête reste ouverte avec limitations documentées.
6. Un conflit entre agents est tranché par le Tech Lead **dans le cadre de la spécification**. Toute question qui impose de changer le contrat est remontée au commanditaire et doit faire l'objet d'un amendement commun.

## Jalons d'avancement (aucune note)

- **Jalon 1 — planification :** backlog GitHub, priorités, risques, design system initial.
- **Jalon 2 — vertical slice :** connexion réelle → création mission → un constat visible côté cabinet.
- **Jalon 3 — cœur métier :** graphe calculé côté serveur, publication client, preuves privées.
- **Jalon 4 — finition :** tests E2E, isolation cross-tenant, corrections CI et capture du produit.

Ces jalons servent à observer les progrès, pas à changer les scores ni à exiger une date intermédiaire arbitraire.
