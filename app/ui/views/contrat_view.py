"""
contrat_view.py — Vue gestion des contrats V5
Onglet dédié : liste + alertes + formulaire complet
"""
import logging
from datetime import datetime, date
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QTextEdit, QGroupBox, QDateEdit, QCheckBox,
    QTabWidget, QFrame, QSplitter, QScrollArea
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

TYPES_CONTRAT = [
    ('MARCHE_PUBLIC',  '📋 Marché public'),
    ('MAPA',           '🤝 MAPA (Marché à procédure adaptée)'),
    ('APPEL_OFFRES',   '📢 Appel d\'offres'),
    ('ACCORD_CADRE',   '📁 Accord-cadre'),
    ('CONVENTION',     '📄 Convention'),
    ('DSP',            '🏛️ DSP (Délégation de service public)'),
]

STATUTS = ['BROUILLON', 'ACTIF', 'RECONDUIT', 'RESILIE', 'TERMINE', 'EXPIRE']

ALERTE_COLORS = {
    'EXPIRE':    '#e74c3c',
    'CRITIQUE':  '#e67e22',
    'ATTENTION': '#f39c12',
    'INFO':      '#3498db',
    'OK':        '#27ae60',
}


class ContratView(QWidget):
    """Vue principale des contrats."""

    def __init__(self):
        super().__init__()
        self._init_services()
        self.init_ui()
        self.load_data()

    def _init_services(self):
        try:
            from app.services.contrat_service import contrat_service
            self.svc = contrat_service
        except Exception as e:
            logger.error(f"contrat_service indisponible : {e}")
            self.svc = None
        try:
            from app.services.budget_v5_service import budget_v5_service
            self.budget_svc = budget_v5_service
        except Exception:
            self.budget_svc = None
        try:
            from app.services.fournisseur_service import fournisseur_service
            self.fourn_svc = fournisseur_service
        except Exception:
            self.fourn_svc = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── En-tête ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background-color: #1a252f; padding: 8px;")
        h_lay = QHBoxLayout(header)

        title = QLabel("📄 Contrats & Marchés")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        h_lay.addWidget(title)
        h_lay.addStretch()

        # KPI alertes
        self.lbl_actifs   = self._kpi_badge("0 actifs",   "#2980b9")
        self.lbl_alertes  = self._kpi_badge("0 alertes",  "#e67e22")
        self.lbl_expires  = self._kpi_badge("0 expirés",  "#e74c3c")
        for w in (self.lbl_actifs, self.lbl_alertes, self.lbl_expires):
            h_lay.addWidget(w)

        layout.addWidget(header)

        # ── Sous-onglets ─────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { padding: 8px 16px; font-weight: bold; }"
            "QTabBar::tab:selected { background: #2980b9; color: white; }")

        self.tabs.addTab(self._build_tab_liste(),   "📋 Tous les contrats")
        self.tabs.addTab(self._build_tab_alertes(), "⚠️  Alertes échéance")

        layout.addWidget(self.tabs)

    # =========================================================================
    # ONGLET 1 — LISTE COMPLÈTE
    # =========================================================================

    def _build_tab_liste(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Toolbar
        tb = QHBoxLayout()

        btn_new = QPushButton("➕ Nouveau contrat")
        btn_new.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 7px 14px;")
        btn_new.clicked.connect(self._new_contrat)
        tb.addWidget(btn_new)

        self.btn_edit = QPushButton("✏️ Modifier")
        self.btn_edit.setStyleSheet(
            "background-color: #3498db; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_edit.clicked.connect(self._edit_contrat)
        self.btn_edit.setEnabled(False)
        tb.addWidget(self.btn_edit)

        self.btn_reconduire = QPushButton("🔄 Reconduire")
        self.btn_reconduire.setStyleSheet(
            "background-color: #8e44ad; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_reconduire.clicked.connect(self._reconduire)
        self.btn_reconduire.setEnabled(False)
        tb.addWidget(self.btn_reconduire)

        self.btn_delete = QPushButton("🗑️ Supprimer")
        self.btn_delete.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_delete.clicked.connect(self._delete_contrat)
        self.btn_delete.setEnabled(False)
        tb.addWidget(self.btn_delete)

        tb.addStretch()

        # Filtres
        self.filter_entite = QComboBox()
        self.filter_entite.setMinimumWidth(160)
        self.filter_entite.addItem("Toutes entités", None)
        self.filter_entite.currentIndexChanged.connect(self.load_data)
        tb.addWidget(self.filter_entite)

        self.filter_type = QComboBox()
        self.filter_type.setMinimumWidth(200)
        self.filter_type.addItem("Tous types", None)
        for code, label in TYPES_CONTRAT:
            self.filter_type.addItem(label, code)
        self.filter_type.currentIndexChanged.connect(self.load_data)
        tb.addWidget(self.filter_type)

        self.filter_statut = QComboBox()
        self.filter_statut.setMinimumWidth(130)
        self.filter_statut.addItem("Tous statuts", None)
        for s in STATUTS:
            self.filter_statut.addItem(s, s)
        self.filter_statut.currentIndexChanged.connect(self.load_data)
        tb.addWidget(self.filter_statut)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setToolTip("Actualiser")
        btn_refresh.clicked.connect(self.load_data)
        tb.addWidget(btn_refresh)

        layout.addLayout(tb)

        # Tableau
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(12)
        self.tbl.setHorizontalHeaderLabels([
            "ID", "Entité", "N° Contrat", "Type", "Objet",
            "Fournisseur", "Application", "Début", "Fin",
            "Durée", "Montant HT", "Statut / Alerte"
        ])
        self.tbl.setColumnHidden(0, True)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(False)
        self.tbl.setColumnWidth(1,  90)   # Entité
        self.tbl.setColumnWidth(2, 140)   # N° contrat
        self.tbl.setColumnWidth(3, 170)   # Type
        self.tbl.setColumnWidth(4, 200)   # Objet
        self.tbl.setColumnWidth(5, 160)   # Fournisseur
        self.tbl.setColumnWidth(6, 130)   # Application
        self.tbl.setColumnWidth(7,  90)   # Début
        self.tbl.setColumnWidth(8,  90)   # Fin
        self.tbl.setColumnWidth(9,  70)   # Durée
        self.tbl.setColumnWidth(10, 120)  # Montant
        self.tbl.setColumnWidth(11, 130)  # Statut
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(self._on_selection)
        self.tbl.doubleClicked.connect(self._edit_contrat)
        layout.addWidget(self.tbl)

        return w

    # =========================================================================
    # ONGLET 2 — ALERTES
    # =========================================================================

    def _build_tab_alertes(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        filtre_row = QHBoxLayout()
        filtre_row.addWidget(QLabel("Afficher les contrats expirant dans :"))
        self.spin_jours = QSpinBox()
        self.spin_jours.setRange(0, 365)
        self.spin_jours.setValue(90)
        self.spin_jours.setSuffix(" jours")
        self.spin_jours.valueChanged.connect(self._reload_alertes)
        filtre_row.addWidget(self.spin_jours)
        filtre_row.addStretch()
        layout.addLayout(filtre_row)

        self.tbl_alertes = QTableWidget()
        self.tbl_alertes.setColumnCount(9)
        self.tbl_alertes.setHorizontalHeaderLabels([
            "ID", "Entité", "N° Contrat", "Objet", "Fournisseur",
            "Application", "Date fin", "Jours restants", "Niveau"
        ])
        self.tbl_alertes.setColumnHidden(0, True)
        hdr = self.tbl_alertes.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        self.tbl_alertes.setColumnWidth(1,  90)
        self.tbl_alertes.setColumnWidth(2, 140)
        self.tbl_alertes.setColumnWidth(3, 200)
        self.tbl_alertes.setColumnWidth(4, 160)
        self.tbl_alertes.setColumnWidth(5, 130)
        self.tbl_alertes.setColumnWidth(6,  90)
        self.tbl_alertes.setColumnWidth(7, 110)
        self.tbl_alertes.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_alertes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_alertes.doubleClicked.connect(self._edit_from_alerte)
        layout.addWidget(self.tbl_alertes)

        return w

    # =========================================================================
    # CHARGEMENT
    # =========================================================================

    def load_data(self):
        if not self.svc:
            return
        self._load_filtres_combos()

        entite_id    = self.filter_entite.currentData()
        type_contrat = self.filter_type.currentData()
        statut       = self.filter_statut.currentData()

        contrats = self.svc.get_all(
            entite_id=entite_id,
            statut=statut,
            type_contrat=type_contrat)

        self.tbl.setRowCount(len(contrats))
        for r, c in enumerate(contrats):
            self._fill_row(self.tbl, r, c)

        self._reload_alertes()
        self._update_kpis()

    def _fill_row(self, tbl, r, c):
        id_item = QTableWidgetItem(str(c['id']))
        id_item.setData(Qt.UserRole, c['id'])
        tbl.setItem(r, 0, id_item)
        tbl.setItem(r, 1, QTableWidgetItem(c.get('entite_code') or ''))
        tbl.setItem(r, 2, QTableWidgetItem(c.get('numero_contrat') or ''))

        # Type lisible
        type_code = c.get('type_contrat', '')
        type_label = next((l for k, l in TYPES_CONTRAT if k == type_code), type_code)
        tbl.setItem(r, 3, QTableWidgetItem(type_label))

        tbl.setItem(r, 4, QTableWidgetItem(c.get('objet') or ''))
        tbl.setItem(r, 5, QTableWidgetItem(c.get('fournisseur_nom') or ''))
        tbl.setItem(r, 6, QTableWidgetItem(c.get('application_nom') or '—'))
        tbl.setItem(r, 7, QTableWidgetItem(str(c.get('date_debut') or '')[:10]))
        tbl.setItem(r, 8, QTableWidgetItem(str(c.get('date_fin') or '')[:10]))

        duree = c.get('duree_mois')
        tbl.setItem(r, 9, QTableWidgetItem(f"{duree} mois" if duree else ''))

        montant = float(c.get('montant_total_ht') or c.get('montant_initial_ht') or 0)
        tbl.setItem(r, 10, QTableWidgetItem(f"{montant:,.0f} €"))

        # Statut + alerte couleur
        niveau = c.get('niveau_alerte', 'OK')
        jours  = c.get('jours_restants')
        if niveau in ('EXPIRE', 'CRITIQUE', 'ATTENTION'):
            label  = f"⚠️ {niveau} ({jours}j)"
        else:
            label  = c.get('statut', '')
        st_item = QTableWidgetItem(label)
        st_item.setBackground(QColor(ALERTE_COLORS.get(niveau, '#95a5a6')))
        st_item.setForeground(QColor('#ffffff'))
        tbl.setItem(r, 11, st_item)

    def _reload_alertes(self):
        if not self.svc:
            return
        jours    = self.spin_jours.value()
        alertes  = self.svc.get_alertes(jours)
        self.tbl_alertes.setRowCount(len(alertes))
        for r, c in enumerate(alertes):
            id_item = QTableWidgetItem(str(c['id']))
            id_item.setData(Qt.UserRole, c['id'])
            self.tbl_alertes.setItem(r, 0, id_item)
            self.tbl_alertes.setItem(r, 1, QTableWidgetItem(c.get('entite_code') or ''))
            self.tbl_alertes.setItem(r, 2, QTableWidgetItem(c.get('numero_contrat') or ''))
            self.tbl_alertes.setItem(r, 3, QTableWidgetItem(c.get('objet') or ''))
            self.tbl_alertes.setItem(r, 4, QTableWidgetItem(c.get('fournisseur_nom') or ''))
            self.tbl_alertes.setItem(r, 5, QTableWidgetItem(c.get('application_nom') or '—'))
            self.tbl_alertes.setItem(r, 6, QTableWidgetItem(str(c.get('date_fin') or '')[:10]))

            jours_r = c.get('jours_restants', 0)
            j_item  = QTableWidgetItem(
                f"EXPIRÉ" if jours_r < 0 else f"{jours_r} jours")
            j_item.setForeground(QColor('#e74c3c' if jours_r < 0 else '#e67e22'))
            self.tbl_alertes.setItem(r, 7, j_item)

            niveau  = c.get('niveau_alerte', 'INFO')
            niv_item = QTableWidgetItem(niveau)
            niv_item.setBackground(QColor(ALERTE_COLORS.get(niveau, '#95a5a6')))
            niv_item.setForeground(QColor('#ffffff'))
            self.tbl_alertes.setItem(r, 8, niv_item)

    def _update_kpis(self):
        if not self.svc:
            return
        stats = self.svc.get_stats()
        self.lbl_actifs.setText(f"  {stats.get('actifs', 0)} actifs  ")
        self.lbl_alertes.setText(f"  ⚠️ {stats.get('alertes_90j', 0)} alertes  ")
        self.lbl_expires.setText(f"  ❌ {stats.get('expires', 0)} expirés  ")

    def _load_filtres_combos(self):
        if not self.budget_svc:
            return
        entites = self.budget_svc.get_entites()
        self.filter_entite.blockSignals(True)
        current = self.filter_entite.currentData()
        self.filter_entite.clear()
        self.filter_entite.addItem("Toutes entités", None)
        for e in entites:
            self.filter_entite.addItem(e['nom'], e['id'])
        idx = self.filter_entite.findData(current)
        if idx >= 0:
            self.filter_entite.setCurrentIndex(idx)
        self.filter_entite.blockSignals(False)

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def _on_selection(self):
        has = self.tbl.currentRow() >= 0
        self.btn_edit.setEnabled(has)
        self.btn_delete.setEnabled(has)
        if has:
            st_item = self.tbl.item(self.tbl.currentRow(), 11)
            statut_txt = st_item.text() if st_item else ''
            self.btn_reconduire.setEnabled(
                'ACTIF' in statut_txt or 'RECONDUIT' in statut_txt
                or statut_txt in STATUTS[:3])
        else:
            self.btn_reconduire.setEnabled(False)

    def _get_selected_id(self):
        row = self.tbl.currentRow()
        if row < 0:
            return None
        item = self.tbl.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _new_contrat(self):
        entites      = self.budget_svc.get_entites() if self.budget_svc else []
        fournisseurs = self.fourn_svc.get_all() if self.fourn_svc else []
        applications = self.budget_svc.get_all_applications() if self.budget_svc else []
        dlg = ContratDialog(entites, fournisseurs, applications, parent=self)
        if dlg.exec_() and self.svc:
            try:
                self.svc.create(dlg.get_data())
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _edit_contrat(self):
        cid = self._get_selected_id()
        if not cid or not self.svc:
            return
        contrat      = self.svc.get_by_id(cid)
        entites      = self.budget_svc.get_entites() if self.budget_svc else []
        fournisseurs = self.fourn_svc.get_all() if self.fourn_svc else []
        applications = self.budget_svc.get_all_applications() if self.budget_svc else []
        dlg = ContratDialog(entites, fournisseurs, applications,
                            contrat=contrat, parent=self)
        if dlg.exec_():
            try:
                self.svc.update(cid, dlg.get_data())
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _edit_from_alerte(self):
        row = self.tbl_alertes.currentRow()
        if row < 0:
            return
        item = self.tbl_alertes.item(row, 0)
        cid  = item.data(Qt.UserRole) if item else None
        if not cid:
            return
        contrat      = self.svc.get_by_id(cid)
        entites      = self.budget_svc.get_entites() if self.budget_svc else []
        fournisseurs = self.fourn_svc.get_all() if self.fourn_svc else []
        applications = self.budget_svc.get_all_applications() if self.budget_svc else []
        dlg = ContratDialog(entites, fournisseurs, applications,
                            contrat=contrat, parent=self)
        if dlg.exec_():
            try:
                self.svc.update(cid, dlg.get_data())
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _reconduire(self):
        cid = self._get_selected_id()
        if not cid or not self.svc:
            return
        ct = self.svc.get_by_id(cid)
        reply = QMessageBox.question(self, "Reconduire le contrat",
            f"Reconduire « {ct.get('objet','')[:50]} » d'un an ?\n"
            f"Nouvelle date de fin : {ct.get('date_fin','')[:10]}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        result = self.svc.reconduire(cid)
        if result['ok']:
            QMessageBox.information(self, "Reconduit", result['message'])
            self.load_data()
        else:
            QMessageBox.warning(self, "Impossible", result['message'])

    def _delete_contrat(self):
        cid = self._get_selected_id()
        if not cid or not self.svc:
            return
        ct = self.svc.get_by_id(cid)
        reply = QMessageBox.question(self, "Supprimer",
            f"Supprimer le contrat « {ct.get('numero_contrat','')} » ?\n{ct.get('objet','')}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ok, msg = self.svc.delete(cid)
        if ok:
            self.load_data()
        else:
            QMessageBox.warning(self, "Impossible", msg)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _kpi_badge(self, text, color):
        lbl = QLabel(f"  {text}  ")
        lbl.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold;"
            f"border-radius:4px; padding:4px 8px; margin:2px;")
        return lbl


# =============================================================================
# DIALOG CONTRAT
# =============================================================================

class ContratDialog(QDialog):
    """Formulaire création / modification d'un contrat."""

    def __init__(self, entites, fournisseurs, applications,
                 contrat=None, parent=None):
        super().__init__(parent)
        self.entites      = entites
        self.fournisseurs = fournisseurs
        self.applications = applications
        self.contrat      = contrat
        self.setWindowTitle("✏️ Modifier contrat" if contrat else "➕ Nouveau contrat")
        self.setMinimumWidth(560)
        self.setMinimumHeight(620)
        self._build()
        if contrat:
            self._fill()

    def _build(self):
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form  = QFormLayout(inner)
        form.setSpacing(10)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # ── Identification ────────────────────────────────────────────────
        grp1 = QGroupBox("Identification")
        f1   = QFormLayout(grp1)

        self.entite = QComboBox()
        self.entite.addItem("— Choisir —", None)
        for e in self.entites:
            self.entite.addItem(e['nom'], e['id'])
        f1.addRow("Entité *:", self.entite)

        self.numero = QLineEdit()
        self.numero.setPlaceholderText("ex: 2026-DSI-001")
        f1.addRow("N° Contrat / Marché *:", self.numero)

        self.type_contrat = QComboBox()
        for code, label in TYPES_CONTRAT:
            self.type_contrat.addItem(label, code)
        self.type_contrat.currentIndexChanged.connect(self._on_type_change)
        f1.addRow("Type *:", self.type_contrat)

        self.objet = QLineEdit()
        self.objet.setPlaceholderText("Objet du contrat")
        f1.addRow("Objet *:", self.objet)

        self.fournisseur = QComboBox()
        self.fournisseur.addItem("— Choisir —", None)
        for f in self.fournisseurs:
            self.fournisseur.addItem(f.get('nom', ''), f.get('id'))
        f1.addRow("Fournisseur *:", self.fournisseur)

        self.application = QComboBox()
        self.application.addItem("— Aucune —", None)
        for a in self.applications:
            self.application.addItem(
                f"{a.get('code','')} — {a.get('nom','')}", a['id'])
        f1.addRow("Application:", self.application)

        self.nature = QComboBox()
        self.nature.addItems(['FONCTIONNEMENT', 'INVESTISSEMENT'])
        f1.addRow("Nature budget:", self.nature)

        form.addRow(grp1)

        # ── Montants ──────────────────────────────────────────────────────
        grp2 = QGroupBox("Montants")
        f2   = QFormLayout(grp2)

        # Montant annuel HT (reconduit chaque année)
        self.montant_annuel_ht = QDoubleSpinBox()
        self.montant_annuel_ht.setMaximum(9_999_999)
        self.montant_annuel_ht.setDecimals(2)
        self.montant_annuel_ht.setSuffix(" €")
        self.montant_annuel_ht.setStyleSheet("font-weight: bold;")
        self.montant_annuel_ht.valueChanged.connect(self._calc_montant_total)
        f2.addRow("Montant annuel HT *:", self.montant_annuel_ht)

        self.tva = QDoubleSpinBox()
        self.tva.setRange(0, 100)
        self.tva.setDecimals(1)
        self.tva.setValue(20.0)
        self.tva.setSuffix(" %")
        self.tva.valueChanged.connect(self._calc_ttc)
        f2.addRow("TVA:", self.tva)

        # Montant total HT = annuel × (1 + nb reconductions max) — calculé auto
        self.montant_ht = QDoubleSpinBox()
        self.montant_ht.setMaximum(99_999_999)
        self.montant_ht.setDecimals(2)
        self.montant_ht.setSuffix(" €")
        self.montant_ht.setReadOnly(True)
        self.montant_ht.setStyleSheet("background-color: #2c3e50; color: #f39c12; font-weight:bold;")
        self.montant_ht.valueChanged.connect(self._calc_ttc)
        f2.addRow("Montant total HT (calculé):", self.montant_ht)

        self.montant_ttc = QDoubleSpinBox()
        self.montant_ttc.setMaximum(99_999_999)
        self.montant_ttc.setDecimals(2)
        self.montant_ttc.setSuffix(" €")
        self.montant_ttc.setReadOnly(True)
        self.montant_ttc.setStyleSheet("background-color: #2c3e50; color: #7f8c8d;")
        f2.addRow("Montant TTC (calculé):", self.montant_ttc)

        self.montant_max = QDoubleSpinBox()
        self.montant_max.setMaximum(9_999_999)
        self.montant_max.setDecimals(2)
        self.montant_max.setSuffix(" €")
        self.lbl_montant_max = QLabel("Montant max (marché BC):")
        f2.addRow(self.lbl_montant_max, self.montant_max)

        self.deliberation = QLineEdit()
        self.deliberation.setPlaceholderText("Référence délibération / marché")
        f2.addRow("Référence marché:", self.deliberation)

        form.addRow(grp2)

        # ── Durée & Reconductions ────────────────────────────────────────
        grp3 = QGroupBox("Durée & Reconductions")
        f3   = QFormLayout(grp3)

        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        self.date_debut.dateChanged.connect(self._calc_duree)
        f3.addRow("Date début *:", self.date_debut)

        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate().addYears(1))
        self.date_fin.dateChanged.connect(self._calc_duree)
        f3.addRow("Date fin *:", self.date_fin)

        self.lbl_duree = QLabel("12 mois")
        self.lbl_duree.setStyleSheet("color: #3498db; font-weight: bold;")
        f3.addRow("Durée calculée:", self.lbl_duree)

        self.reconduction_tacite = QCheckBox("Reconduction tacite")
        f3.addRow("", self.reconduction_tacite)

        self.nb_reconductions = QSpinBox()
        self.nb_reconductions.setRange(0, 10)
        self.nb_reconductions.setValue(0)
        self.nb_reconductions.setSuffix(" fois max")
        self.nb_reconductions.valueChanged.connect(self._calc_montant_total)
        f3.addRow("Nb reconductions:", self.nb_reconductions)

        self.alerte_jours = QSpinBox()
        self.alerte_jours.setRange(0, 365)
        self.alerte_jours.setValue(90)
        self.alerte_jours.setSuffix(" jours avant")
        f3.addRow("Alerte échéance:", self.alerte_jours)

        form.addRow(grp3)

        # ── Statut & Notes ────────────────────────────────────────────────
        grp4 = QGroupBox("Statut")
        f4   = QFormLayout(grp4)

        self.statut = QComboBox()
        self.statut.addItems(STATUTS)
        self.statut.setCurrentText('ACTIF')
        f4.addRow("Statut:", self.statut)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(70)
        self.notes.setPlaceholderText("Notes, observations...")
        f4.addRow("Notes:", self.notes)

        form.addRow(grp4)

        # ── Boutons ───────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Enregistrer")
        btn_ok.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold; padding: 10px;")
        btn_ok.clicked.connect(self._validate)

        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)

        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        # Init affichage selon type
        self._on_type_change()

    def _on_type_change(self):
        """Affiche/masque le champ montant_max selon le type."""
        code = self.type_contrat.currentData()
        show = code in ('MARCHE_BC', 'ACCORD_CADRE')
        self.lbl_montant_max.setVisible(show)
        self.montant_max.setVisible(show)

    def _calc_montant_total(self):
        """Montant total = montant annuel × (1 + nb reconductions max)."""
        annuel = self.montant_annuel_ht.value()
        nb_rec = self.nb_reconductions.value()
        total  = annuel * (1 + nb_rec)
        self.montant_ht.setValue(total)
        self._calc_ttc()

    def _calc_ttc(self):
        ht  = self.montant_ht.value()
        tva = self.tva.value()
        self.montant_ttc.setValue(round(ht * (1 + tva / 100), 2))

    def _calc_duree(self):
        d1 = self.date_debut.date().toPyDate()
        d2 = self.date_fin.date().toPyDate()
        if d2 > d1:
            mois = max(1, round((d2 - d1).days / 30.44))
            self.lbl_duree.setText(f"{mois} mois")
        else:
            self.lbl_duree.setText("⚠️ Date fin < Date début")

    def _fill(self):
        c = self.contrat
        idx = self.entite.findData(c.get('entite_id'))
        if idx >= 0: self.entite.setCurrentIndex(idx)

        self.numero.setText(c.get('numero_contrat') or '')
        self.objet.setText(c.get('objet') or '')

        idx2 = self.type_contrat.findData(c.get('type_contrat'))
        if idx2 >= 0: self.type_contrat.setCurrentIndex(idx2)

        idx3 = self.fournisseur.findData(c.get('fournisseur_id'))
        if idx3 >= 0: self.fournisseur.setCurrentIndex(idx3)

        idx4 = self.application.findData(c.get('application_id'))
        if idx4 >= 0: self.application.setCurrentIndex(idx4)

        idx5 = self.nature.findText(c.get('nature') or c.get('type_budget') or 'FONCTIONNEMENT')
        if idx5 >= 0: self.nature.setCurrentIndex(idx5)

        ht = float(c.get('montant_total_ht') or c.get('montant_initial_ht') or 0)
        annuel = float(c.get('montant_annuel_ht') or 0)
        if annuel == 0 and ht > 0:
            # Rétrocompatibilité : déduire le montant annuel depuis le total
            nb_rec = int(c.get('nb_reconductions_max') or c.get('nombre_reconductions') or 0)
            annuel = ht / (1 + nb_rec) if nb_rec else ht
        self.montant_annuel_ht.setValue(annuel)
        self.montant_ht.setValue(ht)
        self.tva.setValue(float(c.get('tva') or 20.0))
        self.montant_max.setValue(float(c.get('montant_max_ht') or 0))
        self.deliberation.setText(c.get('deliberation') or c.get('piece_marche') or '')

        for field, widget in [('date_debut', self.date_debut), ('date_fin', self.date_fin)]:
            val = c.get(field)
            if val:
                self.date_debut.setDate(QDate.fromString(str(val)[:10], 'yyyy-MM-dd')) \
                    if field == 'date_debut' else \
                    self.date_fin.setDate(QDate.fromString(str(val)[:10], 'yyyy-MM-dd'))

        self.reconduction_tacite.setChecked(bool(c.get('reconduction_tacite')))
        nb = int(c.get('nb_reconductions_max') or c.get('nombre_reconductions') or 0)
        self.nb_reconductions.setValue(nb)
        self.alerte_jours.setValue(int(c.get('alerte_echeance_jours') or 90))

        idx6 = self.statut.findText(c.get('statut') or 'ACTIF')
        if idx6 >= 0: self.statut.setCurrentIndex(idx6)

        self.notes.setPlainText(c.get('notes') or '')
        self._calc_duree()
        self._on_type_change()

    def _validate(self):
        if not self.numero.text().strip():
            QMessageBox.warning(self, "Champ requis", "Le N° de contrat est obligatoire.")
            return
        if not self.objet.text().strip():
            QMessageBox.warning(self, "Champ requis", "L'objet est obligatoire.")
            return
        if not self.fournisseur.currentData():
            QMessageBox.warning(self, "Champ requis", "Le fournisseur est obligatoire.")
            return
        if self.montant_ht.value() <= 0:
            QMessageBox.warning(self, "Montant requis", "Le montant HT doit être > 0.")
            return
        self.accept()

    def get_data(self):
        return {
            'entite_id':              self.entite.currentData(),
            'numero_contrat':         self.numero.text().strip(),
            'type_contrat':           self.type_contrat.currentData(),
            'objet':                  self.objet.text().strip(),
            'fournisseur_id':         self.fournisseur.currentData(),
            'application_id':         self.application.currentData(),
            'nature':                 self.nature.currentText(),
            'montant_annuel_ht':      self.montant_annuel_ht.value(),
            'montant_initial_ht':     self.montant_ht.value(),
            'montant_total_ht':       self.montant_ht.value(),
            'tva':                    self.tva.value(),
            'montant_ttc':            self.montant_ttc.value(),
            'montant_max_ht':         self.montant_max.value() or None,
            'deliberation':           self.deliberation.text().strip(),
            'date_debut':             self.date_debut.date().toString('yyyy-MM-dd'),
            'date_fin':               self.date_fin.date().toString('yyyy-MM-dd'),
            'reconduction_tacite':    1 if self.reconduction_tacite.isChecked() else 0,
            'nb_reconductions_max':   self.nb_reconductions.value(),
            'nombre_reconductions':   self.nb_reconductions.value(),
            'alerte_echeance_jours':  self.alerte_jours.value(),
            'statut':                 self.statut.currentText(),
            'notes':                  self.notes.toPlainText().strip(),
        }
