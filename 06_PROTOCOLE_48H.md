# Protocole 48 h, équité et interventions

## Question posée

À partir d'un **cahier des charges et d'une architecture unique**, la chaîne de développement cloud Claude/Codex (équipe A) et la chaîne Qwen3.8-27B (équipe B) produisent-elles un SaaS fonctionnel, sûr et maintenable en 48 h par équipe ? On compare des **systèmes modèle + agent + outils**, non des modèles isolés si leurs environnements diffèrent.

## Préparation commune

1. Geler les documents par commit et conserver SHA-256 du pack.
2. Partir du même commit de départ. Même jeux de données fictives, mêmes exigences, mêmes références design et sécurité, mêmes droits Git et même capacité de CI.
3. Déclarer versions / identifiants de modèles, fournisseur OpenRouter exact, éventuels paramètres de raisonnement, contexte maximal, température, politique de retry, agent shell/éditeur et outils disponibles.
4. L'architecte commun **termine sa mission avant le lancement** ; aucune réarchitecture spécifique après observation d'une équipe. Questions normatives → addendum identique envoyé aux deux.
5. Si les équipes emploient des frameworks d'agents différents, noter explicitement ce facteur confondant ; ne pas attribuer mécaniquement l'écart au seul LLM.

## Temps

- Chaque équipe reçoit **48 heures murales au maximum**, démarrant à son accès effectif au dépôt. Pour limiter le biais, faire deux fenêtres successives de 48 h ou deux fenêtres parallèles strictement isolées.
- Consigner début et fin avec fuseau horaire, interruptions, incidents de fournisseur / panne réseau, réexécutions et interventions humaines.
- Les pauses volontaires et phases d'attente comptent dans le temps mural ; une panne majeure documentée peut donner lieu à une exception **identique** et annoncée aux deux équipes.
- À l'échéance, figer commit/tag `benchmark-final`, fermer les PR non terminées sans les considérer livrées, archiver les logs.

## Suivi pendant les 48 h : libre, sans notes

Le commanditaire peut consulter PR, issues, CI, démos locales et écrans ; il peut demander un rapport d'avancement factuel. **Aucune note chiffrée, classement ou verdict de qualité comparatif pendant les deux fenêtres.**

### Trois classes d'interventions

| Classe | Exemple | Impact sur le benchmark |
|---|---|---|
| OBSERVATION | « Montre-moi la démo », « où en est la PR auth ? » | Sans instruction technique ; journal facultatif |
| CLARIFICATION COMMUNE | « Le rôle client ne peut pas modifier un finding » | Si normatif, documenter et transmettre **mot pour mot** à A et B |
| AJUSTEMENT / FEEDBACK | « Rends le graphe plus lisible », « ajoute une étape d'onboarding » | Transformer en amendement identique pour A et B, avec priorité, date et éventuellement durée compensée |

Une instruction de débogage donnée **seulement** à une équipe est une **assistance asymétrique**. Elle est autorisée si nécessaire mais doit être tracée, et le résultat « autonomie brute » est présenté séparément du résultat « assisté ».

## Ne pas confondre suivi et jugement

- Les tableaux d'avancement peuvent indiquer `à faire`, `en cours`, `bloqué`, `terminé` sans les convertir en notes.
- Les validations QA et Cyber **dans les équipes** sont normales et autorisées ; elles ne sont pas la note du commanditaire.
- Les observations transmises à l'autre équipe ne doivent jamais contenir son code, ses solutions ou ses résultats privés.

## Livraison attendue

Commit final, code, Docker Compose, migrations, seed, documentation, tests/CI, URL de démo locale, vidéo/captures, liste des PR, décisions, problèmes ouverts, candidats skills, bilan coût/tokens/contexte et déclaration honnête des tests exécutés.

## Après les deux fenêtres

Revue finale **en aveugle lorsque possible** ; tests privés identiques ; revue sécurité manuelle sur environnements locaux ; revue UX ; audit Git ; score final avec blocages et coût. En cas de divergence majeure entre modèles, une seconde expérience sur un autre projet serait nécessaire pour généraliser.
