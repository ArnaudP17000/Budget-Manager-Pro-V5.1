# -*- coding: utf-8 -*-
"""
Service de gestion des portefeuilles
"""

import logging
from typing import List, Optional, Dict
from app.services.database_service import DatabaseService
from app.models.portefeuille import Portefeuille

logger = logging.getLogger(__name__)

class PortefeuilleService:
    """Service de gestion des portefeuilles de projets"""
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service or DatabaseService()
    
    def create_portefeuille(self, portefeuille: Portefeuille) -> int:
        """Crée un nouveau portefeuille"""
        try:
            portefeuille.validate()
            
            query = """
                INSERT INTO portefeuilles (nom, description, responsable, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            
            params = (portefeuille.nom, portefeuille.description, portefeuille.responsable)
            
            portefeuille_id = self.db.execute_update(query, params)
            logger.info(f"Portefeuille créé: ID={portefeuille_id}, nom={portefeuille.nom}")
            
            return portefeuille_id
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du portefeuille: {e}")
            raise
    
    def update_portefeuille(self, portefeuille: Portefeuille) -> bool:
        """Met à jour un portefeuille"""
        try:
            portefeuille.validate()
            
            query = """
                UPDATE portefeuilles SET
                    nom = ?, description = ?, responsable = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            params = (portefeuille.nom, portefeuille.description, 
                     portefeuille.responsable, portefeuille.id)
            
            self.db.execute_update(query, params)
            logger.info(f"Portefeuille mis à jour: ID={portefeuille.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du portefeuille: {e}")
            raise
    
    def get_portefeuille(self, portefeuille_id: int) -> Optional[Portefeuille]:
        """Récupère un portefeuille par son ID"""
        try:
            query = "SELECT * FROM portefeuilles WHERE id = ?"
            results = self.db.execute_query(query, (portefeuille_id,))
            
            if results:
                row = results[0]
                return Portefeuille(
                    id=row['id'],
                    nom=row['nom'],
                    description=row['description'],
                    responsable=row['responsable'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du portefeuille: {e}")
            raise
    
    def get_all_portefeuilles(self) -> List[Portefeuille]:
        """Récupère tous les portefeuilles"""
        try:
            query = "SELECT * FROM portefeuilles ORDER BY nom"
            results = self.db.execute_query(query)
            
            portefeuilles = []
            for row in results:
                portefeuilles.append(Portefeuille(
                    id=row['id'],
                    nom=row['nom'],
                    description=row['description'],
                    responsable=row['responsable'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return portefeuilles
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des portefeuilles: {e}")
            raise
    
    def delete_portefeuille(self, portefeuille_id: int) -> bool:
        """Supprime un portefeuille"""
        try:
            # Vérifier s'il y a des programmes associés
            check_query = "SELECT COUNT(*) as count FROM programmes WHERE portefeuille_id = ?"
            results = self.db.execute_query(check_query, (portefeuille_id,))
            
            if results and results[0]['count'] > 0:
                raise ValueError(
                    f"Impossible de supprimer le portefeuille: "
                    f"{results[0]['count']} programme(s) associé(s)"
                )
            
            query = "DELETE FROM portefeuilles WHERE id = ?"
            self.db.execute_update(query, (portefeuille_id,))
            logger.info(f"Portefeuille supprimé: ID={portefeuille_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du portefeuille: {e}")
            raise
    
    def get_portefeuilles_with_stats(self) -> List[Dict]:
        """Récupère tous les portefeuilles avec leurs statistiques"""
        try:
            query = """
                SELECT 
                    p.id,
                    p.nom,
                    p.description,
                    p.responsable,
                    COUNT(DISTINCT prog.id) as nb_programmes,
                    COUNT(DISTINCT proj.id) as nb_projets,
                    COALESCE(SUM(proj.budget_estime), 0) as budget_total
                FROM portefeuilles p
                LEFT JOIN programmes prog ON prog.portefeuille_id = p.id
                LEFT JOIN projets proj ON proj.programme_id = prog.id
                GROUP BY p.id, p.nom, p.description, p.responsable
                ORDER BY p.nom
            """
            
            results = self.db.execute_query(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            raise
