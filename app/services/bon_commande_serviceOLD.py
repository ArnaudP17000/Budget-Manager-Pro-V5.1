"""
bon_commande_service.py — Service BC V5
Améliorations : vérification solde contrat, recherche, historique par application
"""
import logging
from datetime import datetime
from app.services.database_service import db_service

def _get_audit():
    try:
        from app.services.integrity_service import integrity_service
        return integrity_service
    except Exception:
        return None

logger = logging.getLogger(__name__)


def _d(row):
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return {k: row[k] for k in row.keys()}
    return row


class BonCommandeService:

    def __init__(self):
        self.db = db_service

    # ── Lecture ───────────────────────────────────────────────────────────────

    def get_all_bons_commande(self, filters=None):
        """Récupère BC avec filtres étendus + recherche texte."""
        query = """
            SELECT bc.*,
                f.nom  AS fournisseur_nom,
                p.nom  AS projet_nom,
                s.nom  AS service_nom,
                c.numero_contrat,
                c.type_contrat,
                c.montant_max_ht,
                c.montant_engage_cumul  AS contrat_engage,
                c.objet                 AS contrat_objet,
                e.code                  AS entite_code,
                lb.libelle              AS ligne_libelle,
                lb.montant_vote         AS ligne_vote,
                lb.montant_engage       AS ligne_engage,
                lb.montant_solde        AS ligne_solde,
                a.nom                   AS application_nom
            FROM bons_commande bc
            LEFT JOIN fournisseurs    f  ON f.id  = bc.fournisseur_id
            LEFT JOIN projets         p  ON p.id  = bc.projet_id
            LEFT JOIN services        s  ON s.id  = bc.service_id
            LEFT JOIN contrats        c  ON c.id  = bc.contrat_id
            LEFT JOIN entites         e  ON e.id  = bc.entite_id
            LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id
            LEFT JOIN applications    a  ON a.id  = bc.application_id
            WHERE 1=1
        """
        params = []

        if filters:
            if filters.get('statut'):
                query += ' AND bc.statut=?'; params.append(filters['statut'])
            if filters.get('fournisseur_id'):
                query += ' AND bc.fournisseur_id=?'; params.append(filters['fournisseur_id'])
            if filters.get('projet_id'):
                query += ' AND bc.projet_id=?'; params.append(filters['projet_id'])
            if filters.get('entite_id'):
                query += ' AND bc.entite_id=?'; params.append(filters['entite_id'])
            if filters.get('contrat_id'):
                query += ' AND bc.contrat_id=?'; params.append(filters['contrat_id'])
            if filters.get('application_id'):
                query += ' AND bc.application_id=?'; params.append(filters['application_id'])
            if filters.get('exercice'):
                query += " AND strftime('%Y', bc.date_creation)=?"
                params.append(str(filters['exercice']))
            # Recherche texte globale
            if filters.get('search'):
                q = f"%{filters['search']}%"
                query += """ AND (
                    bc.numero_bc LIKE ? OR bc.objet LIKE ?
                    OR f.nom LIKE ? OR c.numero_contrat LIKE ?
                    OR lb.libelle LIKE ? OR a.nom LIKE ?
                )"""
                params.extend([q, q, q, q, q, q])

        query += ' ORDER BY bc.date_creation DESC, bc.id DESC'
        rows = self.db.fetch_all(query, params if params else None)
        return [_d(r) for r in rows] if rows else []

    def get_bon_commande_by_id(self, bc_id):
        row = self.db.fetch_one("""
            SELECT bc.*,
                f.nom AS fournisseur_nom,
                p.nom AS projet_nom,
                s.nom AS service_nom,
                c.numero_contrat, c.type_contrat,
                c.montant_max_ht, c.montant_engage_cumul AS contrat_engage,
                e.code AS entite_code,
                lb.libelle AS ligne_libelle, lb.montant_solde AS ligne_solde,
                a.nom AS application_nom
            FROM bons_commande bc
            LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id
            LEFT JOIN projets p ON p.id = bc.projet_id
            LEFT JOIN services s ON s.id = bc.service_id
            LEFT JOIN contrats c ON c.id = bc.contrat_id
            LEFT JOIN entites e ON e.id = bc.entite_id
            LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id
            LEFT JOIN applications a ON a.id = bc.application_id
            WHERE bc.id=?
        """, (bc_id,))
        return _d(row)

    def get_stats(self):
        rows = self.db.fetch_all("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN statut='BROUILLON'  THEN 1 ELSE 0 END) as brouillon,
                SUM(CASE WHEN statut='EN_ATTENTE' THEN 1 ELSE 0 END) as en_attente,
                SUM(CASE WHEN statut='VALIDE'     THEN 1 ELSE 0 END) as valide,
                SUM(CASE WHEN statut='IMPUTE'     THEN 1 ELSE 0 END) as impute,
                SUM(CASE WHEN statut='SOLDE'      THEN 1 ELSE 0 END) as solde,
                SUM(CASE WHEN statut='ANNULE'     THEN 1 ELSE 0 END) as annule,
                SUM(montant_ttc) as montant_total,
                SUM(CASE WHEN statut='IMPUTE' THEN montant_ttc ELSE 0 END) as montant_impute
            FROM bons_commande
        """)
        return _d(rows[0]) if rows else {}

    def get_historique_application(self, application_id, exercice=None):
        """Tous les BC liés à une application, avec totaux."""
        conds = ["bc.application_id=?"]
        params = [application_id]
        if exercice:
            conds.append("strftime('%Y', bc.date_creation)=?")
            params.append(str(exercice))
        where = "WHERE " + " AND ".join(conds)
        rows = self.db.fetch_all(f"""
            SELECT bc.*,
                f.nom AS fournisseur_nom,
                c.numero_contrat,
                lb.libelle AS ligne_libelle,
                e.code AS entite_code
            FROM bons_commande bc
            LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id
            LEFT JOIN contrats c ON c.id = bc.contrat_id
            LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id
            LEFT JOIN entites e ON e.id = bc.entite_id
            {where}
            ORDER BY bc.date_creation DESC
        """, params)
        return [_d(r) for r in rows] if rows else []

    # ── Écriture ──────────────────────────────────────────────────────────────

    def creer_bon_commande(self, data):
        if 'statut' not in data:
            data['statut'] = 'BROUILLON'
        data.setdefault('date_creation', datetime.now().isoformat())
        data.setdefault('date_maj',      data['date_creation'])
        return self.db.insert('bons_commande', data)

    def modifier_bon_commande(self, bc_id, data):
        data['date_maj'] = datetime.now().isoformat()
        self.db.update('bons_commande', data, 'id=?', (bc_id,))

    def supprimer_bon_commande(self, bc_id):
        bc = self.get_bon_commande_by_id(bc_id)
        if not bc:
            return {'ok': False, 'message': 'BC introuvable'}
        if bc.get('statut') == 'IMPUTE':
            return {'ok': False, 'message': 'Impossible de supprimer un BC imputé'}
        self.db.delete('bons_commande', 'id=?', (bc_id,))
        return {'ok': True, 'message': 'BC supprimé'}

    # ── Vérification solde contrat (amélioration #1) ───────────────────────

    def verifier_solde_contrat(self, contrat_id, montant_ttc, bc_id=None):
        """
        Vérifie que le montant du BC ne dépasse pas le solde du contrat.
        Retourne (ok, message, solde_restant)
        """
        if not contrat_id:
            return True, "", None

        conn = self.db.get_connection()
        ct = _d(conn.execute(
            "SELECT * FROM contrats WHERE id=?", (contrat_id,)).fetchone())
        if not ct:
            return True, "", None

        montant_max = float(ct.get('montant_max_ht') or ct.get('montant_total_ht') or 0)
        if montant_max <= 0:
            return True, "", None  # Pas de plafond défini

        # Cumul des BC existants sur ce contrat (hors BC actuel si modification)
        row = _d(conn.execute("""
            SELECT COALESCE(SUM(montant_ttc), 0) as cumul
            FROM bons_commande
            WHERE contrat_id=?
            AND statut NOT IN ('ANNULE','BROUILLON')
            AND (? IS NULL OR id != ?)
        """, (contrat_id, bc_id, bc_id)).fetchone())

        cumul     = float(row['cumul']) if row else 0
        solde     = montant_max - cumul
        nouveau   = cumul + float(montant_ttc)

        if nouveau > montant_max:
            return False, (
                f"⚠️ Dépassement du contrat !\n"
                f"Montant max : {montant_max:,.0f} €\n"
                f"Déjà engagé : {cumul:,.0f} €\n"
                f"Ce BC (TTC) : {montant_ttc:,.0f} €\n"
                f"Dépassement : {nouveau - montant_max:,.0f} €"
            ), solde
        return True, f"Solde contrat restant après ce BC : {solde - float(montant_ttc):,.0f} €", solde

    # ── Workflow ──────────────────────────────────────────────────────────────

    def valider_bon_commande(self, bc_id, valideur_id=None):
        bc = self.get_bon_commande_by_id(bc_id)
        if not bc:
            return {'ok': False, 'message': 'BC introuvable'}
        if bc['statut'] not in ('BROUILLON', 'EN_ATTENTE'):
            return {'ok': False, 'message': f"Statut '{bc['statut']}' ne peut pas être validé"}
        now = datetime.now().isoformat()
        self.db.get_connection().execute(
            "UPDATE bons_commande SET statut='VALIDE', valide=1, date_validation=?, valideur_id=?, date_maj=? WHERE id=?",
            (now, valideur_id, now, bc_id))
        self.db.get_connection().commit()
        audit = _get_audit()
        if audit:
            audit.log('BC', bc_id, 'STATUT_CHANGE',
                f"Validation BC {bc.get('numero_bc','')}",
                bc['statut'], 'VALIDE')
        return {'ok': True, 'message': 'BC validé'}

    def imputer_bon_commande(self, bc_id, ligne_budgetaire_id=None):
        """Imputation V5 : sur ligne budgétaire."""
        bc = self.get_bon_commande_by_id(bc_id)
        if not bc:
            return {'ok': False, 'message': 'BC introuvable'}
        if bc['statut'] != 'VALIDE':
            return {'ok': False, 'message': f"Le BC doit être VALIDE (statut : {bc['statut']})"}

        # Utiliser la ligne du BC ou celle passée en paramètre
        lid = ligne_budgetaire_id or bc.get('ligne_budgetaire_id')
        if not lid:
            return {'ok': False, 'message': 'Aucune ligne budgétaire rattachée'}

        try:
            from app.services.budget_v5_service import budget_v5_service
            result = budget_v5_service.imputer_bc_sur_ligne(bc_id, lid)
            if result.get('ok'):
                audit = _get_audit()
                if audit:
                    audit.log('BC', bc_id, 'IMPUTATION',
                        f"BC {bc.get('numero_bc','')} imputé sur ligne {lid}",
                        'VALIDE', 'IMPUTE')
            return result
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    def annuler_imputation(self, bc_id):
        bc = self.get_bon_commande_by_id(bc_id)
        if not bc:
            return {'ok': False, 'message': 'BC introuvable'}
        if bc['statut'] != 'IMPUTE':
            return {'ok': False, 'message': f"Seul un BC IMPUTE peut être annulé"}
        try:
            from app.services.budget_v5_service import budget_v5_service
            return budget_v5_service.annuler_imputation_bc(bc_id)
        except Exception as e:
            return {'ok': False, 'message': str(e)}


bon_commande_service = BonCommandeService()
