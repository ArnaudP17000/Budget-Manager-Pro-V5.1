"""
Dialogue de création/édition de tâche.
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import QDate
from app.services.database_service import db_service
from app.services.tache_service import tache_service

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError):
        return default

logger = logging.getLogger(__name__)

class TacheDialog(QDialog):
    """Dialogue de création/édition de tâche."""
    
    def __init__(self, parent=None, tache=None, projet_obligatoire=True):
        super().__init__(parent)
        # Convertir sqlite3.Row en dict si necessaire
        if tache is not None and hasattr(tache, 'keys'):
            tache = dict(tache)
        self.tache = tache
        self.tache_id = tache.get('id') if tache else None
        self.projet_obligatoire = projet_obligatoire
        self.setWindowTitle("Nouvelle Tâche" if not tache else "Modifier Tâche")
        self.setMinimumWidth(600)
        self.setup_ui()
        
        if tache:
            self.load_tache_data()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Titre
        self.titre_edit = QLineEdit()
        self.titre_edit.setPlaceholderText("Titre de la tâche")
        form.addRow("Titre *:", self.titre_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Description détaillée")
        self.description_edit.setMaximumHeight(100)
        form.addRow("Description:", self.description_edit)
        
        # Projet
        self.projet_combo = QComboBox()
        self.projet_combo.addItem("-- Sélectionner un projet --", None)
        try:
            projets = db_service.fetch_all(
                """SELECT id, code, nom FROM projets 
                   WHERE statut IN ('ACTIF', 'EN_ATTENTE') 
                   ORDER BY nom"""
            )
            for projet in projets:
                label = f"{projet['code']} - {projet['nom']}" if projet['code'] else projet['nom']
                self.projet_combo.addItem(label, projet['id'])
        except Exception as e:
            logger.error(f"Erreur chargement projets: {e}")
        label_projet = "Projet *:" if self.projet_obligatoire else "Projet (optionnel):"
        form.addRow(label_projet, self.projet_combo)
        
        # Priorité
        self.priorite_combo = QComboBox()
        self.priorite_combo.addItems([
            "CRITIQUE",
            "HAUTE",
            "MOYENNE",
            "BASSE"
        ])
        self.priorite_combo.setCurrentIndex(2)
        form.addRow("Priorité *:", self.priorite_combo)
        
        # Statut
        self.statut_combo = QComboBox()
        self.statut_combo.addItems([
            "A_FAIRE",
            "EN_COURS",
            "BLOQUE",
            "TERMINE",
            "ANNULE"
        ])
        form.addRow("Statut *:", self.statut_combo)
        
        # Date échéance
        self.date_echeance = QDateEdit()
        self.date_echeance.setCalendarPopup(True)
        self.date_echeance.setDate(QDate.currentDate().addDays(7))
        form.addRow("Date échéance *:", self.date_echeance)
        
        # Date début
        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        form.addRow("Date début:", self.date_debut)
        
        # Date fin prévue
        self.date_fin_prevue = QDateEdit()
        self.date_fin_prevue.setCalendarPopup(True)
        self.date_fin_prevue.setDate(QDate.currentDate().addDays(7))
        form.addRow("Date fin prévue:", self.date_fin_prevue)
        
        # Assigné à
        self.assigne_combo = QComboBox()
        self.assigne_combo.addItem("-- Non assigné --", None)
        try:
            users = db_service.fetch_all(
                "SELECT id, nom, prenom FROM utilisateurs WHERE actif = 1 ORDER BY nom, prenom"
            )
            for user in users:
                self.assigne_combo.addItem(f"{user['nom']} {user['prenom']}", user['id'])
        except Exception as e:
            logger.error(f"Erreur chargement utilisateurs: {e}")
        form.addRow("Assigné à:", self.assigne_combo)
        
        # Avancement
        self.avancement_spin = QSpinBox()
        self.avancement_spin.setRange(0, 100)
        self.avancement_spin.setSuffix(" %")
        form.addRow("Avancement %:", self.avancement_spin)
        
        # Estimation heures
        self.estimation_spin = QDoubleSpinBox()
        self.estimation_spin.setRange(0, 10000)
        self.estimation_spin.setSingleStep(0.5)
        self.estimation_spin.setSuffix(" h")
        self.estimation_spin.setDecimals(1)
        form.addRow("Estimation heures:", self.estimation_spin)
        
        # Heures réelles
        self.heures_reelles_spin = QDoubleSpinBox()
        self.heures_reelles_spin.setRange(0, 10000)
        self.heures_reelles_spin.setSingleStep(0.5)
        self.heures_reelles_spin.setSuffix(" h")
        self.heures_reelles_spin.setDecimals(1)
        form.addRow("Heures réelles:", self.heures_reelles_spin)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("urgent, backend, api (séparés par virgules)")
        form.addRow("Tags:", self.tags_edit)
        
        # Commentaires
        self.commentaires_edit = QTextEdit()
        self.commentaires_edit.setPlaceholderText("Commentaires ou notes")
        self.commentaires_edit.setMaximumHeight(80)
        form.addRow("Commentaires:", self.commentaires_edit)
        
        layout.addLayout(form)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_tache_data(self):
        """Charge les données de la tâche."""
        try:
            if not self.tache:
                return
            
            self.titre_edit.setText(safe_get(self.tache, 'titre', '') or '')
            self.description_edit.setPlainText(safe_get(self.tache, 'description', '') or '')
            
            # Projet
            if safe_get(self.tache, 'projet_id'):
                for i in range(self.projet_combo.count()):
                    if self.projet_combo.itemData(i) == self.tache['projet_id']:
                        self.projet_combo.setCurrentIndex(i)
                        break
            
            # Priorité
            if safe_get(self.tache, 'priorite'):
                index = self.priorite_combo.findText(self.tache['priorite'])
                if index >= 0:
                    self.priorite_combo.setCurrentIndex(index)
            
            # Statut
            if safe_get(self.tache, 'statut'):
                index = self.statut_combo.findText(self.tache['statut'])
                if index >= 0:
                    self.statut_combo.setCurrentIndex(index)
            
            # Dates
            if safe_get(self.tache, 'date_echeance'):
                self.date_echeance.setDate(QDate.fromString(self.tache['date_echeance'], "yyyy-MM-dd"))
            
            if safe_get(self.tache, 'date_debut'):
                self.date_debut.setDate(QDate.fromString(self.tache['date_debut'], "yyyy-MM-dd"))
            
            if safe_get(self.tache, 'date_fin_prevue'):
                self.date_fin_prevue.setDate(QDate.fromString(self.tache['date_fin_prevue'], "yyyy-MM-dd"))
            
            # Assigné
            assignee_id = safe_get(self.tache, 'assignee_id') or safe_get(self.tache, 'assigne_a')
            if assignee_id:
                for i in range(self.assigne_combo.count()):
                    if self.assigne_combo.itemData(i) == assignee_id:
                        self.assigne_combo.setCurrentIndex(i)
                        break
            
            self.avancement_spin.setValue(safe_get(self.tache, 'avancement', 0) or 0)
            self.estimation_spin.setValue(float(safe_get(self.tache, 'estimation_heures', 0) or 0))
            self.heures_reelles_spin.setValue(float(safe_get(self.tache, 'heures_reelles', 0) or 0))
            self.tags_edit.setText(safe_get(self.tache, 'tags', '') or '')
            self.commentaires_edit.setPlainText(safe_get(self.tache, 'commentaires', '') or '')
        
        except Exception as e:
            logger.error(f"Erreur chargement tâche: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger la tâche:\n{e}")
    
    def accept_dialog(self):
        """Valide et enregistre la tâche."""
        try:
            # Validation
            if not self.titre_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le titre de la tâche est obligatoire.")
                self.titre_edit.setFocus()
                return
            
            projet_id = self.projet_combo.currentData()
            if not projet_id and self.projet_obligatoire:
                QMessageBox.warning(self, "Validation", "Veuillez sélectionner un projet.")
                self.projet_combo.setFocus()
                return
            
            # Préparer les données
            data = {
                'titre': self.titre_edit.text().strip(),
                'description': self.description_edit.toPlainText().strip() or None,
                'projet_id': projet_id,
                'priorite': self.priorite_combo.currentText(),
                'statut': self.statut_combo.currentText(),
                'date_echeance': self.date_echeance.date().toString("yyyy-MM-dd"),
                'date_debut': self.date_debut.date().toString("yyyy-MM-dd"),
                'date_fin_prevue': self.date_fin_prevue.date().toString("yyyy-MM-dd"),
                'avancement': self.avancement_spin.value(),
                'estimation_heures': self.estimation_spin.value(),
                'heures_reelles': self.heures_reelles_spin.value(),
                'tags': self.tags_edit.text().strip() or None,
                'commentaires': self.commentaires_edit.toPlainText().strip() or None,
            }
            
            # Assigné
            assigne_id = self.assigne_combo.currentData()
            if assigne_id:
                data['assignee_id'] = assigne_id
                data['assigne_a'] = assigne_id
            
            # Sauvegarder
            if self.tache_id:
                tache_service.update(self.tache_id, data)
                logger.info(f"Tâche {self.tache_id} mise à jour")
            else:
                self.tache_id = tache_service.create(data)
                logger.info(f"Tâche créée: {self.tache_id}")
            
            self.accept()
        
        except Exception as e:
            logger.error(f"Erreur sauvegarde tâche: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer la tâche:\n{e}")
    
    def get_data(self):
        """Retourne les données du formulaire (pour compatibilité)."""
        return {
            'id': self.tache_id,
            'titre': self.titre_edit.text().strip(),
        }
