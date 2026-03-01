# Service tache pour usage web
import logging
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)

class TacheService:
    def __init__(self):
        self.db = DatabaseService()
    def get_all(self):
        try:
            rows = self.db.fetch_all(
                "SELECT t.*, p.nom as projet_nom, p.code as projet_code "
                "FROM taches t "
                "LEFT JOIN projets p ON p.id = t.projet_id "
                "ORDER BY t.date_echeance ASC NULLS LAST, t.id DESC"
            )
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur taches: {ex}")
            return []
