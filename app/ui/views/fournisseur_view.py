"""
Vue de gestion des fournisseurs.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QGroupBox, QMessageBox,
    QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush
from app.services.fournisseur_service import fournisseur_service
from app.ui.dialogs.fournisseur_dialog import FournisseurDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class FournisseurView(QWidget):
    """Vue de gestion des fournisseurs."""
    
    def __init__(self):
        super().__init__()
        self.fournisseur_service = fournisseur_service
        self.init_ui()
        # Charger les fournisseurs après un court délai
        QTimer.singleShot(100, self.load_fournisseurs)
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel("🏢 Gestion des Fournisseurs")
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Nom", "Nb contrats", "Nb BC", "Montant total", "Statut"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_fournisseur)
        layout.addWidget(self.table)
        
        # Boutons d'action
        buttons_layout = self.create_action_buttons()
        layout.addLayout(buttons_layout)
    
    def create_filters(self):
        """Crée la section des filtres."""
        group = QGroupBox("🔍 Filtres")
        layout = QHBoxLayout()
        
        # Filtre statut
        layout.addWidget(QLabel("Statut:"))
        self.statut_filter = QComboBox()
        self.statut_filter.addItems([
            "Tous",
            "ACTIF",
            "INACTIF",
            "SUSPENDU"
        ])
        self.statut_filter.currentTextChanged.connect(self.load_fournisseurs)
        layout.addWidget(self.statut_filter)
        
        # Recherche
        layout.addWidget(QLabel("Recherche:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nom, SIRET...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_edit)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_kpi(self):
        """Crée la section des KPI."""
        group = QGroupBox("📊 Indicateurs")
        layout = QHBoxLayout()
        
        self.kpi_total = QLabel("Total: 0")
        self.kpi_actifs = QLabel("Actifs: 0")
        self.kpi_inactifs = QLabel("Inactifs: 0")
        self.kpi_contrats = QLabel("Total contrats: 0")
        self.kpi_montant = QLabel("Montant total: 0.00 €")
        
        for kpi in [self.kpi_total, self.kpi_actifs, self.kpi_inactifs,
                    self.kpi_contrats, self.kpi_montant]:
            kpi.setStyleSheet("font-weight: bold; padding: 5px 10px;")
            layout.addWidget(kpi)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self):
        """Crée les boutons d'action."""
        layout = QHBoxLayout()
        
        self.btn_nouveau = QPushButton("➕ Nouveau")
        self.btn_nouveau.clicked.connect(self.create_fournisseur)
        layout.addWidget(self.btn_nouveau)
        
        self.btn_modifier = QPushButton("✏️ Modifier")
        self.btn_modifier.clicked.connect(self.edit_fournisseur)
        layout.addWidget(self.btn_modifier)
        
        self.btn_supprimer = QPushButton("🗑️ Supprimer")
        self.btn_supprimer.clicked.connect(self.delete_fournisseur)
        layout.addWidget(self.btn_supprimer)
        
        self.btn_rafraichir = QPushButton("🔄 Rafraîchir")
        self.btn_rafraichir.clicked.connect(self.load_fournisseurs)
        layout.addWidget(self.btn_rafraichir)
        
        layout.addStretch()
        return layout
    
    def on_search_changed(self):
        """Appelé quand le texte de recherche change."""
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.load_fournisseurs)
        self._search_timer.start(500)
    
    def get_filters(self):
        """Récupère les filtres actifs."""
        filters = {}
        
        # Statut
        statut = self.statut_filter.currentText()
        if statut and statut != "Tous":
            filters['statut'] = statut
        
        # Recherche
        search = self.search_edit.text().strip()
        if search:
            filters['search'] = search
        
        return filters if filters else None
    
    def load_fournisseurs(self):
        """Charge les fournisseurs depuis la base de données."""
        try:
            # Récupérer les filtres
            filters = self.get_filters()
            
            # Charger les fournisseurs
            fournisseurs = self.fournisseur_service.get_all(filters)
            
            # Mettre à jour le tableau
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for row_idx, fournisseur in enumerate(fournisseurs):
                self.table.insertRow(row_idx)
                
                # Nom
                nom_item = QTableWidgetItem(fournisseur['nom'] or '')
                nom_item.setData(Qt.UserRole, fournisseur['id'])
                self.table.setItem(row_idx, 0, nom_item)
                
                # Nb contrats
                nb_contrats = safe_get(fournisseur, 'nb_contrats', 0) or 0
                contrats_item = QTableWidgetItem(str(nb_contrats))
                contrats_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 1, contrats_item)
                
                # Nb BC
                nb_bc = safe_get(fournisseur, 'nb_bc', 0) or 0
                bc_item = QTableWidgetItem(str(nb_bc))
                bc_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 2, bc_item)
                
                # Montant total
                montant_total = safe_get(fournisseur, 'montant_total', 0) or 0
                montant_item = QTableWidgetItem(f"{montant_total:,.2f} €")
                montant_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_idx, 3, montant_item)
                
                # Statut
                statut = safe_get(fournisseur, 'statut', '')
                statut_item = QTableWidgetItem(statut)
                statut_item.setTextAlignment(Qt.AlignCenter)
                
                if statut == 'ACTIF':
                    statut_item.setBackground(QBrush(QColor(144, 238, 144)))  # Vert clair
                elif statut == 'INACTIF':
                    statut_item.setBackground(QBrush(QColor(211, 211, 211)))  # Gris clair
                elif statut == 'SUSPENDU':
                    statut_item.setBackground(QBrush(QColor(255, 182, 193)))  # Rouge clair
                
                self.table.setItem(row_idx, 4, statut_item)
            
            self.table.setSortingEnabled(True)
            
            # Mettre à jour les KPI
            self.update_kpi()
            
            logger.info(f"{len(fournisseurs)} fournisseur(s) chargé(s)")
        
        except Exception as e:
            logger.error(f"Erreur chargement fournisseurs: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les fournisseurs:\n{e}")
    
    def update_kpi(self):
        """Met à jour les indicateurs KPI."""
        try:
            stats = self.fournisseur_service.get_stats()
            
            self.kpi_total.setText(f"Total: {stats.get('total', 0)}")
            self.kpi_actifs.setText(f"Actifs: {stats.get('actifs', 0)}")
            self.kpi_inactifs.setText(f"Inactifs: {stats.get('inactifs', 0)}")
            self.kpi_contrats.setText(f"Total contrats: {stats.get('total_contrats', 0)}")
            montant = stats.get('montant_total', 0) or 0
            self.kpi_montant.setText(f"Montant total: {montant:,.2f} €")
        
        except Exception as e:
            logger.error(f"Erreur mise à jour KPI: {e}")
    
    def create_fournisseur(self):
        """Ouvre le dialogue de création de fournisseur."""
        try:
            dialog = FournisseurDialog(self)
            if dialog.exec_():
                self.load_fournisseurs()
                QMessageBox.information(self, "Succès", "Fournisseur créé avec succès !")
        except Exception as e:
            logger.error(f"Erreur création fournisseur: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de créer le fournisseur:\n{e}")
    
    def edit_fournisseur(self):
        """Ouvre le dialogue d'édition du fournisseur sélectionné."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un fournisseur.")
                return
            
            fournisseur_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            fournisseur = self.fournisseur_service.get_by_id(fournisseur_id)
            if not fournisseur:
                QMessageBox.warning(self, "Erreur", "Fournisseur introuvable.")
                return
            
            dialog = FournisseurDialog(self, fournisseur)
            if dialog.exec_():
                self.load_fournisseurs()
                QMessageBox.information(self, "Succès", "Fournisseur modifié avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur édition fournisseur: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de modifier le fournisseur:\n{e}")
    
    def delete_fournisseur(self):
        """Supprime le fournisseur sélectionné."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un fournisseur.")
                return
            
            fournisseur_nom = self.table.item(selected_row, 0).text()
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Êtes-vous sûr de vouloir supprimer le fournisseur '{fournisseur_nom}' ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                fournisseur_id = self.table.item(selected_row, 0).data(Qt.UserRole)
                self.fournisseur_service.delete(fournisseur_id)
                self.load_fournisseurs()
                QMessageBox.information(self, "Succès", "Fournisseur supprimé avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur suppression fournisseur: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le fournisseur:\n{e}")
