"""Widget d'affichage des KPI financiers."""
import logging
from PyQt5.QtWidgets import QLabel, QGridLayout, QFrame, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from .base_widget import BaseWidget

logger = logging.getLogger(__name__)


class KPIWidget(BaseWidget):
    """Widget affichant les KPI financiers principaux."""
    
    def __init__(self, parent=None):
        super().__init__(
            widget_id='kpi_finances',
            title='Finances Globales',
            icon='💰',
            parent=parent
        )
        self.setup_content()
        
        # Rafraîchissement automatique toutes les 5 minutes
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(300000)  # 5 min
        
        # Premier chargement
        self.refresh_data()
    
    def setup_content(self):
        """Configure le contenu du widget."""
        grid = QGridLayout()
        self.content_layout.addLayout(grid)
        
        # Style pour les cartes KPI
        # [FIX THEME] Style appliqué dynamiquement dans refresh_data via s['kpi_card']
        # [FIX] Style appliqué dynamiquement dans refresh_data via s['kpi_card']
        kpi_style = ''''''
        
        # KPI 1: Budget Total
        self.budget_frame = self.create_kpi_card(
            'BUDGET TOTAL',
            '0 €',
            '#3498db',
            kpi_style
        )
        grid.addWidget(self.budget_frame, 0, 0)
        
        # KPI 2: Dépensé (AP)
        self.depense_frame = self.create_kpi_card(
            'DÉPENSÉ (AP)',
            '0 €',
            '#e74c3c',
            kpi_style
        )
        grid.addWidget(self.depense_frame, 0, 1)
        
        # KPI 3: Engagé (BC)
        self.engage_frame = self.create_kpi_card(
            'ENGAGÉ (BC)',
            '0 €',
            '#f39c12',
            kpi_style
        )
        grid.addWidget(self.engage_frame, 1, 0)
        
        # KPI 4: Disponible
        self.dispo_frame = self.create_kpi_card(
            'DISPONIBLE',
            '0 €',
            '#2ecc71',
            kpi_style
        )
        grid.addWidget(self.dispo_frame, 1, 1)
        
        # Barre de progression globale
        progress_container = QFrame()
        progress_layout = QGridLayout(progress_container)
        
        self.progress_label = QLabel('Exécution budgétaire')
        self.progress_label.setObjectName('progress_label')
        progress_layout.addWidget(self.progress_label, 0, 0)
        
        self.progress_percent = QLabel('0%')
        self.progress_percent.setAlignment(Qt.AlignRight)
        progress_layout.addWidget(self.progress_percent, 0, 1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(18)
        progress_layout.addWidget(self.progress_bar, 1, 0, 1, 2)
        
        self.content_layout.addWidget(progress_container)
        
        # Message d'alerte
        self.alert_label = QLabel('')
        self.alert_label.setWordWrap(True)
        self.alert_label.setStyleSheet('''
            padding: 8px;
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            color: #856404;
        ''')
        self.alert_label.hide()
        self.content_layout.addWidget(self.alert_label)
    
    def create_kpi_card(self, title, value, color, style):
        """Crée une carte KPI."""
        frame = QFrame()
        frame.setStyleSheet(style)
        
        layout = QGridLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel(title)
        title_label.setObjectName('kpi_title')
        title_label.setStyleSheet(f'font-size: 11px; font-weight: bold;')
        layout.addWidget(title_label, 0, 0)
        
        # Valeur
        value_label = QLabel(value)
        value_label.setObjectName('kpi_value')
        value_label.setStyleSheet('font-size: 24px; font-weight: bold;')
        layout.addWidget(value_label, 1, 0)
        
        # Pourcentage (si applicable)
        percent_label = QLabel('')
        percent_label.setObjectName('kpi_percent')
        percent_label.setStyleSheet('font-size: 12px;')
        layout.addWidget(percent_label, 2, 0)
        
        return frame
    
    def refresh_data(self):
        """Rafraîchit les données des KPI."""
        try:
            from app.services.database_service import db_service
            from app.services.theme_service import theme_service
            from config.themes import get_widget_styles
            s = get_widget_styles(theme_service.get_current_theme())
            
            # Mettre à jour les styles des cartes KPI selon le thème
            self.budget_frame.setStyleSheet(s['kpi_card'])
            self.depense_frame.setStyleSheet(s['kpi_card'])
            self.engage_frame.setStyleSheet(s['kpi_card'])
            self.dispo_frame.setStyleSheet(s['kpi_card'])
            
            # Mettre à jour les titres KPI
            for frame, style_key in [
                (self.budget_frame, 'kpi_title_budget'),
                (self.depense_frame, 'kpi_title_depense'),
                (self.engage_frame, 'kpi_title_engage'),
                (self.dispo_frame, 'kpi_title_dispo'),
            ]:
                from PyQt5.QtWidgets import QLabel
                lbl = frame.findChild(QLabel, 'kpi_title')
                if lbl:
                    lbl.setStyleSheet(s[style_key])
            
            # Récupérer les données
            # [FIX] budget_total -> budget_estime (nom réel de la colonne dans projets)
            query_budget = '''
                SELECT COALESCE(SUM(budget_estime), 0) as total_budget
                FROM projets
                WHERE statut NOT IN ('TERMINE', 'ANNULE')
            '''
            result_budget = db_service.fetch_one(query_budget)
            budget_total = result_budget['total_budget'] if result_budget else 0

            # [FIX] autorisations_paiement inexistante -> montant mandaté depuis credits_paiement
            query_depense = '''
                SELECT COALESCE(SUM(montant_mandate), 0) as total_depense
                FROM credits_paiement
                WHERE statut != 'ANNULE'
            '''
            result_depense = db_service.fetch_one(query_depense)
            depense = result_depense['total_depense'] if result_depense else 0
            
            query_engage = '''
                SELECT COALESCE(SUM(montant_ttc), 0) as total_engage
                FROM bons_commande
                WHERE statut NOT IN ('BROUILLON', 'ANNULE')  -- [FIX] statuts complets
            '''
            result_engage = db_service.fetch_one(query_engage)
            engage = result_engage['total_engage'] if result_engage else 0
            
            disponible = budget_total - depense - engage
            
            # Calculer les pourcentages
            depense_pct = (depense / budget_total * 100) if budget_total > 0 else 0
            engage_pct = (engage / budget_total * 100) if budget_total > 0 else 0
            dispo_pct = (disponible / budget_total * 100) if budget_total > 0 else 0
            execution_pct = ((depense + engage) / budget_total * 100) if budget_total > 0 else 0
            
            # Mettre à jour l'interface
            self.update_kpi(self.budget_frame, f'{budget_total:,.0f} €', '')
            self.update_kpi(self.depense_frame, f'{depense:,.0f} €', f'{depense_pct:.1f}% 📊')
            self.update_kpi(self.engage_frame, f'{engage:,.0f} €', f'{engage_pct:.1f}% 📈')
            self.update_kpi(self.dispo_frame, f'{disponible:,.0f} €', f'{dispo_pct:.1f}% ✅')
            
            # Mettre à jour la barre de progression
            self.progress_bar.setValue(int(execution_pct))
            self.progress_percent.setText(f'{execution_pct:.1f}%')
            
            # Changer la couleur selon le seuil
            # [FIX THEME] Couleurs depuis le thème actuel
            if execution_pct > 90:
                pb_style = s['progress_bar_danger']
            elif execution_pct > 80:
                pb_style = s['progress_bar_warn']
            else:
                pb_style = s['progress_bar_ok']
            
            self.progress_bar.setStyleSheet(pb_style)
            
            # Afficher une alerte si nécessaire
            if execution_pct > 85:
                self.alert_label.setText(f'⚠️ Attention: {execution_pct:.1f}% du budget est utilisé')
                self.alert_label.show()
            else:
                self.alert_label.hide()
            
            logger.info('✅ KPI Widget rafraîchi')
            
        except Exception as e:
            logger.error(f'Erreur rafraîchissement KPI: {e}')
    
    def update_kpi(self, frame, value, percent):
        """Met à jour une carte KPI."""
        from app.services.theme_service import theme_service
        from config.themes import get_widget_styles
        s = get_widget_styles(theme_service.get_current_theme())
        
        value_label = frame.findChild(QLabel, 'kpi_value')
        percent_label = frame.findChild(QLabel, 'kpi_percent')
        
        if value_label:
            value_label.setText(value)
            value_label.setStyleSheet(s['kpi_value'])
        if percent_label:
            percent_label.setText(percent)
            percent_label.setStyleSheet(s['kpi_percent'])


