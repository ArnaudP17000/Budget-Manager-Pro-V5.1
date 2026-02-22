"""
integrity_service.py — Intégrité référentielle et journal d'audit
"""
import logging
from datetime import datetime
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


def _d(row):
    if row is None: return None
    return dict(row) if hasattr(row, 'keys') else row


class IntegrityService:
    """
    Vérifie les contraintes avant suppression et journalise les événements métier.
    """

    def __init__(self):
        self.db = db_service

    # =========================================================================
    # VÉRIFICATIONS AVANT SUPPRESSION
    # =========================================================================

    def check_fournisseur(self, fournisseur_id):
        """Bloque si le fournisseur a des contrats actifs ou des BC non annulés."""
        conn = self.db.get_connection()
        errors = []

        n_contrats = _d(conn.execute("""
            SELECT COUNT(*) as n FROM contrats
            WHERE fournisseur_id=? AND statut IN ('ACTIF','RECONDUIT','BROUILLON')
        """, (fournisseur_id,)).fetchone())
        if n_contrats and n_contrats['n'] > 0:
            errors.append(f"{n_contrats['n']} contrat(s) actif(s) rattaché(s)")

        n_bc = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE fournisseur_id=? AND statut NOT IN ('ANNULE','SOLDE')
        """, (fournisseur_id,)).fetchone())
        if n_bc and n_bc['n'] > 0:
            errors.append(f"{n_bc['n']} bon(s) de commande actif(s)")

        return (True, None) if not errors else (False, "Impossible de supprimer ce fournisseur :\n• " + "\n• ".join(errors))

    def check_contrat(self, contrat_id):
        """Bloque si le contrat a des BC rattachés non annulés."""
        conn = self.db.get_connection()
        n = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE contrat_id=? AND statut NOT IN ('ANNULE')
        """, (contrat_id,)).fetchone())
        if n and n['n'] > 0:
            return False, f"Impossible de supprimer ce contrat :\n• {n['n']} bon(s) de commande rattaché(s)\n\nAnnulez d'abord les BC avant de supprimer le contrat."
        return True, None

    def check_ligne_budgetaire(self, ligne_id):
        """Bloque si la ligne a des BC imputés ou validés."""
        conn = self.db.get_connection()
        n = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE ligne_budgetaire_id=? AND statut IN ('VALIDE','IMPUTE','SOLDE')
        """, (ligne_id,)).fetchone())
        if n and n['n'] > 0:
            return False, f"Impossible de supprimer cette ligne budgétaire :\n• {n['n']} BC validé(s) ou imputé(s) sur cette ligne\n\nAnnulez ou désimputez les BC avant de supprimer la ligne."
        return True, None

    def check_application(self, application_id):
        """Bloque si l'application est rattachée à des lignes budgétaires ou BC actifs."""
        conn = self.db.get_connection()
        errors = []

        n_lb = _d(conn.execute("""
            SELECT COUNT(*) as n FROM lignes_budgetaires
            WHERE application_id=? AND statut='ACTIF'
        """, (application_id,)).fetchone())
        if n_lb and n_lb['n'] > 0:
            errors.append(f"{n_lb['n']} ligne(s) budgétaire(s) active(s)")

        n_bc = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE application_id=? AND statut NOT IN ('ANNULE','SOLDE')
        """, (application_id,)).fetchone())
        if n_bc and n_bc['n'] > 0:
            errors.append(f"{n_bc['n']} bon(s) de commande actif(s)")

        return (True, None) if not errors else (False, "Impossible de supprimer cette application :\n• " + "\n• ".join(errors))

    def check_entite(self, entite_id):
        """Bloque si l'entité a des budgets non clôturés."""
        conn = self.db.get_connection()
        n = _d(conn.execute("""
            SELECT COUNT(*) as n FROM budgets_annuels
            WHERE entite_id=? AND statut NOT IN ('CLOTURE')
        """, (entite_id,)).fetchone())
        if n and n['n'] > 0:
            return False, f"Impossible de supprimer cette entité :\n• {n['n']} budget(s) non clôturé(s)\n\nClôturez tous les budgets de l'entité avant de la supprimer."
        return True, None

    # =========================================================================
    # JOURNAL D'AUDIT
    # =========================================================================

    def log(self, objet_type, objet_id, action, detail=None, ancien=None, nouveau=None):
        """
        Enregistre un événement dans le journal d'audit.
        objet_type : 'BC' | 'CONTRAT' | 'BUDGET' | 'LIGNE' | 'FOURNISSEUR' | ...
        action     : 'STATUT_CHANGE' | 'IMPUTATION' | 'RECONDUCTION' | 'VOTE' | 'SUPPRESSION' | ...
        """
        try:
            conn = self.db.get_connection()
            conn.execute("""
                INSERT INTO audit_log
                    (objet_type, objet_id, action, detail, valeur_avant, valeur_apres, date_action)
                VALUES (?,?,?,?,?,?,?)
            """, (
                objet_type, objet_id, action,
                detail or '',
                str(ancien) if ancien is not None else None,
                str(nouveau) if nouveau is not None else None,
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"Audit log échoué ({objet_type}/{action}) : {e}")

    def get_logs(self, objet_type=None, objet_id=None, limit=200):
        """Récupère les entrées du journal."""
        conds, params = [], []
        if objet_type:
            conds.append("objet_type=?"); params.append(objet_type)
        if objet_id:
            conds.append("objet_id=?"); params.append(objet_id)
        where = "WHERE " + " AND ".join(conds) if conds else ""
        rows = self.db.fetch_all(f"""
            SELECT * FROM audit_log {where}
            ORDER BY date_action DESC LIMIT ?
        """, params + [limit])
        return [_d(r) for r in rows] if rows else []


integrity_service = IntegrityService()
