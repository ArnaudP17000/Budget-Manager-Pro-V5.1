from flask import Blueprint, jsonify, request

from app.services.projet_service import ProjetService
from app.services.budget_v5_service import BudgetV5Service
from app.services.bon_commande_service import BonCommandeService
from app.services.contrat_service import ContratService
from app.services.tache_service import TacheService
from app.services.referentiel_service import ReferentielService
from app.services.contact_service import ContactService
from app.services.service_org_service import ServiceOrgService

routes = Blueprint('routes', __name__)

projet_service      = ProjetService()
budget_service      = BudgetV5Service()
bc_service          = BonCommandeService()
contrat_service     = ContratService()
referentiel_service = ReferentielService()
tache_service       = TacheService()
contact_service     = ContactService()
service_org_service = ServiceOrgService()


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@routes.route('/dashboard', methods=['GET'])
def dashboard():
    projets       = projet_service.get_all()
    budget        = budget_service.get_budget()
    bons_commande = bc_service.get_all_bons_commande()
    contrats      = contrat_service.get_all()
    alertes       = contrat_service.get_alertes()
    bc_attente    = [b for b in bons_commande if b.get('statut') in ('BROUILLON', 'EN_ATTENTE')]
    return jsonify({
        "kpi_projets":       len(projets),
        "kpi_budget":        sum(b.get('montant_vote', 0) or 0 for b in budget),
        "kpi_bons_commande": len(bons_commande),
        "kpi_montant_bc":    sum(b.get('montant_ttc', 0) or 0 for b in bons_commande),
        "kpi_contrats":      len([c for c in contrats if c.get('statut') == 'ACTIF']),
        "kpi_alertes_contrats": len(alertes),
        "kpi_bc_attente":    len(bc_attente),
        "alertes_contrats":  alertes[:5],
    })


# ─────────────────────────────────────────────
# ENTITÉS
# ─────────────────────────────────────────────

@routes.route('/entites', methods=['GET'])
def get_entites():
    return jsonify({"list": budget_service.get_entites()})


# ─────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────

@routes.route('/applications', methods=['GET'])
def get_applications():
    return jsonify({"list": budget_service.get_all_applications()})


# ─────────────────────────────────────────────
# BUDGETS ANNUELS
# ─────────────────────────────────────────────

@routes.route('/budget', methods=['GET'])
def get_budget():
    budgets = budget_service.get_budget()
    return jsonify({
        "total_vote":   sum(b.get('montant_vote', 0) or 0 for b in budgets),
        "total_engage": sum(b.get('montant_engage', 0) or 0 for b in budgets),
        "details": budgets
    })

@routes.route('/budget/<int:budget_id>/lignes', methods=['GET'])
def get_lignes_budget(budget_id):
    return jsonify({"list": budget_service.get_lignes(budget_id)})

@routes.route('/lignes', methods=['GET'])
def get_all_lignes():
    budget_id = request.args.get('budget_id', type=int)
    return jsonify({"list": budget_service.get_lignes(budget_id)})

@routes.route('/ligne', methods=['POST'])
def create_ligne():
    data = request.json
    try:
        vote = float(data.get('montant_vote') or 0)
        budget_service.db.execute(
            "INSERT INTO lignes_budgetaires "
            "(budget_id, libelle, application_id, fournisseur_id, "
            "montant_prevu, montant_vote, montant_solde, nature, note, statut) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('budget_id'), data.get('libelle'),
             data.get('application_id') or None, data.get('fournisseur_id') or None,
             float(data.get('montant_prevu') or 0), vote, vote,
             data.get('nature') or 'FONCTIONNEMENT',
             data.get('note') or None, data.get('statut') or 'ACTIF']
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/ligne/<int:ligne_id>', methods=['PUT'])
def update_ligne(ligne_id):
    data = request.json
    try:
        vote = float(data.get('montant_vote') or 0)
        budget_service.db.execute(
            "UPDATE lignes_budgetaires SET "
            "budget_id=%s, libelle=%s, application_id=%s, fournisseur_id=%s, "
            "montant_prevu=%s, montant_vote=%s, "
            "montant_solde=GREATEST(%s - COALESCE(montant_engage, 0), 0), "
            "nature=%s, note=%s, statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('budget_id'), data.get('libelle'),
             data.get('application_id') or None, data.get('fournisseur_id') or None,
             float(data.get('montant_prevu') or 0), vote, vote,
             data.get('nature') or 'FONCTIONNEMENT',
             data.get('note') or None, data.get('statut') or 'ACTIF', ligne_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/ligne/<int:ligne_id>/bcs', methods=['GET'])
def get_ligne_bcs(ligne_id):
    bcs = budget_service.db.fetch_all(
        "SELECT bc.id, bc.numero_bc, bc.objet, bc.montant_ht, bc.montant_ttc, "
        "bc.statut, bc.date_creation, bc.date_imputation, bc.date_solde, "
        "f.nom as fournisseur_nom, "
        "c.numero_contrat as contrat_numero, c.objet as contrat_objet, "
        "p.nom as projet_nom "
        "FROM bons_commande bc "
        "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
        "LEFT JOIN contrats c ON c.id = bc.contrat_id "
        "LEFT JOIN projets p ON p.id = bc.projet_id "
        "WHERE bc.ligne_budgetaire_id = %s ORDER BY bc.date_creation DESC",
        [ligne_id]
    )
    return jsonify({"bcs": [dict(b) for b in bcs] if bcs else []})

@routes.route('/budget/<int:budget_id>/detail', methods=['GET'])
def get_budget_detail(budget_id):
    lignes = budget_service.get_lignes(budget_id)
    for ligne in lignes:
        bcs = budget_service.db.fetch_all(
            "SELECT bc.id, bc.numero_bc, bc.objet, bc.montant_ht, bc.montant_ttc, "
            "bc.statut, bc.date_creation, f.nom as fournisseur_nom, "
            "c.numero_contrat as contrat_numero, c.objet as contrat_objet "
            "FROM bons_commande bc "
            "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
            "LEFT JOIN contrats c ON c.id = bc.contrat_id "
            "WHERE bc.ligne_budgetaire_id = %s ORDER BY bc.date_creation DESC",
            [ligne['id']]
        )
        ligne['bons_commande'] = [dict(b) for b in bcs] if bcs else []
    return jsonify({"lignes": lignes})

@routes.route('/budget/<int:budget_id>/voter', methods=['POST'])
def voter_budget(budget_id):
    data = request.json
    try:
        montant_vote = float(data.get('montant_vote') or 0)
        budget_service.voter_budget(budget_id, montant_vote)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/budget', methods=['POST'])
def create_budget():
    data = request.json
    try:
        budget_service.db.execute(
            "INSERT INTO budgets_annuels (entite_id, exercice, nature, montant_previsionnel, statut) "
            "VALUES (%s, %s, %s, %s, %s)",
            [data.get('entite_id') or None, data.get('exercice'), data.get('nature'),
             data.get('montant_previsionnel') or 0, data.get('statut', 'BROUILLON')]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/budget/<int:budget_id>', methods=['PUT'])
def update_budget(budget_id):
    data = request.json
    try:
        budget_service.db.execute(
            "UPDATE budgets_annuels SET entite_id=%s, exercice=%s, nature=%s, "
            "montant_previsionnel=%s, montant_vote=%s, statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('entite_id') or None, data.get('exercice'), data.get('nature'),
             data.get('montant_previsionnel') or 0, data.get('montant_vote') or 0,
             data.get('statut'), budget_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/budget/<int:budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    try:
        budget_service.db.execute("DELETE FROM budgets_annuels WHERE id=%s", [budget_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# BONS DE COMMANDE
# ─────────────────────────────────────────────

@routes.route('/bon_commande', methods=['GET'])
def get_bon_commande():
    filters = {k: v for k, v in request.args.items() if v}
    bc_list = bc_service.get_all_bons_commande(filters)
    return jsonify({"count": len(bc_list), "list": bc_list})

@routes.route('/bon_commande/stats', methods=['GET'])
def get_bc_stats():
    return jsonify(bc_service.get_stats())

@routes.route('/bon_commande/<int:bc_id>', methods=['GET'])
def get_bon_commande_by_id(bc_id):
    bc = bc_service.get_by_id(bc_id)
    if bc:
        return jsonify(bc)
    return jsonify({"error": "BC introuvable"}), 404

@routes.route('/bon_commande/<int:bc_id>/valider', methods=['POST'])
def valider_bc(bc_id):
    try:
        new_statut = bc_service.valider(bc_id)
        return jsonify({"success": True, "statut": new_statut})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/bon_commande/<int:bc_id>/imputer', methods=['POST'])
def imputer_bc(bc_id):
    data = request.json
    ligne_id = data.get('ligne_id')
    if not ligne_id:
        return jsonify({"success": False, "error": "ligne_id requis"}), 400
    try:
        bc_service.imputer(bc_id, ligne_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/bon_commande', methods=['POST'])
def create_bon_commande():
    data = request.json
    try:
        montant_ht  = float(data.get('montant_ht') or 0)
        montant_ttc = float(data.get('montant_ttc') or montant_ht * 1.2)
        bc_service.db.execute(
            "INSERT INTO bons_commande (numero_bc, objet, fournisseur_id, entite_id, "
            "projet_id, ligne_budgetaire_id, contrat_id, montant_ht, montant_ttc, statut) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('numero_bc'), data.get('objet'), data.get('fournisseur_id') or None,
             data.get('entite_id') or None, data.get('projet_id') or None,
             data.get('ligne_budgetaire_id') or None, data.get('contrat_id') or None,
             montant_ht, montant_ttc, data.get('statut', 'BROUILLON')]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/bon_commande/<int:bc_id>', methods=['PUT'])
def update_bon_commande(bc_id):
    data = request.json
    try:
        montant_ht  = float(data.get('montant_ht') or 0)
        montant_ttc = float(data.get('montant_ttc') or montant_ht * 1.2)
        bc_service.db.execute(
            "UPDATE bons_commande SET numero_bc=%s, objet=%s, fournisseur_id=%s, "
            "entite_id=%s, projet_id=%s, ligne_budgetaire_id=%s, contrat_id=%s, "
            "montant_ht=%s, montant_ttc=%s, statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('numero_bc'), data.get('objet'), data.get('fournisseur_id') or None,
             data.get('entite_id') or None, data.get('projet_id') or None,
             data.get('ligne_budgetaire_id') or None, data.get('contrat_id') or None,
             montant_ht, montant_ttc, data.get('statut'), bc_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/bon_commande/<int:bc_id>', methods=['DELETE'])
def delete_bon_commande(bc_id):
    try:
        bc_service.db.execute("DELETE FROM bons_commande WHERE id=%s", [bc_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# CONTRATS
# ─────────────────────────────────────────────

@routes.route('/contrat', methods=['GET'])
def get_contrats():
    contrats = contrat_service.get_all()
    return jsonify({"count": len(contrats), "list": contrats})

@routes.route('/contrat/<int:contrat_id>', methods=['GET'])
def get_contrat_by_id(contrat_id):
    c = contrat_service.get_by_id(contrat_id)
    if not c:
        return jsonify({"error": "Contrat introuvable"}), 404
    return jsonify(c)

@routes.route('/contrat/alertes', methods=['GET'])
def get_contrat_alertes():
    return jsonify({"list": contrat_service.get_alertes()})

@routes.route('/contrat/<int:contrat_id>/reconduire', methods=['POST'])
def reconduire_contrat(contrat_id):
    data = request.json
    nouvelle_date_fin = data.get('nouvelle_date_fin')
    if not nouvelle_date_fin:
        return jsonify({"success": False, "error": "nouvelle_date_fin requise"}), 400
    try:
        contrat_service.reconduire(contrat_id, nouvelle_date_fin)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contrat', methods=['POST'])
def create_contrat():
    data = request.json
    try:
        montant_ht = float(data.get('montant_total_ht') or 0)
        contrat_service.db.execute(
            "INSERT INTO contrats (numero_contrat, objet, fournisseur_id, montant_initial_ht, "
            "montant_total_ht, montant_ttc, date_debut, date_fin, statut) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('numero_contrat'), data.get('objet'), data.get('fournisseur_id') or None,
             montant_ht, montant_ht, round(montant_ht * 1.2, 2),
             data.get('date_debut') or None, data.get('date_fin') or None,
             data.get('statut', 'ACTIF')]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contrat/<int:contrat_id>', methods=['PUT'])
def update_contrat(contrat_id):
    data = request.json
    try:
        montant_ht = float(data.get('montant_total_ht') or 0)
        contrat_service.db.execute(
            "UPDATE contrats SET numero_contrat=%s, objet=%s, fournisseur_id=%s, "
            "montant_total_ht=%s, montant_ttc=%s, date_debut=%s, date_fin=%s, "
            "statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('numero_contrat'), data.get('objet'), data.get('fournisseur_id') or None,
             montant_ht, round(montant_ht * 1.2, 2),
             data.get('date_debut') or None, data.get('date_fin') or None,
             data.get('statut'), contrat_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contrat/<int:contrat_id>', methods=['DELETE'])
def delete_contrat(contrat_id):
    try:
        contrat_service.db.execute("DELETE FROM contrats WHERE id=%s", [contrat_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# PROJETS
# ─────────────────────────────────────────────

@routes.route('/projet', methods=['GET'])
def get_projets():
    filters = request.args.to_dict()
    projets = projet_service.get_all(filters)
    return jsonify({"count": len(projets), "list": projets})

@routes.route('/projet/<int:projet_id>', methods=['GET'])
def get_projet(projet_id):
    p = projet_service.get_by_id(projet_id)
    if not p:
        return jsonify({"error": "Projet introuvable"}), 404
    return jsonify(p)

@routes.route('/projet', methods=['POST'])
def create_projet():
    data = request.json
    try:
        projet_service.db.execute(
            "INSERT INTO projets (code, nom, description, statut, priorite, type_projet, phase, "
            "service_id, date_debut, date_fin_prevue, date_fin_reelle, "
            "budget_initial, budget_estime, budget_actuel, avancement, "
            "objectifs, enjeux, gains, risques, contraintes, solutions) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [data.get('code'), data.get('nom'), data.get('description'), data.get('statut'),
             data.get('priorite'), data.get('type_projet') or None, data.get('phase') or None,
             data.get('service_id') or None,
             data.get('date_debut') or None, data.get('date_fin_prevue') or None,
             data.get('date_fin_reelle') or None,
             data.get('budget_initial') or None, data.get('budget_estime') or None,
             data.get('budget_actuel') or None, data.get('avancement') or 0,
             data.get('objectifs') or None, data.get('enjeux') or None,
             data.get('gains') or None, data.get('risques') or None,
             data.get('contraintes') or None, data.get('solutions') or None]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/projet/<int:projet_id>', methods=['PUT'])
def update_projet(projet_id):
    data = request.json
    try:
        projet_service.db.execute(
            "UPDATE projets SET code=%s, nom=%s, description=%s, statut=%s, priorite=%s, "
            "type_projet=%s, phase=%s, service_id=%s, "
            "date_debut=%s, date_fin_prevue=%s, date_fin_reelle=%s, "
            "budget_initial=%s, budget_estime=%s, budget_actuel=%s, avancement=%s, "
            "objectifs=%s, enjeux=%s, gains=%s, risques=%s, contraintes=%s, solutions=%s, "
            "updated_at=NOW() WHERE id=%s",
            [data.get('code'), data.get('nom'), data.get('description'), data.get('statut'),
             data.get('priorite'), data.get('type_projet') or None, data.get('phase') or None,
             data.get('service_id') or None,
             data.get('date_debut') or None, data.get('date_fin_prevue') or None,
             data.get('date_fin_reelle') or None,
             data.get('budget_initial') or None, data.get('budget_estime') or None,
             data.get('budget_actuel') or None, data.get('avancement') or 0,
             data.get('objectifs') or None, data.get('enjeux') or None,
             data.get('gains') or None, data.get('risques') or None,
             data.get('contraintes') or None, data.get('solutions') or None,
             projet_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/projet/<int:projet_id>', methods=['DELETE'])
def delete_projet(projet_id):
    try:
        projet_service.db.execute("DELETE FROM projets WHERE id=%s", [projet_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# TÂCHES
# ─────────────────────────────────────────────

@routes.route('/tache', methods=['GET'])
def get_taches():
    taches = tache_service.get_all()
    return jsonify({"count": len(taches), "list": taches})

@routes.route('/tache', methods=['POST'])
def create_tache():
    data = request.json
    try:
        tache_service.db.execute(
            "INSERT INTO taches (projet_id, titre, statut, priorite, date_echeance, "
            "estimation_heures, avancement) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [data.get('projet_id') or None, data.get('titre'),
             data.get('statut', 'A faire'), data.get('priorite'),
             data.get('date_echeance') or None,
             data.get('estimation_heures') or None, data.get('avancement') or 0]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/tache/<int:tache_id>', methods=['GET'])
def get_tache_by_id(tache_id):
    try:
        row = tache_service.db.fetch_one(
            "SELECT t.*, p.nom as projet_nom FROM taches t "
            "LEFT JOIN projets p ON p.id = t.projet_id WHERE t.id = %s",
            [tache_id]
        )
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Tâche introuvable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes.route('/tache/<int:tache_id>', methods=['PUT'])
def update_tache(tache_id):
    data = request.json
    try:
        tache_service.db.execute(
            "UPDATE taches SET projet_id=%s, titre=%s, statut=%s, priorite=%s, "
            "date_echeance=%s, estimation_heures=%s, avancement=%s, updated_at=NOW() WHERE id=%s",
            [data.get('projet_id') or None, data.get('titre'), data.get('statut'),
             data.get('priorite'), data.get('date_echeance') or None,
             data.get('estimation_heures') or None, data.get('avancement') or 0, tache_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/tache/<int:tache_id>', methods=['DELETE'])
def delete_tache(tache_id):
    try:
        tache_service.db.execute("DELETE FROM taches WHERE id=%s", [tache_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# FOURNISSEURS
# ─────────────────────────────────────────────

@routes.route('/fournisseur', methods=['GET'])
def get_fournisseurs_list():
    try:
        rows = referentiel_service.db.fetch_all(
            "SELECT f.*, "
            "(SELECT COUNT(*) FROM contrats c WHERE c.fournisseur_id=f.id) as nb_contrats, "
            "(SELECT COUNT(*) FROM bons_commande bc WHERE bc.fournisseur_id=f.id) as nb_bc, "
            "(SELECT COALESCE(SUM(bc.montant_ttc),0) FROM bons_commande bc WHERE bc.fournisseur_id=f.id) as montant_total "
            "FROM fournisseurs f ORDER BY f.nom"
        )
        result = [dict(r) for r in rows] if rows else []
        return jsonify({"count": len(result), "list": result})
    except Exception as e:
        return jsonify({"count": 0, "list": [], "error": str(e)})

@routes.route('/fournisseur', methods=['POST'])
def create_fournisseur():
    data = request.json
    try:
        referentiel_service.db.execute(
            "INSERT INTO fournisseurs (nom, contact_principal, email, telephone, adresse, ville, statut) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [data.get('nom'), data.get('contact_principal'), data.get('email'),
             data.get('telephone'), data.get('adresse'), data.get('ville'), 'ACTIF']
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/fournisseur/<int:fournisseur_id>', methods=['PUT'])
def update_fournisseur(fournisseur_id):
    data = request.json
    try:
        referentiel_service.db.execute(
            "UPDATE fournisseurs SET nom=%s, contact_principal=%s, email=%s, "
            "telephone=%s, adresse=%s, ville=%s WHERE id=%s",
            [data.get('nom'), data.get('contact_principal'), data.get('email'),
             data.get('telephone'), data.get('adresse'), data.get('ville'), fournisseur_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/fournisseur/<int:fournisseur_id>', methods=['DELETE'])
def delete_fournisseur(fournisseur_id):
    try:
        referentiel_service.db.execute("DELETE FROM fournisseurs WHERE id=%s", [fournisseur_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# CONTACTS
# ─────────────────────────────────────────────

@routes.route('/contact', methods=['GET'])
def get_contacts():
    filters = {k: v for k, v in request.args.items() if v}
    contacts = contact_service.get_all(filters)
    return jsonify({"count": len(contacts), "list": contacts})

@routes.route('/contact', methods=['POST'])
def create_contact():
    data = request.json
    try:
        contact_service.create(data)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contact/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    data = request.json
    try:
        contact_service.update(contact_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contact/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    try:
        contact_service.delete(contact_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# SERVICES (ORGANISATION)
# ─────────────────────────────────────────────

@routes.route('/service_org', methods=['GET'])
def get_services_org():
    services = service_org_service.get_all()
    return jsonify({"count": len(services), "list": services})

@routes.route('/service_org', methods=['POST'])
def create_service_org():
    data = request.json
    try:
        service_org_service.create(data)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/service_org/<int:service_id>', methods=['PUT'])
def update_service_org(service_id):
    data = request.json
    try:
        service_org_service.update(service_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/service_org/<int:service_id>', methods=['DELETE'])
def delete_service_org(service_id):
    try:
        service_org_service.delete(service_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# RÉFÉRENTIELS (données pour les selects)
# ─────────────────────────────────────────────

@routes.route('/referentiels', methods=['GET'])
def get_referentiels():
    try:
        etp          = referentiel_service.get_etp()
        fournisseurs = referentiel_service.get_fournisseurs()
        contacts     = referentiel_service.get_contacts()
        services     = referentiel_service.get_services()
        entites      = budget_service.get_entites()
        projets      = projet_service.get_all()
        lignes       = budget_service.get_lignes()
        applications = budget_service.get_all_applications()
        contrats_ref = contrat_service.db.fetch_all(
            "SELECT id, numero_contrat, objet FROM contrats ORDER BY numero_contrat"
        )
        contrats_ref = [dict(c) for c in contrats_ref] if contrats_ref else []
        return jsonify({
            "etp": etp, "fournisseurs": fournisseurs,
            "contacts": contacts, "services": services,
            "entites": entites, "projets": projets,
            "lignes": lignes, "applications": applications,
            "contrats": contrats_ref,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# KANBAN
# ─────────────────────────────────────────────

@routes.route('/kanban', methods=['GET'])
def kanban():
    projet_id = request.args.get('projet_id')
    filters = {}
    if projet_id:
        filters['projet_id'] = projet_id
    taches = tache_service.get_all()
    if projet_id:
        taches = [t for t in taches if str(t.get('projet_id', '')) == str(projet_id)]
    colonnes = ['A faire', 'En cours', 'En attente', 'Bloqué', 'Terminé']
    columns = {c: [] for c in colonnes}
    for t in taches:
        statut = t.get('statut', 'A faire')
        if statut in columns:
            columns[statut].append(t)
        else:
            columns.setdefault(statut, []).append(t)
    return jsonify({"columns": columns})


# ─────────────────────────────────────────────
# ETP / CHARGE (simplifié)
# ─────────────────────────────────────────────

@routes.route('/etp', methods=['GET'])
def etp():
    try:
        rows = projet_service.db.fetch_all(
            "SELECT p.id, p.code, p.nom, p.statut, "
            "COALESCE(SUM(t.estimation_heures), 0) as heures_estimees, "
            "COALESCE(SUM(t.heures_reelles), 0) as heures_reelles, "
            "COUNT(t.id) as nb_taches "
            "FROM projets p "
            "LEFT JOIN taches t ON t.projet_id = p.id "
            "WHERE p.statut NOT IN ('Terminé', 'Annulé') "
            "GROUP BY p.id, p.code, p.nom, p.statut "
            "ORDER BY heures_estimees DESC"
        )
        result = [dict(r) for r in rows] if rows else []
        total_h = sum(r.get('heures_estimees', 0) or 0 for r in result)
        return jsonify({
            "list": result,
            "total_heures": total_h,
            "total_jours": round(total_h / 7, 1),
            "total_etp": round(total_h / 154, 2),
        })
    except Exception as e:
        return jsonify({"list": [], "error": str(e)})


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

@routes.route('/notifications', methods=['GET'])
def get_notifications():
    try:
        rows = budget_service.db.fetch_all(
            "SELECT * FROM notifications ORDER BY date_creation DESC LIMIT 50"
        )
        result = [dict(r) for r in rows] if rows else []
        non_lues = sum(1 for r in result if not r.get('lue'))
        return jsonify({"list": result, "non_lues": non_lues})
    except Exception as e:
        return jsonify({"list": [], "non_lues": 0})

@routes.route('/notifications/<int:notif_id>/lire', methods=['POST'])
def lire_notification(notif_id):
    try:
        budget_service.db.execute("UPDATE notifications SET lue=true WHERE id=%s", [notif_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
