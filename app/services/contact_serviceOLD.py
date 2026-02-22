"""
Service de gestion des contacts.
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


class ContactService:
    """Service pour gérer les contacts."""
    
    def __init__(self):
        self.db = db_service
    
    def get_all(self, filters=None):
        """
        Récupère tous les contacts avec filtres optionnels.
        
        Args:
            filters: Dict avec clés optionnelles: type, search, service_id
        
        Returns:
            List of contact rows
        """
        try:
            query = """
                SELECT 
                    c.*,
                    COALESCE(s.code, '') || ' - ' || COALESCE(s.nom, '') as service_nom
                FROM contacts c
                LEFT JOIN services s ON c.service_id = s.id
                WHERE 1=1
            """
            params = []
            
            if filters:
                if 'type' in filters and filters['type']:
                    query += " AND c.type = ?"
                    params.append(filters['type'])
                
                if 'search' in filters and filters['search']:
                    query += " AND (c.nom LIKE ? OR c.prenom LIKE ? OR c.email LIKE ?)"
                    search = f"%{filters['search']}%"
                    params.extend([search, search, search])
                
                if 'service_id' in filters and filters['service_id']:
                    query += " AND c.service_id = ?"
                    params.append(filters['service_id'])
            
            query += " ORDER BY c.nom, c.prenom"
            
            rows = self.db.fetch_all(query, params if params else None)
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur récupération contacts: {e}")
            raise
    
    def get_by_id(self, contact_id):
        """
        Récupère un contact par ID.
        
        Args:
            contact_id: ID du contact
        
        Returns:
            Contact row ou None
        """
        try:
            query = "SELECT * FROM contacts WHERE id = ?"
            row = self.db.fetch_one(query, (contact_id,))
            return row_to_dict(row)
        except Exception as e:
            logger.error(f"Erreur récupération contact {contact_id}: {e}")
            raise
    
    def create(self, data):
        """
        Crée un nouveau contact.
        
        Args:
            data: Dict avec les données du contact
        
        Returns:
            ID du contact créé
        """
        try:
            # Ajouter timestamp
            data['date_creation'] = datetime.now().isoformat()
            
            contact_id = self.db.insert('contacts', data)
            logger.info(f"Contact créé: {contact_id} - {data.get('prenom')} {data.get('nom')}")
            return contact_id
        except Exception as e:
            logger.error(f"Erreur création contact: {e}")
            raise
    
    def update(self, contact_id, data):
        """
        Met à jour un contact.
        
        Args:
            contact_id: ID du contact
            data: Dict avec les données à mettre à jour
        
        Returns:
            None
        """
        try:
            self.db.update('contacts', data, "id = ?", (contact_id,))
            logger.info(f"Contact mis à jour: {contact_id}")
        except Exception as e:
            logger.error(f"Erreur mise à jour contact {contact_id}: {e}")
            raise
    
    def delete(self, contact_id):
        """
        Supprime un contact.
        
        Args:
            contact_id: ID du contact
        
        Returns:
            None
        """
        try:
            self.db.delete('contacts', "id = ?", (contact_id,))
            logger.info(f"Contact supprimé: {contact_id}")
        except Exception as e:
            logger.error(f"Erreur suppression contact {contact_id}: {e}")
            raise
    
    def get_by_type(self, type_contact):
        """
        Récupère tous les contacts d'un type donné.
        
        Args:
            type_contact: Type de contact (ELU, DIRECTION, PRESTATAIRE, AMO)
        
        Returns:
            List of contact rows
        """
        try:
            query = "SELECT * FROM contacts WHERE type = ? ORDER BY nom, prenom"
            rows = self.db.fetch_all(query, (type_contact,))
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur récupération contacts par type: {e}")
            raise
    
    def get_stats(self):
        """
        Retourne des statistiques sur les contacts.
        
        Returns:
            Dict avec les statistiques
        """
        try:
            cursor = self.db.conn.cursor()
            
            stats = {}
            
            # Total contacts
            cursor.execute("SELECT COUNT(*) FROM contacts")
            stats['total'] = cursor.fetchone()[0]
            
            # Par type
            cursor.execute("""
                SELECT type, COUNT(*) as count
                FROM contacts
                GROUP BY type
                ORDER BY count DESC
            """)
            stats['par_type'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Avec email
            cursor.execute("SELECT COUNT(*) FROM contacts WHERE email IS NOT NULL AND email != ''")
            stats['avec_email'] = cursor.fetchone()[0]
            
            # Avec téléphone
            cursor.execute("SELECT COUNT(*) FROM contacts WHERE telephone IS NOT NULL AND telephone != ''")
            stats['avec_telephone'] = cursor.fetchone()[0]
            
            # Par service (pour les types internes)
            cursor.execute("""
                SELECT s.nom, COUNT(c.id) as count
                FROM contacts c
                LEFT JOIN services s ON c.service_id = s.id
                WHERE c.service_id IS NOT NULL
                GROUP BY s.nom
                ORDER BY count DESC
            """)
            stats['par_service'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            logger.info(f"Stats contacts calculées: {stats['total']} total")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur récupération stats contacts: {e}")
            return {
                'total': 0,
                'par_type': {},
                'avec_email': 0,
                'avec_telephone': 0,
                'par_service': {}
            }

# Instance globale
contact_service = ContactService()