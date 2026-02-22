"""
Service de gestion des tâches.
"""
import logging
from datetime import datetime
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

class TacheService:
    """Service pour gérer les tâches."""
    
    def __init__(self):
        self.db = db_service
    
    def get_all(self, filters=None):
        """
        Récupère toutes les tâches avec filtres optionnels.
        
        Args:
            filters: Dict avec clés optionnelles: projet_id, statut, priorite, assignee_id
        
        Returns:
            List of tache rows
        """
        try:
            query = """
                SELECT 
                    t.*,
                    p.nom as projet_nom,
                    p.code as projet_code,
                    u.nom || ' ' || u.prenom as assignee_nom
                FROM taches t
                LEFT JOIN projets p ON t.projet_id = p.id
                LEFT JOIN utilisateurs u ON t.assignee_id = u.id OR t.assigne_a = u.id
                WHERE 1=1
            """
            params = []
            
            if filters:
                if 'projet_id' in filters and filters['projet_id']:
                    query += " AND t.projet_id = ?"
                    params.append(filters['projet_id'])
                
                if 'statut' in filters and filters['statut']:
                    query += " AND t.statut = ?"
                    params.append(filters['statut'])
                
                if 'priorite' in filters and filters['priorite']:
                    query += " AND t.priorite = ?"
                    params.append(filters['priorite'])
                
                if 'assignee_id' in filters and filters['assignee_id']:
                    query += " AND (t.assignee_id = ? OR t.assigne_a = ?)"
                    params.extend([filters['assignee_id'], filters['assignee_id']])
                
                if 'search' in filters and filters['search']:
                    query += " AND (t.titre LIKE ? OR t.description LIKE ?)"
                    search = f"%{filters['search']}%"
                    params.extend([search, search])
            
            query += " ORDER BY "
            query += "CASE t.priorite "
            query += "WHEN 'CRITIQUE' THEN 1 "
            query += "WHEN 'HAUTE' THEN 2 "
            query += "WHEN 'MOYENNE' THEN 3 "
            query += "WHEN 'BASSE' THEN 4 "
            query += "ELSE 5 END, "
            query += "t.date_echeance ASC NULLS LAST"
            
            return self.db.fetch_all(query, params if params else None)
        except Exception as e:
            logger.error(f"Erreur récupération tâches: {e}")
            raise
    
    def get_by_id(self, tache_id):
        """
        Récupère une tâche par ID.
        
        Args:
            tache_id: ID de la tâche
        
        Returns:
            Tache row ou None
        """
        try:
            query = "SELECT * FROM taches WHERE id = ?"
            result = self.db.fetch_one(query, (tache_id,))
            return result
        except Exception as e:
            logger.error(f"Erreur récupération tâche {tache_id}: {e}")
            raise
    
    def create(self, data):
        """
        Crée une nouvelle tâche.
        
        Args:
            data: Dict avec les données de la tâche
        
        Returns:
            ID de la tâche créée
        """
        try:
            # Ajouter timestamp si pas présent
            if 'date_creation' not in data:
                data['date_creation'] = datetime.now().date().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            # Assigner assignee_id aussi à assigne_a pour compatibilité
            if 'assignee_id' in data and data['assignee_id']:
                data['assigne_a'] = data['assignee_id']
            elif 'assigne_a' in data and data['assigne_a']:
                data['assignee_id'] = data['assigne_a']
            
            tache_id = self.db.insert('taches', data)
            logger.info(f"Tâche créée: {tache_id} - {data.get('titre')}")
            return tache_id
        except Exception as e:
            logger.error(f"Erreur création tâche: {e}")
            raise
    
    def update(self, tache_id, data):
        """
        Met à jour une tâche.
        
        Args:
            tache_id: ID de la tâche
            data: Dict avec les données à mettre à jour
        
        Returns:
            None
        """
        try:
            data['updated_at'] = datetime.now().isoformat()
            
            # Synchroniser assignee_id et assigne_a
            if 'assignee_id' in data and data['assignee_id']:
                data['assigne_a'] = data['assignee_id']
            elif 'assigne_a' in data and data['assigne_a']:
                data['assignee_id'] = data['assigne_a']
            
            self.db.update('taches', data, "id = ?", (tache_id,))
            logger.info(f"Tâche mise à jour: {tache_id}")
        except Exception as e:
            logger.error(f"Erreur mise à jour tâche {tache_id}: {e}")
            raise
    
    def delete(self, tache_id):
        """
        Supprime une tâche.
        
        Args:
            tache_id: ID de la tâche
        
        Returns:
            None
        """
        try:
            self.db.delete('taches', "id = ?", (tache_id,))
            logger.info(f"Tâche supprimée: {tache_id}")
        except Exception as e:
            logger.error(f"Erreur suppression tâche {tache_id}: {e}")
            raise
    
    def get_stats(self):
        """
        Récupère les statistiques des tâches pour les KPI.
        
        Returns:
            Dict avec les statistiques
        """
        try:
            stats = {}
            
            # Total de tâches
            result = self.db.fetch_one("SELECT COUNT(*) as count FROM taches")
            stats['total'] = result['count'] if result else 0
            
            # Par statut
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM taches WHERE statut = 'A_FAIRE'"
            )
            stats['a_faire'] = result['count'] if result else 0
            
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM taches WHERE statut = 'EN_COURS'"
            )
            stats['en_cours'] = result['count'] if result else 0
            
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM taches WHERE statut = 'BLOQUE'"
            )
            stats['bloquees'] = result['count'] if result else 0
            
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM taches WHERE statut = 'TERMINE'"
            )
            stats['terminees'] = result['count'] if result else 0
            
            # Tâches en retard
            result = self.db.fetch_one(
                """SELECT COUNT(*) as count FROM taches 
                   WHERE date_echeance < date('now') 
                   AND statut NOT IN ('TERMINE', 'ANNULE')"""
            )
            stats['en_retard'] = result['count'] if result else 0
            
            return stats
        except Exception as e:
            logger.error(f"Erreur récupération statistiques tâches: {e}")
            return {
                'total': 0,
                'a_faire': 0,
                'en_cours': 0,
                'bloquees': 0,
                'terminees': 0,
                'en_retard': 0
            }

# Instance globale
tache_service = TacheService()
