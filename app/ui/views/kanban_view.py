"""
Vue Kanban drag & drop pour les tâches.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QLabel,
    QPushButton, QComboBox, QGroupBox, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, pyqtSignal
from PyQt5.QtGui import QDrag, QColor, QPalette
from app.services.tache_service import tache_service
from app.services.projet_service import projet_service
from app.ui.dialogs.tache_dialog import TacheDialog

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row or dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, TypeError, IndexError):
        return default

logger = logging.getLogger(__name__)

class TacheCard(QFrame):
    """Carte de tâche déplaçable."""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, tache, parent=None):
        super().__init__(parent)
        self.tache = tache
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setMaximumWidth(250)
        self.setMinimumHeight(120)
        self.setup_ui()
        self.setCursor(Qt.OpenHandCursor)
    
    def setup_ui(self):
        """Configure l'interface de la carte."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Badge priorité
        priorite = safe_get(self.tache, 'priorite', 'MOYENNE')
        priorite_colors = {
            'CRITIQUE': '🔴',
            'HAUTE': '🟠',
            'MOYENNE': '🟡',
            'BASSE': '🟢'
        }
        priorite_badge = priorite_colors.get(priorite, '⚪')
        
        # Ligne 1: Priorité + Titre
        titre_label = QLabel(f"{priorite_badge} {safe_get(self.tache, 'titre', '')}")
        titre_label.setWordWrap(True)
        titre_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(titre_label)
                # Nom du projet (badge)
        projet_nom = safe_get(self.tache, 'projet_nom', '')
        if projet_nom:
            projet_label = QLabel(f"📁 {projet_nom}")
            projet_label.setStyleSheet("""
                color: #0066cc; 
                font-size: 10px; 
                font-weight: bold;
                background-color: #e6f2ff;
                padding: 2px 6px;
                border-radius: 3px;
            """)
            projet_label.setWordWrap(True)
            layout.addWidget(projet_label)
        
        # Echeance
        if safe_get(self.tache, 'date_écheance'):
            echeance_label = QLabel(f"📅 {self.tache['date_écheance']}")
            echeance_label.setStyleSheet("color: #666; font-size: 11px;")
            layout.addWidget(echeance_label)
        
        # Assigné
        if safe_get(self.tache, 'assigné_id'):
            assignee_label = QLabel(f"👤 Assigné")
            assignee_label.setStyleSheet("color: #666; font-size: 11px;")
            layout.addWidget(assignee_label)
        
        # Tags
        tags = safe_get(self.tache, 'tags', '')
        if tags:
            tags_label = QLabel(f"🏷️ {tags}")
            tags_label.setStyleSheet("color: #0066cc; font-size: 10px;")
            tags_label.setWordWrap(True)
            layout.addWidget(tags_label)
        
        # Barre de progression
        avancement = safe_get(self.tache, 'avancement', 0)
        progress = QProgressBar()
        progress.setValue(avancement)
        progress.setMaximumHeight(15)
        progress.setTextVisible(True)
        progress.setFormat(f"{avancement}%")
        layout.addWidget(progress)
        
        # Couleur selon statut
        statut = safe_get(self.tache, 'statut', 'A_FAIRE')
        if statut == 'BLOQUE':
            self.setStyleSheet("background-color: #ffe6e6;")
        elif statut == 'TERMINE':
            self.setStyleSheet("background-color: #e6ffe6;")
        
        # Tooltip avec informations complètes
        tooltip_parts = []
        
        # Nom du projet
        if safe_get(self.tache, 'projet_nom'):
            tooltip_parts.append(f"📁 Projet: {self.tache['projet_nom']}")
        
        # Code projet
        if safe_get(self.tache, 'projet_code'):
            tooltip_parts.append(f"🔖 Code: {self.tache['projet_code']}")
        
        # Titre
        tooltip_parts.append(f"📝 {safe_get(self.tache, 'titre', '')}")
        
        # Description (première ligne)
        description = safe_get(self.tache, 'description', '')
        if description:
            first_line = description.split('\n')[0][:100]
            tooltip_parts.append(f"💬 {first_line}...")
        
        # Assigné
        if safe_get(self.tache, 'assignee_nom'):
            tooltip_parts.append(f"👤 Assigné: {self.tache['assignee_nom']}")
        
        # Echeance
        if safe_get(self.tache, 'date_echeance'):
            tooltip_parts.append(f"📅 Echeance: {self.tache['date_echeance']}")
        
        # Priorité
        tooltip_parts.append(f"⚡ Priorité: {priorite}")
        
        # Avancement
        tooltip_parts.append(f"📊 Avancement: {avancement}%")
        
        # Créer le tooltip
        self.setToolTip('\n'.join(tooltip_parts))
    
    def mousePressEvent(self, event):
        """Gère le début du drag."""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        """Gère le drag de la carte."""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.tache['id']))
        drag.setMimeData(mime_data)
        
        drag.exec_(Qt.MoveAction)
        self.setCursor(Qt.OpenHandCursor)
    
    def mouseDoubleClickEvent(self, event):
        """Gère le double-clic pour ouvrir le dialogue."""
        # Convertir sqlite3.Row en dict si nécessaire
        tache_dict = dict(self.tache) if not isinstance(self.tache, dict) else self.tache
        self.clicked.emit(tache_dict)


class KanbanColumn(QFrame):
    """Colonne Kanban."""
    
    card_dropped = pyqtSignal(int, str)  # tache_id, nouveau_statut
    
    def __init__(self, titre, statut, parent=None):
        super().__init__(parent)
        self.titre = titre
        self.statut = statut
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Box)
        self.setMinimumWidth(280)
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface de la colonne."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Couleur de l'en-tête selon le statut
        couleurs = {
            'A_FAIRE':    ('#3498db', '#FFFFFF'),   # bleu
            'EN_COURS':   ('#e67e22', '#FFFFFF'),   # orange
            'EN_ATTENTE': ('#8e44ad', '#FFFFFF'),   # violet
            'TERMINE':    ('#27ae60', '#FFFFFF'),   # vert
        }
        bg, fg = couleurs.get(self.statut, ('#555555', '#FFFFFF'))

        # Compteur de cartes
        self.count_label = QLabel("0")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.3); color: white; "
            "font-weight: bold; font-size: 11px; border-radius: 9px; "
            "padding: 1px 7px; min-width: 18px;")

        # En-tête avec titre + compteur côte à côte
        header_w = QWidget()
        header_w.setStyleSheet(
            "background-color: %s; border-radius: 6px;" % bg)
        h_layout = QHBoxLayout(header_w)
        h_layout.setContentsMargins(10, 8, 10, 8)

        titre_lbl = QLabel(self.titre)
        titre_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        titre_lbl.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: %s; "
            "background: transparent;" % fg)

        h_layout.addWidget(titre_lbl)
        h_layout.addStretch()
        h_layout.addWidget(self.count_label)
        layout.addWidget(header_w)
        
        # Zone de cartes dans un scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setSpacing(10)
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)
    
    def _update_count(self):
        """Met à jour le badge compteur."""
        n = self.cards_layout.count()
        self.count_label.setText(str(n))

    def add_card(self, tache, parent_view):
        """Ajoute une carte de tâche."""
        card = TacheCard(tache, self)
        card.clicked.connect(parent_view.open_tache)
        self.cards_layout.addWidget(card)
        self._update_count()
    
    def clear_cards(self):
        """Supprime toutes les cartes."""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def dragEnterEvent(self, event):
        """Accepte le drag."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet("border: 2px dashed #0066cc;")
    
    def dragLeaveEvent(self, event):
        """Réinitialise le style."""
        self.setStyleSheet("")
    
    def dropEvent(self, event):
        """Gère le drop de la carte."""
        self.setStyleSheet("")
        if event.mimeData().hasText():
            tache_id = int(event.mimeData().text())
            self.card_dropped.emit(tache_id, self.statut)
            event.acceptProposedAction()


class KanbanView(QWidget):
    """Vue Kanban pour les tâches."""
    
    def __init__(self):
        super().__init__()
        self.tache_service = tache_service
        self.projet_service = projet_service
        self.columns = {}
        self.init_ui()
        self.load_projets()
        self.load_taches()
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Titre
        title_label = QLabel("📋 Vue Kanban")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # Filtres
        filters_layout = QHBoxLayout()
        
        filters_layout.addWidget(QLabel("Projet:"))
        self.projet_filter = QComboBox()
        self.projet_filter.currentIndexChanged.connect(self.load_taches)
        filters_layout.addWidget(self.projet_filter)
        
        filters_layout.addWidget(QLabel("Priorité:"))
        self.priorite_filter = QComboBox()
        self.priorite_filter.addItems(["Toutes", "CRITIQUE", "HAUTE", "MOYENNE", "BASSE"])
        self.priorite_filter.currentTextChanged.connect(self.load_taches)
        filters_layout.addWidget(self.priorite_filter)
        
        filters_layout.addStretch()
        
        # Bouton créer tâche
        create_btn = QPushButton("✨ Nouvelle Tâche")
        create_btn.clicked.connect(self.create_tache)
        filters_layout.addWidget(create_btn)
        
        # Bouton rafraîchir
        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self.refresh_all)
        filters_layout.addWidget(refresh_btn)
        
        layout.addLayout(filters_layout)
        
        # Colonnes Kanban
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(10)
        
        # 4 colonnes
        colonnes_config = [
            ("📝 À faire", "A_FAIRE"),
            ("⚙️ En cours", "EN_COURS"),
            ("⏸️ En attente", "EN_ATTENTE"),
            ("✅ Terminé", "TERMINE")
        ]
        
        for titre, statut in colonnes_config:
            col = KanbanColumn(titre, statut, self)
            col.card_dropped.connect(self.change_statut)
            self.columns[statut] = col
            columns_layout.addWidget(col)
        
        layout.addLayout(columns_layout)
    
    def load_projets(self):
        """Recharge la liste des projets."""
        try:
            # Sauvegarder la sélection actuelle
            current_projet_id = self.projet_filter.currentData()
            
            # Vider et recharger
            self.projet_filter.clear()
            self.projet_filter.addItem("Tous", None)
            
            projets = self.projet_service.get_all()
            for projet in projets:
                label = f"{projet['code']} - {projet['nom']}" if safe_get(projet, 'code') else projet['nom']
                self.projet_filter.addItem(label, projet['id'])
            
            # Restaurer la sélection
            if current_projet_id:
                index = self.projet_filter.findData(current_projet_id)
                if index >= 0:
                    self.projet_filter.setCurrentIndex(index)
                    
        except Exception as e:
            logger.error(f"Erreur rechargement projets: {e}")
    
    def load_taches(self):
        """Charge les tâches dans le Kanban."""
        try:
            # Préparer les filtres
            filters = {}
            
            projet_id = self.projet_filter.currentData()
            if projet_id:
                filters['projet_id'] = projet_id
            
            priorite = self.priorite_filter.currentText()
            if priorite != "Toutes":
                filters['priorite'] = priorite
            
            # Charger les tâches
            taches = self.tache_service.get_all(filters)
            
            # Effacer les colonnes
            for col in self.columns.values():
                col.clear_cards()
            
            # Ajouter les cartes
            for tache in taches:
                statut = safe_get(tache, 'statut', 'A_FAIRE')
                if statut in self.columns:
                    self.columns[statut].add_card(tache, self)
            
            logger.info(f"{len(taches)} tâches chargées dans le Kanban")
        
        except Exception as e:
            logger.error(f"Erreur chargement tâches Kanban: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de charger les tâches:\n{e}")
    
    def refresh_all(self):
        """Rafraîchit projets et tâches."""
        self.load_projets()
        self.load_taches()
    
    def change_statut(self, tache_id, nouveau_statut):
        """Change le statut d'une tâche."""
        try:
            data = {'statut': nouveau_statut}
            self.tache_service.update(tache_id, data)
            logger.info(f"Tâche {tache_id} -> {nouveau_statut}")
            self.load_taches()
        except Exception as e:
            logger.error(f"Erreur changement statut: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de changer le statut:\n{e}")
    
    def open_tache(self, tache):
        """Ouvre le dialogue de tâche."""
        try:
            dialog = TacheDialog(self, tache)
            if dialog.exec_():
                self.load_taches()
        except Exception as e:
            logger.error(f"Erreur ouverture tâche: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible d'ouvrir la tâche:\n{e}")
    
    def create_tache(self):
        """Crée une nouvelle tâche."""
        try:
            dialog = TacheDialog(self)
            if dialog.exec_():
                self.load_taches()
        except Exception as e:
            logger.error(f"Erreur création tâche: {e}")
            QMessageBox.warning(self, "Erreur", f"Impossible de créer la tâche:\n{e}")