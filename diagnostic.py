"""
diagnostic.py — Trouve exactement quelle requête SQL plante avec "no such column: statut"
Lancer : python diagnostic.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "budget_manager.db"

def test(conn, label, sql, params=None):
    try:
        cur = conn.cursor()
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        rows = cur.fetchall()
        print(f"  ✅ {label} ({len(rows)} lignes)")
        return True
    except Exception as e:
        print(f"  ❌ {label} : {e}")
        return False

def main():
    print("=" * 60)
    print("  DIAGNOSTIC — Recherche 'no such column: statut'")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 1. Colonnes de chaque table
    print("\n── Colonnes des tables ──────────────────────────────────")
    for table in ['budgets_annuels', 'lignes_budgetaires', 'bons_commande',
                  'contrats', 'projets', 'taches', 'applications', 'entites']:
        try:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            has_statut = '✅' if 'statut' in cols else '❌'
            print(f"  {has_statut} {table}.statut  —  {len(cols)} colonnes total")
        except Exception as e:
            print(f"  ⚠️  {table} : {e}")

    # 2. Tester les vues
    print("\n── Vues ─────────────────────────────────────────────────")
    for vue in ['v_synthese_budget', 'v_lignes_budget', 'v_bons_commande', 'v_contrats_alertes']:
        test(conn, vue, f"SELECT * FROM {vue} LIMIT 1")

    # 3. Tester les requêtes de budget_v5_service
    print("\n── Requêtes budget_v5_service ───────────────────────────")
    annee = 2026

    test(conn, "get_budgets", """
        SELECT ba.*, e.code AS entite_code, e.nom AS entite_nom
        FROM budgets_annuels ba
        JOIN entites e ON e.id=ba.entite_id
        ORDER BY ba.exercice DESC
    """)

    test(conn, "get_synthese_budgets", """
        SELECT ba.id, ba.exercice, ba.nature, ba.statut,
               ba.montant_previsionnel, ba.montant_vote,
               ba.montant_engage, ba.montant_solde,
               e.code AS entite_code, e.nom AS entite_nom
        FROM budgets_annuels ba
        JOIN entites e ON e.id = ba.entite_id
        WHERE ba.exercice=?
    """, (annee,))

    test(conn, "get_dashboard bc_attente", """
        SELECT * FROM v_bons_commande
        WHERE statut IN ('BROUILLON','EN_ATTENTE')
        LIMIT 10
    """)

    test(conn, "get_dashboard lignes_alerte", """
        SELECT * FROM v_lignes_budget
        WHERE alerte_seuil=1 AND exercice=?
    """, (annee,))

    test(conn, "get_lignes direct", """
        SELECT * FROM v_lignes_budget
        WHERE exercice=?
    """, (annee,))

    test(conn, "lignes_budgetaires direct", """
        SELECT id, libelle, statut, montant_vote, montant_engage
        FROM lignes_budgetaires LIMIT 5
    """)

    test(conn, "budgets_annuels.statut direct", """
        SELECT id, exercice, nature, statut FROM budgets_annuels LIMIT 5
    """)

    test(conn, "contrats.statut direct", """
        SELECT id, statut FROM contrats LIMIT 5
    """)

    # 4. Requêtes de dashboard_view (autre dashboard)
    print("\n── Requêtes dashboard_view ──────────────────────────────")
    test(conn, "projets actifs", """
        SELECT COUNT(*) FROM projets WHERE statut NOT IN ('TERMINE','ANNULE')
    """)

    test(conn, "taches en cours", """
        SELECT COUNT(*) FROM taches WHERE statut = 'EN_COURS'
    """)

    test(conn, "bc en attente", """
        SELECT COUNT(*) FROM bons_commande
        WHERE statut NOT IN ('ANNULE','BROUILLON')
    """)

    # 5. Requêtes de reporting_service
    print("\n── Requêtes reporting_service ───────────────────────────")
    test(conn, "reporting projets", """
        SELECT * FROM projets
        WHERE statut NOT IN ('cloture', 'annule') LIMIT 5
    """)

    test(conn, "reporting taches", """
        SELECT * FROM taches
        WHERE statut NOT IN ('terminee', 'annulee') LIMIT 5
    """)

    # 6. Table entites — colonnes actif/statut
    # 7. ETPView — requêtes spécifiques
    print("\n── Requêtes ETP ─────────────────────────────────────────")
    test(conn, "taches LEFT JOIN projets", """
        SELECT t.id, t.titre, t.statut, t.projet_id,
               t.date_debut, t.date_echeance,
               t.estimation_heures, t.heures_reelles,
               t.tags, p.nom AS projet_nom
        FROM taches t
        LEFT JOIN projets p ON p.id = t.projet_id
        WHERE t.statut NOT IN ('TERMINE','ANNULE')
        ORDER BY CASE WHEN t.date_echeance IS NULL THEN 1 ELSE 0 END,
                 t.date_echeance, t.titre
        LIMIT 5
    """)
    test(conn, "projets avec SUM taches", """
        SELECT p.id, p.nom, p.code,
               COALESCE(p.statut, 'EN_COURS') AS statut,
               p.date_debut, p.date_fin_prevue,
               COALESCE(SUM(t.estimation_heures), 0) AS h_estimees,
               COALESCE(SUM(t.heures_reelles), 0) AS h_reelles,
               COUNT(t.id) AS nb_taches
        FROM projets p
        LEFT JOIN taches t ON t.projet_id = p.id
        WHERE COALESCE(p.statut,'') NOT IN ('TERMINE','ABANDONNE','ANNULE')
        GROUP BY p.id
        ORDER BY p.nom
        LIMIT 5
    """)
    test(conn, "taches.estimation_heures existe", """
        SELECT estimation_heures, heures_reelles, tags FROM taches LIMIT 1
    """)
    print("\n── Table entites ────────────────────────────────────────")
    test(conn, "entites.actif", "SELECT * FROM entites WHERE actif=1 LIMIT 5")
    test(conn, "entites.statut", "SELECT statut FROM entites LIMIT 5")
    test(conn, "entites all cols", "SELECT * FROM entites LIMIT 1")

    conn.close()
    print("\n" + "=" * 60)
    print("  FIN DIAGNOSTIC")
    print("=" * 60)

if __name__ == "__main__":
    main()
