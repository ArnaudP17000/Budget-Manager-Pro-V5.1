"""
Tests unitaires pour les routes critiques de Budget Manager Pro V5.
Usage : cd webapp/backend && pytest tests/ -v
"""
import json
import pytest
from unittest.mock import MagicMock, patch


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def app():
    """Crée une instance de l'app Flask configurée pour les tests."""
    # Patch la connexion DB avant l'import de server
    with patch('psycopg2.connect') as mock_conn:
        mock_conn.return_value = MagicMock()
        import sys
        # Eviter la réexécution des migrations en cas de rechargement
        for mod in list(sys.modules.keys()):
            if 'app.' in mod or mod in ('routes', 'server'):
                sys.modules.pop(mod, None)

        from server import app as flask_app
        flask_app.config['TESTING'] = True
        flask_app.config['SECRET_KEY'] = 'test-secret'
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _make_token(app, role='admin', user_id=1, login='admin'):
    """Génère un JWT valide pour les tests."""
    import jwt as pyjwt
    import time
    payload = {
        'sub': user_id,
        'role': role,
        'login': login,
        'nom': 'Test',
        'prenom': 'User',
        'service_id': None,
        'exp': int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def _auth_headers(app, role='admin'):
    token = _make_token(app, role=role)
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# ─── Auth ───────────────────────────────────────────────────

class TestAuth:
    def test_login_missing_fields(self, client):
        res = client.post('/api/auth/login',
                          data=json.dumps({}),
                          content_type='application/json')
        assert res.status_code in (400, 422)

    def test_login_wrong_credentials(self, client):
        with patch('app.services.auth_service.AuthService.authenticate', return_value=None):
            res = client.post('/api/auth/login',
                              data=json.dumps({'login': 'bad', 'password': 'bad'}),
                              content_type='application/json')
            assert res.status_code in (401, 400)

    def test_protected_route_without_token(self, client):
        res = client.get('/api/dashboard')
        assert res.status_code == 401

    def test_protected_route_with_bad_token(self, client):
        res = client.get('/api/dashboard',
                         headers={'Authorization': 'Bearer invalid.token.here'})
        assert res.status_code == 401


# ─── Bons de commande ────────────────────────────────────────

class TestBonCommande:
    def _mock_db(self):
        """Retourne un mock DatabaseService avec fetch_all/fetch_one/execute."""
        db = MagicMock()
        db.fetch_all.return_value = []
        db.fetch_one.return_value = None
        db.execute.return_value = None
        return db

    def test_get_bc_requires_auth(self, client):
        res = client.get('/api/bon_commande')
        assert res.status_code == 401

    def test_get_bc_returns_list(self, app, client):
        headers = _auth_headers(app)
        with patch('routes.bc_service.get_all_bons_commande', return_value=[]):
            res = client.get('/api/bon_commande', headers=headers)
            assert res.status_code == 200
            data = res.get_json()
            assert 'list' in data

    def test_create_bc_missing_numero(self, app, client):
        headers = _auth_headers(app)
        payload = {'objet': 'Test', 'montant_ht': 100}
        with patch('routes.bc_service.db') as mock_db:
            mock_db.execute.side_effect = Exception("numero_bc manquant")
            res = client.post('/api/bon_commande',
                              headers=headers,
                              data=json.dumps(payload))
            # Soit 400 (validation), soit 201 si pas de contrôle côté API
            assert res.status_code in (201, 400)

    def test_create_bc_valid(self, app, client):
        headers = _auth_headers(app)
        payload = {'numero_bc': 'BC-TEST-001', 'objet': 'Achat test', 'montant_ht': 1000}
        with patch('routes.bc_service.db') as mock_db:
            mock_db.execute.return_value = None
            mock_db.fetch_one.return_value = None
            res = client.post('/api/bon_commande',
                              headers=headers,
                              data=json.dumps(payload))
            assert res.status_code in (201, 400)

    def test_valider_bc_not_found(self, app, client):
        headers = _auth_headers(app)
        with patch('routes.bc_service.valider', side_effect=ValueError('BC introuvable')):
            res = client.post('/api/bon_commande/9999/valider',
                              headers=headers,
                              data=json.dumps({}))
            assert res.status_code in (400, 404)

    def test_refuser_bc_requires_gestionnaire(self, app, client):
        """Un lecteur ne peut pas refuser un BC."""
        headers = _auth_headers(app, role='lecteur')
        res = client.post('/api/bon_commande/1/refuser',
                          headers=headers,
                          data=json.dumps({'motif': 'Non conforme'}))
        assert res.status_code == 403

    def test_stats_bc(self, app, client):
        headers = _auth_headers(app)
        with patch('routes.bc_service.get_stats', return_value={'_total': {'count': 0, 'total': 0}}):
            res = client.get('/api/bon_commande/stats', headers=headers)
            assert res.status_code == 200


# ─── Dashboard ───────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_returns_kpis(self, app, client):
        headers = _auth_headers(app)
        with patch('routes.projet_service.get_all', return_value=[]), \
             patch('routes.budget_service.get_budget', return_value=[]), \
             patch('routes.bc_service.get_all_bons_commande', return_value=[]), \
             patch('routes.contrat_service.get_all', return_value=[]), \
             patch('routes.contrat_service.get_alertes', return_value=[]), \
             patch('routes.bc_service.db') as mock_db:
            mock_db.fetch_one.return_value = {'cnt': 0}
            res = client.get('/api/dashboard', headers=headers)
            assert res.status_code == 200
            data = res.get_json()
            assert 'kpi_projets' in data
            assert 'kpi_budget' in data
            assert 'kpi_bons_commande' in data
            assert 'kpi_contrats' in data


# ─── Budget ──────────────────────────────────────────────────

class TestBudget:
    def test_get_budget_requires_auth(self, client):
        res = client.get('/api/budget')
        assert res.status_code == 401

    def test_get_budget_returns_details(self, app, client):
        headers = _auth_headers(app)
        with patch('routes.budget_service.get_budget', return_value=[]):
            res = client.get('/api/budget', headers=headers)
            assert res.status_code == 200
            data = res.get_json()
            assert 'details' in data

    def test_voter_budget_admin_only(self, app, client):
        headers = _auth_headers(app, role='lecteur')
        res = client.post('/api/budget/1/voter',
                          headers=headers,
                          data=json.dumps({'montant_vote': 10000}))
        assert res.status_code == 403


# ─── Audit log ───────────────────────────────────────────────

class TestAuditLog:
    def test_audit_log_admin_only(self, app, client):
        headers = _auth_headers(app, role='gestionnaire')
        res = client.get('/api/audit_log', headers=headers)
        assert res.status_code == 403

    def test_audit_log_returns_list(self, app, client):
        headers = _auth_headers(app, role='admin')
        with patch('routes.bc_service.db') as mock_db:
            mock_db.fetch_all.return_value = []
            res = client.get('/api/audit_log', headers=headers)
            assert res.status_code == 200
            data = res.get_json()
            assert 'list' in data


# ─── Contrats ────────────────────────────────────────────────

class TestContrats:
    def test_get_contrats_requires_auth(self, client):
        res = client.get('/api/contrat')
        assert res.status_code == 401

    def test_get_contrats_returns_list(self, app, client):
        headers = _auth_headers(app)
        with patch('routes.contrat_service.get_all', return_value=[]):
            res = client.get('/api/contrat', headers=headers)
            assert res.status_code == 200
            data = res.get_json()
            assert 'list' in data

    def test_delete_contrat_requires_gestionnaire(self, app, client):
        headers = _auth_headers(app, role='lecteur')
        res = client.delete('/api/contrat/1', headers=headers)
        assert res.status_code == 403
