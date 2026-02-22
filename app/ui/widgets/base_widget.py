"""Widget de base pour le dashboard personnalisable."""
import logging
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSizePolicy, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QCursor

logger = logging.getLogger(__name__)


class BaseWidget(QFrame):
    """Widget de base avec header personnalisable et actions."""
    
    # Signaux
    closeRequested = pyqtSignal(str)      # ID du widget
    minimizeRequested = pyqtSignal(str, bool)  # ID, état
    resizeRequested = pyqtSignal(str, str)     # ID, taille (small/medium/large)
    
    def __init__(self, widget_id, title, icon='📊', parent=None):
        super().__init__(parent)
        self.widget_id = widget_id
        self.title = title
        self.icon = icon
        self.is_minimized = False
        self.current_size = 'medium'  # small, medium, large
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Configure l'interface du widget."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setObjectName('widgetHeader')
        self.header.setAutoFillBackground(True)
        self.header.setFixedHeight(38)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 6, 8, 6)
        
        # Titre avec icône
        self.title_label = QLabel(f'{self.icon} {self.title}')
        self.title_label.setObjectName('widgetTitle')
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Bouton taille
        self.size_btn = QPushButton('⊡')
        self.size_btn.setObjectName('widgetButton')
        self.size_btn.setToolTip('Changer la taille')
        self.size_btn.setFixedSize(24, 24)
        self.size_btn.clicked.connect(self.show_size_menu)
        header_layout.addWidget(self.size_btn)
        
        # Bouton minimiser
        self.minimize_btn = QPushButton('─')
        self.minimize_btn.setObjectName('widgetButton')
        self.minimize_btn.setToolTip('Minimiser/Restaurer')
        self.minimize_btn.setFixedSize(24, 24)
        self.minimize_btn.clicked.connect(self.toggle_minimize)
        header_layout.addWidget(self.minimize_btn)
        
        # Bouton fermer
        self.close_btn = QPushButton('✕')
        self.close_btn.setObjectName('widgetButtonClose')
        self.close_btn.setToolTip('Masquer le widget')
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.request_close)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(self.header)
        main_layout.setStretchFactor(self.header, 0)
        
        # Conteneur pour le contenu
        self.content_container = QFrame()
        self.content_container.setObjectName('widgetContent')
        self.content_container.setAutoFillBackground(True)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        
        main_layout.addWidget(self.content_container)
        main_layout.setStretchFactor(self.content_container, 1)
        
        # Activer le drag
        self.setAcceptDrops(True)
        self.header.setMouseTracking(True)
    
    def setup_content(self):
        """À surcharger par les widgets enfants."""
        pass
    
    def show_size_menu(self):
        """Affiche le menu de sélection de taille."""
        menu = QMenu(self)
        
        small_action  = menu.addAction('Petit')
        medium_action = menu.addAction('Moyen')
        large_action  = menu.addAction('Grand')
        
        if self.current_size == 'small':
            small_action.setCheckable(True)
            small_action.setChecked(True)
        elif self.current_size == 'medium':
            medium_action.setCheckable(True)
            medium_action.setChecked(True)
        else:
            large_action.setCheckable(True)
            large_action.setChecked(True)
        
        action = menu.exec_(QCursor.pos())
        
        if action == small_action:
            self.change_size('small')
        elif action == medium_action:
            self.change_size('medium')
        elif action == large_action:
            self.change_size('large')
    
    def change_size(self, size):
        """Change la taille du widget."""
        if size != self.current_size:
            self.current_size = size
            self.resizeRequested.emit(self.widget_id, size)
            self.update_size_constraints()
    
    def update_size_constraints(self):
        """Met à jour les contraintes de taille."""
        if self.current_size == 'small':
            self.setMinimumSize(200, 150)
            self.setMaximumSize(300, 200)
        elif self.current_size == 'medium':
            self.setMinimumSize(300, 200)
            self.setMaximumSize(500, 400)
        else:  # large
            self.setMinimumSize(400, 300)
            self.setMaximumSize(16777215, 16777215)
        
        self.adjustSize()
    
    def toggle_minimize(self):
        """Minimise/Restaure le widget."""
        self.is_minimized = not self.is_minimized
        self.content_container.setVisible(not self.is_minimized)
        self.minimize_btn.setText('☐' if self.is_minimized else '─')
        self.minimizeRequested.emit(self.widget_id, self.is_minimized)
        self.adjustSize()
    
    def request_close(self):
        """Demande la fermeture du widget."""
        self.closeRequested.emit(self.widget_id)
    
    def refresh_data(self):
        """Rafraîchit les données du widget. À surcharger."""
        pass

    def on_theme_changed(self, theme_name=None):
        """
        Appelé quand le thème change.
        Reapplique les styles ET rafraîchit les données
        (les widgets enfants utilisent get_widget_styles() dans refresh_data).
        """
        self.apply_styles()
        self.refresh_data()

    def _get_theme(self):
        """Retourne le thème actif (avec fallback sécurisé)."""
        try:
            from app.services.theme_service import theme_service
            return theme_service.get_current_theme()
        except Exception:
            # Fallback thème clair si service indisponible
            return {
                'surface':            '#FFFFFF',
                'surface_alt':        '#F8F9FB',
                'widget_bg':          '#FFFFFF',
                'widget_header':      '#2C5F99',
                'widget_header_text': '#FFFFFF',
                'widget_border':      '#D0D8E8',
                'border':             '#D8DDE8',
                'text':               '#1A2640',
                'text_secondary':     '#6B7A99',
                'hover':              '#EDF1F8',
                'danger':             '#C0392B',
                'danger_bg':          '#FDE8E6',
            }

    def _apply_label_styles(self):
        """Force les couleurs des labels du header (contourne le QSS global QLabel)."""
        t = self._get_theme()
        color = t.get('widget_header_text', '#FFFFFF')
        self.title_label.setStyleSheet(
            f'color: {color}; font-size: 13px; font-weight: bold; letter-spacing: 0.3px;'
        )
        for btn in [self.size_btn, self.minimize_btn, self.close_btn]:
            btn.setStyleSheet(
                f'QPushButton {{ color: {color}; background: transparent; border: none; font-weight: bold; }}'
                f'QPushButton:hover {{ background: rgba(255,255,255,0.18); border-radius: 4px; }}'
            )
        # Bouton close : hover rouge
        self.close_btn.setStyleSheet(
            f'QPushButton {{ color: {color}; background: transparent; border: none; font-weight: bold; }}'
            f'QPushButton:hover {{ background: {t.get("danger","#C0392B")}; color: #FFFFFF; border-radius: 4px; }}'
        )

    def apply_styles(self):
        """
        Applique les styles CSS dynamiquement selon le thème actif.
        [FIX V4.2.1] Remplacement des couleurs hardcodées (#2b2b2b, #ddd, #2c3e50)
        par des variables issues du thème Clair/Sombre.
        """
        t = self._get_theme()

        self.setStyleSheet(f"""
            BaseWidget {{
                background-color: {t['widget_bg']};
                border: 1px solid {t['widget_border']};
                border-radius: 8px;
            }}

            /* ── Header ── */
            #widgetHeader {{
                background-color: {t['widget_header']};
                border-bottom: 1px solid {t['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}

            #widgetTitle {{
                font-size: 13px;
                font-weight: bold;
                color: {t['widget_header_text']};
                letter-spacing: 0.3px;
            }}

            /* ── Boutons header ── */
            #widgetButton {{
                background-color: transparent;
                border: none;
                color: {t['widget_header_text']};
                font-size: 13px;
                font-weight: bold;
            }}

            #widgetButton:hover {{
                background-color: rgba(255, 255, 255, 0.18);
                border-radius: 4px;
            }}

            #widgetButtonClose {{
                background-color: transparent;
                border: none;
                color: {t['widget_header_text']};
                font-size: 13px;
                font-weight: bold;
            }}

            #widgetButtonClose:hover {{
                background-color: {t['danger']};
                color: #FFFFFF;
                border-radius: 4px;
            }}

            /* ── Contenu ── */
            #widgetContent {{
                background-color: {t['widget_bg']};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)
        self._apply_label_styles()
    
    def mousePressEvent(self, event):
        """Gère le début du drag."""
        if event.button() == Qt.LeftButton and self.header.geometry().contains(event.pos()):
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Gère le déplacement pendant le drag."""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if hasattr(self, 'drag_start_position'):
            if (event.pos() - self.drag_start_position).manhattanLength() < 10:
                return
            logger.debug(f'Drag du widget {self.widget_id}')
        
        super().mouseMoveEvent(event)
