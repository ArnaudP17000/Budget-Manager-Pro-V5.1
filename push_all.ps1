Write-Host "`n=== Push complet vers GitHub ===" -ForegroundColor Cyan

# 1. Vérifier l'état actuel
Write-Host "`n📋 Fichiers modifiés :" -ForegroundColor Yellow
git status

# 2. Ajouter TOUS les fichiers modifiés
Write-Host "`n➕ Ajout de tous les fichiers..." -ForegroundColor Yellow
git add .

# 3. Créer un commit avec un message descriptif
Write-Host "`n💾 Création du commit..." -ForegroundColor Yellow
git commit -m "feat: Amélioration contacts et Kanban

- Ajout types contacts: INTERNE, EXTERNE
- Migration base de données pour nouveaux types
- Correction filtres et conditions contact_dialog.py
- Correction filtres contact_view.py
- Ajout refresh_all() et load_projets() dans kanban_view.py
- Sauvegarde base de données"

# 4. Pousser vers GitHub
Write-Host "`n🚀 Push vers GitHub..." -ForegroundColor Yellow
git push origin main

Write-Host "`n✅ Push terminé avec succès !" -ForegroundColor Green