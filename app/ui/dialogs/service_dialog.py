"""
Dialogue de création/édition de service.
"""
import logging
from PyQt5.QtWidgets import (
    QHBoxLayout, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QMessageBox, QPushButton
)
from PyQt5.QtCore import Qt
from app.services.database_service import db_service
from app.services.service_service import service_service

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class ServiceDialog(QDialog):
    """Dialogue de création/édition de service."""
    
    def __init__(self, parent=None, service=None):
        super().__init__(parent)
        self.service = service
        self.service_id = service['id'] if service else None
        self.setWindowTitle("Nouveau Service" if not service else "Modifier Service")
        self.setMinimumWidth(500)
        self.setup_ui()
        
        if service:
            self.load_service_data()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Code
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Code du service (ex: DSI)")
        form.addRow("Code *:", self.code_edit)
        
        # Nom
        self.nom_edit = QLineEdit()
        self.nom_edit.setPlaceholderText("Nom du service")
        form.addRow("Nom *:", self.nom_edit)
        
        # Responsable — tous les contacts + bouton création
        resp_row = QHBoxLayout()
        self.responsable_combo = QComboBox()
        self.responsable_combo.setEditable(True)
        self.responsable_combo.setInsertPolicy(QComboBox.NoInsert)
        self.responsable_combo.completer().setFilterMode(Qt.MatchContains)
        self.responsable_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.responsable_combo.addItem("-- Aucun --", None)
        try:
            contacts = db_service.fetch_all(
                "SELECT id, nom, prenom, fonction FROM contacts ORDER BY nom, prenom"
            ) or []
            for c in contacts:
                label = f"{c['prenom'] or ''} {c['nom']}".strip()
                if c['fonction']:
                    label += f" ({c['fonction']})"
                self.responsable_combo.addItem(label, c['id'])
        except Exception as e:
            logger.error(f"Erreur chargement contacts: {e}")
        self.responsable_combo.lineEdit().setPlaceholderText("Tapez un nom...")
        resp_row.addWidget(self.responsable_combo)
        btn_new_resp = QPushButton("➕")
        btn_new_resp.setFixedWidth(32)
        btn_new_resp.setToolTip("Nouveau contact")
        btn_new_resp.clicked.connect(self._nouveau_responsable)
        resp_row.addWidget(btn_new_resp)
        form.addRow("Responsable:", resp_row)
        
        # Service parent (optionnel)
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("-- Aucun (service racine) --", None)
        try:
            services = db_service.fetch_all(
                "SELECT id, code, nom FROM services ORDER BY code"
            )
            for serv in services:
                # Ne pas afficher le service lui-même dans la liste des parents
                if not self.service_id or serv['id'] != self.service_id:
                    label = f"{serv['code']} - {serv['nom']}"
                    self.parent_combo.addItem(label, serv['id'])
        except Exception as e:
            logger.error(f"Erreur chargement services: {e}")
        form.addRow("Service parent:", self.parent_combo)
        
        layout.addLayout(form)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_service_data(self):
        """Charge les données du service."""
        try:
            if not self.service:
                return
            
            self.code_edit.setText(safe_get(self.service, 'code', '') or '')
            self.nom_edit.setText(safe_get(self.service, 'nom', '') or '')
            
            # Responsable
            if safe_get(self.service, 'responsable_id'):
                for i in range(self.responsable_combo.count()):
                    if self.responsable_combo.itemData(i) == self.service['responsable_id']:
                        self.responsable_combo.setCurrentIndex(i)
                        break
            
            # Parent
            if safe_get(self.service, 'parent_id'):
                for i in range(self.parent_combo.count()):
                    if self.parent_combo.itemData(i) == self.service['parent_id']:
                        self.parent_combo.setCurrentIndex(i)
                        break
        
        except Exception as e:
            logger.error(f"Erreur chargement service: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger le service:\n{e}")
    
    def accept_dialog(self):
        """Valide et enregistre le service."""
        try:
            # Validation
            if not self.code_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le code du service est obligatoire.")
                self.code_edit.setFocus()
                return
            
            if not self.nom_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le nom du service est obligatoire.")
                self.nom_edit.setFocus()
                return
            
            # Préparer les données
            data = {
                'code': self.code_edit.text().strip().upper(),
                'nom': self.nom_edit.text().strip(),
            }
            
            # Responsable
            responsable_id = self.responsable_combo.currentData()
            if responsable_id:
                data['responsable_id'] = responsable_id
            
            # Parent
            parent_id = self.parent_combo.currentData()
            if parent_id:
                data['parent_id'] = parent_id
            
            # Sauvegarder
            if self.service_id:
                service_service.update(self.service_id, data)
                logger.info(f"Service {self.service_id} mis à jour")
            else:
                self.service_id = service_service.create(data)
                logger.info(f"Service créé: {self.service_id}")
            
            self.accept()
        
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            logger.error(f"Erreur sauvegarde service: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le service:\n{e}")
    
    def _nouveau_responsable(self):
        """Crée un nouveau contact rapide comme responsable."""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Nouveau responsable")
        dlg.setMinimumWidth(320)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        nom_e    = QLineEdit(); nom_e.setPlaceholderText("NOM")
        prenom_e = QLineEdit(); prenom_e.setPlaceholderText("Prénom")
        fonc_e   = QLineEdit(); fonc_e.setPlaceholderText("ex: Chef de service")
        email_e  = QLineEdit()
        form.addRow("Nom *:",    nom_e)
        form.addRow("Prénom:",   prenom_e)
        form.addRow("Fonction:", fonc_e)
        form.addRow("Email:",    email_e)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec_() != QDialog.Accepted or not nom_e.text().strip():
            return
        try:
            conn = db_service.get_connection()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO contacts (nom, prenom, fonction, email, type, date_creation)"
                " VALUES (?,?,?,?,'INTERNE',datetime('now'))",
                (nom_e.text().strip().upper(),
                 prenom_e.text().strip(),
                 fonc_e.text().strip(),
                 email_e.text().strip()))
            conn.commit()
            new_id = cur.lastrowid
            label  = f"{prenom_e.text().strip()} {nom_e.text().strip().upper()}"
            if fonc_e.text().strip():
                label += f" ({fonc_e.text().strip()})"
            self.responsable_combo.addItem(label, new_id)
            self.responsable_combo.setCurrentIndex(self.responsable_combo.count() - 1)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Erreur", str(e))

    def get_data(self):
        """Retourne les données du formulaire (pour compatibilité)."""
        return {
            'id': self.service_id,
            'code': self.code_edit.text().strip(),
            'nom': self.nom_edit.text().strip(),
        }
