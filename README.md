# Budget Manager Pro V5

Application de gestion budgétaire DSI pour collectivités — Ville & CDA de La Rochelle.

## Stack
- Python 3.10+ / PyQt5
- SQLite

## Installation
```bash
pip install -r requirements.txt
```

## Premier lancement (migration base)
```bash
# Si migration depuis V4 :
python migrate_v5.py

# Si base corrompue ou vues manquantes :
python repair_v5.py

# Lancer l'application :
python run.py
```

## Structure
```
app/
  services/
    budget_v5_service.py     — Budgets, lignes, entités, applications
    contrat_service.py       — Contrats & marchés
    bon_commande_service.py  — Bons de commande + workflow validation/imputation
    database_service.py      — Connexion SQLite
    fournisseur_service.py   — Fournisseurs
    projet_service.py        — Projets
    contact_service.py       — Contacts
    ...
  ui/
    views/
      dashboard_view.py      — Tableau de bord
      budget_v5_view.py      — Budget annuel / lignes / applications / entités / N+1
      contrat_view.py        — Contrats & alertes échéance
      bon_commande_view.py   — Bons de commande
      projet_view.py         — Projets
      ...
    widgets/                 — Widgets dashboard
    dialogs/                 — Formulaires
  database/
    schema.py                — Schéma SQLite (référence)
```

## Modèle de données V5
```
ENTITÉS (Ville / CDA)
  └── BUDGETS ANNUELS (exercice × nature)
        └── LIGNES BUDGÉTAIRES (par application / projet)
              └── BONS DE COMMANDE (imputés sur lignes)
                    └── FACTURES

CONTRATS (liés à entité + application + BC)
APPLICATIONS (patrimoine applicatif DSI)
PROJETS (liés à entité + lignes budgétaires)
```

## Fonctionnalités
- Budget annuel par entité (Ville / CDA) — fonctionnement & investissement
- Lignes budgétaires par application ou projet avec suivi engage/solde
- Contrats & marchés : 5 types, reconductions, alertes échéance
- Bons de commande avec workflow validation → imputation → soldé
- Dashboard Ville vs CDA avec KPI temps réel
- Préparation budget N+1 depuis historique
- Gestion projets, tâches, kanban
- Contacts, fournisseurs, services
