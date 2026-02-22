"""
Service de gestion des projets.
"""
import logging
from datetime import datetime
from app.services.database_service import db_service

def row_to_dict(row):
    """Convertit sqlite3.Row en dict."""
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)

class ProjetService:
    """Service pour gérer les projets."""
    
    def __init__(self):
        self.db = db_service
    
    def get_all(self, filters=None):
        """
        Récupère tous les projets avec filtres optionnels.
        
        Args:
            filters: Dict avec clés optionnelles: statut, search, budget_min, budget_max
        
        Returns:
            List of projet rows
        """
        try:
            query = """
                SELECT 
                    p.*,
                    u1.nom || ' ' || u1.prenom as chef_projet_nom,
                    u2.nom || ' ' || u2.prenom as responsable_nom
                FROM projets p
                LEFT JOIN utilisateurs u1 ON p.chef_projet_id = u1.id
                LEFT JOIN utilisateurs u2 ON p.responsable_id = u2.id
                WHERE 1=1
            """
            params = []
            
            if filters:
                if 'statut' in filters and filters['statut']:
                    query += " AND p.statut = ?"
                    params.append(filters['statut'])
                
                if 'search' in filters and filters['search']:
                    query += " AND (p.code LIKE ? OR p.nom LIKE ? OR p.description LIKE ?)"
                    search = f"%{filters['search']}%"
                    params.extend([search, search, search])
                
                if 'budget_min' in filters and filters['budget_min'] is not None:
                    query += " AND (p.budget_initial >= ? OR p.budget_estime >= ?)"
                    params.extend([filters['budget_min'], filters['budget_min']])
                
                if 'budget_max' in filters and filters['budget_max'] is not None:
                    query += " AND (p.budget_initial <= ? OR p.budget_estime <= ?)"
                    params.extend([filters['budget_max'], filters['budget_max']])
            
            query += " ORDER BY p.date_creation DESC"
            
            rows = self.db.fetch_all(query, params if params else None)
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            raise
    
    def get_by_id(self, projet_id):
        """
        Récupère un projet par ID.
        
        Args:
            projet_id: ID du projet
        
        Returns:
            Projet row ou None
        """
        try:
            query = "SELECT * FROM projets WHERE id = ?"
            result = self.db.fetch_one(query, (projet_id,))
            return result
        except Exception as e:
            logger.error(f"Erreur récupération projet {projet_id}: {e}")
            raise
    
    def create(self, data):
        """
        Crée un nouveau projet.
        
        Args:
            data: Dict avec les données du projet
        
        Returns:
            ID du projet créé
        """
        try:
            # Valider que le code est unique s'il est fourni
            if 'code' in data and data['code']:
                existing = self.db.fetch_one(
                    "SELECT id FROM projets WHERE code = ?", 
                    (data['code'],)
                )
                if existing:
                    raise ValueError(f"Le code projet {data['code']} existe déjà")
            
            # Générer un code si non fourni
            if 'code' not in data or not data['code']:
                data['code'] = self._generate_code()
            
            # Ajouter timestamp
            data['date_creation'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            projet_id = self.db.insert('projets', data)
            logger.info(f"Projet créé: {projet_id} - {data.get('nom')}")
            return projet_id
        except Exception as e:
            logger.error(f"Erreur création projet: {e}")
            raise
    
    def update(self, projet_id, data):
        """
        Met à jour un projet.
        
        Args:
            projet_id: ID du projet
            data: Dict avec les données à mettre à jour
        
        Returns:
            None
        """
        try:
            # Valider que le code est unique si modifié
            if 'code' in data and data['code']:
                existing = self.db.fetch_one(
                    "SELECT id FROM projets WHERE code = ? AND id != ?", 
                    (data['code'], projet_id)
                )
                if existing:
                    raise ValueError(f"Le code projet {data['code']} existe déjà")
            
            data['updated_at'] = datetime.now().isoformat()
            self.db.update('projets', data, "id = ?", (projet_id,))
            logger.info(f"Projet mis à jour: {projet_id}")
        except Exception as e:
            logger.error(f"Erreur mise à jour projet {projet_id}: {e}")
            raise
    
    def delete(self, projet_id):
        """
        Supprime un projet.
        
        Args:
            projet_id: ID du projet
        
        Returns:
            None
        """
        try:
            self.db.delete('projets', "id = ?", (projet_id,))
            logger.info(f"Projet supprimé: {projet_id}")
        except Exception as e:
            logger.error(f"Erreur suppression projet {projet_id}: {e}")
            raise
    
    def get_stats(self):
        """
        Récupère les statistiques des projets pour les KPI.
        
        Returns:
            Dict avec les statistiques
        """
        try:
            stats = {}
            
            # Total de projets
            result = self.db.fetch_one("SELECT COUNT(*) as count FROM projets")
            stats['total'] = result['count'] if result else 0
            
            # Par statut
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM projets WHERE statut = 'ACTIF'"
            )
            stats['actifs'] = result['count'] if result else 0
            
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM projets WHERE statut = 'EN_ATTENTE'"
            )
            stats['en_attente'] = result['count'] if result else 0
            
            result = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM projets WHERE statut = 'TERMINE'"
            )
            stats['termines'] = result['count'] if result else 0
            
            # Budget total
            result = self.db.fetch_one(
                "SELECT SUM(COALESCE(budget_initial, budget_estime, 0)) as total FROM projets"
            )
            stats['budget_total'] = result['total'] if result and result['total'] else 0
            
            # Budget consommé
            result = self.db.fetch_one(
                "SELECT SUM(COALESCE(budget_consomme, 0)) as total FROM projets"
            )
            stats['budget_consomme'] = result['total'] if result and result['total'] else 0
            
            return stats
        except Exception as e:
            logger.error(f"Erreur récupération statistiques projets: {e}")
            return {
                'total': 0,
                'actifs': 0,
                'en_attente': 0,
                'termines': 0,
                'budget_total': 0,
                'budget_consomme': 0
            }
    
    def _generate_code(self):
        """Génère un code de projet unique."""
        try:
            # Trouver le dernier code
            result = self.db.fetch_one(
                "SELECT code FROM projets WHERE code LIKE 'PRJ%' ORDER BY code DESC LIMIT 1"
            )
            
            if result and result['code']:
                # Extraire le numéro et incrémenter
                last_code = result['code']
                if '-' in last_code:
                    parts = last_code.split('-')
                    if len(parts) >= 2:
                        try:
                            num = int(parts[-1]) + 1
                            year = datetime.now().year
                            return f"PRJ{year}-{num:03d}"
                        except ValueError:
                            pass
            
            # Code par défaut
            year = datetime.now().year
            return f"PRJ{year}-001"
        except Exception as e:
            logger.error(f"Erreur génération code projet: {e}")
            year = datetime.now().year
            return f"PRJ{year}-001"

# Instance globale
projet_service = ProjetService()
