# Guide Utilisateur - Budget Manager Pro V4.2

## 🚀 Démarrage rapide

### Première connexion

1. Lancer l'application : `python run.py`
2. L'application s'ouvre sur le **Dashboard**
3. Choisir votre thème : **Affichage → Thème** (Clair ou Sombre)

## 📊 Le Dashboard

Le Dashboard est votre point d'entrée principal. Il affiche :

### KPI (Indicateurs clés)
- **📁 Projets actifs** : Nombre de projets en cours
- **💰 Budget total** : Montant total des AP actives
- **🛒 BC en attente** : Bons de commande à valider
- **📄 Contrats actifs** : Nombre de contrats en cours

### Informations budgétaires
- Crédits votés (BP + DM)
- Crédits disponibles
- Montants engagés
- Taux d'engagement en %

### Alertes
- BC en attente de validation
- Contrats arrivant à échéance (< 3 mois)
- Dépassements budgétaires

## 📁 Gestion des projets

### Créer un nouveau projet

1. **Menu : Projets → Nouveau projet** (ou Ctrl+N)
2. Remplir le formulaire :
   - **Nom** * : Obligatoire
   - **Description** : Détails du projet
   - **Type** : Infrastructure, Application, Réseau, Sécurité, Support, Autre
   - **Phase** : Étude, Conception, Réalisation, Recette, Clôture
   - **Priorité** : Critique, Haute, Moyenne, Basse
   - **Statut** : Actif, En attente, Terminé, Annulé
   - **Dates** : Début et fin prévue
   - **Avancement** : % (0-100)
   - **Budget estimé** : En euros
3. **Enregistrer**

### Modifier un projet

1. Sélectionner le projet dans la liste
2. Cliquer sur "Éditer"
3. Modifier les champs
4. Enregistrer

## 💰 Gestion budgétaire

### Créer une AP (Autorisation de Programme)

Les AP sont des enveloppes budgétaires pluriannuelles pour l'investissement.

1. **Menu : Budget → Nouvelle AP**
2. Remplir :
   - **Numéro** * : Ex: AP-2024-001
   - **Libellé** * : Description
   - **Montant total** * : Montant global en euros
   - **Exercices** : Année de début et de fin
   - **Chapitre M57** : Classification comptable (ex: 2313)
   - **Fonction M57** : Fonction budgétaire (ex: 01)
   - **Opération** : Code opération d'investissement
   - **Statut** : Active, Clôturée, Annulée
3. **Enregistrer**

### Créer un CP (Crédit de Paiement)

Les CP sont les crédits annuels rattachés à une AP.

1. **Menu : Budget → Nouveau CP**
2. Remplir :
   - **AP** * : Sélectionner l'AP parente
   - **Exercice** * : Année budgétaire
   - **Montant voté** * : Crédit voté pour l'exercice
   - Le montant disponible s'ajuste automatiquement
   - **Date de vote**
   - **Statut** : Actif, Clôturé, Annulé
3. **Enregistrer**

Le système calculera automatiquement :
- Montant disponible = Voté - Engagé
- Taux d'engagement

## 🛒 Bons de commande

### Créer un BC

1. **Menu : Achats → Nouveau Bon de commande** (ou Ctrl+B)
2. **Identification** :
   - **Numéro BC** * : Saisie **manuelle** (ex: BC2024-0001)
   - Date de création
3. **Classification budgétaire** :
   - **Type Budget** * : **FONCTIONNEMENT** ou **INVESTISSEMENT**
   - Nature comptable : Chapitre M57 (ex: 2313)
   - Fonction M57 (ex: 01)
   - Opération : Si investissement
4. **Objet** :
   - **Objet** * : Description courte
   - Description : Détails
   - **Fournisseur** * : Sélectionner
5. **Montants** :
   - **Montant HT** *
   - TVA (%) : 20% par défaut
   - Montant TTC : Calculé automatiquement
6. **Validation** :
   - ✅ **Cocher "BC Validé"** pour valider
   - L'imputation budgétaire sera **automatique**
   - Choisir le statut
7. **Livraison** :
   - Date de livraison prévue
8. **Enregistrer**

### Workflow BC

```
BROUILLON → EN_ATTENTE → ✅ VALIDÉ → IMPUTÉ → RÉCEPTIONNÉ
```

Quand vous cochez "BC Validé" :
- Le BC est marqué comme validé
- Le montant est **automatiquement imputé** sur le budget
- Un engagement budgétaire est créé
- Le statut passe à VALIDE puis IMPUTE

### Consulter les BC

1. Menu : Achats → Bons de commande
2. Filtrer par statut, fournisseur, projet
3. Voir les détails, modifier, valider

## 📄 Contrats

### Créer un contrat

1. **Menu : Achats → Nouveau Contrat**
2. **Identification** :
   - **Numéro** * : Ex: 2024-DSI-001
   - **Type** * : Marché public, MAPA, Appel d'offres, Accord-cadre, Convention, DSP
   - **Objet** * : Description
3. **Classification** :
   - **Type Budget** * : Fonctionnement ou Investissement
   - Nature comptable, Fonction
4. **Fournisseur** * : Sélectionner
5. **Montants** :
   - **Montant initial HT** *
   - Montant total HT : Avec avenants
   - Montant TTC : Calculé automatiquement
6. **Période** :
   - **Date début** * et **Date fin** *
   - Durée en mois : Calculée automatiquement
   - Reconduction tacite : Case à cocher
   - Nombre de reconductions
7. **Statut** : Brouillon, Actif, Reconduit, Résilié, Terminé
8. **Enregistrer**

### Alertes d'échéance

Le système génère automatiquement des alertes :
- **3 mois avant échéance** : "Contrat arrive à terme"
- **1 mois avant** : "Décision urgente"
- Sur le Dashboard dans la section Alertes

### Suivre la consommation

- Créer des BC rattachés au contrat
- Le système calcule le montant consommé
- Alerte si > 80% du montant

## ✅ To-do list

### Créer une to-do

1. Menu : À faire → Nouvelle to-do
2. Remplir :
   - Titre
   - Description
   - Priorité : Critique, Haute, Moyenne, Basse
   - Échéance
   - Rattachement à un projet (optionnel)
   - Tags
3. Enregistrer

### Gérer les to-do

- Changer le statut : À faire → En cours → Terminé
- Modifier, supprimer
- Filtrer par priorité, échéance
- Vue par utilisateur

## 🎨 Personnalisation

### Changer le thème

1. **Menu : Affichage → Thème**
2. Choisir **Clair** ou **Sombre**
3. Le changement est **immédiat**
4. Le thème est **sauvegardé automatiquement**

### Thème Clair
- Fond blanc/gris clair
- Texte foncé
- Idéal pour travail en journée

### Thème Sombre
- Fond sombre
- Texte clair
- Réduit la fatigue oculaire
- Idéal pour travail prolongé

## 🔍 Recherche et filtres

### Rechercher un projet
1. Vue Projets
2. Barre de recherche : Nom, description
3. Filtres : Phase, Priorité, Statut

### Rechercher un BC
1. Vue Bons de commande
2. Filtres : Statut, Fournisseur, Projet, Montant

### Rechercher un contrat
1. Vue Contrats
2. Filtres : Type, Statut, Fournisseur, Échéance

## 💡 Bonnes pratiques

### Projets
- Créer une AP avant le projet
- Associer le projet à l'AP
- Mettre à jour l'avancement régulièrement
- Créer des tâches pour suivre le détail

### Budget
- Créer les AP en début d'exercice
- Créer les CP pour chaque exercice
- Vérifier la disponibilité avant engagement

### Bons de commande
- Toujours remplir le numéro manuellement
- Choisir le bon type F/I
- Remplir la classification M57
- **Cocher "BC Validé"** seulement après vérification
- L'imputation est automatique !

### Contrats
- Créer le contrat dès la signature
- Surveiller les alertes d'échéance
- Renouveler ou résilier à temps
- Créer des BC rattachés au contrat

## ❓ Questions fréquentes

**Q: Comment importer des données Excel ?**  
A: Fonctionnalité à venir

**Q: Puis-je exporter en PDF ?**  
A: Fonctionnalité à venir (reportlab intégré)

**Q: Comment gérer les avenants ?**  
A: Via le contrat, créer un avenant

**Q: Les données sont-elles sauvegardées automatiquement ?**  
A: Oui, à chaque enregistrement dans la base SQLite

**Q: Puis-je travailler hors ligne ?**  
A: Oui, l'application fonctionne entièrement en local

## 🆘 Support

En cas de problème :
1. Consulter les logs : `data/app.log`
2. Vérifier la base de données : `data/budget_manager.db`
3. Signaler un bug sur GitHub avec les logs

---

**Bon usage de Budget Manager Pro !**
