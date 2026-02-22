"""
Service de notifications et alertes pour AP/CP.
"""
import logging
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types de notifications."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

class NotificationPriority(Enum):
    """Priorités des notifications."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Notification:
    """Classe représentant une notification."""
    
    def __init__(self, title: str, message: str, 
                 notification_type: NotificationType = NotificationType.INFO,
                 priority: NotificationPriority = NotificationPriority.MEDIUM,
                 data: Optional[Dict] = None):
        self.id = f"{datetime.now().timestamp()}"
        self.title = title
        self.message = message
        self.type = notification_type
        self.priority = priority
        self.data = data or {}
        self.created_at = datetime.now()
        self.read = False
    
    def to_dict(self):
        """Convertit en dictionnaire."""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type.value,
            'priority': self.priority.value,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'read': self.read
        }

class NotificationService:
    """Service de gestion des notifications."""
    
    def __init__(self):
        self.notifications: List[Notification] = []
        self.observers = []
    
    def add_observer(self, callback):
        """Ajoute un observateur qui sera notifié des nouvelles notifications."""
        self.observers.append(callback)
    
    def remove_observer(self, callback):
        """Supprime un observateur."""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def notify_observers(self, notification: Notification):
        """Notifie tous les observateurs."""
        for callback in self.observers:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Erreur notification observateur: {e}")
    
    def add_notification(self, title: str, message: str,
                        notification_type: NotificationType = NotificationType.INFO,
                        priority: NotificationPriority = NotificationPriority.MEDIUM,
                        data: Optional[Dict] = None):
        """Ajoute une nouvelle notification."""
        notification = Notification(title, message, notification_type, priority, data)
        self.notifications.insert(0, notification)  # Ajouter au début
        
        logger.info(f"Nouvelle notification: {title} [{notification_type.value}]")
        
        # Notifier les observateurs
        self.notify_observers(notification)
        
        # Limiter à 100 notifications max
        if len(self.notifications) > 100:
            self.notifications = self.notifications[:100]
        
        return notification
    
    def get_unread_count(self):
        """Retourne le nombre de notifications non lues."""
        return sum(1 for n in self.notifications if not n.read)
    
    def get_all(self, unread_only=False):
        """Récupère toutes les notifications."""
        if unread_only:
            return [n for n in self.notifications if not n.read]
        return self.notifications
    
    def mark_as_read(self, notification_id: str):
        """Marque une notification comme lue."""
        for notif in self.notifications:
            if notif.id == notification_id:
                notif.read = True
                break
    
    def mark_all_as_read(self):
        """Marque toutes les notifications comme lues."""
        for notif in self.notifications:
            notif.read = False
    
    def clear_all(self):
        """Efface toutes les notifications."""
        self.notifications.clear()
    
    def clear_read(self):
        """Efface les notifications lues."""
        self.notifications = [n for n in self.notifications if not n.read]

# Instance globale
notification_service = NotificationService()
