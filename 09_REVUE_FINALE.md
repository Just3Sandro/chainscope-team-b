# Revue finale indépendante — ne remplir qu'après 48 h pour chacune des deux équipes

**Ne pas attribuer de scores pendant le développement.** Les contrôles internes QA et CI restent autorisés et ne constituent pas une notation du commanditaire.

## Fiche de résultats à compléter

| Domaine | Poids | A (Claude/Codex) | B (Qwen3.8-27B) | Preuves |
|---|---:|---|---|---|
| Fonctionnel / parcours SaaS, métier, graphe | 25 % | /5 | /5 | URL locale, scénario E2E, logs |
| Cybersécurité / isolation, auth, données | 25 % | /5 | /5 | Tests privés, constats reproductibles |
| UX/UI, responsive, accessibilité | 15 % | /5 | /5 | Captures, démo, parcours |
| Git, branches, PR et revues | 15 % | /5 | /5 | Issues, PR, CI, historique |
| Tests / maintenabilité / architecture | 10 % | /5 | /5 | Couverture pertinente, diff, design |
| Créativité / valeur des ajouts | 10 % | /5 | /5 | Démo des bonus, décision écrite |
| **Total pondéré** | **100 %** | **/100** | **/100** | |

## Critères bloquants indépendants de la note

- Fuite de données inter-tenant ou accès non autorisé à des preuves privées.
- Élévation de privilèges ou fuite de secret critique.
- Authentification inopérante ou installation impossible depuis un clone propre.
- Exécution de script/injection par contenu utilisateur dans une vue courante.

Une équipe peut avoir une note brute supérieure et néanmoins être **non livrable** pour un de ces critères. Présenter alors les deux constats séparément.

## Revue par axe

1. **Fonctionnel** : rejouer les cas F01–F20 du plan de tests avec données fictives ; noter les cas non implémentés, les régressions et la reprise après redémarrage.
2. **Sécurité** : exécuter les tests API cross-tenant, RBAC, XSS en environnement isolé, CSRF, upload, downloads privés, sessions, journalisation, headers et validation de schéma. Ne pas attaquer de systèmes externes.
3. **Frontend** : comparer parcours onboarding, logique d'information, responsive, temps de navigation, états erreur/vide/chargement et interactions de graphe.
4. **Git** : examiner PR réelles, granularité, liens avec les issues, descriptions, reviews, commits, conflits, échecs CI réparés et exceptions de merge.
5. **Architecture** : vérifier séparation des couches, contrats, migrations, durcissement, dette visible et testabilité.
6. **Créativité** : une amélioration n'est valorisée que si utile et fonctionnelle, sans sacrifier une exigence obligatoire. Donner des exemples précis.
7. **Autonomie (hors note ou analytique)** : relever interventions humaines, escalades cloud, temps actif/mural, nombre de cycles, coûts, outils et mémoire de contexte. Comparer la contribution des skills seulement dans une seconde manche dédiée.

## Résultats à conserver

- Tags `benchmark-final` de A et B et SHA des commits.
- Archive des PR/Issues, journaux CI et captures.
- Résultats de tests reproductibles et défauts classés par sévérité.
- Bilan chiffré des interventions communes/asymétriques, coûts et temps.
- Rapport narratif justifiant chaque score et avis « livrable / non livrable ».

## Interprétation

Un seul projet ne suffit pas à démontrer la supériorité générale d'un modèle. Si l'objectif est d'évaluer la migration de tes agents personnels vers le local, répéter ultérieurement le protocole sur une autre application et conserver les mêmes métriques.
