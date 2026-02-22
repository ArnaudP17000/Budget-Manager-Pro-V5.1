"""
Vue de gestion des contacts.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QGroupBox, QMessageBox,
    QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from app.services.contact_service import contact_service
from app.ui.dialogs.contact_dialog import ContactDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class ContactView(QWidget):
    """Vue de gestion des contacts."""
    
    def __init__(self):
        super().__init__()
        self.contact_service = contact_service
        self.init_ui()
        # Charger les contacts aprÃ¨s un court dÃ©lai
        QTimer.singleShot(100, self.load_contacts)
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel("Gestion des Contacts")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # Filtres
        filters_group = self.create_filters()
        layout.addWidget(filters_group)
        
        # KPI
        kpi_group = self.create_kpi()
        layout.addWidget(kpi_group)
        
        # Tableau
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Nom", "Prénom", "Fonction", "Type", "Téléphone", "Email"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_contact)
        layout.addWidget(self.table)
        
        # Boutons d'action
        buttons_layout = self.create_action_buttons()
        layout.addLayout(buttons_layout)
    
    def create_filters(self):
        """CrÃ©e la section des filtres."""
        group = QGroupBox("Filtres")
        layout = QHBoxLayout()
        
        # Filtre type
        layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems([
            "Tous",
            "ELU",
            "DIRECTION",
            "INTERNE",
            "EXTERNE",
            "PRESTATAIRE",
            "AMO"
        ])
        self.type_filter.currentTextChanged.connect(self.load_contacts)
        layout.addWidget(self.type_filter)
        
        # Recherche
        layout.addWidget(QLabel("Recherche:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nom, prénom, email...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_edit)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_kpi(self):
        """CrÃ©e la section des KPI."""
        group = QGroupBox("Indicateurs")
        layout = QHBoxLayout()
        
        self.kpi_total = QLabel("Total: 0")
        self.kpi_fournisseurs = QLabel("Fournisseurs: 0")
        self.kpi_clients = QLabel("Clients: 0")
        self.kpi_internes = QLabel("Internes: 0")
        self.kpi_externes = QLabel("Externes: 0")
        
        for kpi in [self.kpi_total, self.kpi_fournisseurs, self.kpi_clients,
                    self.kpi_internes, self.kpi_externes]:
            kpi.setStyleSheet("font-weight: bold; padding: 5px 10px;")
            layout.addWidget(kpi)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self):
        """CrÃ©e les boutons d'action."""
        layout = QHBoxLayout()
        
        self.btn_nouveau = QPushButton("Nouveau")
        self.btn_nouveau.clicked.connect(self.create_contact)
        layout.addWidget(self.btn_nouveau)
        
        self.btn_modifier = QPushButton("Modifier")
        self.btn_modifier.clicked.connect(self.edit_contact)
        layout.addWidget(self.btn_modifier)
        
        self.btn_supprimer = QPushButton("Supprimer")
        self.btn_supprimer.clicked.connect(self.delete_contact)
        layout.addWidget(self.btn_supprimer)
        
        self.btn_rafraichir = QPushButton("Rafraîchir")
        self.btn_rafraichir.clicked.connect(self.load_contacts)
        layout.addWidget(self.btn_rafraichir)
        
        layout.addStretch()
        return layout
    
    def on_search_changed(self):
        """AppelÃ© quand le texte de recherche change."""
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.load_contacts)
        self._search_timer.start(500)
    
    def get_filters(self):
        """RÃ©cupÃ¨re les filtres actifs."""
        filters = {}
        
        # Type
        type_contact = self.type_filter.currentText()
        if type_contact and type_contact != "Tous":
            filters['type'] = type_contact
        
        # Recherche
        search = self.search_edit.text().strip()
        if search:
            filters['search'] = search
        
        return filters if filters else None
    
    def load_contacts(self):
        """Charge les contacts depuis la base de donnÃ©es."""
        try:
            # Récupérer les filtres
            filters = self.get_filters()
            
            # Charger les contacts
            contacts = self.contact_service.get_all(filters)
            
            # Mettre Ã  jour le tableau
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for row_idx, contact in enumerate(contacts):
                self.table.insertRow(row_idx)
                
                # Nom
                nom_item = QTableWidgetItem(contact['nom'] or '')
                nom_item.setData(Qt.UserRole, contact['id'])
                self.table.setItem(row_idx, 0, nom_item)
                
                # PrÃ©nom
                prenom_item = QTableWidgetItem(safe_get(contact, 'prenom', '') or '')
                self.table.setItem(row_idx, 1, prenom_item)
                
                # Fonction
                fonction_item = QTableWidgetItem(safe_get(contact, 'fonction', '') or '')
                self.table.setItem(row_idx, 2, fonction_item)
                
                # Type
                type_contact = safe_get(contact, 'type', '')
                type_item = QTableWidgetItem(type_contact)
                type_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 3, type_item)
                
                # TÃ©lÃ©phone
                telephone_item = QTableWidgetItem(safe_get(contact, 'telephone', '') or '')
                self.table.setItem(row_idx, 4, telephone_item)
                
                # Email
                email_item = QTableWidgetItem(safe_get(contact, 'email', '') or '')
                self.table.setItem(row_idx, 5, email_item)
            
            self.table.setSortingEnabled(True)
            
            # Mettre Ã  jour les KPI
            self.update_kpi()
            
            logger.info(f"{len(contacts)} contact(s) chargés)")
        
        except Exception as e:
            logger.error(f"Erreur chargement contacts: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les contacts:\n{e}")
    
    def update_kpi(self):
        """Met Ã  jour les indicateurs KPI."""
        try:
            stats = self.contact_service.get_stats()
            
            self.kpi_total.setText(f"Total: {stats.get('total', 0)}")
            self.kpi_fournisseurs.setText(f"Fournisseurs: {stats.get('fournisseurs', 0)}")
            self.kpi_clients.setText(f"Clients: {stats.get('clients', 0)}")
            self.kpi_internes.setText(f"Internes: {stats.get('internes', 0)}")
            self.kpi_externes.setText(f"Externes: {stats.get('externes', 0)}")
        
        except Exception as e:
            logger.error(f"Erreur mise Ã  jour KPI: {e}")
    
    def create_contact(self):
        """Ouvre le dialogue de crÃ©ation de contact."""
        try:
            dialog = ContactDialog(self)
            if dialog.exec_():
                self.load_contacts()
                QMessageBox.information(self, "Succès", "Contact créé avec succès !")
        except Exception as e:
            logger.error(f"Erreur création contact: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de créer le contact:\n{e}")
    
    def edit_contact(self):
        """Ouvre le dialogue d'Ã©dition du contact sÃ©lectionnÃ©."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sÃ©lectionner un contact.")
                return
            
            contact_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            contact = self.contact_service.get_by_id(contact_id)
            if not contact:
                QMessageBox.warning(self, "Erreur", "Contact introuvable.")
                return
            
            dialog = ContactDialog(self, contact)
            if dialog.exec_():
                self.load_contacts()
                QMessageBox.information(self, "Succès", "Contact modifié avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur Ã©dition contact: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de modifier le contact:\n{e}")
    
    def delete_contact(self):
        """Supprime le contact sÃ©lectionné."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un contact.")
                return
            
            contact_nom = self.table.item(selected_row, 0).text()
            contact_prenom = self.table.item(selected_row, 1).text()
            nom_complet = f"{contact_nom} {contact_prenom}".strip()
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"êtes-voustes-vous sûr de vouloir supprimer le contact '{nom_complet}' ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                contact_id = self.table.item(selected_row, 0).data(Qt.UserRole)
                self.contact_service.delete(contact_id)
                self.load_contacts()
                QMessageBox.information(self, "Succès", "Contact supprimé avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur suppression contact: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le contact:\n{e}")
