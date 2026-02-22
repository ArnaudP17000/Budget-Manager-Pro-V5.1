"""
recalc_lignes.py — Recalcule montant_engage et montant_solde
de TOUTES les lignes budgetaires a partir des BC reels.
A lancer une seule fois pour reparer une ligne sur-imputee.
Usage : python recalc_lignes.py
"""
import sqlite3, sys, os

# Chercher la base automatiquement
DB_CANDIDATES = [
    r"D:\Budget-Manager-Pro-V5\budget_manager.db",
    r"D:\Budget-Manager-Pro-V5\data\budget_manager.db",
    r"D:\Budget-Manager-Pro-V5\budget.db",
]

def find_db():
    for p in DB_CANDIDATES:
        if os.path.exists(p):
            return p
    # Chercher dans le dossier courant
    for f in os.listdir('.'):
        if f.endswith('.db'):
            return f
    return None

db_path = find_db()
if not db_path:
    print("ERREUR : base de donnees introuvable.")
    print("Modifiez DB_CANDIDATES dans ce script avec le bon chemin.")
    sys.exit(1)

print(f"Base : {db_path}")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Lister toutes les lignes budgetaires
lignes = cur.execute("SELECT id, libelle, montant_vote, montant_engage, montant_solde FROM lignes_budgetaires").fetchall()
print(f"\n{len(lignes)} ligne(s) budgetaire(s) trouvee(s)\n")
print(f"{'ID':>4}  {'Libelle':<40}  {'Vote':>12}  {'Engage actuel':>14}  {'Engage reel':>12}  {'Ecart':>10}")
print("-" * 100)

corrections = []

for lb in lignes:
    lid      = lb['id']
    libelle  = (lb['libelle'] or '')[:40]
    vote     = float(lb['montant_vote'] or 0)
    eng_actu = float(lb['montant_engage'] or 0)

    # Calculer le vrai engage depuis les BC
    row = cur.execute("""
        SELECT COALESCE(SUM(montant_ttc), 0) AS total_engage,
               COALESCE(SUM(CASE WHEN statut='SOLDE' THEN montant_ttc ELSE 0 END), 0) AS total_paye
        FROM bons_commande
        WHERE ligne_budgetaire_id = ?
          AND statut IN ('IMPUTE', 'SOLDE')
    """, (lid,)).fetchone()

    eng_reel  = float(row['total_engage'] or 0)
    paye_reel = float(row['total_paye'] or 0)
    ecart     = eng_actu - eng_reel

    flag = "  ⚠️  ECART" if abs(ecart) > 0.01 else ""
    print(f"{lid:>4}  {libelle:<40}  {vote:>12,.2f}  {eng_actu:>14,.2f}  {eng_reel:>12,.2f}  {ecart:>10,.2f}{flag}")

    if abs(ecart) > 0.01:
        corrections.append((lid, libelle, vote, eng_actu, eng_reel, paye_reel, ecart))

print(f"\n{len(corrections)} ligne(s) a corriger")

if not corrections:
    print("Tout est coherent, aucune correction necessaire.")
    conn.close()
    sys.exit(0)

print("\nLignes a corriger :")
for lid, libelle, vote, eng_actu, eng_reel, paye_reel, ecart in corrections:
    solde_reel = vote - eng_reel
    print(f"  ID {lid} : {libelle}")
    print(f"    Engage : {eng_actu:,.2f} -> {eng_reel:,.2f}  (ecart : {ecart:+,.2f})")
    print(f"    Solde  : {vote - eng_actu:,.2f} -> {solde_reel:,.2f}")
    print(f"    Paye   : {paye_reel:,.2f}")

rep = input("\nAppliquer les corrections ? (o/n) : ").strip().lower()
if rep != 'o':
    print("Annule.")
    conn.close()
    sys.exit(0)

from datetime import datetime
now = datetime.now().isoformat()

for lid, libelle, vote, eng_actu, eng_reel, paye_reel, ecart in corrections:
    solde_reel = vote - eng_reel
    cur.execute("""
        UPDATE lignes_budgetaires SET
            montant_engage = ?,
            montant_paye   = ?,
            montant_solde  = ?,
            date_maj       = ?
        WHERE id = ?
    """, (eng_reel, paye_reel, solde_reel, now, lid))
    print(f"  ✅ Ligne {lid} corrigee : engage {eng_actu:,.2f} -> {eng_reel:,.2f}")

conn.commit()
conn.close()
print("\n✅ Corrections appliquees avec succes.")
