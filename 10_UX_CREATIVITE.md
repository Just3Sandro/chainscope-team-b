# Design et créativité — liberté encadrée

## Inspirations communes (pas des maquettes à copier)

- **Linear** : densité informationnelle et ergonomie fluide des listes et filtres.
- **Sentry** : triage, regroupement de constats et lecture rapide d'incidents.
- **OWASP DefectDojo** : organisation métier d'une plateforme de suivi de vulnérabilités.
- **React Flow** : graphes interactifs et interactions d'édition/navigations.

Les agents peuvent étudier ces références, mais **aucune ressemblance visuelle précise n'est imposée**. Ne pas copier l'identité ni des éléments protégés.

## Libertés autorisées

- Nom de pages internes, couleurs, typographie, navigation secondaire et organisation des tableaux.
- Graphique de synthèse, filtres avancés, raccourcis clavier, micro-interactions, mode sombre.
- Idées originales explicables : vues « avant/après remédiation », regroupements de chemins par cible, raccourci constat→graphe, vue client plus pédagogique.

## Invariants UX

- Les principaux parcours de la spec doivent être accessibles et fonctionnels ; aucune page ne doit se contenter de données mockées pour une fonctionnalité métier.
- Messages d'erreur clairs, indicateurs de chargement, tableaux filtrables, interfaces utilisables au clavier et sur tablette.
- Le graphe doit refléter **la vérité serveur**, pas seulement un dessin interactif ; le calcul et le statut des edges ne sont pas réinventés côté client.
- Les contenus privés ne doivent pas fuiter dans le DOM, la cache frontend ou les erreurs lorsque le rôle client ne les autorise pas.
- Pas de bonus créatif qui exige un service SaaS externe payant ou l'exposition publique de l'application.

## Évaluation

La créativité sera notée uniquement à la fin, sur les fonctionnalités démontrables et les décisions écrites dans `docs/DECISIONS.md`, et non sur une maquette séduisante sans backend.
