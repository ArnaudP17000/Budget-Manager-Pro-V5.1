"""
Widget centre de notifications.
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMenu
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from app.services.notification_service import notification_service, NotificationType

logger = logging.getLogger(__name__)

class NotificationWidget(QWidget):
    """Widget d'affichage d'une notification."""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Couleur de fond selon type
        colors = {
            NotificationType.INFO: "#d1ecf1",
            NotificationType.SUCCESS: "#d4edda",
            NotificationType.WARNING: "#fff3cd",
            NotificationType.ERROR: "#f8d7da"
        }
        
        text_colors = {
            NotificationType.INFO: "#0c5460",
            NotificationType.SUCCESS: "#155724",
            NotificationType.WARNING: "#856404",
            NotificationType.ERROR: "#721c24"
        }
        
        bg_color = colors.get(self.notification.type, "#ffffff")
        text_color = text_colors.get(self.notification.type, "#000000")
        
        self.setStyleSheet(f"""
            background-color: {bg_color};
            border-radius: 5px;
            border: 1px solid {text_color};
        """)
        
        # Titre
        title_label = QLabel(self.notification.title)
        title_label.setStyleSheet(f"font-weight: bold; color: {text_color}; font-size: 12px;")
        layout.addWidget(title_label)
        
        # Message
        message_label = QLabel(self.notification.message)
        message_label.setStyleSheet(f"color: {text_color}; font-size: 11px;")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Heure
        time_label = QLabel(self.notification.created_at.strftime("%H:%M"))
        time_label.setStyleSheet(f"color: {text_color}; font-size: 9px; font-style: italic;")
        layout.addWidget(time_label)
    
    def mousePressEvent(self, event):
        """Gère le clic sur la notification."""
        self.clicked.emit(self.notification.id)
        super().mousePressEvent(event)

class NotificationCenterWidget(QWidget):
    """Widget centre de notifications."""
    
    notification_clicked = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notification_service = notification_service
        self.init_ui()
        
        # S'abonner aux nouvelles notifications
        self.notification_service.add_observer(self.on_new_notification)
        
        # Charger notifications existantes
        self.load_notifications()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout(self)
        
        # En-tête
        header_layout = QHBoxLayout()
        
        title = QLabel("🔔 Notifications")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("""
            background-color: #dc3545;
            color: white;
            border-radius: 10px;
            padding: 2px 8px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.count_label)
        
        header_layout.addStretch()
        
        # Bouton tout marquer comme lu
        mark_all_btn = QPushButton("✓ Tout marquer lu")
        mark_all_btn.clicked.connect(self.mark_all_read)
        header_layout.addWidget(mark_all_btn)
        
        # Bouton effacer
        clear_btn = QPushButton("🗑️ Effacer lues")
        clear_btn.clicked.connect(self.clear_read)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Liste des notifications
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("border: none;")
        layout.addWidget(self.list_widget)
    
    def load_notifications(self):
        """Charge les notifications."""
        self.list_widget.clear()
        
        notifications = self.notification_service.get_all()
        
        for notif in notifications:
            item = QListWidgetItem(self.list_widget)
            widget = NotificationWidget(notif)
            widget.clicked.connect(self.on_notification_clicked)
            
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        
        # Mettre à jour le compteur
        unread_count = self.notification_service.get_unread_count()
        self.count_label.setText(str(unread_count))
        
        if unread_count == 0:
            self.count_label.hide()
        else:
            self.count_label.show()
    
    def on_new_notification(self, notification):
        """Appelé lors d'une nouvelle notification."""
        self.load_notifications()
    
    def on_notification_clicked(self, notification_id):
        """Gère le clic sur une notification."""
        self.notification_service.mark_as_read(notification_id)
        self.load_notifications()
        
        # Émettre signal avec données
        for notif in self.notification_service.get_all():
            if notif.id == notification_id:
                self.notification_clicked.emit(notif.data)
                break
    
    def mark_all_read(self):
        """Marque toutes les notifications comme lues."""
        self.notification_service.mark_all_as_read()
        self.load_notifications()
    
    def clear_read(self):
        """Efface les notifications lues."""
        self.notification_service.clear_read()
        self.load_notifications()

class NotificationBadge(QPushButton):
    """Badge de notification pour la barre d'outils."""
    
    def __init__(self, parent=None):
        super().__init__("🔔", parent)
        self.notification_service = notification_service
        self.setStyleSheet("font-size: 16px; padding: 5px;")
        
        # Timer pour rafraîchir le badge
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_badge)
        self.timer.start(5000)  # Toutes les 5 secondes
        
        self.update_badge()
    
    def update_badge(self):
        """Met à jour le badge."""
        count = self.notification_service.get_unread_count()
        if count > 0:
            self.setText(f"🔔 ({count})")
            self.setStyleSheet("font-size: 16px; padding: 5px; font-weight: bold; color: #dc3545;")
        else:
            self.setText("🔔")
            self.setStyleSheet("font-size: 16px; padding: 5px;")
