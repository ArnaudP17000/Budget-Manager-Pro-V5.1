"""
Dialogue de crÃ©ation/Ã©dition de contact.
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QMessageBox
)
from app.services.database_service import db_service
from app.services.contact_service import contact_service

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class ContactDialog(QDialog):
    """Dialogue de crÃ©ation/Ã©dition de contact."""
    
    def __init__(self, parent=None, contact=None):
        super().__init__(parent)
        self.contact = contact
        self.contact_id = contact['id'] if contact else None
        self.setWindowTitle("Nouveau Contact" if not contact else "Modifier Contact")
        self.setMinimumWidth(500)
        self.setup_ui()
        
        if contact:
            self.load_contact_data()
        
        # GÃ©rer l'affichage conditionnel des champs
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        self.on_type_changed(self.type_combo.currentText())
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Nom
        self.nom_edit = QLineEdit()
        self.nom_edit.setPlaceholderText("Nom")
        form.addRow("Nom *:", self.nom_edit)
        
        # PrÃ©nom
        self.prenom_edit = QLineEdit()
        self.prenom_edit.setPlaceholderText("Prénom")
        form.addRow("Prénom *:", self.prenom_edit)
        
        # Fonction
        self.fonction_edit = QLineEdit()
        self.fonction_edit.setPlaceholderText("Fonction ou poste")
        form.addRow("Fonction:", self.fonction_edit)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["ELU", "INTERNE", "EXTERNE", "DIRECTION", "PRESTATAIRE", "FOURNISSEUR", "AMO"])
        self.type_combo.setCurrentIndex(1)  # DIRECTION par défaut
        form.addRow("Type *:", self.type_combo)
        
        # Téléphone
        self.telephone_edit = QLineEdit()
        self.telephone_edit.setPlaceholderText("01 23 45 67 89")
        form.addRow("Téléphone:", self.telephone_edit)
        
        # Email
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("contact@exemple.fr")
        form.addRow("Email:", self.email_edit)
        
        # Service (pour DIRECTION et ELU)
        self.service_combo = QComboBox()
        self.service_combo.addItem("-- Aucun --", None)
        try:
            services = db_service.fetch_all(
                "SELECT id, code, nom FROM services ORDER BY code"
            )
            for service in services:
                label = f"{service['code']} - {service['nom']}"
                self.service_combo.addItem(label, service['id'])
        except Exception as e:
            logger.error(f"Erreur chargement services: {e}")
        form.addRow("Service:", self.service_combo)
        
        # Organisation (saisie libre pour EXTERNE/AMO)
        self.organisation_edit = QLineEdit()
        self.organisation_edit.setPlaceholderText("Nom de l'organisation externe")
        form.addRow("Organisation:", self.organisation_edit)

        # Fournisseur (combo pour PRESTATAIRE/FOURNISSEUR)
        self.fournisseur_combo = QComboBox()
        self.fournisseur_combo.addItem("-- Choisir un fournisseur --", None)
        try:
            fournisseurs = db_service.fetch_all(
                "SELECT id, nom FROM fournisseurs WHERE actif=1 ORDER BY nom"
            ) or []
            for f in fournisseurs:
                self.fournisseur_combo.addItem(f['nom'], f['id'])
        except Exception as e:
            logger.error(f"Chargement fournisseurs : {e}")
        self.fournisseur_combo.hide()
        form.addRow("Fournisseur:", self.fournisseur_combo)
        # Garder une référence à la row du form pour show/hide le label
        self._fourn_label = form.labelForField(self.fournisseur_combo)
        
        layout.addLayout(form)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def on_type_changed(self, type_text):
        """Affiche/masque les champs selon le type."""
        # Service visible pour agents internes
        self.service_combo.setEnabled(type_text in ['ELU', 'INTERNE', 'DIRECTION'])

        # PRESTATAIRE / FOURNISSEUR → combo fournisseurs
        use_fourn = type_text in ('PRESTATAIRE', 'FOURNISSEUR')
        self.fournisseur_combo.setVisible(use_fourn)
        if self._fourn_label:
            self._fourn_label.setVisible(use_fourn)

        # EXTERNE / AMO → saisie libre organisation
        use_org = type_text in ('EXTERNE', 'AMO')
        self.organisation_edit.setVisible(use_org)
        self.organisation_edit.setEnabled(use_org)
        org_label = None
        try:
            from PyQt5.QtWidgets import QFormLayout
            form = self.organisation_edit.parent().layout()
            if isinstance(form, QFormLayout):
                org_label = form.labelForField(self.organisation_edit)
        except Exception:
            pass
        if org_label:
            org_label.setVisible(use_org)
    
    def load_contact_data(self):
        """Charge les donnÃ©es du contact."""
        try:
            if not self.contact:
                return
            
            self.nom_edit.setText(safe_get(self.contact, 'nom', '') or '')
            self.prenom_edit.setText(safe_get(self.contact, 'prenom', '') or '')
            self.fonction_edit.setText(safe_get(self.contact, 'fonction', '') or '')
            
            type_val = safe_get(self.contact, 'type', 'DIRECTION') or 'DIRECTION'
            index = self.type_combo.findText(type_val)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            self.telephone_edit.setText(safe_get(self.contact, 'telephone', '') or '')
            self.email_edit.setText(safe_get(self.contact, 'email', '') or '')
            
            # Service
            if safe_get(self.contact, 'service_id'):
                for i in range(self.service_combo.count()):
                    if self.service_combo.itemData(i) == self.contact['service_id']:
                        self.service_combo.setCurrentIndex(i)
                        break
            
            type_val = safe_get(self.contact, 'type', '') or ''
            if type_val in ('PRESTATAIRE', 'FOURNISSEUR'):
                fourn_id = safe_get(self.contact, 'fournisseur_id')
                org = safe_get(self.contact, 'organisation', '') or ''
                if fourn_id:
                    idx = self.fournisseur_combo.findData(fourn_id)
                    if idx >= 0:
                        self.fournisseur_combo.setCurrentIndex(idx)
                elif org:
                    idx = self.fournisseur_combo.findText(org)
                    if idx >= 0:
                        self.fournisseur_combo.setCurrentIndex(idx)
            else:
                self.organisation_edit.setText(safe_get(self.contact, 'organisation', '') or '')
        
        except Exception as e:
            logger.error(f"Erreur chargement contact: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger le contact:\n{e}")
    
    def accept_dialog(self):
        """Valide et enregistre le contact."""
        try:
            # Validation
            if not self.nom_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le nom est obligatoire.")
                self.nom_edit.setFocus()
                return
            
            if not self.prenom_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le prÃ©nom est obligatoire.")
                self.prenom_edit.setFocus()
                return
            
            # PrÃ©parer les donnÃ©es
            data = {
                'nom': self.nom_edit.text().strip(),
                'prenom': self.prenom_edit.text().strip(),
                'fonction': self.fonction_edit.text().strip() or None,
                'type': self.type_combo.currentText(),
                'telephone': self.telephone_edit.text().strip() or None,
                'email': self.email_edit.text().strip() or None,
            }
            
            # Service ou organisation selon le type
            if self.type_combo.currentText() in ['ELU', 'DIRECTION']:
                service_id = self.service_combo.currentData()
                if service_id:
                    data['service_id'] = service_id
            else:
                type_val = self.type_combo.currentText()
                if type_val in ('PRESTATAIRE', 'FOURNISSEUR'):
                    data['organisation'] = self.fournisseur_combo.currentText() or None
                    data['fournisseur_id'] = self.fournisseur_combo.currentData()
                else:
                    data['organisation'] = self.organisation_edit.text().strip() or None
                    data['fournisseur_id'] = None
            
            # Sauvegarder
            if self.contact_id:
                contact_service.update(self.contact_id, data)
                logger.info(f"Contact {self.contact_id} mis Ã  jour")
            else:
                self.contact_id = contact_service.create(data)
                logger.info(f"Contact crÃ©Ã©: {self.contact_id}")
            
            self.accept()
        
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            logger.error(f"Erreur sauvegarde contact: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le contact:\n{e}")
    
    def get_data(self):
        """Retourne les donnÃ©es du formulaire (pour compatibilitÃ©)."""
        return {
            'id': self.contact_id,
            'nom': self.nom_edit.text().strip(),
            'prenom': self.prenom_edit.text().strip(),
        }
