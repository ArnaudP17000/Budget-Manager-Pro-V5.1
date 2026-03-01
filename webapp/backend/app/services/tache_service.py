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
                "SELECT t.*, p.nom as projet_nom, p.code as projet_code, "
                "u.nom || ' ' || u.prenom as assignee_nom, "
                "u.id as assignee_user_id, "
                "s.nom as assignee_service_nom, s.code as assignee_service_code, "
                "s.is_unite as assignee_is_unite "
                "FROM taches t "
                "LEFT JOIN projets p ON p.id = t.projet_id "
                "LEFT JOIN utilisateurs u ON u.id = t.assignee_id "
                "LEFT JOIN services s ON s.id = u.service_id "
                "ORDER BY t.date_echeance ASC NULLS LAST, t.id DESC"
            )
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur taches: {ex}")
            return []
