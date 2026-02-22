"""Gestionnaire de widgets pour le dashboard."""
import logging
from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QFrame, QVBoxLayout,
    QDialog, QListWidget, QPushButton, QHBoxLayout,
    QLabel, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag

logger = logging.getLogger(__name__)


class WidgetManager(QWidget):
    """Gestionnaire de widgets avec grid layout personnalisable."""
    
    # Signaux
    widgetAdded = pyqtSignal(str)  # widget_id
    widgetRemoved = pyqtSignal(str)  # widget_id
    layoutChanged = pyqtSignal()  # Layout modifié
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widgets = {}  # {widget_id: widget_instance}
        self.positions = {}  # {widget_id: (row, col, rowspan, colspan)}
        self.available_widgets = []  # Liste des widgets disponibles
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Barre d'outils
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Grid container
        self.grid_container = QFrame()
        self.grid_container.setObjectName('gridContainer')
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        
        layout.addWidget(self.grid_container)
        
        # Appliquer les styles
        self.apply_styles()
    
    def create_toolbar(self):
        """Crée la barre d'outils."""
        toolbar = QFrame()
        toolbar.setObjectName('toolbar')
        toolbar.setFixedHeight(50)
        
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)
        
        # Titre
        title = QLabel('📊 Dashboard Avancé')
        title.setObjectName('dashboardTitle')
        toolbar_layout.addWidget(title)
        
        toolbar_layout.addStretch()
        
        # Bouton ajouter widget
        add_btn = QPushButton('➕ Ajouter Widget')
        add_btn.setObjectName('toolbarButton')
        add_btn.clicked.connect(self.show_add_widget_dialog)
        toolbar_layout.addWidget(add_btn)
        
        # Bouton réorganiser
        reorganize_btn = QPushButton('🔄 Réorganiser')
        reorganize_btn.setObjectName('toolbarButton')
        reorganize_btn.setToolTip('Réorganiser automatiquement les widgets')
        reorganize_btn.clicked.connect(self.auto_reorganize)
        toolbar_layout.addWidget(reorganize_btn)
        
        # Bouton réinitialiser
        reset_btn = QPushButton('↺ Réinitialiser')
        reset_btn.setObjectName('toolbarButtonSecondary')
        reset_btn.setToolTip('Restaurer la disposition par défaut')
        reset_btn.clicked.connect(self.reset_to_default)
        toolbar_layout.addWidget(reset_btn)
        
        
        # Bouton gérer backups
        backup_btn = QPushButton('📦 Sauvegardes')
        backup_btn.setObjectName('toolbarButtonSecondary')
        backup_btn.setToolTip('Gérer les sauvegardes')
        backup_btn.clicked.connect(self.show_backup_manager)
        toolbar_layout.addWidget(backup_btn)

        # Bouton sauvegarder
        save_btn = QPushButton('💾 Sauvegarder')
        save_btn.setObjectName('toolbarButton')
        save_btn.setToolTip('Sauvegarder la disposition actuelle')
        save_btn.clicked.connect(self.save_layout)
        toolbar_layout.addWidget(save_btn)
        
        return toolbar
    
    def add_widget(self, widget, row=None, col=None, rowspan=1, colspan=1):
        """Ajoute un widget au grid."""
        try:
            widget_id = widget.widget_id
            
            # Si position non spécifiée, trouver une position libre
            if row is None or col is None:
                row, col = self.find_free_position()
            
            # Ajouter au grid
            self.grid_layout.addWidget(widget, row, col, rowspan, colspan)
            
            # Enregistrer
            self.widgets[widget_id] = widget
            self.positions[widget_id] = (row, col, rowspan, colspan)
            
            # Connecter les signaux
            widget.closeRequested.connect(self.remove_widget)
            widget.minimizeRequested.connect(self.on_widget_minimize)
            widget.resizeRequested.connect(self.on_widget_resize)
            
            logger.info(f'✅ Widget {widget_id} ajouté à ({row}, {col})')
            self.widgetAdded.emit(widget_id)
            self.layoutChanged.emit()
            
            return True
            
        except Exception as e:
            logger.error(f'Erreur ajout widget: {e}', exc_info=True)
            return False
    
    def remove_widget(self, widget_id):
        """Retire un widget du grid."""
        try:
            if widget_id not in self.widgets:
                return
            
            # Confirmation
            reply = QMessageBox.question(
                self,
                'Confirmation',
                f'Masquer le widget ?',
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                widget = self.widgets[widget_id]
                
                # Retirer du grid
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()
                
                # Nettoyer les références
                del self.widgets[widget_id]
                del self.positions[widget_id]
                
                logger.info(f'✅ Widget {widget_id} retiré')
                self.widgetRemoved.emit(widget_id)
                self.layoutChanged.emit()
                
                # Réorganiser automatiquement
                self.auto_reorganize()
        
        except Exception as e:
            logger.error(f'Erreur retrait widget: {e}', exc_info=True)
    
    def on_widget_minimize(self, widget_id, is_minimized):
        """Gère la minimisation d'un widget."""
        logger.debug(f'Widget {widget_id} minimisé: {is_minimized}')
        self.layoutChanged.emit()
    
    def on_widget_resize(self, widget_id, size):
        """Gère le redimensionnement d'un widget."""
        try:
            if widget_id not in self.positions:
                return
            
            row, col, _, _ = self.positions[widget_id]
            
            # Définir les spans selon la taille
            if size == 'small':
                rowspan, colspan = 1, 1
            elif size == 'medium':
                rowspan, colspan = 1, 2
            else:  # large
                rowspan, colspan = 2, 2
            
            # Réappliquer au grid
            widget = self.widgets[widget_id]
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, row, col, rowspan, colspan)
            
            # Mettre à jour la position
            self.positions[widget_id] = (row, col, rowspan, colspan)
            
            logger.info(f'✅ Widget {widget_id} redimensionné: {size}')
            self.layoutChanged.emit()
            
        except Exception as e:
            logger.error(f'Erreur redimensionnement widget: {e}', exc_info=True)
    
    def find_free_position(self):
        """Trouve une position libre dans le grid."""
        # Parcourir le grid pour trouver un emplacement libre
        max_row = 0
        max_col = 0
        
        for row, col, rowspan, colspan in self.positions.values():
            max_row = max(max_row, row + rowspan)
            max_col = max(max_col, col + colspan)
        
        # Chercher une position libre
        for row in range(max_row + 1):
            for col in range(3):  # Max 3 colonnes
                if self.is_position_free(row, col):
                    return row, col
        
        # Si aucune position libre, ajouter une nouvelle ligne
        return max_row, 0
    
    def is_position_free(self, row, col):
        """Vérifie si une position est libre."""
        for widget_id, (r, c, rs, cs) in self.positions.items():
            if (r <= row < r + rs) and (c <= col < c + cs):
                return False
        return True
    
    def auto_reorganize(self):
        """Réorganise automatiquement les widgets."""
        try:
            logger.info('🔄 Réorganisation automatique...')
            
            # Récupérer tous les widgets
            widgets_list = list(self.widgets.items())
            
            if not widgets_list:
                return
            
            # Retirer tous les widgets du grid
            for widget_id, widget in widgets_list:
                self.grid_layout.removeWidget(widget)
            
            # Réorganiser en grille optimale
            col = 0
            row = 0
            max_cols = 3  # Maximum 3 colonnes
            
            for widget_id, widget in widgets_list:
                # Déterminer le span selon la taille actuelle
                size = widget.current_size
                if size == 'small':
                    rowspan, colspan = 1, 1
                elif size == 'medium':
                    rowspan, colspan = 1, 2
                else:  # large
                    rowspan, colspan = 2, 2
                
                # Vérifier si ça rentre dans la ligne actuelle
                if col + colspan > max_cols:
                    row += 1
                    col = 0
                
                # Ajouter au grid
                self.grid_layout.addWidget(widget, row, col, rowspan, colspan)
                self.positions[widget_id] = (row, col, rowspan, colspan)
                
                # Passer à la colonne suivante
                col += colspan
                
                if col >= max_cols:
                    row += 1
                    col = 0
            
            logger.info('✅ Réorganisation terminée')
            self.layoutChanged.emit()
            
        except Exception as e:
            logger.error(f'Erreur réorganisation: {e}', exc_info=True)
    
    def show_add_widget_dialog(self):
        """Affiche le dialogue d'ajout de widget."""
        dialog = AddWidgetDialog(self.get_available_widgets(), self)
        
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_selected_widget()
            if selected:
                self.create_and_add_widget(selected)
    
    def get_available_widgets(self):
        """Retourne la liste des widgets disponibles."""
        all_widgets = [
            {'id': 'kpi_finances', 'name': '💰 KPI Finances', 'class': 'KPIWidget'},
            {'id': 'alertes', 'name': '🔔 Alertes', 'class': 'AlertWidget'},
            {'id': 'top_projets', 'name': '📁 Top Projets', 'class': 'ProjectWidget'},
            {'id': 'meteo_budgetaire', 'name': '🌤️ Météo Budgétaire', 'class': 'MeteoWidget'},
            {'id': 'graphique_evolution', 'name': '📈 Graphique Évolution', 'class': 'ChartWidget'},
            {'id': 'calendrier', 'name': '📅 Calendrier', 'class': 'CalendarWidget'},
        ]
        
        # Filtrer les widgets déjà ajoutés
        available = [w for w in all_widgets if w['id'] not in self.widgets]
        
        return available
    
    def create_and_add_widget(self, widget_info):
        """Crée et ajoute un widget."""
        try:
            widget_class = widget_info['class']
            
            # Importer et instancier le widget
            from .widgets import KPIWidget, AlertWidget, ProjectWidget, MeteoWidget
            from .widgets.chart_widget import ChartWidget
            
            widget_map = {
                'KPIWidget': KPIWidget,
                'AlertWidget': AlertWidget,
                'ProjectWidget': ProjectWidget,
                'MeteoWidget': MeteoWidget,
                'ChartWidget': ChartWidget,
            }
            
            if widget_class in widget_map:
                widget = widget_map[widget_class](self)
                self.add_widget(widget)
                
                QMessageBox.information(
                    self,
                    'Widget ajouté',
                    f"Le widget {widget_info['name']} a été ajouté au dashboard."
                )
            else:
                QMessageBox.warning(
                    self,
                    'Widget non disponible',
                    f"Le widget {widget_class} n'est pas encore implémenté."
                )
        
        except Exception as e:
            logger.error(f'Erreur création widget: {e}', exc_info=True)
            QMessageBox.critical(
                self,
                'Erreur',
                f'Erreur lors de la création du widget: {e}'
            )
    
    def reset_to_default(self):
        """Réinitialise la disposition par défaut."""
        reply = QMessageBox.question(
            self,
            'Confirmation',
            'Réinitialiser la disposition par défaut ?\n\nTous les widgets actuels seront supprimés.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Retirer tous les widgets
            for widget_id in list(self.widgets.keys()):
                widget = self.widgets[widget_id]
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()
            
            self.widgets.clear()
            self.positions.clear()
            
            # Ajouter les widgets par défaut
            self.load_default_layout()
    
    def load_default_layout(self):
        """Charge la disposition par défaut."""
        try:
            from .widgets import KPIWidget, AlertWidget, ProjectWidget, MeteoWidget
            
            # Layout par défaut:
            # Row 0: KPI (colspan=2) | Alertes (colspan=1)
            # Row 1: Top Projets (colspan=2) | Météo (colspan=1)
            
            kpi = KPIWidget(self)
            self.add_widget(kpi, row=0, col=0, rowspan=1, colspan=2)
            
            alert = AlertWidget(self)
            self.add_widget(alert, row=0, col=2, rowspan=1, colspan=1)
            
            projects = ProjectWidget(self)
            self.add_widget(projects, row=1, col=0, rowspan=1, colspan=2)
            
            meteo = MeteoWidget(self)
            self.add_widget(meteo, row=1, col=2, rowspan=1, colspan=1)
            
            logger.info('✅ Layout par défaut chargé')
            
        except Exception as e:
            logger.error(f'Erreur chargement layout par défaut: {e}', exc_info=True)
    
    def save_layout(self):
        """Sauvegarde la disposition actuelle."""
        try:
            from .widget_config import widget_config as config
            layout_data = {
                'widgets': {},
                'positions': {}
            }
            
            for widget_id, widget in self.widgets.items():
                layout_data['widgets'][widget_id] = {
                    'class': widget.__class__.__name__,
                    'size': widget.current_size,
                    'minimized': widget.is_minimized
                }
                
                layout_data['positions'][widget_id] = list(self.positions[widget_id])
            
            config.save_layout(layout_data)
            
            QMessageBox.information(
                self,
                'Sauvegarde',
                'La disposition a été sauvegardée avec succès !'
            )
            
            logger.info('✅ Layout sauvegardé')
            
        except Exception as e:
            logger.error(f'Erreur sauvegarde layout: {e}', exc_info=True)
            QMessageBox.warning(
                self,
                'Erreur',
                f'Erreur lors de la sauvegarde: {e}'
            )
    
    def load_layout(self):
        """Charge la disposition sauvegardée (délègue à load_layout_from_config)."""
        self.load_layout_from_config()
    

    def load_layout_from_config(self):
        '''Charge la disposition depuis la configuration sauvegardée.'''
        try:
            from .widget_config import widget_config
            
            layout_data = widget_config.load_layout()
            
            if not layout_data:
                logger.info('Aucune configuration trouvée, chargement layout par défaut')
                self.load_default_layout()
                return
            
            logger.info('📥 Chargement layout depuis configuration...')
            
            # Nettoyer les widgets existants
            for widget_id in list(self.widgets.keys()):
                widget = self.widgets[widget_id]
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()
            
            self.widgets.clear()
            self.positions.clear()
            
            # Recréer les widgets
            from .widgets import KPIWidget, AlertWidget, ProjectWidget, MeteoWidget
            from .widgets.chart_widget import ChartWidget
            
            widget_classes = {
                'KPIWidget': KPIWidget,
                'AlertWidget': AlertWidget,
                'ProjectWidget': ProjectWidget,
                'MeteoWidget': MeteoWidget,
                'ChartWidget': ChartWidget,
            }
            
            widgets_data = layout_data.get('widgets', {})
            positions_data = layout_data.get('positions', {})
            
            for widget_id, widget_info in widgets_data.items():
                try:
                    # Créer le widget
                    widget_class_name = widget_info.get('class')
                    
                    if widget_class_name not in widget_classes:
                        logger.warning(f'Widget non disponible: {widget_class_name}')
                        continue
                    
                    widget_class = widget_classes[widget_class_name]
                    widget = widget_class(self)
                    
                    # Restaurer l'état
                    widget.current_size = widget_info.get('size', 'medium')
                    widget.update_size_constraints()
                    
                    if widget_info.get('minimized', False):
                        widget.toggle_minimize()
                    
                    # Récupérer la position
                    position = positions_data.get(widget_id, [0, 0, 1, 1])
                    row, col, rowspan, colspan = position
                    
                    # Ajouter au grid
                    self.add_widget(widget, row, col, rowspan, colspan)
                    
                except Exception as e:
                    logger.error(f'Erreur chargement widget {widget_id}: {e}')
            
            logger.info(f'✅ {len(self.widgets)} widget(s) chargé(s)')
            
        except Exception as e:
            logger.error(f'Erreur chargement layout: {e}', exc_info=True)
            self.load_default_layout()


    def show_backup_manager(self):
        '''Affiche le gestionnaire de sauvegardes.'''
        try:
            from .backup_manager_dialog import BackupManagerDialog
            from .widget_config import widget_config
            
            dialog = BackupManagerDialog(widget_config, self)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f'Erreur ouverture backup manager: {e}', exc_info=True)
            QMessageBox.critical(
                self,
                'Erreur',
                f'Erreur lors de l\'ouverture du gestionnaire de sauvegardes:\n{e}'
            )

    def apply_styles(self):
        """Applique les styles CSS dynamiquement selon le thème actif."""
        try:
            from app.services.theme_service import theme_service
            t = theme_service.get_current_theme()
        except Exception:
            t = {
                'background': '#F0F2F5', 'surface': '#FFFFFF',
                'primary': '#2C5F99', 'secondary': '#4A7FC1',
                'text': '#1A2640', 'text_secondary': '#6B7A99',
                'text_on_primary': '#FFFFFF',
                'border': '#D8DDE8', 'hover': '#EDF1F8',
                'widget_header': '#2C5F99',
            }
        self.setStyleSheet(f"""
            #gridContainer {{
                background-color: {t['background']};
            }}
            #toolbar {{
                background-color: {t['widget_header']};
                border-bottom: 2px solid {t['border']};
            }}
            #dashboardTitle {{
                font-size: 18px;
                font-weight: bold;
                color: {t['text_on_primary']};
            }}
            #toolbarButton {{
                background-color: {t['primary']};
                color: {t['text_on_primary']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            #toolbarButton:hover {{
                background-color: {t['secondary']};
            }}
            #toolbarButtonSecondary {{
                background-color: rgba(255,255,255,0.15);
                color: {t['text_on_primary']};
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            #toolbarButtonSecondary:hover {{
                background-color: rgba(255,255,255,0.25);
            }}
        """)

    def on_theme_changed(self, theme_name=None):
        """Propage le changement de thème à tous les widgets."""
        self.apply_styles()
        for widget in self.widgets.values():
            if hasattr(widget, 'on_theme_changed'):
                widget.on_theme_changed(theme_name)


class AddWidgetDialog(QDialog):
    """Dialogue de sélection de widget à ajouter."""
    
    def __init__(self, available_widgets, parent=None):
        super().__init__(parent)
        self.available_widgets = available_widgets
        self.selected_widget = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface."""
        self.setWindowTitle('Ajouter un widget')
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel('Sélectionnez un widget à ajouter:')
        title.setStyleSheet('font-weight: bold; font-size: 14px; margin-bottom: 10px;')
        layout.addWidget(title)
        
        # Liste des widgets
        self.widget_list = QListWidget()
        self.widget_list.setStyleSheet('''
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QListWidget::item:selected {
                background-color: #2196f3;
                color: black;
            }
        ''')
        
        for widget in self.available_widgets:
            item = QListWidgetItem(widget['name'])
            item.setData(Qt.UserRole, widget)
            self.widget_list.addItem(item)
        
        self.widget_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.widget_list)
        
        # Boutons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton('Annuler')
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton('Ajouter')
        add_btn.setFixedWidth(100)
        add_btn.setStyleSheet('''
            QPushButton {
                background-color: #2196f3;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        ''')
        add_btn.clicked.connect(self.on_add_clicked)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
    
    def on_item_double_clicked(self, item):
        """Gère le double-clic sur un item."""
        self.selected_widget = item.data(Qt.UserRole)
        self.accept()
    
    def on_add_clicked(self):
        """Gère le clic sur Ajouter."""
        current_item = self.widget_list.currentItem()
        if current_item:
            self.selected_widget = current_item.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                'Sélection requise',
                'Veuillez sélectionner un widget.'
            )
    
    def get_selected_widget(self):
        """Retourne le widget sélectionné."""
        return self.selected_widget




