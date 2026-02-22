"""
contrat_service.py — Service gestion des contrats V5
"""
import logging
from datetime import datetime, date, timedelta
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
    return dict(row) if hasattr(row, 'keys') else row


TYPES_CONTRAT = [
    ('MARCHE_BC',          'Marché à bons de commande'),
    ('MARCHE_MAINTENANCE', 'Marché de maintenance / support'),
    ('GRE_A_GRE',          'Gré à gré (MAPA)'),
    ('ACCORD_CADRE',       'Accord-cadre'),
    ('HORS_MARCHE',        'Hors marché / prestation ponctuelle'),
]


class ContratService:

    def __init__(self):
        self.db = db_service

    # ── Lecture ───────────────────────────────────────────────────────────────

    def get_all(self, entite_id=None, statut=None, type_contrat=None):
        conds, params = [], []
        if entite_id:
            conds.append("c.entite_id=?"); params.append(entite_id)
        if statut:
            conds.append("c.statut=?"); params.append(statut)
        if type_contrat:
            conds.append("c.type_contrat=?"); params.append(type_contrat)
        where = "WHERE " + " AND ".join(conds) if conds else ""
        rows = self.db.fetch_all(f"""
            SELECT c.*,
                e.code  AS entite_code,
                e.nom   AS entite_nom,
                f.nom   AS fournisseur_nom,
                a.nom   AS application_nom,
                a.code  AS application_code,
                CAST(julianday(c.date_fin) - julianday('now') AS INTEGER) AS jours_restants,
                CASE
                    WHEN julianday(c.date_fin) < julianday('now') THEN 'EXPIRE'
                    WHEN julianday(c.date_fin) - julianday('now') <= 30  THEN 'CRITIQUE'
                    WHEN julianday(c.date_fin) - julianday('now') <= 90  THEN 'ATTENTION'
                    WHEN julianday(c.date_fin) - julianday('now') <= 180 THEN 'INFO'
                    ELSE 'OK'
                END AS niveau_alerte
            FROM contrats c
            LEFT JOIN entites   e ON e.id = c.entite_id
            LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id
            LEFT JOIN applications a ON a.id = c.application_id
            {where}
            ORDER BY c.date_fin ASC
        """, params if params else None)
        return [_d(r) for r in rows] if rows else []

    def get_by_id(self, contrat_id):
        row = self.db.fetch_one("""
            SELECT c.*,
                e.code AS entite_code, e.nom AS entite_nom,
                f.nom  AS fournisseur_nom,
                a.nom  AS application_nom
            FROM contrats c
            LEFT JOIN entites   e ON e.id = c.entite_id
            LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id
            LEFT JOIN applications a ON a.id = c.application_id
            WHERE c.id=?
        """, (contrat_id,))
        return _d(row)

    def get_alertes(self, jours=90):
        """Retourne les contrats qui expirent dans moins de X jours."""
        rows = self.db.fetch_all("""
            SELECT c.*,
                e.code AS entite_code, e.nom AS entite_nom,
                f.nom  AS fournisseur_nom,
                a.nom  AS application_nom,
                CAST(julianday(c.date_fin) - julianday('now') AS INTEGER) AS jours_restants,
                CASE
                    WHEN julianday(c.date_fin) < julianday('now') THEN 'EXPIRE'
                    WHEN julianday(c.date_fin) - julianday('now') <= 30  THEN 'CRITIQUE'
                    WHEN julianday(c.date_fin) - julianday('now') <= 90  THEN 'ATTENTION'
                    ELSE 'INFO'
                END AS niveau_alerte
            FROM contrats c
            LEFT JOIN entites   e ON e.id = c.entite_id
            LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id
            LEFT JOIN applications a ON a.id = c.application_id
            WHERE c.statut IN ('ACTIF','RECONDUIT')
            AND julianday(c.date_fin) - julianday('now') <= ?
            ORDER BY c.date_fin ASC
        """, (jours,))
        return [_d(r) for r in rows] if rows else []

    # ── Écriture ──────────────────────────────────────────────────────────────

    def create(self, data):
        data['date_creation'] = datetime.now().isoformat()
        data['date_maj']      = data['date_creation']
        # Synchroniser type_budget avec nature pour compatibilité
        if 'nature' in data and 'type_budget' not in data:
            data['type_budget'] = data['nature']
        elif 'type_budget' not in data:
            data['type_budget'] = 'FONCTIONNEMENT'
        # Calculer durée en mois si dates présentes
        data = self._calc_duree(data)
        # Initialiser cumuls
        data.setdefault('montant_engage_cumul', 0)
        data.setdefault('montant_restant', data.get('montant_max_ht') or data.get('montant_total_ht') or 0)
        return self.db.insert('contrats', data)

    def update(self, contrat_id, data):
        data['date_maj'] = datetime.now().isoformat()
        data = self._calc_duree(data)
        self.db.update('contrats', data, 'id=?', (contrat_id,))

    def reconduire(self, contrat_id):
        """Reconduit un contrat d'un an."""
        conn = self.db.get_connection()
        cur  = conn.cursor()
        ct   = _d(cur.execute("SELECT * FROM contrats WHERE id=?", (contrat_id,)).fetchone())
        if not ct:
            return {'ok': False, 'message': "Contrat introuvable"}
        if not ct.get('reconduction_tacite') and int(ct.get('nombre_reconductions',0)) <= 0:
            return {'ok': False, 'message': "Ce contrat n'est pas reconductible"}

        from datetime import date as dt
        try:
            old_fin  = datetime.strptime(ct['date_fin'][:10], '%Y-%m-%d').date()
            new_fin  = old_fin.replace(year=old_fin.year + 1)
            nb_faits = int(ct.get('nb_reconductions_faites') or 0) + 1
            nb_max   = int(ct.get('nb_reconductions_max') or ct.get('nombre_reconductions') or 0)
            if nb_max and nb_faits > nb_max:
                return {'ok': False, 'message': f"Nombre max de reconductions atteint ({nb_max})"}
            now = datetime.now().isoformat()
            cur.execute("""
                UPDATE contrats SET
                    date_fin = ?, statut = 'RECONDUIT',
                    nb_reconductions_faites = ?, date_maj = ?
                WHERE id = ?
            """, (new_fin.isoformat(), nb_faits, now, contrat_id))

            # Incrémenter le budget lié du montant annuel
            montant_annuel = float(ct.get('montant_annuel_ht') or 0)
            budget_msg = ""
            if montant_annuel > 0:
                # Chercher la ligne budgétaire liée à ce contrat sur l'exercice N+1
                exercice_n1 = new_fin.year
                ligne = cur.execute("""
                    SELECT lb.id, lb.budget_id, lb.montant_prevu, lb.montant_vote, lb.montant_solde
                    FROM lignes_budgetaires lb
                    JOIN budgets_annuels ba ON ba.id = lb.budget_id
                    WHERE lb.fournisseur_id = ? AND ba.exercice = ?
                    LIMIT 1
                """, (ct.get('fournisseur_id'), exercice_n1)).fetchone()

                if ligne:
                    ligne = dict(ligne)
                    cur.execute("""
                        UPDATE lignes_budgetaires SET
                            montant_prevu = montant_prevu + ?,
                            montant_vote  = montant_vote + ?,
                            montant_solde = montant_solde + ?,
                            date_maj = ?
                        WHERE id = ?
                    """, (montant_annuel, montant_annuel, montant_annuel, now, ligne['id']))
                    # Recalculer le budget parent
                    try:
                        from app.services.budget_v5_service import budget_v5_service
                        budget_v5_service._recalc_budget_prevu(ligne['budget_id'])
                    except Exception:
                        pass
                    budget_msg = f"\nBudget {exercice_n1} incrémenté de {montant_annuel:,.0f} €"
                else:
                    budget_msg = f"\n⚠️ Aucune ligne budgétaire trouvée pour {exercice_n1} — incrémentation manuelle requise"

            conn.commit()
            audit = _get_audit()
            if audit:
                audit.log('CONTRAT', contrat_id, 'RECONDUCTION',
                    f"Reconduction contrat {ct.get('numero_contrat','')}",
                    ct['date_fin'], new_fin.isoformat())
            return {'ok': True, 'message': f"Contrat reconduit jusqu'au {new_fin.strftime('%d/%m/%Y')}{budget_msg}"}
        except Exception as e:
            conn.rollback()
            return {'ok': False, 'message': str(e)}

    def changer_statut(self, contrat_id, statut):
        self.db.update('contrats', {'statut': statut, 'date_maj': datetime.now().isoformat()},
                       'id=?', (contrat_id,))

    def delete(self, contrat_id):
        # Vérifier si des BC y sont rattachés
        n = _d(self.db.fetch_one(
            "SELECT COUNT(*) as n FROM bons_commande WHERE contrat_id=?", (contrat_id,)))
        if n and n['n'] > 0:
            return False, f"{n['n']} bon(s) de commande rattaché(s) à ce contrat"
        self.db.delete('contrats', 'id=?', (contrat_id,))
        return True, "Contrat supprimé"

    def get_stats(self):
        """Statistiques globales pour le dashboard."""
        rows = self.db.fetch_all("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN statut='ACTIF' THEN 1 ELSE 0 END) as actifs,
                SUM(CASE WHEN julianday(date_fin)-julianday('now') <= 90
                         AND statut IN ('ACTIF','RECONDUIT') THEN 1 ELSE 0 END) as alertes_90j,
                SUM(CASE WHEN julianday(date_fin) < julianday('now')
                         AND statut IN ('ACTIF','RECONDUIT') THEN 1 ELSE 0 END) as expires
            FROM contrats
        """)
        return _d(rows[0]) if rows else {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _calc_duree(self, data):
        try:
            if data.get('date_debut') and data.get('date_fin'):
                d1 = datetime.strptime(data['date_debut'][:10], '%Y-%m-%d')
                d2 = datetime.strptime(data['date_fin'][:10], '%Y-%m-%d')
                data['duree_mois'] = max(1, round((d2 - d1).days / 30.44))
        except Exception:
            pass
        return data


contrat_service = ContratService()
