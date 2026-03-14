# Budget Manager Pro V5 — Documentation de déploiement

> Version applicative : 6.44 — Dernière mise à jour : 2026-03-14

---

## Table des matières

1. [Architecture de l'application](#1-architecture-de-lapplication)
2. [Prérequis serveur](#2-prérequis-serveur)
3. [Structure des fichiers](#3-structure-des-fichiers)
4. [Variables d'environnement](#4-variables-denvironnement)
5. [Déploiement depuis zéro](#5-déploiement-depuis-zéro)
6. [Migration depuis l'environnement existant](#6-migration-depuis-lenvironnement-existant)
7. [Restauration de la base de données](#7-restauration-de-la-base-de-données)
8. [Proxy inverse (Nginx Proxy Manager)](#8-proxy-inverse-nginx-proxy-manager)
9. [Mises à jour et redéploiement](#9-mises-à-jour-et-redéploiement)
10. [Comptes et rôles](#10-comptes-et-rôles)
11. [Vérification post-déploiement](#11-vérification-post-déploiement)
12. [Problèmes courants](#12-problèmes-courants)

---

## 1. Architecture de l'application

```
┌─────────────────────────────────────────────────────────┐
│  Internet / LAN                                         │
│           │                                             │
│    Nginx Proxy Manager (réseau npm_net)                 │
│           │  reverse proxy → port 5000                  │
│           │                                             │
│  ┌────────▼──────────┐       ┌──────────────────────┐  │
│  │  Docker container  │       │  PostgreSQL           │  │
│  │  bmp_backend       │──────►  (externe ou local)   │  │
│  │  Python 3.13       │       │  base: budget_manager │  │
│  │  Flask + Gunicorn  │       └──────────────────────┘  │
│  │  port 5000         │                                  │
│  │  /app  → backend   │                                  │
│  │  /frontend → HTML  │                                  │
│  └────────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

**Stack technique :**
| Composant | Technologie |
|-----------|-------------|
| Backend   | Python 3.13 · Flask · Gunicorn (4 workers) |
| Base de données | PostgreSQL 14+ |
| Authentification | JWT (PyJWT 2.8) · bcrypt |
| Frontend  | HTML/CSS/JavaScript vanilla (fichiers statiques servis par Flask) |
| Conteneurisation | Docker · Docker Compose |
| Proxy inverse | Nginx Proxy Manager (optionnel mais recommandé) |

---

## 2. Prérequis serveur

### Système minimal
- Linux (Ubuntu 22.04 LTS recommandé) ou équivalent
- 2 Go RAM minimum, 4 Go recommandés
- 10 Go disque libre

### Logiciels à installer

```bash
# Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose (plugin v2)
sudo apt-get install -y docker-compose-plugin

# Git
sudo apt-get install -y git

# Client PostgreSQL (pour les dumps/restaurations)
sudo apt-get install -y postgresql-client
```

### PostgreSQL
PostgreSQL peut être :
- **Externe** : un serveur PostgreSQL dédié (recommandé en production)
- **Local sur le même hôte** : installé directement sur le serveur Docker

```bash
# Installation locale (si pas de serveur PostgreSQL dédié)
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

## 3. Structure des fichiers

```
Budget-Manager-Pro-V5/
└── webapp/                          ← racine du projet déployé
    ├── docker-compose.yml
    ├── .env                         ← variables d'environnement (NON versionné)
    ├── .env.example                 ← modèle
    ├── backend/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── server.py                ← point d'entrée Flask + migrations DB
    │   ├── routes.py                ← toutes les routes API (~1500 lignes)
    │   ├── tpe_routes.py            ← module TPE (optionnel)
    │   ├── data/
    │   │   └── tpe_import.json      ← données initiales TPE (optionnel)
    │   └── app/
    │       └── services/
    │           ├── database_service.py
    │           ├── auth_service.py
    │           ├── budget_v5_service.py
    │           ├── tpe_service.py
    │           ├── fiche_projet_html_service.py
    │           └── fiche_projet_web_service.py
    └── frontend/
        ├── index.html
        └── app.js
```

---

## 4. Variables d'environnement

Créer le fichier `webapp/.env` (jamais commité dans Git) :

```env
# Connexion PostgreSQL
DB_HOST=127.0.0.1          # ou l'IP/hostname du serveur PostgreSQL
DB_PORT=5432
DB_NAME=budget_manager
DB_USER=bmp_user
DB_PASS=MOT_DE_PASSE_FORT

# Sécurité JWT — OBLIGATOIRE en production, chaîne aléatoire longue
SECRET_KEY=changez-cette-cle-par-une-valeur-aleatoire-longue-et-secrete

# Durée de session (heures)
JWT_EXPIRY_HOURS=8
```

> **Important :** Si `SECRET_KEY` n'est pas défini, l'application en dérive un depuis les credentials DB (non recommandé). Toujours définir une `SECRET_KEY` explicite en production.

---

## 5. Déploiement depuis zéro

### 5.1. Préparer la base de données

```bash
# Se connecter à PostgreSQL en tant que superuser
sudo -u postgres psql

-- Créer l'utilisateur et la base
CREATE USER bmp_user WITH PASSWORD 'MOT_DE_PASSE_FORT';
CREATE DATABASE budget_manager OWNER bmp_user;
GRANT ALL PRIVILEGES ON DATABASE budget_manager TO bmp_user;
\q
```

> **Note :** L'application crée automatiquement toutes les tables au premier démarrage via `run_migrations()` dans `server.py`. Il n'y a pas de fichier SQL d'initialisation à exécuter manuellement.

### 5.2. Cloner le dépôt

```bash
# Sur le serveur de destination
cd /opt
git clone https://github.com/ArnaudP17000/webapp budget
cd /opt/budget
```

### 5.3. Créer le fichier .env

```bash
cp webapp/.env.example webapp/.env
nano webapp/.env
# Remplir les valeurs réelles (DB_HOST, DB_PASS, SECRET_KEY)
```

### 5.4. Configurer le réseau Docker

Si vous utilisez **Nginx Proxy Manager** (NPM), le `docker-compose.yml` se connecte au réseau externe `ngxmanager_default`. Si NPM est déjà installé, ce réseau existe. Sinon :

```bash
# Option A : NPM déjà présent → rien à faire, le réseau existe

# Option B : Pas de NPM, exposer directement le port
# Modifier webapp/docker-compose.yml et retirer la section "npm_net"
# L'application sera accessible sur http://IP_SERVEUR:5000
```

### 5.5. Construire et lancer

```bash
cd /opt/budget/webapp
docker compose build --no-cache
docker compose up -d

# Vérifier que le conteneur tourne
docker compose ps
docker compose logs -f backend
```

Le premier démarrage peut prendre 1-2 minutes (installation des dépendances Python, création des tables).

### 5.6. Vérifier le démarrage

```bash
# L'API doit répondre
curl http://localhost:5000/api/health
# Réponse attendue : {"status":"ok"}

# Voir les logs de migrations
docker compose logs backend | grep -i migration
```

---

## 6. Migration depuis l'environnement existant

### Étape 1 — Exporter les données (sur l'ancien serveur)

```bash
# Sur l'ancien serveur, en tant qu'utilisateur pouvant accéder à PostgreSQL
# Remplacer les valeurs entre <> par les vraies valeurs

pg_dump \
  -h postgre.addict-gamers.fr \
  -U admin \
  -d budget_manager \
  --no-owner \
  --no-privileges \
  -F c \
  -f /tmp/bmp_backup_$(date +%Y%m%d_%H%M).dump

# Vérifier la taille du dump
ls -lh /tmp/bmp_backup_*.dump
```

Si vous n'avez pas accès SSH au serveur PostgreSQL mais que le conteneur tourne :

```bash
# Via le conteneur Docker existant
docker exec bmp_backend pg_dump \
  -h $DB_HOST -U $DB_USER -d $DB_NAME \
  --no-owner --no-privileges -F c \
  -f /tmp/backup.dump

docker cp bmp_backend:/tmp/backup.dump /tmp/bmp_backup_$(date +%Y%m%d).dump
```

### Étape 2 — Transférer le dump

```bash
# De l'ancien serveur vers le nouveau
scp /tmp/bmp_backup_*.dump user@NOUVEAU_SERVEUR:/tmp/

# Ou via un poste local intermédiaire
scp user@ANCIEN_SERVEUR:/tmp/bmp_backup_*.dump .
scp bmp_backup_*.dump user@NOUVEAU_SERVEUR:/tmp/
```

### Étape 3 — Restaurer sur le nouveau serveur

Voir section 7 ci-dessous.

---

## 7. Restauration de la base de données

### 7.1. Dump complet avec pg_dump (recommandé)

```bash
# Sur le nouveau serveur, après avoir créé la base (section 5.1)

pg_restore \
  -h 127.0.0.1 \
  -U bmp_user \
  -d budget_manager \
  --no-owner \
  --no-privileges \
  -v \
  /tmp/bmp_backup_YYYYMMDD.dump
```

En cas d'erreur "role does not exist", c'est normal avec `--no-owner` — les objets seront assignés à `bmp_user`.

### 7.2. Alternative : dump SQL texte

```bash
# Export en format SQL texte (plus portable)
pg_dump \
  -h postgre.addict-gamers.fr \
  -U admin \
  -d budget_manager \
  --no-owner \
  --no-privileges \
  -f /tmp/bmp_backup.sql

# Restauration
psql -h 127.0.0.1 -U bmp_user -d budget_manager -f /tmp/bmp_backup.sql
```

### 7.3. Vérification post-restauration

```bash
psql -h 127.0.0.1 -U bmp_user -d budget_manager -c "\dt"
# Doit lister toutes les tables :
# audit_log, budget_permissions, budgets_annuels, bons_commande,
# contacts, contrats, entites, fournisseur_contacts, fournisseurs,
# jalons, journal_projet, lignes_budgetaires, modules_config,
# notes, notifications, projet_contacts, projet_equipe, projets,
# services, sso_config, taches, tpe, tpe_cartes, utilisateurs
```

### 7.4. Resynchroniser les séquences (important après restauration)

Après une restauration, les séquences auto-increment peuvent être décalées. L'application le fait automatiquement au démarrage (`run_migrations()`), mais vous pouvez aussi le faire manuellement :

```bash
psql -h 127.0.0.1 -U bmp_user -d budget_manager << 'EOF'
SELECT setval('projets_id_seq',       GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM projets)));
SELECT setval('services_id_seq',      GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM services)));
SELECT setval('utilisateurs_id_seq',  GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM utilisateurs)));
SELECT setval('contacts_id_seq',      GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM contacts)));
SELECT setval('taches_id_seq',        GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM taches)));
SELECT setval('contrats_id_seq',      GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM contrats)));
SELECT setval('bons_commande_id_seq', GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM bons_commande)));
SELECT setval('fournisseurs_id_seq',  GREATEST(1, (SELECT COALESCE(MAX(id),1) FROM fournisseurs)));
EOF
```

### 7.5. Stratégie de sauvegarde régulière

Mettre en place un cron sur le serveur de production :

```bash
# Editer la crontab
crontab -e

# Sauvegarde quotidienne à 2h du matin, conservation 30 jours
0 2 * * * pg_dump -h 127.0.0.1 -U bmp_user -d budget_manager --no-owner -F c -f /opt/backups/bmp_$(date +\%Y\%m\%d).dump && find /opt/backups -name "bmp_*.dump" -mtime +30 -delete

# Créer le dossier de sauvegardes
mkdir -p /opt/backups
```

---

## 8. Proxy inverse (Nginx Proxy Manager)

### Si NPM est déjà installé sur le serveur

1. Ouvrir l'interface NPM (port 81 par défaut)
2. **Proxy Hosts → Add Proxy Host**
   - Domain Name : `budget.votre-domaine.fr`
   - Scheme : `http`
   - Forward Hostname : `bmp_backend` (nom du conteneur Docker)
   - Forward Port : `5000`
   - Activer SSL avec Let's Encrypt

### Si vous n'utilisez pas NPM

Modifier `webapp/docker-compose.yml` pour retirer la dépendance au réseau externe :

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: bmp_backend
    restart: always
    ports:
      - "5000:5000"
    env_file:
      - .env

networks: {}
```

Puis configurer votre propre Nginx ou Caddy en reverse proxy vers `localhost:5000`.

---

## 9. Mises à jour et redéploiement

### Workflow de déploiement depuis le poste de développement

Le code source est dans `c:\testweb\Budget-Manager-Pro-V5\` (Windows).
Le sous-dossier `webapp/` est pushé comme racine du repo GitHub.

```bash
# Sur le poste de développement (Windows / Git Bash)
cd c:\testweb\Budget-Manager-Pro-V5

# Push le dossier webapp/ comme racine du repo GitHub
git push webapp $(git subtree split --prefix=webapp master):master --force
```

### Redéploiement sur le serveur

```bash
# Sur le serveur de production
cd /opt/budget
git pull
docker compose up -d --build
```

> Les migrations `run_migrations()` s'exécutent à chaque démarrage — elles sont idempotentes (les colonnes/tables existantes ne sont pas recréées).

---

## 10. Comptes et rôles

### Compte admin par défaut

Créé automatiquement au premier démarrage **si aucun compte `admin` n'existe** :

| Champ | Valeur |
|-------|--------|
| Login | `admin` |
| Mot de passe | `Admin1234!` |

**Changer ce mot de passe immédiatement** après le premier accès via Paramètres → Gestion utilisateurs.

### Rôles disponibles

| Rôle | Droits |
|------|--------|
| `admin` | Accès complet à tous les modules, toutes les données, gestion utilisateurs |
| `gestionnaire` | Gestion de ses propres données + données de son service |
| `gestionnaire_service` | Vue agrégée du service (lecture seule sur budget/projets), pas de modification |
| `lecteur` | Lecture seule, accès uniquement aux budgets qui lui sont attribués explicitement |

### Modules par rôle (défaut)

| Module | admin | gestionnaire | gestionnaire_service | lecteur |
|--------|:-----:|:------------:|:--------------------:|:-------:|
| Budget | ✓ | ✓ | ✓ | ✓ |
| Bons de commande | ✓ | ✓ | — | ✓ |
| Contrats | ✓ | ✓ | — | — |
| Projets | ✓ | ✓ | ✓ | ✓ |
| Tâches / Kanban | ✓ | ✓ | — | — |
| Fournisseurs | ✓ | ✓ | — | — |
| Contacts | ✓ | ✓ | ✓ | — |
| Services / ETP | ✓ | — | — | — |
| Gantt | ✓ | ✓ | — | — |
| Notifications | ✓ | ✓ | ✓ | ✓ |
| Notes | ✓ | ✓ | — | ✓ |
| TPE | ✓ | — | — | — |

---

## 11. Vérification post-déploiement

Checklist après un déploiement ou une migration :

```bash
# 1. Conteneur en cours d'exécution
docker compose ps
# → bmp_backend   Up

# 2. API répond
curl http://localhost:5000/api/health
# → {"status":"ok"}

# 3. Page frontend accessible
curl -s http://localhost:5000/ | grep -c "Budget Manager"
# → 1

# 4. Login fonctionne
curl -s -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"Admin1234!"}' | python3 -m json.tool
# → {"token":"...","user":{...}}

# 5. Tables présentes dans la DB
psql -h 127.0.0.1 -U bmp_user -d budget_manager -c "SELECT count(*) FROM utilisateurs;"
# → doit retourner un nombre >= 1

# 6. Logs sans erreur critique
docker compose logs --tail=50 backend | grep -i error
# → idéalement vide
```

---

## 12. Problèmes courants

### L'application ne démarre pas

```bash
docker compose logs backend
```

**Cause fréquente :** mauvaises variables dans `.env` (mot de passe DB, host inaccessible).

```bash
# Tester la connexion DB depuis le conteneur
docker exec -it bmp_backend python3 -c "
import psycopg2, os
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'),
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASS')
)
print('Connexion OK')
"
```

### Erreur "duplicate key" lors de la restauration

```bash
# Resynchroniser toutes les séquences (voir section 7.4)
# L'application le fait aussi automatiquement au redémarrage
docker compose restart backend
```

### Les sessions JWT sont invalidées après redéploiement

Si `SECRET_KEY` n'est pas défini dans `.env`, la clé est dérivée des variables DB à chaque démarrage — ce qui peut changer. **Solution :** toujours définir `SECRET_KEY` explicitement dans `.env`.

### Page blanche ou JS non mis à jour (cache navigateur)

Le frontend utilise un cache-buster (`?v=X.XX`) sur les fichiers JS/CSS. Forcer un rechargement avec `Ctrl+Shift+R` ou vider le cache navigateur.

### Le réseau npm_net n'existe pas

```bash
# Si NPM n'est pas installé, retirer la section npm_net du docker-compose.yml
# ou créer le réseau manuellement
docker network create ngxmanager_default
```

### PostgreSQL sur le même hôte Docker (réseau host)

Si PostgreSQL est installé localement sur le serveur Docker, utiliser `DB_HOST=172.17.0.1` (gateway Docker bridge) ou passer en `network_mode: host` dans le `docker-compose.yml` et utiliser `DB_HOST=127.0.0.1`.

---

## Récapitulatif — Migration en 5 commandes

```bash
# 1. Sur l'ANCIEN serveur : exporter la base
pg_dump -h DB_HOST -U DB_USER -d budget_manager --no-owner -F c -f /tmp/bmp.dump

# 2. Transférer le dump
scp /tmp/bmp.dump user@NOUVEAU_SERVEUR:/tmp/

# 3. Sur le NOUVEAU serveur : préparer la base
sudo -u postgres psql -c "CREATE USER bmp_user WITH PASSWORD 'xxxx'; CREATE DATABASE budget_manager OWNER bmp_user;"
pg_restore -h 127.0.0.1 -U bmp_user -d budget_manager --no-owner /tmp/bmp.dump

# 4. Cloner le repo et configurer
git clone https://github.com/ArnaudP17000/webapp /opt/budget
cp /opt/budget/webapp/.env.example /opt/budget/webapp/.env
# Editer .env avec les bonnes valeurs

# 5. Lancer
cd /opt/budget/webapp && docker compose up -d --build
```
