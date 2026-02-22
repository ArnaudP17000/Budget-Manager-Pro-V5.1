"""
Service de gestion des services (organigramme).
"""
import logging
from datetime import datetime
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

def row_to_dict(row):
    '''Convertit sqlite3.Row en dict.'''
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return {key: row[key] for key in row.keys()}
    return row


class ServiceService:
    """Service pour gÃ©rer les services."""
    
    def __init__(self):
        self.db = db_service
    
    def get_all(self, filters=None):
        """
        RÃ©cupÃ¨re tous les services avec filtres optionnels.
        
        Args:
            filters: Dict avec clÃ©s optionnelles: search, parent_id
        
        Returns:
            List of service rows
        """
        try:
            query = """
                SELECT 
                    s.*,
                    COALESCE(c.nom, '') || ' ' || COALESCE(c.prenom, '') as responsable_nom,
                    (SELECT COUNT(*) FROM projets WHERE service_id = s.id) as nb_projets
                FROM services s
                LEFT JOIN contacts c ON s.responsable_id = c.id
                WHERE 1=1
            """
            params = []
            
            if filters:
                if 'search' in filters and filters['search']:
                    query += " AND (s.code LIKE ? OR s.nom LIKE ?)"
                    search = f"%{filters['search']}%"
                    params.extend([search, search])
                
                if 'parent_id' in filters:
                    if filters['parent_id'] is None:
                        query += " AND s.parent_id IS NULL"
                    else:
                        query += " AND s.parent_id = ?"
                        params.append(filters['parent_id'])
            
            query += " ORDER BY s.code"
            
            rows = self.db.fetch_all(query, params if params else None)
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur rÃ©cupÃ©ration services: {e}")
            raise
    
    def get_by_id(self, service_id):
        """
        RÃ©cupÃ¨re un service par ID.
        
        Args:
            service_id: ID du service
        
        Returns:
            Service row ou None
        """
        try:
            query = "SELECT * FROM services WHERE id = ?"
            row = self.db.fetch_one(query, (service_id,))
            return row_to_dict(row)
        except Exception as e:
            logger.error(f"Erreur rÃ©cupÃ©ration service {service_id}: {e}")
            raise
    
    def create(self, data):
        """
        CrÃ©e un nouveau service.
        
        Args:
            data: Dict avec les donnÃ©es du service
        
        Returns:
            ID du service crÃ©Ã©
        """
        try:
            # Valider que le code est unique
            if 'code' in data and data['code']:
                existing = self.db.fetch_one(
                    "SELECT id FROM services WHERE code = ?", 
                    (data['code'],)
                )
                if existing:
                    raise ValueError(f"Le code service {data['code']} existe dÃ©jÃ ")
            
            # Ajouter timestamp
            data['date_creation'] = datetime.now().isoformat()
            
            service_id = self.db.insert('services', data)
            logger.info(f"Service crÃ©Ã©: {service_id} - {data.get('code')}")
            return service_id
        except Exception as e:
            logger.error(f"Erreur crÃ©ation service: {e}")
            raise
    
    def update(self, service_id, data):
        """
        Met Ã  jour un service.
        
        Args:
            service_id: ID du service
            data: Dict avec les donnÃ©es Ã  mettre Ã  jour
        
        Returns:
            None
        """
        try:
            # Valider que le code est unique si modifiÃ©
            if 'code' in data and data['code']:
                existing = self.db.fetch_one(
                    "SELECT id FROM services WHERE code = ? AND id != ?", 
                    (data['code'], service_id)
                )
                if existing:
                    raise ValueError(f"Le code service {data['code']} existe dÃ©jÃ ")
            
            self.db.update('services', data, "id = ?", (service_id,))
            logger.info(f"Service mis Ã  jour: {service_id}")
        except Exception as e:
            logger.error(f"Erreur mise Ã  jour service {service_id}: {e}")
            raise
    
    def delete(self, service_id):
        """
        Supprime un service.
        
        Args:
            service_id: ID du service
        
        Returns:
            None
        """
        try:
            self.db.delete('services', "id = ?", (service_id,))
            logger.info(f"Service supprimÃ©: {service_id}")
        except Exception as e:
            logger.error(f"Erreur suppression service {service_id}: {e}")
            raise


    def get_stats(self):
        """Récupère les statistiques des services"""
        try:
            query_total = "SELECT COUNT(*) as total FROM services"
            total_result = self.db.fetch_one(query_total)
            
            query_avec_resp = "SELECT COUNT(*) as count FROM services WHERE responsable_id IS NOT NULL"
            avec_resp_result = self.db.fetch_one(query_avec_resp)
            
            query_sans_resp = "SELECT COUNT(*) as count FROM services WHERE responsable_id IS NULL"
            sans_resp_result = self.db.fetch_one(query_sans_resp)
            
            query_projets = "SELECT COUNT(*) as count FROM projets WHERE service_id IS NOT NULL"
            projets_result = self.db.fetch_one(query_projets)
            
            return {
                'total': total_result['total'] if total_result else 0,
                'avec_responsable': avec_resp_result['count'] if avec_resp_result else 0,
                'sans_responsable': sans_resp_result['count'] if sans_resp_result else 0,
                'total_projets': projets_result['count'] if projets_result else 0
            }
        except Exception as e:
            logger.error(f"Erreur récupération stats services: {e}")
            return {
                'total': 0,
                'avec_responsable': 0,
                'sans_responsable': 0,
                'total_projets': 0
            }

# Instance globale
service_service = ServiceService()
