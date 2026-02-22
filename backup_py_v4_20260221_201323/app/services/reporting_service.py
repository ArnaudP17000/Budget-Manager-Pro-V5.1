# -*- coding: utf-8 -*-
"""
Service de génération de rapports et exports
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ReportingService:
    """Service de génération de rapports et d'exports"""
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service or DatabaseService()
    
    def generer_rapport_projet(self, projet_id: int) -> Dict:
        """
        Génère un rapport complet pour un projet
        
        Returns:
            Dictionnaire avec toutes les informations du projet
        """
        try:
            # Informations du projet
            projet_query = """
                SELECT 
                    p.*,
                    prog.nom as programme_nom,
                    port.nom as portefeuille_nom
                FROM projets p
                LEFT JOIN programmes prog ON p.programme_id = prog.id
                LEFT JOIN portefeuilles port ON prog.portefeuille_id = port.id
                WHERE p.id = ?
            """
            
            projet_results = self.db.execute_query(projet_query, (projet_id,))
            
            if not projet_results:
                raise ValueError(f"Projet {projet_id} non trouvé")
            
            projet = dict(projet_results[0])
            
            # Tâches du projet
            taches_query = """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN statut = 'terminee' THEN 1 ELSE 0 END) as terminees,
                       AVG(avancement) as avancement_moyen
                FROM taches
                WHERE projet_id = ?
            """
            taches_results = self.db.execute_query(taches_query, (projet_id,))
            projet['taches'] = dict(taches_results[0]) if taches_results else {}
            
            # Budget AP/CP
            budget_query = """
                SELECT 
                    SUM(ap.montant_ap) as montant_ap_total,
                    SUM(cp.montant_cp) as total_cp,
                    SUM(cp.montant_engage) as total_engage,
                    SUM(cp.montant_mandate) as total_mandate,
                    SUM(cp.montant_paye) as total_paye
                FROM autorisations_programme ap
                LEFT JOIN credits_paiement cp ON cp.ap_id = ap.id
                WHERE ap.projet_id = ?
            """
            budget_results = self.db.execute_query(budget_query, (projet_id,))
            projet['budget'] = dict(budget_results[0]) if budget_results else {}
            
            # Contrats
            contrats_query = """
                SELECT COUNT(*) as nb_contrats,
                       SUM(montant_actuel) as montant_total_contrats
                FROM contrats
                WHERE projet_id = ?
            """
            contrats_results = self.db.execute_query(contrats_query, (projet_id,))
            projet['contrats'] = dict(contrats_results[0]) if contrats_results else {}
            
            # Bons de commande
            bdc_query = """
                SELECT COUNT(*) as nb_bdc,
                       SUM(montant_ttc) as montant_total_bdc,
                       SUM(CASE WHEN statut = 'valide' THEN 1 ELSE 0 END) as nb_valides
                FROM bons_commande
                WHERE projet_id = ?
            """
            bdc_results = self.db.execute_query(bdc_query, (projet_id,))
            projet['bons_commande'] = dict(bdc_results[0]) if bdc_results else {}
            
            logger.info(f"Rapport généré pour projet {projet_id}")
            return projet
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport projet: {e}")
            raise
    
    def generer_synthese_budgetaire(self, exercice: int) -> Dict:
        """
        Génère une synthèse budgétaire pour un exercice
        
        Returns:
            Dictionnaire avec les totaux AP/CP/engagé/mandaté/payé
        """
        try:
            # Récupérer les totaux AP
            ap_query = """
                SELECT 
                    COUNT(id) as nb_ap,
                    COALESCE(SUM(montant_ap), 0) as total_ap
                FROM autorisations_programme
                WHERE exercice = ?
            """
            ap_results = self.db.execute_query(ap_query, (exercice,))
            ap_data = dict(ap_results[0]) if ap_results else {'nb_ap': 0, 'total_ap': 0}
            
            # Récupérer les totaux CP
            cp_query = """
                SELECT 
                    COALESCE(SUM(montant_cp), 0) as total_cp,
                    COALESCE(SUM(montant_engage), 0) as total_engage,
                    COALESCE(SUM(montant_mandate), 0) as total_mandate,
                    COALESCE(SUM(montant_paye), 0) as total_paye,
                    COALESCE(SUM(montant_cp) - SUM(montant_engage), 0) as reste_disponible
                FROM credits_paiement
                WHERE exercice = ?
            """
            cp_results = self.db.execute_query(cp_query, (exercice,))
            cp_data = dict(cp_results[0]) if cp_results else {}
            
            # Combiner les résultats
            synthese = {**ap_data, **cp_data}
            synthese['exercice'] = exercice
            synthese['date_generation'] = datetime.now().isoformat()
            
            # Projets par statut
            projets_query = """
                SELECT 
                    statut,
                    COUNT(*) as nombre,
                    SUM(budget_estime) as budget_total
                FROM projets
                GROUP BY statut
            """
            projets_results = self.db.execute_query(projets_query)
            synthese['projets_par_statut'] = [dict(row) for row in projets_results]
            
            logger.info(f"Synthèse budgétaire générée pour exercice {exercice}")
            return synthese
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la synthèse budgétaire: {e}")
            raise
    
    def get_kpi_dashboard(self) -> Dict:
        """
        Récupère les KPI pour le dashboard
        
        Returns:
            Dictionnaire avec les indicateurs clés
        """
        try:
            kpi = {}
            
            # Nombre de projets par statut
            query_projets = """
                SELECT statut, COUNT(*) as nombre
                FROM projets
                GROUP BY statut
            """
            results = self.db.execute_query(query_projets)
            kpi['projets_par_statut'] = {row['statut']: row['nombre'] for row in results}
            
            # Projets en retard
            query_retard = """
                SELECT COUNT(*) as nombre
                FROM projets
                WHERE date_fin_prevue < date('now')
                AND statut NOT IN ('cloture', 'annule')
            """
            results = self.db.execute_query(query_retard)
            kpi['projets_en_retard'] = results[0]['nombre'] if results else 0
            
            # Budget total
            query_budget = """
                SELECT 
                    SUM(budget_estime) as budget_estime_total,
                    SUM(budget_reel) as budget_reel_total
                FROM projets
                WHERE statut != 'annule'
            """
            results = self.db.execute_query(query_budget)
            if results:
                kpi['budget_estime_total'] = results[0]['budget_estime_total'] or 0
                kpi['budget_reel_total'] = results[0]['budget_reel_total'] or 0
            
            # Taux d'avancement moyen
            query_avancement = """
                SELECT AVG(avancement) as avancement_moyen
                FROM projets
                WHERE statut IN ('etude', 'realisation')
            """
            results = self.db.execute_query(query_avancement)
            kpi['avancement_moyen'] = results[0]['avancement_moyen'] if results else 0
            
            # Alertes actives
            query_alertes = """
                SELECT COUNT(*) as nombre
                FROM alertes
                WHERE date_lecture IS NULL
            """
            results = self.db.execute_query(query_alertes)
            kpi['alertes_non_lues'] = results[0]['nombre'] if results else 0
            
            # Todos en retard
            query_todos = """
                SELECT COUNT(*) as nombre
                FROM todos
                WHERE echeance < date('now')
                AND statut NOT IN ('terminee', 'annulee')
            """
            results = self.db.execute_query(query_todos)
            kpi['todos_en_retard'] = results[0]['nombre'] if results else 0
            
            logger.info("KPI dashboard générés")
            return kpi
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des KPI: {e}")
            raise
    
    def export_excel(self, data: List[Dict], filename: str) -> bool:
        """
        Exporte des données vers Excel (stub pour future implémentation)
        
        Args:
            data: Liste de dictionnaires à exporter
            filename: Nom du fichier de sortie
            
        Returns:
            True si l'export a réussi
        """
        logger.warning("Export Excel non encore implémenté")
        raise NotImplementedError("Export Excel à implémenter avec openpyxl ou pandas")
    
    def export_pdf(self, report_data: Dict, filename: str) -> bool:
        """
        Exporte un rapport vers PDF (stub pour future implémentation)
        
        Args:
            report_data: Données du rapport
            filename: Nom du fichier de sortie
            
        Returns:
            True si l'export a réussi
        """
        logger.warning("Export PDF non encore implémenté")
        raise NotImplementedError("Export PDF à implémenter avec reportlab ou weasyprint")
