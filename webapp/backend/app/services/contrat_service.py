# Service contrat pour usage web
import logging
from datetime import date as _date
from app.services.database_service import DatabaseService

def _d(row):
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row

logger = logging.getLogger(__name__)


def _compute_alerte(row):
    date_fin = row.get('date_fin')
    statut = row.get('statut', '')
    if not date_fin:
        row['niveau_alerte'] = 'OK'
        row['jours_restants'] = None
        return row
    if isinstance(date_fin, str):
        try:
            from datetime import datetime
            date_fin_dt = datetime.strptime(date_fin[:10], '%Y-%m-%d').date()
        except Exception:
            row['niveau_alerte'] = 'OK'
            row['jours_restants'] = None
            return row
    else:
        date_fin_dt = date_fin
    jours = (date_fin_dt - _date.today()).days
    row['jours_restants'] = jours
    if statut in ('RESILIE', 'TERMINE'):
        row['niveau_alerte'] = 'OK'
    elif jours < 0:
        row['niveau_alerte'] = 'EXPIRE'
    elif jours <= 30:
        row['niveau_alerte'] = 'CRITIQUE'
    elif jours <= 90:
        row['niveau_alerte'] = 'ATTENTION'
    elif jours <= 180:
        row['niveau_alerte'] = 'INFO'
    else:
        row['niveau_alerte'] = 'OK'
    return row


class ContratService:
    def __init__(self):
        self.db = DatabaseService()

    def get_all(self):
        try:
            rows = self.db.fetch_all(
                "SELECT c.*, f.nom as fournisseur_nom "
                "FROM contrats c "
                "LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id "
                "ORDER BY c.date_fin ASC"
            )
            return [_compute_alerte(_d(r)) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur contrats: {ex}")
            return []

    def get_alertes(self):
        try:
            rows = self.db.fetch_all(
                "SELECT c.*, f.nom as fournisseur_nom "
                "FROM contrats c "
                "LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id "
                "WHERE c.statut IN ('ACTIF', 'RECONDUIT') "
                "AND c.date_fin::date <= CURRENT_DATE + INTERVAL '180 days' "
                "ORDER BY c.date_fin ASC"
            )
            return [_compute_alerte(_d(r)) for r in rows] if rows else []
        except Exception as ex:
            logger.warning(f"Erreur alertes contrats: {ex}")
            return []

    def get_by_id(self, contrat_id):
        try:
            row = self.db.fetch_one(
                "SELECT c.*, f.nom as fournisseur_nom, f.email as fournisseur_email, "
                "f.telephone as fournisseur_telephone, f.contact_principal as fournisseur_contact, "
                "f.adresse as fournisseur_adresse, f.ville as fournisseur_ville "
                "FROM contrats c "
                "LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id "
                "WHERE c.id = %s",
                [contrat_id]
            )
            if not row:
                return None
            c = _compute_alerte(_d(row))
            bcs = self.db.fetch_all(
                "SELECT bc.id, bc.numero_bc, bc.objet, bc.montant_ht, bc.montant_ttc, "
                "bc.statut, bc.date_creation, bc.date_validation, "
                "lb.libelle as ligne_libelle "
                "FROM bons_commande bc "
                "LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id "
                "WHERE bc.contrat_id = %s ORDER BY bc.id DESC",
                [contrat_id]
            )
            c['bons_commande'] = [dict(b) for b in bcs] if bcs else []
            c['montant_bc_total'] = round(
                sum(float(b.get('montant_ttc') or 0) for b in c['bons_commande']), 2
            )
            return c
        except Exception as e:
            logger.error(f"Erreur get_by_id contrat {contrat_id}: {e}")
            return None

    def reconduire(self, contrat_id, nouvelle_date_fin):
        self.db.execute(
            "UPDATE contrats SET statut='RECONDUIT', date_fin=%s, "
            "nombre_reconductions = COALESCE(nombre_reconductions,0) + 1, "
            "date_maj=NOW() WHERE id=%s",
            [nouvelle_date_fin, contrat_id]
        )
