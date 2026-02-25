"""
Configuration globale de l'application Budget Manager Pro.
"""
import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"

# Base de données
DATABASE_PATH = DATA_DIR / "budget_manager.db"

# Préférences utilisateur
USER_PREFERENCES_PATH = CONFIG_DIR / "user_preferences.json"

# Application
APP_NAME = "Budget Manager Pro By A.P"
APP_VERSION = "5"
APP_TITLE = f"{APP_NAME} V{APP_VERSION}"

# Limites et seuils
MAX_FILE_SIZE_MB = 50
ALERT_THRESHOLD_BUDGET = 0.80  # Alerte à 80% consommation
ALERT_MONTHS_BEFORE_CONTRACT_END = 3
WARNING_MONTHS_BEFORE_CONTRACT_END = 6

# Pagination
DEFAULT_PAGE_SIZE = 100

# Export
EXPORT_DIR = DATA_DIR / "exports"

# Formats de date
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = DATA_DIR / "app.log"
