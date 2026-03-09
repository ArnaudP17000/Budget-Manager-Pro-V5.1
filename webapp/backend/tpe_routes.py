"""
tpe_routes.py — Blueprint plugin TPE (Terminaux de Paiement Electronique)
Desinstallation : supprimer ce fichier + tpe_service.py + bloc # TPE MODULE dans server.py
                  + retirer app.register_blueprint(tpe_routes,...) dans server.py
"""
import hashlib, logging, os
from functools import wraps
from flask import Blueprint, g, jsonify, request, send_file
import jwt as _jwt
import io

logger = logging.getLogger(__name__)
tpe_routes = Blueprint("tpe", __name__)


# ── Auth standalone (meme logique que routes.py) ──────────────────────────────
def _secret():
    s = os.getenv("SECRET_KEY")
    if s:
        return s
    b = "bmp-" + os.getenv("DB_HOST","") + "-" + os.getenv("DB_NAME","") + "-" + os.getenv("DB_PASS","")
    return hashlib.sha256(b.encode()).hexdigest()


def require_auth(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not token:
                return jsonify({"error": "Non authentifie"}), 401
            try:
                payload = _jwt.decode(token, _secret(), algorithms=["HS256"])
                payload['sub'] = int(payload['sub'])
            except _jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expire"}), 401
            except _jwt.InvalidTokenError:
                return jsonify({"error": "Token invalide"}), 401
            from app.services.database_service import DatabaseService
            u = DatabaseService().fetch_one(
                "SELECT actif FROM utilisateurs WHERE id=%s", [payload.get("sub")]
            )
            if not u or not u.get("actif"):
                return jsonify({"error": "Compte desactive"}), 401
            g.user = payload
            if roles and payload.get("role") not in roles:
                return jsonify({"error": "Droits insuffisants"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _err(msg, code=400):
    return jsonify({"success": False, "error": str(msg)}), code


def _ok(**data):
    return jsonify({"success": True, **data})


def _module_enabled():
    try:
        from app.services.database_service import DatabaseService
        row = DatabaseService().fetch_one(
            "SELECT enabled FROM modules_config WHERE module_name=%s", ["tpe"]
        )
        return bool(row and row.get("enabled"))
    except Exception:
        return False


# ── Routes ─────────────────────────────────────────────────────────────────────

@tpe_routes.route("/tpe", methods=["GET"])
@require_auth()
def get_tpe_list():
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    from app.services.tpe_service import TpeService
    svc = TpeService()
    search = request.args.get("q")
    return jsonify({"list": svc.get_all(search), "stats": svc.stats()})


@tpe_routes.route("/tpe/stats", methods=["GET"])
@require_auth()
def get_tpe_stats():
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    from app.services.tpe_service import TpeService
    return jsonify(TpeService().stats())


@tpe_routes.route("/tpe/export", methods=["GET"])
@require_auth()
def export_tpe_excel():
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    from app.services.tpe_service import TpeService
    xlsx = TpeService().export_excel()
    return send_file(
        io.BytesIO(xlsx),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="tpe_export.xlsx"
    )


@tpe_routes.route("/tpe", methods=["POST"])
@require_auth("admin", "gestionnaire")
def create_tpe():
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    data = request.json or {}
    if not data.get("service"):
        return _err("Le service est obligatoire")
    try:
        from app.services.tpe_service import TpeService
        tpe_id = TpeService().create(data, created_by_id=g.user.get("sub"))
        return _ok(id=tpe_id), 201
    except Exception as e:
        return _err(e)


@tpe_routes.route("/tpe/<int:tpe_id>", methods=["GET"])
@require_auth()
def get_tpe(tpe_id):
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    from app.services.tpe_service import TpeService
    row = TpeService().get_by_id(tpe_id)
    if not row:
        return jsonify({"error": "TPE introuvable"}), 404
    return jsonify(row)


@tpe_routes.route("/tpe/<int:tpe_id>", methods=["PUT"])
@require_auth("admin", "gestionnaire")
def update_tpe(tpe_id):
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    data = request.json or {}
    if not data.get("service"):
        return _err("Le service est obligatoire")
    try:
        from app.services.tpe_service import TpeService
        TpeService().update(tpe_id, data)
        return _ok()
    except Exception as e:
        return _err(e)


@tpe_routes.route("/tpe/<int:tpe_id>", methods=["DELETE"])
@require_auth("admin", "gestionnaire")
def delete_tpe(tpe_id):
    if not _module_enabled():
        return jsonify({"error": "Module TPE non active"}), 404
    try:
        from app.services.tpe_service import TpeService
        TpeService().delete(tpe_id)
        return _ok()
    except Exception as e:
        return _err(e)
