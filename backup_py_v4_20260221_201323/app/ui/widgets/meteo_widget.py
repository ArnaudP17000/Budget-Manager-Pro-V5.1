"""Widget Météo Budgétaire."""
import logging
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from .base_widget import BaseWidget

logger = logging.getLogger(__name__)


class MeteoWidget(BaseWidget):
    """Widget affichant la météo budgétaire."""
    
    def __init__(self, parent=None):
        super().__init__(
            widget_id='meteo_budgetaire',
            title='Météo Budgétaire',
            icon='🌤️',
            parent=parent
        )
        self.setup_content()
        
        # Rafraîchissement auto
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(300000)  # 5 min
        
        self.refresh_data()
    
    def setup_content(self):
        """Configure le contenu du widget."""
        # Icône météo (grande)
        self.meteo_icon = QLabel('☀️')
        self.meteo_icon.setAlignment(Qt.AlignCenter)
        self.meteo_icon.setStyleSheet('font-size: 48px;')
        self.content_layout.addWidget(self.meteo_icon)
        
        # Statut
        self.status_label = QLabel('Beau fixe')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('font-size: 18px; font-weight: bold;')
        self.content_layout.addWidget(self.status_label)
        
        # Description
        self.desc_label = QLabel('Budget sous contrôle')
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setStyleSheet('margin-bottom: 10px;')
        self.content_layout.addWidget(self.desc_label)
        
        # Indicateurs
        self.indicators_layout = QVBoxLayout()
        self.content_layout.addLayout(self.indicators_layout)
        
        self.content_layout.addStretch()
    
    def refresh_data(self):
        """Rafraîchit la météo budgétaire."""
        try:
            from app.services.database_service import db_service
            from app.services.theme_service import theme_service
            from config.themes import get_widget_styles
            s = get_widget_styles(theme_service.get_current_theme())

            # Calculer les métriques
            # [FIX] budget_total -> budget_estime, autorisations_paiement -> credits_paiement
            query_global = '''
                SELECT 
                    COALESCE(SUM(budget_estime), 0) as budget,
                    (SELECT COALESCE(SUM(montant_mandate), 0)
                     FROM credits_paiement WHERE statut != 'ANNULE') as depense,
                    (SELECT COALESCE(SUM(montant_ttc), 0)
                     FROM bons_commande WHERE statut NOT IN ('BROUILLON', 'ANNULE')) as engage
                FROM projets
                WHERE statut NOT IN ('TERMINE', 'ANNULE')
            '''
            
            result = db_service.fetch_one(query_global)
            
            if result:
                budget = result.get('budget', 0) if hasattr(result, 'get') else result['budget']
                depense = result.get('depense', 0) if hasattr(result, 'get') else result['depense']
                engage = result.get('engage', 0) if hasattr(result, 'get') else result['engage']
                
                execution = ((depense + engage) / budget * 100) if budget > 0 else 0
                
                # Déterminer la météo
                if execution < 70:
                    icon = '☀️'
                    status = 'Beau fixe'
                    desc = 'Budget sous contrôle'
                    color = '#2ecc71'
                elif execution < 85:
                    icon = '⛅'
                    status = 'Variable'
                    desc = 'Surveillance recommandée'
                    color = '#f39c12'
                elif execution < 95:
                    icon = '🌧️'
                    status = 'Risqué'
                    desc = 'Risque de dépassement'
                    color = '#e67e22'
                else:
                    icon = '⛈️'
                    status = 'Alerte'
                    desc = 'Dépassement en cours'
                    color = '#e74c3c'
                
                # Mettre à jour l'interface
                self.meteo_icon.setText(icon)
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f'font-size: 18px; font-weight: bold; color: {color};')
                self.desc_label.setText(desc)
                self.desc_label.setStyleSheet(s['meteo_desc'])
                
                # Nettoyer les indicateurs
                while self.indicators_layout.count() > 0:
                    item = self.indicators_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # Ajouter les indicateurs
                self.add_indicator('Exécution', f'{execution:.1f}%')
                self.add_indicator('Dépensé', f'{depense:,.0f} €')
                self.add_indicator('Engagé', f'{engage:,.0f} €')
                self.add_indicator('Disponible', f'{budget - depense - engage:,.0f} €')
                
                logger.info('✅ Météo budgétaire rafraîchie')
            
        except Exception as e:
            logger.error(f'Erreur rafraîchissement météo: {e}', exc_info=True)
    
    def add_indicator(self, label, value):
        """Ajoute un indicateur."""
        from app.services.theme_service import theme_service
        from config.themes import get_widget_styles
        s = get_widget_styles(theme_service.get_current_theme())
        frame = QFrame()
        frame.setStyleSheet(s['indicator_card'])
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        
        label_widget = QLabel(label + ':')
        label_widget.setStyleSheet(s['indicator_label'])
        layout.addWidget(label_widget)
        
        layout.addStretch()
        
        value_widget = QLabel(value)
        value_widget.setStyleSheet(s['indicator_value'])
        layout.addWidget(value_widget)
        
        self.indicators_layout.addWidget(frame)


