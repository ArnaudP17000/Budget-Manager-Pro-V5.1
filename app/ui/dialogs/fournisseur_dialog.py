"""
Dialogue de création/édition de fournisseur.
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDialogButtonBox, QMessageBox, QLabel, QGroupBox
)
from app.services.database_service import db_service
from app.services.fournisseur_service import fournisseur_service

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class FournisseurDialog(QDialog):
    """Dialogue de création/édition de fournisseur."""
    
    def __init__(self, parent=None, fournisseur=None):
        super().__init__(parent)
        self.fournisseur = fournisseur
        self.fournisseur_id = fournisseur['id'] if fournisseur else None
        self.setWindowTitle("Nouveau Fournisseur" if not fournisseur else "Modifier Fournisseur")
        self.setMinimumWidth(600)
        self.setup_ui()
        
        if fournisseur:
            self.load_fournisseur_data()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Nom
        self.nom_edit = QLineEdit()
        self.nom_edit.setPlaceholderText("Nom du fournisseur")
        form.addRow("Nom *:", self.nom_edit)
        
        # Statut
        self.statut_combo = QComboBox()
        self.statut_combo.addItems(["ACTIF", "INACTIF"])
        form.addRow("Statut *:", self.statut_combo)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes ou remarques")
        self.notes_edit.setMaximumHeight(100)
        form.addRow("Notes:", self.notes_edit)
        
        layout.addLayout(form)
        
        # Section historique (affichage uniquement)
        if self.fournisseur_id:
            history_group = QGroupBox("Historique")
            history_layout = QVBoxLayout(history_group)
            
            self.contrats_label = QLabel("Chargement...")
            self.bc_label = QLabel("Chargement...")
            history_layout.addWidget(self.contrats_label)
            history_layout.addWidget(self.bc_label)
            
            layout.addWidget(history_group)
            
            # Charger l'historique
            self.load_historique()
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_fournisseur_data(self):
        """Charge les données du fournisseur."""
        try:
            if not self.fournisseur:
                return
            
            self.nom_edit.setText(safe_get(self.fournisseur, 'nom', '') or '')
            
            statut = safe_get(self.fournisseur, 'statut', 'ACTIF') or 'ACTIF'
            index = self.statut_combo.findText(statut)
            if index >= 0:
                self.statut_combo.setCurrentIndex(index)
            
            self.notes_edit.setPlainText(safe_get(self.fournisseur, 'notes', '') or '')
        
        except Exception as e:
            logger.error(f"Erreur chargement fournisseur: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger le fournisseur:\n{e}")
    
    def load_historique(self):
        """Charge l'historique des contrats et BC."""
        try:
            contrats = fournisseur_service.get_contrats(self.fournisseur_id)
            bc = fournisseur_service.get_bons_commande(self.fournisseur_id)
            
            self.contrats_label.setText(f"📄 Contrats: {len(contrats)}")
            self.bc_label.setText(f"🛒 Bons de commande: {len(bc)}")
        except Exception as e:
            logger.error(f"Erreur chargement historique: {e}")
            self.contrats_label.setText("📄 Contrats: Erreur")
            self.bc_label.setText("🛒 Bons de commande: Erreur")
    
    def accept_dialog(self):
        """Valide et enregistre le fournisseur."""
        try:
            # Validation
            if not self.nom_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le nom du fournisseur est obligatoire.")
                self.nom_edit.setFocus()
                return
            
            # Préparer les données
            data = {
                'nom': self.nom_edit.text().strip(),
                'statut': self.statut_combo.currentText(),
                'notes': self.notes_edit.toPlainText().strip() or None,
            }
            
            # Sauvegarder
            if self.fournisseur_id:
                fournisseur_service.update(self.fournisseur_id, data)
                logger.info(f"Fournisseur {self.fournisseur_id} mis à jour")
            else:
                self.fournisseur_id = fournisseur_service.create(data)
                logger.info(f"Fournisseur créé: {self.fournisseur_id}")
            
            self.accept()
        
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            logger.error(f"Erreur sauvegarde fournisseur: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le fournisseur:\n{e}")
    
    def get_data(self):
        """Retourne les données du formulaire (pour compatibilité)."""
        return {
            'id': self.fournisseur_id,
            'nom': self.nom_edit.text().strip(),
        }
