# Protocole Skill Candidates / amélioration continue

## Principe

Chaque équipe peut produire de nouveaux **candidats skills** quand un problème récurrent apparaît. Il s'agit de procédures, d'outils, de checklists ou de tests réutilisables ; **ce n'est pas une modification des poids du LLM**.

Pendant ce premier benchmark :

- Les agents ont le droit d'apprendre *dans le contexte courant* et de se corriger avec les résultats de leurs tests.
- Ils peuvent enregistrer un candidat dans `skill_candidates/<nom>/SKILL.md`.
- Un **nouveau candidat n'est pas injecté automatiquement** dans les prompts ni activé globalement pendant les 48 h ; il ne remplace pas les consignes initiales. Les corrections de code et de tests utiles restent autorisées.
- Aucun skill propriétaire préexistant d'une équipe n'est admis sauf s'il est fourni aux deux équipes avant le départ.
- Après l'évaluation, on pourra organiser une manche séparée « avec skills activés » en utilisant les meilleurs candidats, contrôlés et testés.

## Gabarit du candidat

Chaque fichier `skill_candidates/<slug>/SKILL.md` doit contenir :

```markdown
# Nom du skill
- Auteur (rôle) :
- Déclencheur / situations où l'utiliser :
- Problème initial observé et issue/PR associées :
- Procédure reproductible :
- Outils nécessaires et permissions minimales :
- Exemple qui fonctionne :
- Test automatique de validation :
- Contre-exemples / limites :
- Risque de sécurité ou d'effet secondaire :
- Version et date :
- Statut : candidate (non activée)
```

## Critère de qualité post-benchmark

Un candidat ne devient **validé** qu'après tests sur plusieurs exemples, comparaison avant/après sur des cas non utilisés lors de sa rédaction, absence de régression et revue de sécurité. Un gain sur un seul exemple n'est pas suffisant.

## À éviter

- Transformer une correction ponctuelle en règle générale sans preuve.
- Enregistrer secrets, clés d'API, données clients ou prompts malveillants rencontrés dans des fichiers tiers.
- Créer des skills contradictoires ou trop volumineux, injectés dans chaque prompt même lorsqu'ils sont hors sujet.
- Noter une équipe pendant le développement sur le volume de skills : **la pertinence prime sur le nombre**.
