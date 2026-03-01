# Service organigramme (services) pour usage web
import logging
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)


class ServiceOrgService:
    def __init__(self):
        self.db = DatabaseService()

    def get_all(self):
        try:
            rows = self.db.fetch_all(
                "SELECT s.*, "
                "c.nom || ' ' || c.prenom as responsable_nom, "
                "p.nom as parent_nom, "
                "(SELECT COUNT(*) FROM projets pr WHERE pr.service_id = s.id) as nb_projets "
                "FROM services s "
                "LEFT JOIN contacts c ON c.id = s.responsable_id "
                "LEFT JOIN services p ON p.id = s.parent_id "
                "ORDER BY s.code"
            )
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur services: {ex}")
            return []

    def create(self, data):
        self.db.execute(
            "INSERT INTO services (code, nom, responsable_id, parent_id) VALUES (%s, %s, %s, %s)",
            [data.get('code'), data.get('nom'),
             data.get('responsable_id') or None, data.get('parent_id') or None]
        )

    def update(self, service_id, data):
        self.db.execute(
            "UPDATE services SET code=%s, nom=%s, responsable_id=%s, parent_id=%s WHERE id=%s",
            [data.get('code'), data.get('nom'),
             data.get('responsable_id') or None, data.get('parent_id') or None,
             service_id]
        )

    def delete(self, service_id):
        self.db.execute("DELETE FROM services WHERE id=%s", [service_id])
