# ChainScope — Benchmark V2 prêt au lancement

**Projet :** SaaS pentest multi-tenant, graphe d'attaque, preuves et portail client.  
**But :** comparer deux chaînes de développement sur un cahier des charges unique.  
**Équipe A :** architecte commun + développeurs Claude/Codex.  
**Équipe B :** même architecte commun + développeurs Qwen3.8-27B.  
**Temps :** 48 h par équipe, horloge de travail documentée.  
**Notes :** aucune avant les deux clôtures.  
**Statut :** V2 figée au lancement ; changements uniquement via addendum écrit communiqué à A et B.

## Démarrage rapide

1. Conserver ce dossier comme **source unique** et noter son SHA-256 (archive ou commit).
2. Créer deux dépôts privés **séparés** à partir du même commit initial (A et B), contenant ces documents et les modèles GitHub. Ne pas fournir l'évaluation privée ni le dépôt de l'autre équipe.
3. Configurer dans chaque dépôt les mêmes permissions, règles de protection de `main`, secrets de développement *fictifs* et environnements d'outils. Les agents doivent créer les scripts CI réels dans leur code.
4. Donner **strictement** `07_PROMPT_COMMUN.md` aux deux équipes ; ne changer que l'identifiant neutre A/B et les paramètres du fournisseur consigné.
5. Lancer le chronomètre de chaque équipe à l'accès effectif au dépôt, au même plafond de 48 h. Les interruptions humaines et pannes sont enregistrées.
6. Suivre librement l'avancement sans donner de notes. Les demandes de changement passent par `08_JOURNAL_INTERVENTIONS.md`, et la même instruction est reçue par A et B.
7. Clore chaque équipe sur un **commit/tag immuable** ; sauvegarder le diff Git, les PR, le journal d'actions et les coûts. Tester ensuite avec `09_REVUE_FINALE.md` et le plan indépendant.

## Fichiers

- `01_SPECIFICATIONS_ET_ARCHITECTURE.md` : exigences et contrats API normatifs.
- `02_PLAN_DE_TEST_ET_SECURITE.md` : critères publics et matrice d'audit.
- `03_ROLES_ET_HANDOFFS.md` : cinq rôles, responsabilités et livrables.
- `04_GIT_ISSUES_PR_CI.md` : GitHub, branches, PR et qualité des changements.
- `05_SKILLS_ET_AMELIORATION.md` : apprentissage procédural et candidats skills.
- `06_PROTOCOLE_48H.md` : conditions de comparaison, observations, métriques.
- `07_PROMPT_COMMUN.md` : unique prompt de lancement pour A et B.
- `08_JOURNAL_INTERVENTIONS.md` : modèle d'amendements et remontées.
- `09_REVUE_FINALE.md` : grille d'analyse sans notes prédéfinies.
- `10_UX_CREATIVITE.md` : inspirations et liberté visuelle.
- `.github/` : modèles d'issues et de PR identiques.

## Sécurité et périmètre

Uniquement des comptes et données de démonstration **fictifs**. Pas de scans offensifs réels ni de déploiement public sans validation. Ne pas donner aux agents les secrets personnels, tokens de production ni droits d'administrateur GitHub. Ce dossier est un **benchmark d'ingénierie**, pas un produit certifié.
