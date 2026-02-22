"""Widget Top 5 Projets."""
import logging
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QFrame, QProgressBar, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from .base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ProjectWidget(BaseWidget):
    """Widget affichant le top 5 des projets."""
    
    def __init__(self, parent=None):
        super().__init__(
            widget_id='top_projets',
            title='Top 5 Projets',
            icon='📁',
            parent=parent
        )
        self.setup_content()
        
        # Rafraîchissement auto
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(120000)  # 2 min
        
        self.refresh_data()
    
    def setup_content(self):
        """Configure le contenu du widget."""
        self.projects_layout = QVBoxLayout()
        self.content_layout.addLayout(self.projects_layout)
        
        self.content_layout.addStretch()
    
    def refresh_data(self):
        """Rafraîchit les données des projets."""
        try:
            # Nettoyer
            while self.projects_layout.count() > 0:
                item = self.projects_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            from app.services.database_service import db_service
            from app.services.theme_service import theme_service
            from config.themes import get_widget_styles
            s = get_widget_styles(theme_service.get_current_theme())
            
            # [FIX] budget_total -> budget_estime, autorisations_paiement -> bons_commande
            query = '''
                SELECT 
                    p.id,
                    p.nom,
                    COALESCE(p.budget_estime, 0) as budget_total,
                    COALESCE(SUM(bc.montant_ttc), 0) as depense,
                    CASE 
                        WHEN COALESCE(p.budget_estime, 0) > 0 THEN 
                            COALESCE(SUM(bc.montant_ttc), 0) * 100.0 / p.budget_estime
                        ELSE 0
                    END as pourcentage
                FROM projets p
                LEFT JOIN bons_commande bc ON bc.projet_id = p.id
                    AND bc.statut NOT IN ('BROUILLON', 'ANNULE')
                WHERE p.statut NOT IN ('TERMINE', 'ANNULE')
                GROUP BY p.id, p.nom, p.budget_estime
                ORDER BY pourcentage DESC
                LIMIT 5
            '''

            projets = db_service.fetch_all(query)

            if projets:
                for i, p in enumerate(projets, 1):
                    nom = p.get('nom', 'N/A') if hasattr(p, 'get') else p['nom']
                    budget = p.get('budget_total', 0) if hasattr(p, 'get') else p['budget_total']
                    depense = p.get('depense', 0) if hasattr(p, 'get') else p['depense']
                    pct = p.get('pourcentage', 0) if hasattr(p, 'get') else p['pourcentage']
                    
                    self.add_project_item(i, nom, budget, depense, pct, s)
            else:
                no_data = QLabel('Aucun projet actif')
                no_data.setAlignment(Qt.AlignCenter)
                no_data.setStyleSheet(s['no_data'])
                self.projects_layout.addWidget(no_data)
            
            logger.info(f'✅ {len(projets) if projets else 0} projet(s) chargé(s)')
            
        except Exception as e:
            logger.error(f'Erreur rafraîchissement projets: {e}', exc_info=True)
    
    def add_project_item(self, rank, nom, budget, depense, pct, s=None):
        """Ajoute un item projet."""
        if s is None:
            from app.services.theme_service import theme_service
            from config.themes import get_widget_styles
            s = get_widget_styles(theme_service.get_current_theme())
        frame = QFrame()
        frame.setStyleSheet(s['item_card'])
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        
        # Ligne 1: Rang + Nom + Badge
        top_layout = QHBoxLayout()
        
        rank_label = QLabel(f'{rank}.')
        rank_label.setStyleSheet(s['item_rank'])
        top_layout.addWidget(rank_label)
        
        nom_label = QLabel(nom)
        nom_label.setStyleSheet(s['item_title'])
        top_layout.addWidget(nom_label)
        
        top_layout.addStretch()
        
        # Badge statut
        if pct > 90:
            badge = '🔴'
            badge_text = 'Critique'
        elif pct > 80:
            badge = '🟠'
            badge_text = 'Attention'
        else:
            badge = '🟢'
            badge_text = 'OK'
        
        status_label = QLabel(f'{badge} {badge_text}')
        status_label.setStyleSheet(s['item_subtitle'])
        top_layout.addWidget(status_label)
        
        layout.addLayout(top_layout)
        
        # Ligne 2: Budget info
        info_label = QLabel(f'Budget: {budget:,.0f} € | Dépensé: {depense:,.0f} € | Reste: {budget - depense:,.0f} €')
        info_label.setStyleSheet(s['item_subtitle'])
        layout.addWidget(info_label)
        
        # Ligne 3: Barre de progression
        progress_layout = QHBoxLayout()
        
        progress = QProgressBar()
        progress.setValue(int(pct))
        progress.setTextVisible(False)
        progress.setFixedHeight(12)
        
        # Couleur selon pourcentage
        if pct > 90:
            progress.setStyleSheet(s['mini_progress_danger'])
        elif pct > 80:
            progress.setStyleSheet(s['mini_progress_warn'])
        else:
            progress.setStyleSheet(s['mini_progress_ok'])
        
        progress_layout.addWidget(progress)
        
        pct_label = QLabel(f'{pct:.1f}%')
        pct_label.setStyleSheet(s['progress_label'])
        pct_label.setFixedWidth(50)
        pct_label.setAlignment(Qt.AlignRight)
        progress_layout.addWidget(pct_label)
        
        layout.addLayout(progress_layout)
        
        self.projects_layout.addWidget(frame)


