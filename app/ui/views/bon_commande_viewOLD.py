"""
bon_commande_view.py — Vue Bons de Commande V5
Améliorations :
  #1  Vérification solde contrat avant enregistrement
  #3  Recherche texte globale (N°, objet, fournisseur, contrat, application)
  #4  Filtre contrat filtré par fournisseur sélectionné
  #5  Contrat filtré par entité dans le dialog
  #9  Historique BC par application (onglet dédié)
  #10 Lien BC → contrat avec affichage solde restant
"""
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QComboBox, QLineEdit,
    QMessageBox, QDialog, QFormLayout, QTextEdit, QDateEdit,
    QDoubleSpinBox, QGroupBox, QTabWidget, QScrollArea, QFrame,
    QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

STATUT_COLORS = {
    'BROUILLON':  '#95a5a6',
    'EN_ATTENTE': '#f39c12',
    'VALIDE':     '#2ecc71',
    'IMPUTE':     '#2980b9',
    'SOLDE':      '#1abc9c',
    'ANNULE':     '#e74c3c',
}


class BonCommandeView(QWidget):

    def __init__(self):
        super().__init__()
        self._init_services()
        self.bons_commande = []
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self.init_ui()
        self.load_data()

    def _init_services(self):
        try:
            from app.services.bon_commande_service import bon_commande_service
            self.svc = bon_commande_service
        except Exception as e:
            logger.error(f"bon_commande_service indisponible : {e}")
            self.svc = None
        try:
            from app.services.fournisseur_service import fournisseur_service
            self.fourn_svc = fournisseur_service
        except Exception:
            self.fourn_svc = None
        try:
            from app.services.projet_service import projet_service
            self.projet_svc = projet_service
        except Exception:
            self.projet_svc = None
        try:
            from app.services.budget_v5_service import budget_v5_service
            self.budget_svc = budget_v5_service
        except Exception:
            self.budget_svc = None

    # =========================================================================
    # UI
    # =========================================================================

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # En-tête KPI
        layout.addWidget(self._build_kpi_bar())

        # Sous-onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { padding: 8px 16px; font-weight: bold; }"
            "QTabBar::tab:selected { background:#2980b9; color:white; }")
        self.tabs.addTab(self._build_tab_liste(),       "📋 Liste des BC")
        self.tabs.addTab(self._build_tab_historique(),  "📊 Historique par application")
        layout.addWidget(self.tabs)

    def _build_kpi_bar(self):
        bar = QWidget()
        bar.setStyleSheet("background:#1a252f; padding:6px;")
        h = QHBoxLayout(bar)
        h.setSpacing(8)

        self.kpi_total    = self._kpi_badge("0 BC",       "#3498db")
        self.kpi_brouillon= self._kpi_badge("0 brouillon","#95a5a6")
        self.kpi_attente  = self._kpi_badge("0 en attente","#f39c12")
        self.kpi_valide   = self._kpi_badge("0 validés",  "#2ecc71")
        self.kpi_impute   = self._kpi_badge("0 imputés",  "#2980b9")
        self.kpi_montant  = self._kpi_badge("0 €",        "#e74c3c")

        for w in (self.kpi_total, self.kpi_brouillon, self.kpi_attente,
                  self.kpi_valide, self.kpi_impute, self.kpi_montant):
            h.addWidget(w)
        h.addStretch()
        return bar

    def _kpi_badge(self, text, color):
        lbl = QLabel(f"  {text}  ")
        lbl.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold;"
            f"border-radius:4px; padding:4px 10px; margin:2px;")
        return lbl

    # ── Onglet 1 : Liste ─────────────────────────────────────────────────────

    def _build_tab_liste(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Toolbar actions
        tb = QHBoxLayout()
        self.btn_add    = self._btn("➕ Nouveau BC", "#27ae60", self._new_bc)
        self.btn_edit   = self._btn("✏️ Modifier",  "#3498db", self._edit_bc, False)
        self.btn_valider= self._btn("✅ Valider",   "#2ecc71", self._valider_bc, False)
        self.btn_imputer= self._btn("💰 Imputer",   "#8e44ad", self._imputer_bc, False)
        self.btn_fiche  = self._btn("📄 Fiche détail", "#2c3e50", self._voir_fiche, False)
        self.btn_delete = self._btn("🗑️ Supprimer", "#e74c3c", self._delete_bc, False)
        for b in (self.btn_add, self.btn_edit, self.btn_valider,
                  self.btn_imputer, self.btn_fiche, self.btn_delete):
            tb.addWidget(b)
        tb.addStretch()
        layout.addLayout(tb)

        # Filtres
        fl = QHBoxLayout()

        fl.addWidget(QLabel("Statut:"))
        self.filter_statut = QComboBox()
        self.filter_statut.setMinimumWidth(120)
        self.filter_statut.addItem("Tous", None)
        for s in STATUT_COLORS:
            self.filter_statut.addItem(s, s)
        self.filter_statut.currentIndexChanged.connect(self.apply_filters)
        fl.addWidget(self.filter_statut)

        fl.addWidget(QLabel("Entité:"))
        self.filter_entite = QComboBox()
        self.filter_entite.setMinimumWidth(120)
        self.filter_entite.addItem("Toutes", None)
        self.filter_entite.currentIndexChanged.connect(self.apply_filters)
        fl.addWidget(self.filter_entite)

        fl.addWidget(QLabel("Fournisseur:"))
        self.filter_fournisseur = QComboBox()
        self.filter_fournisseur.setMinimumWidth(150)
        self.filter_fournisseur.addItem("Tous", None)
        self.filter_fournisseur.currentIndexChanged.connect(self.apply_filters)
        fl.addWidget(self.filter_fournisseur)

        fl.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Recherche N° BC, objet, fournisseur, contrat, application...")
        self.search_input.setMinimumWidth(280)
        self.search_input.textChanged.connect(
            lambda: self._search_timer.start(300))
        fl.addWidget(self.search_input)

        btn_clear = QPushButton("✕")
        btn_clear.setFixedWidth(28)
        btn_clear.clicked.connect(lambda: self.search_input.clear())
        fl.addWidget(btn_clear)

        fl.addStretch()
        layout.addLayout(fl)

        # Tableau
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ID", "Entité", "N° BC", "Date", "Fournisseur",
            "Objet", "Contrat", "Ligne budgétaire",
            "HT", "TTC", "Statut", "Application"
        ])
        self.table.setColumnHidden(0, True)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(False)
        self.table.setColumnWidth(1,  70)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3,  90)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 200)
        self.table.setColumnWidth(6, 140)
        self.table.setColumnWidth(7, 160)
        self.table.setColumnWidth(8,  90)
        self.table.setColumnWidth(9,  90)
        self.table.setColumnWidth(10, 100)
        self.table.setColumnWidth(11, 130)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.doubleClicked.connect(self._voir_fiche)
        layout.addWidget(self.table)

        return w

    def _btn(self, label, color, slot, enabled=True):
        b = QPushButton(label)
        b.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold; padding:7px 14px;")
        b.clicked.connect(slot)
        b.setEnabled(enabled)
        return b

    # ── Onglet 2 : Historique par application ────────────────────────────────

    def _build_tab_historique(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        fl = QHBoxLayout()
        fl.addWidget(QLabel("Application:"))
        self.hist_combo_app = QComboBox()
        self.hist_combo_app.setMinimumWidth(250)
        self.hist_combo_app.addItem("— Choisir —", None)
        self.hist_combo_app.currentIndexChanged.connect(self._load_historique)
        fl.addWidget(self.hist_combo_app)

        fl.addWidget(QLabel("Exercice:"))
        self.hist_combo_exercice = QComboBox()
        self.hist_combo_exercice.setMinimumWidth(100)
        self.hist_combo_exercice.addItem("Tous", None)
        for y in range(2024, 2028):
            self.hist_combo_exercice.addItem(str(y), y)
        self.hist_combo_exercice.currentIndexChanged.connect(self._load_historique)
        fl.addWidget(self.hist_combo_exercice)

        fl.addStretch()
        layout.addLayout(fl)

        # Totaux
        self.hist_totaux = QLabel("Sélectionnez une application")
        self.hist_totaux.setStyleSheet(
            "background:#2c3e50; color:#ecf0f1; padding:8px; border-radius:4px;")
        layout.addWidget(self.hist_totaux)

        # Tableau historique
        self.tbl_hist = QTableWidget()
        self.tbl_hist.setColumnCount(9)
        self.tbl_hist.setHorizontalHeaderLabels([
            "ID", "N° BC", "Date", "Fournisseur", "Objet",
            "Contrat", "Ligne budg.", "TTC", "Statut"
        ])
        self.tbl_hist.setColumnHidden(0, True)
        hdr = self.tbl_hist.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        self.tbl_hist.setColumnWidth(1, 130)
        self.tbl_hist.setColumnWidth(2,  90)
        self.tbl_hist.setColumnWidth(3, 150)
        self.tbl_hist.setColumnWidth(4, 200)
        self.tbl_hist.setColumnWidth(5, 140)
        self.tbl_hist.setColumnWidth(6, 150)
        self.tbl_hist.setColumnWidth(7,  90)
        self.tbl_hist.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_hist.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tbl_hist)

        return w

    # =========================================================================
    # CHARGEMENT
    # =========================================================================

    def load_data(self):
        if not self.svc:
            return
        self._load_combos()
        self.bons_commande = self.svc.get_all_bons_commande()
        self._update_kpis()
        self.apply_filters()
        self._load_hist_combo_apps()
        logger.info(f"{len(self.bons_commande)} bon(s) de commande chargé(s)")

    def _load_combos(self):
        # Entités
        if self.budget_svc:
            entites = self.budget_svc.get_entites()
            self.filter_entite.blockSignals(True)
            self.filter_entite.clear()
            self.filter_entite.addItem("Toutes", None)
            for e in entites:
                self.filter_entite.addItem(e['nom'], e['id'])
            self.filter_entite.blockSignals(False)

        # Fournisseurs
        if self.fourn_svc:
            fournisseurs = self.fourn_svc.get_all()
            self.filter_fournisseur.blockSignals(True)
            self.filter_fournisseur.clear()
            self.filter_fournisseur.addItem("Tous", None)
            for f in fournisseurs:
                self.filter_fournisseur.addItem(f.get('nom', ''), f.get('id'))
            self.filter_fournisseur.blockSignals(False)

    def _load_hist_combo_apps(self):
        if not self.budget_svc:
            return
        apps = self.budget_svc.get_all_applications()
        self.hist_combo_app.blockSignals(True)
        self.hist_combo_app.clear()
        self.hist_combo_app.addItem("— Choisir —", None)
        for a in apps:
            self.hist_combo_app.addItem(
                f"{a.get('code','')} — {a.get('nom','')}", a['id'])
        self.hist_combo_app.blockSignals(False)

    def _update_kpis(self):
        if not self.svc:
            return
        s = self.svc.get_stats()
        self.kpi_total.setText(f"  {s.get('total',0)} BC  ")
        self.kpi_brouillon.setText(f"  {s.get('brouillon',0)} brouillon  ")
        self.kpi_attente.setText(f"  {s.get('en_attente',0)} en attente  ")
        self.kpi_valide.setText(f"  {s.get('valide',0)} validés  ")
        self.kpi_impute.setText(f"  {s.get('impute',0)} imputés  ")
        m = float(s.get('montant_total') or 0)
        self.kpi_montant.setText(f"  {m:,.0f} €  ")

    def apply_filters(self):
        statut    = self.filter_statut.currentData()
        entite_id = self.filter_entite.currentData()
        fourn_id  = self.filter_fournisseur.currentData()
        search    = self.search_input.text().strip().lower()

        data = self.bons_commande
        if statut:
            data = [b for b in data if b.get('statut') == statut]
        if entite_id:
            data = [b for b in data if b.get('entite_id') == entite_id]
        if fourn_id:
            data = [b for b in data if b.get('fournisseur_id') == fourn_id]
        if search:
            data = [b for b in data if any(
                search in str(b.get(f, '') or '').lower()
                for f in ('numero_bc', 'objet', 'fournisseur_nom',
                          'numero_contrat', 'application_nom',
                          'ligne_libelle', 'description'))]

        self._display(data)

    def _do_search(self):
        self.apply_filters()

    def _display(self, data):
        self.table.setRowCount(len(data))
        for r, bc in enumerate(data):
            id_item = QTableWidgetItem(str(bc['id']))
            id_item.setData(Qt.UserRole, bc['id'])
            self.table.setItem(r, 0, id_item)
            self.table.setItem(r, 1, QTableWidgetItem(bc.get('entite_code') or ''))
            self.table.setItem(r, 2, QTableWidgetItem(bc.get('numero_bc') or ''))
            date_str = str(bc.get('date_creation') or bc.get('date_commande') or '')[:10]
            self.table.setItem(r, 3, QTableWidgetItem(date_str))
            self.table.setItem(r, 4, QTableWidgetItem(bc.get('fournisseur_nom') or ''))
            self.table.setItem(r, 5, QTableWidgetItem(bc.get('objet') or ''))
            self.table.setItem(r, 6, QTableWidgetItem(bc.get('numero_contrat') or '—'))
            self.table.setItem(r, 7, QTableWidgetItem(bc.get('ligne_libelle') or '—'))
            ht  = float(bc.get('montant_ht') or 0)
            ttc = float(bc.get('montant_ttc') or 0)
            self.table.setItem(r, 8,  QTableWidgetItem(f"{ht:,.0f} €"))
            self.table.setItem(r, 9,  QTableWidgetItem(f"{ttc:,.0f} €"))
            statut = bc.get('statut', '')
            st_item = QTableWidgetItem(statut)
            st_item.setBackground(QColor(STATUT_COLORS.get(statut, '#95a5a6')))
            st_item.setForeground(QColor('#ffffff'))
            self.table.setItem(r, 10, st_item)
            self.table.setItem(r, 11, QTableWidgetItem(bc.get('application_nom') or '—'))

    def _load_historique(self):
        app_id   = self.hist_combo_app.currentData()
        exercice = self.hist_combo_exercice.currentData()
        if not app_id or not self.svc:
            return
        bcs = self.svc.get_historique_application(app_id, exercice)
        self.tbl_hist.setRowCount(len(bcs))
        total = 0
        for r, bc in enumerate(bcs):
            id_item = QTableWidgetItem(str(bc['id']))
            id_item.setData(Qt.UserRole, bc['id'])
            self.tbl_hist.setItem(r, 0, id_item)
            self.tbl_hist.setItem(r, 1, QTableWidgetItem(bc.get('numero_bc') or ''))
            date_str = str(bc.get('date_creation') or '')[:10]
            self.tbl_hist.setItem(r, 2, QTableWidgetItem(date_str))
            self.tbl_hist.setItem(r, 3, QTableWidgetItem(bc.get('fournisseur_nom') or ''))
            self.tbl_hist.setItem(r, 4, QTableWidgetItem(bc.get('objet') or ''))
            self.tbl_hist.setItem(r, 5, QTableWidgetItem(bc.get('numero_contrat') or '—'))
            self.tbl_hist.setItem(r, 6, QTableWidgetItem(bc.get('ligne_libelle') or '—'))
            ttc = float(bc.get('montant_ttc') or 0)
            total += ttc
            self.tbl_hist.setItem(r, 7, QTableWidgetItem(f"{ttc:,.0f} €"))
            statut = bc.get('statut', '')
            st = QTableWidgetItem(statut)
            st.setBackground(QColor(STATUT_COLORS.get(statut, '#95a5a6')))
            st.setForeground(QColor('#ffffff'))
            self.tbl_hist.setItem(r, 8, st)

        exo_label = f"exercice {exercice}" if exercice else "tous exercices"
        self.hist_totaux.setText(
            f"  {len(bcs)} BC  |  Total TTC : {total:,.0f} €  |  {exo_label}  ")

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def _on_selection(self):
        row    = self.table.currentRow()
        has    = row >= 0
        self.btn_edit.setEnabled(has)
        self.btn_delete.setEnabled(has)
        if has:
            statut = (self.table.item(row, 10) or QTableWidgetItem('')).text()
            self.btn_valider.setEnabled(statut in ('BROUILLON', 'EN_ATTENTE'))
            self.btn_imputer.setEnabled(statut == 'VALIDE')
            self.btn_fiche.setEnabled(True)
        else:
            self.btn_valider.setEnabled(False)
            self.btn_imputer.setEnabled(False)
            self.btn_fiche.setEnabled(False)

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _voir_fiche(self):
        bc_id = self._get_selected_id()
        if not bc_id:
            return
        try:
            from app.ui.views.fiche_bc_view import FicheBCDialog
            dlg = FicheBCDialog(bc_id, parent=self)
            dlg.exec_()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Erreur", str(e))

    def _new_bc(self):
        dlg = BonCommandeDialog(
            budget_svc=self.budget_svc,
            fourn_svc=self.fourn_svc,
            projet_svc=self.projet_svc,
            bc_svc=self.svc,
            parent=self)
        if dlg.exec_() == QDialog.Accepted and self.svc:
            try:
                data = dlg.get_data()
                bc_id = self.svc.creer_bon_commande(data)
                # Créer le projet associé si la case est cochée
                if dlg.chk_creer_projet.isChecked():
                    self._creer_projet_depuis_bc(bc_id, data, dlg)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))


    def _creer_projet_depuis_bc(self, bc_id, data, dlg):
        """Crée une fiche projet depuis un BC si la case est cochée."""
        try:
            from app.services.projet_service import projet_service
            from datetime import date

            # Correspondance statut BC → statut projet
            bc_to_statut = {
                'BROUILLON':  'PLANIFIE',
                'EN_ATTENTE': 'PLANIFIE',
                'VALIDE':     'EN_COURS',
                'IMPUTE':     'EN_COURS',
                'SOLDE':      'TERMINE',
                'ANNULE':     'ANNULE',
            }
            statut_bc     = data.get('statut', 'BROUILLON')
            statut_projet = bc_to_statut.get(statut_bc, 'PLANIFIE')

            # Date début = aujourd'hui, fin = date livraison BC si renseignée
            date_debut   = date.today().isoformat()
            date_fin     = data.get('date_livraison_prevue') or date_debut

            # Durée en heures → stocker dans description
            duree_h = dlg.projet_duree.value()

            # Nom du projet = objet du BC
            nom = data.get('objet') or f"Projet BC-{bc_id}"

            projet_data = {
                'nom':           nom,
                'description':   f"Projet créé automatiquement depuis BC #{bc_id}\nDurée estimée : {duree_h}h",
                'statut':        statut_projet,
                'phase':         'REALISATION' if statut_projet == 'EN_COURS' else 'INITIALISATION',
                'priorite':      'NORMALE',
                'type_projet':   'ACQUISITION',
                'date_debut':    date_debut,
                'date_fin_prevue': date_fin,
                'budget_estime': float(data.get('montant_ttc') or 0),
                'budget_initial': float(data.get('montant_ht') or 0),
                'budget_actuel': float(data.get('montant_ttc') or 0),
                'avancement':    0,
                'entite_id':     data.get('entite_id'),
            }

            projet_id = projet_service.create(projet_data)

            # Rattacher le fournisseur comme prestataire
            fourn_id = data.get('fournisseur_id')
            if fourn_id and projet_id:
                try:
                    from app.services.database_service import db_service
                    conn = db_service.get_connection()
                    conn.execute(
                        "INSERT OR IGNORE INTO projet_prestataires (projet_id, fournisseur_id) VALUES (?,?)",
                        (projet_id, fourn_id)
                    )
                    # Lier BC ↔ projet
                    conn.execute(
                        "UPDATE bons_commande SET projet_id=? WHERE id=?",
                        (projet_id, bc_id)
                    )
                    conn.commit()
                except Exception:
                    pass

            QMessageBox.information(
                self, "Projet créé",
                f"✅ Fiche projet créée avec succès\n"
                f"Nom : {nom}\n"
                f"Statut : {statut_projet}\n"
                f"Budget estimé : {float(data.get('montant_ttc') or 0):,.0f} €\n"
                f"Durée : {duree_h}h"
            )
        except Exception as e:
            QMessageBox.warning(self, "Projet non créé", f"Le BC a été créé mais la création du projet a échoué :\n{e}")

    def _edit_bc(self):
        bc_id = self._get_selected_id()
        if not bc_id or not self.svc:
            return
        bc = self.svc.get_bon_commande_by_id(bc_id)
        dlg = BonCommandeDialog(
            budget_svc=self.budget_svc,
            fourn_svc=self.fourn_svc,
            projet_svc=self.projet_svc,
            bc_svc=self.svc,
            bc=bc, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            try:
                self.svc.modifier_bon_commande(bc_id, dlg.get_data())
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _valider_bc(self):
        bc_id = self._get_selected_id()
        if not bc_id or not self.svc:
            return
        result = self.svc.valider_bon_commande(bc_id)
        if result['ok']:
            self.load_data()
        else:
            QMessageBox.warning(self, "Impossible", result['message'])

    def _imputer_bc(self):
        bc_id = self._get_selected_id()
        if not bc_id or not self.svc:
            return
        bc = self.svc.get_bon_commande_by_id(bc_id)
        if not bc.get('ligne_budgetaire_id'):
            QMessageBox.warning(self, "Ligne manquante",
                "Ce BC n'est pas rattaché à une ligne budgétaire.\n"
                "Modifiez-le et sélectionnez une ligne avant d'imputer.")
            return
        result = self.svc.imputer_bon_commande(bc_id)
        if result['ok']:
            QMessageBox.information(self, "BC imputé", result.get('message', '✅'))
            self.load_data()
        else:
            QMessageBox.warning(self, "Impossible", result['message'])

    def _delete_bc(self):
        bc_id = self._get_selected_id()
        if not bc_id or not self.svc:
            return
        bc = self.svc.get_bon_commande_by_id(bc_id)
        reply = QMessageBox.question(self, "Supprimer",
            f"Supprimer le BC « {bc.get('numero_bc','')} » ?\n{bc.get('objet','')}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        result = self.svc.supprimer_bon_commande(bc_id)
        if result['ok']:
            try:
                from app.services.integrity_service import integrity_service
                integrity_service.log('BC', bc_id, 'SUPPRESSION',
                    f"Suppression BC {bc.get('numero_bc','')} — {bc.get('objet','')[:50]}")
            except Exception:
                pass
            self.load_data()
        else:
            QMessageBox.warning(self, "Impossible", result['message'])


# =============================================================================
# DIALOG BC — avec vérification solde contrat
# =============================================================================

class BonCommandeDialog(QDialog):

    def __init__(self, budget_svc=None, fourn_svc=None, projet_svc=None,
                 bc_svc=None, bc=None, parent=None):
        super().__init__(parent)
        self.budget_svc  = budget_svc
        self.fourn_svc   = fourn_svc
        self.projet_svc  = projet_svc
        self.bc_svc      = bc_svc
        self.bc          = bc
        self.setWindowTitle("✏️ Modifier BC" if bc else "➕ Nouveau Bon de Commande")
        self.setMinimumWidth(600)
        self.setMinimumHeight(680)
        self._build()
        if bc:
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

        # ── Identification ─────────────────────────────────────────────────
        grp1 = QGroupBox("Identification")
        f1   = QFormLayout(grp1)

        self.entite = QComboBox()
        self.entite.addItem("— Choisir —", None)
        if self.budget_svc:
            for e in self.budget_svc.get_entites():
                self.entite.addItem(e['nom'], e['id'])
        self.entite.currentIndexChanged.connect(self._on_entite_change)
        f1.addRow("Entité *:", self.entite)

        self.numero_bc = QLineEdit()
        self.numero_bc.setPlaceholderText("ex: BC-VILLE-2026-001")
        f1.addRow("N° BC *:", self.numero_bc)

        self.objet = QLineEdit()
        self.objet.setPlaceholderText("Objet du bon de commande")
        f1.addRow("Objet *:", self.objet)

        self.fournisseur = QComboBox()
        self.fournisseur.addItem("— Choisir —", None)
        if self.fourn_svc:
            for f in self.fourn_svc.get_all():
                self.fournisseur.addItem(f.get('nom', ''), f.get('id'))
        self.fournisseur.currentIndexChanged.connect(self._on_fournisseur_change)
        f1.addRow("Fournisseur *:", self.fournisseur)

        self.nature = QComboBox()
        self.nature.addItems(['FONCTIONNEMENT', 'INVESTISSEMENT'])
        f1.addRow("Nature:", self.nature)

        form.addRow(grp1)

        # ── Contrat & Ligne budgétaire ────────────────────────────────────
        grp2 = QGroupBox("Rattachement budgétaire")
        f2   = QFormLayout(grp2)

        self.contrat = QComboBox()
        self.contrat.addItem("— Hors marché —", None)
        self.contrat.currentIndexChanged.connect(self._on_contrat_change)
        f2.addRow("Contrat / Marché:", self.contrat)

        # Indicateur solde contrat
        self.lbl_solde_contrat = QLabel("")
        self.lbl_solde_contrat.setStyleSheet("color:#2ecc71; font-style:italic;")
        self.lbl_solde_contrat.setWordWrap(True)
        f2.addRow("", self.lbl_solde_contrat)

        self.ligne_budg = QComboBox()
        self.ligne_budg.addItem("— Aucune —", None)
        self.ligne_budg.currentIndexChanged.connect(self._on_ligne_change)
        f2.addRow("Ligne budgétaire:", self.ligne_budg)

        self.lbl_solde_ligne = QLabel("")
        self.lbl_solde_ligne.setStyleSheet("color:#3498db; font-style:italic;")
        f2.addRow("", self.lbl_solde_ligne)

        self.application = QComboBox()
        self.application.addItem("— Aucune —", None)
        if self.budget_svc:
            for a in self.budget_svc.get_all_applications():
                self.application.addItem(
                    f"{a.get('code','')} — {a.get('nom','')}", a['id'])
        f2.addRow("Application:", self.application)

        self.projet = QComboBox()
        self.projet.addItem("— Aucun —", None)
        if self.projet_svc:
            for p in self.projet_svc.get_all():
                self.projet.addItem(p.get('nom', ''), p.get('id'))
        f2.addRow("Projet:", self.projet)

        form.addRow(grp2)

        # ── Dates ─────────────────────────────────────────────────────────
        grp3 = QGroupBox("Dates")
        f3   = QFormLayout(grp3)

        self.date_commande = QDateEdit()
        self.date_commande.setCalendarPopup(True)
        self.date_commande.setDate(QDate.currentDate())
        f3.addRow("Date commande:", self.date_commande)

        self.date_livraison = QDateEdit()
        self.date_livraison.setCalendarPopup(True)
        self.date_livraison.setDate(QDate.currentDate().addDays(30))
        f3.addRow("Livraison prévue:", self.date_livraison)

        form.addRow(grp3)

        # ── Montants ───────────────────────────────────────────────────────
        grp4 = QGroupBox("Montants")
        f4   = QFormLayout(grp4)

        self.montant_ht = QDoubleSpinBox()
        self.montant_ht.setMaximum(9_999_999)
        self.montant_ht.setDecimals(2)
        self.montant_ht.setSuffix(" €")
        self.montant_ht.valueChanged.connect(self._calc_ttc)
        f4.addRow("Montant HT *:", self.montant_ht)

        self.taux_tva = QDoubleSpinBox()
        self.taux_tva.setRange(0, 100)
        self.taux_tva.setDecimals(1)
        self.taux_tva.setValue(20.0)
        self.taux_tva.setSuffix(" %")
        self.taux_tva.valueChanged.connect(self._calc_ttc)
        f4.addRow("Taux TVA:", self.taux_tva)

        self.montant_ttc = QDoubleSpinBox()
        self.montant_ttc.setMaximum(9_999_999)
        self.montant_ttc.setDecimals(2)
        self.montant_ttc.setSuffix(" €")
        self.montant_ttc.setReadOnly(True)
        self.montant_ttc.setStyleSheet("background:#2c3e50; color:#7f8c8d;")
        f4.addRow("Montant TTC (calculé):", self.montant_ttc)

        # Alerte dépassement contrat
        self.lbl_alerte_contrat = QLabel("")
        self.lbl_alerte_contrat.setStyleSheet(
            "color:#e74c3c; font-weight:bold; padding:4px;")
        self.lbl_alerte_contrat.setWordWrap(True)
        self.lbl_alerte_contrat.hide()
        f4.addRow("", self.lbl_alerte_contrat)

        self.montant_ttc.valueChanged.connect(self._check_solde_contrat)

        form.addRow(grp4)

        # ── Statut & Notes ─────────────────────────────────────────────────
        grp5 = QGroupBox("Statut")
        f5   = QFormLayout(grp5)

        self.statut = QComboBox()
        self.statut.addItems(['BROUILLON', 'EN_ATTENTE', 'VALIDE', 'IMPUTE', 'SOLDE', 'ANNULE'])
        f5.addRow("Statut:", self.statut)

        self.description = QTextEdit()
        self.description.setMaximumHeight(70)
        self.description.setPlaceholderText("Description / notes...")
        f5.addRow("Description:", self.description)

        form.addRow(grp5)

        # ── Création projet liée ───────────────────────────────────────────
        grp6 = QGroupBox("🗂️ Projet associé")
        grp6.setStyleSheet("QGroupBox { color: #3498db; font-weight: bold; }")
        f6   = QFormLayout(grp6)

        self.chk_creer_projet = QCheckBox("Créer aussi une fiche projet")
        self.chk_creer_projet.setChecked(False)
        f6.addRow("", self.chk_creer_projet)

        self.projet_duree = QDoubleSpinBox()
        self.projet_duree.setRange(0.25, 999)
        self.projet_duree.setValue(1.0)
        self.projet_duree.setDecimals(2)
        self.projet_duree.setSuffix(" h")
        self.projet_duree.setEnabled(False)
        f6.addRow("Durée estimée:", self.projet_duree)

        self.chk_creer_projet.toggled.connect(self.projet_duree.setEnabled)
        form.addRow(grp6)

        # ── Boutons ────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Enregistrer")
        btn_ok.setStyleSheet(
            "background:#2ecc71; color:white; font-weight:bold; padding:10px;")
        btn_ok.clicked.connect(self._validate)
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    # ── Slots dynamiques ─────────────────────────────────────────────────────

    def _on_entite_change(self):
        """Recharge contrats et lignes selon l'entité."""
        self._reload_contrats()
        self._reload_lignes()

    def _on_fournisseur_change(self):
        """Filtre les contrats selon le fournisseur sélectionné."""
        self._reload_contrats()

    def _reload_contrats(self):
        entite_id = self.entite.currentData()
        fourn_id  = self.fournisseur.currentData()
        if not self.budget_svc:
            return
        try:
            from app.services.contrat_service import contrat_service
            contrats = contrat_service.get_all(entite_id=entite_id)
            if fourn_id:
                contrats = [c for c in contrats if c.get('fournisseur_id') == fourn_id]
            self.contrat.blockSignals(True)
            current = self.contrat.currentData()
            self.contrat.clear()
            self.contrat.addItem("— Hors marché —", None)
            for c in contrats:
                label = f"{c.get('numero_contrat','')} — {c.get('objet','')[:40]}"
                self.contrat.addItem(label, c['id'])
            idx = self.contrat.findData(current)
            if idx >= 0:
                self.contrat.setCurrentIndex(idx)
            self.contrat.blockSignals(False)
            self._on_contrat_change()
        except Exception:
            pass

    def _on_contrat_change(self):
        """Affiche le solde du contrat sélectionné."""
        contrat_id = self.contrat.currentData()
        if not contrat_id:
            self.lbl_solde_contrat.setText("")
            return
        try:
            from app.services.contrat_service import contrat_service
            ct = contrat_service.get_by_id(contrat_id)
            if ct:
                montant_max  = float(ct.get('montant_max_ht') or ct.get('montant_total_ht') or 0)
                engage       = float(ct.get('montant_engage_cumul') or 0)
                solde        = montant_max - engage
                pct          = (engage / montant_max * 100) if montant_max else 0
                self.lbl_solde_contrat.setText(
                    f"📋 {ct.get('type_contrat','')} — "
                    f"Max: {montant_max:,.0f} € | "
                    f"Engagé: {engage:,.0f} € | "
                    f"Solde: {solde:,.0f} € ({pct:.0f}%)")
                self._check_solde_contrat()
                # Auto-remplir fournisseur
                fourn_id = ct.get('fournisseur_id')
                if fourn_id:
                    idx = self.fournisseur.findData(fourn_id)
                    if idx >= 0:
                        self.fournisseur.blockSignals(True)
                        self.fournisseur.setCurrentIndex(idx)
                        self.fournisseur.blockSignals(False)
        except Exception:
            pass

    def _check_solde_contrat(self):
        """Vérifie en temps réel si le montant dépasse le solde du contrat."""
        contrat_id = self.contrat.currentData()
        montant    = self.montant_ttc.value()
        if not contrat_id or not montant or not self.bc_svc:
            self.lbl_alerte_contrat.hide()
            return
        bc_id = self.bc.get('id') if self.bc else None
        ok, msg, _ = self.bc_svc.verifier_solde_contrat(contrat_id, montant, bc_id)
        if not ok:
            self.lbl_alerte_contrat.setText(msg)
            self.lbl_alerte_contrat.show()
        else:
            self.lbl_alerte_contrat.hide()

    def _reload_lignes(self):
        entite_id = self.entite.currentData()
        if not self.budget_svc:
            return
        try:
            lignes = self.budget_svc.get_lignes(entite_id=entite_id)
            self.ligne_budg.blockSignals(True)
            current = self.ligne_budg.currentData()
            self.ligne_budg.clear()
            self.ligne_budg.addItem("— Aucune —", None)
            for lb in lignes:
                solde = float(lb.get('montant_solde') or 0)
                label = f"{lb.get('libelle','')} — solde: {solde:,.0f} €"
                self.ligne_budg.addItem(label, lb['id'])
            idx = self.ligne_budg.findData(current)
            if idx >= 0:
                self.ligne_budg.setCurrentIndex(idx)
            self.ligne_budg.blockSignals(False)
            self._on_ligne_change()
        except Exception:
            pass

    def _on_ligne_change(self):
        lid = self.ligne_budg.currentData()
        if not lid or not self.budget_svc:
            self.lbl_solde_ligne.setText("")
            return
        try:
            lb = self.budget_svc.get_ligne_by_id(lid)
            if lb:
                vote   = float(lb.get('montant_vote') or 0)
                engage = float(lb.get('montant_engage') or 0)
                solde  = float(lb.get('montant_solde') or 0)
                pct    = (engage / vote * 100) if vote else 0
                color  = "#e74c3c" if pct >= 80 else "#2ecc71"
                self.lbl_solde_ligne.setStyleSheet(f"color:{color}; font-style:italic;")
                self.lbl_solde_ligne.setText(
                    f"📊 Voté: {vote:,.0f} € | "
                    f"Engagé: {engage:,.0f} € | "
                    f"Solde: {solde:,.0f} € ({pct:.0f}%)")
        except Exception:
            pass

    def _calc_ttc(self):
        ht  = self.montant_ht.value()
        tva = self.taux_tva.value()
        self.montant_ttc.setValue(round(ht * (1 + tva / 100), 2))

    # ── Pré-remplissage ───────────────────────────────────────────────────────

    def _fill(self):
        bc = self.bc

        idx = self.entite.findData(bc.get('entite_id'))
        if idx >= 0:
            self.entite.setCurrentIndex(idx)

        self.numero_bc.setText(bc.get('numero_bc') or '')
        self.objet.setText(bc.get('objet') or '')

        idx2 = self.fournisseur.findData(bc.get('fournisseur_id'))
        if idx2 >= 0:
            self.fournisseur.setCurrentIndex(idx2)

        self._reload_contrats()
        idx3 = self.contrat.findData(bc.get('contrat_id'))
        if idx3 >= 0:
            self.contrat.setCurrentIndex(idx3)

        self._reload_lignes()
        idx4 = self.ligne_budg.findData(bc.get('ligne_budgetaire_id'))
        if idx4 >= 0:
            self.ligne_budg.setCurrentIndex(idx4)

        idx5 = self.application.findData(bc.get('application_id'))
        if idx5 >= 0:
            self.application.setCurrentIndex(idx5)

        idx6 = self.projet.findData(bc.get('projet_id'))
        if idx6 >= 0:
            self.projet.setCurrentIndex(idx6)

        for field, widget in [
            ('date_creation', self.date_commande),
            ('date_livraison_prevue', self.date_livraison)
        ]:
            val = bc.get(field)
            if val:
                widget.setDate(QDate.fromString(str(val)[:10], 'yyyy-MM-dd'))

        ht  = float(bc.get('montant_ht') or 0)
        tva = float(bc.get('tva') or 20.0)
        self.montant_ht.setValue(ht)
        self.taux_tva.setValue(tva)

        nature = bc.get('nature') or bc.get('type_budget') or 'FONCTIONNEMENT'
        idx7 = self.nature.findText(nature)
        if idx7 >= 0:
            self.nature.setCurrentIndex(idx7)

        idx8 = self.statut.findText(bc.get('statut') or 'BROUILLON')
        if idx8 >= 0:
            self.statut.setCurrentIndex(idx8)

        self.description.setPlainText(bc.get('description') or bc.get('notes') or '')

    # ── Validation & données ──────────────────────────────────────────────────

    def _validate(self):
        if not self.numero_bc.text().strip():
            QMessageBox.warning(self, "Champ requis", "Le N° BC est obligatoire.")
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

        # Vérification solde contrat (#1)
        contrat_id = self.contrat.currentData()
        montant    = self.montant_ttc.value()
        if contrat_id and self.bc_svc:
            bc_id = self.bc.get('id') if self.bc else None
            ok, msg, _ = self.bc_svc.verifier_solde_contrat(contrat_id, montant, bc_id)
            if not ok:
                reply = QMessageBox.warning(self, "⚠️ Dépassement contrat",
                    msg + "\n\nVoulez-vous quand même enregistrer ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return

        self.accept()

    def get_data(self):
        return {
            'entite_id':            self.entite.currentData(),
            'numero_bc':            self.numero_bc.text().strip(),
            'objet':                self.objet.text().strip(),
            'fournisseur_id':       self.fournisseur.currentData(),
            'contrat_id':           self.contrat.currentData(),
            'ligne_budgetaire_id':  self.ligne_budg.currentData(),
            'application_id':       self.application.currentData(),
            'projet_id':            self.projet.currentData(),
            'date_commande':        self.date_commande.date().toString('yyyy-MM-dd'),
            'date_livraison_prevue':self.date_livraison.date().toString('yyyy-MM-dd'),
            'montant_ht':           self.montant_ht.value(),
            'tva':                  self.taux_tva.value(),
            'montant_ttc':          self.montant_ttc.value(),
            'nature':               self.nature.currentText(),
            'type_budget':          self.nature.currentText(),
            'statut':               self.statut.currentText(),
            'description':          self.description.toPlainText().strip(),
        }
