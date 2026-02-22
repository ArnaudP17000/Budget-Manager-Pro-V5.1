"""
budget_v5_service.py — Service de gestion budgétaire V5
Gère : entités, budgets annuels, lignes budgétaires, imputation BC, préparation N+1
"""
import logging
from datetime import datetime, date
from app.services.database_service import db_service

def _get_audit():
    try:
        from app.services.integrity_service import integrity_service
        return integrity_service
    except Exception:
        return None

logger = logging.getLogger(__name__)


def _d(row):
    """sqlite3.Row → dict."""
    if row is None:
        return None
    return dict(row) if hasattr(row, 'keys') else row


class BudgetV5Service:

    def __init__(self):
        self.db = db_service

    # =========================================================================
    # ENTITÉS
    # =========================================================================

    def get_entites(self):
        rows = self.db.fetch_all("SELECT * FROM entites WHERE actif=1 ORDER BY code")
        return [_d(r) for r in rows] if rows else []

    def get_entite_by_code(self, code):
        return _d(self.db.fetch_one("SELECT * FROM entites WHERE code=?", (code,)))

    # =========================================================================
    # APPLICATIONS
    # =========================================================================

    def get_all_applications(self, entite_id=None):
        if entite_id:
            rows = self.db.fetch_all(
                "SELECT a.*, e.code AS entite_code, f.nom AS fournisseur_nom "
                "FROM applications a "
                "LEFT JOIN entites e ON e.id=a.entite_id "
                "LEFT JOIN fournisseurs f ON f.id=a.fournisseur_id "
                "WHERE a.entite_id=? OR a.entite_id IS NULL "
                "ORDER BY a.nom", (entite_id,))
        else:
            rows = self.db.fetch_all(
                "SELECT a.*, e.code AS entite_code, f.nom AS fournisseur_nom "
                "FROM applications a "
                "LEFT JOIN entites e ON e.id=a.entite_id "
                "LEFT JOIN fournisseurs f ON f.id=a.fournisseur_id "
                "ORDER BY a.nom")
        return [_d(r) for r in rows] if rows else []

    def create_application(self, data):
        data['date_creation'] = datetime.now().isoformat()
        # Vérifier unicité du code
        existing = self.db.fetch_one(
            "SELECT id FROM applications WHERE code=?",
            (data.get('code','').upper(),))
        if existing:
            raise ValueError(
                f"Une application avec le code « {data.get('code')} » existe déjà.\n"
                "Choisissez un code différent.")
        data['code'] = data.get('code','').upper()
        return self.db.insert('applications', data)

    def update_application(self, app_id, data):
        self.db.update('applications', data, 'id=?', (app_id,))

    def delete_application(self, app_id):
        # Vérifier dépendances
        n = self.db.fetch_one(
            "SELECT COUNT(*) as n FROM lignes_budgetaires WHERE application_id=?",
            (app_id,))
        if _d(n)['n'] > 0:
            return False, "Cette application est référencée dans des lignes budgétaires"
        self.db.delete('applications', 'id=?', (app_id,))
        return True, "Application supprimée"

    # =========================================================================
    # BUDGETS ANNUELS
    # =========================================================================

    def get_budgets(self, exercice=None, entite_id=None):
        conds, params = [], []
        if exercice:
            conds.append("exercice=?"); params.append(exercice)
        if entite_id:
            conds.append("entite_id=?"); params.append(entite_id)
        where = "WHERE " + " AND ".join(conds) if conds else ""
        rows = self.db.fetch_all(f"""
            SELECT ba.*, e.code AS entite_code, e.nom AS entite_nom
            FROM budgets_annuels ba
            JOIN entites e ON e.id=ba.entite_id
            {where}
            ORDER BY ba.exercice DESC, e.code, ba.nature
        """, params if params else None)
        return [_d(r) for r in rows] if rows else []

    def get_budget_by_id(self, budget_id):
        row = self.db.fetch_one("""
            SELECT ba.*, e.code AS entite_code, e.nom AS entite_nom
            FROM budgets_annuels ba
            JOIN entites e ON e.id=ba.entite_id
            WHERE ba.id=?
        """, (budget_id,))
        return _d(row)

    def create_budget(self, data):
        data['date_creation'] = datetime.now().isoformat()
        data['date_maj'] = data['date_creation']
        try:
            bid = self.db.insert('budgets_annuels', data)
            logger.info(f"Budget créé : {bid}")
            return bid
        except Exception as e:
            logger.error(f"Erreur création budget : {e}")
            raise

    def update_budget(self, budget_id, data):
        data['date_maj'] = datetime.now().isoformat()
        self.db.update('budgets_annuels', data, 'id=?', (budget_id,))

    def voter_budget(self, budget_id, montant_vote, date_vote=None):
        """Enregistre le vote du budget par les élus."""
        ancien = self.db.fetch_one(
            "SELECT montant_vote FROM budgets_annuels WHERE id=?", (budget_id,))
        ancien_vote = dict(ancien)['montant_vote'] if ancien else None
        data = {
            'montant_vote': montant_vote,
            'date_vote': date_vote or date.today().isoformat(),
            'statut': 'VOTE',
            'montant_solde': montant_vote,
            'date_maj': datetime.now().isoformat()
        }
        self.db.update('budgets_annuels', data, 'id=?', (budget_id,))
        self._recalc_budget(budget_id)
        try:
            from app.services.integrity_service import integrity_service
            integrity_service.log('BUDGET', budget_id, 'VOTE',
                f"Vote budget — montant vote : {montant_vote}",
                ancien_vote, montant_vote)
        except Exception:
            pass

    def get_synthese_budgets(self, exercice=None):
        """Synthèse tous budgets — essaie v_synthese_budget, fallback sur requête directe."""
        where_view  = "WHERE exercice=?"   if exercice else ""
        where_table = "WHERE ba.exercice=?" if exercice else ""
        params = (exercice,) if exercice else None
        # Essai 1 : vue v_synthese_budget
        try:
            rows = self.db.fetch_all(f"""
                SELECT *
                FROM v_synthese_budget
                {where_view}
                ORDER BY exercice DESC, entite_code, nature
            """, params)
            if rows is not None:
                return [_d(r) for r in rows]
        except Exception:
            pass
        # Fallback : requête directe sur les tables
        try:
            rows = self.db.fetch_all(f"""
                SELECT
                    ba.id, ba.exercice, ba.nature,
                    ba.statut, ba.statut AS statut_budget,
                    ba.montant_previsionnel, ba.montant_vote,
                    ba.montant_engage, ba.montant_solde,
                    e.code AS entite_code,
                    e.nom  AS entite_nom,
                    e.id   AS entite_id
                FROM budgets_annuels ba
                JOIN entites e ON e.id = ba.entite_id
                {where_table}
                ORDER BY ba.exercice DESC, e.code, ba.nature
            """, params)
            return [_d(r) for r in rows] if rows else []
        except Exception:
            return []

    # =========================================================================
    # LIGNES BUDGÉTAIRES
    # =========================================================================

    def get_lignes(self, budget_id=None, entite_id=None, exercice=None):
        conds, params = [], []
        if budget_id:
            conds.append("budget_id=?"); params.append(budget_id)
        if entite_id:
            conds.append("entite_id=?"); params.append(entite_id)
        if exercice:
            conds.append("exercice=?"); params.append(exercice)
        where = "WHERE " + " AND ".join(conds) if conds else ""
        rows = self.db.fetch_all(f"""
            SELECT * FROM v_lignes_budget {where}
            ORDER BY taux_engagement_pct DESC
        """, params if params else None)
        return [_d(r) for r in rows] if rows else []

    def get_ligne_by_id(self, ligne_id):
        return _d(self.db.fetch_one(
            "SELECT * FROM v_lignes_budget WHERE id=?", (ligne_id,)))

    def create_ligne(self, data):
        data['date_creation'] = datetime.now().isoformat()
        data['date_maj'] = data['date_creation']
        data.setdefault('montant_solde', data.get('montant_vote', 0))
        lid = self.db.insert('lignes_budgetaires', data)
        logger.info(f"Ligne budgétaire créée : {lid}")
        # Recalculer le budget parent (montant_prevu = somme des lignes)
        budget_id = data.get('budget_id')
        if budget_id:
            self._recalc_budget_prevu(budget_id)
        return lid

    def update_ligne(self, ligne_id, data):
        data['date_maj'] = datetime.now().isoformat()
        self.db.update('lignes_budgetaires', data, 'id=?', (ligne_id,))
        # Recalculer le budget parent
        budget_id = data.get('budget_id')
        if not budget_id:
            row = self.db.fetch_one("SELECT budget_id FROM lignes_budgetaires WHERE id=?", (ligne_id,))
            if row: budget_id = dict(row)['budget_id']
        if budget_id:
            self._recalc_budget_prevu(budget_id)

    def delete_ligne(self, ligne_id):
        try:
            from app.services.integrity_service import integrity_service
            ok, msg = integrity_service.check_ligne_budgetaire(ligne_id)
            if not ok:
                return False, msg
        except ImportError:
            n = self.db.fetch_one(
                "SELECT COUNT(*) as n FROM bons_commande WHERE ligne_budgetaire_id=?",
                (ligne_id,))
            if _d(n) and _d(n)['n'] > 0:
                return False, "Des BC sont imputés sur cette ligne"
        # Récupérer budget_id avant suppression
        row = self.db.fetch_one("SELECT budget_id FROM lignes_budgetaires WHERE id=?", (ligne_id,))
        budget_id = dict(row)['budget_id'] if row else None
        self.db.delete('lignes_budgetaires', 'id=?', (ligne_id,))
        if budget_id:
            self._recalc_budget_prevu(budget_id)
        return True, "Ligne supprimée"

    # =========================================================================
    # IMPUTATION BC → LIGNE BUDGÉTAIRE
    # =========================================================================

    def imputer_bc_sur_ligne(self, bc_id, ligne_id, bypass_solde=False):
        """
        Impute un BC validé sur une ligne budgétaire.
        Débite montant_engage et recalcule montant_solde.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()

            bc = _d(cur.execute(
                "SELECT * FROM bons_commande WHERE id=?", (bc_id,)).fetchone())
            if not bc:
                return {'ok': False, 'message': "BC introuvable"}
            if bc['statut'] != 'VALIDE':
                return {'ok': False, 'message': f"Le BC doit être VALIDE (statut: {bc['statut']})"}

            ligne = _d(cur.execute(
                "SELECT * FROM lignes_budgetaires WHERE id=?", (ligne_id,)).fetchone())
            if not ligne:
                return {'ok': False, 'message': "Ligne budgétaire introuvable"}
            if ligne['statut'] != 'ACTIF':
                return {'ok': False, 'message': f"Ligne '{ligne['statut']}' — imputation impossible"}

            montant = float(bc['montant_ttc'] or 0)

            # Recalculer le solde réel : vote - déjà engagé (robuste si montant_solde=0 legacy)
            montant_vote   = float(ligne.get('montant_vote') or ligne.get('montant_prevu') or 0)
            montant_engage = float(ligne.get('montant_engage') or 0)
            solde_reel     = montant_vote - montant_engage

            # Si montant_solde stocké > 0, utiliser le max (plus fiable)
            solde_stocke   = float(ligne.get('montant_solde') or 0)
            solde          = max(solde_reel, solde_stocke)

            # Resynchroniser montant_solde si incohérent (migration legacy)
            if solde_stocke == 0 and montant_vote > 0:
                solde = solde_reel

            if montant_vote > 0 and solde < montant and not bypass_solde:
                return {'ok': False, 'message':
                    f"Solde insuffisant sur la ligne : disponible {solde:,.2f} € / demandé {montant:,.2f} €"}

            now = datetime.now().isoformat()

            # Débiter la ligne (recalcul solde depuis vote pour robustesse legacy)
            cur.execute("""
                UPDATE lignes_budgetaires SET
                    montant_engage = montant_engage + ?,
                    montant_solde  = CASE
                        WHEN montant_solde > 0
                        THEN montant_solde - ?
                        ELSE COALESCE(montant_vote, montant_prevu, 0) - (montant_engage + ?)
                    END,
                    date_maj = ?
                WHERE id = ?
            """, (montant, montant, montant, now, ligne_id))

            # Mettre à jour le BC
            cur.execute("""
                UPDATE bons_commande SET
                    statut = 'IMPUTE',
                    impute = 1,
                    ligne_budgetaire_id = ?,
                    date_imputation = ?,
                    montant_engage = ?,
                    date_maj = ?
                WHERE id = ?
            """, (ligne_id, now, montant, now, bc_id))

            # Recalculer montant_engage du budget parent
            self._recalc_budget_from_ligne(cur, ligne_id)

            # Si le BC est lié à un contrat → mettre à jour le cumul
            if bc.get('contrat_id'):
                cur.execute("""
                    UPDATE contrats SET
                        montant_engage_cumul = montant_engage_cumul + ?,
                        montant_restant = CASE WHEN montant_max_ht IS NOT NULL
                            THEN montant_max_ht - (montant_engage_cumul + ?)
                            ELSE montant_restant END
                    WHERE id = ?
                """, (montant, montant, bc['contrat_id']))

            # Recalculer montant_engage du projet si rattaché
            if bc.get('projet_id'):
                cur.execute("""
                    UPDATE projets SET
                        montant_engage = COALESCE((
                            SELECT SUM(montant_ttc) FROM bons_commande
                            WHERE projet_id=? AND statut IN ('IMPUTE','SOLDE','VALIDE')
                        ), 0),
                        montant_solde = montant_prevu - COALESCE((
                            SELECT SUM(montant_ttc) FROM bons_commande
                            WHERE projet_id=? AND statut IN ('IMPUTE','SOLDE','VALIDE')
                        ), 0)
                    WHERE id = ?
                """, (bc['projet_id'], bc['projet_id'], bc['projet_id']))

            conn.commit()
            logger.info(f"BC {bc_id} imputé sur ligne {ligne_id} — {montant:,.2f} €")
            return {
                'ok': True,
                'message': f"BC imputé : {montant:,.2f} € engagés sur \"{ligne['libelle']}\""
            }

        except Exception as e:
            if conn: conn.rollback()
            logger.error(f"Erreur imputation BC {bc_id} : {e}", exc_info=True)
            return {'ok': False, 'message': str(e)}

    def annuler_imputation_bc(self, bc_id):
        """Annule l'imputation d'un BC et rembourse la ligne budgétaire."""
        conn = None
        try:
            conn = self.db.get_connection()
            cur  = conn.cursor()

            bc = _d(cur.execute(
                "SELECT * FROM bons_commande WHERE id=?", (bc_id,)).fetchone())
            if not bc:
                return {'ok': False, 'message': "BC introuvable"}
            if bc['statut'] != 'IMPUTE':
                return {'ok': False, 'message': f"Seul un BC IMPUTE peut être annulé"}

            montant  = float(bc.get('montant_engage') or bc.get('montant_ttc') or 0)
            ligne_id = bc.get('ligne_budgetaire_id')
            now      = datetime.now().isoformat()

            if ligne_id and montant:
                cur.execute("""
                    UPDATE lignes_budgetaires SET
                        montant_engage = MAX(0, montant_engage - ?),
                        montant_solde  = montant_solde + ?,
                        date_maj = ?
                    WHERE id = ?
                """, (montant, montant, now, ligne_id))
                self._recalc_budget_from_ligne(cur, ligne_id)

            if bc.get('contrat_id') and montant:
                cur.execute("""
                    UPDATE contrats SET
                        montant_engage_cumul = MAX(0, montant_engage_cumul - ?),
                        montant_restant = montant_restant + ?
                    WHERE id = ?
                """, (montant, montant, bc['contrat_id']))

            cur.execute("""
                UPDATE bons_commande SET
                    statut='ANNULE', impute=0, montant_engage=0,
                    ligne_budgetaire_id=NULL, date_maj=?
                WHERE id=?
            """, (now, bc_id))

            conn.commit()
            return {'ok': True, 'message': f"BC annulé — {montant:,.2f} € remboursés sur la ligne"}

        except Exception as e:
            if conn: conn.rollback()
            logger.error(f"Erreur annulation imputation BC {bc_id} : {e}")
            return {'ok': False, 'message': str(e)}

    # =========================================================================
    # PRÉPARATION BUDGET N+1
    # =========================================================================

    def get_apercu_n1(self, entite_id, exercice_source, exercice_cible):
        """
        Calcule l apercu des lignes qui seront generees pour N+1.
        Retourne une liste de dicts avec toutes les infos pour affichage.
        """
        conn = self.db.get_connection()
        cur  = conn.cursor()
        lignes_apercu = []

        for nature in ('FONCTIONNEMENT', 'INVESTISSEMENT'):
            lignes_src = cur.execute("""
                SELECT lb.*,
                    COALESCE(a.nom, '') AS application_nom,
                    COALESCE(p.code || ' - ' || p.nom, '') AS projet_nom
                FROM lignes_budgetaires lb
                JOIN budgets_annuels ba ON ba.id=lb.budget_id
                LEFT JOIN applications a ON a.id=lb.application_id
                LEFT JOIN projets p ON p.id=lb.projet_id
                WHERE ba.entite_id=? AND ba.exercice=? AND ba.nature=?
            """, (entite_id, exercice_source, nature)).fetchall()

            for src in lignes_src:
                src = dict(src)
                vote     = float(src.get('montant_vote') or 0)
                engage   = float(src.get('montant_engage') or 0)
                paye     = float(src.get('montant_paye') or 0)
                solde    = float(src.get('montant_solde') or 0)
                taux     = (engage / vote * 100) if vote > 0 else 0

                # Compter les BC lies
                nb_bc = (cur.execute(
                    "SELECT COUNT(*) FROM bons_commande WHERE ligne_budgetaire_id=?",
                    (src['id'],)).fetchone() or [0])[0]

                # Calcul suggestion N+1
                if solde < 0:
                    # Depassement : voté + depassement + 10% marge
                    suggestion = engage * 1.10
                    raison = 'Depassement N -> +10% marge'
                elif taux > 90:
                    # Tres consomme : augmenter de 15%
                    suggestion = vote * 1.15
                    raison = 'Taux >90% -> +15%'
                elif taux < 30 and vote > 0:
                    # Peu consomme : reduire de 20%
                    suggestion = vote * 0.80
                    raison = 'Taux <30% -> -20%'
                else:
                    # Normal : reconduire le vote
                    suggestion = vote if vote > 0 else float(src.get('montant_prevu') or 0)
                    raison = 'Reconduction'

                # Note enrichie
                note_parts = [f"Source : {exercice_source}"]
                note_parts.append(f"Vote N : {vote:,.0f} EUR")
                note_parts.append(f"Consomme N : {engage:,.0f} EUR ({taux:.0f}%)")
                if solde < 0:
                    note_parts.append(f"DEPASSEMENT : {abs(solde):,.0f} EUR")
                note_parts.append(f"Paye N : {paye:,.0f} EUR")
                note_parts.append(f"BC lies : {nb_bc}")
                note_parts.append(f"Suggestion : {raison}")
                note = ' | '.join(note_parts)

                lignes_apercu.append({
                    'libelle':       src['libelle'],
                    'nature':        nature,
                    'vote_n':        vote,
                    'engage_n':      engage,
                    'paye_n':        paye,
                    'solde_n':       solde,
                    'taux_n':        taux,
                    'nb_bc':         nb_bc,
                    'suggestion':    round(suggestion, 2),
                    'raison':        raison,
                    'note_generee':  note,
                    'application_nom': src.get('application_nom', ''),
                    'projet_nom':    src.get('projet_nom', ''),
                    'application_id': src.get('application_id'),
                    'projet_id':     src.get('projet_id'),
                    'seuil_alerte_pct': src.get('seuil_alerte_pct', 80),
                    'fournisseur_id': src.get('fournisseur_id'),
                    'source':        'LIGNE',
                    'alerte':        solde < 0 or taux > 90,
                })

            # Projets actifs lies a cette entite
            projets_actifs = cur.execute("""
                SELECT p.*, e.code AS entite_code
                FROM projets p
                JOIN entites e ON e.id = ?
                WHERE p.statut IN ('ACTIF', 'EN_COURS', 'PLANIFIE')
                  AND p.statut != 'TERMINE'
            """, (entite_id,)).fetchall()

            for proj in projets_actifs:
                proj = dict(proj)
                budget_p = float(proj.get('montant_prevu') or proj.get('budget_initial') or 0)
                engage_p = float(proj.get('montant_engage') or 0)
                restant  = budget_p - engage_p
                if restant <= 0:
                    continue
                libelle = f"Projet {proj.get('code','')} - {proj.get('nom','')[:50]}"
                # Eviter doublon avec lignes existantes
                if any(l['libelle'] == libelle for l in lignes_apercu):
                    continue
                note = (f"Projet actif | Budget prevu : {budget_p:,.0f} EUR | "
                        f"Engage : {engage_p:,.0f} EUR | Restant : {restant:,.0f} EUR")
                lignes_apercu.append({
                    'libelle':       libelle,
                    'nature':        nature,
                    'vote_n':        budget_p,
                    'engage_n':      engage_p,
                    'paye_n':        0,
                    'solde_n':       restant,
                    'taux_n':        (engage_p/budget_p*100) if budget_p > 0 else 0,
                    'nb_bc':         0,
                    'suggestion':    round(restant, 2),
                    'raison':        'Projet actif N+1',
                    'note_generee':  note,
                    'application_id': proj.get('application_id'),
                    'projet_id':     proj.get('id'),
                    'application_nom': '',
                    'projet_nom':    proj.get('nom', ''),
                    'seuil_alerte_pct': 80,
                    'fournisseur_id': None,
                    'source':        'PROJET',
                    'alerte':        False,
                })

        return lignes_apercu

    def preparer_budget_n1(self, entite_id, exercice_source, exercice_cible,
                           lignes_validees=None):
        """
        Pré-remplit les budgets N+1 à partir de l'historique de l'année source.
        lignes_validees : liste de dicts avec 'libelle','nature','montant_prevu_n1','note'
                          si None -> calcul automatique depuis get_apercu_n1
        Retourne le nb de lignes créées.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cur  = conn.cursor()
            nb   = 0
            now  = datetime.now().isoformat()

            # Si lignes_validees non fourni -> calcul auto depuis apercu
            if lignes_validees is None:
                lignes_validees = self.get_apercu_n1(entite_id, exercice_source, exercice_cible)
                # Convertir suggestion en montant_prevu_n1
                for l in lignes_validees:
                    l['montant_prevu_n1'] = l['suggestion']
                    l['note'] = l['note_generee']

            for nature in ('FONCTIONNEMENT', 'INVESTISSEMENT'):
                # Recuperer ou creer le budget cible
                existing = cur.execute("""
                    SELECT id FROM budgets_annuels
                    WHERE entite_id=? AND exercice=? AND nature=?
                """, (entite_id, exercice_cible, nature)).fetchone()

                if existing:
                    budget_cible_id = existing[0]
                else:
                    cur.execute("""
                        INSERT INTO budgets_annuels
                            (entite_id, exercice, nature, statut, date_creation, date_maj)
                        VALUES (?, ?, ?, 'EN_PREPARATION', ?, ?)
                    """, (entite_id, exercice_cible, nature, now, now))
                    budget_cible_id = cur.lastrowid

                lignes_nature = [l for l in lignes_validees if l.get('nature') == nature]

                for lg in lignes_nature:
                    libelle = lg['libelle']
                    already = cur.execute(
                        "SELECT id FROM lignes_budgetaires WHERE budget_id=? AND libelle=?",
                        (budget_cible_id, libelle)).fetchone()
                    if already:
                        continue

                    montant = float(lg.get('montant_prevu_n1') or lg.get('suggestion') or 0)
                    cur.execute("""
                        INSERT INTO lignes_budgetaires
                            (budget_id, libelle, application_id, projet_id,
                             fournisseur_id, montant_prevu, montant_prevu_n1,
                             nature, seuil_alerte_pct, note,
                             statut, date_creation, date_maj)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIF', ?, ?)
                    """, (budget_cible_id, libelle,
                          lg.get('application_id'), lg.get('projet_id'),
                          lg.get('fournisseur_id'), montant, montant,
                          nature, lg.get('seuil_alerte_pct', 80),
                          lg.get('note', f"Genere depuis {exercice_source}"),
                          now, now))
                    nb += 1

                # Contrats de maintenance actifs non encore inclus
                contrats_maint = cur.execute("""
                    SELECT c.*, f.nom as fournisseur_nom FROM contrats c
                    JOIN fournisseurs f ON f.id=c.fournisseur_id
                    WHERE c.entite_id=? AND c.nature=?
                    AND c.type_contrat='MARCHE_MAINTENANCE'
                    AND c.statut IN ('ACTIF','RECONDUIT')
                    AND c.date_fin >= date(?, '-6 months')
                """, (entite_id, nature, f"{exercice_cible}-01-01")).fetchall()

                for ct in contrats_maint:
                    ct = dict(ct)
                    libelle = f"Maintenance {ct['fournisseur_nom']} - {ct['objet'][:40]}"
                    already = cur.execute(
                        "SELECT id FROM lignes_budgetaires WHERE budget_id=? AND libelle=?",
                        (budget_cible_id, libelle)).fetchone()
                    if already:
                        continue
                    cur.execute("""
                        INSERT INTO lignes_budgetaires
                            (budget_id, libelle, application_id,
                             montant_prevu, montant_prevu_n1, nature,
                             note, statut, date_creation, date_maj)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIF', ?, ?)
                    """, (budget_cible_id, libelle, ct.get('application_id'),
                          ct['montant_ht'], ct['montant_ht'], nature,
                          f"Reconduction contrat {ct['numero_contrat']}",
                          now, now))
                    nb += 1

            conn.commit()
            logger.info("Preparation N+1 : %d lignes creees pour %s", nb, exercice_cible)
            return nb

        except Exception as e:
            if conn: conn.rollback()
            logger.error("Erreur preparation N+1 : %s", e, exc_info=True)
            raise

    # =========================================================================
    # DASHBOARD — SYNTHÈSE VILLE vs CDA
    # =========================================================================

    def get_dashboard_data(self, exercice=None):
        """
        Retourne toutes les données pour le tableau de bord principal :
        - Synthèse par entité (4 budgets : VILLE fonct/invest, CDA fonct/invest)
        - Alertes contrats
        - Top BC en attente de validation
        - Taux d'engagement par ligne (alertes seuil)
        """
        exercice = exercice or datetime.now().year

        # Synthèse budgets
        syntheses = self.get_synthese_budgets(exercice)

        # Alertes contrats (expire dans < 90j)
        alertes_contrats = self.db.fetch_all("""
            SELECT * FROM v_contrats_alertes
            WHERE niveau_alerte IN ('EXPIRE','CRITIQUE','ATTENTION')
            ORDER BY jours_restants
            LIMIT 20
        """)

        # Lignes en alerte seuil
        lignes_alerte = self.db.fetch_all("""
            SELECT * FROM v_lignes_budget
            WHERE alerte_seuil=1 AND exercice=?
            ORDER BY taux_engagement_pct DESC
        """, (exercice,))

        # BC en attente de validation
        bc_attente = self.db.fetch_all("""
            SELECT * FROM v_bons_commande
            WHERE statut IN ('BROUILLON','EN_ATTENTE')
            ORDER BY date_creation DESC
            LIMIT 10
        """)

        # Totaux globaux par entité
        totaux = {}
        for s in syntheses:
            code = s.get('entite_code', '')
            if code not in totaux:
                totaux[code] = {
                    'entite_nom': s.get('entite_nom',''),
                    'montant_vote': 0, 'montant_engage': 0, 'montant_solde': 0
                }
            totaux[code]['montant_vote']   += float(s.get('montant_vote') or 0)
            totaux[code]['montant_engage'] += float(s.get('montant_engage') or 0)
            totaux[code]['montant_solde']  += float(s.get('montant_solde') or 0)

        return {
            'exercice':         exercice,
            'syntheses':        syntheses,
            'totaux_entites':   totaux,
            'alertes_contrats': [_d(r) for r in alertes_contrats] if alertes_contrats else [],
            'lignes_alerte':    [_d(r) for r in lignes_alerte] if lignes_alerte else [],
            'bc_attente':       [_d(r) for r in bc_attente] if bc_attente else [],
        }

    # =========================================================================
    # HELPERS INTERNES
    # =========================================================================

    def _recalc_budget_prevu(self, budget_id):
        """
        Recalcule montant_previsionnel du budget = somme des montants_prevu de ses lignes.
        Recalcule aussi montant_vote si des lignes ont un vote renseigné.
        """
        conn = self.db.get_connection()
        now  = datetime.now().isoformat()

        # Somme montant_prevu des lignes → montant_previsionnel du budget
        row_prevu = conn.execute("""
            SELECT COALESCE(SUM(montant_prevu), 0) as total
            FROM lignes_budgetaires
            WHERE budget_id = ? AND statut != 'CLOTURE'
        """, (budget_id,)).fetchone()
        total_prevu = row_prevu[0] if row_prevu else 0

        conn.execute(
            "UPDATE budgets_annuels SET montant_previsionnel=?, date_maj=? WHERE id=?",
            (total_prevu, now, budget_id)
        )

        # Si des lignes ont un montant_vote → mettre à jour montant_vote + solde budget
        row_vote = conn.execute("""
            SELECT COALESCE(SUM(montant_vote), 0) as total
            FROM lignes_budgetaires
            WHERE budget_id = ? AND montant_vote > 0 AND statut != 'CLOTURE'
        """, (budget_id,)).fetchone()
        total_vote = row_vote[0] if row_vote else 0

        if total_vote > 0:
            conn.execute("""
                UPDATE budgets_annuels SET
                    montant_vote  = ?,
                    montant_solde = ? - COALESCE(montant_engage, 0),
                    date_maj = ?
                WHERE id = ?
            """, (total_vote, total_vote, now, budget_id))

        conn.commit()
        logger.info(f"Budget {budget_id} recalculé — prévu={total_prevu:.0f}€, voté={total_vote:.0f}€")

    def _recalc_budget(self, budget_id):
        """Recalcule montant_engage + montant_solde du budget depuis ses lignes."""
        conn = self.db.get_connection()
        cur  = conn.cursor()
        self._recalc_budget_id(cur, budget_id)
        conn.commit()

    def _recalc_budget_from_ligne(self, cur, ligne_id):
        """Recalcule le budget parent à partir d'un curseur existant."""
        row = cur.execute(
            "SELECT budget_id FROM lignes_budgetaires WHERE id=?", (ligne_id,)).fetchone()
        if row:
            self._recalc_budget_id(cur, row[0])

    def _recalc_budget_id(self, cur, budget_id):
        cur.execute("""
            UPDATE budgets_annuels SET
                montant_engage = COALESCE((
                    SELECT SUM(montant_engage) FROM lignes_budgetaires
                    WHERE budget_id=?
                ), 0),
                montant_solde = montant_vote - COALESCE((
                    SELECT SUM(montant_engage) FROM lignes_budgetaires
                    WHERE budget_id=?
                ), 0),
                date_maj = ?
            WHERE id=?
        """, (budget_id, budget_id, datetime.now().isoformat(), budget_id))


# Singleton
budget_v5_service = BudgetV5Service()
