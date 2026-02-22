"""
Vue Dashboard avec KPI et graphiques.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class KPIWidget(QFrame):
    """Widget pour afficher un KPI."""
    
    def __init__(self, title, value, icon="", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)
        
        layout = QVBoxLayout(self)
        
        # Icône et valeur
        value_label = QLabel(f"{icon} {value}")
        value_label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        # Titre
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11pt;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        self.setMinimumHeight(120)

class DashboardView(QWidget):
    """Vue Dashboard principale."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("📊 Dashboard - Vue d'ensemble")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Scroll area pour le contenu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # KPI principaux
        kpi_group = QGroupBox("📈 Indicateurs clés")
        kpi_layout = QGridLayout(kpi_group)
        
        self.kpi_projets = KPIWidget("Projets actifs", "0", "📁")
        self.kpi_budget = KPIWidget("Budget total (€)", "0", "💰")
        self.kpi_bc_attente = KPIWidget("BC en attente", "0", "🛒")
        self.kpi_contrats = KPIWidget("Contrats actifs", "0", "📄")
        
        kpi_layout.addWidget(self.kpi_projets, 0, 0)
        kpi_layout.addWidget(self.kpi_budget, 0, 1)
        kpi_layout.addWidget(self.kpi_bc_attente, 0, 2)
        kpi_layout.addWidget(self.kpi_contrats, 0, 3)
        
        content_layout.addWidget(kpi_group)
        
        # Budget
        budget_group = QGroupBox("💰 Budget")
        budget_layout = QVBoxLayout(budget_group)
        
        self.budget_info = QLabel("Chargement des informations budgétaires...")
        budget_layout.addWidget(self.budget_info)
        
        content_layout.addWidget(budget_group)
        
        # Alertes
        alertes_group = QGroupBox("🔔 Alertes et notifications")
        alertes_layout = QVBoxLayout(alertes_group)
        
        self.alertes_label = QLabel("Aucune alerte")
        alertes_layout.addWidget(self.alertes_label)
        
        content_layout.addWidget(alertes_group)
        
        # Activité récente
        activite_group = QGroupBox("📝 Activité récente")
        activite_layout = QVBoxLayout(activite_group)
        
        self.activite_label = QLabel("Aucune activité récente")
        activite_layout.addWidget(self.activite_label)
        
        content_layout.addWidget(activite_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def load_data(self):
        """Charge les données du dashboard."""
        try:
            conn = db_service.get_connection()
            
            # Compter les projets actifs
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM projets WHERE statut = 'ACTIF'"
            )
            row = cursor.fetchone()
            nb_projets = row['count'] if row else 0
            self.kpi_projets.findChild(QLabel).setText(f"📁 {nb_projets}")
            
            # Compter les BC en attente
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM bons_commande WHERE statut = 'EN_ATTENTE'"
            )
            row = cursor.fetchone()
            nb_bc = row['count'] if row else 0
            self.kpi_bc_attente.findChildren(QLabel)[0].setText(f"🛒 {nb_bc}")
            
            # Compter les contrats actifs
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM contrats WHERE statut = 'ACTIF'"
            )
            row = cursor.fetchone()
            nb_contrats = row['count'] if row else 0
            self.kpi_contrats.findChildren(QLabel)[0].setText(f"📄 {nb_contrats}")
            
            # Budget total (AP)
            cursor = conn.execute(
                "SELECT SUM(montant_total) as total FROM autorisations_programme WHERE statut = 'ACTIVE'"
            )
            row = cursor.fetchone()
            budget_total = row['total'] if row and row['total'] else 0
            self.kpi_budget.findChildren(QLabel)[0].setText(f"💰 {budget_total:,.0f}")
            
            # Infos budget détaillées
            cursor = conn.execute("""
                SELECT 
                    SUM(montant_vote) as vote,
                    SUM(montant_disponible) as dispo,
                    SUM(montant_engage) as engage
                FROM credits_paiement
                WHERE statut = 'ACTIF'
            """)
            row = cursor.fetchone()
            if row:
                vote = row['vote'] or 0
                dispo = row['dispo'] or 0
                engage = row['engage'] or 0
                
                budget_text = f"""
                <b>Crédits votés:</b> {vote:,.2f} €<br>
                <b>Crédits disponibles:</b> {dispo:,.2f} €<br>
                <b>Engagés:</b> {engage:,.2f} €<br>
                <b>Taux d'engagement:</b> {(engage/vote*100 if vote > 0 else 0):.1f}%
                """
                self.budget_info.setText(budget_text)
            
            # Alertes
            alertes = []
            
            # BC en attente de validation
            if nb_bc > 0:
                alertes.append(f"⚠️ {nb_bc} bon(s) de commande en attente de validation")
            
            # Contrats à échéance (< 3 mois)
            cursor = conn.execute("""
                SELECT COUNT(*) as count 
                FROM contrats 
                WHERE statut = 'ACTIF' 
                AND date_fin <= date('now', '+3 months')
            """)
            row = cursor.fetchone()
            nb_contrats_echeance = row['count'] if row else 0
            if nb_contrats_echeance > 0:
                alertes.append(f"📄 {nb_contrats_echeance} contrat(s) arrivent à échéance dans moins de 3 mois")
            
            if alertes:
                self.alertes_label.setText("<br>".join(alertes))
            else:
                self.alertes_label.setText("✅ Aucune alerte")
            
            logger.info("Dashboard chargé")
            
        except Exception as e:
            logger.error(f"Erreur chargement dashboard: {e}")
            self.budget_info.setText(f"Erreur: {e}")
