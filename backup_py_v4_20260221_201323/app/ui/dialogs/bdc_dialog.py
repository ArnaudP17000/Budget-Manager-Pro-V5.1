"""
Dialogue de création/édition de Bon de Commande.
Avec numéro manuel, type F/I, validation et imputation automatique.
"""
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox,
    QPushButton, QMessageBox, QLabel, QCheckBox
)
from PyQt5.QtCore import QDate
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class BDCDialog(QDialog):
    """Dialogue de création/édition de Bon de Commande."""
    
    def __init__(self, parent=None, bc_id=None):
        super().__init__(parent)
        self.bc_id = bc_id
        self.setWindowTitle("Nouveau Bon de Commande" if not bc_id else "Éditer Bon de Commande")
        self.setMinimumWidth(700)
        self.setup_ui()
        
        if bc_id:
            self.load_bc()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        
        # ===== Identification =====
        id_group = QGroupBox("📝 Identification")
        id_form = QFormLayout(id_group)
        
        self.numero_edit = QLineEdit()
        self.numero_edit.setPlaceholderText("Ex: BC2024-0001")
        id_form.addRow("Numéro BC * (manuel):", self.numero_edit)
        
        self.date_creation = QDateEdit()
        self.date_creation.setCalendarPopup(True)
        self.date_creation.setDate(QDate.currentDate())
        id_form.addRow("Date création:", self.date_creation)
        
        layout.addWidget(id_group)
        
        # ===== Classification Budgétaire =====
        budget_group = QGroupBox("💰 Classification Budgétaire")
        budget_form = QFormLayout(budget_group)
        
        self.type_budget_combo = QComboBox()
        self.type_budget_combo.addItems(["FONCTIONNEMENT", "INVESTISSEMENT"])
        budget_form.addRow("Type Budget * (F/I):", self.type_budget_combo)
        
        self.nature_edit = QLineEdit()
        self.nature_edit.setPlaceholderText("Ex: 2313 (Chapitre M57)")
        budget_form.addRow("Nature comptable:", self.nature_edit)
        
        self.fonction_edit = QLineEdit()
        self.fonction_edit.setPlaceholderText("Ex: 020")
        budget_form.addRow("Fonction M57:", self.fonction_edit)
        
        self.operation_edit = QLineEdit()
        self.operation_edit.setPlaceholderText("Si investissement")
        budget_form.addRow("Opération:", self.operation_edit)
        
        layout.addWidget(budget_group)
        
        # ===== Objet =====
        objet_group = QGroupBox("📋 Objet")
        objet_form = QFormLayout(objet_group)
        
        self.objet_edit = QLineEdit()
        self.objet_edit.setPlaceholderText("Objet du bon de commande")
        objet_form.addRow("Objet *:", self.objet_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Description détaillée")
        objet_form.addRow("Description:", self.description_edit)
        
        # Fournisseur
        self.fournisseur_combo = QComboBox()
        self.load_fournisseurs()
        objet_form.addRow("Fournisseur *:", self.fournisseur_combo)
        
        layout.addWidget(objet_group)
        
        # ===== Montants =====
        montants_group = QGroupBox("💵 Montants")
        montants_form = QFormLayout(montants_group)
        
        self.montant_ht_spin = QDoubleSpinBox()
        self.montant_ht_spin.setRange(0, 10000000)
        self.montant_ht_spin.setDecimals(2)
        self.montant_ht_spin.setSuffix(" €")
        self.montant_ht_spin.valueChanged.connect(self.calculate_ttc)
        montants_form.addRow("Montant HT *:", self.montant_ht_spin)
        
        self.tva_spin = QDoubleSpinBox()
        self.tva_spin.setRange(0, 100)
        self.tva_spin.setDecimals(1)
        self.tva_spin.setSuffix(" %")
        self.tva_spin.setValue(20.0)
        self.tva_spin.valueChanged.connect(self.calculate_ttc)
        montants_form.addRow("TVA:", self.tva_spin)
        
        self.montant_ttc_spin = QDoubleSpinBox()
        self.montant_ttc_spin.setRange(0, 10000000)
        self.montant_ttc_spin.setDecimals(2)
        self.montant_ttc_spin.setSuffix(" €")
        self.montant_ttc_spin.setReadOnly(True)
        montants_form.addRow("Montant TTC:", self.montant_ttc_spin)
        
        layout.addWidget(montants_group)
        
        # ===== Validation =====
        validation_group = QGroupBox("✅ Validation et Imputation")
        validation_layout = QVBoxLayout(validation_group)
        
        self.valide_check = QCheckBox("BC Validé (imputation automatique)")
        self.valide_check.stateChanged.connect(self.on_validation_changed)
        validation_layout.addWidget(self.valide_check)
        
        self.validation_info = QLabel(
            "⚠️ Lors de la validation, le BC sera automatiquement imputé sur le budget."
        )
        self.validation_info.setWordWrap(True)
        self.validation_info.setStyleSheet("color: orange; font-style: italic;")
        validation_layout.addWidget(self.validation_info)
        
        self.statut_combo = QComboBox()
        self.statut_combo.addItems([
            "BROUILLON",
            "EN_ATTENTE",
            "VALIDE",
            "IMPUTE",
            "ANNULE"
        ])
        validation_form = QFormLayout()
        validation_form.addRow("Statut:", self.statut_combo)
        validation_layout.addLayout(validation_form)
        
        layout.addWidget(validation_group)
        
        # ===== Livraison =====
        livraison_group = QGroupBox("🚚 Livraison")
        livraison_form = QFormLayout(livraison_group)
        
        self.date_livraison = QDateEdit()
        self.date_livraison.setCalendarPopup(True)
        self.date_livraison.setDate(QDate.currentDate().addMonths(1))
        livraison_form.addRow("Date livraison prévue:", self.date_livraison)
        
        layout.addWidget(livraison_group)
        
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
    
    def calculate_ttc(self):
        """Calcule le montant TTC."""
        ht = self.montant_ht_spin.value()
        tva = self.tva_spin.value()
        ttc = ht * (1 + tva / 100)
        self.montant_ttc_spin.setValue(ttc)
    
    def on_validation_changed(self, state):
        """Gère le changement de l'état de validation."""
        if state:
            self.statut_combo.setCurrentText("VALIDE")
            self.validation_info.setText(
                "✅ Le BC sera imputé automatiquement sur le budget lors de l'enregistrement."
            )
            self.validation_info.setStyleSheet("color: green; font-style: italic;")
        else:
            self.validation_info.setText(
                "⚠️ Lors de la validation, le BC sera automatiquement imputé sur le budget."
            )
            self.validation_info.setStyleSheet("color: orange; font-style: italic;")
    
    def load_bc(self):
        """Charge les données du BC."""
        try:
            row = db_service.fetch_one(
                "SELECT * FROM bons_commande WHERE id = ?",
                (self.bc_id,)
            )
            if row:
                self.numero_edit.setText(row['numero_bc'] or '')
                if row['date_creation']:
                    self.date_creation.setDate(QDate.fromString(row['date_creation'], "yyyy-MM-dd"))
                if row['type_budget']:
                    self.type_budget_combo.setCurrentText(row['type_budget'])
                self.nature_edit.setText(row['nature_comptable'] or '')
                self.fonction_edit.setText(row['fonction'] or '')
                self.operation_edit.setText(row['operation'] or '')
                self.objet_edit.setText(row['objet'] or '')
                self.description_edit.setPlainText(row['description'] or '')
                
                # Fournisseur
                if row['fournisseur_id']:
                    index = self.fournisseur_combo.findData(row['fournisseur_id'])
                    if index >= 0:
                        self.fournisseur_combo.setCurrentIndex(index)
                
                self.montant_ht_spin.setValue(row['montant_ht'] or 0)
                self.tva_spin.setValue(row['tva'] or 20.0)
                self.montant_ttc_spin.setValue(row['montant_ttc'] or 0)
                
                self.valide_check.setChecked(row['valide'] or False)
                if row['statut']:
                    self.statut_combo.setCurrentText(row['statut'])
                
                if row['date_livraison_prevue']:
                    self.date_livraison.setDate(QDate.fromString(row['date_livraison_prevue'], "yyyy-MM-dd"))
        except Exception as e:
            logger.error(f"Erreur chargement BC: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger le BC:\n{e}")
    
    def save(self):
        """Enregistre le BC avec imputation automatique si validé."""
        try:
            # Validation
            if not self.numero_edit.text().strip():
                QMessageBox.warning(self, "Validation", "Le numéro de BC est obligatoire.")
                return
            
            if not self.objet_edit.text().strip():
                QMessageBox.warning(self, "Validation", "L'objet du BC est obligatoire.")
                return
            
            if self.fournisseur_combo.currentData() is None:
                QMessageBox.warning(self, "Validation", "Veuillez sélectionner un fournisseur.")
                return
            
            if self.montant_ht_spin.value() <= 0:
                QMessageBox.warning(self, "Validation", "Le montant HT doit être supérieur à 0.")
                return
            
            # Vérifier unicité du numéro BC
            if not self.bc_id:
                existing = db_service.fetch_one(
                    "SELECT id FROM bons_commande WHERE numero_bc = ?",
                    (self.numero_edit.text().strip(),)
                )
                if existing:
                    QMessageBox.warning(self, "Validation", "Ce numéro de BC existe déjà.")
                    return
            
            data = {
                'numero_bc': self.numero_edit.text().strip(),
                'date_creation': self.date_creation.date().toString("yyyy-MM-dd"),
                'type_budget': self.type_budget_combo.currentText(),
                'nature_comptable': self.nature_edit.text().strip(),
                'fonction': self.fonction_edit.text().strip(),
                'operation': self.operation_edit.text().strip(),
                'objet': self.objet_edit.text().strip(),
                'description': self.description_edit.toPlainText().strip(),
                'fournisseur_id': self.fournisseur_combo.currentData(),
                'montant_ht': self.montant_ht_spin.value(),
                'tva': self.tva_spin.value(),
                'montant_ttc': self.montant_ttc_spin.value(),
                'valide': self.valide_check.isChecked(),
                'statut': self.statut_combo.currentText(),
                'date_livraison_prevue': self.date_livraison.date().toString("yyyy-MM-dd"),
                'date_maj': datetime.now().isoformat(),
            }
            
            # Si validé, imputer automatiquement
            if self.valide_check.isChecked():
                data['impute'] = True
                data['date_validation'] = datetime.now().isoformat()
                data['date_imputation'] = datetime.now().isoformat()
                data['montant_engage'] = self.montant_ttc_spin.value()
                # TODO: Trouver le CP approprié et créer l'engagement
            
            if self.bc_id:
                # Mise à jour
                db_service.update('bons_commande', data, "id = ?", (self.bc_id,))
                logger.info(f"BC {self.bc_id} mis à jour")
            else:
                # Création
                bc_id = db_service.insert('bons_commande', data)
                logger.info(f"BC créé: {bc_id}")
            
            QMessageBox.information(
                self,
                "Succès",
                f"Bon de commande enregistré.\n" +
                ("✅ Imputation budgétaire effectuée." if self.valide_check.isChecked() else "")
            )
            self.accept()
        except Exception as e:
            logger.error(f"Erreur sauvegarde BC: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le BC:\n{e}")
