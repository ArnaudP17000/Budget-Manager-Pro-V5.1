"""
Vue de gestion des services.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QGroupBox, QMessageBox,
    QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from app.services.service_service import service_service
from app.ui.dialogs.service_dialog import ServiceDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class ServiceView(QWidget):
    """Vue de gestion des services."""
    
    def __init__(self):
        super().__init__()
        self.service_service = service_service
        self.init_ui()
        # Charger les services aprÃ¨s un court dÃ©lai
        QTimer.singleShot(100, self.load_services)
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel("Gestion des Services")
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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Code", "Nom", "Responsable", "Nb projets"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_service)
        layout.addWidget(self.table)
        
        # Boutons d'action
        buttons_layout = self.create_action_buttons()
        layout.addLayout(buttons_layout)
    
    def create_filters(self):
        """CrÃ©e la section des filtres."""
        group = QGroupBox("Filtres")
        layout = QHBoxLayout()
        
        # Recherche
        layout.addWidget(QLabel("Recherche:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Code, nom, responsable...")
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
        self.kpi_avec_responsable = QLabel("Avec responsable: 0")
        self.kpi_sans_responsable = QLabel("Sans responsable: 0")
        self.kpi_total_projets = QLabel("Total projets: 0")
        
        for kpi in [self.kpi_total, self.kpi_avec_responsable, 
                    self.kpi_sans_responsable, self.kpi_total_projets]:
            kpi.setStyleSheet("font-weight: bold; padding: 5px 10px;")
            layout.addWidget(kpi)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self):
        """CrÃ©e les boutons d'action."""
        layout = QHBoxLayout()
        
        self.btn_nouveau = QPushButton("Nouveau")
        self.btn_nouveau.clicked.connect(self.create_service)
        layout.addWidget(self.btn_nouveau)
        
        self.btn_modifier = QPushButton("Modifier")
        self.btn_modifier.clicked.connect(self.edit_service)
        layout.addWidget(self.btn_modifier)
        
        self.btn_supprimer = QPushButton("Supprimer")
        self.btn_supprimer.clicked.connect(self.delete_service)
        layout.addWidget(self.btn_supprimer)
        
        self.btn_rafraichir = QPushButton("Rafraîchir")
        self.btn_rafraichir.clicked.connect(self.load_services)
        layout.addWidget(self.btn_rafraichir)
        
        layout.addStretch()
        return layout
    
    def on_search_changed(self):
        """AppelÃ© quand le texte de recherche change."""
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.load_services)
        self._search_timer.start(500)
    
    def get_filters(self):
        """RÃ©cupÃ¨re les filtres actifs."""
        filters = {}
        
        # Recherche
        search = self.search_edit.text().strip()
        if search:
            filters['search'] = search
        
        return filters if filters else None
    
    def load_services(self):
        """Charge les services depuis la base de donnÃ©es."""
        try:
            # RÃ©cupÃ©rer les filtres
            filters = self.get_filters()
            
            # Charger les services
            services = self.service_service.get_all(filters)
            
            # Mettre Ã  jour le tableau
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for row_idx, service in enumerate(services):
                self.table.insertRow(row_idx)
                
                # Code
                code_item = QTableWidgetItem(service['code'] or '')
                code_item.setData(Qt.UserRole, service['id'])
                self.table.setItem(row_idx, 0, code_item)
                
                # Nom
                nom_item = QTableWidgetItem(service['nom'] or '')
                self.table.setItem(row_idx, 1, nom_item)
                
                # Responsable
                responsable = safe_get(service, 'responsable_nom', '')
                responsable_item = QTableWidgetItem(responsable)
                self.table.setItem(row_idx, 2, responsable_item)
                
                # Nb projets
                nb_projets = safe_get(service, 'nb_projets', 0) or 0
                projets_item = QTableWidgetItem(str(nb_projets))
                projets_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 3, projets_item)
            
            self.table.setSortingEnabled(True)
            
            # Mettre Ã  jour les KPI
            self.update_kpi()
            
            logger.info(f"{len(services)} service(s) chargÃ©(s)")
        
        except Exception as e:
            logger.error(f"Erreur chargement services: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les services:\n{e}")
    
    def update_kpi(self):
        """Met Ã  jour les indicateurs KPI."""
        try:
            stats = self.service_service.get_stats()
            
            self.kpi_total.setText(f"Total: {stats.get('total', 0)}")
            self.kpi_avec_responsable.setText(f"Avec responsable: {stats.get('avec_responsable', 0)}")
            self.kpi_sans_responsable.setText(f"Sans responsable: {stats.get('sans_responsable', 0)}")
            self.kpi_total_projets.setText(f"Total projets: {stats.get('total_projets', 0)}")
        
        except Exception as e:
            logger.error(f"Erreur mise Ã  jour KPI: {e}")
    
    def create_service(self):
        """Ouvre le dialogue de crÃ©ation de service."""
        try:
            dialog = ServiceDialog(self)
            if dialog.exec_():
                self.load_services()
                QMessageBox.information(self, "Succès", "Service crée avec succès !")
        except Exception as e:
            logger.error(f"Erreur crÃ©ation service: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de créer le service:\n{e}")
    
    def edit_service(self):
        """Ouvre le dialogue d'Ã©dition du service sÃ©lectionnÃ©."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un service.")
                return
            
            service_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            service = self.service_service.get_by_id(service_id)
            if not service:
                QMessageBox.warning(self, "Erreur", "Service introuvable.")
                return
            
            dialog = ServiceDialog(self, service)
            if dialog.exec_():
                self.load_services()
                QMessageBox.information(self, "SuccÃ¨s", "Service modifié avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur Ã©dition service: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de modifier le service:\n{e}")
    
    def delete_service(self):
        """Supprime le service sÃ©lectionnÃ©."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un service.")
                return
            
            service_nom = self.table.item(selected_row, 1).text()
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"êtes-vous sûr de vouloir supprimer le service '{service_nom}' ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                service_id = self.table.item(selected_row, 0).data(Qt.UserRole)
                self.service_service.delete(service_id)
                self.load_services()
                QMessageBox.information(self, "Succès", "Service supprimé avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur suppression service: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le service:\n{e}")
