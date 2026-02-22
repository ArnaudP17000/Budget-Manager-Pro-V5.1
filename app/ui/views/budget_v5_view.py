"""
budget_v5_view.py — Vue Budget Manager V5
Onglet principal de gestion budgétaire adapté DSI collectivité.
Sous-onglets :
  1. Dashboard Ville / CDA
  2. Budgets annuels
  3. Lignes budgétaires
  4. Applications
  5. Préparation N+1
"""
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QSpinBox, QTextEdit, QGroupBox, QFrame,
    QSplitter, QScrollArea, QGridLayout, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class BudgetV5View(QWidget):
    """Vue principale gestion budgétaire V5."""

    def __init__(self):
        super().__init__()
        self.exercice_courant = datetime.now().year
        self.entite_filtre = None
        self._init_services()
        self.init_ui()
        self.load_all()

    def _init_services(self):
        try:
            from app.services.budget_v5_service import budget_v5_service
            self.svc = budget_v5_service
        except Exception as e:
            logger.error(f"Impossible de charger budget_v5_service : {e}")
            self.svc = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Barre de titre + filtres ──────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background-color: #1a252f; padding: 8px;")
        h_layout = QHBoxLayout(header)

        title = QLabel("💰 Gestion Budgétaire")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        h_layout.addWidget(title)

        h_layout.addStretch()

        lbl_ex = QLabel("Exercice :")
        lbl_ex.setStyleSheet("color: #bdc3c7;")
        h_layout.addWidget(lbl_ex)

        self.combo_exercice = QComboBox()
        self.combo_exercice.setMinimumWidth(90)
        for y in range(datetime.now().year + 1, datetime.now().year - 4, -1):
            self.combo_exercice.addItem(str(y))
        self.combo_exercice.setCurrentText(str(self.exercice_courant))
        self.combo_exercice.currentTextChanged.connect(self._on_exercice_change)
        h_layout.addWidget(self.combo_exercice)

        lbl_ent = QLabel("  Entité :")
        lbl_ent.setStyleSheet("color: #bdc3c7;")
        h_layout.addWidget(lbl_ent)

        self.combo_entite = QComboBox()
        self.combo_entite.setMinimumWidth(160)
        self.combo_entite.addItem("Toutes", None)
        self.combo_entite.currentIndexChanged.connect(self._on_entite_change)
        h_layout.addWidget(self.combo_entite)

        layout.addWidget(header)

        # ── Sous-onglets ──────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { padding: 8px 16px; font-weight: bold; }
            QTabBar::tab:selected { background: #2980b9; color: white; }
        """)

        self.tab_dashboard    = self._build_tab_dashboard()
        self.tab_budgets      = self._build_tab_budgets()
        self.tab_lignes       = self._build_tab_lignes()
        self.tab_applications = self._build_tab_applications()
        self.tab_n1           = self._build_tab_n1()

        self.tab_entites = self._build_tab_entites()

        self.tabs.addTab(self.tab_dashboard,    "📊 Tableau de bord")
        self.tabs.addTab(self.tab_budgets,      "📅 Budgets annuels")
        self.tabs.addTab(self.tab_lignes,       "📋 Lignes budgétaires")
        self.tabs.addTab(self.tab_applications, "💻 Applications")
        self.tabs.addTab(self.tab_n1,           "🔮 Préparer N+1")
        self.tabs.addTab(self.tab_entites,      "🏛️ Entités")

        layout.addWidget(self.tabs)

    # =========================================================================
    # ONGLET 1 — DASHBOARD VILLE vs CDA
    # =========================================================================

    def _build_tab_dashboard(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Bouton rafraîchir
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self.load_dashboard)
        btn_refresh.setStyleSheet(
            "background-color: #2980b9; color: white; font-weight: bold; padding: 6px 16px;")
        layout.addWidget(btn_refresh, alignment=Qt.AlignRight)

        # Zone scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.dashboard_content = QWidget()
        self.dashboard_layout  = QVBoxLayout(self.dashboard_content)
        scroll.setWidget(self.dashboard_content)
        layout.addWidget(scroll)

        return w

    def load_dashboard(self):
        # Vider
        while self.dashboard_layout.count():
            item = self.dashboard_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.svc:
            self.dashboard_layout.addWidget(QLabel("Service non disponible"))
            return

        try:
            data = self.svc.get_dashboard_data(self.exercice_courant)
        except Exception as e:
            self.dashboard_layout.addWidget(QLabel(f"Erreur : {e}"))
            return

        # ── KPI globaux ───────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        totaux = data.get('totaux_entites', {})
        for code, t in totaux.items():
            card = self._kpi_card(
                t.get('entite_nom', code),
                f"{t['montant_vote']:,.0f} €",
                f"{t['montant_engage']:,.0f} € engagés",
                f"Solde : {t['montant_solde']:,.0f} €",
                '#2980b9' if code == 'VILLE' else '#8e44ad'
            )
            kpi_row.addWidget(card)
        kpi_w = QWidget()
        kpi_w.setLayout(kpi_row)
        self.dashboard_layout.addWidget(kpi_w)

        # ── Synthèse par nature ───────────────────────────────────────────────
        lbl_synt = QLabel("Détail par nature de dépense")
        lbl_synt.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 12px;")
        self.dashboard_layout.addWidget(lbl_synt)

        synthese_tbl = QTableWidget()
        synthese_tbl.setColumnCount(7)
        synthese_tbl.setHorizontalHeaderLabels([
            "Entité", "Nature", "Prévisionnel", "Voté", "Engagé", "Solde", "Avancement"
        ])
        synthese_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        synthese_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        synthese_tbl.setMaximumHeight(200)

        synt = data.get('syntheses', [])
        synthese_tbl.setRowCount(len(synt))
        for r, s in enumerate(synt):
            vote   = float(s.get('montant_vote') or 0)
            engage = float(s.get('montant_engage') or 0)
            solde  = float(s.get('montant_solde') or 0)
            pct    = int(engage * 100 / vote) if vote else 0

            synthese_tbl.setItem(r, 0, QTableWidgetItem(s.get('entite_nom', '')))
            synthese_tbl.setItem(r, 1, QTableWidgetItem(s.get('nature', '')))
            synthese_tbl.setItem(r, 2, QTableWidgetItem(f"{float(s.get('montant_previsionnel') or 0):,.0f} €"))
            synthese_tbl.setItem(r, 3, QTableWidgetItem(f"{vote:,.0f} €"))
            synthese_tbl.setItem(r, 4, QTableWidgetItem(f"{engage:,.0f} €"))
            self._colored_item(synthese_tbl, r, 5, f"{solde:,.0f} €", solde)

            pb = QProgressBar()
            pb.setValue(min(pct, 100))
            pb.setStyleSheet(
                "QProgressBar::chunk { background: #e74c3c; }" if pct >= 80
                else "QProgressBar::chunk { background: #2ecc71; }"
            )
            pb.setFormat(f"{pct}%")
            synthese_tbl.setCellWidget(r, 6, pb)

        self.dashboard_layout.addWidget(synthese_tbl)

        # ── Alertes contrats ──────────────────────────────────────────────────
        alertes = data.get('alertes_contrats', [])
        if alertes:
            lbl_al = QLabel(f"⚠️  Alertes contrats ({len(alertes)})")
            lbl_al.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #e67e22; margin-top: 12px;")
            self.dashboard_layout.addWidget(lbl_al)

            al_tbl = QTableWidget()
            al_tbl.setColumnCount(6)
            al_tbl.setHorizontalHeaderLabels([
                "Entité", "Contrat", "Fournisseur", "Fin", "Jours restants", "Niveau"
            ])
            al_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            al_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            al_tbl.setMaximumHeight(150)
            al_tbl.setRowCount(len(alertes))
            colors = {'EXPIRE': '#e74c3c', 'CRITIQUE': '#e67e22',
                      'ATTENTION': '#f39c12', 'INFO': '#3498db'}
            for r, a in enumerate(alertes):
                niveau = a.get('niveau_alerte', 'INFO')
                al_tbl.setItem(r, 0, QTableWidgetItem(a.get('entite_code', '')))
                al_tbl.setItem(r, 1, QTableWidgetItem(a.get('numero_contrat', '')))
                al_tbl.setItem(r, 2, QTableWidgetItem(a.get('fournisseur_nom', '')))
                al_tbl.setItem(r, 3, QTableWidgetItem(str(a.get('date_fin', ''))))
                al_tbl.setItem(r, 4, QTableWidgetItem(str(a.get('jours_restants', ''))))
                niv_item = QTableWidgetItem(niveau)
                niv_item.setBackground(QColor(colors.get(niveau, '#95a5a6')))
                niv_item.setForeground(QColor('#ffffff'))
                al_tbl.setItem(r, 5, niv_item)
            self.dashboard_layout.addWidget(al_tbl)

        # ── BC en attente ─────────────────────────────────────────────────────
        bc_att = data.get('bc_attente', [])
        if bc_att:
            lbl_bc = QLabel(f"🕐 Bons de commande en attente de validation ({len(bc_att)})")
            lbl_bc.setStyleSheet(
                "font-size: 14px; font-weight: bold; margin-top: 12px;")
            self.dashboard_layout.addWidget(lbl_bc)

            bc_tbl = QTableWidget()
            bc_tbl.setColumnCount(5)
            bc_tbl.setHorizontalHeaderLabels(
                ["Entité", "N° BC", "Objet", "Fournisseur", "Montant TTC"])
            bc_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            bc_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            bc_tbl.setMaximumHeight(150)
            bc_tbl.setRowCount(len(bc_att))
            for r, bc in enumerate(bc_att):
                bc_tbl.setItem(r, 0, QTableWidgetItem(bc.get('entite_code', '')))
                bc_tbl.setItem(r, 1, QTableWidgetItem(bc.get('numero_bc', '')))
                bc_tbl.setItem(r, 2, QTableWidgetItem(bc.get('objet', '')[:50]))
                bc_tbl.setItem(r, 3, QTableWidgetItem(bc.get('fournisseur_nom', '')))
                bc_tbl.setItem(r, 4, QTableWidgetItem(
                    f"{float(bc.get('montant_ttc') or 0):,.2f} €"))
            self.dashboard_layout.addWidget(bc_tbl)

        self.dashboard_layout.addStretch()

    def _kpi_card(self, title, value, sub1, sub2, color):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background: {color}; border-radius: 8px;
                padding: 12px; margin: 4px;
            }}
        """)
        lay = QVBoxLayout(card)
        t = QLabel(title)
        t.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        v = QLabel(value)
        v.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        s1 = QLabel(sub1)
        s1.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 11px;")
        s2 = QLabel(sub2)
        s2.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 11px;")
        for w in (t, v, s1, s2):
            lay.addWidget(w)
        return card

    def _colored_item(self, tbl, row, col, text, value):
        item = QTableWidgetItem(text)
        if value < 0:
            item.setForeground(QColor('#e74c3c'))
        elif value < 1000:
            item.setForeground(QColor('#e67e22'))
        else:
            item.setForeground(QColor('#2ecc71'))
        tbl.setItem(row, col, item)

    # =========================================================================
    # ONGLET 2 — BUDGETS ANNUELS
    # =========================================================================

    def _build_tab_budgets(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_new = QPushButton("➕ Nouveau budget")
        btn_new.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 7px 14px;")
        btn_new.clicked.connect(self._new_budget)
        toolbar.addWidget(btn_new)

        btn_export = QPushButton("📊 Export Excel")
        btn_export.setStyleSheet(
            "background-color: #16a085; color: white; font-weight: bold; padding: 7px 14px;")
        btn_export.clicked.connect(self._export_excel)
        toolbar.addWidget(btn_export)

        self.btn_edit_budget = QPushButton("✏️ Modifier")
        self.btn_edit_budget.setStyleSheet(
            "background-color: #3498db; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_edit_budget.clicked.connect(self._edit_budget)
        self.btn_edit_budget.setEnabled(False)
        toolbar.addWidget(self.btn_edit_budget)

        self.btn_voter_budget = QPushButton("🗳️ Enregistrer vote")
        self.btn_voter_budget.setStyleSheet(
            "background-color: #8e44ad; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_voter_budget.clicked.connect(self._voter_budget)
        self.btn_voter_budget.setEnabled(False)
        toolbar.addWidget(self.btn_voter_budget)

        self.btn_del_budget = QPushButton("🗑️ Supprimer")
        self.btn_del_budget.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_del_budget.clicked.connect(self._delete_budget)
        self.btn_del_budget.setEnabled(False)
        toolbar.addWidget(self.btn_del_budget)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tableau budgets
        self.tbl_budgets = QTableWidget()
        self.tbl_budgets.setColumnCount(8)
        self.tbl_budgets.setHorizontalHeaderLabels([
            "ID", "Entité", "Exercice", "Nature", "Prévisionnel",
            "Voté", "Engagé", "Statut"
        ])
        self.tbl_budgets.setColumnHidden(0, True)
        hdr = self.tbl_budgets.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        hdr.setDefaultSectionSize(130)
        self.tbl_budgets.setColumnWidth(1, 200)  # Entité
        self.tbl_budgets.setColumnWidth(2, 80)   # Exercice
        self.tbl_budgets.setColumnWidth(3, 150)  # Nature
        self.tbl_budgets.setColumnWidth(4, 130)  # Prévisionnel
        self.tbl_budgets.setColumnWidth(5, 120)  # Voté
        self.tbl_budgets.setColumnWidth(6, 120)  # Engagé
        self.tbl_budgets.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_budgets.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_budgets.itemSelectionChanged.connect(self._on_budget_selection)
        self.tbl_budgets.doubleClicked.connect(self._edit_budget)
        layout.addWidget(self.tbl_budgets)

        return w

    def load_budgets(self):
        if not self.svc:
            return
        budgets = self.svc.get_budgets(self.exercice_courant)
        self.tbl_budgets.setRowCount(len(budgets))
        statut_colors = {
            'EN_PREPARATION': '#95a5a6', 'SOUMIS': '#f39c12',
            'VOTE': '#2ecc71', 'CLOTURE': '#7f8c8d'
        }
        for r, b in enumerate(budgets):
            vote   = float(b.get('montant_vote') or 0)
            engage = float(b.get('montant_engage') or 0)

            id_item = QTableWidgetItem(str(b['id']))
            id_item.setData(Qt.UserRole, b['id'])
            self.tbl_budgets.setItem(r, 0, id_item)
            self.tbl_budgets.setItem(r, 1, QTableWidgetItem(b.get('entite_nom', '')))
            self.tbl_budgets.setItem(r, 2, QTableWidgetItem(str(b.get('exercice', ''))))
            self.tbl_budgets.setItem(r, 3, QTableWidgetItem(b.get('nature', '')))
            self.tbl_budgets.setItem(r, 4, QTableWidgetItem(
                f"{float(b.get('montant_previsionnel') or 0):,.0f} €"))
            self.tbl_budgets.setItem(r, 5, QTableWidgetItem(f"{vote:,.0f} €"))
            self.tbl_budgets.setItem(r, 6, QTableWidgetItem(f"{engage:,.0f} €"))

            statut = b.get('statut', '')
            st_item = QTableWidgetItem(statut)
            st_item.setBackground(QColor(statut_colors.get(statut, '#95a5a6')))
            st_item.setForeground(QColor('#ffffff'))
            self.tbl_budgets.setItem(r, 7, st_item)

    def _on_budget_selection(self):
        has = self.tbl_budgets.currentRow() >= 0
        self.btn_edit_budget.setEnabled(has)
        self.btn_voter_budget.setEnabled(has)
        self.btn_del_budget.setEnabled(has)

    def _new_budget(self):
        if not self.svc:
            return
        dlg = BudgetDialog(self.svc, parent=self)
        if dlg.exec_():
            self.load_budgets()

    def _edit_budget(self):
        row = self.tbl_budgets.currentRow()
        if row < 0 or not self.svc:
            return
        budget_id = self.tbl_budgets.item(row, 0).data(Qt.UserRole)
        budget    = self.svc.get_budget_by_id(budget_id)
        if not budget:
            return
        dlg = BudgetDialog(self.svc, budget=budget, parent=self)
        if dlg.exec_():
            self.load_budgets()
            self.load_lignes()

    def _delete_budget(self):
        row = self.tbl_budgets.currentRow()
        if row < 0 or not self.svc:
            return
        budget_id = self.tbl_budgets.item(row, 0).data(Qt.UserRole)
        entite    = self.tbl_budgets.item(row, 1).text()
        nature    = self.tbl_budgets.item(row, 3).text()
        exercice  = self.tbl_budgets.item(row, 2).text()
        # Vérifier si des lignes y sont rattachées
        lignes = self.svc.get_lignes(budget_id=budget_id)
        if lignes:
            QMessageBox.warning(self, "Impossible",
                f"Ce budget contient {len(lignes)} ligne(s) budgétaire(s).\n"
                "Supprimez d'abord les lignes avant de supprimer le budget.")
            return
        reply = QMessageBox.question(self, "Supprimer",
            f"Supprimer le budget {nature} {exercice} — {entite} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            conn = self.svc.db.get_connection()
            conn.execute("DELETE FROM budgets_annuels WHERE id=?", (budget_id,))
            conn.commit()
            self.load_budgets()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _voter_budget(self):
        row = self.tbl_budgets.currentRow()
        if row < 0:
            return
        budget_id = self.tbl_budgets.item(row, 0).data(Qt.UserRole)

        from PyQt5.QtWidgets import QInputDialog
        montant, ok = QInputDialog.getDouble(
            self, "Vote du budget",
            "Montant voté par les élus (€) :",
            0, 0, 99999999, 2)
        if ok and montant > 0:
            self.svc.voter_budget(budget_id, montant)
            QMessageBox.information(self, "Vote enregistré",
                f"Budget voté : {montant:,.2f} €")
            self.load_budgets()

    # =========================================================================
    # ONGLET 3 — LIGNES BUDGÉTAIRES
    # =========================================================================

    def _build_tab_lignes(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Filtre budget
        filtre_row = QHBoxLayout()
        filtre_row.addWidget(QLabel("Budget :"))
        self.combo_budget_lignes = QComboBox()
        self.combo_budget_lignes.setMinimumWidth(280)
        self.combo_budget_lignes.currentIndexChanged.connect(self._on_budget_filtre_change)
        filtre_row.addWidget(self.combo_budget_lignes)
        filtre_row.addStretch()

        btn_new_ligne = QPushButton("➕ Nouvelle ligne")
        btn_new_ligne.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 7px 14px;")
        btn_new_ligne.clicked.connect(self._new_ligne)
        filtre_row.addWidget(btn_new_ligne)

        self.btn_edit_ligne = QPushButton("✏️ Modifier")
        self.btn_edit_ligne.setStyleSheet(
            "background-color: #3498db; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_edit_ligne.clicked.connect(self._edit_ligne)
        self.btn_edit_ligne.setEnabled(False)
        filtre_row.addWidget(self.btn_edit_ligne)

        self.btn_del_ligne = QPushButton("🗑️ Supprimer")
        self.btn_del_ligne.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_del_ligne.clicked.connect(self._delete_ligne)
        self.btn_del_ligne.setEnabled(False)
        filtre_row.addWidget(self.btn_del_ligne)

        layout.addLayout(filtre_row)

        # Tableau lignes
        self.tbl_lignes = QTableWidget()
        self.tbl_lignes.setColumnCount(11)
        self.tbl_lignes.setHorizontalHeaderLabels([
            "ID", "Libellé", "Application", "Fournisseur",
            "Voté", "Engagé", "Solde", "Taux %", "Alerte", "Référence D.S.I", "Budget imputé"
        ])
        self.tbl_lignes.setColumnHidden(0, True)
        hdr_l = self.tbl_lignes.horizontalHeader()
        hdr_l.setSectionResizeMode(QHeaderView.Interactive)
        hdr_l.setStretchLastSection(True)
        hdr_l.setDefaultSectionSize(110)
        self.tbl_lignes.setColumnWidth(1, 220)  # Libellé
        self.tbl_lignes.setColumnWidth(2, 130)  # Application
        self.tbl_lignes.setColumnWidth(3, 150)  # Fournisseur
        self.tbl_lignes.setColumnWidth(4, 110)  # Voté
        self.tbl_lignes.setColumnWidth(5, 110)  # Engagé
        self.tbl_lignes.setColumnWidth(6, 110)  # Solde
        self.tbl_lignes.setColumnWidth(7, 80)   # Taux %
        self.tbl_lignes.setColumnWidth(8, 90)   # Alerte
        self.tbl_lignes.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_lignes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_lignes.itemSelectionChanged.connect(self._on_ligne_selection)
        self.tbl_lignes.itemDoubleClicked.connect(self._show_historique_bc)

        # Splitter : tableau lignes (haut) + panneau historique BC (bas)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tbl_lignes)
        splitter.addWidget(self._build_historique_panel())
        splitter.setSizes([380, 220])
        layout.addWidget(splitter)

        return w

    def _build_historique_panel(self):
        """Panneau inferieur : historique BC imputes sur la ligne selectionnee."""
        panel = QWidget()
        vbox  = QVBoxLayout(panel)
        vbox.setContentsMargins(0, 4, 0, 0)

        # En-tete
        hdr = QHBoxLayout()
        self.lbl_histo_titre = QLabel("Selectionnez une ligne pour voir l historique des BC")
        self.lbl_histo_titre.setStyleSheet(
            "font-weight:bold; color:#ecf0f1; background:#2c3e50;"
            "padding:6px 10px; border-radius:4px;")
        hdr.addWidget(self.lbl_histo_titre)
        hdr.addStretch()

        self.btn_histo_refresh = QPushButton("🔄")
        self.btn_histo_refresh.setFixedWidth(32)
        self.btn_histo_refresh.setToolTip("Actualiser")
        self.btn_histo_refresh.clicked.connect(self._show_historique_bc)
        self.btn_histo_refresh.setEnabled(False)
        hdr.addWidget(self.btn_histo_refresh)

        self.btn_histo_open_bc = QPushButton("🔍 Ouvrir BC")
        self.btn_histo_open_bc.setStyleSheet(
            "background:#8e44ad;color:white;font-weight:bold;padding:4px 10px;")
        self.btn_histo_open_bc.clicked.connect(self._ouvrir_bc_depuis_histo)
        self.btn_histo_open_bc.setEnabled(False)
        hdr.addWidget(self.btn_histo_open_bc)
        vbox.addLayout(hdr)

        # Tableau historique BC
        self.tbl_histo_bc = QTableWidget()
        self.tbl_histo_bc.setColumnCount(9)
        self.tbl_histo_bc.setHorizontalHeaderLabels([
            "ID", "N° BC", "Objet", "Fournisseur",
            "Montant TTC", "Date imputation", "Date solde", "Statut", "Projet"
        ])
        self.tbl_histo_bc.setColumnHidden(0, True)
        hdr_h = self.tbl_histo_bc.horizontalHeader()
        hdr_h.setSectionResizeMode(QHeaderView.Interactive)
        hdr_h.setStretchLastSection(False)
        hdr_h.setSectionResizeMode(2, QHeaderView.Stretch)  # Objet prend l espace
        self.tbl_histo_bc.setColumnWidth(1, 120)
        self.tbl_histo_bc.setColumnWidth(3, 140)
        self.tbl_histo_bc.setColumnWidth(4, 110)
        self.tbl_histo_bc.setColumnWidth(5, 130)
        self.tbl_histo_bc.setColumnWidth(6, 110)
        self.tbl_histo_bc.setColumnWidth(7, 90)
        self.tbl_histo_bc.setColumnWidth(8, 130)
        self.tbl_histo_bc.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_histo_bc.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_histo_bc.setAlternatingRowColors(True)
        self.tbl_histo_bc.itemSelectionChanged.connect(
            lambda: self.btn_histo_open_bc.setEnabled(
                self.tbl_histo_bc.currentRow() >= 0))
        vbox.addWidget(self.tbl_histo_bc)

        # Barre de totaux
        self.lbl_histo_totaux = QLabel("")
        self.lbl_histo_totaux.setStyleSheet(
            "color:#f39c12; font-weight:bold; padding:4px 8px;"
            "background:#1a252f; border-radius:3px;")
        vbox.addWidget(self.lbl_histo_totaux)

        return panel

    def load_lignes(self):
        if not self.svc:
            return
        # Remplir le combo budgets
        self.combo_budget_lignes.blockSignals(True)
        self.combo_budget_lignes.clear()
        self.combo_budget_lignes.addItem("-- Tous les budgets --", None)
        budgets = self.svc.get_budgets(self.exercice_courant)
        for b in budgets:
            label = f"{b.get('entite_code','')} — {b.get('nature','')} {b.get('exercice','')}"
            self.combo_budget_lignes.addItem(label, b['id'])
        self.combo_budget_lignes.blockSignals(False)
        self._reload_lignes_table()

    def _on_budget_filtre_change(self):
        self._reload_lignes_table()

    def _reload_lignes_table(self):
        if not self.svc:
            return
        budget_id = self.combo_budget_lignes.currentData()
        lignes = self.svc.get_lignes(
            budget_id=budget_id,
            exercice=self.exercice_courant if not budget_id else None
        )
        self.tbl_lignes.setRowCount(len(lignes))
        for r, lb in enumerate(lignes):
            vote    = float(lb.get('montant_vote') or 0)
            engage  = float(lb.get('montant_engage') or 0)
            solde   = float(lb.get('montant_solde') or 0)
            taux    = float(lb.get('taux_engagement_pct') or 0)
            alerte  = bool(lb.get('alerte_seuil'))

            id_item = QTableWidgetItem(str(lb['id']))
            id_item.setData(Qt.UserRole, lb['id'])
            self.tbl_lignes.setItem(r, 0, id_item)
            self.tbl_lignes.setItem(r, 1, QTableWidgetItem(lb.get('libelle', '')))
            self.tbl_lignes.setItem(r, 2, QTableWidgetItem(lb.get('application_nom') or '—'))
            self.tbl_lignes.setItem(r, 3, QTableWidgetItem(lb.get('fournisseur_nom') or '—'))
            self.tbl_lignes.setItem(r, 4, QTableWidgetItem(f"{vote:,.0f} €"))
            self.tbl_lignes.setItem(r, 5, QTableWidgetItem(f"{engage:,.0f} €"))
            self._colored_item(self.tbl_lignes, r, 6, f"{solde:,.0f} €", solde)
            self.tbl_lignes.setItem(r, 7, QTableWidgetItem(f"{taux:.1f} %"))

            al_item = QTableWidgetItem("⚠️ SEUIL" if alerte else "✅ OK")
            al_item.setBackground(QColor('#e74c3c') if alerte else QColor('#27ae60'))
            al_item.setForeground(QColor('#ffffff'))
            self.tbl_lignes.setItem(r, 8, al_item)
            self.tbl_lignes.setItem(r, 9, QTableWidgetItem(lb.get('note') or ''))
            # Budget imputé en dernière colonne
            budget_label = f"{lb.get('entite_code','?')} — {lb.get('budget_nature','?')} {lb.get('exercice','?')}"
            self.tbl_lignes.setItem(r, 10, QTableWidgetItem(budget_label))

    def _on_ligne_selection(self):
        has = self.tbl_lignes.currentRow() >= 0
        self.btn_edit_ligne.setEnabled(has)
        self.btn_del_ligne.setEnabled(has)
        if has:
            self._show_historique_bc()

    def _show_historique_bc(self):
        """Charge et affiche les BC imputes sur la ligne selectionnee."""
        row = self.tbl_lignes.currentRow()
        if row < 0 or not self.svc:
            return
        ligne_id = self.tbl_lignes.item(row, 0).data(Qt.UserRole)
        libelle  = self.tbl_lignes.item(row, 1).text() if self.tbl_lignes.item(row, 1) else ''
        vote     = self.tbl_lignes.item(row, 4).text() if self.tbl_lignes.item(row, 4) else ''
        engage   = self.tbl_lignes.item(row, 5).text() if self.tbl_lignes.item(row, 5) else ''
        solde    = self.tbl_lignes.item(row, 6).text() if self.tbl_lignes.item(row, 6) else ''

        self.btn_histo_refresh.setEnabled(True)

        try:
            from app.services.database_service import db_service
            rows = db_service.fetch_all("""
                SELECT
                    b.id,
                    b.numero_bc,
                    b.objet,
                    COALESCE(f.nom, '--') AS fournisseur_nom,
                    b.montant_ttc,
                    b.date_imputation,
                    b.date_solde,
                    b.statut,
                    COALESCE(p.code || ' -- ' || p.nom, '--') AS projet_nom
                FROM bons_commande b
                LEFT JOIN fournisseurs f ON f.id = b.fournisseur_id
                LEFT JOIN projets p ON p.id = b.projet_id
                WHERE b.ligne_budgetaire_id = ?
                  AND b.statut IN ('IMPUTE', 'SOLDE', 'VALIDE')
                ORDER BY COALESCE(b.date_imputation, b.date_creation) DESC
            """, (ligne_id,)) or []
            # Convertir sqlite3.Row en dict
            bcs = [dict(r) for r in rows]
        except Exception as e:
            logger.error("Historique BC ligne %s : %s", ligne_id, e)
            bcs = []

        # Titre
        self.lbl_histo_titre.setText(
            f"📜 Historique BC — {libelle}   |   "
            f"Vote : {vote}   Engage : {engage}   Solde : {solde}   "
            f"({len(bcs)} BC)")

        COULEURS = {
            'IMPUTE': '#2980b9',
            'SOLDE':  '#27ae60',
            'VALIDE': '#f39c12',
        }

        self.tbl_histo_bc.setRowCount(0)
        total_impute = 0.0
        total_solde  = 0.0

        for bc in bcs:
            r = self.tbl_histo_bc.rowCount()
            self.tbl_histo_bc.insertRow(r)

            montant = float(bc.get('montant_ttc') or 0)
            statut  = bc.get('statut', '')

            id_item = QTableWidgetItem(str(bc.get('id', '')))
            id_item.setData(Qt.UserRole, bc.get('id'))
            self.tbl_histo_bc.setItem(r, 0, id_item)
            self.tbl_histo_bc.setItem(r, 1, QTableWidgetItem(bc.get('numero_bc') or ''))
            self.tbl_histo_bc.setItem(r, 2, QTableWidgetItem(bc.get('objet') or ''))
            self.tbl_histo_bc.setItem(r, 3, QTableWidgetItem(bc.get('fournisseur_nom') or ''))

            m_item = QTableWidgetItem(f"{montant:,.2f} €")
            m_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            m_item.setForeground(QColor('#e67e22'))
            self.tbl_histo_bc.setItem(r, 4, m_item)

            # Date imputation
            d_imp = str(bc.get('date_imputation') or '')[:10]
            self.tbl_histo_bc.setItem(r, 5, QTableWidgetItem(d_imp))

            # Date solde
            d_sol = str(bc.get('date_solde') or '')[:10]
            self.tbl_histo_bc.setItem(r, 6, QTableWidgetItem(d_sol))

            # Statut coloré
            s_item = QTableWidgetItem(statut)
            s_item.setBackground(QColor(COULEURS.get(statut, '#7f8c8d')))
            s_item.setForeground(QColor('#ffffff'))
            s_item.setTextAlignment(Qt.AlignCenter)
            self.tbl_histo_bc.setItem(r, 7, s_item)

            self.tbl_histo_bc.setItem(r, 8, QTableWidgetItem(bc.get('projet_nom') or '—'))

            if statut in ('IMPUTE', 'SOLDE'):
                total_impute += montant
            if statut == 'SOLDE':
                total_solde += montant

        # Barre totaux
        self.lbl_histo_totaux.setText(
            f"  Total impute : {total_impute:,.2f} €   |   "
            f"  Total solde (paye) : {total_solde:,.2f} €   |   "
            f"  En cours (impute non solde) : {total_impute - total_solde:,.2f} €  ")

    def _ouvrir_bc_depuis_histo(self):
        """Ouvre le detail du BC selectionne dans l historique."""
        row = self.tbl_histo_bc.currentRow()
        if row < 0:
            return
        bc_id = self.tbl_histo_bc.item(row, 0).data(Qt.UserRole)
        if not bc_id:
            return
        try:
            from app.services.bon_commande_service import bon_commande_service
            bc = bon_commande_service.get_bon_commande_by_id(bc_id)
            if bc:
                from app.ui.views.fiche_bc_view import FicheBCView
                dlg = FicheBCView(bc, parent=self)
                dlg.exec_()
        except Exception as e:
            logger.error("Ouverture BC %s : %s", bc_id, e)
            num  = self.tbl_histo_bc.item(row, 1).text() if self.tbl_histo_bc.item(row, 1) else ''
            objet = self.tbl_histo_bc.item(row, 2).text() if self.tbl_histo_bc.item(row, 2) else ''
            QMessageBox.information(self, "BC " + str(bc_id),
                "Num BC : " + num + "\nObjet : " + objet)
    def _new_ligne(self):
        if not self.svc:
            return
        budget_id = self.combo_budget_lignes.currentData()
        budgets   = self.svc.get_budgets(self.exercice_courant)
        dlg = LigneDialog(self.svc, budgets, budget_id_defaut=budget_id, parent=self)
        if dlg.exec_():
            self._reload_lignes_table()
            self.load_budgets()  # Mettre à jour le montant prévisionnel

    def _edit_ligne(self):
        row = self.tbl_lignes.currentRow()
        if row < 0:
            return
        ligne_id = self.tbl_lignes.item(row, 0).data(Qt.UserRole)
        ligne    = self.svc.get_ligne_by_id(ligne_id)
        budgets  = self.svc.get_budgets(self.exercice_courant)
        dlg = LigneDialog(self.svc, budgets, ligne=ligne, parent=self)
        if dlg.exec_():
            self._reload_lignes_table()
            self.load_budgets()  # Mettre à jour le montant prévisionnel

    def _delete_ligne(self):
        row = self.tbl_lignes.currentRow()
        if row < 0:
            return
        ligne_id = self.tbl_lignes.item(row, 0).data(Qt.UserRole)
        libelle  = self.tbl_lignes.item(row, 1).text()
        reply = QMessageBox.question(self, "Supprimer",
            f"Supprimer la ligne « {libelle} » ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ok, msg = self.svc.delete_ligne(ligne_id)
        if ok:
            self._reload_lignes_table()
        else:
            QMessageBox.warning(self, "Impossible", msg)

    # =========================================================================
    # ONGLET 4 — APPLICATIONS
    # =========================================================================

    def _build_tab_applications(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        toolbar = QHBoxLayout()
        btn_new = QPushButton("➕ Nouvelle application")
        btn_new.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 7px 14px;")
        btn_new.clicked.connect(self._new_application)
        toolbar.addWidget(btn_new)

        self.btn_edit_app = QPushButton("✏️ Modifier")
        self.btn_edit_app.setStyleSheet(
            "background-color: #3498db; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_edit_app.clicked.connect(self._edit_application)
        self.btn_edit_app.setEnabled(False)
        toolbar.addWidget(self.btn_edit_app)

        self.btn_del_app = QPushButton("🗑️ Supprimer")
        self.btn_del_app.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_del_app.clicked.connect(self._delete_application)
        self.btn_del_app.setEnabled(False)
        toolbar.addWidget(self.btn_del_app)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.tbl_apps = QTableWidget()
        self.tbl_apps.setColumnCount(7)
        self.tbl_apps.setHorizontalHeaderLabels([
            "ID", "Code", "Nom", "Type", "Entité", "Fournisseur", "Statut"
        ])
        self.tbl_apps.setColumnHidden(0, True)
        hdr_a = self.tbl_apps.horizontalHeader()
        hdr_a.setSectionResizeMode(QHeaderView.Interactive)
        hdr_a.setStretchLastSection(True)
        hdr_a.setDefaultSectionSize(120)
        self.tbl_apps.setColumnWidth(1, 80)   # Code
        self.tbl_apps.setColumnWidth(2, 200)  # Nom
        self.tbl_apps.setColumnWidth(3, 130)  # Type
        self.tbl_apps.setColumnWidth(4, 160)  # Entité
        self.tbl_apps.setColumnWidth(5, 160)  # Fournisseur
        self.tbl_apps.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_apps.setEditTriggers(QTableWidget.NoEditTriggers)
        def _on_app_select():
            sel = self.tbl_apps.currentRow() >= 0
            self.btn_edit_app.setEnabled(sel)
            self.btn_del_app.setEnabled(sel)
        self.tbl_apps.itemSelectionChanged.connect(_on_app_select)
        layout.addWidget(self.tbl_apps)

        return w

    def load_applications(self):
        if not self.svc:
            return
        apps = self.svc.get_all_applications()
        self.tbl_apps.setRowCount(len(apps))
        statut_colors = {
            'ACTIF': '#27ae60', 'EN_MIGRATION': '#f39c12',
            'OBSOLETE': '#e74c3c', 'ABANDONNE': '#7f8c8d'
        }
        for r, a in enumerate(apps):
            id_item = QTableWidgetItem(str(a['id']))
            id_item.setData(Qt.UserRole, a['id'])
            self.tbl_apps.setItem(r, 0, id_item)
            self.tbl_apps.setItem(r, 1, QTableWidgetItem(a.get('code', '')))
            self.tbl_apps.setItem(r, 2, QTableWidgetItem(a.get('nom', '')))
            self.tbl_apps.setItem(r, 3, QTableWidgetItem(a.get('type_app', '')))
            self.tbl_apps.setItem(r, 4, QTableWidgetItem(a.get('entite_code') or 'Partagée'))
            self.tbl_apps.setItem(r, 5, QTableWidgetItem(a.get('fournisseur_nom') or '—'))
            statut = a.get('statut', 'ACTIF')
            st = QTableWidgetItem(statut)
            st.setBackground(QColor(statut_colors.get(statut, '#95a5a6')))
            st.setForeground(QColor('#ffffff'))
            self.tbl_apps.setItem(r, 6, st)

    def _delete_application(self):
        row = self.tbl_apps.currentRow()
        if row < 0:
            return
        app_id   = int(self.tbl_apps.item(row, 0).text())
        app_nom  = self.tbl_apps.item(row, 2).text()
        rep = QMessageBox.question(
            self, "Confirmer la suppression",
            f"Supprimer l'application '{app_nom}' ?\n\n"
            "Cette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if rep != QMessageBox.Yes:
            return
        ok, msg = self.svc.delete_application(app_id)
        if ok:
            QMessageBox.information(self, "Succès", msg)
            self.load_applications()
        else:
            QMessageBox.warning(self, "Impossible", msg)

    def _new_application(self):
        entites = self.svc.get_entites() if self.svc else []
        try:
            from app.services.fournisseur_service import fournisseur_service
            fournisseurs = fournisseur_service.get_all()
        except Exception:
            fournisseurs = []
        dlg = ApplicationDialog(entites, fournisseurs, parent=self)
        if dlg.exec_() and self.svc:
            try:
                self.svc.create_application(dlg.get_data())
                self.load_applications()
            except ValueError as e:
                QMessageBox.warning(self, "Code déjà utilisé", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _edit_application(self):
        row = self.tbl_apps.currentRow()
        if row < 0 or not self.svc:
            return
        app_id = self.tbl_apps.item(row, 0).data(Qt.UserRole)
        apps   = self.svc.get_all_applications()
        app    = next((a for a in apps if a['id'] == app_id), None)
        if not app:
            return
        entites = self.svc.get_entites()
        try:
            from app.services.fournisseur_service import fournisseur_service
            fournisseurs = fournisseur_service.get_all()
        except Exception:
            fournisseurs = []
        dlg = ApplicationDialog(entites, fournisseurs, app=app, parent=self)
        if dlg.exec_():
            self.svc.update_application(app_id, dlg.get_data())
            self.load_applications()

    # =========================================================================
    # ONGLET 5 — PRÉPARATION N+1
    # =========================================================================

    def _build_tab_n1(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # ── Paramètres ───────────────────────────────────────────────────────
        grp = QGroupBox("Parametres de generation N+1")
        grp.setStyleSheet("QGroupBox { font-weight: bold; padding: 10px; }")
        form = QFormLayout(grp)

        self.combo_entite_n1 = QComboBox()
        self.combo_entite_n1.addItem("Toutes les entites", None)
        form.addRow("Entite :", self.combo_entite_n1)

        row_ex = QHBoxLayout()
        self.spin_source = QSpinBox()
        self.spin_source.setRange(2020, 2035)
        self.spin_source.setValue(datetime.now().year)
        row_ex.addWidget(QLabel("Source (N) :"))
        row_ex.addWidget(self.spin_source)
        row_ex.addWidget(QLabel("   Cible (N+1) :"))
        self.spin_cible = QSpinBox()
        self.spin_cible.setRange(2021, 2036)
        self.spin_cible.setValue(datetime.now().year + 1)
        row_ex.addWidget(self.spin_cible)
        row_ex.addStretch()
        form.addRow(row_ex)

        btn_apercu = QPushButton("🔍 Calculer apercu N+1")
        btn_apercu.setStyleSheet(
            "background:#2980b9;color:white;font-weight:bold;padding:8px 20px;")
        btn_apercu.clicked.connect(self._charger_apercu_n1)
        form.addRow(btn_apercu)

        layout.addWidget(grp)

        # ── Tableau aperçu ────────────────────────────────────────────────────
        lbl_apercu = QLabel("Apercu des lignes qui seront generees (modifiez le montant N+1 avant de valider) :")
        lbl_apercu.setStyleSheet("font-weight:bold; padding:6px 0;")
        layout.addWidget(lbl_apercu)

        self.tbl_n1 = QTableWidget(0, 9)
        self.tbl_n1.setHorizontalHeaderLabels([
            "Nature", "Libelle", "Application / Projet",
            "Vote N", "Consomme N", "Taux %", "Solde N",
            "Suggestion N+1", "Note"
        ])
        hdr = self.tbl_n1.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(8, QHeaderView.Stretch)
        self.tbl_n1.setColumnWidth(0, 130)
        self.tbl_n1.setColumnWidth(2, 150)
        self.tbl_n1.setColumnWidth(3, 100)
        self.tbl_n1.setColumnWidth(4, 110)
        self.tbl_n1.setColumnWidth(5, 70)
        self.tbl_n1.setColumnWidth(6, 100)
        self.tbl_n1.setColumnWidth(7, 110)
        self.tbl_n1.setAlternatingRowColors(True)
        self.tbl_n1.setSelectionBehavior(QTableWidget.SelectRows)
        # Colonne 7 (Suggestion N+1) est editable, les autres non
        layout.addWidget(self.tbl_n1)

        # Legende
        leg = QHBoxLayout()
        for couleur, texte in [('#c0392b','Depassement (solde negatif)'),
                                ('#e67e22','Taux > 90%'),
                                ('#27ae60','Taux < 30% (sous-consomme)')]:
            lbl = QLabel(f"■ {texte}")
            lbl.setStyleSheet(f"color:{couleur}; font-size:11px;")
            leg.addWidget(lbl)
        leg.addStretch()
        layout.addLayout(leg)

        # Barre totaux + bouton generer
        bottom = QHBoxLayout()
        self.lbl_n1_totaux = QLabel("")
        self.lbl_n1_totaux.setStyleSheet(
            "font-weight:bold; color:#f39c12; padding:4px 8px;"
            "background:#1a252f; border-radius:3px;")
        bottom.addWidget(self.lbl_n1_totaux)
        bottom.addStretch()

        btn_gen = QPushButton("🚀 Generer budget N+1")
        btn_gen.setStyleSheet(
            "background:#8e44ad;color:white;font-weight:bold;"
            "padding:10px 28px;font-size:14px;")
        btn_gen.clicked.connect(self._generer_n1)
        bottom.addWidget(btn_gen)
        layout.addLayout(bottom)

        # Stocker les données aperçu
        self._apercu_n1_data = []
        return w

    def _charger_apercu_n1(self):
        """Charge et affiche l apercu des lignes N+1."""
        if not self.svc:
            return
        entite_id = self.combo_entite_n1.currentData()
        src   = self.spin_source.value()
        cible = self.spin_cible.value()

        self.tbl_n1.setRowCount(0)
        self._apercu_n1_data = []

        COULEURS_ALERTE = {
            'depasse':   '#c0392b',
            'critique':  '#e67e22',
            'sous':      '#27ae60',
            'normal':    None,
        }

        try:
            entites = self.svc.get_entites()
            total_suggestion = 0.0
            total_vote_n = 0.0

            for ent in entites:
                if entite_id and ent['id'] != entite_id:
                    continue
                lignes = self.svc.get_apercu_n1(ent['id'], src, cible)
                for lg in lignes:
                    r = self.tbl_n1.rowCount()
                    self.tbl_n1.insertRow(r)

                    vote    = float(lg.get('vote_n') or 0)
                    engage  = float(lg.get('engage_n') or 0)
                    solde   = float(lg.get('solde_n') or 0)
                    taux    = float(lg.get('taux_n') or 0)
                    sugg    = float(lg.get('suggestion') or 0)
                    total_vote_n     += vote
                    total_suggestion += sugg

                    # Couleur de la ligne
                    if solde < 0:
                        bg = QColor('#5c1010')
                        cat = 'depasse'
                    elif taux > 90:
                        bg = QColor('#5c3a10')
                        cat = 'critique'
                    elif taux < 30 and vote > 0:
                        bg = QColor('#0f3d1e')
                        cat = 'sous'
                    else:
                        bg = None
                        cat = 'normal'

                    def cell(txt, editable=False, align=None):
                        it = QTableWidgetItem(str(txt))
                        if not editable:
                            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                        if align:
                            it.setTextAlignment(align)
                        if bg:
                            it.setBackground(bg)
                        return it

                    nat_item = cell(lg.get('nature', ''))
                    if lg.get('source') == 'PROJET':
                        nat_item.setForeground(QColor('#9b59b6'))
                    self.tbl_n1.setItem(r, 0, nat_item)
                    self.tbl_n1.setItem(r, 1, cell(lg.get('libelle', '')))
                    appli = lg.get('application_nom') or lg.get('projet_nom') or ''
                    self.tbl_n1.setItem(r, 2, cell(appli))
                    self.tbl_n1.setItem(r, 3, cell(f"{vote:,.0f} EUR",
                        align=Qt.AlignRight|Qt.AlignVCenter))
                    eng_item = cell(f"{engage:,.0f} EUR",
                        align=Qt.AlignRight|Qt.AlignVCenter)
                    if taux > 90:
                        eng_item.setForeground(QColor('#e74c3c'))
                    self.tbl_n1.setItem(r, 4, eng_item)

                    taux_item = cell(f"{taux:.0f} %",
                        align=Qt.AlignCenter)
                    if taux > 90:
                        taux_item.setForeground(QColor('#e74c3c'))
                    elif taux < 30 and vote > 0:
                        taux_item.setForeground(QColor('#2ecc71'))
                    self.tbl_n1.setItem(r, 5, taux_item)

                    solde_item = cell(f"{solde:,.0f} EUR",
                        align=Qt.AlignRight|Qt.AlignVCenter)
                    if solde < 0:
                        solde_item.setForeground(QColor('#ff6b6b'))
                    self.tbl_n1.setItem(r, 6, solde_item)

                    # Suggestion N+1 : editable
                    sugg_item = QTableWidgetItem(f"{sugg:,.2f}")
                    sugg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    sugg_item.setBackground(QColor('#1a3a52'))
                    sugg_item.setForeground(QColor('#f39c12'))
                    self.tbl_n1.setItem(r, 7, sugg_item)

                    self.tbl_n1.setItem(r, 8, cell(lg.get('raison', '')))

                    # Tooltip sur la note complete
                    for c in range(9):
                        it = self.tbl_n1.item(r, c)
                        if it:
                            it.setToolTip(lg.get('note_generee', ''))

                    self._apercu_n1_data.append(lg)

            self.lbl_n1_totaux.setText(
                f"  {self.tbl_n1.rowCount()} lignes   |   "
                f"  Total vote N : {total_vote_n:,.0f} EUR   |   "
                f"  Total suggere N+1 : {total_suggestion:,.0f} EUR  "
            )

        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Erreur apercu", str(e))

    def _generer_n1(self):
        if not self.svc:
            return
        entite_id = self.combo_entite_n1.currentData()
        src   = self.spin_source.value()
        cible = self.spin_cible.value()

        # Verifier qu un apercu a ete calcule
        if not self._apercu_n1_data:
            rep = QMessageBox.question(self, "Apercu manquant",
                "Aucun apercu n a ete calcule.\n"
                "Voulez-vous generer directement avec les montants suggeres ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep != QMessageBox.Yes:
                return
            self._charger_apercu_n1()
            if not self._apercu_n1_data:
                QMessageBox.warning(self, "Aucune donnee",
                    "Aucune ligne trouvee pour l exercice source " + str(src))
                return

        # Recuperer les montants modifies depuis le tableau
        lignes_validees = []
        for r in range(self.tbl_n1.rowCount()):
            if r >= len(self._apercu_n1_data):
                break
            lg = dict(self._apercu_n1_data[r])
            sugg_item = self.tbl_n1.item(r, 7)
            try:
                lg['montant_prevu_n1'] = float(
                    (sugg_item.text() if sugg_item else '0').replace(',', '').replace(' EUR', ''))
            except Exception:
                lg['montant_prevu_n1'] = lg.get('suggestion', 0)
            lg['note'] = lg.get('note_generee', '')
            lignes_validees.append(lg)

        nb_total = 0
        total_budget = sum(l['montant_prevu_n1'] for l in lignes_validees)

        reply = QMessageBox.question(self, "Confirmer la generation",
            f"Generation budget {cible} a partir de {src}\n\n"
            f"{len(lignes_validees)} ligne(s) | Total : {total_budget:,.0f} EUR\n\n"
            "Les lignes existantes ne seront pas ecrasees.\n"
            "Confirmer ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            entites = self.svc.get_entites()
            for ent in entites:
                if entite_id and ent['id'] != entite_id:
                    continue
                lignes_ent = [l for l in lignes_validees
                              if not entite_id or True]
                nb = self.svc.preparer_budget_n1(
                    ent['id'], src, cible, lignes_validees=lignes_ent)
                nb_total += nb

            QMessageBox.information(self, "Generation terminee",
                f"{nb_total} ligne(s) creee(s) pour le budget {cible}.\n\n"
                f"Allez dans l onglet Lignes budgetaires pour les consulter.")
            self._apercu_n1_data = []
            self.tbl_n1.setRowCount(0)
            self.load_all()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # =========================================================================
    # CHARGEMENT GLOBAL
    # =========================================================================


    # =========================================================================
    # ONGLET ENTITÉS
    # =========================================================================

    def _build_tab_entites(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        toolbar = QHBoxLayout()
        btn_new = QPushButton("➕ Nouvelle entité")
        btn_new.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 7px 14px;")
        btn_new.clicked.connect(self._new_entite)
        toolbar.addWidget(btn_new)

        self.btn_edit_entite = QPushButton("✏️ Modifier")
        self.btn_edit_entite.setStyleSheet(
            "background-color: #3498db; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_edit_entite.clicked.connect(self._edit_entite)
        self.btn_edit_entite.setEnabled(False)
        toolbar.addWidget(self.btn_edit_entite)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        info = QLabel(
            "ℹ️  Les entités sont les structures juridiques dont vous gérez le budget "
            "(Ville de La Rochelle, CDA...)")
        info.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tbl_entites = QTableWidget()
        self.tbl_entites.setColumnCount(4)
        self.tbl_entites.setHorizontalHeaderLabels(["ID", "Code", "Nom", "SIRET"])
        self.tbl_entites.setColumnHidden(0, True)
        hdr = self.tbl_entites.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        self.tbl_entites.setColumnWidth(1, 100)
        self.tbl_entites.setColumnWidth(2, 300)
        self.tbl_entites.setColumnWidth(3, 160)
        self.tbl_entites.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_entites.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_entites.itemSelectionChanged.connect(
            lambda: self.btn_edit_entite.setEnabled(
                self.tbl_entites.currentRow() >= 0))
        self.tbl_entites.doubleClicked.connect(self._edit_entite)
        layout.addWidget(self.tbl_entites)
        return w

    def load_entites(self):
        if not self.svc:
            return
        entites = self.svc.get_entites()
        self.tbl_entites.setRowCount(len(entites))
        for r, e in enumerate(entites):
            id_item = QTableWidgetItem(str(e["id"]))
            id_item.setData(Qt.UserRole, e["id"])
            self.tbl_entites.setItem(r, 0, id_item)
            self.tbl_entites.setItem(r, 1, QTableWidgetItem(e.get("code", "")))
            self.tbl_entites.setItem(r, 2, QTableWidgetItem(e.get("nom", "")))
            self.tbl_entites.setItem(r, 3, QTableWidgetItem(e.get("siret") or ""))

    def _new_entite(self):
        if not self.svc:
            return
        dlg = EntiteDialog(parent=self)
        if not dlg.exec_():
            return
        data = dlg.get_data()
        try:
            conn = self.svc.db.get_connection()
            conn.execute(
                "INSERT INTO entites (code, nom, siret, actif) VALUES (?,?,?,1)",
                (data["code"], data["nom"], data["siret"]))
            conn.commit()
            # Créer budgets de l'exercice courant pour cette entité
            row = self.svc.db.fetch_one(
                "SELECT id FROM entites WHERE code=?", (data["code"],))
            if row:
                eid = dict(row)["id"]
                for nature in ("FONCTIONNEMENT", "INVESTISSEMENT"):
                    conn.execute(
                        "INSERT OR IGNORE INTO budgets_annuels"
                        " (entite_id, exercice, nature, statut, date_creation, date_maj)"
                        " VALUES (?,?,?,'EN_PREPARATION',datetime('now'),datetime('now'))",
                        (eid, self.exercice_courant, nature))
                conn.commit()
            self.load_entites()
            self._load_entites_combos()
            self.load_budgets()
            QMessageBox.information(self, "Entité créée",
                f"Entité '{data['nom']}' créée avec ses budgets {self.exercice_courant}.")
        except Exception as e:
            if "UNIQUE" in str(e):
                QMessageBox.warning(self, "Code déjà utilisé",
                    f"Une entité avec le code '{data['code']}' existe déjà.")
            else:
                QMessageBox.critical(self, "Erreur", str(e))

    def _edit_entite(self):
        row = self.tbl_entites.currentRow()
        if row < 0 or not self.svc:
            return
        entite_id = self.tbl_entites.item(row, 0).data(Qt.UserRole)
        entites   = self.svc.get_entites()
        entite    = next((e for e in entites if e["id"] == entite_id), None)
        if not entite:
            return
        dlg = EntiteDialog(entite=entite, parent=self)
        if not dlg.exec_():
            return
        data = dlg.get_data()
        try:
            conn = self.svc.db.get_connection()
            conn.execute(
                "UPDATE entites SET code=?, nom=?, siret=? WHERE id=?",
                (data["code"], data["nom"], data["siret"], entite_id))
            conn.commit()
            self.load_entites()
            self._load_entites_combos()
            self.load_budgets()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


    def _export_excel(self):
        """Export Excel du budget — amélioration #8."""
        try:
            from app.services.export_service import export_service
        except ImportError:
            QMessageBox.warning(self, "Export",
                "Service d'export non disponible.")
            return

        exercice = self.exercice_courant
        ok, result = export_service.export_budget_excel(exercice)
        if ok:
            QMessageBox.information(self, "Export réussi",
                f"Fichier Excel créé :\n{result}\n\n"
                "5 onglets : Synthèse, Lignes budgétaires, Contrats, BC, Prévisionnel N+1")
        else:
            QMessageBox.critical(self, "Erreur export", result)

    def load_all(self):
        self._load_entites_combos()
        self.load_dashboard()
        self.load_budgets()
        self.load_lignes()
        self.load_applications()
        self.load_entites()

    def _load_entites_combos(self):
        if not self.svc:
            return
        entites = self.svc.get_entites()
        for combo in (self.combo_entite, self.combo_entite_n1):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Toutes", None)
            for e in entites:
                combo.addItem(e['nom'], e['id'])
            combo.blockSignals(False)

    def _on_exercice_change(self, text):
        try:
            self.exercice_courant = int(text)
            self.load_all()
        except ValueError:
            pass

    def _on_entite_change(self):
        self.entite_filtre = self.combo_entite.currentData()
        self.load_all()


# =============================================================================
# DIALOGS
# =============================================================================

class BudgetDialog(QDialog):
    def __init__(self, svc, budget=None, parent=None):
        super().__init__(parent)
        self.svc    = svc
        self.budget = budget
        self.setWindowTitle("✏️ Modifier budget" if budget else "➕ Nouveau budget")
        self.setMinimumWidth(420)
        self._build()
        if budget:
            self._fill()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.combo_entite = QComboBox()
        entites = self.svc.get_entites()
        for e in entites:
            self.combo_entite.addItem(e['nom'], e['id'])
        form.addRow("Entité *:", self.combo_entite)

        self.spin_exercice = QSpinBox()
        self.spin_exercice.setRange(2020, 2040)
        self.spin_exercice.setValue(datetime.now().year)
        form.addRow("Exercice *:", self.spin_exercice)

        self.combo_nature = QComboBox()
        self.combo_nature.addItems(['FONCTIONNEMENT', 'INVESTISSEMENT'])
        form.addRow("Nature *:", self.combo_nature)

        self.spin_previsionnel = QDoubleSpinBox()
        self.spin_previsionnel.setMaximum(99999999)
        self.spin_previsionnel.setDecimals(2)
        self.spin_previsionnel.setSuffix(" €")
        form.addRow("Montant prévisionnel:", self.spin_previsionnel)

        self.note = QTextEdit()
        self.note.setMaximumHeight(80)
        self.note.setPlaceholderText("Justifications, argumentaire pour les élus...")
        form.addRow("Note de présentation:", self.note)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Enregistrer")
        btn_ok.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        btn_ok.clicked.connect(self._save)
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _fill(self):
        b = self.budget
        idx = self.combo_entite.findData(b.get('entite_id'))
        if idx >= 0: self.combo_entite.setCurrentIndex(idx)
        self.spin_exercice.setValue(b.get('exercice', datetime.now().year))
        idx2 = self.combo_nature.findText(b.get('nature', ''))
        if idx2 >= 0: self.combo_nature.setCurrentIndex(idx2)
        self.spin_previsionnel.setValue(float(b.get('montant_previsionnel') or 0))
        self.note.setPlainText(b.get('note_presentation') or '')

    def _save(self):
        data = {
            'entite_id':           self.combo_entite.currentData(),
            'exercice':            self.spin_exercice.value(),
            'nature':              self.combo_nature.currentText(),
            'montant_previsionnel':self.spin_previsionnel.value(),
            'note_presentation':   self.note.toPlainText().strip(),
        }
        try:
            if self.budget:
                self.svc.update_budget(self.budget['id'], data)
            else:
                self.svc.create_budget(data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


class LigneDialog(QDialog):
    def __init__(self, svc, budgets, ligne=None, budget_id_defaut=None, parent=None):
        super().__init__(parent)
        self.svc     = svc
        self.ligne   = ligne
        self.budgets = budgets
        self.setWindowTitle("✏️ Modifier ligne" if ligne else "➕ Nouvelle ligne")
        self.setMinimumWidth(480)
        self._build(budget_id_defaut)
        if ligne:
            self._fill()

    def _build(self, budget_id_defaut):
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.combo_budget = QComboBox()
        for b in self.budgets:
            label = f"{b.get('entite_code','')} — {b.get('nature','')} {b.get('exercice','')}"
            self.combo_budget.addItem(label, b['id'])
        if budget_id_defaut:
            idx = self.combo_budget.findData(budget_id_defaut)
            if idx >= 0: self.combo_budget.setCurrentIndex(idx)
        form.addRow("Budget *:", self.combo_budget)

        self.libelle = QLineEdit()
        self.libelle.setPlaceholderText("ex: Maintenance SIRH, Migration GED...")
        form.addRow("Libellé *:", self.libelle)

        self.combo_nature = QComboBox()
        self.combo_nature.addItems(['FONCTIONNEMENT', 'INVESTISSEMENT'])
        form.addRow("Nature *:", self.combo_nature)

        # Application
        self.combo_app = QComboBox()
        self.combo_app.addItem("— Aucune —", None)
        for a in self.svc.get_all_applications():
            self.combo_app.addItem(f"{a.get('code','')} — {a.get('nom','')}", a['id'])
        form.addRow("Application:", self.combo_app)

        # Fournisseur principal de cette ligne
        self.combo_fournisseur = QComboBox()
        self.combo_fournisseur.addItem("— Aucun —", None)
        try:
            from app.services.fournisseur_service import fournisseur_service
            for f in fournisseur_service.get_all():
                self.combo_fournisseur.addItem(f.get('nom', ''), f.get('id'))
        except Exception:
            pass
        form.addRow("Fournisseur:", self.combo_fournisseur)

        self.spin_prevu = QDoubleSpinBox()
        self.spin_prevu.setMaximum(9999999)
        self.spin_prevu.setDecimals(2)
        self.spin_prevu.setSuffix(" €")
        form.addRow("Montant prévu:", self.spin_prevu)

        self.spin_vote = QDoubleSpinBox()
        self.spin_vote.setMaximum(9999999)
        self.spin_vote.setDecimals(2)
        self.spin_vote.setSuffix(" €")
        form.addRow("Montant voté:", self.spin_vote)

        self.spin_seuil = QSpinBox()
        self.spin_seuil.setRange(50, 100)
        self.spin_seuil.setValue(80)
        self.spin_seuil.setSuffix(" %")
        form.addRow("Seuil alerte:", self.spin_seuil)

        self.note = QLineEdit()
        self.note.setPlaceholderText("Référence D.S.I / justification")
        form.addRow("Référence D.S.I:", self.note)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Enregistrer")
        btn_ok.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        btn_ok.clicked.connect(self._save)
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _fill(self):
        lb = self.ligne
        idx = self.combo_budget.findData(lb.get('budget_id'))
        if idx >= 0: self.combo_budget.setCurrentIndex(idx)
        self.libelle.setText(lb.get('libelle', ''))
        idx2 = self.combo_nature.findText(lb.get('nature', ''))
        if idx2 >= 0: self.combo_nature.setCurrentIndex(idx2)
        idx3 = self.combo_app.findData(lb.get('application_id'))
        if idx3 >= 0: self.combo_app.setCurrentIndex(idx3)
        idx_f = self.combo_fournisseur.findData(lb.get('fournisseur_id'))
        if idx_f >= 0: self.combo_fournisseur.setCurrentIndex(idx_f)
        self.spin_prevu.setValue(float(lb.get('montant_prevu') or 0))
        self.spin_vote.setValue(float(lb.get('montant_vote') or 0))
        self.spin_seuil.setValue(int(lb.get('seuil_alerte_pct') or 80))
        self.note.setText(lb.get('note') or '')

    def _save(self):
        if not self.libelle.text().strip():
            QMessageBox.warning(self, "Champ requis", "Le libellé est obligatoire")
            return
        montant_vote = self.spin_vote.value()
        data = {
            'budget_id':        self.combo_budget.currentData(),
            'libelle':          self.libelle.text().strip(),
            'nature':           self.combo_nature.currentText(),
            'application_id':   self.combo_app.currentData(),
            'fournisseur_id':   self.combo_fournisseur.currentData(),
            'montant_prevu':    self.spin_prevu.value(),
            'montant_vote':     montant_vote,
            'montant_solde':    montant_vote,
            'seuil_alerte_pct': self.spin_seuil.value(),
            'note':             self.note.text().strip(),
        }
        try:
            if self.ligne:
                self.svc.update_ligne(self.ligne['id'], data)
            else:
                self.svc.create_ligne(data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


class ApplicationDialog(QDialog):
    def __init__(self, entites, fournisseurs, app=None, parent=None):
        super().__init__(parent)
        self.entites     = entites
        self.fournisseurs = fournisseurs
        self.app         = app
        self.setWindowTitle("✏️ Modifier application" if app else "➕ Nouvelle application")
        self.setMinimumWidth(440)
        self._build()
        if app:
            self._fill()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.code = QLineEdit()
        self.code.setPlaceholderText("ex: SIRH, GED, GMAO...")
        form.addRow("Code *:", self.code)

        self.nom = QLineEdit()
        form.addRow("Nom *:", self.nom)

        self.combo_type = QComboBox()
        self.combo_type.addItems(['METIER', 'INFRASTRUCTURE', 'TRANSVERSE', 'SECURITE'])
        form.addRow("Type:", self.combo_type)

        self.combo_entite = QComboBox()
        self.combo_entite.addItem("Partagée (Ville + CDA)", None)
        for e in self.entites:
            self.combo_entite.addItem(e['nom'], e['id'])
        form.addRow("Entité:", self.combo_entite)

        self.combo_fournisseur = QComboBox()
        self.combo_fournisseur.addItem("— Aucun —", None)
        for f in self.fournisseurs:
            self.combo_fournisseur.addItem(f.get('nom', ''), f.get('id'))
        form.addRow("Éditeur/Fournisseur:", self.combo_fournisseur)

        self.version = QLineEdit()
        form.addRow("Version actuelle:", self.version)

        self.combo_statut = QComboBox()
        self.combo_statut.addItems(['ACTIF', 'EN_MIGRATION', 'OBSOLETE', 'ABANDONNE'])
        form.addRow("Statut:", self.combo_statut)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        form.addRow("Notes:", self.notes)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Enregistrer")
        btn_ok.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _fill(self):
        a = self.app
        self.code.setText(a.get('code', ''))
        self.nom.setText(a.get('nom', ''))
        idx = self.combo_type.findText(a.get('type_app', ''))
        if idx >= 0: self.combo_type.setCurrentIndex(idx)
        idx2 = self.combo_entite.findData(a.get('entite_id'))
        if idx2 >= 0: self.combo_entite.setCurrentIndex(idx2)
        idx3 = self.combo_fournisseur.findData(a.get('fournisseur_id'))
        if idx3 >= 0: self.combo_fournisseur.setCurrentIndex(idx3)
        self.version.setText(a.get('version_actuelle') or '')
        idx4 = self.combo_statut.findText(a.get('statut', ''))
        if idx4 >= 0: self.combo_statut.setCurrentIndex(idx4)
        self.notes.setPlainText(a.get('notes') or '')

    def get_data(self):
        return {
            'code':             self.code.text().strip().upper(),
            'nom':              self.nom.text().strip(),
            'type_app':         self.combo_type.currentText(),
            'entite_id':        self.combo_entite.currentData(),
            'fournisseur_id':   self.combo_fournisseur.currentData(),
            'version_actuelle': self.version.text().strip(),
            'statut':           self.combo_statut.currentText(),
            'notes':            self.notes.toPlainText().strip(),
        }


class EntiteDialog(QDialog):
    """Dialog création/modification d'entité."""
    def __init__(self, entite=None, parent=None):
        super().__init__(parent)
        self.entite = entite
        self.setWindowTitle("✏️ Modifier entité" if entite else "➕ Nouvelle entité")
        self.setMinimumWidth(400)
        self._build()
        if entite:
            self._fill()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.code = QLineEdit()
        self.code.setPlaceholderText("ex: VILLE, CDA, SDIS...")
        self.code.setMaxLength(20)
        form.addRow("Code *:", self.code)

        self.nom = QLineEdit()
        self.nom.setPlaceholderText("ex: Ville de La Rochelle")
        form.addRow("Nom complet *:", self.nom)

        self.siret = QLineEdit()
        self.siret.setPlaceholderText("14 chiffres")
        self.siret.setMaxLength(14)
        form.addRow("SIRET:", self.siret)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Enregistrer")
        btn_ok.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        btn_ok.clicked.connect(self._validate)
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _fill(self):
        self.code.setText(self.entite.get("code", ""))
        self.nom.setText(self.entite.get("nom", ""))
        self.siret.setText(self.entite.get("siret") or "")

    def _validate(self):
        if not self.code.text().strip():
            QMessageBox.warning(self, "Champ requis", "Le code est obligatoire.")
            return
        if not self.nom.text().strip():
            QMessageBox.warning(self, "Champ requis", "Le nom est obligatoire.")
            return
        self.accept()

    def get_data(self):
        return {
            "code":  self.code.text().strip().upper(),
            "nom":   self.nom.text().strip(),
            "siret": self.siret.text().strip() or None,
        }
