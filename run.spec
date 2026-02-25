# -*- mode: python ; coding: utf-8 -*-
# Fichier .spec pour Budget-Manager-Pro-V5
# Remplace le fichier run.spec dans C:\Budget-Manager-Pro-V5\

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config/user_preferences.json', 'config'),
        ('budget.ico', '.'),
        ('data/budget_manager.db', 'data'),
        ('data', 'data'),
        ('backups', 'backups'),
        ('logs', 'logs'),
    ],
    hiddenimports=[
        # App core
        'app',
        'app.database',
        'app.database.schema',
        # Models
        'app.models',
        'app.models.contact',
        'app.models.fournisseur',
        'app.models.portefeuille',
        'app.models.service',
        # Services
        'app.services',
        'app.services.bon_commande_service',
        'app.services.budget_v5_service',
        'app.services.contact_service',
        'app.services.contrat_service',
        'app.services.database_service',
        'app.services.export_service',
        'app.services.fiche_projet_service',
        'app.services.fournisseur_service',
        'app.services.integrity_service',
        'app.services.iparapheur_connector',
        'app.services.notification_service',
        'app.services.projet_service',
        'app.services.service_service',
        'app.services.tache_service',
        'app.services.theme_service',
        # UI
        'app.ui',
        'app.ui.main_window',
        # Views
        'app.ui.views',
        'app.ui.views.dashboard_view',
        'app.ui.views.budget_v5_view',
        'app.ui.views.bon_commande_view',
        'app.ui.views.contrat_view',
        'app.ui.views.projet_view',
        'app.ui.views.tache_view',
        'app.ui.views.kanban_view',
        'app.ui.views.etp_view',
        'app.ui.views.fiche_bc_view',
        'app.ui.views.fournisseur_view',
        'app.ui.views.contact_view',
        'app.ui.views.service_view',
        # Dialogs
        'app.ui.dialogs',
        'app.ui.dialogs.contact_dialog',
        'app.ui.dialogs.contrat_dialog',
        'app.ui.dialogs.document_dialog',
        'app.ui.dialogs.fournisseur_dialog',
        'app.ui.dialogs.projet_dialog',
        'app.ui.dialogs.service_dialog',
        'app.ui.dialogs.tache_dialog',
        # Widgets
        'app.ui.widgets',
        'app.ui.widgets.base_widget',
        'app.ui.widgets.chart_widget',
        'app.ui.widgets.widget_config',
        # Config
        'config',
        'config.settings',
        'config.themes',
        # Dépendances externes
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.chart',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtPrintSupport',
        # Stdlib souvent manquant
        'sqlite3',
        'json',
        'datetime',
        'os',
        'sys',
        'logging',
        'shutil',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BudgetManagerPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # Pas de fenêtre noire
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='budget.ico',    # Ton icône
)
