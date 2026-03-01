# Service contacts pour usage web
import logging
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)


class ContactService:
    def __init__(self):
        self.db = DatabaseService()

    def get_all(self, filters=None):
        try:
            query = (
                "SELECT c.*, s.nom as service_nom "
                "FROM contacts c "
                "LEFT JOIN services s ON s.id = c.service_id "
                "WHERE 1=1"
            )
            params = []
            if filters:
                if filters.get('type'):
                    query += " AND c.type = %s"
                    params.append(filters['type'])
                if filters.get('search'):
                    s = '%' + filters['search'] + '%'
                    query += " AND (c.nom ILIKE %s OR c.prenom ILIKE %s OR c.email ILIKE %s OR c.organisation ILIKE %s)"
                    params.extend([s, s, s, s])
            query += " ORDER BY c.nom, c.prenom"
            rows = self.db.fetch_all(query, params)
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur contacts: {ex}")
            return []

    def create(self, data):
        self.db.execute(
            "INSERT INTO contacts (nom, prenom, fonction, type, telephone, email, service_id, organisation) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('nom'), data.get('prenom'), data.get('fonction'),
             data.get('type'), data.get('telephone'), data.get('email'),
             data.get('service_id') or None, data.get('organisation')]
        )

    def update(self, contact_id, data):
        self.db.execute(
            "UPDATE contacts SET nom=%s, prenom=%s, fonction=%s, type=%s, "
            "telephone=%s, email=%s, service_id=%s, organisation=%s WHERE id=%s",
            [data.get('nom'), data.get('prenom'), data.get('fonction'),
             data.get('type'), data.get('telephone'), data.get('email'),
             data.get('service_id') or None, data.get('organisation'), contact_id]
        )

    def delete(self, contact_id):
        self.db.execute("DELETE FROM contacts WHERE id=%s", [contact_id])
