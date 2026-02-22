# Budget Manager Pro V5 — Nouveau repo propre

## Prérequis

- Python 3.10+
- Git installé
- Accès GitHub (ou GitLab)

---

## ETAPE 1 — Créer le nouveau repo sur GitHub

1. Aller sur https://github.com/new
2. Nom : `Budget-Manager-Pro-V5`
3. Visibilité : **Private**
4. Ne pas initialiser avec README (on le fait localement)
5. Cliquer **Create repository**
6. Copier l'URL : `https://github.com/ArnaudP17000/Budget-Manager-Pro-V5.1`

---

## ETAPE 2 — Préparer le dossier local propre

Ouvrir un terminal (PowerShell ou cmd) et exécuter :

```powershell
# Aller dans votre dossier de travail
cd D:\

# Créer le nouveau dossier propre
mkdir Budget-Manager-Pro-V5.1
cd Budget-Manager-Pro-V5.1

# Copier UNIQUEMENT les fichiers utiles depuis l'ancien dossier
# (adapter le chemin source si nécessaire)
$SRC = "D:\Budget-Manager-Pro-V4.2-main"
$DST = "D:\Budget-Manager-Pro-V5"

# Fichiers racine
copy $SRC\run.py             $DST\
copy $SRC\requirements.txt  $DST\
copy $SRC\.gitignore         $DST\
copy $SRC\repair_v5.py       $DST\

# Structure app\
xcopy $SRC\app\__init__.py              $DST\app\ /Y
xcopy $SRC\app\database\               $DST\app\database\ /E /Y
xcopy $SRC\app\models\                 $DST\app\models\ /E /Y
xcopy $SRC\app\services\               $DST\app\services\ /E /Y
xcopy $SRC\app\ui\                     $DST\app\ui\ /E /Y
xcopy $SRC\config\                     $DST\config\ /E /Y
xcopy $SRC\docs\                       $DST\docs\ /E /Y

# Créer les dossiers nécessaires
mkdir $DST\data
mkdir $DST\backups
mkdir $DST\logs

# Créer les .gitkeep pour les dossiers vides
echo $null > $DST\data\.gitkeep
echo $null > $DST\backups\.gitkeep
echo $null > $DST\logs\.gitkeep
```

---

## ETAPE 3 — Supprimer les fichiers orphelins V4 du nouveau dossier

```powershell
cd D:\Budget-Manager-Pro-V5.1

# Services V4 obsolètes
del app\services\portefeuille_service.py
del app\services\reporting_service.py

# Dialogs V4 obsolètes
del app\ui\dialogs\bdc_dialog.py
del app\ui\dialogs\todo_dialog.py

# Widgets V4 obsolètes
del app\ui\widgets\alert_widget.py
del app\ui\widgets\kpi_widget.py
del app\ui\widgets\meteo_widget.py
del app\ui\widgets\notification_widget.py
del app\ui\widgets\project_widget.py
del app\ui\widgets\widget_manager.py

# Fichiers de migration/nettoyage (ne plus versionner)
del migrate_v5.py       2>nul
del create_test_data.py 2>nul
del push_all.ps1        2>nul
del cleanup_db_v5.py    2>nul
del cleanup_py_v5.py    2>nul

# Docs obsolètes
del docs\SCREENSHOTS.md       2>nul
del IMPLEMENTATION_COMPLETE.md 2>nul
del IMPLEMENTATION_SUMMARY.md  2>nul
```

---

## ETAPE 4 — Initialiser le repo Git local

```powershell
cd D:\Budget-Manager-Pro-V5.1

git init
git branch -M main

# Configurer votre identité (si pas déjà fait)
git config user.name  "ArnaudP17000"
git config user.email "arnaud.pheloup@agglo-larochelle.fr"
```

---

## ETAPE 5 — Premier commit

```powershell
cd D:\Budget-Manager-Pro-V5.1

# Ajouter tous les fichiers
git add .

# Vérifier ce qui sera commité
git status

# Premier commit
git commit -m "Initial commit — Budget Manager Pro V5 (code base propre)"
```

---

## ETAPE 6 — Pousser vers GitHub

```powershell
# Relier au repo GitHub créé à l'étape 1
git remote add origin https://github.com/ArnaudP17000/Budget-Manager-Pro-V5.1

# Pousser
git push -u origin main
```

---

## ETAPE 7 — Installation depuis zéro (sur un nouveau poste)

```powershell
# Cloner le repo
git clone https://github.com/ArnaudP17000/Budget-Manager-Pro-V5.1
cd Budget-Manager-Pro-V5.1

# Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la base de données
python repair_v5.py

# Lancer l'application
python run.py
```

---

## Structure finale du repo

```
Budget-Manager-Pro-V5.1/
├── run.py                          # Point d'entrée
├── repair_v5.py                    # Init/réparation base de données
├── requirements.txt                # Dépendances Python
├── .gitignore
│
├── app/
│   ├── database/
│   │   └── schema.py
│   ├── models/
│   │   ├── contact.py
│   │   ├── fournisseur.py
│   │   ├── portefeuille.py
│   │   └── service.py
│   ├── services/
│   │   ├── bon_commande_service.py
│   │   ├── budget_v5_service.py    # Budget annuels + lignes
│   │   ├── contact_service.py
│   │   ├── contrat_service.py
│   │   ├── database_service.py
│   │   ├── export_service.py       # Export Excel 5 onglets
│   │   ├── fournisseur_service.py
│   │   ├── integrity_service.py
│   │   ├── notification_service.py
│   │   ├── projet_service.py
│   │   ├── service_service.py
│   │   ├── tache_service.py
│   │   └── theme_service.py
│   └── ui/
│       ├── main_window.py
│       ├── dialogs/
│       │   ├── contact_dialog.py
│       │   ├── contrat_dialog.py
│       │   ├── document_dialog.py
│       │   ├── fournisseur_dialog.py
│       │   ├── projet_dialog.py
│       │   ├── service_dialog.py
│       │   └── tache_dialog.py
│       ├── views/
│       │   ├── bon_commande_view.py
│       │   ├── budget_v5_view.py
│       │   ├── contact_view.py
│       │   ├── contrat_view.py
│       │   ├── dashboard_view.py
│       │   ├── fiche_bc_view.py
│       │   ├── fournisseur_view.py
│       │   ├── kanban_view.py
│       │   ├── projet_view.py
│       │   ├── service_view.py
│       │   └── tache_view.py
│       └── widgets/
│           ├── base_widget.py
│           ├── chart_widget.py
│           └── widget_config.py
│
├── config/
│   ├── settings.py
│   └── themes.py
│
├── docs/
│   ├── GUIDE_DSI.md
│   ├── GUIDE_UTILISATEUR.md
│   └── COMPTABILITE_M57.md
│
├── data/                           # Ignoré par git (contient la DB)
│   └── .gitkeep
├── backups/                        # Ignoré par git
│   └── .gitkeep
└── logs/                           # Ignoré par git
    └── .gitkeep
```

---

## Workflow Git quotidien

```powershell
# Avant de travailler — récupérer les dernières modifs
git pull

# Après modification d'un ou plusieurs fichiers
git add app\services\export_service.py
git commit -m "fix: export Excel onglet N+1 toutes entités"
git push

# Voir l'historique
git log --oneline -10

# Annuler les modifs non commitées d'un fichier
git checkout -- app\services\export_service.py

# Créer une branche pour une nouvelle feature
git checkout -b feature/nouveau-rapport
# ... travail ...
git commit -m "feat: ajout rapport mensuel"
git push -u origin feature/nouveau-rapport
```

---

## .gitignore recommandé (déjà dans le projet)

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
venv/
env/

# Base de données — NE JAMAIS VERSIONNER
data/*.db
data/*.db-shm
data/*.db-wal
backups/
logs/

# Fichiers temporaires
*.log
cleanup_*.py
*_backup_*.db
backup_py_v4_*/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```