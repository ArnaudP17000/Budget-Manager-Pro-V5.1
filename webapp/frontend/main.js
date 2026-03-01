// Exemple d'appel API pour chaque vue principale
function loadDashboard() {
    fetch('/api/dashboard')
        .then(r => r.json())
        .then(data => {
            document.getElementById('kpi-projets').textContent = 'Projets actifs: ' + data.kpi_projets;
            document.getElementById('kpi-budget').textContent = 'Budget total (€): ' + data.kpi_budget;
            document.getElementById('kpi-bc').textContent = 'Bons de commande: ' + data.kpi_bons_commande;
        });
}

function loadBudget() {
    fetch('/api/budget')
        .then(r => r.json())
        .then(data => {
            // Afficher les données du budget
        });
}

function loadBonCommande() {
    fetch('/api/bon_commande')
        .then(r => r.json())
        .then(data => {
            // Afficher la liste des bons de commande
        });
}

function loadContrat() {
    fetch('/api/contrat')
        .then(r => r.json())
        .then(data => {
            // Afficher la liste des contrats
        });
}

function loadProjet() {
    fetch('/api/projet')
        .then(r => r.json())
        .then(data => {
            // Afficher la liste des projets
        });
}

function loadTache() {
    fetch('/api/tache')
        .then(r => r.json())
        .then(data => {
            // Afficher la liste des tâches
        });
}

function loadKanban() {
    fetch('/api/kanban')
        .then(r => r.json())
        .then(data => {
            // Afficher le kanban
        });
}

function loadReferentiels() {
    fetch('/api/referentiels')
        .then(r => r.json())
        .then(data => {
            // Afficher les référentiels
        });
}

// Appel initial pour le dashboard
loadDashboard();
