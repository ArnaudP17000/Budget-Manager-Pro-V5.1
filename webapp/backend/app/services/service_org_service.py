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
                "(SELECT COUNT(*) FROM projets pr WHERE pr.service_id = s.id) as nb_projets, "
                "(SELECT COUNT(*) FROM utilisateurs u WHERE u.service_id = s.id AND u.actif = true) as nb_membres "
                "FROM services s "
                "LEFT JOIN contacts c ON c.id = s.responsable_id "
                "LEFT JOIN services p ON p.id = s.parent_id "
                "ORDER BY s.parent_id NULLS FIRST, s.code"
            )
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur services: {ex}")
            return []

    def get_membres(self, service_id):
        try:
            rows = self.db.fetch_all(
                "SELECT id, nom, prenom, email, role FROM utilisateurs "
                "WHERE service_id = %s AND actif = true ORDER BY nom",
                [service_id]
            )
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur membres service: {ex}")
            return []

    def create(self, data):
        self.db.execute(
            "INSERT INTO services (code, nom, responsable_id, parent_id, nb_personnes, membres_label) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [data.get('code'), data.get('nom'),
             data.get('responsable_id') or None, data.get('parent_id') or None,
             data.get('nb_personnes') or None, data.get('membres_label') or None]
        )

    def update(self, service_id, data):
        self.db.execute(
            "UPDATE services SET code=%s, nom=%s, responsable_id=%s, parent_id=%s, "
            "nb_personnes=%s, membres_label=%s WHERE id=%s",
            [data.get('code'), data.get('nom'),
             data.get('responsable_id') or None, data.get('parent_id') or None,
             data.get('nb_personnes') or None, data.get('membres_label') or None,
             service_id]
        )

    def delete(self, service_id):
        self.db.execute("DELETE FROM services WHERE id=%s", [service_id])
