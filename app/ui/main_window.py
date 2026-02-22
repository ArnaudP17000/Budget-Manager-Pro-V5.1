"""
Fenêtre principale de l'application Budget Manager Pro V5.
"""
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QMenuBar, QMenu, QAction, QStatusBar, QMessageBox, QToolBar,
    QPushButton, QTabWidget, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

from config.settings import APP_TITLE
from app.services.theme_service import theme_service
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""

    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, 1400, 900)

        try:
            db_service.get_connection()
            logger.info("Base de données initialisée")
        except Exception as e:
            logger.error(f"Erreur initialisation base: {e}")
            QMessageBox.critical(self, "Erreur",
                f"Impossible d'initialiser la base de données:\n{e}")

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.create_tabs()
        self.create_menu()
        self.create_toolbar()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Prêt")

    def _add_tab(self, module_path, class_name, label):
        """Charge un onglet dynamiquement avec gestion d'erreur."""
        try:
            import importlib, traceback
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            view = cls()
            self.tabs.addTab(view, label)
            setattr(self, f"_view_{class_name}", view)
            logger.info(f"✅ Onglet {label} chargé")
            return view
        except Exception as e:
            import traceback
            logger.error(f"❌ Erreur {label}: {e}\n{traceback.format_exc()}")
            err = QLabel(f"{label} non disponible:\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setWordWrap(True)
            self.tabs.addTab(err, label)
            return None

    def create_tabs(self):
        # ── Workflow principal ─────────────────────────────────────────────
        self.dashboard_view = self._add_tab(
            "app.ui.views.dashboard_view", "DashboardView", "📊 Dashboard")

        self.budget_v5_view = self._add_tab(
            "app.ui.views.budget_v5_view", "BudgetV5View", "💰 Budget")

        self.bon_commande_view = self._add_tab(
            "app.ui.views.bon_commande_view", "BonCommandeView", "🛒 Bons de commande")

        self.contrat_view = self._add_tab(
            "app.ui.views.contrat_view", "ContratView", "📄 Contrats")

        self.projet_view = self._add_tab(
            "app.ui.views.projet_view", "ProjetView", "📁 Projets")

        self.tache_view = self._add_tab(
            "app.ui.views.tache_view", "TacheView", "✅ Tâches")

        self.kanban_view = self._add_tab(
            "app.ui.views.kanban_view", "KanbanView", "📋 Kanban")

        # ── Référentiels ──────────────────────────────────────────────────
        self.etp_view = self._add_tab(
            "app.ui.views.etp_view", "ETPView", "👤 ETP / Charge")

        self.fournisseur_view = self._add_tab(
            "app.ui.views.fournisseur_view", "FournisseurView", "🏢 Fournisseurs")

        self.contact_view = self._add_tab(
            "app.ui.views.contact_view", "ContactView", "📇 Contacts")

        self.service_view = self._add_tab(
            "app.ui.views.service_view", "ServiceView", "🏛️ Services")

    def _tab_index(self, view_attr):
        """Retourne l'index d'un onglet par son attribut."""
        view = getattr(self, view_attr, None)
        if view:
            return self.tabs.indexOf(view)
        return 0

    def create_menu(self):
        menubar = self.menuBar()

        # ── Fichier ────────────────────────────────────────────────────────
        file_menu = menubar.addMenu("&Fichier")
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # ── Affichage ──────────────────────────────────────────────────────
        view_menu = menubar.addMenu("&Affichage")
        for label, attr in [
            ("&Dashboard",       "dashboard_view"),
            ("&Budget",          "budget_v5_view"),
            ("&Bons de commande","bon_commande_view"),
            ("&Projets",         "projet_view"),
            ("&Tâches",          "tache_view"),
            ("&Kanban",          "kanban_view"),
        ]:
            a = QAction(label, self)
            a.triggered.connect(
                lambda _, x=attr: self.tabs.setCurrentIndex(self._tab_index(x)))
            view_menu.addAction(a)

        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("&Thème")
        for name in ("Clair", "Sombre"):
            a = QAction(name, self)
            a.triggered.connect(lambda _, n=name: self.change_theme(n))
            theme_menu.addAction(a)

        # ── Budget ────────────────────────────────────────────────────────
        budget_menu = menubar.addMenu("&Budget")

        new_budget_action = QAction("Nouveau &budget annuel", self)
        new_budget_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(self._tab_index("budget_v5_view")))
        budget_menu.addAction(new_budget_action)

        new_ligne_action = QAction("Nouvelle &ligne budgétaire", self)
        new_ligne_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(self._tab_index("budget_v5_view")))
        budget_menu.addAction(new_ligne_action)

        # ── Achats ────────────────────────────────────────────────────────
        achats_menu = menubar.addMenu("A&chats")

        bc_action = QAction("Nouveau &Bon de commande", self)
        bc_action.setShortcut("Ctrl+B")
        bc_action.triggered.connect(self.new_bc)
        achats_menu.addAction(bc_action)

        # ── Projets ───────────────────────────────────────────────────────
        projets_menu = menubar.addMenu("&Projets")

        new_projet_action = QAction("&Nouveau projet", self)
        new_projet_action.setShortcut("Ctrl+N")
        new_projet_action.triggered.connect(self.new_projet)
        projets_menu.addAction(new_projet_action)

        # ── Aide ──────────────────────────────────────────────────────────
        help_menu = menubar.addMenu("&Aide")
        about_action = QAction("À &propos", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        nav_items = [
            ("📊 Dashboard",     "dashboard_view"),
            ("💰 Budget",        "budget_v5_view"),
            ("🛒 Bons commande", "bon_commande_view"),
            ("📄 Contrats",      "contrat_view"),
            ("📁 Projets",       "projet_view"),
            ("✅ Tâches",        "tache_view"),
            ("📋 Kanban",        "kanban_view"),
        ]
        for label, attr in nav_items:
            btn = QPushButton(label)
            btn.clicked.connect(
                lambda _, x=attr: self.tabs.setCurrentIndex(self._tab_index(x)))
            toolbar.addWidget(btn)

        toolbar.addSeparator()

        btn_new_bc = QPushButton("➕ Nouveau BC")
        btn_new_bc.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 5px 10px;")
        btn_new_bc.clicked.connect(self.new_bc)
        toolbar.addWidget(btn_new_bc)

        btn_new_projet = QPushButton("➕ Nouveau projet")
        btn_new_projet.setStyleSheet(
            "background-color: #2980b9; color: white; font-weight: bold; padding: 5px 10px;")
        btn_new_projet.clicked.connect(self.new_projet)
        toolbar.addWidget(btn_new_projet)

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def new_projet(self):
        try:
            from app.ui.dialogs.projet_dialog import ProjetDialog
            dialog = ProjetDialog(self)
            if dialog.exec_():
                self.statusBar.showMessage("Projet créé", 3000)
                v = getattr(self, "projet_view", None)
                if v and hasattr(v, "load_projets"):
                    v.load_projets()
        except Exception as e:
            logger.error(f"Erreur création projet: {e}")
            QMessageBox.warning(self, "Erreur", str(e))

    def new_bc(self):
        try:
            # Ouvrir le bon dialog V5 via la vue BC
            v = getattr(self, "bon_commande_view", None)
            if v and hasattr(v, "_new_bc"):
                v._new_bc()
            else:
                # Fallback direct
                from app.ui.views.bon_commande_view import BonCommandeDialog
                dialog = BonCommandeDialog(parent=self)
                if dialog.exec_():
                    self.statusBar.showMessage("Bon de commande créé", 3000)
                    if v and hasattr(v, "load_data"):
                        v.load_data()
        except Exception as e:
            logger.error(f"Erreur création BC: {e}")
            QMessageBox.warning(self, "Erreur", str(e))

    def new_contrat(self):
        try:
            from app.ui.dialogs.contrat_dialog import ContratDialog
            dialog = ContratDialog(self)
            if dialog.exec_():
                self.statusBar.showMessage("Contrat créé", 3000)
        except Exception as e:
            logger.error(f"Erreur création contrat: {e}")
            QMessageBox.warning(self, "Erreur", str(e))

    def show_about(self):
        QMessageBox.about(self, "À propos",
            f"<h2>{APP_TITLE}</h2>"
            "<p>Gestion budgétaire DSI — Ville & CDA de La Rochelle</p>"
            "<p><b>Fonctionnalités :</b></p>"
            "<ul>"
            "<li>Budget annuel par entité (Ville / CDA) avec lignes budgétaires</li>"
            "<li>Bons de commande avec validation et imputation</li>"
            "<li>Suivi contrats avec alertes échéance</li>"
            "<li>Gestion de projets (Kanban, tâches)</li>"
            "<li>Patrimoine applicatif et fournisseurs</li>"
            "<li>Préparation budget N+1</li>"
            "</ul>"
        )

    def change_theme(self, theme_name):
        if theme_service.set_theme(theme_name):
            self.apply_theme()
            self.theme_changed.emit(theme_name)
            self.statusBar.showMessage(f"Thème : {theme_name}", 3000)

    def apply_theme(self):
        self.setStyleSheet(theme_service.get_stylesheet())
        logger.info(f"Thème appliqué: {theme_service.get_current_theme_name()}")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Quitter",
            "Voulez-vous vraiment quitter ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            db_service.close()
            event.accept()
        else:
            event.ignore()
