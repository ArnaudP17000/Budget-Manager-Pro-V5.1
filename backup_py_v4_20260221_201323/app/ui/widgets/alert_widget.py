"""Widget d'affichage des alertes."""
import logging
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QFrame, QScrollArea, QPushButton
from PyQt5.QtCore import Qt, QTimer
from .base_widget import BaseWidget

logger = logging.getLogger(__name__)


class AlertWidget(BaseWidget):
    """Widget affichant les alertes et actions requises."""
    
    def __init__(self, parent=None):
        super().__init__(
            widget_id='alertes',
            title='Alertes & Actions',
            icon='🔔',
            parent=parent
        )
        self.setup_content()
        
        # Rafraîchissement auto
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(60000)  # 1 min
        
        self.refresh_data()
    
    def setup_content(self):
        """Configure le contenu du widget."""
        # Zone scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_widget = QFrame()
        self.alerts_layout = QVBoxLayout(scroll_widget)
        self.alerts_layout.setSpacing(8)
        
        scroll.setWidget(scroll_widget)
        self.content_layout.addWidget(scroll)
        
        # Message si aucune alerte
        self.no_alert_label = QLabel('✅ Aucune alerte')
        self.no_alert_label.setAlignment(Qt.AlignCenter)
        self.alerts_layout.addWidget(self.no_alert_label)
    
    def refresh_data(self):
        """Rafraîchit les alertes."""
        try:
            # Nettoyer les alertes existantes
            while self.alerts_layout.count() > 0:
                item = self.alerts_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            alerts = []
            
            from app.services.database_service import db_service
            from app.services.theme_service import theme_service
            from config.themes import get_widget_styles
            s = get_widget_styles(theme_service.get_current_theme())
            # Récupérer les alertes depuis la base
            
            # 1. Projets dépassant 80% du budget
            # [FIX] autorisations_paiement → bons_commande (table correcte pour les dépenses par projet)
            # [FIX] HAVING sans GROUP BY interdit en SQLite → sous-requête avec filtre WHERE
            query_projets = '''
                SELECT nom, budget_total, depense, pourcentage
                FROM (
                    SELECT 
                        nom,
                        budget_estime as budget_total,
                        (SELECT COALESCE(SUM(montant_ttc), 0) 
                         FROM bons_commande 
                         WHERE projet_id = projets.id
                           AND statut NOT IN ('ANNULE', 'BROUILLON')) as depense,
                        CASE 
                            WHEN budget_estime > 0 THEN 
                                (SELECT COALESCE(SUM(montant_ttc), 0) 
                                 FROM bons_commande 
                                 WHERE projet_id = projets.id
                                   AND statut NOT IN ('ANNULE', 'BROUILLON')) * 100.0 / budget_estime
                            ELSE 0
                        END as pourcentage
                    FROM projets
                    WHERE statut NOT IN ('TERMINE', 'ANNULE')
                      AND budget_estime > 0
                ) sub
                WHERE pourcentage > 80
                ORDER BY pourcentage DESC
            '''
            projets_alert = db_service.fetch_all(query_projets)
            
            for p in projets_alert or []:
                pct = p.get('pourcentage', 0) if hasattr(p, 'get') else p['pourcentage']
                nom = p.get('nom', 'N/A') if hasattr(p, 'get') else p['nom']
                
                level = 'critique' if pct > 90 else 'attention'
                alerts.append({
                    'level': level,
                    'title': f'Projet {nom}',
                    'message': f'Budget utilisé à {pct:.1f}%',
                    'action': 'Voir projet'
                })
            
            # 2. BC en retard de livraison
            query_bc = '''
                SELECT 
                    numero_bc,
                    date_livraison_prevue,
                    julianday('now') - julianday(date_livraison_prevue) as retard_jours
                FROM bons_commande
                WHERE statut IN ('ENVOYE', 'VALIDE')
                  AND date_livraison_prevue IS NOT NULL
                  AND date_livraison_prevue < date('now')
                ORDER BY retard_jours DESC
                LIMIT 5
            '''
            bc_alert = db_service.fetch_all(query_bc)
            
            for bc in bc_alert or []:
                retard = bc.get('retard_jours', 0) if hasattr(bc, 'get') else bc['retard_jours']
                numero = bc.get('numero_bc', 'N/A') if hasattr(bc, 'get') else bc['numero_bc']
                
                level = 'critique' if retard > 15 else 'attention'
                alerts.append({
                    'level': level,
                    'title': f'BC {numero}',
                    'message': f'Retard de livraison: {int(retard)} jours',
                    'action': 'Voir BC'
                })
            
            # 3. AP actives depuis plus de 30 jours sans CP associé
            # [FIX] autorisations_paiement → autorisations_programme (nom correct de la table)
            query_ap = '''
                SELECT 
                    COUNT(*) as nb_ap,
                    julianday('now') - julianday(MIN(ap.date_creation)) as age_max
                FROM autorisations_programme ap
                LEFT JOIN credits_paiement cp ON cp.ap_id = ap.id
                WHERE ap.statut = 'ACTIVE'
                  AND cp.id IS NULL
                  AND julianday('now') - julianday(ap.date_creation) > 30
            '''
            ap_alert = db_service.fetch_one(query_ap)
            
            if ap_alert:
                nb = ap_alert.get('nb_ap', 0) if hasattr(ap_alert, 'get') else ap_alert['nb_ap']
                age = ap_alert.get('age_max', 0) if hasattr(ap_alert, 'get') else ap_alert['age_max']
                
                if nb > 0:
                    alerts.append({
                        'level': 'attention',
                        'title': f'{nb} AP en attente',
                        'message': f'Jusqu\'à {int(age)} jours d\'attente',
                        'action': 'Voir AP'
                    })
            
            # Afficher les alertes
            if alerts:
                # Grouper par niveau
                critiques = [a for a in alerts if a['level'] == 'critique']
                attentions = [a for a in alerts if a['level'] == 'attention']
                
                if critiques:
                    self.add_alert_section('🔴 CRITIQUE', critiques, '#fee')
                
                if attentions:
                    self.add_alert_section('🟠 ATTENTION', attentions, '#fff3cd')
            else:
                self.no_alert_label = QLabel('✅ Aucune alerte')
                self.no_alert_label.setAlignment(Qt.AlignCenter)
                self.no_alert_label.setStyleSheet(s['alert_ok'])
                self.alerts_layout.addWidget(self.no_alert_label)
            
            self.alerts_layout.addStretch()
            
            logger.info(f'✅ {len(alerts)} alerte(s) chargée(s)')
            
        except Exception as e:
            logger.error(f'Erreur rafraîchissement alertes: {e}', exc_info=True)
    
    def add_alert_section(self, title, alerts, level='attention', s=None):
        if s is None:
            from app.services.theme_service import theme_service
            from config.themes import get_widget_styles
            s = get_widget_styles(theme_service.get_current_theme())
        """Ajoute une section d'alertes."""
        # Titre de section
        section_title = QLabel(title)
        from app.services.theme_service import theme_service
        from config.themes import get_widget_styles
        s = get_widget_styles(theme_service.get_current_theme())
        section_title.setStyleSheet(s['section_title'])
        self.alerts_layout.addWidget(section_title)
        
        # Alertes
        for alert in alerts:
            alert_frame = QFrame()
            alert_frame.setStyleSheet(s['alert_critique'] if level == 'critique' else s['alert_attention'])
            
            alert_layout = QVBoxLayout(alert_frame)
            alert_layout.setContentsMargins(8, 8, 8, 8)
            alert_layout.setSpacing(4)
            
            title_label = QLabel(alert['title'])
            title_label.setStyleSheet(s['item_title'])
            alert_layout.addWidget(title_label)
            
            msg_label = QLabel(alert['message'])
            msg_label.setStyleSheet(s['item_subtitle'])
            alert_layout.addWidget(msg_label)
            
            self.alerts_layout.addWidget(alert_frame)


