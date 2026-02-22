"""
Vue de gestion des tâches.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QGroupBox, QMessageBox,
    QHeaderView, QCheckBox, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush
from app.services.tache_service import tache_service
from app.services.projet_service import projet_service
from app.ui.dialogs.tache_dialog import TacheDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class TacheView(QWidget):
    """Vue de gestion des tâches."""
    
    def __init__(self):
        super().__init__()
        self.tache_service = tache_service
        self.projet_service = projet_service
        self.init_ui()
        # Charger les tâches après un court délai
        QTimer.singleShot(100, self.load_taches)
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel("✅ Gestion des Tâches")
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
            "☐", "Titre", "Projet", "Priorité", "Échéance", 
            "Statut", "Assigné à", "Avancement"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_tache)
        layout.addWidget(self.table)
        
        # Boutons d'action
        buttons_layout = self.create_action_buttons()
        layout.addLayout(buttons_layout)
    
    def create_filters(self):
        """Crée la section des filtres."""
        group = QGroupBox("🔍 Filtres")
        layout = QHBoxLayout()
        
        # Filtre projet
        layout.addWidget(QLabel("Projet:"))
        self.projet_filter = QComboBox()
        self.projet_filter.addItem("Tous", None)
        try:
            projets = self.projet_service.get_all()
            for projet in projets:
                label = f"{projet['code']} - {projet['nom']}" if safe_get(projet, 'code') else projet['nom']
                self.projet_filter.addItem(label, projet['id'])
        except Exception as e:
            logger.error(f"Erreur chargement projets pour filtre: {e}")
        self.projet_filter.currentIndexChanged.connect(self.load_taches)
        layout.addWidget(self.projet_filter)
        
        # Filtre priorité
        layout.addWidget(QLabel("Priorité:"))
        self.priorite_filter = QComboBox()
        self.priorite_filter.addItems([
            "Toutes",
            "CRITIQUE",
            "HAUTE",
            "MOYENNE",
            "BASSE"
        ])
        self.priorite_filter.currentTextChanged.connect(self.load_taches)
        layout.addWidget(self.priorite_filter)
        
        # Filtre statut
        layout.addWidget(QLabel("Statut:"))
        self.statut_filter = QComboBox()
        self.statut_filter.addItems([
            "Tous",
            "A_FAIRE",
            "EN_COURS",
            "BLOQUE",
            "TERMINE"
        ])
        self.statut_filter.currentTextChanged.connect(self.load_taches)
        layout.addWidget(self.statut_filter)
        
        # Recherche
        layout.addWidget(QLabel("Recherche:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Titre, description...")
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
        self.kpi_a_faire = QLabel("À faire: 0")
        self.kpi_en_cours = QLabel("En cours: 0")
        self.kpi_bloquees = QLabel("Bloquées: 0")
        self.kpi_terminees = QLabel("Terminées: 0")
        self.kpi_retard = QLabel("En retard: 0")
        
        for kpi in [self.kpi_total, self.kpi_a_faire, self.kpi_en_cours,
                    self.kpi_bloquees, self.kpi_terminees, self.kpi_retard]:
            kpi.setStyleSheet("font-weight: bold; padding: 5px 10px;")
            layout.addWidget(kpi)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self):
        """Crée les boutons d'action."""
        layout = QHBoxLayout()
        
        self.btn_nouvelle = QPushButton("➕ Nouvelle")
        self.btn_nouvelle.clicked.connect(self.create_tache)
        layout.addWidget(self.btn_nouvelle)
        
        self.btn_modifier = QPushButton("✏️ Modifier")
        self.btn_modifier.clicked.connect(self.edit_tache)
        layout.addWidget(self.btn_modifier)
        
        self.btn_terminer = QPushButton("✅ Terminer")
        self.btn_terminer.clicked.connect(self.complete_tache)
        layout.addWidget(self.btn_terminer)
        
        self.btn_supprimer = QPushButton("🗑️ Supprimer")
        self.btn_supprimer.clicked.connect(self.delete_tache)
        layout.addWidget(self.btn_supprimer)
        
        self.btn_rafraichir = QPushButton("🔄 Rafraîchir")
        self.btn_rafraichir.clicked.connect(self.load_taches)
        layout.addWidget(self.btn_rafraichir)
        
        layout.addStretch()
        return layout
    
    def on_search_changed(self):
        """Appelé quand le texte de recherche change."""
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.load_taches)
        self._search_timer.start(500)
    
    def get_filters(self):
        """Récupère les filtres actifs."""
        filters = {}
        
        # Projet
        projet_id = self.projet_filter.currentData()
        if projet_id:
            filters['projet_id'] = projet_id
        
        # Priorité
        priorite = self.priorite_filter.currentText()
        if priorite and priorite != "Toutes":
            filters['priorite'] = priorite
        
        # Statut
        statut = self.statut_filter.currentText()
        if statut and statut != "Tous":
            filters['statut'] = statut
        
        # Recherche
        search = self.search_edit.text().strip()
        if search:
            filters['search'] = search
        
        return filters if filters else None
    
    def load_taches(self):
        """Charge les tâches depuis la base de données."""
        try:
            # Récupérer les filtres
            filters = self.get_filters()
            
            # Charger les tâches
            taches = self.tache_service.get_all(filters)
            
            # Mettre à jour le tableau
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for row_idx, tache in enumerate(taches):
                self.table.insertRow(row_idx)
                
                # Checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(safe_get(tache, 'statut') == 'TERMINE')
                # Note: state parameter is intentionally unused, required by Qt signal
                checkbox.stateChanged.connect(lambda state, row=row_idx: self.toggle_tache_status(row))
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row_idx, 0, checkbox_widget)
                
                # Titre
                titre_item = QTableWidgetItem(tache['titre'] or '')
                titre_item.setData(Qt.UserRole, tache['id'])
                self.table.setItem(row_idx, 1, titre_item)
                
                # Projet
                projet_text = safe_get(tache, 'projet_code', '') or ''
                if safe_get(tache, 'projet_nom'):
                    if projet_text:
                        projet_text += ' - '
                    projet_text += tache['projet_nom']
                projet_item = QTableWidgetItem(projet_text)
                self.table.setItem(row_idx, 2, projet_item)
                
                # Priorité (badge coloré)
                priorite = safe_get(tache, 'priorite', '')
                priorite_item = QTableWidgetItem(priorite)
                priorite_item.setTextAlignment(Qt.AlignCenter)
                
                if priorite == 'CRITIQUE':
                    priorite_item.setBackground(QBrush(QColor(255, 99, 71)))  # Rouge
                    priorite_item.setForeground(QBrush(QColor(255, 255, 255)))
                elif priorite == 'HAUTE':
                    priorite_item.setBackground(QBrush(QColor(255, 165, 0)))  # Orange
                elif priorite == 'MOYENNE':
                    priorite_item.setBackground(QBrush(QColor(255, 215, 0)))  # Jaune
                elif priorite == 'BASSE':
                    priorite_item.setBackground(QBrush(QColor(144, 238, 144)))  # Vert clair
                
                self.table.setItem(row_idx, 3, priorite_item)
                
                # Échéance (colorier en rouge si dépassée)
                from datetime import datetime
                date_echeance = safe_get(tache, 'date_echeance', '')
                echeance_item = QTableWidgetItem(date_echeance or '')
                # Highlight overdue tasks in red
                if date_echeance and safe_get(tache, 'statut') not in ('TERMINE', 'ANNULE'):
                    try:
                        echeance_date = datetime.strptime(date_echeance, '%Y-%m-%d').date()
                        if echeance_date < datetime.now().date():
                            echeance_item.setForeground(QBrush(QColor(255, 0, 0)))  # Rouge
                            echeance_item.setBackground(QBrush(QColor(255, 230, 230)))  # Rouge clair
                    except ValueError:
                        pass  # Invalid date format, skip coloring
                self.table.setItem(row_idx, 4, echeance_item)
                
                # Statut
                statut = safe_get(tache, 'statut', '')
                statut_item = QTableWidgetItem(statut)
                statut_item.setTextAlignment(Qt.AlignCenter)
                
                if statut == 'TERMINE':
                    statut_item.setBackground(QBrush(QColor(173, 216, 230)))  # Bleu clair
                elif statut == 'EN_COURS':
                    statut_item.setBackground(QBrush(QColor(144, 238, 144)))  # Vert clair
                elif statut == 'BLOQUE':
                    statut_item.setBackground(QBrush(QColor(255, 182, 193)))  # Rouge clair
                
                self.table.setItem(row_idx, 5, statut_item)
                
                # Assigné à
                assignee = safe_get(tache, 'assignee_nom', '') or ''
                assignee_item = QTableWidgetItem(assignee)
                self.table.setItem(row_idx, 6, assignee_item)
                
                # Avancement
                avancement = safe_get(tache, 'avancement', 0) or 0
                progress_widget = QWidget()
                progress_layout = QHBoxLayout(progress_widget)
                progress_layout.setContentsMargins(5, 2, 5, 2)
                
                progress_bar = QProgressBar()
                progress_bar.setMaximum(100)
                progress_bar.setValue(int(avancement))
                progress_bar.setFormat(f"{avancement}%")
                progress_bar.setTextVisible(True)
                progress_layout.addWidget(progress_bar)
                
                self.table.setCellWidget(row_idx, 7, progress_widget)
                
                # Griser la ligne si terminée
                if statut == 'TERMINE':
                    for col in range(1, 7):
                        item = self.table.item(row_idx, col)
                        if item:
                            item.setForeground(QBrush(QColor(128, 128, 128)))
            
            self.table.setSortingEnabled(True)
            
            # Mettre à jour les KPI
            self.update_kpi()
            
            logger.info(f"{len(taches)} tâche(s) chargée(s)")
        
        except Exception as e:
            logger.error(f"Erreur chargement tâches: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les tâches:\n{e}")
    
    def update_kpi(self):
        """Met à jour les indicateurs KPI."""
        try:
            stats = self.tache_service.get_stats()
            
            self.kpi_total.setText(f"Total: {stats.get('total', 0)}")
            self.kpi_a_faire.setText(f"À faire: {stats.get('a_faire', 0)}")
            self.kpi_en_cours.setText(f"En cours: {stats.get('en_cours', 0)}")
            self.kpi_bloquees.setText(f"Bloquées: {stats.get('bloquees', 0)}")
            self.kpi_terminees.setText(f"Terminées: {stats.get('terminees', 0)}")
            self.kpi_retard.setText(f"En retard: {stats.get('en_retard', 0)}")
        
        except Exception as e:
            logger.error(f"Erreur mise à jour KPI: {e}")
    
    def toggle_tache_status(self, row):
        """Bascule le statut d'une tâche via la checkbox."""
        try:
            tache_id = self.table.item(row, 1).data(Qt.UserRole)
            checkbox_widget = self.table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox.isChecked():
                self.tache_service.update(tache_id, {'statut': 'TERMINE', 'avancement': 100})
            else:
                self.tache_service.update(tache_id, {'statut': 'A_FAIRE', 'avancement': 0})
            
            self.load_taches()
        
        except Exception as e:
            logger.error(f"Erreur changement statut tâche: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de changer le statut:\n{e}")
    
    def create_tache(self):
        """Ouvre le dialogue de création de tâche."""
        try:
            dialog = TacheDialog(self)
            if dialog.exec_():
                self.load_taches()
                QMessageBox.information(self, "Succès", "Tâche créée avec succès !")
        except Exception as e:
            logger.error(f"Erreur création tâche: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de créer la tâche:\n{e}")
    
    def edit_tache(self):
        """Ouvre le dialogue d'édition de la tâche sélectionnée."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner une tâche.")
                return
            
            tache_id = self.table.item(selected_row, 1).data(Qt.UserRole)
            tache = self.tache_service.get_by_id(tache_id)
            if not tache:
                QMessageBox.warning(self, "Erreur", "Tâche introuvable.")
                return
            
            dialog = TacheDialog(self, tache)
            if dialog.exec_():
                self.load_taches()
                QMessageBox.information(self, "Succès", "Tâche modifiée avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur édition tâche: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de modifier la tâche:\n{e}")
    
    def complete_tache(self):
        """Marque la tâche sélectionnée comme terminée."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner une tâche.")
                return
            
            tache_id = self.table.item(selected_row, 1).data(Qt.UserRole)
            self.tache_service.update(tache_id, {'statut': 'TERMINE', 'avancement': 100})
            self.load_taches()
            QMessageBox.information(self, "Succès", "Tâche marquée comme terminée !")
        
        except Exception as e:
            logger.error(f"Erreur complétion tâche: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible de terminer la tâche:\n{e}")
    
    def delete_tache(self):
        """Supprime la tâche sélectionnée."""
        try:
            selected_row = self.table.currentRow()
            if selected_row < 0:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner une tâche.")
                return
            
            tache_titre = self.table.item(selected_row, 1).text()
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Êtes-vous sûr de vouloir supprimer la tâche '{tache_titre}' ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                tache_id = self.table.item(selected_row, 1).data(Qt.UserRole)
                self.tache_service.delete(tache_id)
                self.load_taches()
                QMessageBox.information(self, "Succès", "Tâche supprimée avec succès !")
        
        except Exception as e:
            logger.error(f"Erreur suppression tâche: {e}", exc_info=True)
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer la tâche:\n{e}")
