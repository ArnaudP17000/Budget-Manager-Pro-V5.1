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
    QCheckBox
)
from PyQt5.QtCore import QDate, Qt
from app.services.database_service import db_service
from app.services.projet_service import projet_service
from app.ui.dialogs.document_dialog import DocumentDialog
from app.ui.dialogs.tache_dialog import TacheDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
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
        budget_tab = self.create_budget_tab()
        self.tabs.addTab(budget_tab, "💰 Budget")
        
        # Onglet 3: Équipe
        equipe_tab = self.create_equipe_tab()
        self.tabs.addTab(equipe_tab, "👥 Équipe")
        
        # Onglet 4: Contacts
        contacts_tab = self.create_contacts_tab()
        self.tabs.addTab(contacts_tab, "📞 Contacts")
        
        # Onglet 5: Documents
        documents_tab = self.create_documents_tab()
        self.tabs.addTab(documents_tab, "📄 Documents")
        
        # Onglet 6: Tâches
        taches_tab = self.create_taches_tab()
        self.tabs.addTab(taches_tab, "✓ Tâches")
        
        layout.addWidget(self.tabs)
        
        # Boutons OK/Annuler
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
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
    
    def create_budget_tab(self):
        """Crée l'onglet Budget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        
        # Budget initial
        self.budget_initial_spin = QDoubleSpinBox()
        self.budget_initial_spin.setRange(0, 100000000)
        self.budget_initial_spin.setSingleStep(1000)
        self.budget_initial_spin.setSuffix(" €")
        self.budget_initial_spin.setDecimals(2)
        form.addRow("Budget initial:", self.budget_initial_spin)
        
        # Budget estimé
        self.budget_estime_spin = QDoubleSpinBox()
        self.budget_estime_spin.setRange(0, 100000000)
        self.budget_estime_spin.setSingleStep(1000)
        self.budget_estime_spin.setSuffix(" €")
        self.budget_estime_spin.setDecimals(2)
        form.addRow("Budget estimé:", self.budget_estime_spin)
        
        # Budget actuel
        self.budget_actuel_spin = QDoubleSpinBox()
        self.budget_actuel_spin.setRange(0, 100000000)
        self.budget_actuel_spin.setSingleStep(1000)
        self.budget_actuel_spin.setSuffix(" €")
        self.budget_actuel_spin.setDecimals(2)
        form.addRow("Budget actuel:", self.budget_actuel_spin)
        
        # Budget consommé (lecture seule)
        self.budget_consomme_label = QLabel("0 €")
        form.addRow("Budget consommé:", self.budget_consomme_label)
        
        # Lien AP
        self.ap_combo = QComboBox()
        self.ap_combo.addItem("-- Aucune --", None)
        # Charger les AP disponibles
        try:
            aps = db_service.fetch_all(
                "SELECT id, numero_ap, libelle FROM autorisations_programme WHERE statut = 'ACTIVE' ORDER BY numero_ap"
            )
            for ap in aps:
                self.ap_combo.addItem(f"{ap['numero_ap']} - {ap['libelle']}", ap['id'])
        except Exception as e:
            logger.error(f"Erreur chargement AP: {e}")
        form.addRow("Autorisation Programme:", self.ap_combo)
        
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
        
        # Bouton créer tâche
        btn_layout = QHBoxLayout()
        btn_create_tache = QPushButton("➕ Créer tâche")
        btn_create_tache.clicked.connect(self.create_tache)
        btn_layout.addWidget(btn_create_tache)
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
                index = self.type_combo.findText(self.projet['type_projet'])
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'phase'):
                index = self.phase_combo.findText(self.projet['phase'])
                if index >= 0:
                    self.phase_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'priorite'):
                index = self.priorite_combo.findText(self.projet['priorite'])
                if index >= 0:
                    self.priorite_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'statut'):
                index = self.statut_combo.findText(self.projet['statut'])
                if index >= 0:
                    self.statut_combo.setCurrentIndex(index)
            
            if safe_get(self.projet, 'date_debut'):
                self.date_debut.setDate(QDate.fromString(self.projet['date_debut'], "yyyy-MM-dd"))
            
            if safe_get(self.projet, 'date_fin_prevue'):
                self.date_fin.setDate(QDate.fromString(self.projet['date_fin_prevue'], "yyyy-MM-dd"))
            
            if safe_get(self.projet, 'date_fin_reelle'):
                self.date_fin_reelle.setDate(QDate.fromString(self.projet['date_fin_reelle'][:10], "yyyy-MM-dd"))
                self.chk_termine.setChecked(True)
                self.date_fin_reelle.setEnabled(True)
            
            self.avancement_spin.setValue(safe_get(self.projet, 'avancement', 0) or 0)
            
            # Service bénéficiaire
            if safe_get(self.projet, 'service_id'):
                for i in range(self.service_combo.count()):
                    if self.service_combo.itemData(i) == self.projet['service_id']:
                        self.service_combo.setCurrentIndex(i)
                        break
            
            # Onglet Budget
            self.budget_initial_spin.setValue(float(safe_get(self.projet, 'budget_initial', 0) or 0))
            self.budget_estime_spin.setValue(float(safe_get(self.projet, 'budget_estime', 0) or 0))
            self.budget_actuel_spin.setValue(float(safe_get(self.projet, 'budget_actuel', 0) or 0))
            budget_consomme = float(safe_get(self.projet, 'budget_consomme', 0) or 0)
            self.budget_consomme_label.setText(f"{budget_consomme:,.2f} €")
            
            # AP
            if safe_get(self.projet, 'ap_id'):
                for i in range(self.ap_combo.count()):
                    if self.ap_combo.itemData(i) == self.projet['ap_id']:
                        self.ap_combo.setCurrentIndex(i)
                        break
            
            # Onglet Équipe
            if safe_get(self.projet, 'responsable_id'):
                target = f"USR_{self.projet['responsable_id']}"
                for i in range(self.responsable_combo.count()):
                    if self.responsable_combo.itemData(i) == target:
                        self.responsable_combo.setCurrentIndex(i)
                        break

            if safe_get(self.projet, 'chef_projet_id'):
                target = f"USR_{self.projet['chef_projet_id']}"
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
                'budget_initial': self.budget_initial_spin.value(),
                'budget_estime': self.budget_estime_spin.value(),
                'budget_actuel': self.budget_actuel_spin.value(),
            }
            
            # Date fin réelle si définie
            if self.chk_termine.isChecked():
                data['date_fin_reelle'] = self.date_fin_reelle.date().toString("yyyy-MM-dd")
            else:
                data['date_fin_reelle'] = None
            
            # AP
            ap_id = self.ap_combo.currentData()
            if ap_id:
                data['ap_id'] = ap_id
            
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
        """Ajoute un contact au projet."""
        try:
            if not self.projet_id:
                QMessageBox.warning(self, "Attention", "Veuillez d'abord enregistrer le projet.")
                return
            
            # Récupérer tous les contacts disponibles
            contacts = db_service.fetch_all("""
                SELECT id, nom, prenom, type, fonction
                FROM contacts
                ORDER BY nom, prenom
            """)
            
            if not contacts:
                QMessageBox.information(self, "Info", "Aucun contact disponible.")
                return
            
            # Créer une liste de choix
            contact_choices = [f"{c['nom']} {c['prenom']} ({c['type']})" for c in contacts]
            contact_choice, ok = QInputDialog.getItem(
                self, "Ajouter un contact", 
                "Sélectionnez un contact:", 
                contact_choices, 0, False
            )
            
            if not ok:
                return
            
            contact_idx = contact_choices.index(contact_choice)
            contact = contacts[contact_idx]
            
            # Demander le rôle
            role, ok = QInputDialog.getItem(
                self, "Rôle du contact",
                "Sélectionnez le rôle:",
                ["SPONSOR", "VALIDEUR", "REFERENT", "INFORME"],
                0, False
            )
            
            if not ok:
                return
            
            # Insérer dans la base
            db_service.execute("""
                INSERT OR IGNORE INTO projet_contacts (projet_id, contact_id, role)
                VALUES (?, ?, ?)
            """, (self.projet_id, contact['id'], role))
            
            # Recharger la table
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
            
            # Créer une tâche pré-remplie avec le projet_id
            from app.ui.dialogs.tache_dialog import TacheDialog
            dialog = TacheDialog(self, tache={'projet_id': self.projet_id})
            if dialog.exec_() == QDialog.Accepted:
                self.load_taches()
        
        except Exception as e:
            logger.error(f"Erreur création tâche: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de créer la tâche:\n{e}")
