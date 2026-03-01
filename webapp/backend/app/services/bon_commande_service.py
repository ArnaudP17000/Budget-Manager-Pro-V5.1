# Service bon de commande pour usage web
import logging
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)


class BonCommandeService:
    def __init__(self):
        self.db = DatabaseService()

    def get_all_bons_commande(self, filters=None):
        try:
            query = (
                "SELECT bc.*, f.nom as fournisseur_nom, e.code as entite_code, e.nom as entite_nom, "
                "c.numero_contrat, lb.libelle as ligne_libelle "
                "FROM bons_commande bc "
                "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
                "LEFT JOIN entites e ON e.id = bc.entite_id "
                "LEFT JOIN contrats c ON c.id = bc.contrat_id "
                "LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id "
                "WHERE 1=1"
            )
            params = []
            if filters:
                if filters.get('statut'):
                    query += " AND bc.statut = %s"
                    params.append(filters['statut'])
                if filters.get('entite_id'):
                    query += " AND bc.entite_id = %s"
                    params.append(filters['entite_id'])
                if filters.get('fournisseur_id'):
                    query += " AND bc.fournisseur_id = %s"
                    params.append(filters['fournisseur_id'])
                if filters.get('search'):
                    s = '%' + filters['search'] + '%'
                    query += " AND (bc.numero_bc ILIKE %s OR bc.objet ILIKE %s OR f.nom ILIKE %s)"
                    params.extend([s, s, s])
            query += " ORDER BY bc.date_creation DESC"
            rows = self.db.fetch_all(query, params)
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur bons_commande: {ex}")
            return []

    def get_by_id(self, bc_id):
        try:
            row = self.db.fetch_one(
                "SELECT bc.*, f.nom as fournisseur_nom, f.email as fournisseur_email, "
                "f.telephone as fournisseur_telephone, "
                "e.code as entite_code, e.nom as entite_nom, "
                "c.numero_contrat, c.montant_total_ht as contrat_montant_ht, "
                "c.montant_engage as contrat_montant_engage, "
                "lb.libelle as ligne_libelle, lb.montant_vote as ligne_vote, "
                "lb.montant_engage as ligne_engage, lb.montant_solde as ligne_solde "
                "FROM bons_commande bc "
                "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
                "LEFT JOIN entites e ON e.id = bc.entite_id "
                "LEFT JOIN contrats c ON c.id = bc.contrat_id "
                "LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id "
                "WHERE bc.id = %s",
                [bc_id]
            )
            return _d(row)
        except Exception as ex:
            logger.warning(f"Erreur get_bc {bc_id}: {ex}")
            return None

    def get_stats(self):
        try:
            rows = self.db.fetch_all(
                "SELECT statut, COUNT(*) as count, COALESCE(SUM(montant_ttc), 0) as total "
                "FROM bons_commande GROUP BY statut"
            )
            stats = {}
            for r in rows:
                stats[r['statut']] = {'count': r['count'], 'total': float(r['total'] or 0)}
            total_row = self.db.fetch_one(
                "SELECT COUNT(*) as count, COALESCE(SUM(montant_ttc),0) as total FROM bons_commande"
            )
            stats['_total'] = {
                'count': total_row['count'] if total_row else 0,
                'total': float((total_row['total'] if total_row else 0) or 0)
            }
            return stats
        except Exception as ex:
            logger.warning(f"Erreur bc stats: {ex}")
            return {}

    def valider(self, bc_id):
        bc = self.get_by_id(bc_id)
        if not bc:
            raise ValueError("BC introuvable")
        statut = bc.get('statut')
        if statut == 'BROUILLON':
            new_statut = 'EN_ATTENTE'
            self.db.execute(
                "UPDATE bons_commande SET statut=%s, date_maj=NOW() WHERE id=%s",
                [new_statut, bc_id]
            )
        elif statut == 'EN_ATTENTE':
            new_statut = 'VALIDE'
            self.db.execute(
                "UPDATE bons_commande SET statut=%s, valide=true, date_validation=NOW(), date_maj=NOW() WHERE id=%s",
                [new_statut, bc_id]
            )
        else:
            raise ValueError(f"Impossible de valider un BC en statut '{statut}'")
        return new_statut

    def imputer(self, bc_id, ligne_id):
        bc = self.get_by_id(bc_id)
        if not bc:
            raise ValueError("BC introuvable")
        if bc.get('statut') != 'VALIDE':
            raise ValueError("Le BC doit être VALIDE pour être imputé")

        montant = float(bc.get('montant_ttc') or bc.get('montant_ht') or 0)

        ligne = self.db.fetch_one("SELECT * FROM lignes_budgetaires WHERE id=%s", [ligne_id])
        if not ligne:
            raise ValueError("Ligne budgétaire introuvable")
        ligne = _d(ligne)

        vote = float(ligne.get('montant_vote') or 0)
        engage = float(ligne.get('montant_engage') or 0)
        solde = vote - engage

        if montant > solde:
            raise ValueError(f"Solde insuffisant : disponible {solde:.2f}€, BC {montant:.2f}€")

        self.db.execute(
            "UPDATE lignes_budgetaires "
            "SET montant_engage = COALESCE(montant_engage,0) + %s, "
            "montant_solde = COALESCE(montant_vote,0) - (COALESCE(montant_engage,0) + %s), "
            "date_maj=NOW() WHERE id=%s",
            [montant, montant, ligne_id]
        )
        self.db.execute(
            "UPDATE bons_commande SET statut='IMPUTE', ligne_budgetaire_id=%s, "
            "montant_engage=%s, date_imputation=NOW(), budget_impute=true, impute=true, date_maj=NOW() "
            "WHERE id=%s",
            [ligne_id, montant, bc_id]
        )
        return True
