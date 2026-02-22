"""
Service de gestion des fournisseurs.
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


class FournisseurService:
    """Service pour gérer les fournisseurs."""
    
    def __init__(self):
        self.db = db_service
    
    def get_all(self, filters=None):
        """
        Récupère tous les fournisseurs avec filtres optionnels.
        
        Args:
            filters: Dict avec clés optionnelles: statut, search
        
        Returns:
            List of fournisseur rows
        """
        try:
            query = """
                SELECT 
                    f.*,
                    (SELECT COUNT(*) FROM contrats WHERE fournisseur_id = f.id) as nb_contrats,
                    (SELECT COUNT(*) FROM bons_commande WHERE fournisseur_id = f.id) as nb_bc,
                    (SELECT SUM(montant_ttc) FROM bons_commande WHERE fournisseur_id = f.id) as montant_total
                FROM fournisseurs f
                WHERE 1=1
            """
            params = []
            
            if filters:
                if 'statut' in filters and filters['statut']:
                    query += " AND f.statut = ?"
                    params.append(filters['statut'])
                
                if 'search' in filters and filters['search']:
                    query += " AND f.nom LIKE ?"
                    search = f"%{filters['search']}%"
                    params.append(search)
            
            query += " ORDER BY f.nom"
            
            rows = self.db.fetch_all(query, params if params else None)
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur récupération fournisseurs: {e}")
            raise
    
    def get_by_id(self, fournisseur_id):
        """
        Récupère un fournisseur par ID.
        
        Args:
            fournisseur_id: ID du fournisseur
        
        Returns:
            Fournisseur row ou None
        """
        try:
            query = "SELECT * FROM fournisseurs WHERE id = ?"
            row = self.db.fetch_one(query, (fournisseur_id,))
            return row_to_dict(row)
        except Exception as e:
            logger.error(f"Erreur récupération fournisseur {fournisseur_id}: {e}")
            raise
    
    def create(self, data):
        """
        Crée un nouveau fournisseur.
        
        Args:
            data: Dict avec les données du fournisseur
        
        Returns:
            ID du fournisseur créé
        """
        try:
            # Ajouter timestamp et actif par défaut
            data['date_creation'] = datetime.now().isoformat()
            if 'actif' not in data:
                data['actif'] = True
            
            fournisseur_id = self.db.insert('fournisseurs', data)
            logger.info(f"Fournisseur créé: {fournisseur_id} - {data.get('nom')}")
            return fournisseur_id
        except Exception as e:
            logger.error(f"Erreur création fournisseur: {e}")
            raise
    
    def update(self, fournisseur_id, data):
        """
        Met à jour un fournisseur.
        
        Args:
            fournisseur_id: ID du fournisseur
            data: Dict avec les données à mettre à jour
        
        Returns:
            None
        """
        try:
            self.db.update('fournisseurs', data, "id = ?", (fournisseur_id,))
            logger.info(f"Fournisseur mis à jour: {fournisseur_id}")
        except Exception as e:
            logger.error(f"Erreur mise à jour fournisseur {fournisseur_id}: {e}")
            raise
    
    def delete(self, fournisseur_id):
        """Supprime un fournisseur après vérification intégrité."""
        try:
            # Vérification intégrité référentielle
            try:
                from app.services.integrity_service import integrity_service
                ok, msg = integrity_service.check_fournisseur(fournisseur_id)
                if not ok:
                    return False, msg
            except ImportError:
                pass
            fourn = self.get_by_id(fournisseur_id)
            self.db.delete('fournisseurs', "id = ?", (fournisseur_id,))
            logger.info(f"Fournisseur supprimé: {fournisseur_id}")
            try:
                from app.services.integrity_service import integrity_service
                integrity_service.log('FOURNISSEUR', fournisseur_id, 'SUPPRESSION',
                    f"Suppression fournisseur {fourn.get('nom','') if fourn else ''}")
            except Exception:
                pass
            return True, "Fournisseur supprimé"
        except Exception as e:
            logger.error(f"Erreur suppression fournisseur {fournisseur_id}: {e}")
            return False, str(e)
    
    def get_contrats(self, fournisseur_id):
        """
        Récupère les contrats d'un fournisseur.
        
        Args:
            fournisseur_id: ID du fournisseur
        
        Returns:
            List of contrat rows
        """
        try:
            query = """
                SELECT * FROM contrats 
                WHERE fournisseur_id = ? 
                ORDER BY date_debut DESC
            """
            rows = self.db.fetch_all(query, (fournisseur_id,))
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur récupération contrats fournisseur: {e}")
            return []
    
    def get_bons_commande(self, fournisseur_id):
        """
        Récupère les bons de commande d'un fournisseur.
        
        Args:
            fournisseur_id: ID du fournisseur
        
        Returns:
            List of bon_commande rows
        """
        try:
            query = """
                SELECT * FROM bons_commande 
                WHERE fournisseur_id = ? 
                ORDER BY date_creation DESC
            """
            rows = self.db.fetch_all(query, (fournisseur_id,))
            return [row_to_dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur récupération bons de commande fournisseur: {e}")
            return []

# Instance globale

    def get_stats(self):
        """Récupère les statistiques des fournisseurs."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN statut = 'ACTIF' THEN 1 ELSE 0 END) as actifs,
                    SUM(CASE WHEN statut = 'INACTIF' THEN 1 ELSE 0 END) as inactifs
                FROM fournisseurs
            """
            row = self.db.fetch_one(query)
            return dict(row) if row else {}
        except Exception as e:
            logger.error(f'Erreur récupération stats fournisseurs: {e}')
            return {}

fournisseur_service = FournisseurService()
