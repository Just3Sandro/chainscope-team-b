# ChainScope — Design System & Spécification UI

**Statut** : livrable Jalon 1 (issue #2). Ce document est la référence de l'interface pour le développeur : direction artistique, tokens, navigation par rôle, spécification des 9 pages de la spec §7, langage visuel du graphe, accessibilité et bonus UX.
**Références** : `01_SPECIFICATIONS_ET_ARCHITECTURE.md` (§4, §7), `10_UX_CREATIVITE.md`, `03_ROLES_ET_HANDOFFS.md`, inspirations (non copié) : Linear, Sentry, DefectDojo, React Flow.
**Rappels contraignants** : le serveur est la source de vérité (chemins actifs, statuts, permissions) ; les contenus privés ne sont jamais rendus dans le DOM côté client ; responsive desktop/tablette ; états chargement/erreur/vide partout ; aucune donnée mockée.

---

## 1. Direction artistique

### 1.1 Positionnement

ChainScope est une **console d'opérations offensive, sobre et dense** : l'outil quotidien de cabinets qui pilotent des campagnes de pentest, pas une vitrine. Le visuel doit donc ressembler à une salle de contrôle plus qu'à un site produit — densité informationnelle (tableaux, chips, grille 4 px), couleurs neutres froides qui laissent toute la place au signal (sévérités, statuts, chemins actifs), zéro décoratif, micro-interactions courtes et prévisibles. La sobriété vient des surfaces claires et de l'accent unique ; la densité vient des lignes de tableau de 32–40 px et des KPI toujours contextualisés. Un thème sombre global est un non-livré assumé (lisibilité des tableaux et budget 48 h) ; les tokens restent compatibles avec un thème sombre ultérieur (aucune couleur hardcodée hors tokens).

### 1.2 Marque et écusson

- **Motif** : deux maillons de chaîne entrelacés dont le second s'ouvre en **nœud de graphe** (cercle) — « le lien de la chaîne d'attaque, en scope ». L'écusson est le glyphe seul (sans fond), utilisable en mono : encre `#0F172A` sur fond clair, accent `#1D4ED8` sur fond sombre, taille minimale 24 px.
- **Logotype** : écusson + « ChainScope » en Inter 600 ; « Chain » en encre, « Scope » en accent (24 px, espacement -0.02 em).
- **Emplacement** : sidebar cabinet (haut), topbar portail client, page de connexion, onglet du navigateur (favicon = écusson 24 px).

### 1.3 Palette (résumé — tokens complets en §2)

Fond de page gris-bleu très clair, surfaces blanches, bordures grises discrètes. L'accent **bleu `#1D4ED8`** est réservé aux éléments interactifs et au chemin actif du graphe. Les 4 sévérités et 4 statuts de constats ont chacun un triple (dot / fond doux / texte) calibré pour le contraste AA. Le violet est réservé à `ACCEPTED_RISK` pour le distinguer nettement de « corrigé ».

### 1.4 Typographie

- **UI** : **Inter** (Google Fonts, OFL) 400/500/600/700 — stack de repli système (`system-ui, "Segoe UI", Roboto…`).
- **Monospace** : **JetBrains Mono** (Google Fonts, OFL) 400/600 pour **CVSS, UUID/ID, `request_id`, SHA-256, slug, valeurs de code** — jamais pour du texte courant.
- Tailles (base 14 px pour la densité) : 11 caption / 12 secondaire / 14 corps et tableaux / 16 titres de section / 20 titre de page / 24 KPI et titres modales / 30 titre login. Le palier 11 px ne sert qu'aux libellés uppercase et chips, en `ink-soft` ou plus foncé — jamais en `ink-faint` (règle unique, §7.5).
- Règle : le CVSS s'affiche toujours `7.8` (1 décimale) en mono ; un ID s'affiche en mono tronqué (`f4a2…c91d`) avec `title` complet.

### 1.5 Ton des microcopy

Court, opérationnel, à la voix active. Pas de marketing, pas de « Bienvenue ! », pas de phrases réconfortantes.
- Boutons = verbe + objet : « Publier le constat », « Fermer la mission », « Inviter un membre ».
- Erreur = fait + issue : « Le serveur a refusé la requête (403). Vous n'avez pas les droits sur cette ressource. Réessayer / Retour au tableau de bord ».
- Vide = état + action possible : « Aucun chemin actif vers la cible. Les liens connus sont corrigés. Créer un constat pour documenter le risque. »
- Jamais de message qui révèle l'existence d'un compte (auth) : « E-mail ou mot de passe incorrect. ».

---

## 2. Design tokens

### 2.1 Principes

- Grille **4 px** ; aucun espacement hors échelle ; rayons et ombres nominalisés.
- Toute couleur passe par un token : `bg-surface`, `text-ink-soft`, `border`, `text-sev-critical-ink`… L'application ne contient aucun hexadécimal hors `@theme`.
- Un triple par sémantique (pointe / fond doux / texte) : `.dot` (10 px), fond de chip, texte de chip. Le texte de chip est toujours ≥ 4,5:1 sur son fond (teintes 700–800 sur fonds 100).
- Mappage 1:1 Tailwind CSS v4 : chaque token `--color-x` génère les utilitaires (`bg-x`, `text-x`, `border-x`) et reste accessible comme variable CSS `var(--color-x)`.

### 2.2 Bloc `@theme` Tailwind v4 (prêt à coller)

```css
@theme {
  /* Typographie */
  --font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;

  --text-2xs: 0.6875rem;  --text-2xs--line-height: 1rem;      /* 11/16 libellés uppercase/chips (ink-soft+, jamais ink-faint) */
  --text-xs: 0.75rem;     --text-xs--line-height: 1rem;       /* 12/16 secondaire, aide, request_id, métadonnées */
  --text-sm: 0.875rem;    --text-sm--line-height: 1.25rem;    /* 14/20 corps, tableaux */
  --text-base: 0.875rem;  --text-base--line-height: 1.25rem;  /* 14/20 défaut UI */
  --text-lg: 1rem;        --text-lg--line-height: 1.5rem;     /* 16/24 titres de section */
  --text-xl: 1.25rem;     --text-xl--line-height: 1.75rem;    /* 20/28 titres de page */
  --text-2xl: 1.5rem;     --text-2xl--line-height: 2.25rem;   /* 24/36 KPI, titres modales */
  --text-3xl: 1.875rem;   --text-3xl--line-height: 2.5rem;    /* 30/40 titre login */

  /* Neutres */
  --color-canvas: #f4f6f9;          /* fond de page */
  --color-surface: #ffffff;         /* cartes, panneaux, modales */
  --color-surface-muted: #eef1f6;   /* en-têtes de tableau, zones inactives */
  --color-hover: #f1f4f9;           /* survol de lignes/boutons fantômes */
  --color-selected: #dbeafe;        /* ligne sélectionnée (accent-soft) */
  --color-border: #e2e7ee;          /* bordure standard */
  --color-border-strong: #c6cfdb;  /* bordure saillante, input au focus non actif */
  --color-ink: #0f172a;            /* texte principal (≈15:1 sur blanc) */
  --color-ink-soft: #475569;       /* texte secondaire (≈7,3:1) */
  --color-ink-faint: #64748b;      /* texte tertiaire, timestamps (≈4,7:1) */
  --color-ink-inverse: #ffffff;    /* texte sur accent/écusson sombre */

  /* Accent (interactif) */
  --color-accent: #1d4ed8;         /* bouton primaire, lien (≈5,5:1 avec blanc) */
  --color-accent-hover: #1e40af;
  --color-accent-soft: #dbeafe;    /* fond de sélection, KPI cliqué */
  --color-focus: #3b82f6;          /* anneau de focus */

  /* Sévérités — LOW / MEDIUM / HIGH / CRITICAL */
  --color-sev-low: #0284c7;         --color-sev-low-soft: #e0f2fe;     --color-sev-low-ink: #075985;
  --color-sev-medium: #d97706;     --color-sev-medium-soft: #fef3c7;   --color-sev-medium-ink: #92400e;
  --color-sev-high: #ea580c;       --color-sev-high-soft: #ffedd5;     --color-sev-high-ink: #9a3412;
  --color-sev-critical: #dc2626;   --color-sev-critical-soft: #fee2e2; --color-sev-critical-ink: #b91c1c;

  /* Statuts de constats — OPEN / IN_PROGRESS / REMEDIATED / ACCEPTED_RISK */
  --color-st-open: #64748b;        --color-st-open-soft: #eef2f6;       --color-st-open-ink: #334155;
  --color-st-inprog: #d97706;      --color-st-inprog-soft: #fef3c7;     --color-st-inprog-ink: #92400e;
  --color-st-remediated: #16a34a;  --color-st-remediated-soft: #dcfce7; --color-st-remediated-ink: #166534;
  --color-st-accepted: #7c3aed;    --color-st-accepted-soft: #f3e8ff;   --color-st-accepted-ink: #6b21a8;

  /* Statuts de missions */
  --color-mi-draft: #64748b;       --color-mi-draft-soft: #eef2f6;      --color-mi-draft-ink: #334155;
  --color-mi-active: #2563eb;      --color-mi-active-soft: #dbeafe;     --color-mi-active-ink: #1e40af;
  --color-mi-closed: #334155;      --color-mi-closed-soft: #e2e8f0;     --color-mi-closed-ink: #1e293b;

  /* Feedback (formes, toasts, validation) */
  --color-success: #15803d;        --color-success-soft: #dcfce7;
  --color-danger: #dc2626;         --color-danger-soft: #fee2e2;
  --color-warning: #d97706;        --color-warning-soft: #fef3c7;

  /* Rayons */
  --radius-2xs: 4px;    /* tags, mini-chips */
  --radius-xs: 6px;     /* points du graphe, icônes carrées */
  --radius-sm: 8px;     /* boutons, inputs, chips statuts */
  --radius-md: 12px;    /* cartes, KPI, panels */
  --radius-lg: 16px;    /* modales */
  --radius-pill: 999px; /* chips sévérité, pastilles de rôle */

  /* Ombres */
  --shadow-xs: 0 1px 2px rgb(15 23 42 / 0.05);
  --shadow-sm: 0 1px 3px rgb(15 23 42 / 0.08), 0 1px 2px rgb(15 23 42 / 0.04);
  --shadow-md: 0 4px 12px rgb(15 23 42 / 0.10);   /* menu, panneau latéral */
  --shadow-lg: 0 12px 32px rgb(15 23 42 / 0.14);  /* modale */
  --shadow-focus: 0 0 0 3px rgb(59 130 246 / 0.35); /* anneau de focus */
}
```

### 2.3 Métriques de layout (non génériques)

| Métrique | Valeur | Usage |
|---|---|---|
| Sidebar cabinet | 232 px (rail 64 px en tablette) | navigation cabinet |
| Topbar | 56 px | toutes les apps |
| Gouttière contenu | 24 px desktop / 16 px tablette | zone principale |
| Ligne de tableau | 32 px compacte / **40 px défaut** / 48 px confort | 40 px par défaut, 32 px en audit et listes longues |
| KPI card | 12 px padding, valeur `text-2xl` 600 | rangée de 4 max |
| Modal | 480 px (confirmation) / 640 px (formulaire) | centrée, `radius-lg`, `shadow-lg` |
| Panneau latéral graphe | 320 px, repliable | détail nœud/edge/chemin |
| Input / bouton | 36 px hauteur | formulaire et actions |
| Cible tactile tablette | ≥ 44 × 44 px via padding | boutons d'action en ligne |

### 2.4 Règles d'usage (exemples vus comme erreurs)

- Ne pas utiliser `sev-critical` (rouge) pour autre chose que la sévérité CRITICAL ; les erreurs de formulaire/utilisation de la page utilisent `danger` ; les deux sont proches mais sémantiquement distinctes.
- Jamais de couleur seule : tout chip contient texte (ou icône + `aria-label`) ; l'edge du graphe porte un label.
- `accent` ne se met pas en fond de KPI ni d'edge non actif ; le chemin actif est le seul cas de trait `accent` épais.
- Monospace obligatoire pour : CVSS, IDs, `request_id`, hash, slug.

---

## 3. Navigation et architecture d'information

### 3.1 Trois applications, trois shells

Un même compte peut appartenier à plusieurs espaces. Après connexion, la réponse de `GET /auth/me` (memberships) route vers :

| Rôle | App | Shell |
|---|---|---|
| `TENANT_ADMIN`, `PENTESTER` | Cabinet | Sidebar + topbar |
| `CLIENT_VIEWER` | Portail client | Topbar seule (épurée) |
| `PLATFORM_ADMIN` | Plateforme | Topbar + menu à 2 entrées |
| Plusieurs des précédents | — | Écran de sélection d'espace (`/workspace`) |

**Écran de sélection** : carte par espace (nom du tenant / de la ClientOrg / « Administration plateforme »), chip de rôle, action « Ouvrir ». Choisir un espace n'affecte aucune donnée : chaque appel API reste ressource par ressource (le serveur autorise, jamais le frontend).

### 3.2 App cabinet (sidebar)

```
[Écusson ChainScope]   [Bouton hamburger (tablette)]
CABINET — NomDuCabinet
  ▸ Tableau de bord        /
  ▸ Missions               /missions
  ▸ Clients                /clients
  ▸ Journal d'audit        /audit        (visible TENANT_ADMIN seulement)
────────────────────────────────────────
[Avatar] Prénom Nom
  [Chip rôle]  ▸ Se déconnecter / Changer d'espace
```

- Ordre = fréquence d'usage. Le **Graphe n'est pas un item de navigation global** : il s'ouvre depuis une mission (spec §7.6), ce qui préserve le contexte engagement.
- PENTESTER : l'item « Journal d'audit » est absent du DOM (pas de lien masqué) ; URL directe → page 403.
- Sidebar active : fond `canvas`, item actif = fond `selected` + texte `accent` + barre 3 px gauche ; survol = `hover`.
- Tablette (768–1023 px) : sidebar en rail 64 px (icônes + tooltip au focus/survol) ; bouton hamburger pour l'ouvrir en tiroir (overlay `shadow-md`, fermeture Échap ou clic extérieur).

### 3.3 Portail client (nav épurée, sans sidebar cabinet)

```
[Écusson] ChainScope  Portail client      [ClientOrg]   [Avatar ▾]
────────────────────────────────────────────────────────
  Mes missions            →   détail mission   →   détail constat
```

- Un seul niveau de navigation : **Mes missions** (liste, `/client`) → mission (détail, `/client/m/:id`) → constat (détail, `/client/m/:id/f/:fid`).
- Aucune entrée vers le cabinet, le graphe, l'audit ou la gestion. Le chip « Portail client » (fond `mi-active-soft`, texte `mi-active-ink`) est permanent pour rappeler le mode lecture seule.
- Menu utilisateur : « Se déconnecter » uniquement.

### 3.4 Administration plateforme

```
[Écusson] ChainScope  Plateforme          [Avatar ▾]
  Tenants  ·  Comptes
```

- Deux entrées, topbar (pas de sidebar : 2 items seulement). `/platform/tenants`, `/platform/users`.
- Garde `PLATFORM_ADMIN` sur les deux routes ; tout autre rôle → page 403 dédiée.
- **Interdit** : aucun lien vers les missions, constats, preuves ou journaux d'un tenant (pas de lecture des données métiers).

### 3.5 Règles de garde (clairement séparées du serveur)

1. Le frontend masque ce qu'il ne doit pas afficher (items, boutons) selon le rôle de session ; **le serveur reste le seul à autoriser** (spec §8).
2. Un bouton masqué n'est pas un bouton désactivé : les actions inaccessibles n'existent pas dans le DOM (pas de « Publier » au PENTESTER si l'engagement le refuse, pas de mutation aucune au CLIENT_VIEWER).
3. URL directe vers une route d'un autre rôle → **403**. URL directe vers une ressource inexistante ou hors périmètre (autre tenant/engagement) → **404** (alignement avec les codes API : le 404 cache l'existence).
4. Changer de rôle/tenant n'est jamais « en direct » : « Changer d'espace » passe par `/workspace` (relecture de `me`).

### 3.6 Comportement 401 / 403 / 404

| Cas | Détection | Comportement |
|---|---|---|
| **401** sur une mutation | TanStack Query / intercepteur | `POST /auth/logout` non requis ; redirection `/login?next=<url encodée>&reason=expired` + bandeau « Session expirée. Reconnectez-vous pour continuer. » Après login, retour sur `<next>`. |
| **401** sur un chargement | `GET /auth/me` au boot | Redirection `/login` silencieuse (pas d'écran d'erreur). |
| **403** (route ou API) | garde route ou réponse API | Page dédiée : titre « Accès refusé », sous-titre factuel (« Ce contenu est réservé au rôle administrateur du cabinet. »), `request_id` en mono (copiable), boutons « Tableau de bord » / « Mes missions » selon rôle. Le contenu interdit n'est jamais rendu partiellement. |
| **404** (route ou ressource) | — | Page dédiée : titre « Page introuvable », texte « Cette ressource n'existe pas ou vous n'y avez pas accès. », boutons d'accueil selon rôle. Identique que l'ID soit faux ou hors périmètre (pas de fuite d'existence). |
| **5xx / réseau** | — | Bloc d'erreur inline (pas de plein écran, sauf 5xx sur page) : message, `request_id`, bouton « Réessayer » (re-query). Sur l'erreur de bord global React : écran 500 avec « Réessayer » (rechargement) et le `request_id` si disponible. |

---

## 4. Composants transverses et états globaux

### 4.1 États (obligatoires sur toute page avec données)

- **Chargement** : squelettes (formes grises `surface-muted`, sans pulsation si `prefers-reduced-motion`) aux dimensions exactes du contenu ; tableaux : 5 lignes fantômes ; graphe : spinner centré + « Chargement du graphe… » sur canvas plein (`aria-busy="true"`). Jamais de bouton d'action actif pendant un chargement qui mute la vue (boutons en état `loading` : spinner interne, désactivés).
- **Vide** : centré, écusson filaire 48 px + titre 14/600 + explication opérationnelle 12 px + CTA si le rôle autorise (ex. « Créer une mission »). Le vide est toujours explicatif, jamais « Aucun résultat » seul.
- **Erreur** : bloc inline `danger-soft` bordé `danger/30`, icône 16 px, message 14 px, `request_id` mono 12 px, bouton fantôme « Réessayer ». Sur les listes, l'erreur remplace le corps de la liste mais garde les filtres (réessayable sans reperdre le contexte).
- **Succès** : toast haut-droite (voir 4.6). Pas d'écran de succès dédié hormis auth (redirection immédiate + toast sur la page cible : « Mission créée. »).

### 4.2 Table de données

- En-tête sticky, fond `surface-muted`, libellés 12/600 uppercase tracking 0.04 em ; colonnes triables : flèche `aria-sort` (aucune / ascendante / descendante), tri par clic ou Entrée.
- Lignes 40 px (32 px en audit), survol `hover`, sélection `selected` ; bordure inférieure `border`.
- Barre de filtres au-dessus (recherche + selects + chips actives comptabilisées : « Statut: En cours × ») ; « Réinitialiser » si ≥ 1 filtre.
- Pagination pied de tableau : « 1–20 sur 132 » + Préc./Suiv. (boutons, focusables), état vide géré à part.
- Actions de ligne : menu « ⋮ » en dernier (ouvert par clic ou Entrée, navigation flèches, Échap referme) — chaque action est accessible sans la souris.
- ARIA : `<table>` sémantique, `<th scope="col">`, `caption` visuellement caché sur chaque tableau (ex. « Constats de la mission X »).

### 4.3 Chips et badges

| Chip | Format | Usage |
|---|---|---|
| Sévérité | pastille 10 px + label, fond `sev-*-soft`, texte `sev-*-ink`, `radius-pill` | colonnes sévérité, KPI, légende graphe |
| Statut constat | point + label, fond `st-*-soft` / texte `st-*-ink`, `radius-sm` | tables constats, détail |
| Statut mission | label avec icône (brouillon / play / cadenas), fond `mi-*-soft` | tables missions, en-tête détail |
| Publication | icône œil/œil barré + « Publié le 12/05 » ou « Non publié », texte `ink-soft`/`ink-faint` | tables constats, détail |
| Criticité (graphe) | carré 18 px `radius-2xs`, fond `surface`, bord 1.5 px, chiffre 12/700 mono ; teinte du bord = échelle grise→critique (1: `ink-faint`, 5: `sev-critical`) | nœuds du graphe |
| Rôle | pastille de texte 11 px uppercase `ink-soft` (`TENANT ADMIN`, `PENTESTER`, `CLIENT`, `PLATFORM`) | sidebar, espace, comptes plateforme |

### 4.4 Formulaires

- `label` visible 12/500 au-dessus du champ (jamais de placeholder comme label) ; champ requis : `*` + `aria-required` ; aide 12 px `ink-faint` sous le champ.
- Input 36 px, `radius-sm`, bordure `border-strong` au focus actif ; erreur : bordure `danger`, message 12 px `danger` avec icône, `aria-invalid` + `aria-describedby` pointant le message.
- Validation : à la soumission + au blur pour les champs déjà modifiés ; CVSS : nombre 0–10, 1 décimale, message précis (« CVSS doit être entre 0.0 et 10.0 »).
- Soumission : bouton primaire en état de chargement (spinner, désactivé) ; échec 4xx → erreurs inline ; 429 → message « Trop de requêtes. Réessayez dans un instant. » ; 5xx → bloc d'erreur + « Réessayer ».
- Un formulaire = une ressource = une mutation : pas de « Sauvegarder + publier » combiné.

### 4.5 Modales et confirmations

- Confirmation simple : 480 px, titre 16/600, corps 14, [Annuler] fantôme + [Confirmer] primaire (ou `danger` si destructif) ; focus sur le bouton le plus sûr, trap de focus, Échap = annuler, clic fond = ne ferme pas (sécurité).
- Confirmation destructrice (suppression) : nom de la ressource en mono 13 px dans le corps, avertissement de conséquences, bouton `danger`. Le bouton « Supprimer » ne ferme pas, il soumet ; en cas d'erreur, la modale reste ouverte avec le message.
- Formulaire : 640 px, titre 16/600, sections en `fieldset` si > 6 champs.
- **Confirmations obligatoires** (liste exhaustive) :
  1. Suppression d'un actif (cascading edges mentionné).
  2. Suppression d'un edge du graphe.
  3. Suppression d'un constat (preuves et relations mentionnées).
  4. **Publication** d'un constat : « Publier « Titre » pour **ClientOrg** ? Le constat et ses preuves visibles seront consultables immédiatement par le client. »
  5. **Rétractation** : « Le constat et ses preuves visibles seront immédiatement masqués au client. »
  6. Passage du statut à **REMEDIATED** : « Ce constat sera exclu des chemins actifs du graphe. »
  7. **Clôture de mission** : « La mission passera en lecture seule pour le cabinet (réouverture par un administrateur uniquement). »
  8. Suspension / réactivation d'un tenant (plateforme) ; désactivation d'un compte (plateforme).
  9. **Envoi d'invitation** (membre de cabinet ou compte client) : récapitulatif destinataire + rôle + durée de validité du lien (« Le lien est valable 7 jours et utilisable une fois. »).

### 4.6 Notifications (toast)

- Haut-droite, pile max 4, largeur 320 px, icône + texte 13/500, auto-dismiss 5 s, barre de progression fine, bouton ×.
- `role="status"` `aria-live="polite"` ; pas de toast pour une erreur bloquante (celle-ci est inline).
- Texte = action passée accomplie : « Constat publié. », « Invitation envoyée à a@b.c. », « Position du nœud enregistrée. »

### 4.7 Carte KPI

- 12 px padding, `radius-md`, bordure `border`, fond `surface` ; label 12 px uppercase `ink-faint`, valeur 24/600 (mono si nombre technique), sous-ligne 12 px de contexte (« +3 cette semaine », « sur 4 missions actives »).
- KPI cliquable = fond `selected` + flèche chevron ; il applique le filtre équivalent sur la page cible (ex. KPI « Constats ouverts HIGH » → liste des constats filtrée).

---

## 5. Spécification des 9 pages (spec §7)

### P1 — Authentification (`/login`, `/forgot`, `/reset`, `/invite`)

- **Rôles** : anonyme (+ invitation).
- **Blocs** : carte centrée 400 px sur `canvas`, écusson 32 px, logotype, titre 20/600. Login : e-mail, mot de passe (bouton afficher/masquer), lien « Mot de passe oublié ? ». `/forgot` : e-mail seul → écran neutre « Si un compte existe pour cette adresse, un lien a été envoyé. » (aucune énumération). `/reset` : nouveau mot de passe + confirmation. `/invite?token=…` : entête « Invitation au cabinet X » ou « Invitation au portail client de Y » + chip rôle + mot de passe + confirmation ; à l'acceptation, connexion automatique.
- **Actions primaires** : « Se connecter », « Envoyer le lien », « Réinitialiser », « Accepter l'invitation ».
- **États** : chargement (bouton spinner) ; erreur auth (bandeau non révélateur) ; invitation expirée/consommée (état dédié : « Ce lien a expiré ou a déjà été utilisé. » + lien vers login) ; succès = redirection par rôle (ou `/workspace`).
- **Interdits** : révéler l'existence d'un compte ; pré-remplir un e-mail depuis l'URL hors invitation ; conserver `next` en clair si pointant vers `/platform` ou `/client` (vérification côté serveur post-login : la redirection vers une app non autorisée retombe sur `/workspace`).

### P2 — Tableau de bord cabinet (`/`)

- **Rôles** : TENANT_ADMIN, PENTESTER.
- **Blocs** :
  1. **Rangée KPI (4)** : Missions actives · Constats ouverts (mini-barre empilée par sévérité) · Chemins actifs (somme des missions actives) · Constats publiés. Chacune cliquable → liste filtrée.
  2. **Missions** : tableau (nom, client, statut, constats, chemins actifs, modifiée) + filtres statut/client + recherche.
  3. **Activité récente** (TENANT_ADMIN uniquement, depuis `/audit-events` top 10) : icône action + « publication de CON-12 » + timestamp relatif + « Tout voir → ».
- **Actions primaires** : « Nouvelle mission » (formulaire de création, 4.5), ouvrir une mission.
- **États** : vide (aucune mission : CTA création) ; chargement (squelettes KPI + lignes) ; erreur (bloc inline + Réessayer, les KPI passent en état d'erreur « — ») ; succès (toasts sur création).
- **Interdits** : bloc activité pour le PENTESTER (endpoint admin-only — l'item n'existe pas dans le DOM) ; aucun chiffre de KPI calculé « à la main » au-delà de l'agrégation des réponses API existantes (missions, constats, `graph/paths`) ; si un endpoint d'agrégation dédié s'avère nécessaire, décision Tech Lead (issue de suivi), pas d'improvisation de contrat.

### P3 — Espace clients du cabinet (`/clients`, `/clients/:id`)

- **Rôles** : TENANT_ADMIN (lecture + gestion), PENTESTER (lecture seule pour naviguer vers ses missions).
- **Blocs liste** : tableau (nom, missions, membres, créés) + recherche + « Nouveau client » (modale 480 px : nom unique).
- **Blocs détail** : en-tête (nom, chip « Client org ») ; **Membres & invitations** (tableau : e-mail, chip rôle CLIENT, statut actif/`En attente` + date d'expiration, actions « Copier le lien » / « Expired » sans action) + bouton « Inviter » (modale : e-mail, info « lien valable 7 jours, utilisable une fois ») ; **Missions** (tableau avec statuts, lien vers chaque mission).
- **Confirmations** : envoi d'invitation (modale 4.5-9, mention durée).
- **États** : vide (aucun client : CTA) ; invitations expirées : chip gris, non actionnables ; erreur/chargement standards.
- **Interdits** : PENTESTER ne voit aucun bouton d'invitation ni de création ; pas de suppression de client (aucun endpoint DELETE clients) ; pas de champ d'information de contact libre hors du nom (pas de collecte de données inutiles).

### P4 — Espace missions (`/missions`, `/missions/new`, `/missions/:id`)

- **Rôles** : TENANT_ADMIN (gestion complète), PENTESTER (travaux techniques, sans clôture/réouverture).
- **Liste** : tableau (nom, client, statut mission, constats, chemins actifs, modifiée) + filtres (statut, client) + recherche + « Nouvelle mission ».
- **Création** (page `/missions/new` plutôt que modale, 4 champs) : nom, client (select), portée (textarea, multi-lignes), statut verrouillé `DRAFT`.
- **Détail** : en-tête (nom, client, chip statut, portée 12 px), actions contextuelles : `DRAFT` → « Démarrer » ; `IN_PROGRESS` → « Fermer la mission » (confirm. 4.5-7) — visible TENANT_ADMIN, masquée PENTESTER ; `CLOSED` → bandeau lecture seule + « Rouvrir » (TENANT_ADMIN, confirmation).
- **Onglets** : `Actifs` · `Constats` · `Graphe`.
  - *Actifs* : tableau (nom, type, criticité (badge 4.3), drapeaux : icône porte (entrée) / icône écusson (cible) + `aria-label`, position x/y en mono 12 px) + « Ajouter un actif » (modale 640 : nom, type select, criticité slider 1–5 avec prévisualisation du badge, checkboxes entrée/cible, description) + menu ligne (Modifier, Supprimer → confirm. 4.5-1).
  - *Constats* : tableau (titre, sévérité, CVSS mono, statut, publication, modifiée) + filtres (sévérité, statut, publication) + « Nouveau constat » (page dédiée 2 colonnes : titre, sévérité (radio-chips), CVSS, description, impact, recommandation, statut par défaut `OPEN`) + menu ligne (Ouvrir, Modifier statut, Supprimer → confirm. 4.5-3).
- **États** : vide (aucun actif → CTA ; aucun constat → CTA « Documenter le premier constat ») ; `CLOSED` : bandeau permanent + tous les onglets en lecture seule (boutons de mutation absents du DOM, 3.5-2) ; erreur/chargement standards.
- **Interdits** : client changer un statut (route inexistante côté portail) ; PENTESTER clore/rouvrir ; éditer la portée après `IN_PROGRESS` (lecture seule dans l'en-tête) ; aucun affichage de chemins calculés côté client (les comptes « chemins actifs » viennent de `graph/paths`).

### P5 — Détail d'un constat (`/missions/:id/findings/:fid`)

- **Rôles** : cabinet (mutation selon permissions), CLIENT_VIEWER (version lecture seule, même URL de portail `/client/…` — voir P7).
- **Blocs (cabinet)** :
  1. **En-tête** : titre 20/600, chip sévérité (large, avec CVSS mono 16 px à droite), chip statut, chip publication, barre CVSS 0–10 (repère à la valeur, graduée 0/2.5/5/7.5/10).
  2. **Corps** : Description / Impact / Recommandation (sections 14/1.5, titres 14/600 ; texte rendu échappé, jamais de HTML brut).
  3. **Actions** (colonne droite ou barre sticky) : « Modifier le statut » (menu : **Ouvert**, **En cours**, **Corrigé** → confirm. 4.5-6, **Risque accepté** + info « reste exploitable dans les chemins actifs » ; valeurs d'enum envoyées : `OPEN`, `IN_PROGRESS`, `REMEDIATED`, `ACCEPTED_RISK`), « Publier » / « Rétracter » (confirm. 4.5-4/5), « Modifier » (page formulaire), « Supprimer » (confirm. 4.5-3, danger).
  4. **Preuves** : liste (fichier, type, taille, hash court mono, date, chip « Visible client » si `client_visible`) + « Ajouter une preuve » (modale : drag-drop/fichier, types PDF/PNG/JPEG/TXT, 10 Mio max, checkbox « visible par le client » non cochée par défaut) + téléchargement via route autorisée (bouton, jamais de lien direct au stockage).
  5. **Relations dans le graphe** : liste source → cible (noms d'actifs) + « Voir dans le graphe » (redirige `/missions/:id/graph` avec focus sur l'edge concerné).
  6. **Méta** : auteur, créé, modifié, publié le (si publié), engagement, client org.
- **États** : non publié = bandeau discret « Non publié au client » dans l'en-tête ; `REMEDIATED` = bandeau vert « Corrige : les chemins utilisant ce constat sont inactivés. » ; erreur/chargement standards ; 404 si hors périmètre.
- **Interdits (portail client, cf. P7)** : aucun bouton de mutation, pas de champ interne, pas de liste de relations du graphe, pas de preuve non `client_visible`, pas de hash ni ID techniques au-delà du titre de preuve.

### P6 — Graphe interactif (`/missions/:id/graph`)

→ spécification complète en **§6** (langage visuel, interactions, états, bonus §8).

### P7 — Portail client (`/client`, `/client/m/:id`, `/client/m/:id/f/:fid`)

- **Rôle** : CLIENT_VIEWER (lecture seule, app séparée 3.3).
- **Mes missions** : liste des missions de sa ClientOrg (nom, chip statut mission, constats **publiés** (count), preuves publiées (count), dernière publication) + carte récap « X missions · Y constats publiés · Z preuves disponibles ».
- **Détail mission** : en-tête (nom, chip statut, portée en lecture), **Constats publiés** (tableau : titre, sévérité, CVSS, statut, « Publié le … », preuve dispo) + détail constat (P5 version publique : description/impact/recommandation + preuve « Télécharger » si `client_visible`) .
- **États** : vide pédagogique (« Aucun résultat publié pour le moment. Votre cabinet vous informera dès qu'un constat sera publié. ») ; chargement ; erreur + réessayer.
- **Interdits** : **aucun bouton de mutation dans le DOM** (ni masqué, ni désactivé) ; aucun non publié (constat, preuve) — pas même en `title`/attribut ; pas de graphe, pas d'audit, pas de membres du cabinet, pas de « notes internes » ; pas de champ de modification de statut ; le chip « Portail client » est permanent.

### P8 — Administration plateforme (`/platform/tenants`, `/platform/users`)

- **Rôle** : PLATFORM_ADMIN (garde 3.4).
- **Tenants** : tableau (nom, slug mono, statut actif/suspendu, membres (count), créé le) + « Nouveau tenant » (modale 2 étapes : 1) nom + slug, 2) e-mail de l'admin à inviter — la 2ᵉ étape récapitule destinataire + rôle et vaut confirmation (4.5-9)) + menu ligne : Suspendre / Réactiver (confirm. 4.5-8 : « Les membres ne pourront plus se connecter ; les données sont conservées. »).
- **Comptes** : tableau (e-mail, statut actif/inactif, espaces (chips comptées : « 2 cabinets · 1 client » — **compteurs uniquement**, pas de détails), créé le) + menu ligne : Désactiver / Réactiver le compte (confirmation).
- **États** : vides (aucun tenant : CTA) ; erreur/chargement standards.
- **Interdits** : aucune lecture des données métiers (missions, constats, preuves, journaux tenant) — pas de lien, pas de colonne ; pas de modification d'un slug existant ; le détail d'un tenant s'ouvre seulement sur un sous-tableau de ses membres (e-mail + rôle), jamais sur ses ressources.

### P9 — Journal d'audit cabinet (`/audit`)

- **Rôle** : TENANT_ADMIN uniquement (PENTESTER → 403).
- **Blocs** : filtres (action (select multi : publication, suppression, login, invitation, changement de statut, téléchargement de preuve…), type de ressource, acteur, période (dates), recherche texte sur l'action) + tableau 32 px : horodatage (avec secondes, `text-xs`), acteur (initiales + nom), action (chip neutre 11 px `ink-soft`), ressource (type + id court mono, ex. `Finding f4a2…`), `request_id` (mono 12 px, copiable au clic).
- **Pagination** : `limit=50&offset` (dans la plage API `limit ≤ 100`), « Préc./Suiv. » + « 51–100 sur 1 234 ».
- **États** : vide (filtres trop restrictifs : « Aucun événement ne correspond. Réinitialiser les filtres. ») ; chargement ; erreur.
- **Interdits** : aucune metadata sensible (pas de corps de preuve, pas de description de constat, pas de token) ; pas d'export (bonus hors périmètre) ; pas d'action de correction dans le journal (append-only).

---

## 6. Graphe React Flow (`/missions/:id/graph`)

### 6.1 Principe

Le canvas **représente** la vérité serveur : actifs + positions, edges + leur constat, chemins actifs (résultat de `graph/paths`). Aucun calcul de chemin, aucun statut n'est réinventé côté client ; le style d'un edge découle uniquement du statut du constat retourné par l'API.

### 6.2 Nœuds (actifs)

| Type | Forme / contenu | Détails |
|---|---|---|
| Actif standard | rectangle 40 px haut, min 96 px large, `radius-sm`, fond `surface`, bordure `border-strong` 1 px | icône de type (14 px, `ink-soft`) + nom 13/500 (tronqué, `title` complet) + badge criticité en haut-droite |
| **Point d'entrée** | idem + liseré gauche 3 px `accent` + tag « ENTRÉE » (11 px, `accent-soft`/`accent`) | icône porte |
| **Cible critique (crown jewel)** | idem + tag « CIBLE » (`sev-critical-soft`/`sev-critical-ink`) + icône écusson `sev-critical` | le seul nœud avec liseré haut `sev-critical` 3 px |

- **Criticité 1–5** : badge carré 18 px (chiffre mono 12/700), teinte du bord et du chiffre : 1 `ink-faint` → 2 `ink-soft` → 3 `st-inprog` → 4 `sev-high` → 5 `sev-critical`. Criticité ≥ 4 : lueur (`box-shadow 0 0 12px 2px sev-high/35 %` ou `sev-critical/40 %`) — la lueur accompagne le badge, elle ne le remplace jamais (lisibilité au clavier et en impression).
- État sélectionné : anneau 2 px `focus` + `shadow-focus` ; état du chemin actif : anneau 2 px `accent` (voir 6.4).

### 6.3 Edges (relations)

- Orientées : flèche en bout (marker 12 px), trait 2 px.
- **Couleur = sévérité du constat** (`sev-low`…`sev-critical`), label centré : point de sévérité + titre du constat tronqué (max 24 caractères, `text-xs`), fond `surface` 80 % opaque `radius-2xs` pour la lisibilité.
- **Constat `REMEDIATED`** : trait pointillé `6 4`, couleur `ink-faint`, label avec préfixe « corrigé — » ; l'edge **n'appartient à aucun chemin actif** (cohérent avec le calcul serveur).
- **Constat `ACCEPTED_RISK`** : trait continu couleur sévérité + point violet sur le label (rappel : reste exploitable).
- Edge sélectionnée : épaisseur 3 px, `shadow` discrète, label complet.

### 6.4 Chemins actifs et surlignage

- **Panneau « Chemins actifs » (gauche, 280 px, repliable)** : liste ordonnée (score décroissant, comme l'API) ; chaque item : « P{n} · score {x} · {n} sauts · cible : {nom} », sous-ligne dépliable : la séquence actif → actif avec, à chaque saut, le chip sévérité + titre du constat. Item actif : fond `selected`, bord gauche `accent` 3 px.
- **Sélection d'un chemin** (clic item ou clic edge puis « Chemin ») : les edges du chemin passent à 3 px `accent` avec animation de pointillés défilants (désactivée si `prefers-reduced-motion`) ; les nœuds concernés : anneau `accent` ; le reste du canvas : opacité 0.35 (mode focus). La sélection est persistée dans l'URL (`?path={index}`) pour être partageable et réactivée au retour.
- **Clic nœud** : panneau latéral droit 320 px — nom, type, criticité (badge + « 4/5 »), drapeaux, constats associés (chips + CVSS mono), actions cabinet : « Modifier l'actif », « Supprimer » (confirmation), « Ouvrir la liste des actifs ».
- **Clic edge** : même panneau — titre du constat (lien détail P5), chip sévérité, CVSS, statut, publication, actions : « Ouvrir le constat », « Supprimer cette relation » (confirmation 4.5-2 : « La relation {source} → {cible} sera supprimée. Le constat reste sur la mission. »).
- **Édition** : bouton « Créer une relation » (mode édition) : clic source → clic cible → modale choix du constat (liste filtrable) → `POST edges` ; toast succès. Bouton « Supprimer » sur l'edge sélectionnée (id. confirmation).
- **Positionnement** : drag d'un nœud → déplacement optimiste + **PATCH debouncé 500 ms** ; échec → retour à l'ancienne position + toast « Échec de l'enregistrement de la position. »
- **Canvas** : fit-on-load, zoom molette/pincer, pan (space+drag), contrôles zoom + « Recentrer » en bas-droite ; **légende** en bas-gauche (repliable, `aria-label` « Légende du graphe ») : nœuds (standard/entrée/cible), criticité (échelle 1–5), edges (4 sévérités + pointillé corrigé), chemin actif.

### 6.5 États du graphe

- **Chargement** : spinner + texte, `aria-busy`.
- **Erreur** : bloc inline centré + Réessayer.
- **Vide — aucun actif** : CTA « Ajouter un actif » (navigue vers l'onglet Actifs).
- **Vide — actifs sans edges** : message « Aucune relation d'attaque définie. Créez un lien entre un point d'entrée et un actif cible. » + CTA « Créer une relation ».
- **« Aucun chemin actif » (état pédagogique, requis)** : le graphe reste affiché (les edges corrigées en pointillé gris sont visibles) + bandeau vert `success-soft` en haut du canvas : « **Aucun chemin actif vers la cible.** Un chemin actif relie un point d'entrée à un actif critique via des constats non corrigés. Tous les liens connus de cette mission passent par un constat corrigé ou accepté — le risque est traité ou assumé. » + bouton secondaire « Revoir l'état avant remédiation » (active le bonus §8). Jamais de chemin fictif dessiné (cohérent avec l'API : tableau vide = état vide).

### 6.6 Accessibilité du graphe (cf. §7)

Canvas `role="group"` `aria-label="Graphe d'attaque de la mission X"` ; résumé texte non visuel : « 5 actifs, 6 relations, 2 chemins actifs. » ; nœuds = boutons avec tabindex roving (flèches pour se déplacer entre nœuds quand le canvas a le focus, Entrée/Espace sélectionne, Échap ferme le panneau) ; le **panneau Chemins actifs est l'alternative complète au clavier** : on peut parcourir, sélectionner et ouvrir tous les constats du graphe sans toucher au canvas.

---

## 7. Accessibilité

1. **Clavier** : 100 % des parcours majeurs sans souris — login, sélection d'espace, création d'une mission, ajout d'un actif, création d'un constat, changement de statut, publication/rétractation, ajout/téléchargement de preuve, création/suppression d'une relation, sélection d'un chemin (panneau listé), navigation des tableaux (tri par Entrée, actions ligne via menu ⋹ focusable), filtres, pagination, modales (trap de focus, Échap), toasts (lecture `aria-live`).
2. **Focus visible** : anneau 2 px `focus` + offset 2 px sur tout élément interactif (`:focus-visible`), y compris nœuds/edges du graphe et items de liste ; jamais supprimé.
3. **Skip-link** : « Aller au contenu principal » en premier focusable de chaque page app.
4. **Label** : tout champ a un `<label>` visible ; les contrôles sans texte (⋮, ×, zoom) ont un `aria-label` ; les chips couleur seules sont interdites (texte ou icône sémantique toujours présents).
5. **Contraste AA** : paires du §2 vérifiées ≥ 4.5:1 (texte courant) et ≥ 3:1 (éléments UI). **Règle unique `ink-faint`** : réservé aux éléments non critiques (timestamps, aide de formulaire, `request_id`, badge de criticité) et toujours rendu en ≥ 12 px ; le palier 11 px ne sert qu'aux libellés uppercase et chips, en `ink-soft` ou plus foncé (cf. §1.4).
6. **Rôles ARIA** : tableaux sémantiques + `caption` + `scope="col"` + `aria-sort` ; modales `role="dialog"` `aria-modal` `aria-labelledby` ; toasts `role="status"` ; graphe `role="group"` + alternative textuelle (6.6) ; listes de chemins = `<ol>` natif (pas de `role` artificiel).
7. **Mouvement** : `prefers-reduced-motion` → pas de pointillés animés, pas de pulsation de squelette, pas de transition > 150 ms.
8. **Tablette** : cibles ≥ 44 px via padding, sidebar en rail (tooltip au focus), modales en bottom-sheet plein large si < 900 px, drag du graphe au doigt (pinch-zoom conservé).

---

## 8. Bonus UX — Vue « avant/après remédiation » du graphe

**Choix (parmi les 3 proposés)** : commutateur **« État : Aujourd'hui / Avant remédiation »** dans la barre d'outils du graphe (P6), par défaut « Aujourd'hui ».

- **Ce qu'il change (pure représentation)** : en mode « Avant remédiation », les edges dont le constat est `REMEDIATED` (déjà présentes dans la liste serveur, simplement rendues en pointillé gris en mode aujourd'hui) sont affichées en couleur sévérité avec le préfixe label « corrigé le {date} » ; un bandeau violet `st-accepted-soft` avertit « Vue historique — les chemins valides restent ceux calculés par le serveur ». En mode « Aujourd'hui », retour au socle. Le bouton « Revoir l'état avant remédiation » du bandeau « Aucun chemin actif » (6.5) active ce mode directement.
- **Utilité réelle** : montrer au cabinet (et au client, si le graphe est publié à l'avenir) ce que la remédiation a réellement coupé dans la chaîne d'attaque — la valeur pédagogique du produit, sans ajouter un seul endpoint.
- **Non-interférence avec le socle** : aucun calcul côté client (les chemins actifs restent 100 % issus de `graph/paths` ; le mode historique ne dessine jamais un « chemin actif » inactif, il ne rend que des edges existantes) ; états vides/erreurs identiques ; aucune donnée privée additionnelle exposée (les edges et leurs statuts sont déjà servis au cabinet) ; le commutateur est un control sémantique (label texte, état `aria-pressed`) donc pleinement accessible ; zéro impact sur les parcours obligatoires (désactivable en un clic, inactif si aucune edge corrigée — le toggle est simplement masqué).

---

## 9. Décisions ouvertes / suivi

- KPI agrégés du dashboard (P2) : endpoints existants vs endpoint dédié → Tech Lead (issue de suivi si nécessaire).
- **Comptes plateforme (P8, `/platform/users`)** : la liste des comptes avec compteurs d'espaces n'existe pas dans le contrat API minimal de la spec §6 (routes plateforme limitées à `/platform/tenants`, cf. issue #7). P8 n'est implémentable que si le Tech Lead définit un endpoint de lecture seule plateforme pour les comptes (issue de suivi, à planifier avec #7/CS-04) ; cette route n'est pas présentée ici comme existante.
- Nom des icônes d'actifs par type : choix d'un jeu d'icônes (Lucide, MIT) à la mise en œuvre, sans contrainte de ce document.
- Le thème sombre et l'export PDF du journal d'audit sont des non-livrés assumés (bonus hors périmètre de ce design).
