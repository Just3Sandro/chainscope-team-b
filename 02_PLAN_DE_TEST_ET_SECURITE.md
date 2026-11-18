# ChainScope — Plan de vérification indépendant V2

**À préparer avant le développement ; ne pas transmettre l'implémentation des tests privés aux agents.** Les cas d'acceptation publics peuvent être communiqués intégralement. Les scénarios ci-dessous sont des critères, pas des scripts exécutables.

## 1. Jeu de données de référence (fictif)

- Tenant **Aegis Red Team** : client `Acme Santé`, engagements `Audit Web 2026` et `Audit AD 2026`.
- Tenant **Boreal Security** : client `Boreal Finance`, engagement `Audit Externe 2026`.
- Utilisateurs distincts : plateforme admin, admin Aegis, pentester Aegis, lecteur Acme, admin Boreal, lecteur Boreal.
- Pour `Audit Web 2026` : actif `Web` (entry_point), `API`, `DB` (crown_jewel, criticality 5) ; findings `F1` (CVSS 8.8, OPEN), `F2` (CVSS 7.5, OPEN) ; edges `Web→API (F1)`, `API→DB (F2)`.
- Score attendu du chemin initial : `2 × 5 × min(8.8,7.5) = 75.0`.

## 2. Critères d'acceptation obligatoires

| ID | Scénario | Résultat exigé |
|---|---|---|
| F01 | Login correct, logout et re-login | Session créée/révoquée ; après logout les routes privées refusent l'ancienne session |
| F02 | Invitation client consommée puis rejouée | Première activation réussie ; deuxième refusée |
| F03 | Admin Aegis crée un client et un engagement | Ressources persistées, scope de tenant cohérent |
| F04 | Pentester crée actif et constat | Champs validés, visibles au bon cabinet seulement |
| F05 | Client lit un finding non publié | Refus / absence, indépendamment de l'UUID connu |
| F06 | Finding publié | Visible au client autorisé, invisible à un autre client |
| F07 | Client tente de modifier un finding | Refus côté backend |
| F08 | Graphe initial Web→API→DB | Un chemin de score 75.0 correctement ordonné |
| F09 | Passage F2 à REMEDIATED | Chemin Web→DB disparu sans suppression manuelle de l'edge |
| F10 | Passage F2 à ACCEPTED_RISK | Chemin de nouveau actif (acceptation ≠ correction) |
| F11 | Edge vers actif d'un autre engagement | Rejet et état de base inchangé |
| F12 | Upload PNG/PDF autorisé | Stockage privé, SHA-256 correct et download autorisé |
| F13 | Client devine evidence ID privé | Refus tant que finding non publié ou evidence non visible |
| F14 | Fichier interdit ou > 10 Mio | Rejet, sans stockage durable d'objet non autorisé |
| F15 | XSS dans titre/description | Aucun script exécuté lors du rendu ou export HTML |
| F16 | CSRF sur requête mutante | Refus sans jeton correct |
| F17 | Modification de rôle par champ injecté dans body | Impossible (mass assignment empêché) |
| F18 | Action sensible effectuée | Audit event enregistré sans jeton ni mot de passe |
| F19 | Refresh navigateur + reprise après redémarrage Compose | Données et sessions valides non expirées persistées ; aucune perte de DB |
| F20 | Installation depuis clone propre | `docker compose up --build` + migrations/seed documentés, aucun secret commité |

## 3. Tests sécurité complémentaires (séparés et indépendants)

### Isolation / authorization

- Modifier `tenant_id`, `engagement_id`, `finding_id`, `client_org_id` dans URL, JSON ou filtres ; tenter lectures, écritures, téléchargements et agrégations cross-tenant.
- Vérifier que les listes ne renvoient pas de données du voisin et qu'aucun champ interne n'est exposé dans la réponse client.
- Essayer de publier/rétracter en tant que client ; tenter l'élévation de privilèges par modification des paramètres.

### Sessions / usurpation

- Cookie expiré, révoqué ou altéré ; reset token réutilisé ; jeton d'invitation expiré ; changement de mot de passe et sessions anciennes.
- Validation du CSRF pour mutations cookie-based et contrôles d'origines.
- Vérifier absence de cookie de session dans JavaScript, logs, URL ou HTML.

### Contenu et stockage

- Payloads inoffensifs de test HTML/JS dans les champs utilisateur pour vérifier encodage ; pas d'exécution de script dans le navigateur.
- Upload sous faux MIME, faux suffixe, nom de fichier avec séparateurs, PDF volumineux, content-type dangereux ; vérifier limite, nettoyage, isolation.
- Vérifier téléchargement avec `Content-Disposition: attachment` et `nosniff`.

### Logique métier

- Graphes cycliques, edges doublons, éléments supprimés, absence de crown jewel, CVSS 0/10, plus de six sauts, deux chemins à scores identiques, recalcul après correction.
- Mutations dans mission `CLOSED`, tentative de lien de constat d'un autre engagement, accès aux preuves non publiées.

## 4. Vérifications reproductibles

- Tests automatisés : `pytest`, `vitest run`, `playwright test`, build frontend et backend.
- Examens indépendants : API HTTP, requêtes à ID échangés, inspection des logs, check sécurité des headers, test de persistance sur volume.
- Vérification visuelle : authentification, dashboard, gestion des engagements, graphe, portail client, états d'erreur, responsive.
- Temps et taux de réussite doivent être consignés ; ne pas déclarer « testé » sans commandes et journaux d'exécution.

## 5. Référentiels

- OWASP ASVS 5.0 : https://github.com/OWASP/ASVS
- OWASP API Security Top 10 : https://owasp.org/API-Security/
- OWASP File Upload Cheat Sheet : https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

## 6. Critères bloquants de livraison

- Fuite de données cross-tenant ou accès à une preuve sans autorisation.
- Escalade de privilèges exploitable.
- Échec du chemin de connexion normal (app non utilisable).
- Impossible de démarrer depuis l'environnement livré.
- Injection de code dans la chaîne de rendu des données utilisateur.

Une fonctionnalité cosmétique ou un bonus ne compense aucun blocage de cette liste.


## 7. Gouvernance de la revue finale V2

Les scénarios ci-dessus sont communs ; **les implémentations de tests privés et les grilles de notes restent hors des dépôts des deux équipes**. Les reviewers vérifient en dernier lieu la sécurité avec des données fictives et sur des instances locales isolées. Les scores sont remplis **après** les 48 heures seulement. Toutes les vulnérabilités remontées doivent comprendre impact, préconditions et preuve reproductible non destructive. Une faille bloquante est signalée séparément de la note globale.
