"""
Vue de gestion des projets.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QGroupBox, QMessageBox,
    QHeaderView, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush
from app.services.projet_service import projet_service
from app.ui.dialogs.projet_dialog import ProjetDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class ProjetView(QWidget):
    """Vue de gestion des projets."""
    
    def __init__(self):
        super().__init__()
        self.projet_service = projet_service
        self.init_ui()
        # Charger les projets après un court délai pour que l'UI soit complète
        QTimer.singleShot(100, self.load_projets)
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel("📁 Gestion des Projets")
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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Code", "Nom", "Budget Initial", "Date Début", "Date Fin",
            "Statut", "Avancement", "Responsable"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_projet)
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
            "EN_ATTENTE",
            "TERMINE",
            "ANNULE"
        ])
        self.statut_filter.currentTextChanged.connect(self.load_projets)
        layout.addWidget(self.statut_filter)
        
        # Filtre budget
        layout.addWidget(QLabel("Budget:"))
        self.budget_filter = QComboBox()
        self.budget_filter.addItems([
            "Tous",
            "< 100k €",
            "100k - 500k €",
            "> 500k €"
        ])
        self.budget_filter.currentTextChanged.connect(self.load_projets)
        layout.addWidget(self.budget_filter)
        
        # Recherche
        layout.addWidget(QLabel("Recherche:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Code, nom, description...")
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
        self.kpi_attente = QLabel("En attente: 0")
        self.kpi_termines = QLabel("Terminés: 0")
        self.kpi_budget = QLabel("Budget total: 0 €")
        
        for kpi in [self.kpi_total, self.kpi_actifs, self.kpi_attente, 
                    self.kpi_termines, self.kpi_budget]:
            kpi.setStyleSheet("font-weight: bold; padding: 5px 10px;")
            layout.addWidget(kpi)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self):
        """Crée les boutons d'action."""
        layout = QHBoxLayout()
        
        self.btn_nouveau = QPushButton("➕ Nouveau")
        self.btn_nouveau.clicked.connect(self.create_projet)
        layout.addWidget(self.btn_nouveau)
        
        self.btn_modifier = QPushButton("✏️ Modifier")
        self.btn_modifier.clicked.connect(self.edit_projet)
        layout.addWidget(self.btn_modifier)
        
        self.btn_supprimer = QPushButton("🗑️ Supprimer")
        self.btn_supprimer.clicked.connect(self.delete_projet)
        layout.addWidget(self.btn_supprimer)
        
        self.btn_rafraichir = QPushButton("🔄 Rafraîchir")
        self.btn_rafraichir.clicked.connect(self.load_projets)
        layout.addWidget(self.btn_rafraichir)

        self.btn_fiche = QPushButton("🖨️ Fiche Word")
        self.btn_fiche.setStyleSheet(
            "background:#C00000;color:white;font-weight:bold;padding:5px 12px;border-radius:4px;")
        self.btn_fiche.clicked.connect(self.exporter_fiche)
        layout.addWidget(self.btn_fiche)

        layout.addStretch()
        return layout
    
    def on_search_changed(self):
        """Appelé quand le texte de recherche change."""
        # Attendre un court délai avant de rechercher pour éviter trop de requêtes
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.load_projets)
        self._search_timer.start(500)  # 500ms de délai
    
    def get_filters(self):
        """Récupère les filtres actifs."""
        filters = {}
        
        # Statut
        statut = self.statut_filter.currentText()
        if statut and statut != "Tous":
            filters['statut'] = statut
        
        # Budget
        budget_text = self.budget_filter.currentText()
        if budget_text and budget_text != "Tous":
            if "< 100k" in budget_text:
                filters['budget_max'] = 100000
            elif "100k - 500k" in budget_text:
                filters['budget_min'] = 100000
                filters['budget_max'] = 500000
            elif "> 500k" in budget_text:
                filters['budget_min'] = 500000
        
        # Recherche
        search = self.search_edit.text().strip()
        if search:
            filters['search'] = search
        
        return filters if filters else None
    
    def load_projets(self):
        """Charge les projets depuis la base de données."""
        try:
            # Récupérer les filtres
            filters = self.get_filters()
            
            # Charger les projets
            projets = self.projet_service.get_all(filters)
            
            # Mettre à jour le tableau
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for row_idx, projet in enumerate(projets):
                self.table.insertRow(row_idx)
                
                # Code
                code_item = QTableWidgetItem(projet['code'] or '')
                code_item.setData(Qt.UserRole, projet['id'])
                self.table.setItem(row_idx, 0, code_item)
                
                # Nom
                nom_item = QTableWidgetItem(projet['nom'] or '')
                self.table.setItem(row_idx, 1, nom_item)
                
                # Budget Initial (use explicit None check to handle 0 as valid value)
                budget_initial = safe_get(projet, 'budget_initial')
                budget_estime = safe_get(projet, 'budget_estime')
                budget = budget_initial if budget_initial is not None else (budget_estime or 0)
                budget_item = QTableWidgetItem(f"{budget:,.0f} €")
                budget_item.setData(Qt.UserRole, budget)
                budget_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_idx, 2, budget_item)
                
                # Date début
                date_debut = safe_get(projet, 'date_debut', '')
                date_item = QTableWidgetItem(date_debut or '')
                self.table.setItem(row_idx, 3, date_item)
                
                # Date fin prévue
                date_fin = safe_get(projet, 'date_fin_prevue', '')
                date_fin_item = QTableWidgetItem(date_fin or '')
                self.table.setItem(row_idx, 4, date_fin_item)
                
                # Statut (badge coloré)
                statut = safe_get(projet, 'statut', '')
                statut_item = QTableWidgetItem(statut)
                statut_item.setTextAlignment(Qt.AlignCenter)
                
                # Couleur selon le statut
                if statut == 'ACTIF':
                    statut_item.setBackground(QBrush(QColor(144, 238, 144)))  # Vert clair
                elif statut == 'EN_ATTENTE':
                    statut_item.setBackground(QBrush(QColor(255, 215, 0)))  # Jaune
                elif statut == 'TERMINE':
                    statut_item.setBackground(QBrush(QColor(173, 216, 230)))  # Bleu clair
                elif statut == 'ANNULE':
                    statut_item.setBackground(QBrush(QColor(255, 182, 193)))  # Rouge clair
                
                self.table.setItem(row_idx, 5, statut_item)
                
                # Avancement (barre de progression)
                avancement = safe_get(projet, 'avancement', 0) or 0
                progress_widget = QWidget()
                progress_layout = QHBoxLayout(progress_widget)
                progress_layout.setContentsMargins(5, 2, 5, 2)
                
                progress_bar = QProgressBar()
                progress_bar.setMaximum(100)
                progress_bar.setValue(int(avancement))
                progress_bar.setFormat(f"{avancement}%")
                progress_bar.setTextVisible(True)
                progress_layout.addWidget(progress_bar)
                
                self.table.setCellWidget(row_idx, 6, progress_widget)
                
                # Responsable
                responsable = safe_get(projet, 'responsable_nom', '') or safe_get(projet, 'chef_projet_nom', '') or ''
                responsable_item = QTableWidgetItem(responsable)
                self.table.setItem(row_idx, 7, responsable_item)
            
            self.table.setSortingEnabled(True)
            
            # Mettre à jour les KPI
            self.update_kpi()
            
            logger.info(f"{len(projets)} projet(s) chargé(s)")
        
        except Exception as e:
            logger.error(f"Erreur chargement projets: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les projets:\n{e}")
    
    def update_kpi(self):
        """Met à jour les indicateurs KPI."""
        try:
            stats = self.projet_service.get_stats()
            
            self.kpi_total.setText(f"Total: {stats.get('total', 0)}")
            self.kpi_actifs.setText(f"Actifs: {stats.get('actifs', 0)}")
            self.kpi_attente.setText(f"En attente: {stats.get('en_attente', 0)}")
            self.kpi_termines.setText(f"Terminés: {stats.get('termines', 0)}")
            
            budget_total = stats.get('budget_total', 0)
            self.kpi_budget.setText(f"Budget total: {budget_total:,.0f} €")
        
        except Exception as e:
            logger.error(f"Erreur mise à jour KPI: {e}")
    
    def create_projet(self):
        """Ouvre le dialogue de création de projet."""
        try:
            dialog = ProjetDialog(self)
            if dialog.exec_():
                self.load_projets()
                QMessageBox.information(self, "Succès", "Projet créé avec succès !")
        except Exception as e:
            logger.error(f"Erreur création projet: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de créer le projet:\n{e}")
    
    def edit_projet(self):
        """Ouvre le dialogue d'édition du projet sélectionné."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un projet.")
                return
            
            # Récupérer l'ID du projet
            projet_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            
            # Charger le projet complet
            projet = self.projet_service.get_by_id(projet_id)
            if not projet:
                QMessageBox.warning(self, "Erreur", "Projet introuvable.")
                return
            
            # Ouvrir le dialogue
            dialog = ProjetDialog(self, projet)
            if dialog.exec_():
                self.load_projets()
                QMessageBox.information(self, "Succès", "Projet modifié avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur édition projet: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de modifier le projet:\n{e}")
    
    def exporter_fiche(self):
        """Exporte la fiche Word du projet sélectionné."""
        import os, sys
        from pathlib import Path
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Attention", "Sélectionnez un projet.")
                return
            projet_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            from app.services.fiche_projet_service import generer_fiche_depuis_id
            out_dir = str(Path(__file__).parent.parent.parent)
            path = generer_fiche_depuis_id(projet_id, out_dir)
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "✅ Fiche générée", f"Fiche enregistrée :\n{path}")
        except Exception as e:
            logger.error(f"Erreur fiche: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Erreur", f"Impossible de générer la fiche :\n{e}")

    def delete_projet(self):
        """Supprime le projet sélectionné."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un projet.")
                return
            
            # Confirmation
            projet_nom = self.table.item(selected_row, 1).text()
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Êtes-vous sûr de vouloir supprimer le projet '{projet_nom}' ?\n\n"
                "Cette action supprimera également toutes les tâches associées.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                projet_id = self.table.item(selected_row, 0).data(Qt.UserRole)
                self.projet_service.delete(projet_id)
                self.load_projets()
                QMessageBox.information(self, "Succès", "Projet supprimé avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur suppression projet: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le projet:\n{e}")
