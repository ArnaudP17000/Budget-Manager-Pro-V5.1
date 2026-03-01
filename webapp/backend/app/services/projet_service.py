import logging
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ProjetService:
    def __init__(self):
        self.db = DatabaseService()

    def get_all(self, filters=None):
        try:
            query = (
                "SELECT p.*, s.nom as service_nom, s.code as service_code "
                "FROM projets p "
                "LEFT JOIN services s ON s.id = p.service_id "
                "WHERE 1=1"
            )
            params = []
            if filters:
                if filters.get('statut'):
                    query += " AND p.statut = %s"
                    params.append(filters['statut'])
            query += " ORDER BY p.date_creation DESC"
            rows = self.db.fetch_all(query, params)
            return [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.error(f"Erreur get_all projets: {e}")
            return []

    def get_by_id(self, projet_id):
        try:
            row = self.db.fetch_one(
                "SELECT p.*, s.nom as service_nom, s.code as service_code "
                "FROM projets p "
                "LEFT JOIN services s ON s.id = p.service_id "
                "WHERE p.id = %s",
                [projet_id]
            )
            if not row:
                return None
            p = dict(row)
            taches = self.db.fetch_all(
                "SELECT id, titre, statut, priorite, date_echeance, "
                "estimation_heures, heures_reelles, avancement FROM taches WHERE projet_id=%s "
                "ORDER BY date_echeance ASC NULLS LAST",
                [projet_id]
            )
            p['taches'] = [dict(t) for t in taches] if taches else []
            # Stats tâches par statut
            stats_taches = {}
            for t in p['taches']:
                s = t.get('statut', 'Inconnu')
                stats_taches[s] = stats_taches.get(s, 0) + 1
            p['taches_stats'] = stats_taches
            p['heures_estimees'] = sum(float(t.get('estimation_heures') or 0) for t in p['taches'])
            p['heures_reelles']  = sum(float(t.get('heures_reelles') or 0) for t in p['taches'])
            bcs = self.db.fetch_all(
                "SELECT bc.id, bc.numero_bc, bc.objet, bc.montant_ht, bc.montant_ttc, "
                "bc.statut, bc.date_creation, f.nom as fournisseur_nom "
                "FROM bons_commande bc "
                "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
                "WHERE bc.projet_id=%s ORDER BY bc.id DESC",
                [projet_id]
            )
            p['bons_commande'] = [dict(b) for b in bcs] if bcs else []
            # Budget consommé calculé depuis les BCs (IMPUTE + SOLDE)
            bc_consomme = sum(
                float(b.get('montant_ttc') or 0)
                for b in p['bons_commande']
                if b.get('statut') in ('IMPUTE', 'SOLDE', 'VALIDE')
            )
            p['budget_consomme_calcule'] = round(bc_consomme, 2)
            p['montant_bc_total'] = round(sum(float(b.get('montant_ttc') or 0) for b in p['bons_commande']), 2)

            # ── Équipe : membres (projet_equipe → utilisateurs) ─────────────
            try:
                membres = self.db.fetch_all(
                    "SELECT pe.id as membre_id, "
                    "  COALESCE(pe.membre_label, TRIM(COALESCE(u.prenom,'') || ' ' || COALESCE(u.nom,''))) as nom_complet, "
                    "  COALESCE(u.email, '') as email, "
                    "  COALESCE(u.fonction, '') as fonction, "
                    "  COALESCE(u.telephone, '') as telephone "
                    "FROM projet_equipe pe "
                    "LEFT JOIN utilisateurs u ON u.id = pe.utilisateur_id "
                    "WHERE pe.projet_id = %s",
                    [projet_id]
                )
            except Exception:
                membres = self.db.fetch_all(
                    "SELECT pe.id as membre_id, "
                    "  TRIM(COALESCE(u.prenom,'') || ' ' || COALESCE(u.nom,'')) as nom_complet, "
                    "  COALESCE(u.email, '') as email, "
                    "  COALESCE(u.fonction, '') as fonction, "
                    "  COALESCE(u.telephone, '') as telephone "
                    "FROM projet_equipe pe "
                    "LEFT JOIN utilisateurs u ON u.id = pe.utilisateur_id "
                    "WHERE pe.projet_id = %s",
                    [projet_id]
                )
            p['equipe'] = [dict(m) for m in membres] if membres else []

            # ── Prestataires ────────────────────────────────────────────────
            prest = self.db.fetch_all(
                "SELECT f.nom as fournisseur_nom, f.email, f.telephone, f.contact_principal "
                "FROM projet_prestataires pp "
                "JOIN fournisseurs f ON f.id = pp.fournisseur_id "
                "WHERE pp.projet_id = %s",
                [projet_id]
            )
            p['prestataires'] = [dict(pr) for pr in prest] if prest else []

            # ── Contacts externes (projet_contacts) ─────────────────────────
            contacts_ext = self.db.fetch_all(
                "SELECT pc.contact_id, pc.role, "
                "  COALESCE(pc.contact_libre, TRIM(COALESCE(c.prenom,'') || ' ' || COALESCE(c.nom,''))) as nom_affiche, "
                "  COALESCE(c.nom,'') as nom, COALESCE(c.prenom,'') as prenom, "
                "  COALESCE(c.email,'') as email, COALESCE(c.telephone,'') as telephone, "
                "  COALESCE(c.organisation,'') as organisation "
                "FROM projet_contacts pc "
                "LEFT JOIN contacts c ON c.id = pc.contact_id "
                "WHERE pc.projet_id = %s",
                [projet_id]
            )
            p['contacts_externes'] = [dict(ce) for ce in contacts_ext] if contacts_ext else []

            # ── Documents ──────────────────────────────────────────────────
            docs = self.db.fetch_all(
                "SELECT nom_fichier, type_document, taille, date_ajout "
                "FROM projet_documents WHERE projet_id = %s ORDER BY date_ajout DESC",
                [projet_id]
            )
            p['documents'] = [dict(d) for d in docs] if docs else []

            # ── Responsable / Chef projet ──────────────────────────────────
            for role, col in [('responsable_nom', 'responsable_contact_id'),
                               ('chef_projet_nom', 'chef_projet_contact_id')]:
                cid = p.get(col)
                if cid:
                    cr = self.db.fetch_one(
                        "SELECT nom, prenom, email, telephone FROM contacts WHERE id = %s", [cid]
                    )
                    if cr:
                        p[role] = f"{cr.get('prenom') or ''} {cr.get('nom') or ''}".strip()
                        p[role + '_email'] = cr.get('email')
                        p[role + '_tel']   = cr.get('telephone')

            return p
        except Exception as e:
            logger.error(f"Erreur get_by_id projet {projet_id}: {e}")
            return None

    def add_equipe_membre(self, projet_id, utilisateur_id=None, membre_label=None):
        self.db.execute(
            "INSERT INTO projet_equipe (projet_id, utilisateur_id, membre_label) VALUES (%s, %s, %s)",
            [projet_id, utilisateur_id or None, membre_label or None]
        )

    def remove_equipe_membre(self, projet_id, membre_id):
        self.db.execute(
            "DELETE FROM projet_equipe WHERE id=%s AND projet_id=%s",
            [membre_id, projet_id]
        )

    def add_projet_contact(self, projet_id, contact_id=None, role=None, contact_libre=None):
        self.db.execute(
            "INSERT INTO projet_contacts (projet_id, contact_id, role, contact_libre) VALUES (%s, %s, %s, %s)",
            [projet_id, contact_id or None, role or None, contact_libre or None]
        )

    def remove_projet_contact(self, projet_id, contact_id=None, contact_libre=None):
        if contact_id:
            self.db.execute(
                "DELETE FROM projet_contacts WHERE projet_id=%s AND contact_id=%s",
                [projet_id, contact_id]
            )
        else:
            self.db.execute(
                "DELETE FROM projet_contacts WHERE projet_id=%s AND contact_libre=%s",
                [projet_id, contact_libre]
            )
