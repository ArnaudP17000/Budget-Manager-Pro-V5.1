"""
Dialogue de création/édition de Contrat.
Avec alertes automatiques d'échéance.
"""
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox,
    QPushButton, QMessageBox, QCheckBox, QSpinBox
)
from PyQt5.QtCore import QDate
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class ContratDialog(QDialog):
    """Dialogue de création/édition de Contrat."""
    
    def __init__(self, parent=None, contrat_id=None):
        super().__init__(parent)
        self.contrat_id = contrat_id
        self.setWindowTitle("Nouveau Contrat" if not contrat_id else "Éditer Contrat")
        self.setMinimumWidth(700)
        self.setup_ui()
        
        if contrat_id:
            self.load_contrat()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        
        # Identification
        id_group = QGroupBox("📄 Identification")
        id_form = QFormLayout(id_group)
        
        self.numero_edit = QLineEdit()
        self.numero_edit.setPlaceholderText("Ex: 2024-DSI-001")
        id_form.addRow("Numéro contrat *:", self.numero_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "MARCHE_PUBLIC",
            "MAPA",
            "APPEL_OFFRES",
            "ACCORD_CADRE",
            "CONVENTION",
            "DSP"
        ])
        id_form.addRow("Type de contrat *:", self.type_combo)
        
        self.objet_edit = QLineEdit()
        self.objet_edit.setPlaceholderText("Objet du contrat")
        id_form.addRow("Objet *:", self.objet_edit)
        
        layout.addWidget(id_group)
        
        # Classification budgétaire
        budget_group = QGroupBox("💰 Classification Budgétaire")
        budget_form = QFormLayout(budget_group)
        
        self.type_budget_combo = QComboBox()
        self.type_budget_combo.addItems(["FONCTIONNEMENT", "INVESTISSEMENT"])
        budget_form.addRow("Type Budget *:", self.type_budget_combo)
        
        self.nature_edit = QLineEdit()
        self.nature_edit.setPlaceholderText("Chapitre M57")
        budget_form.addRow("Nature comptable:", self.nature_edit)
        
        self.fonction_edit = QLineEdit()
        self.fonction_edit.setPlaceholderText("Fonction M57")
        budget_form.addRow("Fonction:", self.fonction_edit)
        
        layout.addWidget(budget_group)
        
        # Fournisseur
        fournisseur_group = QGroupBox("🏢 Fournisseur")
        fournisseur_form = QFormLayout(fournisseur_group)
        
        self.fournisseur_combo = QComboBox()
        self.load_fournisseurs()
        fournisseur_form.addRow("Fournisseur *:", self.fournisseur_combo)
        
        layout.addWidget(fournisseur_group)
        
        # Montants
        montants_group = QGroupBox("💵 Montants")
        montants_form = QFormLayout(montants_group)
        
        self.montant_initial_spin = QDoubleSpinBox()
        self.montant_initial_spin.setRange(0, 100000000)
        self.montant_initial_spin.setDecimals(2)
        self.montant_initial_spin.setSuffix(" €")
        self.montant_initial_spin.valueChanged.connect(self.update_total)
        montants_form.addRow("Montant initial HT *:", self.montant_initial_spin)
        
        self.montant_total_spin = QDoubleSpinBox()
        self.montant_total_spin.setRange(0, 100000000)
        self.montant_total_spin.setDecimals(2)
        self.montant_total_spin.setSuffix(" €")
        self.montant_total_spin.valueChanged.connect(self.calculate_ttc)
        montants_form.addRow("Montant total HT:", self.montant_total_spin)
        
        self.montant_ttc_spin = QDoubleSpinBox()
        self.montant_ttc_spin.setRange(0, 100000000)
        self.montant_ttc_spin.setDecimals(2)
        self.montant_ttc_spin.setSuffix(" €")
        self.montant_ttc_spin.setReadOnly(True)
        montants_form.addRow("Montant TTC:", self.montant_ttc_spin)
        
        layout.addWidget(montants_group)
        
        # Période
        periode_group = QGroupBox("📅 Période")
        periode_form = QFormLayout(periode_group)
        
        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDate(QDate.currentDate())
        self.date_debut.dateChanged.connect(self.calculate_duree)
        periode_form.addRow("Date début *:", self.date_debut)
        
        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate().addYears(1))
        self.date_fin.dateChanged.connect(self.calculate_duree)
        periode_form.addRow("Date fin *:", self.date_fin)
        
        self.duree_spin = QSpinBox()
        self.duree_spin.setRange(0, 1000)
        self.duree_spin.setSuffix(" mois")
        self.duree_spin.setReadOnly(True)
        periode_form.addRow("Durée:", self.duree_spin)
        
        self.reconduction_check = QCheckBox("Reconduction tacite")
        periode_form.addRow("", self.reconduction_check)
        
        self.nb_reconductions_spin = QSpinBox()
        self.nb_reconductions_spin.setRange(0, 10)
        periode_form.addRow("Nb reconductions:", self.nb_reconductions_spin)
        
        layout.addWidget(periode_group)
        
        # Statut
        statut_group = QGroupBox("📊 Statut")
        statut_form = QFormLayout(statut_group)
        
        self.statut_combo = QComboBox()
        self.statut_combo.addItems([
            "BROUILLON",
            "ACTIF",
            "RECONDUIT",
            "RESILIE",
            "TERMINE"
        ])
        statut_form.addRow("Statut:", self.statut_combo)
        
        layout.addWidget(statut_group)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self.save)
        buttons_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
    
    def load_fournisseurs(self):
        """Charge la liste des fournisseurs."""
        try:
            rows = db_service.fetch_all(
                "SELECT id, nom FROM fournisseurs WHERE actif = 1 ORDER BY nom"
            )
            self.fournisseur_combo.addItem("-- Sélectionner --", None)
            for row in rows:
                self.fournisseur_combo.addItem(row['nom'], row['id'])
        except Exception as e:
            logger.error(f"Erreur chargement fournisseurs: {e}")
    
    def update_total(self):
        """Met à jour le montant total."""
        if not self.contrat_id:
            self.montant_total_spin.setValue(self.montant_initial_spin.value())
    
    def calculate_ttc(self):
        """Calcule le montant TTC (avec TVA 20%)."""
        ht = self.montant_total_spin.value()
        ttc = ht * 1.20
        self.montant_ttc_spin.setValue(ttc)
    
    def calculate_duree(self):
        """Calcule la durée en mois."""
        date_debut = self.date_debut.date()
        date_fin = self.date_fin.date()
        months = (date_fin.year() - date_debut.year()) * 12 + (date_fin.month() - date_debut.month())
        self.duree_spin.setValue(max(0, months))
    
    def load_contrat(self):
        """Charge les données du contrat."""
        try:
            row = db_service.fetch_one(
                "SELECT * FROM contrats WHERE id = ?",
                (self.contrat_id,)
            )
            if row:
                self.numero_edit.setText(row['numero_contrat'] or '')
                if row['type_contrat']:
                    self.type_combo.setCurrentText(row['type_contrat'])
                self.objet_edit.setText(row['objet'] or '')
                if row['type_budget']:
                    self.type_budget_combo.setCurrentText(row['type_budget'])
                self.nature_edit.setText(row['nature_comptable'] or '')
                self.fonction_edit.setText(row['fonction'] or '')
                
                if row['fournisseur_id']:
                    index = self.fournisseur_combo.findData(row['fournisseur_id'])
                    if index >= 0:
                        self.fournisseur_combo.setCurrentIndex(index)
                
                self.montant_initial_spin.setValue(row['montant_initial_ht'] or 0)
                self.montant_total_spin.setValue(row['montant_total_ht'] or 0)
                self.montant_ttc_spin.setValue(row['montant_ttc'] or 0)
                
                if row['date_debut']:
                    self.date_debut.setDate(QDate.fromString(row['date_debut'], "yyyy-MM-dd"))
                if row['date_fin']:
                    self.date_fin.setDate(QDate.fromString(row['date_fin'], "yyyy-MM-dd"))
                self.duree_spin.setValue(row['duree_mois'] or 0)
                
                self.reconduction_check.setChecked(row['reconduction_tacite'] or False)
                self.nb_reconductions_spin.setValue(row['nombre_reconductions'] or 0)
                
                if row['statut']:
                    self.statut_combo.setCurrentText(row['statut'])
        except Exception as e:
            logger.error(f"Erreur chargement contrat: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger le contrat:\n{e}")
    
    def save(self):
        """Enregistre le contrat."""
        try:
            # Validation
            if not self.numero_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le numéro de contrat est obligatoire.")
                return
            
            if not self.objet_edit.text().strip():
                QMessageBox.warning(self, "Validation", "L'objet du contrat est obligatoire.")
                return
            
            if self.fournisseur_combo.currentData() is None:
                QMessageBox.warning(self, "Validation", "Veuillez sélectionner un fournisseur.")
                return
            
            if self.montant_initial_spin.value() <= 0:
                QMessageBox.warning(self, "Validation", "Le montant initial doit être supérieur à 0.")
                return
            
            # Vérifier unicité du numéro
            if not self.contrat_id:
                existing = db_service.fetch_one(
                    "SELECT id FROM contrats WHERE numero_contrat = ?",
                    (self.numero_edit.text().strip(),)
                )
                if existing:
                    QMessageBox.warning(self, "Validation", "Ce numéro de contrat existe déjà.")
                    return
            
            data = {
                'numero_contrat': self.numero_edit.text().strip(),
                'type_contrat': self.type_combo.currentText(),
                'objet': self.objet_edit.text().strip(),
                'type_budget': self.type_budget_combo.currentText(),
                'nature_comptable': self.nature_edit.text().strip(),
                'fonction': self.fonction_edit.text().strip(),
                'fournisseur_id': self.fournisseur_combo.currentData(),
                'montant_initial_ht': self.montant_initial_spin.value(),
                'montant_total_ht': self.montant_total_spin.value(),
                'montant_ttc': self.montant_ttc_spin.value(),
                'date_debut': self.date_debut.date().toString("yyyy-MM-dd"),
                'date_fin': self.date_fin.date().toString("yyyy-MM-dd"),
                'duree_mois': self.duree_spin.value(),
                'reconduction_tacite': self.reconduction_check.isChecked(),
                'nombre_reconductions': self.nb_reconductions_spin.value(),
                'statut': self.statut_combo.currentText(),
                'date_maj': datetime.now().isoformat(),
            }
            
            if self.contrat_id:
                db_service.update('contrats', data, "id = ?", (self.contrat_id,))
                logger.info(f"Contrat {self.contrat_id} mis à jour")
            else:
                contrat_id = db_service.insert('contrats', data)
                logger.info(f"Contrat créé: {contrat_id}")
            
            self.accept()
        except Exception as e:
            logger.error(f"Erreur sauvegarde contrat: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le contrat:\n{e}")
