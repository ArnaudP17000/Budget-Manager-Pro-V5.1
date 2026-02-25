"""
Dialogue de création/édition de projet.
"""
import logging
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QMessageBox, QLabel, QTabWidget, QWidget, QDialogButtonBox,
    QListWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QFileDialog, QInputDialog, QListWidgetItem,
    QCheckBox, QSplitter, QProgressBar, QGroupBox, QScrollArea, QGridLayout,
    QSizePolicy, QFrame
)
from PyQt5.QtCore import QDate, Qt, QSize
from PyQt5.QtGui import QColor, QFont, QBrush
from app.services.database_service import db_service
from app.services.projet_service import projet_service
from app.ui.dialogs.document_dialog import DocumentDialog
from app.ui.dialogs.tache_dialog import TacheDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError, IndexError):
        return default

logger = logging.getLogger(__name__)

class ProjetDialog(QDialog):
    """Dialogue de création/édition de projet."""
    
    def __init__(self, parent=None, projet=None):
        super().__init__(parent)
        self.projet = projet
        self.projet_id = projet['id'] if projet else None
        self.setWindowTitle("Nouveau Projet" if not projet else "Modifier Projet")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setup_ui()
        
        if projet:
            self.load_projet_data()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        
        # Onglets
        self.tabs = QTabWidget()
        
        # Onglet 1: Général
        general_tab = self.create_general_tab()
        self.tabs.addTab(general_tab, "📋 Général")
        
        # Onglet 2: Budget
        opportunite_tab = self.create_opportunite_tab()
        self.tabs.addTab(opportunite_tab, "🎯 Opportunité")

        budget_tab = self.create_budget_tab()
        self.tabs.addTab(budget_tab, "💰 Budget")
        
        # Onglet 3: Équipe
        equipe_tab = self.create_equipe_tab()
        self.tabs.addTab(equipe_tab, "👥 Équipe")
        
        # Onglet 4: Contacts
        acteurs_tab = self.create_acteurs_tab()
        self.tabs.addTab(acteurs_tab, "🪪 Acteurs détail")

        couts_tab = self.create_couts_tab()
        self.tabs.addTab(couts_tab, "💶 Coûts & Charges")

        contacts_tab = self.create_contacts_tab()
        self.tabs.addTab(contacts_tab, "📞 Contacts")
        
        # Onglet 5: Documents
        documents_tab = self.create_documents_tab()
        self.tabs.addTab(documents_tab, "📄 Documents")
        
        # Onglet 6: Tâches
        taches_tab = self.create_taches_tab()
        self.tabs.addTab(taches_tab, "✓ Tâches")
        
        layout.addWidget(self.tabs)
        
        # Boutons
        btn_layout = QHBoxLayout()

        self.btn_fiche = QPushButton("🖨️ Exporter Fiche Word")
        self.btn_fiche.setStyleSheet(
            "background:#C00000;color:white;font-weight:bold;padding:6px 14px;border-radius:4px;")
        self.btn_fiche.clicked.connect(self._exporter_fiche)
        btn_layout.addWidget(self.btn_fiche)

        btn_layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        btn_layout.addWidget(buttons)
        layout.addLayout(btn_layout)
    
    def create_general_tab(self):
        """Crée l'onglet Général."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        
        # Code projet
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("PRJ2024-001 (auto si vide)")
        form.addRow("Code projet:", self.code_edit)
        
        # Nom projet
        self.nom_edit = QLineEdit()
        self.nom_edit.setPlaceholderText("Nom du projet")
        form.addRow("Nom *:", self.nom_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Description du projet")
        self.description_edit.setMaximumHeight(80)
        form.addRow("Description:", self.description_edit)
        
        # Type projet
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Infrastructure",
            "Application",
            "Réseau",
            "Sécurité",
            "Support",
            "Autre"
        ])
        form.addRow("Type projet:", self.type_combo)
        
        # Phase
        self.phase_combo = QComboBox()
        self.phase_combo.addItems([
            "ETUDE",
            "CONCEPTION",
            "REALISATION",
            "RECETTE",
            "CLOTURE"
        ])
        form.addRow("Phase:", self.phase_combo)
        
        # Priorité
        self.priorite_combo = QComboBox()
        self.priorite_combo.addItems([
            "CRITIQUE",
            "HAUTE",
            "MOYENNE",
            "BASSE"
        ])
        self.priorite_combo.setCurrentIndex(2)
        form.addRow("Priorité:", self.priorite_combo)
        
        # Statut
        self.statut_combo = QComboBox()
        self.statut_combo.addItems([
            "ACTIF",
            "EN_ATTENTE",
            "TERMINE",
            "ANNULE"
        ])
        form.addRow("Statut *:", self.statut_combo)
        
        # Date début
        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        form.addRow("Date début *:", self.date_debut)
        
        # Date fin prévue
        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate().addMonths(6))
        form.addRow("Date fin prévue *:", self.date_fin)
        
        # Date fin réelle
        # Checkbox pour activer la date réelle
        self.chk_termine = QCheckBox("Projet terminé")
        self.chk_termine.setChecked(False)
        form.addRow("", self.chk_termine)

        self.date_fin_reelle = QDateEdit()
        self.date_fin_reelle.setCalendarPopup(True)
        self.date_fin_reelle.setDate(QDate.currentDate())
        self.date_fin_reelle.setEnabled(False)
        self.chk_termine.toggled.connect(self.date_fin_reelle.setEnabled)
        self.chk_termine.toggled.connect(self._on_termine_toggled)
        form.addRow("Date fin réelle:", self.date_fin_reelle)
        
        # Avancement
        self.avancement_spin = QSpinBox()
        self.avancement_spin.setRange(0, 100)
        self.avancement_spin.setSuffix(" %")
        form.addRow("Avancement %:", self.avancement_spin)
        
        # Service bénéficiaire
        self.service_combo = QComboBox()
        self.service_combo.addItem("-- Aucun --", None)
        # Charger les services
        try:
            services = db_service.fetch_all(
                "SELECT id, code, nom FROM services ORDER BY code"
            )
            for service in services:
                self.service_combo.addItem(f"{service['code']} - {service['nom']}", service['id'])
        except Exception as e:
            logger.error(f"Erreur chargement services: {e}")
        form.addRow("Service bénéficiaire:", self.service_combo)
        
        layout.addLayout(form)
        layout.addStretch()
        return widget
    
    def create_opportunite_tab(self):
        """Onglet Opportunite — objectifs, risques, gains, solutions + registre risques."""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # Sous-onglets : Contexte | Registre risques | Contraintes 6 axes | Triangle d or
        sub_tabs = QTabWidget()
        sub_tabs.setStyleSheet(
            "QTabBar::tab { padding: 5px 12px; font-size: 11px; }"
        )
        main_layout.addWidget(sub_tabs)

        # ── Sous-onglet 1 : Contexte (champs texte existants) ──────────────
        ctx = QWidget()
        ctx_layout = QVBoxLayout(ctx)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.objectifs_edit = QTextEdit()
        self.objectifs_edit.setPlaceholderText("Objectifs metier operationnels du projet...")
        self.objectifs_edit.setMinimumHeight(70)
        form.addRow("Objectifs metier:", self.objectifs_edit)

        self.enjeux_edit = QTextEdit()
        self.enjeux_edit.setPlaceholderText("Enjeux strategiques de l etablissement...")
        self.enjeux_edit.setMinimumHeight(55)
        form.addRow("Enjeux strategiques:", self.enjeux_edit)

        self.gains_edit = QTextEdit()
        self.gains_edit.setPlaceholderText("Gains qualitatifs et benefices attendus...")
        self.gains_edit.setMinimumHeight(55)
        form.addRow("Gains / Benefices:", self.gains_edit)

        self.risques_edit = QTextEdit()
        self.risques_edit.setPlaceholderText("Risques a NE PAS faire le projet...")
        self.risques_edit.setMinimumHeight(55)
        form.addRow("Risques / Freins:", self.risques_edit)

        self.contraintes_edit = QTextEdit()
        self.contraintes_edit.setPlaceholderText("Contraintes techniques, reglementaires, RGPD...")
        self.contraintes_edit.setMinimumHeight(50)
        form.addRow("Contraintes:", self.contraintes_edit)

        self.solutions_edit = QTextEdit()
        self.solutions_edit.setPlaceholderText("Solutions organisationnelles et techniques...")
        self.solutions_edit.setMinimumHeight(50)
        form.addRow("Solutions:", self.solutions_edit)

        ctx_layout.addLayout(form)
        sub_tabs.addTab(ctx, "📝 Contexte")

        # ── Sous-onglet 2 : Registre des risques ───────────────────────────
        rsk = QWidget()
        rsk_layout = QVBoxLayout(rsk)

        # Barre d outils
        rsk_toolbar = QHBoxLayout()
        btn_add_risk = QPushButton("➕ Ajouter risque")
        btn_add_risk.setStyleSheet(
            "background:#27ae60;color:white;font-weight:bold;padding:5px 12px;")
        btn_add_risk.clicked.connect(self._add_risque_row)
        rsk_toolbar.addWidget(btn_add_risk)

        btn_del_risk = QPushButton("🗑️ Supprimer")
        btn_del_risk.setStyleSheet(
            "background:#e74c3c;color:white;font-weight:bold;padding:5px 12px;")
        btn_del_risk.clicked.connect(self._del_risque_row)
        rsk_toolbar.addWidget(btn_del_risk)
        rsk_toolbar.addStretch()

        lbl_legende = QLabel(
            "  🔴 Critique (>=12)   🟠 Eleve (6-11)   🟡 Modere (3-5)   🟢 Faible (1-2)")
        lbl_legende.setStyleSheet("color:#95a5a6; font-size:11px;")
        rsk_toolbar.addWidget(lbl_legende)
        rsk_layout.addLayout(rsk_toolbar)

        # Tableau registre des risques
        self.tbl_risques = QTableWidget(0, 7)
        self.tbl_risques.setHorizontalHeaderLabels([
            "Description du risque",
            "Categorie",
            "Proba (1-4)",
            "Impact (1-4)",
            "Criticite (P x I)",
            "Action corrective",
            "Statut"
        ])
        hdr_r = self.tbl_risques.horizontalHeader()
        hdr_r.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr_r.setSectionResizeMode(5, QHeaderView.Stretch)
        self.tbl_risques.setColumnWidth(1, 110)
        self.tbl_risques.setColumnWidth(2, 80)
        self.tbl_risques.setColumnWidth(3, 70)
        self.tbl_risques.setColumnWidth(4, 75)
        self.tbl_risques.setColumnWidth(6, 90)
        self.tbl_risques.setAlternatingRowColors(True)
        self.tbl_risques.itemChanged.connect(self._update_criticite)
        rsk_layout.addWidget(self.tbl_risques)
        sub_tabs.addTab(rsk, "⚠️ Registre risques")

        # ── Sous-onglet 3 : Les 6 contraintes ──────────────────────────────
        ctr = QWidget()
        ctr_layout = QVBoxLayout(ctr)

        lbl_intro = QLabel(
            "Les 6 contraintes sont interconnectees — modifier l une impacte les autres.")
        lbl_intro.setStyleSheet(
            "color:#3498db; font-style:italic; padding:4px 0; font-size:12px;")
        ctr_layout.addWidget(lbl_intro)

        grid = QGridLayout()
        grid.setSpacing(8)

        CONTRAINTES_DEF = [
            ("🎯 Portee",         "portee_desc",
             "Perimetre, livrables, fonctionnalites incluses. Une portee large = plus de temps et de budget."),
            ("💰 Couts",          "couts_desc",
             "Budget global, salaires, equipements, licences. Ressources financieres."),
            ("⏱ Delais",          "delais_desc",
             "Calendrier, jalons, phases, dates cles. Toute modification impacte les autres."),
            ("⚡ Ressources",      "ressources_desc",
             "Equipes, competences, equipements, logiciels. Mauvaise allocation = retards."),
            ("🔍 Qualite",        "qualite_desc",
             "Criteres d acceptation, niveaux de service. Influencee par toutes les contraintes."),
            ("🎲 Risques projets","risques_proj_desc",
             "Evenements imprevisibles pouvant impacter le projet. Voir registre des risques."),
        ]

        self._contraintes_edits = {}
        for i, (label, attr, placeholder) in enumerate(CONTRAINTES_DEF):
            grp = QGroupBox(label)
            grp.setStyleSheet(
                "QGroupBox { font-weight:bold; border:1px solid #34495e;"
                "border-radius:4px; margin-top:8px; padding:6px; }"
                "QGroupBox::title { subcontrol-origin:margin; left:8px; color:#3498db; }")
            g_layout = QVBoxLayout(grp)
            edit = QTextEdit()
            edit.setPlaceholderText(placeholder)
            edit.setMinimumHeight(60)
            edit.setMaximumHeight(80)
            g_layout.addWidget(edit)
            self._contraintes_edits[attr] = edit
            grid.addWidget(grp, i // 2, i % 2)

        ctr_layout.addLayout(grid)
        sub_tabs.addTab(ctr, "🔗 6 Contraintes")

        # ── Sous-onglet 4 : Triangle d or ──────────────────────────────────
        tri = QWidget()
        tri_layout = QVBoxLayout(tri)

        lbl_tri = QLabel("Triangle d or : Portee / Couts / Delais")
        lbl_tri.setStyleSheet(
            "font-size:14px; font-weight:bold; color:#f39c12; padding:6px 0;")
        tri_layout.addWidget(lbl_tri)

        lbl_tri_desc = QLabel(
            "Toucher a l un impose de reajuster les deux autres pour garder l equilibre. "
            "Evaluez la tension sur chaque axe : 1 = sous controle, 5 = tres tendu.")
        lbl_tri_desc.setStyleSheet("color:#95a5a6; font-size:11px;")
        lbl_tri_desc.setWordWrap(True)
        tri_layout.addWidget(lbl_tri_desc)

        tri_grid = QGridLayout()
        tri_grid.setSpacing(12)

        TRIANGLE_AXES = [
            ("🎯 Portee",  "tension_portee",
             "Risque de derive du perimetre (scope creep) ?"),
            ("💰 Couts",   "tension_couts",
             "Pression sur le budget disponible ?"),
            ("⏱ Delais",  "tension_delais",
             "Pression sur le calendrier ?"),
        ]
        self._tension_spins = {}
        for col, (label, attr, tooltip) in enumerate(TRIANGLE_AXES):
            box = QGroupBox(label)
            box.setStyleSheet(
                "QGroupBox { font-weight:bold; border:2px solid #f39c12;"
                "border-radius:6px; margin-top:10px; padding:10px; }"
                "QGroupBox::title { color:#f39c12; subcontrol-origin:margin; left:10px; }")
            b_lay = QVBoxLayout(box)

            spin = QSpinBox()
            spin.setRange(1, 5)
            spin.setValue(3)
            spin.setToolTip(tooltip)
            spin.setStyleSheet(
                "QSpinBox { font-size:20px; font-weight:bold; padding:4px;"
                "min-width:60px; text-align:center; }")
            spin.valueChanged.connect(self._update_triangle_display)
            b_lay.addWidget(spin, alignment=Qt.AlignCenter)

            bar = QProgressBar()
            bar.setRange(1, 5)
            bar.setValue(3)
            bar.setTextVisible(False)
            bar.setMaximumHeight(12)
            bar.setStyleSheet(
                "QProgressBar { border:1px solid #555; border-radius:3px; }"
                "QProgressBar::chunk { background:#f39c12; border-radius:3px; }")
            b_lay.addWidget(bar)

            lbl_hint = QLabel(tooltip)
            lbl_hint.setStyleSheet("color:#7f8c8d; font-size:10px;")
            lbl_hint.setWordWrap(True)
            b_lay.addWidget(lbl_hint)

            self._tension_spins[attr] = (spin, bar)
            tri_grid.addWidget(box, 0, col)

        tri_layout.addLayout(tri_grid)

        # Zone d alerte triangle
        self.lbl_triangle_alerte = QLabel("")
        self.lbl_triangle_alerte.setStyleSheet(
            "font-size:12px; padding:8px; border-radius:4px; margin-top:8px;")
        self.lbl_triangle_alerte.setWordWrap(True)
        tri_layout.addWidget(self.lbl_triangle_alerte)

        # Arbitrage
        arb_grp = QGroupBox("Strategie d arbitrage")
        arb_lay = QVBoxLayout(arb_grp)
        self.arbitrage_edit = QTextEdit()
        self.arbitrage_edit.setPlaceholderText(
            "Si les delais sont serres, quelle concession est acceptable ? "
            "Reduire la portee ? Augmenter le budget ? Phaser les livrables ?...")
        self.arbitrage_edit.setMinimumHeight(70)
        arb_lay.addWidget(self.arbitrage_edit)
        tri_layout.addWidget(arb_grp)
        tri_layout.addStretch()
        sub_tabs.addTab(tri, "🔺 Triangle d or")

        self._update_triangle_display()
        return widget

    # ── Méthodes Registre des risques ────────────────────────────────────────

    def _add_risque_row(self, data=None):
        """Ajoute une ligne dans le registre des risques."""
        r = self.tbl_risques.rowCount()
        self.tbl_risques.insertRow(r)

        # Description
        desc = QTableWidgetItem(data.get('description', '') if data else '')
        self.tbl_risques.setItem(r, 0, desc)

        # Categorie (combo)
        cat_combo = QComboBox()
        for c in ['Planning', 'Budget', 'Technique', 'Ressources',
                  'Qualite', 'Perimetre', 'Organisationnel', 'Autre']:
            cat_combo.addItem(c)
        if data:
            idx = cat_combo.findText(data.get('categorie', ''))
            if idx >= 0:
                cat_combo.setCurrentIndex(idx)
        self.tbl_risques.setCellWidget(r, 1, cat_combo)

        # Probabilite (1-4)
        prob_spin = QSpinBox()
        prob_spin.setRange(1, 4)
        prob_spin.setValue(int(data.get('probabilite', 2)) if data else 2)
        prob_spin.valueChanged.connect(lambda v, row=r: self._recalc_criticite(row))
        self.tbl_risques.setCellWidget(r, 2, prob_spin)

        # Impact (1-4)
        imp_spin = QSpinBox()
        imp_spin.setRange(1, 4)
        imp_spin.setValue(int(data.get('impact', 2)) if data else 2)
        imp_spin.valueChanged.connect(lambda v, row=r: self._recalc_criticite(row))
        self.tbl_risques.setCellWidget(r, 3, imp_spin)

        # Criticite (calculee)
        crit_item = QTableWidgetItem('')
        crit_item.setFlags(crit_item.flags() & ~Qt.ItemIsEditable)
        crit_item.setTextAlignment(Qt.AlignCenter)
        self.tbl_risques.setItem(r, 4, crit_item)

        # Action corrective
        action = QTableWidgetItem(data.get('action', '') if data else '')
        self.tbl_risques.setItem(r, 5, action)

        # Statut (combo)
        statut_combo = QComboBox()
        for s in ['Identifie', 'En cours', 'Surveille', 'Resolu', 'Accepte']:
            statut_combo.addItem(s)
        if data:
            idx = statut_combo.findText(data.get('statut', ''))
            if idx >= 0:
                statut_combo.setCurrentIndex(idx)
        self.tbl_risques.setCellWidget(r, 6, statut_combo)

        self._recalc_criticite(r)

    def _del_risque_row(self):
        row = self.tbl_risques.currentRow()
        if row >= 0:
            self.tbl_risques.removeRow(row)

    def _update_criticite(self, item):
        pass  # Geree par _recalc_criticite via spinbox

    def _recalc_criticite(self, row):
        """Recalcule criticite = probabilite x impact et colorie la cellule."""
        try:
            prob_w = self.tbl_risques.cellWidget(row, 2)
            imp_w  = self.tbl_risques.cellWidget(row, 3)
            if not prob_w or not imp_w:
                return
            crit = prob_w.value() * imp_w.value()
            item = self.tbl_risques.item(row, 4)
            if not item:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
                self.tbl_risques.setItem(row, 4, item)
            item.setText(str(crit))
            if crit >= 12:
                item.setBackground(QBrush(QColor('#c0392b')))
                item.setForeground(QBrush(QColor('white')))
            elif crit >= 6:
                item.setBackground(QBrush(QColor('#e67e22')))
                item.setForeground(QBrush(QColor('white')))
            elif crit >= 3:
                item.setBackground(QBrush(QColor('#f1c40f')))
                item.setForeground(QBrush(QColor('#2c3e50')))
            else:
                item.setBackground(QBrush(QColor('#27ae60')))
                item.setForeground(QBrush(QColor('white')))
        except Exception:
            pass

    def _get_risques_data(self):
        """Exporte le registre des risques en liste de dicts."""
        result = []
        for r in range(self.tbl_risques.rowCount()):
            prob_w  = self.tbl_risques.cellWidget(r, 2)
            imp_w   = self.tbl_risques.cellWidget(r, 3)
            cat_w   = self.tbl_risques.cellWidget(r, 1)
            stat_w  = self.tbl_risques.cellWidget(r, 6)
            desc    = self.tbl_risques.item(r, 0)
            action  = self.tbl_risques.item(r, 5)
            if desc and desc.text().strip():
                result.append({
                    'description':  desc.text().strip(),
                    'categorie':    cat_w.currentText() if cat_w else '',
                    'probabilite':  prob_w.value() if prob_w else 2,
                    'impact':       imp_w.value() if imp_w else 2,
                    'criticite':    (prob_w.value() * imp_w.value()) if (prob_w and imp_w) else 4,
                    'action':       action.text().strip() if action else '',
                    'statut':       stat_w.currentText() if stat_w else 'Identifie',
                })
        return result

    def _load_risques_data(self, risques_json):
        """Charge le registre des risques depuis JSON stocke."""
        import json
        if not risques_json:
            return
        try:
            risques = json.loads(risques_json) if isinstance(risques_json, str) else risques_json
            for r in risques:
                self._add_risque_row(r)
        except Exception as e:
            logger.warning("Chargement registre risques : %s", e)

    # ── Méthodes Triangle d or ─────────────────────────────────────────────

    def _update_triangle_display(self):
        """Met a jour les barres et l alerte du triangle d or."""
        try:
            vals = {}
            for attr, (spin, bar) in self._tension_spins.items():
                v = spin.value()
                vals[attr] = v
                bar.setValue(v)
                if v >= 4:
                    bar.setStyleSheet(
                        "QProgressBar::chunk { background:#e74c3c; } "
                        "QProgressBar { border:1px solid #555; border-radius:3px; }")
                elif v >= 3:
                    bar.setStyleSheet(
                        "QProgressBar::chunk { background:#f39c12; } "
                        "QProgressBar { border:1px solid #555; border-radius:3px; }")
                else:
                    bar.setStyleSheet(
                        "QProgressBar::chunk { background:#27ae60; } "
                        "QProgressBar { border:1px solid #555; border-radius:3px; }")

            tensions_elevees = [k.replace('tension_', '').capitalize()
                                for k, v in vals.items() if v >= 4]
            total = sum(vals.values())

            if total >= 13:
                msg = ("🔴 ALERTE : Triangle d or tres tendu sur tous les axes ! "
                       "Un arbitrage urgent est necessaire.")
                style = "background:#5c1010; color:#ff6b6b; border:1px solid #c0392b;"
            elif tensions_elevees:
                axes = ', '.join(tensions_elevees)
                msg = (f"🟠 Tension elevee sur : {axes}. "
                       "Envisagez un arbitrage sur les axes concernes.")
                style = "background:#5c3a10; color:#f39c12; border:1px solid #e67e22;"
            else:
                msg = "🟢 Triangle equilibre — les trois axes sont sous controle."
                style = "background:#0f3d1e; color:#2ecc71; border:1px solid #27ae60;"

            self.lbl_triangle_alerte.setText(msg)
            self.lbl_triangle_alerte.setStyleSheet(
                f"font-size:12px; padding:8px; border-radius:4px; margin-top:8px; {style}")
        except Exception:
            pass

    def _get_contraintes_data(self):
        """Exporte les 6 contraintes en dict."""
        return {attr: edit.toPlainText().strip()
                for attr, edit in self._contraintes_edits.items()}

    def _get_triangle_data(self):
        """Exporte les valeurs de tension du triangle."""
        return {attr: spin.value()
                for attr, (spin, bar) in self._tension_spins.items()}

    def create_budget_tab(self):
        """Crée l'onglet Budget — V5 (lignes budgétaires)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()

        # Budget prévisionnel
        self.budget_initial_spin = QDoubleSpinBox()
        self.budget_initial_spin.setRange(0, 100000000)
        self.budget_initial_spin.setSingleStep(1000)
        self.budget_initial_spin.setSuffix(" €")
        self.budget_initial_spin.setDecimals(2)
        form.addRow("Budget prévisionnel:", self.budget_initial_spin)

        # Budget estimé
        self.budget_estime_spin = QDoubleSpinBox()
        self.budget_estime_spin.setRange(0, 100000000)
        self.budget_estime_spin.setSingleStep(1000)
        self.budget_estime_spin.setSuffix(" €")
        self.budget_estime_spin.setDecimals(2)
        form.addRow("Budget estimé:", self.budget_estime_spin)

        # Budget actuel (voté)
        self.budget_actuel_spin = QDoubleSpinBox()
        self.budget_actuel_spin.setRange(0, 100000000)
        self.budget_actuel_spin.setSingleStep(1000)
        self.budget_actuel_spin.setSuffix(" €")
        self.budget_actuel_spin.setDecimals(2)
        form.addRow("Budget voté:", self.budget_actuel_spin)

        # Budget consommé (lecture seule — calculé depuis BC)
        self.budget_consomme_label = QLabel("0,00 €")
        self.budget_consomme_label.setStyleSheet("color:#e67e22;font-weight:bold;")
        form.addRow("Budget consommé (BC):", self.budget_consomme_label)

        # Ligne budgétaire liée (V5)
        self.ligne_budg_combo = QComboBox()
        self.ligne_budg_combo.addItem("-- Aucune ligne --", None)
        try:
            from app.services.budget_v5_service import budget_v5_service
            lignes = budget_v5_service.get_lignes()
            for lb in lignes:
                label = f"{lb.get('entite_code','')} | {lb.get('libelle','')[:40]} ({lb.get('exercice','')})"
                self.ligne_budg_combo.addItem(label, lb['id'])
        except Exception as e:
            logger.error(f"Erreur chargement lignes budgétaires: {e}")
        form.addRow("Ligne budgétaire V5:", self.ligne_budg_combo)

        # Récapitulatif BC liés
        self.bc_recap_label = QLabel("Aucun BC lié")
        self.bc_recap_label.setStyleSheet("color:#95a5a6;font-style:italic;")
        self.bc_recap_label.setWordWrap(True)
        form.addRow("BC liés:", self.bc_recap_label)

        layout.addLayout(form)
        layout.addStretch()
        return widget
    
    def create_equipe_tab(self):
        """Crée l'onglet Équipe."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        
        # Responsable projet
        row_resp = QHBoxLayout()
        self.responsable_combo = QComboBox()
        self.responsable_combo.setMinimumWidth(300)
        self.responsable_combo.setEditable(True)
        self.responsable_combo.setInsertPolicy(QComboBox.NoInsert)
        self.responsable_combo.completer().setFilterMode(Qt.MatchContains)
        self.responsable_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self._charger_personnes(self.responsable_combo)
        self.responsable_combo.lineEdit().setPlaceholderText("Tapez un nom...")
        row_resp.addWidget(self.responsable_combo)
        btn_add_resp = QPushButton("➕")
        btn_add_resp.setFixedWidth(32)
        btn_add_resp.setToolTip("Créer un agent DSI")
        btn_add_resp.clicked.connect(lambda: self._ajouter_agent(self.responsable_combo))
        row_resp.addWidget(btn_add_resp)
        form.addRow("Responsable *:", row_resp)

        # Chef de projet
        row_chef = QHBoxLayout()
        self.chef_projet_combo = QComboBox()
        self.chef_projet_combo.setMinimumWidth(300)
        self.chef_projet_combo.setEditable(True)
        self.chef_projet_combo.setInsertPolicy(QComboBox.NoInsert)
        self.chef_projet_combo.completer().setFilterMode(Qt.MatchContains)
        self.chef_projet_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self._charger_personnes(self.chef_projet_combo)
        self.chef_projet_combo.lineEdit().setPlaceholderText("Tapez un nom...")
        row_chef.addWidget(self.chef_projet_combo)
        btn_add_chef = QPushButton("➕")
        btn_add_chef.setFixedWidth(32)
        btn_add_chef.setToolTip("Créer un agent DSI")
        btn_add_chef.clicked.connect(lambda: self._ajouter_agent(self.chef_projet_combo))
        row_chef.addWidget(btn_add_chef)
        form.addRow("Chef de projet:", row_chef)
        
        layout.addLayout(form)
        
        # Équipe DSI (multi-selection)
        layout.addWidget(QLabel("Membres de l'équipe projet :"))

        # Barre d'ajout avec recherche
        add_row = QHBoxLayout()
        self.equipe_search = QComboBox()
        self.equipe_search.setEditable(True)
        self.equipe_search.setInsertPolicy(QComboBox.NoInsert)
        self.equipe_search.setMinimumWidth(320)
        self.equipe_search.completer().setFilterMode(Qt.MatchContains)
        self.equipe_search.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self._charger_personnes(self.equipe_search)
        self.equipe_search.lineEdit().setPlaceholderText("Tapez un nom pour filtrer...")
        add_row.addWidget(self.equipe_search)
        btn_ajouter_membre = QPushButton("➕ Ajouter")
        btn_ajouter_membre.setStyleSheet(
            "background:#27ae60; color:white; font-weight:bold; padding:6px 12px;")
        btn_ajouter_membre.clicked.connect(self._ajouter_membre_equipe)
        add_row.addWidget(btn_ajouter_membre)
        add_row.addStretch()
        layout.addLayout(add_row)

        # Liste des membres sélectionnés
        self.equipe_list = QListWidget()
        self.equipe_list.setMaximumHeight(150)
        self.equipe_list.setStyleSheet("QListWidget { background: #2c3e50; color: #ecf0f1; }")
        layout.addWidget(self.equipe_list)

        btn_retirer = QPushButton("🗑️ Retirer le membre sélectionné")
        btn_retirer.setStyleSheet("color: #e74c3c; font-size: 11px;")
        btn_retirer.clicked.connect(
            lambda: self.equipe_list.takeItem(self.equipe_list.currentRow())
            if self.equipe_list.currentRow() >= 0 else None)
        layout.addWidget(btn_retirer)
        
        layout.addWidget(QLabel("Prestataires / Fournisseurs :"))

        # Barre d'ajout prestataire
        prest_row = QHBoxLayout()
        self.prestataire_search = QComboBox()
        self.prestataire_search.setMinimumWidth(320)
        self.prestataire_search.setEditable(True)
        self.prestataire_search.setInsertPolicy(QComboBox.NoInsert)
        self.prestataire_search.completer().setFilterMode(Qt.MatchContains)
        self.prestataire_search.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.prestataire_search.addItem("-- Choisir --", None)
        try:
            fournisseurs = db_service.fetch_all(
                "SELECT id, nom FROM fournisseurs WHERE actif=1 ORDER BY nom"
            ) or []
            for f in fournisseurs:
                self.prestataire_search.addItem(f['nom'], f['id'])
        except Exception as e:
            logger.error(f"Chargement fournisseurs : {e}")
        prest_row.addWidget(self.prestataire_search)
        btn_add_prest = QPushButton("➕ Ajouter")
        btn_add_prest.setStyleSheet(
            "background:#27ae60; color:white; font-weight:bold; padding:6px 12px;")
        btn_add_prest.clicked.connect(self._ajouter_prestataire)
        prest_row.addWidget(btn_add_prest)
        prest_row.addStretch()
        layout.addLayout(prest_row)

        self.prestataires_list = QListWidget()
        self.prestataires_list.setMaximumHeight(130)
        self.prestataires_list.setStyleSheet("QListWidget { background: #2c3e50; color: #ecf0f1; }")
        layout.addWidget(self.prestataires_list)

        btn_retirer_prest = QPushButton("🗑️ Retirer le prestataire sélectionné")
        btn_retirer_prest.setStyleSheet("color: #e74c3c; font-size: 11px;")
        btn_retirer_prest.clicked.connect(
            lambda: self.prestataires_list.takeItem(self.prestataires_list.currentRow())
            if self.prestataires_list.currentRow() >= 0 else None)
        layout.addWidget(btn_retirer_prest)
        
        layout.addStretch()
        return widget
    
    def create_acteurs_tab(self):
        """Onglet Acteurs détail — Fonction/Service et Email/Tél de chaque membre."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl = QLabel(
            "Completez ici la fonction/service et les coordonnees de chaque acteur du projet. "
            "Ces informations apparaitront dans la section Equipe & Contacts de la fiche Word.")
        lbl.setStyleSheet("color:#7f8c8d; font-style:italic; padding:4px;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        # Tableau éditable : Rôle | Nom | Fonction/Service | Email | Téléphone
        self.acteurs_table = QTableWidget(0, 5)
        self.acteurs_table.setHorizontalHeaderLabels(
            ["Rôle", "Nom Prénom", "Fonction / Service", "Email", "Téléphone"])
        hdr = self.acteurs_table.horizontalHeader()
        hdr.setSectionResizeMode(0, hdr.ResizeToContents)
        hdr.setSectionResizeMode(1, hdr.Stretch)
        hdr.setSectionResizeMode(2, hdr.Stretch)
        hdr.setSectionResizeMode(3, hdr.Stretch)
        hdr.setSectionResizeMode(4, hdr.ResizeToContents)
        self.acteurs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.acteurs_table.setAlternatingRowColors(True)
        layout.addWidget(self.acteurs_table)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualiser depuis Équipe")
        btn_refresh.setToolTip("Recharge les membres depuis l'onglet Équipe")
        btn_refresh.clicked.connect(self._refresh_acteurs_table)
        btn_layout.addWidget(btn_refresh)
        btn_add_row = QPushButton("➕ Ligne manuelle")
        btn_add_row.clicked.connect(self._add_acteur_row)
        btn_layout.addWidget(btn_add_row)
        btn_del_row = QPushButton("🗑️ Supprimer")
        btn_del_row.clicked.connect(self._del_acteur_row)
        btn_layout.addWidget(btn_del_row)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        return widget

    def _refresh_acteurs_table(self):
        """Recharge le tableau acteurs depuis l'onglet Équipe + chef/responsable."""
        t = self.acteurs_table
        # Récupérer les lignes déjà saisies pour ne pas écraser les coordonnées
        existing = {}
        for r in range(t.rowCount()):
            nom_item = t.item(r, 1)
            if nom_item:
                key = nom_item.text().strip()
                existing[key] = {
                    'role':     (t.item(r, 0).text() if t.item(r, 0) else ''),
                    'fonction': (t.item(r, 2).text() if t.item(r, 2) else ''),
                    'email':    (t.item(r, 3).text() if t.item(r, 3) else ''),
                    'tel':      (t.item(r, 4).text() if t.item(r, 4) else ''),
                }

        rows_data = []

        # Chef de projet
        chef_text = self.chef_projet_combo.currentText().strip()
        if chef_text and '---' not in chef_text:
            ex = existing.get(chef_text, {})
            rows_data.append({
                'role': ex.get('role', 'Chef de projet DSI'),
                'nom': chef_text,
                'fonction': ex.get('fonction', ''),
                'email': ex.get('email', ''),
                'tel': ex.get('tel', ''),
            })

        # Responsable
        resp_text = self.responsable_combo.currentText().strip()
        if resp_text and '---' not in resp_text and resp_text != chef_text:
            ex = existing.get(resp_text, {})
            rows_data.append({
                'role': ex.get('role', 'Responsable métier'),
                'nom': resp_text,
                'fonction': ex.get('fonction', ''),
                'email': ex.get('email', ''),
                'tel': ex.get('tel', ''),
            })

        # Membres équipe
        for i in range(self.equipe_list.count()):
            item = self.equipe_list.item(i)
            if not item: continue
            nom = item.text().replace('👤 ', '').replace('📇 ', '').strip()
            ex = existing.get(nom, {})
            rows_data.append({
                'role': ex.get('role', 'Équipe projet'),
                'nom': nom,
                'fonction': ex.get('fonction', ''),
                'email': ex.get('email', ''),
                'tel': ex.get('tel', ''),
            })

        t.setRowCount(0)
        for rd in rows_data:
            r = t.rowCount(); t.insertRow(r)
            t.setItem(r, 0, QTableWidgetItem(rd['role']))
            nom_item = QTableWidgetItem(rd['nom'])
            nom_item.setFlags(nom_item.flags() & ~Qt.ItemIsEditable)
            t.setItem(r, 1, nom_item)
            t.setItem(r, 2, QTableWidgetItem(rd['fonction']))
            t.setItem(r, 3, QTableWidgetItem(rd['email']))
            t.setItem(r, 4, QTableWidgetItem(rd['tel']))

    def _add_acteur_row(self):
        r = self.acteurs_table.rowCount()
        self.acteurs_table.insertRow(r)
        for c in range(5):
            self.acteurs_table.setItem(r, c, QTableWidgetItem(''))

    def _del_acteur_row(self):
        row = self.acteurs_table.currentRow()
        if row >= 0:
            self.acteurs_table.removeRow(row)

    def _get_acteurs_data(self):
        """Retourne la liste des acteurs depuis le tableau pour la fiche Word."""
        acteurs = []
        t = self.acteurs_table
        for r in range(t.rowCount()):
            role  = t.item(r, 0).text().strip() if t.item(r, 0) else ''
            nom   = t.item(r, 1).text().strip() if t.item(r, 1) else ''
            fn    = t.item(r, 2).text().strip() if t.item(r, 2) else ''
            email = t.item(r, 3).text().strip() if t.item(r, 3) else ''
            tel   = t.item(r, 4).text().strip() if t.item(r, 4) else ''
            if nom or role:
                acteurs.append({'role': role, 'nom': nom,
                                'fonction': fn, 'email': email or tel})
        return acteurs

    def create_couts_tab(self):
        """Onglet Coûts & Charges — tableau MOE/MOA/Licences/Matériels."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl = QLabel(
            "Renseignez les couts et charges par categorie et par phase. "
            "Ces donnees alimentent le tableau Couts & Charges de la fiche Word.")
        lbl.setStyleSheet("color:#7f8c8d; font-style:italic; padding:4px;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        # Tableau des coûts : Catégorie | Définition projet | Mise en œuvre | Total €
        self.couts_table = QTableWidget(0, 4)
        self.couts_table.setHorizontalHeaderLabels(
            ["Catégorie", "Définition projet (€)", "Mise en œuvre (€)", "Total €"])
        hdr = self.couts_table.horizontalHeader()
        hdr.setSectionResizeMode(0, hdr.Stretch)
        hdr.setSectionResizeMode(1, hdr.ResizeToContents)
        hdr.setSectionResizeMode(2, hdr.ResizeToContents)
        hdr.setSectionResizeMode(3, hdr.ResizeToContents)
        self.couts_table.setAlternatingRowColors(True)
        self.couts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.couts_table)

        # Lignes par défaut
        self._init_couts_table()
        # Calcul automatique du total à chaque changement
        self.couts_table.itemChanged.connect(self._update_couts_total)

        # Zone modalités de financement
        layout.addWidget(QLabel("Modalités de financement (internes / externes) :"))
        self.financement_edit = QTextEdit()
        self.financement_edit.setPlaceholderText(
            "Décrivez les sources de financement, subventions, dates de disponibilité...")
        self.financement_edit.setMaximumHeight(80)
        layout.addWidget(self.financement_edit)

        return widget

    def _init_couts_table(self):
        """Remplit le tableau Coûts avec les catégories standards."""
        cats = [
            "MOE interne",
            "MOA interne",
            "Licences / Logiciels",
            "Matériels / Serveurs",
            "Sous-traitance",
            "Autres",
        ]
        self.couts_table.blockSignals(True)
        self.couts_table.setRowCount(0)
        for cat in cats:
            r = self.couts_table.rowCount()
            self.couts_table.insertRow(r)
            cat_item = QTableWidgetItem(cat)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
            cat_item.setBackground(Qt.lightGray)
            self.couts_table.setItem(r, 0, cat_item)
            self.couts_table.setItem(r, 1, QTableWidgetItem("0"))
            self.couts_table.setItem(r, 2, QTableWidgetItem("0"))
            # Total calculé auto
            tot_item = QTableWidgetItem("0")
            tot_item.setFlags(tot_item.flags() & ~Qt.ItemIsEditable)
            self.couts_table.setItem(r, 3, tot_item)
        self.couts_table.blockSignals(False)

    def _update_couts_total(self, item):
        """Recalcule le total de la ligne modifiée."""
        if item.column() not in (1, 2):
            return
        r = item.row()
        self.couts_table.blockSignals(True)
        try:
            v1 = float(self.couts_table.item(r, 1).text().replace(',', '.') or 0)
        except Exception:
            v1 = 0
        try:
            v2 = float(self.couts_table.item(r, 2).text().replace(',', '.') or 0)
        except Exception:
            v2 = 0
        total_item = self.couts_table.item(r, 3)
        if total_item:
            total_item.setText(f"{v1 + v2:,.2f}")
        self.couts_table.blockSignals(False)

    def _get_couts_data(self):
        """Retourne les coûts pour la fiche Word."""
        couts = {}
        for r in range(self.couts_table.rowCount()):
            cat = self.couts_table.item(r, 0).text() if self.couts_table.item(r, 0) else ''
            try: def_ = float(self.couts_table.item(r, 1).text().replace(',', '.') or 0)
            except: def_ = 0
            try: meo  = float(self.couts_table.item(r, 2).text().replace(',', '.') or 0)
            except: meo = 0
            if cat:
                couts[cat] = {'definition': def_, 'mise_en_oeuvre': meo, 'total': def_ + meo}
        return couts

    def create_contacts_tab(self):
        """Crée l'onglet Contacts."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Table des contacts
        self.contacts_table = QTableWidget(0, 5)
        self.contacts_table.setHorizontalHeaderLabels(["ID", "Contact", "Type", "Fonction", "Rôle"])
        self.contacts_table.setColumnHidden(0, True)
        self.contacts_table.horizontalHeader().setStretchLastSection(True)
        self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.contacts_table)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_add_contact = QPushButton("➕ Ajouter")
        btn_add_contact.clicked.connect(self.add_contact)
        btn_modify_role = QPushButton("✏️ Modifier rôle")
        btn_modify_role.clicked.connect(self.modify_contact_role)
        btn_remove_contact = QPushButton("➖ Retirer")
        btn_remove_contact.clicked.connect(self.remove_contact)
        btn_layout.addWidget(btn_add_contact)
        btn_layout.addWidget(btn_modify_role)
        btn_layout.addWidget(btn_remove_contact)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_documents_tab(self):
        """Crée l'onglet Documents."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Table des documents
        self.documents_table = QTableWidget(0, 5)
        self.documents_table.setHorizontalHeaderLabels(["ID", "Type", "Nom fichier", "Date", "Taille"])
        self.documents_table.setColumnHidden(0, True)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.documents_table)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_add_doc = QPushButton("➕ Ajouter")
        btn_add_doc.clicked.connect(self.add_document)
        btn_download_doc = QPushButton("⬇️ Télécharger")
        btn_download_doc.clicked.connect(self.download_document)
        btn_remove_doc = QPushButton("🗑️ Supprimer")
        btn_remove_doc.clicked.connect(self.remove_document)
        btn_layout.addWidget(btn_add_doc)
        btn_layout.addWidget(btn_download_doc)
        btn_layout.addWidget(btn_remove_doc)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_taches_tab(self):
        """Crée l'onglet Tâches."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # KPI Tâches
        kpi_layout = QHBoxLayout()
        self.total_taches_label = QLabel("Total: 0")
        self.taches_terminees_label = QLabel("Terminées: 0")
        self.taches_en_cours_label = QLabel("En cours: 0")
        kpi_layout.addWidget(self.total_taches_label)
        kpi_layout.addWidget(self.taches_terminees_label)
        kpi_layout.addWidget(self.taches_en_cours_label)
        kpi_layout.addStretch()
        layout.addLayout(kpi_layout)
        
        # Table des tâches (lecture seule)
        self.taches_table = QTableWidget(0, 6)
        self.taches_table.setHorizontalHeaderLabels(["ID", "Titre", "Statut", "Priorité", "Échéance", "Avancement %"])
        self.taches_table.setColumnHidden(0, True)
        self.taches_table.horizontalHeader().setStretchLastSection(True)
        self.taches_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.taches_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.taches_table)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_create_tache = QPushButton("➕ Créer tâche")
        btn_create_tache.setStyleSheet("background:#27ae60;color:white;font-weight:bold;padding:6px 12px;")
        btn_create_tache.clicked.connect(self.create_tache)
        btn_layout.addWidget(btn_create_tache)

        btn_new_bc = QPushButton("🛒 Nouveau BC lié au projet")
        btn_new_bc.setStyleSheet("background:#8e44ad;color:white;font-weight:bold;padding:6px 12px;")
        btn_new_bc.clicked.connect(self.create_bc_projet)
        btn_layout.addWidget(btn_new_bc)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def load_projet_data(self):
        """Charge les données du projet."""
        try:
            if not self.projet:
                return
            
            # Onglet Général
            self.code_edit.setText(safe_get(self.projet, 'code', '') or '')
            self.nom_edit.setText(safe_get(self.projet, 'nom', '') or '')
            self.description_edit.setPlainText(safe_get(self.projet, 'description', '') or '')
            
            if safe_get(self.projet, 'type_projet'):
                index = self.type_combo.findText(safe_get(self.projet, 'type_projet'))
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'phase'):
                index = self.phase_combo.findText(safe_get(self.projet, 'phase'))
                if index >= 0:
                    self.phase_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'priorite'):
                index = self.priorite_combo.findText(safe_get(self.projet, 'priorite'))
                if index >= 0:
                    self.priorite_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'statut'):
                index = self.statut_combo.findText(safe_get(self.projet, 'statut'))
                if index >= 0:
                    self.statut_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'date_debut'):
                self.date_debut.setDate(QDate.fromString(safe_get(self.projet, 'date_debut'), "yyyy-MM-dd"))
            
            if safe_get(self.projet, 'date_fin_prevue'):
                self.date_fin.setDate(QDate.fromString(safe_get(self.projet, 'date_fin_prevue'), "yyyy-MM-dd"))
            
            if safe_get(self.projet, 'date_fin_reelle'):
                self.date_fin_reelle.setDate(QDate.fromString(safe_get(self.projet, 'date_fin_reelle')[:10], "yyyy-MM-dd"))
                self.chk_termine.setChecked(True)
                self.date_fin_reelle.setEnabled(True)
            elif safe_get(self.projet, 'statut') == 'TERMINE':
                # Projet marque TERMINE sans date reelle -> cocher quand meme
                self.chk_termine.setChecked(True)
                self.date_fin_reelle.setEnabled(True)
                self.avancement_spin.setValue(100)
            
            self.avancement_spin.setValue(safe_get(self.projet, 'avancement', 0) or 0)
            
            # Service bénéficiaire
            if safe_get(self.projet, 'service_id'):
                for i in range(self.service_combo.count()):
                    if self.service_combo.itemData(i) == safe_get(self.projet, 'service_id'):
                        self.service_combo.setCurrentIndex(i)
                        break
            
            # Onglet Opportunite — champs contexte
            self.objectifs_edit.setPlainText(safe_get(self.projet, 'objectifs', '') or '')
            self.enjeux_edit.setPlainText(safe_get(self.projet, 'enjeux', '') or '')
            self.risques_edit.setPlainText(safe_get(self.projet, 'risques', '') or '')
            self.gains_edit.setPlainText(safe_get(self.projet, 'gains', '') or '')
            self.contraintes_edit.setPlainText(safe_get(self.projet, 'contraintes', '') or '')
            self.solutions_edit.setPlainText(safe_get(self.projet, 'solutions', '') or '')

            # Registre des risques (JSON)
            self._load_risques_data(safe_get(self.projet, 'registre_risques'))

            # 6 contraintes
            import json
            ctr_json = safe_get(self.projet, 'contraintes_6axes')
            if ctr_json:
                try:
                    ctr_data = json.loads(ctr_json) if isinstance(ctr_json, str) else ctr_json
                    for attr, edit in self._contraintes_edits.items():
                        edit.setPlainText(ctr_data.get(attr, ''))
                except Exception:
                    pass

            # Triangle d or
            tri_json = safe_get(self.projet, 'triangle_tensions')
            if tri_json:
                try:
                    tri_data = json.loads(tri_json) if isinstance(tri_json, str) else tri_json
                    for attr, (spin, bar) in self._tension_spins.items():
                        spin.setValue(int(tri_data.get(attr, 3)))
                except Exception:
                    pass

            # Arbitrage
            self.arbitrage_edit.setPlainText(safe_get(self.projet, 'arbitrage', '') or '')

            # Onglet Budget
            self.budget_initial_spin.setValue(float(safe_get(self.projet, 'budget_initial', 0) or 0))
            self.budget_estime_spin.setValue(float(safe_get(self.projet, 'budget_estime', 0) or 0))
            self.budget_actuel_spin.setValue(float(safe_get(self.projet, 'budget_actuel', 0) or 0))
            budget_consomme = float(safe_get(self.projet, 'budget_consomme', 0) or 0)
            self.budget_consomme_label.setText(f"{budget_consomme:,.2f} €")
            
            # Ligne budgétaire V5
            ligne_id = safe_get(self.projet, 'ligne_budgetaire_id')
            if ligne_id:
                for i in range(self.ligne_budg_combo.count()):
                    if self.ligne_budg_combo.itemData(i) == ligne_id:
                        self.ligne_budg_combo.setCurrentIndex(i)
                        break

            # Récapitulatif BC liés
            try:
                bcs = db_service.fetch_all(
                    "SELECT numero_bc, objet, montant_ttc, statut FROM bons_commande "
                    "WHERE projet_id=? ORDER BY date_creation DESC LIMIT 5",
                    (self.projet_id,))
                if bcs:
                    total = sum(float(b.get('montant_ttc') or 0) for b in bcs)
                    lines = [f"• {b.get('numero_bc','')} — {b.get('objet','')[:30]} ({b.get('statut','')})" for b in bcs]
                    lines.append(f"Total : {total:,.2f} €")
                    self.bc_recap_label.setText("\n".join(lines))
                    self.bc_recap_label.setStyleSheet("color:#2ecc71;")
                else:
                    self.bc_recap_label.setText("Aucun BC lié")
            except Exception:
                pass
            
            # Onglet Équipe
            if safe_get(self.projet, 'responsable_id'):
                target = f"USR_{safe_get(self.projet, 'responsable_id')}"
                for i in range(self.responsable_combo.count()):
                    if self.responsable_combo.itemData(i) == target:
                        self.responsable_combo.setCurrentIndex(i)
                        break

            if safe_get(self.projet, 'chef_projet_id'):
                target = f"USR_{safe_get(self.projet, 'chef_projet_id')}"
                for i in range(self.chef_projet_combo.count()):
                    if self.chef_projet_combo.itemData(i) == target:
                        self.chef_projet_combo.setCurrentIndex(i)
                        break
            
            # Charger équipe depuis projet_membres
            self.equipe_list.clear()
            conn = db_service.get_connection()
            try:
                membres = conn.execute(
                    "SELECT * FROM projet_membres WHERE projet_id=? ORDER BY id",
                    (self.projet_id,)
                ).fetchall()
                for m in membres:
                    m = dict(m)
                    label = m.get('label') or ''
                    uid = m.get('utilisateur_id')
                    cid = m.get('contact_id')
                    if uid:
                        val = f"USR_{uid}"
                        if not label:
                            u = conn.execute(
                                "SELECT nom, prenom, fonction FROM utilisateurs WHERE id=?",
                                (uid,)).fetchone()
                            label = f"👤 {u['nom']} {u['prenom'] or ''}" if u else f"👤 #{uid}"
                    elif cid:
                        val = f"CTT_{cid}"
                        if not label:
                            c = conn.execute(
                                "SELECT nom, prenom, fonction FROM contacts WHERE id=?",
                                (cid,)).fetchone()
                            label = f"📇 {c['nom']} {c['prenom'] or ''}" if c else f"📇 #{cid}"
                    else:
                        continue
                    item = QListWidgetItem(label)
                    item.setData(Qt.UserRole, val)
                    self.equipe_list.addItem(item)
                logger.info(f"load_equipe : {self.equipe_list.count()} membre(s) chargé(s)")
            except Exception as e:
                logger.error(f"load_equipe : {e}")

            # Recharger l'onglet Acteurs détail
            try:
                self._refresh_acteurs_table()
            except Exception as e:
                logger.error(f"_refresh_acteurs_table: {e}")
            
            # Reconstruire la liste prestataires depuis la DB
            self.prestataires_list.clear()
            prestataires = db_service.fetch_all("""
                SELECT pp.fournisseur_id, f.nom
                FROM projet_prestataires pp
                JOIN fournisseurs f ON f.id = pp.fournisseur_id
                WHERE pp.projet_id = ?
                ORDER BY f.nom
            """, (self.projet_id,)) or []
            for p in prestataires:
                p = dict(p)
                item = QListWidgetItem(p.get('nom',''))
                item.setData(Qt.UserRole, p['fournisseur_id'])
                self.prestataires_list.addItem(item)
            
            # Charger contacts
            self.load_contacts()
            
            # Charger documents
            self.load_documents()
            
            # Charger tâches
            self.load_taches()
        
        except Exception as e:
            logger.error(f"Erreur chargement projet: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger le projet:\n{e}")
    
    def _on_termine_toggled(self, checked):
        """Synchronise statut combo + avancement quand on coche/decoche Projet termine."""
        if checked:
            idx = self.statut_combo.findText('TERMINE')
            if idx >= 0:
                self.statut_combo.setCurrentIndex(idx)
            self.avancement_spin.setValue(100)
        else:
            # Si on decoche, repasser a ACTIF seulement si le statut etait TERMINE
            if self.statut_combo.currentText() == 'TERMINE':
                idx = self.statut_combo.findText('ACTIF')
                if idx >= 0:
                    self.statut_combo.setCurrentIndex(idx)

    def _exporter_fiche(self):
        """Génère et ouvre la fiche projet Word."""
        import os, sys
        from pathlib import Path
        try:
            from app.services.fiche_projet_service import generer_fiche_depuis_id
            # Si nouveau projet non encore sauvegardé, avertir
            if not self.projet_id:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "Info",
                    "Enregistrez d'abord le projet avant de générer la fiche.")
                return
            # Dossier de sortie = racine de l'appli
            out_dir = str(Path(__file__).parent.parent.parent)
            # Récupérer les données saisies dans les onglets Acteurs et Coûts
            try:
                extra = {
                    'contacts_detail': self._get_acteurs_data(),
                    'couts_detail':    self._get_couts_data(),
                    'financement':     self.financement_edit.toPlainText().strip(),
                }
            except Exception:
                extra = {}
            path = generer_fiche_depuis_id(self.projet_id, out_dir, extra=extra)
            # Ouvrir avec Word / LibreOffice
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "✅ Fiche générée",
                f"Fiche enregistrée :\n{path}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur génération fiche: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Erreur", f"Impossible de générer la fiche :\n{e}")

    def accept_dialog(self):
        """Valide et enregistre le projet."""
        try:
            # Validation
            if not self.nom_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le nom du projet est obligatoire.")
                self.tabs.setCurrentIndex(0)
                self.nom_edit.setFocus()
                return
            
            # Vérifier que date fin > date début
            if self.date_fin.date() < self.date_debut.date():
                QMessageBox.warning(
                    self, "Validation", 
                    "La date de fin doit être postérieure à la date de début."
                )
                self.tabs.setCurrentIndex(0)
                return
            
            # Préparer les données
            data = {
                'code': self.code_edit.text().strip() or None,
                'nom': self.nom_edit.text().strip(),
                'description': self.description_edit.toPlainText().strip() or None,
                'type_projet': self.type_combo.currentText(),
                'phase': self.phase_combo.currentText(),
                'priorite': self.priorite_combo.currentText(),
                'statut': self.statut_combo.currentText(),
                'date_debut': self.date_debut.date().toString("yyyy-MM-dd"),
                'date_fin_prevue': self.date_fin.date().toString("yyyy-MM-dd"),
                'avancement': self.avancement_spin.value(),
                # Onglet Opportunité
                'objectifs':   self.objectifs_edit.toPlainText().strip() or None,
                'enjeux':      self.enjeux_edit.toPlainText().strip() or None,
                'risques':     self.risques_edit.toPlainText().strip() or None,
                'gains':       self.gains_edit.toPlainText().strip() or None,
                'contraintes': self.contraintes_edit.toPlainText().strip() or None,
                'solutions':   self.solutions_edit.toPlainText().strip() or None,
                'registre_risques':  __import__('json').dumps(
                    self._get_risques_data(), ensure_ascii=False),
                'contraintes_6axes': __import__('json').dumps(
                    self._get_contraintes_data(), ensure_ascii=False),
                'triangle_tensions': __import__('json').dumps(
                    self._get_triangle_data(), ensure_ascii=False),
                'arbitrage':   self.arbitrage_edit.toPlainText().strip() or None,
                'budget_initial': self.budget_initial_spin.value(),
                'budget_estime': self.budget_estime_spin.value(),
                'budget_actuel': self.budget_actuel_spin.value(),
            }
            
            # Date fin reelle + statut + avancement si termine
            if self.chk_termine.isChecked():
                data['date_fin_reelle'] = self.date_fin_reelle.date().toString("yyyy-MM-dd")
                data['statut']          = 'TERMINE'
                data['avancement']      = 100
                # Mettre a jour le combo statut pour coherence visuelle
                idx = self.statut_combo.findText('TERMINE')
                if idx >= 0:
                    self.statut_combo.setCurrentIndex(idx)
                self.avancement_spin.setValue(100)
            else:
                data['date_fin_reelle'] = None
                # Si le statut etait TERMINE et qu on decoche, repasser en ACTIF
                if data.get('statut') == 'TERMINE':
                    data['statut'] = 'ACTIF' 
            
            # AP
            # Ligne budgétaire V5
            lb = self.ligne_budg_combo.currentData()
            if lb:
                data['ligne_budgetaire_id'] = lb
            
            # Équipe
            responsable_val = self.responsable_combo.currentData()
            if responsable_val and responsable_val not in (None, '__sep__'):
                if str(responsable_val).startswith('USR_'):
                    data['responsable_id'] = int(str(responsable_val)[4:])
                # Si contact, on ignore (pas de colonne dédiée) — futur: ALTER TABLE
            
            chef_val = self.chef_projet_combo.currentData()
            if chef_val and chef_val not in (None, '__sep__'):
                if str(chef_val).startswith('USR_'):
                    data['chef_projet_id'] = int(str(chef_val)[4:])
                # Si contact, on ignore pour l'instant (colonne à ajouter via ALTER TABLE)
            
            # Service bénéficiaire
            service_id = self.service_combo.currentData()
            if service_id:
                data['service_id'] = service_id
            
            # Sauvegarder
            if self.projet_id:
                projet_service.update(self.projet_id, data)
                logger.info(f"Projet {self.projet_id} mis à jour")
            else:
                self.projet_id = projet_service.create(data)
                logger.info(f"Projet créé: {self.projet_id}")
            
            # Sauvegarder équipe DSI
            self.save_equipe()
            
            # Sauvegarder prestataires
            self.save_prestataires()
            
            self.accept()
        
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            logger.error(f"Erreur sauvegarde projet: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le projet:\n{e}")
    

    def _charger_personnes(self, combo):
        """Charge contacts + utilisateurs internes dans un combo (contacts en priorité)."""
        combo.clear()
        combo.addItem("-- Aucun --", None)
        try:
            # Contacts en priorité (table la plus remplie)
            contacts = db_service.fetch_all(
                "SELECT id, nom, prenom, fonction, organisation FROM contacts ORDER BY nom, prenom"
            ) or []
            contacts = [dict(c) for c in contacts]
            logger.info(f"_charger_personnes : {len(contacts)} contact(s) trouvé(s)")
            if contacts:
                combo.addItem("── Contacts ──", "__sep__")
                combo.model().item(combo.count() - 1).setEnabled(False)
            for c in contacts:
                nom_complet = f"{c.get('nom','') or ''} {c.get('prenom','') or ''}".strip()
                detail = []
                if c.get('fonction'):
                    detail.append(c['fonction'])
                if c.get('organisation'):
                    detail.append(c['organisation'])
                label = nom_complet + (f" — {', '.join(detail)}" if detail else "")
                combo.addItem(label, f"CTT_{c['id']}")
        except Exception as e:
            logger.error(f"Chargement contacts : {e}")
        try:
            # Agents DSI internes
            users = db_service.fetch_all(
                "SELECT id, nom, prenom, fonction FROM utilisateurs WHERE actif=1 ORDER BY nom, prenom"
            ) or []
            users = [dict(u) for u in users]
            if users:
                combo.addItem("── Agents DSI ──", "__sep__")
                combo.model().item(combo.count() - 1).setEnabled(False)
            for u in users:
                label = f"{u.get('nom','') or ''} {u.get('prenom','') or ''}".strip()
                if u.get('fonction'):
                    label += f" ({u['fonction']})"
                combo.addItem(label, f"USR_{u['id']}")
        except Exception as e:
            logger.error(f"Chargement utilisateurs : {e}")

    def _charger_personnes_list(self, list_widget):
        """Charge utilisateurs + contacts dans un QListWidget."""
        list_widget.clear()
        try:
            users = db_service.fetch_all(
                "SELECT id, nom, prenom, fonction FROM utilisateurs WHERE actif=1 ORDER BY nom, prenom"
            ) or []
            users = [dict(u) for u in users]
            for u in users:
                label = f"👤 {u['nom']} {u.get('prenom','') or ''}"
                if u.get('fonction'):
                    label += f" ({u['fonction']})"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, f"USR_{u['id']}")
                list_widget.addItem(item)
        except Exception as e:
            logger.error(f"Chargement utilisateurs list : {e}")
        try:
            contacts = db_service.fetch_all(
                "SELECT id, nom, prenom, fonction, organisation FROM contacts ORDER BY nom, prenom"
            ) or []
            contacts = [dict(c) for c in contacts]
            for c in contacts:
                nom = f"{c.get('nom','')} {c.get('prenom','') or ''}".strip()
                org = c.get('organisation') or c.get('fonction') or ''
                label = f"📇 {nom}" + (f" — {org}" if org else "")
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, f"CTT_{c['id']}")
                list_widget.addItem(item)
        except Exception as e:
            logger.error(f"Chargement contacts list : {e}")


    def _ajouter_prestataire(self):
        """Ajoute le fournisseur sélectionné dans la liste prestataires."""
        fourn_id  = self.prestataire_search.currentData()
        label     = self.prestataire_search.currentText().strip()
        if not fourn_id or not label or label == '-- Choisir --':
            return
        # Vérifier doublon
        for i in range(self.prestataires_list.count()):
            if self.prestataires_list.item(i).data(Qt.UserRole) == fourn_id:
                return
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, fourn_id)
        self.prestataires_list.addItem(item)
        self.prestataire_search.setCurrentIndex(0)

    def _ajouter_membre_equipe(self):
        """Ajoute le contact/agent sélectionné dans la liste équipe."""
        val   = self.equipe_search.currentData()
        label = self.equipe_search.currentText().strip()
        if not val or val == '__sep__' or not label or label == '-- Aucun --':
            return
        # Vérifier doublon
        for i in range(self.equipe_list.count()):
            if self.equipe_list.item(i).data(Qt.UserRole) == val:
                return
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, val)
        self.equipe_list.addItem(item)
        # Remettre le combo sur "-- Aucun --"
        self.equipe_search.setCurrentIndex(0)

    def _ajouter_agent(self, combo):
        """Ouvre un mini-dialog pour créer un agent DSI interne."""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("➕ Nouvel agent DSI")
        dlg.setMinimumWidth(340)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        nom_e    = QLineEdit(); nom_e.setPlaceholderText("NOM")
        prenom_e = QLineEdit(); prenom_e.setPlaceholderText("Prénom")
        fonc_e   = QLineEdit(); fonc_e.setPlaceholderText("ex: Chef de projet, Architecte...")
        email_e  = QLineEdit(); email_e.setPlaceholderText("prenom.nom@larochelle.fr")
        form.addRow("Nom *:",      nom_e)
        form.addRow("Prénom:",     prenom_e)
        form.addRow("Fonction:",   fonc_e)
        form.addRow("Email:",      email_e)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec_() != QDialog.Accepted:
            return
        nom = nom_e.text().strip().upper()
        if not nom:
            return
        try:
            conn = db_service.get_connection()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO utilisateurs (nom, prenom, fonction, email, actif, date_creation)"
                " VALUES (?,?,?,?,1,datetime('now'))",
                (nom, prenom_e.text().strip(), fonc_e.text().strip(), email_e.text().strip()))
            conn.commit()
            new_id = cur.lastrowid
            label  = f"{nom} {prenom_e.text().strip()}"
            if fonc_e.text().strip():
                label += f" ({fonc_e.text().strip()})"
            combo.addItem(label, f"USR_{new_id}")
            combo.setCurrentIndex(combo.count() - 1)
            # Ne PAS recharger equipe_list — l'utilisateur ajoute manuellement via ➕ Ajouter
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Erreur", str(e))

    def get_data(self):
        """Retourne les données du formulaire (pour compatibilité)."""
        return {
            'id': self.projet_id,
            'code': self.code_edit.text().strip(),
            'nom': self.nom_edit.text().strip(),
        }
    
    def save_equipe(self):
        """Sauvegarde l'équipe projet dans projet_membres."""
        try:
            conn = db_service.get_connection()

            # Créer la table si elle n'existe pas encore
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projet_membres (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    projet_id    INTEGER NOT NULL,
                    utilisateur_id INTEGER,
                    contact_id   INTEGER,
                    label        TEXT,
                    date_creation TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "DELETE FROM projet_membres WHERE projet_id=?",
                (self.projet_id,)
            )

            inseres = 0
            for i in range(self.equipe_list.count()):
                item = self.equipe_list.item(i)
                if not item: continue
                val   = str(item.data(Qt.UserRole) or '')
                label = item.text()
                if val.startswith('USR_'):
                    conn.execute(
                        "INSERT INTO projet_membres (projet_id, utilisateur_id, label) VALUES (?,?,?)",
                        (self.projet_id, int(val[4:]), label)
                    )
                    inseres += 1
                elif val.startswith('CTT_'):
                    conn.execute(
                        "INSERT INTO projet_membres (projet_id, contact_id, label) VALUES (?,?,?)",
                        (self.projet_id, int(val[4:]), label)
                    )
                    inseres += 1

            conn.commit()
            logger.info(f"save_equipe : {inseres} membre(s) sauvegardé(s)")

        except Exception as e:
            logger.error(f"Erreur save_equipe : {e}", exc_info=True)
    
    def save_prestataires(self):
        """Sauvegarde les prestataires."""
        try:
            # Supprimer les associations existantes
            db_service.execute(
                "DELETE FROM projet_prestataires WHERE projet_id = ?",
                (self.projet_id,)
            )
            
            # Sauver tous les prestataires de la liste
            for i in range(self.prestataires_list.count()):
                item = self.prestataires_list.item(i)
                if not item: continue
                fournisseur_id = item.data(Qt.UserRole)
                if not fournisseur_id: continue
                db_service.execute(
                    "INSERT OR IGNORE INTO projet_prestataires (projet_id, fournisseur_id) VALUES (?, ?)",
                    (self.projet_id, fournisseur_id)
                )
        except Exception as e:
            logger.error(f"Erreur sauvegarde prestataires: {e}")
    
    def load_contacts(self):
        """Charge les contacts du projet."""
        try:
            self.contacts_table.setRowCount(0)
            contacts = db_service.fetch_all("""
                SELECT pc.id, c.id as contact_id, c.nom, c.prenom, c.type, c.fonction, pc.role
                FROM projet_contacts pc
                JOIN contacts c ON pc.contact_id = c.id
                WHERE pc.projet_id = ?
                ORDER BY pc.role, c.nom
            """, (self.projet_id,))
            
            for contact in contacts:
                row = self.contacts_table.rowCount()
                self.contacts_table.insertRow(row)
                self.contacts_table.setItem(row, 0, QTableWidgetItem(str(contact['id'])))
                self.contacts_table.setItem(row, 1, QTableWidgetItem(f"{contact['nom']} {contact['prenom']}"))
                self.contacts_table.setItem(row, 2, QTableWidgetItem(contact['type'] or ''))
                self.contacts_table.setItem(row, 3, QTableWidgetItem(contact['fonction'] or ''))
                self.contacts_table.setItem(row, 4, QTableWidgetItem(contact['role'] or ''))
        except Exception as e:
            logger.error(f"Erreur chargement contacts: {e}")
    
    def load_documents(self):
        """Charge les documents du projet."""
        try:
            self.documents_table.setRowCount(0)
            documents = db_service.fetch_all("""
                SELECT id, type_document, nom_fichier, date_ajout, taille
                FROM projet_documents
                WHERE projet_id = ?
                ORDER BY date_ajout DESC
            """, (self.projet_id,))
            
            for doc in documents:
                row = self.documents_table.rowCount()
                self.documents_table.insertRow(row)
                self.documents_table.setItem(row, 0, QTableWidgetItem(str(doc['id'])))
                self.documents_table.setItem(row, 1, QTableWidgetItem(doc['type_document'] or ''))
                self.documents_table.setItem(row, 2, QTableWidgetItem(doc['nom_fichier'] or ''))
                date_str = doc['date_ajout'][:10] if doc['date_ajout'] else ''
                self.documents_table.setItem(row, 3, QTableWidgetItem(date_str))
                taille = doc['taille'] or 0
                taille_str = f"{taille / 1024:.1f} Ko" if taille < 1024*1024 else f"{taille / (1024*1024):.1f} Mo"
                self.documents_table.setItem(row, 4, QTableWidgetItem(taille_str))
        except Exception as e:
            logger.error(f"Erreur chargement documents: {e}")
    
    def load_taches(self):
        """Charge les tâches du projet."""
        try:
            self.taches_table.setRowCount(0)
            taches = db_service.fetch_all("""
                SELECT id, titre, statut, priorite, date_echeance, avancement
                FROM taches
                WHERE projet_id = ?
                ORDER BY date_echeance, priorite
            """, (self.projet_id,))
            
            # KPI
            total = len(taches)
            terminees = sum(1 for t in taches if t['statut'] == 'TERMINE')
            en_cours = sum(1 for t in taches if t['statut'] == 'EN_COURS')
            
            self.total_taches_label.setText(f"Total: {total}")
            self.taches_terminees_label.setText(f"Terminées: {terminees}")
            self.taches_en_cours_label.setText(f"En cours: {en_cours}")
            
            for tache in taches:
                row = self.taches_table.rowCount()
                self.taches_table.insertRow(row)
                self.taches_table.setItem(row, 0, QTableWidgetItem(str(tache['id'])))
                self.taches_table.setItem(row, 1, QTableWidgetItem(tache['titre'] or ''))
                self.taches_table.setItem(row, 2, QTableWidgetItem(tache['statut'] or ''))
                self.taches_table.setItem(row, 3, QTableWidgetItem(tache['priorite'] or ''))
                echeance = tache['date_echeance'] or ''
                self.taches_table.setItem(row, 4, QTableWidgetItem(echeance))
                self.taches_table.setItem(row, 5, QTableWidgetItem(f"{tache['avancement'] or 0}%"))
        except Exception as e:
            logger.error(f"Erreur chargement tâches: {e}")
    
    def add_contact(self):
        """Ajoute un contact au projet — dialog avec combo recherchable."""
        try:
            if not self.projet_id:
                QMessageBox.warning(self, "Attention", "Veuillez d'abord enregistrer le projet.")
                return

            # Récupérer TOUS les contacts sans filtre
            contacts = db_service.fetch_all("""
                SELECT id, nom, prenom, type, fonction, organisation
                FROM contacts
                ORDER BY type, nom, prenom
            """) or []
            contacts = [dict(c) for c in contacts]

            if not contacts:
                QMessageBox.information(self, "Info", "Aucun contact disponible.\nAjoutez des contacts dans l'onglet Contacts.")
                return

            # Dialog de sélection
            dlg = QDialog(self)
            dlg.setWindowTitle("Ajouter un contact au projet")
            dlg.setMinimumWidth(480)
            layout = QVBoxLayout(dlg)

            # Recherche
            search = QLineEdit()
            search.setPlaceholderText("Rechercher un contact...")
            layout.addWidget(search)

            # Combo contacts groupés par type
            combo = QComboBox()
            combo.setEditable(False)

            def populate_combo(filtre=""):
                combo.clear()
                combo.addItem("-- Choisir un contact --", None)
                type_courant = None
                for c in contacts:
                    nom = f"{c.get('nom','') or ''} {c.get('prenom','') or ''}".strip()
                    type_c = c.get('type') or 'Autre'
                    detail = c.get('fonction') or c.get('organisation') or ''
                    label = f"{nom}" + (f" — {detail}" if detail else "")
                    if filtre and filtre.lower() not in label.lower() and filtre.lower() not in type_c.lower():
                        continue
                    if type_c != type_courant:
                        combo.addItem(f"── {type_c} ──", "__sep__")
                        combo.model().item(combo.count()-1).setEnabled(False)
                        type_courant = type_c
                    combo.addItem(label, c['id'])

            populate_combo()
            search.textChanged.connect(populate_combo)
            layout.addWidget(combo)

            # Rôle
            form = QFormLayout()
            role_combo = QComboBox()
            role_combo.addItems(["REFERENT", "SPONSOR", "VALIDEUR", "INFORME", "AUTRE"])
            form.addRow("Rôle dans le projet:", role_combo)
            layout.addLayout(form)

            # Bouton créer nouveau contact
            btn_new_contact = QPushButton("➕ Créer un nouveau contact")
            btn_new_contact.setStyleSheet(
                "background-color: #27ae60; color: white; font-weight: bold; padding: 6px 12px;")

            def ouvrir_creation_contact():
                from app.ui.dialogs.contact_dialog import ContactDialog
                dlg_contact = ContactDialog(dlg)
                if dlg_contact.exec_() == QDialog.Accepted:
                    new_id = dlg_contact.contact_id
                    if new_id:
                        # Recharger la liste des contacts
                        contacts.clear()
                        nouveaux = db_service.fetch_all("""
                            SELECT id, nom, prenom, type, fonction, organisation
                            FROM contacts ORDER BY type, nom, prenom
                        """) or []
                        contacts.extend([dict(c) for c in nouveaux])
                        populate_combo(search.text())
                        # Sélectionner automatiquement le nouveau contact
                        for i in range(combo.count()):
                            if combo.itemData(i) == new_id:
                                combo.setCurrentIndex(i)
                                break

            btn_new_contact.clicked.connect(ouvrir_creation_contact)
            layout.addWidget(btn_new_contact)

            # Boutons OK/Annuler
            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            layout.addWidget(btns)

            if dlg.exec_() != QDialog.Accepted:
                return

            contact_id = combo.currentData()
            if not contact_id or contact_id == "__sep__":
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un contact.")
                return

            role = role_combo.currentText()
            db_service.execute("""
                INSERT OR IGNORE INTO projet_contacts (projet_id, contact_id, role)
                VALUES (?, ?, ?)
            """, (self.projet_id, contact_id, role))
            self.load_contacts()

        except Exception as e:
            logger.error(f"Erreur ajout contact: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le contact:\n{e}")
    
    def modify_contact_role(self):
        """Modifie le rôle d'un contact."""
        try:
            current_row = self.contacts_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un contact.")
                return
            
            pc_id = int(self.contacts_table.item(current_row, 0).text())
            current_role = self.contacts_table.item(current_row, 4).text()
            
            # Demander le nouveau rôle
            role, ok = QInputDialog.getItem(
                self, "Modifier le rôle",
                "Nouveau rôle:",
                ["SPONSOR", "VALIDEUR", "REFERENT", "INFORME"],
                ["SPONSOR", "VALIDEUR", "REFERENT", "INFORME"].index(current_role) if current_role in ["SPONSOR", "VALIDEUR", "REFERENT", "INFORME"] else 0,
                False
            )
            
            if not ok:
                return
            
            # Mettre à jour
            db_service.execute(
                "UPDATE projet_contacts SET role = ? WHERE id = ?",
                (role, pc_id)
            )
            
            # Recharger
            self.load_contacts()
            
        except Exception as e:
            logger.error(f"Erreur modification rôle contact: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de modifier le rôle:\n{e}")
    
    def remove_contact(self):
        """Retire un contact du projet."""
        try:
            current_row = self.contacts_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un contact.")
                return
            
            pc_id = int(self.contacts_table.item(current_row, 0).text())
            
            reply = QMessageBox.question(
                self, "Confirmation",
                "Voulez-vous vraiment retirer ce contact du projet ?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                db_service.execute("DELETE FROM projet_contacts WHERE id = ?", (pc_id,))
                self.load_contacts()
        
        except Exception as e:
            logger.error(f"Erreur retrait contact: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de retirer le contact:\n{e}")
    
    def add_document(self):
        """Ajoute un document au projet."""
        try:
            if not self.projet_id:
                QMessageBox.warning(self, "Attention", "Veuillez d'abord enregistrer le projet.")
                return
            
            # Ouvrir le dialogue de document
            dialog = DocumentDialog(self, self.projet_id)
            if dialog.exec_() == QDialog.Accepted:
                self.load_documents()
        
        except Exception as e:
            logger.error(f"Erreur ajout document: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le document:\n{e}")
    
    def download_document(self):
        """Télécharge un document."""
        try:
            current_row = self.documents_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un document.")
                return
            
            doc_id = int(self.documents_table.item(current_row, 0).text())
            doc = db_service.fetch_one(
                "SELECT nom_fichier, chemin_fichier FROM projet_documents WHERE id = ?",
                (doc_id,)
            )
            
            if not doc or not doc['chemin_fichier']:
                QMessageBox.warning(self, "Attention", "Fichier introuvable.")
                return
            
            if not os.path.exists(doc['chemin_fichier']):
                QMessageBox.warning(self, "Attention", "Le fichier n'existe plus sur le disque.")
                return
            
            # Demander où enregistrer
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Enregistrer sous", doc['nom_fichier']
            )
            
            if save_path:
                import shutil
                shutil.copy2(doc['chemin_fichier'], save_path)
                QMessageBox.information(self, "Succès", "Document téléchargé avec succès.")
        
        except Exception as e:
            logger.error(f"Erreur téléchargement document: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de télécharger le document:\n{e}")
    
    def remove_document(self):
        """Supprime un document."""
        try:
            current_row = self.documents_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un document.")
                return
            
            doc_id = int(self.documents_table.item(current_row, 0).text())
            
            reply = QMessageBox.question(
                self, "Confirmation",
                "Voulez-vous vraiment supprimer ce document ?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                db_service.execute("DELETE FROM projet_documents WHERE id = ?", (doc_id,))
                self.load_documents()
        
        except Exception as e:
            logger.error(f"Erreur suppression document: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le document:\n{e}")
    
    def create_tache(self):
        """Crée une nouvelle tâche pour ce projet."""
        try:
            if not self.projet_id:
                QMessageBox.warning(self, "Attention", "Veuillez d'abord enregistrer le projet.")
                return
            from app.ui.dialogs.tache_dialog import TacheDialog
            dialog = TacheDialog(self, tache={'projet_id': self.projet_id})
            if dialog.exec_() == QDialog.Accepted:
                self.load_taches()
        except Exception as e:
            logger.error(f"Erreur création tâche: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de créer la tâche:\n{e}")

    def create_bc_projet(self):
        """Crée un BC lié à ce projet depuis l'onglet Tâches (hors budget)."""
        try:
            if not self.projet_id:
                QMessageBox.warning(self, "Attention", "Veuillez d'abord enregistrer le projet.")
                return

            from app.ui.views.bon_commande_view import BonCommandeDialog
            from app.services.budget_v5_service import budget_v5_service
            from app.services.bon_commande_service import bon_commande_service
            from app.services.fournisseur_service import fournisseur_service

            # Récupérer l'entité du projet
            projet = db_service.fetch_one(
                "SELECT * FROM projets WHERE id=?", (self.projet_id,))
            entite_id = dict(projet).get('entite_id') if projet else None

            dlg = BonCommandeDialog(
                budget_svc=budget_v5_service,
                fourn_svc=fournisseur_service,
                bc_svc=bon_commande_service,
                bc={'projet_id': self.projet_id,
                    'entite_id': entite_id,
                    'budget_impute': 'HORS_BUDGET',
                    'statut': 'BROUILLON'},
                parent=self
            )
            if dlg.exec_() == QDialog.Accepted:
                data = dlg.get_data()
                # Forcer hors budget
                data['budget_impute'] = 'HORS_BUDGET'
                data['projet_id']     = self.projet_id
                if entite_id:
                    data['entite_id'] = entite_id

                # Chercher une ligne budgétaire existante pour l'entité
                lb = db_service.fetch_one("""
                    SELECT lb.id, lb.montant_vote, lb.montant_solde
                    FROM lignes_budgetaires lb
                    JOIN budgets_annuels ba ON ba.id = lb.budget_id
                    WHERE ba.entite_id = ?
                    AND lb.statut = 'ACTIF'
                    ORDER BY lb.montant_vote DESC
                    LIMIT 1
                """, (entite_id,)) if entite_id else None

                if lb:
                    data['ligne_budgetaire_id'] = dict(lb)['id']

                bc_id = bon_commande_service.create_bon_commande(data)

                # Proposer de créer une tâche liée
                rep = QMessageBox.question(
                    self, "Créer une tâche ?",
                    "Voulez-vous créer une tâche associée à ce bon de commande ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if rep == QMessageBox.Yes:
                    from app.ui.dialogs.tache_dialog import TacheDialog
                    bc_data = bon_commande_service.get_bon_commande_by_id(bc_id)
                    tache_init = {
                        'projet_id':    self.projet_id,
                        'titre':        f"BC {data.get('numero_bc','')} — {data.get('objet','')}",
                        'description':  f"Tâche liée au BC {data.get('numero_bc','')}",
                        'statut':       'A_FAIRE',
                        'priorite':     'MOYENNE',
                    }
                    tdlg = TacheDialog(self, tache=tache_init, projet_obligatoire=False)
                    if tdlg.exec_() == QDialog.Accepted:
                        self.load_taches()
                else:
                    self.load_taches()

                QMessageBox.information(self, "BC créé",
                    f"Bon de commande créé et lié au projet.\n"
                    f"{'Imputé sur ligne budgétaire existante.' if lb else 'Aucune ligne budgétaire disponible — marqué Hors Budget.'}")
        except Exception as e:
            logger.error(f"Erreur création BC projet: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de créer le BC:\n{e}")
