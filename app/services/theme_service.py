"""
Service de gestion des thèmes (Clair/Sombre).
"""
import json
import logging
from pathlib import Path
from config.settings import USER_PREFERENCES_PATH
from config.themes import THEMES, get_stylesheet

logger = logging.getLogger(__name__)

class ThemeService:
    """Service de gestion des thèmes."""
    
    def __init__(self):
        self.current_theme_name = "Clair"
        self.load_preferences()
    
    def load_preferences(self):
        """Charge les préférences utilisateur."""
        try:
            if USER_PREFERENCES_PATH.exists():
                with open(USER_PREFERENCES_PATH, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    self.current_theme_name = prefs.get('theme', 'Clair')
        except Exception as e:
            logger.error(f"Erreur chargement préférences: {e}")
            self.current_theme_name = "Clair"
    
    def save_preferences(self, theme_name):
        """Sauvegarde les préférences utilisateur."""
        try:
            prefs = {}
            if USER_PREFERENCES_PATH.exists():
                with open(USER_PREFERENCES_PATH, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            
            prefs['theme'] = theme_name
            
            with open(USER_PREFERENCES_PATH, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Thème sauvegardé: {theme_name}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde préférences: {e}")
    
    def get_current_theme(self):
        """Retourne le thème actuel."""
        return THEMES.get(self.current_theme_name, THEMES["Clair"])
    
    def get_current_theme_name(self):
        """Retourne le nom du thème actuel."""
        return self.current_theme_name
    
    def set_theme(self, theme_name):
        """Change le thème actuel."""
        if theme_name in THEMES:
            self.current_theme_name = theme_name
            self.save_preferences(theme_name)
            return True
        return False
    
    def get_stylesheet(self):
        """Retourne le stylesheet CSS du thème actuel."""
        theme = self.get_current_theme()
        return get_stylesheet(theme)
    
    def get_available_themes(self):
        """Retourne la liste des thèmes disponibles."""
        return list(THEMES.keys())

# Instance globale
theme_service = ThemeService()
