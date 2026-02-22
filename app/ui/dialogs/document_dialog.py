"""
Dialogue d'ajout de document projet.
"""
import logging
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QMessageBox, QPushButton, QFileDialog, QHBoxLayout
)
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class DocumentDialog(QDialog):
    """Dialogue d'ajout de document à un projet."""
    
    def __init__(self, parent=None, projet_id=None):
        super().__init__(parent)
        self.projet_id = projet_id
        self.selected_file_path = None
        self.setWindowTitle("Ajouter un document")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Type de document
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Cahier des charges",
            "Rapport",
            "PV de réunion",
            "Fiche technique",
            "Contrat",
            "Facture",
            "Présentation",
            "Autre"
        ])
        form.addRow("Type *:", self.type_combo)
        
        # Sélection de fichier
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Aucun fichier sélectionné")
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Parcourir...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        form.addRow("Fichier *:", file_layout)
        
        layout.addLayout(form)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def browse_file(self):
        """Ouvre un dialogue de sélection de fichier."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier",
            "",
            "Tous les fichiers (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            self.file_path_edit.setText(os.path.basename(file_path))
    
    def accept_dialog(self):
        """Valide et enregistre le document."""
        try:
            if not self.selected_file_path:
                QMessageBox.warning(self, "Validation", "Veuillez sélectionner un fichier.")
                return
            
            if not self.projet_id:
                QMessageBox.warning(self, "Erreur", "Aucun projet sélectionné.")
                return
            
            # Préparer les données
            file_name = os.path.basename(self.selected_file_path)
            file_size = os.path.getsize(self.selected_file_path)
            
            data = {
                'projet_id': self.projet_id,
                'nom_fichier': file_name,
                'type_document': self.type_combo.currentText(),
                'chemin_fichier': self.selected_file_path,
                'taille': file_size,
            }
            
            # Sauvegarder
            doc_id = db_service.insert('projet_documents', data)
            logger.info(f"Document ajouté: {doc_id} - {file_name}")
            
            self.accept()
        
        except Exception as e:
            logger.error(f"Erreur ajout document: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter le document:\n{e}")
    
    def get_data(self):
        """Retourne les données du formulaire (pour compatibilité)."""
        return {
            'nom_fichier': os.path.basename(self.selected_file_path) if self.selected_file_path else '',
            'type_document': self.type_combo.currentText(),
        }
