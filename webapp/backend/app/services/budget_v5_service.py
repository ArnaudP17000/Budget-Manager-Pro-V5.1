# Service budget pour usage web
import logging
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)


class BudgetV5Service:
    def __init__(self):
        self.db = DatabaseService()

    def get_entites(self):
        try:
            rows = self.db.fetch_all("SELECT * FROM entites WHERE actif = true ORDER BY code")
            return [_d(r) for r in rows] if rows else []
        except Exception:
            logger.warning("Table entites inexistante")
            return []

    def get_all_applications(self):
        try:
            rows = self.db.fetch_all(
                "SELECT a.*, e.code as entite_code, f.nom as fournisseur_nom "
                "FROM applications a "
                "LEFT JOIN entites e ON e.id = a.entite_id "
                "LEFT JOIN fournisseurs f ON f.id = a.fournisseur_id "
                "ORDER BY a.nom"
            )
            return [_d(r) for r in rows] if rows else []
        except Exception:
            logger.warning("Table applications inexistante")
            return []

    def get_budget(self):
        try:
            rows = self.db.fetch_all(
                "SELECT b.*, e.code as entite_code, e.nom as entite_nom "
                "FROM budgets_annuels b "
                "LEFT JOIN entites e ON e.id = b.entite_id "
                "ORDER BY b.exercice DESC, e.code"
            )
            return [_d(r) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur budgets_annuels: {ex}")
            return []

    def voter_budget(self, budget_id, montant_vote):
        self.db.execute(
            "UPDATE budgets_annuels SET montant_vote=%s, statut='VOTE', "
            "montant_solde=GREATEST(COALESCE(%s,0)-COALESCE(montant_engage,0), 0), "
            "date_maj=NOW() WHERE id=%s",
            [montant_vote, montant_vote, budget_id]
        )

    def get_lignes(self, budget_id=None):
        try:
            query = (
                "SELECT l.*, a.nom as application_nom, p.nom as projet_nom, "
                "f.nom as fournisseur_nom, "
                "COALESCE(e.code, e.nom) || ' — ' || b.nature || ' ' || b.exercice::text as budget_label "
                "FROM lignes_budgetaires l "
                "LEFT JOIN applications a ON a.id = l.application_id "
                "LEFT JOIN projets p ON p.id = l.projet_id "
                "LEFT JOIN fournisseurs f ON f.id = l.fournisseur_id "
                "LEFT JOIN budgets_annuels b ON b.id = l.budget_id "
                "LEFT JOIN entites e ON e.id = b.entite_id"
            )
            params = []
            if budget_id:
                query += " WHERE l.budget_id = %s"
                params.append(budget_id)
            query += " ORDER BY l.libelle"
            rows = self.db.fetch_all(query, params)
            result = []
            for r in rows:
                d = _d(r)
                vote = float(d.get('montant_vote') or 0)
                engage = float(d.get('montant_engage') or 0)
                d['taux_engagement'] = round(engage / vote * 100, 1) if vote > 0 else 0
                d['alerte'] = d['taux_engagement'] >= 80
                result.append(d)
            return result
        except Exception as ex:
            logger.warning(f"Erreur lignes_budgetaires: {ex}")
            return []
