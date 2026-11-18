# Journal des interventions et amendements communs

Ce fichier doit être maintenu par le commanditaire **hors des dépôts des équipes**, puis chaque amendement validé est copié **mot pour mot** dans les deux dépôts avec sa date. Aucune note ne doit être attribuée avant la clôture des deux fenêtres.

## Format d'une intervention

```yaml
id: CS-CHANGE-0001
date_time_paris: "AAAA-MM-JJ HH:MM"
type: OBSERVATION | CLARIFICATION_COMMUNE | AJUSTEMENT_COMMUN | ASSISTANCE_ASYMETRIQUE
request: "Instruction exacte ou constat factuel"
changes_scope: false
priority: P0 | P1 | P2 | NONE
sent_to_A: "date/heure ou sans objet"
sent_to_B: "date/heure ou sans objet"
time_compensation_minutes_A: 0
time_compensation_minutes_B: 0
notes: "Impact sur la comparabilité"
```

## Exemples

**Observation :** « Montre l'état de ta CI et les PR en cours. » — Aucun changement, pas de note.

**Ajustement commun :** « Sur le graphe, un clic sur un edge doit afficher sa vulnérabilité associée ; priorité P1. » — Envoyer le même texte à A et B, noter la date.

**Assistance asymétrique :** « J'ai indiqué à l'équipe B que sa politique CORS était mauvaise et comment la réparer. » — Si ce conseil est donné seulement à B, le noter et distinguer cette aide dans l'analyse. La note brute d'autonomie n'est alors plus strictement comparable.

## Registre (vierge au lancement)

| ID | Date/heure | Classe | Instruction | A reçue | B reçue | Impact |
|---|---|---|---|---|---|---|
| | | | | | | |
