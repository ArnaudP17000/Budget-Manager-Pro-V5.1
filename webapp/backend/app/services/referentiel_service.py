# Service référentiels pour usage web
import logging
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)

class ReferentielService:
    def __init__(self):
        self.db = DatabaseService()
    def get_etp(self):
        try:
            rows = self.db.fetch_all("SELECT * FROM etp ORDER BY nom")
            return [_d(r) for r in rows] if rows else []
        except Exception:
            logger.warning("Table etp inexistante")
            return []
    def get_fournisseurs(self):
        rows = self.db.fetch_all("SELECT * FROM fournisseurs ORDER BY nom")
        return [_d(r) for r in rows] if rows else []
    def get_contacts(self):
        rows = self.db.fetch_all("SELECT * FROM contacts ORDER BY nom")
        return [_d(r) for r in rows] if rows else []
    def get_services(self):
        rows = self.db.fetch_all("SELECT * FROM services ORDER BY nom")
        return [_d(r) for r in rows] if rows else []
