"""
fiche_projet_html_service.py
Génère la fiche projet en HTML — vue + édition inline.
Token JWT et projet_id injectés par le parent (app.js).
"""
import json as _json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

RED   = '#1565C0'
PINK  = '#D6EAF8'
GRAY1 = '#D8D8D8'
GRAY2 = '#BFBFBF'
GRAY4 = '#F2F2F2'


def _e(s):
    if s is None: return ''
    return (str(s).replace('&','&amp;').replace('<','&lt;')
            .replace('>','&gt;').replace('"','&quot;'))

def _fmt_eur(v):
    try: return f"{float(v or 0):,.2f} \u20ac"
    except: return '0,00 \u20ac'

def _fmt_pct(v):
    try: return f"{int(v or 0)} %"
    except: return '0 %'

def _fmt_date(d):
    if not d: return ''
    try: return datetime.fromisoformat(str(d)[:10]).strftime('%d/%m/%Y')
    except: return str(d)[:10]

def _iso_date(d):
    if not d: return ''
    try:
        s = str(d)
        if len(s) >= 10: return s[:10]
        return ''
    except: return ''

def _progress_bar(pct):
    try: v = int(pct or 0)
    except: v = 0
    color = '#27AE60' if v >= 80 else ('#F39C12' if v >= 40 else '#C0392B')
    return (f'<div style="background:#e0e0e0;border-radius:4px;height:16px;width:100%;margin:4px 0">'
            f'<div id="prog-bar" style="width:{v}%;background:{color};height:16px;border-radius:4px;'
            f'display:flex;align-items:center;justify-content:center;color:#fff;font-size:9px;font-weight:bold">'
            f'{v}%</div></div>')


# ─────────────────────────────────────────────────────────────────────────────
# Helpers HTML
# ─────────────────────────────────────────────────────────────────────────────
def _sec(title, colspan=4):
    return f'<tr><td class="sec" colspan="{colspan}">{_e(title)}</td></tr>\n'

def _sub(title, colspan=4, bg=GRAY2):
    return (f'<tr><td style="background:{bg};font-weight:bold;padding:5px 8px;font-size:11px" '
            f'colspan="{colspan}">{_e(title)}</td></tr>\n')

def _hdr(*cols):
    cells = ''.join(f'<th class="hdr">{_e(c)}</th>' for c in cols)
    return f'<tr>{cells}</tr>\n'

def _field(name, label, value, input_type='text', w_lbl='17%', colspan_val=1, opts=None):
    """Cellule label + valeur (view + edit).
    Pour input_type='date', passer la valeur ISO (YYYY-MM-DD) — l'affichage DD/MM/YYYY est calculé automatiquement."""
    sel = ''
    view_val = value or ''
    if opts:
        sel = f'<select class="ef" name="{_e(name)}">'
        for v, l in opts:
            sel_attr = ' selected' if str(value or '') == str(v) else ''
            sel += f'<option value="{_e(v)}"{sel_attr}>{_e(l)}</option>'
        sel += '</select>'
        edit_html = sel
    elif input_type == 'date':
        iso_val = _iso_date(value)   # YYYY-MM-DD pour l'input
        view_val = _fmt_date(iso_val)  # DD/MM/YYYY pour l'affichage
        edit_html = f'<input class="ef" type="date" name="{_e(name)}" value="{_e(iso_val)}">'
    else:
        edit_html = f'<input class="ef" type="{input_type}" name="{_e(name)}" value="{_e(value or "")}">'
    span = f' colspan="{colspan_val}"' if colspan_val > 1 else ''
    return (f'<td class="lbl" style="width:{w_lbl}">{_e(label)}</td>'
            f'<td class="val"{span}>'
            f'<span class="vv">{_e(view_val)}</span>'
            f'{edit_html}</td>\n')

def _field2(n1, l1, v1, n2, l2, v2, t1='text', t2='text', opts1=None, opts2=None):
    return f'<tr>{_field(n1, l1, v1, t1, opts=opts1)}{_field(n2, l2, v2, t2, opts=opts2)}</tr>\n'

def _field_ta(name, value, label=None, colspan=4, min_h=70, rows=4):
    """Cellule textarea (view + edit)."""
    pre = f'<tr><td style="background:{GRAY2};font-weight:bold;padding:4px 8px;font-size:11px" colspan="{colspan}">{_e(label)}</td></tr>\n' if label else ''
    return pre + (
        f'<tr><td colspan="{colspan}" style="padding:0;vertical-align:top">'
        f'<div class="vv" style="background:{PINK};white-space:pre-wrap;padding:6px 8px;min-height:{min_h}px">{_e(value or "")}</div>'
        f'<textarea class="ef" name="{_e(name)}" rows="{rows}" style="width:100%;min-height:{min_h}px">{_e(value or "")}</textarea>'
        f'</td></tr>\n'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Génération HTML principale
# ─────────────────────────────────────────────────────────────────────────────
def generer_fiche_html(data: dict, projet_id: int) -> str:
    p = data
    today = datetime.now().strftime('%d/%m/%Y')
    data_json = _json.dumps(data, default=str, ensure_ascii=False)

    # Options pour les selects
    TYPES = [('','-- Type --'),('INFRASTRUCTURE','Infrastructure'),('APPLICATIF','Applicatif'),
             ('METIER','Métier'),('SECURITE','Sécurité'),('RESEAU','Réseau'),('AUTRE','Autre')]
    PRIORITES = [('','-- Priorité --'),('CRITIQUE','Critique'),('HAUTE','Haute'),
                 ('MOYENNE','Moyenne'),('BASSE','Basse')]
    PHASES = [('','-- Phase --'),('CADRAGE','Cadrage'),('CONCEPTION','Conception'),
              ('REALISATION','Réalisation'),('RECETTE','Recette'),('PRODUCTION','Production'),
              ('CLOTURE','Clôture')]
    STATUTS = [('ACTIF','Actif'),('EN_PAUSE','En pause'),('TERMINE','Terminé'),
               ('ANNULE','Annulé'),('EN_ATTENTE','En attente')]

    # Données JSON complexes
    ctr_data = {}
    if p.get('contraintes_6axes'):
        try: ctr_data = _json.loads(p['contraintes_6axes']) if isinstance(p['contraintes_6axes'], str) else (p['contraintes_6axes'] or {})
        except: pass

    tri_data = {}
    if p.get('triangle_tensions'):
        try: tri_data = _json.loads(p['triangle_tensions']) if isinstance(p['triangle_tensions'], str) else (p['triangle_tensions'] or {})
        except: pass

    risques_list = []
    if p.get('registre_risques'):
        try: risques_list = _json.loads(p['registre_risques']) if isinstance(p['registre_risques'], str) else (p['registre_risques'] or [])
        except: pass

    NIVEAUX = {1:'Faible',2:'Modéré',3:'Modéré',4:'Élevé',5:'Critique'}
    COULEURS_TRI = {1:'#27AE60',2:'#27AE60',3:'#F39C12',4:'#E67E22',5:'#C0392B'}
    AXES_6 = [
        ('portee_desc',       'Portée',     'Périmètre, livrables, fonctionnalités incluses'),
        ('couts_desc',        'Coûts',      'Budget global, salaires, équipements, licences'),
        ('delais_desc',       'Délais',     'Calendrier, jalons, phases, dates clés'),
        ('ressources_desc',   'Ressources', 'Équipes, compétences, équipements, logiciels'),
        ('qualite_desc',      'Qualité',    "Critères d'acceptation, niveaux de service"),
        ('risques_proj_desc', 'Risques',    'Événements imprévus pouvant impacter le projet'),
    ]

    taches = p.get('taches', []) or []
    contacts = p.get('contacts', []) or []
    acteurs = [('Chef de projet DSI', p.get('chef_projet',''), 'DSI', ''),
               ('Responsable métier',  p.get('responsable',''), '', '')]
    for c in contacts:
        acteurs.append((c.get('role',''), c.get('nom',''), c.get('fonction',''), c.get('email','')))
    if not contacts and p.get('equipe'):
        acteurs.append(('Équipe projet', p.get('equipe',''), '', ''))

    css = f"""
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#111;background:#ececec}}
.toolbar{{position:sticky;top:0;z-index:100;background:#1a1a2e;display:flex;align-items:center;
  gap:6px;padding:8px 14px;box-shadow:0 2px 8px rgba(0,0,0,.3)}}
.toolbar span{{flex:1;color:#ccc;font-size:12px;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tbtn{{border:none;border-radius:4px;padding:6px 12px;font-size:11px;font-weight:bold;cursor:pointer;
  display:inline-flex;align-items:center;gap:4px}}
.tbtn-edit{{background:#6f42c1;color:#fff}} .tbtn-save{{background:#198754;color:#fff}}
.tbtn-cancel{{background:#6c757d;color:#fff}} .tbtn-print{{background:#0d6efd;color:#fff}}
.tbtn-word{{background:#146c43;color:#fff}} .tbtn-close{{background:#dc3545;color:#fff}}
.tbtn:hover{{opacity:.87}} .tbtn:active{{opacity:.75}}
.save-status{{color:#6c6;font-size:11px;font-weight:bold;padding:0 6px}}
.page{{max-width:980px;margin:20px auto;background:#fff;padding:22px 26px;
  box-shadow:0 2px 12px rgba(0,0,0,.18);border-radius:4px}}
h1.titre{{background:{RED};color:#fff;text-align:center;padding:13px;font-size:17px;
  letter-spacing:.5px;border-radius:3px 3px 0 0}}
p.soustitre{{background:#0d47a1;color:{PINK};text-align:center;padding:7px;
  font-size:11px;margin-bottom:20px}}
table.fiche{{width:100%;border-collapse:collapse;margin-bottom:18px;border:1px solid #bbb}}
table.fiche td,table.fiche th{{border:1px solid #bbb;padding:5px 8px;font-size:11px;vertical-align:middle}}
.sec{{background:{RED};color:#fff;font-weight:bold;font-size:13px;padding:8px 10px;letter-spacing:.3px}}
.hdr{{background:{RED};color:#fff;text-align:center;font-weight:bold;font-size:10px}}
.lbl{{background:{GRAY1};font-weight:bold}}
.val{{background:{PINK}}} .val-w{{background:#fff}} .val-g{{background:{GRAY4}}}
.ctr{{text-align:center}}
.footer-fiche{{text-align:center;color:#999;font-size:9px;margin-top:22px;
  padding-top:8px;border-top:1px solid #ddd}}

/* View / Edit mode */
.ef{{display:none!important}} .vv{{display:block}}
body.edit-mode .ef{{display:block!important}} body.edit-mode .vv{{display:none}}
body.edit-mode .ef-flex{{display:flex!important;flex-direction:column;gap:3px}}
input.ef,select.ef{{width:100%;border:1px solid #93c;border-radius:3px;padding:3px 5px;
  font-size:11px;background:#fdf4ff;font-family:inherit}}
textarea.ef{{width:100%;border:1px solid #93c;border-radius:3px;padding:4px 6px;
  font-size:11px;background:#fdf4ff;font-family:inherit;resize:vertical}}
input[type=range].ef{{padding:0;background:none;border:none;accent-color:{RED}}}
/* Champs éditables en edit mode conservent la couleur de fond de la cellule */
body.edit-mode .val input.ef,body.edit-mode .val textarea.ef,
body.edit-mode .val select.ef{{background:#fdf4ff}}
body.edit-mode .val-g input.ef{{background:#f5f5f5}}

/* Autocomplete contact */
.contact-ac-wrap{{display:none;position:relative}}
body.edit-mode .contact-ac-wrap{{display:block}}
.ac-input{{width:100%;border:1px solid #93c;border-radius:3px;padding:5px 8px;font-size:11px;
  background:#fdf4ff;font-family:inherit;box-sizing:border-box;outline:none}}
.ac-input:focus{{border-color:#6f42c1;box-shadow:0 0 0 2px rgba(111,66,193,.15)}}
.ac-input.ac-ok{{border-color:#198754;background:#f0fdf4}}
.ac-input.ac-err{{border-color:#dc3545;background:#fff5f5}}
.ac-drop{{position:absolute;top:calc(100% + 2px);left:0;right:0;background:#fff;
  border:1px solid #93c;border-radius:4px;box-shadow:0 4px 14px rgba(0,0,0,.18);
  max-height:200px;overflow-y:auto;z-index:9999;display:none}}
.ac-drop.open{{display:block}}
.ac-item{{padding:6px 9px;cursor:pointer;font-size:11px;border-bottom:1px solid #f0e0ff;line-height:1.5}}
.ac-item:last-child{{border-bottom:none}}
.ac-item:hover,.ac-item.ac-active{{background:#ede0ff}}
.ac-item .ac-sub{{color:#888;font-size:10px;margin-left:5px}}
.ac-empty{{padding:10px;color:#999;font-size:11px;text-align:center;font-style:italic}}

/* Registre risques editor */
#risques-editor table{{width:100%;border-collapse:collapse}}
#risques-editor td,#risques-editor th{{border:1px solid #bbb;padding:3px 5px;font-size:10px}}
#risques-editor th{{background:{RED};color:#fff;text-align:center}}
#risques-editor input,#risques-editor select{{width:100%;font-size:10px;border:1px solid #ccc;
  padding:2px 3px;font-family:inherit}}
.btn-rsk-del{{background:#dc3545;color:#fff;border:none;border-radius:3px;cursor:pointer;
  padding:2px 7px;font-size:10px}}
.btn-rsk-add{{background:{RED};color:#fff;border:none;border-radius:3px;cursor:pointer;
  padding:4px 10px;font-size:11px;margin-top:5px}}

@media print{{
  .toolbar{{display:none!important}}
  body{{background:#fff}}
  .page{{margin:0;padding:12px;box-shadow:none;max-width:100%}}
  tr{{page-break-inside:avoid}}
}}
</style>"""

    # ── Toolbar
    toolbar = f"""
<div class="toolbar">
  <span>Fiche Projet — {_e(p.get('code',''))}</span>
  <button class="tbtn tbtn-edit" id="btn-edit" onclick="startEdit()">&#9998; Modifier</button>
  <button class="tbtn tbtn-save" id="btn-save" style="display:none" onclick="saveFiche()">&#128190; Sauvegarder</button>
  <button class="tbtn tbtn-cancel" id="btn-cancel" style="display:none" onclick="cancelEdit()">&#10005; Annuler</button>
  <span class="save-status" id="save-status"></span>
  <button class="tbtn tbtn-print" onclick="window.print()">&#128424; Imprimer / PDF</button>
  <button class="tbtn tbtn-word" id="btn-word-dl">&#128196; Word</button>
  <button class="tbtn tbtn-close" onclick="window.parent.postMessage('closeFicheViewer','*')">&#10005; Fermer</button>
</div>"""

    h = f'<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="UTF-8">\n'
    h += f'<title>Fiche — {_e(p.get("code",""))}</title>\n{css}\n</head>\n<body>\n'
    h += toolbar
    h += '<div class="page">\n'

    # Bandeau titre
    h += f'<h1 class="titre">FICHE PROJET \u2014 Budget Manager Pro V5</h1>\n'
    h += f'<p class="soustitre" id="bandeau-sub">Date\u00a0: {today}\u00a0\u00a0|\u00a0\u00a0Code\u00a0: {_e(p.get("code",""))}\u00a0\u00a0|\u00a0\u00a0Statut\u00a0: {_e(p.get("statut",""))}</p>\n'

    # ── 1. IDENTIFICATION
    h += '<table class="fiche">\n'
    h += _sec('1. IDENTIFICATION')
    h += _sub('Informations générales')
    h += _field2('code','Code projet',p.get('code',''), 'nom','Intitulé',p.get('nom',''))
    h += _field2('type_projet','Type',p.get('type_projet',''),'priorite','Priorité',p.get('priorite',''),
                 opts1=TYPES, opts2=PRIORITES)
    h += _field2('phase','Phase',p.get('phase',''),'avancement','Avancement (%)',p.get('avancement',0),
                 opts1=PHASES, t2='number')
    pct = p.get('avancement') or 0
    h += f'<tr><td colspan="4" style="padding:5px 8px;background:#fafafa">{_progress_bar(pct)}</td></tr>\n'
    h += _field2('date_debut','Date début',p.get('date_debut',''),
                 'date_fin_prevue','Fin prévue',p.get('date_fin',''),
                 t1='date', t2='date')
    h += (f'<tr>{_field("date_fin_reelle","Fin réelle",p.get("date_fin_reelle",""),"date")}'
          f'<td class="lbl">Service</td><td class="val"><span class="vv">{_e(p.get("service",""))}</span>'
          f'<input class="ef" type="text" name="service_nom" value="{_e(p.get("service",""))}" disabled></td></tr>\n')
    h += _sub('Description détaillée du projet')
    h += _field_ta('description', p.get('description',''), min_h=80, rows=5)
    h += _sub('Note interne')
    h += _field_ta('note', p.get('note',''), min_h=50, rows=3)
    h += _sub('Acteurs du projet')
    h += _hdr('Rôle','Nom Prénom','Fonction / Service','Email / Tél')
    # Contacts : chef et responsable éditables avec recherche
    for row_id, role_lbl, contact_name, contact_id_field in [
        ('row-chef', 'Chef de projet DSI', p.get('chef_projet',''), 'chef_projet_contact_id'),
        ('row-resp', 'Responsable métier',  p.get('responsable',''), 'responsable_contact_id'),
    ]:
        cid = p.get(contact_id_field) or ''
        vv_html = _e(contact_name) if contact_name else "<em style='color:#aaa'>Non défini</em>"
        h += (f'<tr id="{row_id}">'
              f'<td class="lbl">{_e(role_lbl)}</td>'
              f'<td class="val-w" colspan="3">'
              f'<span class="vv">{vv_html}</span>'
              f'<div class="contact-ac-wrap">'
              f'<input class="ac-input" type="text" placeholder="Tapez un nom, prénom ou fonction…" '
              f'data-field="{_e(contact_id_field)}" autocomplete="off" spellcheck="false">'
              f'<input type="hidden" name="{_e(contact_id_field)}" class="ef" value="{_e(str(cid))}">'
              f'<div class="ac-drop"></div>'
              f'</div>'
              f'</td></tr>\n')
    for role, nom, fn, email in acteurs[2:]:
        h += (f'<tr><td class="lbl">{_e(role)}</td>'
              f'<td class="val-w">{_e(nom)}</td>'
              f'<td class="val-w">{_e(fn)}</td>'
              f'<td class="val">{_e(email)}</td></tr>\n')
    h += '</table>\n'

    # ── 2. OPPORTUNITÉ
    h += '<table class="fiche">\n'
    h += _sec('2. OPPORTUNITÉ')
    h += _sub('Objectifs "métier" opérationnels du projet')
    h += _field_ta('objectifs', p.get('objectifs',''), min_h=70, rows=4)
    h += _sub('Principaux risques identifiés à NE PAS faire le projet')
    h += _field_ta('risques', p.get('risques',''), min_h=60, rows=3)
    h += _sub('Gains qualitatifs et bénéfices attendus')
    h += _field_ta('gains', p.get('gains',''), min_h=60, rows=3)
    h += _sub("Enjeux stratégiques de l'établissement")
    h += _field_ta('enjeux', p.get('enjeux',''), min_h=50, rows=3)
    h += '</table>\n'

    # ── 3. BUDGET & FINANCEMENT
    h += '<table class="fiche">\n'
    h += _sec('3. BUDGET & FINANCEMENT')
    h += _sub('Synthèse budgétaire')
    h += _field2('budget_initial','Budget prévisionnel',_fmt_eur(p.get('budget_previsionnel')),
                 'budget_actuel','Budget voté',_fmt_eur(p.get('budget_vote')),
                 t1='number', t2='number')
    h += (f'<tr><td class="lbl">Budget consommé (BC)</td><td class="val">'
          f'<span class="vv">{_e(_fmt_eur(p.get("budget_consomme")))}</span>'
          f'<input class="ef" type="number" name="budget_estime" value="{_e(str(p.get("budget_consomme") or ""))}"></td>'
          f'<td class="lbl">Ligne budgétaire</td><td class="val">{_e(p.get("ligne_budg",""))}</td></tr>\n')
    h += (f'<tr><td class="lbl">Bons de commande liés</td>'
          f'<td class="val" colspan="3" style="white-space:pre-wrap">{_e(p.get("bcs","Aucun BC lié"))}</td></tr>\n')
    h += _sub('Modalités de financement (internes / externes)')
    h += _field_ta('financement', p.get('financement','') or '', min_h=60, rows=3)
    h += '</table>\n'

    # ── 4. PLANNING & TÂCHES
    h += '<table class="fiche">\n'
    h += _sec('4. PLANNING & TÂCHES')
    h += _hdr('Tâche / Livrable','Statut','Échéance','Charge (h)')
    if taches:
        for i, tk in enumerate(taches):
            bg = GRAY4 if i % 2 else '#fff'
            h += (f'<tr style="background:{bg}">'
                  f'<td style="width:55%">{_e(tk.get("titre",""))}</td>'
                  f'<td class="ctr">{_e(tk.get("statut",""))}</td>'
                  f'<td class="val ctr">{_e(tk.get("echeance",""))}</td>'
                  f'<td class="val ctr">{_e(tk.get("heures",""))}</td></tr>\n')
    else:
        h += '<tr><td colspan="4" style="text-align:center;color:#888;padding:16px">Aucune tâche enregistrée</td></tr>\n'
    h += (f'<tr><td colspan="4" class="vv" style="background:#fafafa;padding:4px 8px;font-size:10px;color:#888">'
          f'Les tâches se gèrent via l\'onglet Tâches du projet.</td></tr>\n')
    h += '</table>\n'

    # ── 5. ÉQUIPE & CONTACTS
    h += '<table class="fiche">\n'
    h += _sec('5. ÉQUIPE & CONTACTS')
    h += _hdr('Rôle','Nom Prénom','Fonction / Service','Email / Tél')
    for role, nom, fn, email in acteurs:
        h += (f'<tr><td class="lbl">{_e(role)}</td>'
              f'<td class="val-w">{_e(nom)}</td>'
              f'<td class="val-w">{_e(fn)}</td>'
              f'<td class="val">{_e(email)}</td></tr>\n')
    h += (f'<tr><td colspan="4" class="vv" style="background:#fafafa;padding:4px 8px;font-size:10px;color:#888">'
          f'L\'équipe et les contacts se gèrent via les onglets dédiés du projet.</td></tr>\n')
    h += '</table>\n'

    # ── 6. SOLUTIONS & CONTRAINTES
    h += '<table class="fiche">\n'
    h += _sec('6. SOLUTIONS & CONTRAINTES')
    h += _sub('Ressources MOE disponibles — Solutions envisagées')
    h += _field_ta('solutions', p.get('solutions',''), min_h=70, rows=4)
    h += _sub('Contraintes techniques / réglementaires / RGPD')
    h += _field_ta('contraintes', p.get('contraintes',''), min_h=70, rows=4)
    h += '</table>\n'

    # ── 6b. LES 6 CONTRAINTES PROJET
    h += '<table class="fiche">\n'
    h += _sec('6b. LES 6 CONTRAINTES PROJET')
    h += _sub("Les 6 contraintes sont interconnectées — modifier l'une impacte les autres.")
    for i in range(0, len(AXES_6), 2):
        h += '<tr>\n'
        for j in range(2):
            if i + j < len(AXES_6):
                attr, label, hint = AXES_6[i + j]
                val = ctr_data.get(attr, '') or ''
                bg = PINK if val else GRAY4
                h += (f'<td colspan="2" style="background:{bg};padding:8px;vertical-align:top;width:50%">'
                      f'<strong class="vv">{_e(label)}</strong>'
                      f'<div class="vv" style="white-space:pre-wrap;margin-top:2px">'
                      f'{_e(val) if val else f"<em style=\'color:#888\'>{_e(hint)}</em>"}</div>'
                      f'<strong class="ef" style="display:block;font-size:10px;margin-bottom:3px">{_e(label)}</strong>'
                      f'<textarea class="ef" name="{_e(attr)}" rows="3" placeholder="{_e(hint)}">{_e(val)}</textarea>'
                      f'</td>\n')
            else:
                h += f'<td colspan="2" style="background:{GRAY4}"></td>\n'
        h += '</tr>\n'
    h += '</table>\n'

    # ── 6c. TRIANGLE D'OR
    axes_tri = [
        ('tension_portee', 'Portée',  'Risque de dérive du périmètre (scope creep)'),
        ('tension_couts',  'Coûts',   'Pression sur le budget disponible'),
        ('tension_delais', 'Délais',  'Pression sur le calendrier'),
    ]
    total_tri = sum(int(tri_data.get(a, 3)) for a, _, _ in axes_tri)
    if total_tri >= 13:   alerte, fill_tri = 'ALERTE : Triangle très tendu \u2014 arbitrage urgent !', '#C0392B'
    elif total_tri >= 10: alerte, fill_tri = 'Attention : tensions élevées sur certains axes.', '#E67E22'
    else:                 alerte, fill_tri = 'Triangle équilibré \u2014 axes sous contrôle.', '#27AE60'

    h += '<table class="fiche">\n'
    h += _sec("6c. TRIANGLE D'OR \u2014 PORTÉE / COÛTS / DÉLAIS")
    h += _sub('Niveau de tension sur chaque axe (1 = sous contrôle, 5 = très tendu)')
    h += _hdr('Axe','Tension (1-5)','Niveau','Interprétation')

    for attr, label, desc in axes_tri:
        v = int(tri_data.get(attr, 3))
        col = COULEURS_TRI.get(v, '#F39C12')
        niv = NIVEAUX.get(v, 'Modéré')
        bars = '\u2588' * v + '\u2591' * (5 - v)
        h += (f'<tr>'
              f'<td class="lbl">{_e(label)}</td>'
              f'<td style="background:{col};color:#fff;font-weight:bold;text-align:center" id="tri-cell-{attr}">'
              f'<span class="vv">{v}/5 {bars}</span>'
              f'<div class="ef" style="display:flex;align-items:center;gap:6px;padding:2px">'
              f'<input type="range" class="ef" name="{_e(attr)}" min="1" max="5" value="{v}" '
              f'oninput="updateTriSlider(this)">'
              f'<span id="tri-lbl-{attr}" style="white-space:nowrap;min-width:30px">{v}/5</span></div>'
              f'</td>'
              f'<td class="val ctr" id="tri-niv-{attr}"><span class="vv">{_e(niv)}</span>'
              f'<span class="ef">{_e(niv)}</span></td>'
              f'<td>{_e(desc)}</td></tr>\n')

    h += (f'<tr id="tri-alerte"><td colspan="4" style="background:{fill_tri};color:#fff;'
          f'font-weight:bold;padding:7px 8px">{_e(alerte)}</td></tr>\n')
    h += _sub("Stratégie d'arbitrage")
    h += _field_ta('arbitrage', p.get('arbitrage',''), min_h=50, rows=3)
    h += '</table>\n'

    # ── 6d. REGISTRE DES RISQUES
    risques_sorted = sorted(risques_list, key=lambda x: int(x.get('criticite',0)), reverse=True)
    CRIT_COLORS = {range(12,26):'#C0392B', range(6,12):'#E67E22', range(3,6):'#F1C40F', range(0,3):'#27AE60'}
    def _crit_color(c):
        c = int(c or 0)
        if c >= 12: return '#C0392B'
        if c >= 6:  return '#E67E22'
        if c >= 3:  return '#F1C40F'
        return '#27AE60'

    h += '<table class="fiche">\n'
    h += _sec('6d. REGISTRE DES RISQUES', colspan=7)
    h += _hdr('Description','Catégorie','Proba','Impact','Crit.','Action corrective','Statut')

    if risques_sorted:
        for i, rsk in enumerate(risques_sorted):
            crit = int(rsk.get('criticite',0))
            fc_r = _crit_color(crit)
            bg = GRAY4 if i % 2 else '#fff'
            h += (f'<tr style="background:{bg}" class="vv">'
                  f'<td style="width:28%">{_e(rsk.get("description",""))}</td>'
                  f'<td>{_e(rsk.get("categorie",""))}</td>'
                  f'<td class="ctr">{_e(str(rsk.get("probabilite","") or ""))}</td>'
                  f'<td class="ctr">{_e(str(rsk.get("impact","") or ""))}</td>'
                  f'<td class="ctr" style="background:{fc_r};color:#fff;font-weight:bold">{crit}</td>'
                  f'<td>{_e(rsk.get("action",""))}</td>'
                  f'<td class="val ctr">{_e(rsk.get("statut",""))}</td></tr>\n')
        nb_crit  = sum(1 for r in risques_sorted if int(r.get('criticite',0)) >= 12)
        nb_eleve = sum(1 for r in risques_sorted if 6 <= int(r.get('criticite',0)) < 12)
        fill_s = '#C0392B' if nb_crit else ('#E67E22' if nb_eleve else '#27AE60')
        synthese = f"Total\u00a0: {len(risques_sorted)} | Critiques\u00a0: {nb_crit} | Élevés\u00a0: {nb_eleve}"
        h += (f'<tr class="vv"><td colspan="7" style="background:{fill_s};color:#fff;'
              f'font-weight:bold;padding:5px 8px">{_e(synthese)}</td></tr>\n')
    else:
        h += '<tr class="vv"><td colspan="7" style="text-align:center;color:#888;padding:16px">Aucun risque enregistré.</td></tr>\n'

    # Éditeur registre risques (edit mode)
    h += f'''<tr class="ef"><td colspan="7" style="padding:8px;background:#fff">
  <div id="risques-editor">
    <table id="risques-table">
      <thead><tr>
        <th style="width:26%">Description</th><th>Catégorie</th>
        <th style="width:5%">Proba</th><th style="width:5%">Impact</th>
        <th style="width:5%">Crit.</th><th style="width:22%">Action corrective</th>
        <th>Statut</th><th style="width:3%"></th>
      </tr></thead>
      <tbody id="risques-tbody"></tbody>
    </table>
    <button class="btn-rsk-add" onclick="addRisqueRow()">+ Ajouter un risque</button>
  </div>
</td></tr>\n'''
    h += '</table>\n'

    # ── 7. VALIDATION & SIGNATURES
    h += '<table class="fiche">\n'
    h += _sec('7. VALIDATION & SIGNATURES')
    h += _hdr('Valideur','Nom / Prénom','Date','Visa')
    for role in ['Chef de projet','Responsable DSI','Direction']:
        h += (f'<tr><td class="lbl">{_e(role)}</td>'
              f'<td class="val" style="min-height:40px;height:40px"></td>'
              f'<td class="val"></td><td class="val-w"></td></tr>\n')
    h += '</table>\n'

    h += (f'<p class="footer-fiche">Budget Manager Pro V5 \u2014 '
          f'Fiche projet {_e(p.get("code",""))} \u2014 Générée le {today}</p>\n')
    h += '</div>\n'  # .page

    # ── JavaScript
    h += f'''<script>
const TOKEN = '__BMP_TOKEN__';
const PROJET_ID = __PROJET_ID__;
const _DATA_ORIG = {data_json};
let _risques = {_json.dumps(risques_list, ensure_ascii=False)};
let _editActive = false;

const NIVEAUX_TRI = {{1:'Faible',2:'Modéré bas',3:'Modéré',4:'Élevé',5:'Critique'}};
const COLORS_TRI  = {{1:'#27AE60',2:'#27AE60',3:'#F39C12',4:'#E67E22',5:'#C0392B'}};
const CAT_RISQUES = ['Technique','Financier','Planning','Ressources','Juridique','Autre'];
const STATUTS_RSK = ['Identifié','En cours de traitement','Résolu','Accepté','Clos'];

function startEdit() {{
  document.body.classList.add('edit-mode');
  document.getElementById('btn-edit').style.display   = 'none';
  document.getElementById('btn-save').style.display   = '';
  document.getElementById('btn-cancel').style.display = '';
  _editActive = true;
  renderRisquesEditor();
  loadContactsForSelects();
}}

function cancelEdit() {{
  document.body.classList.remove('edit-mode');
  document.getElementById('btn-edit').style.display   = '';
  document.getElementById('btn-save').style.display   = 'none';
  document.getElementById('btn-cancel').style.display = 'none';
  document.getElementById('save-status').textContent  = '';
  _editActive = false;
}}

async function saveFiche() {{
  const status = document.getElementById('save-status');
  status.textContent = 'Enregistrement…';
  status.style.color = '#ccc';

  // Collecter tous les champs ef par name
  const fd = {{}};
  document.querySelectorAll('.ef[name]').forEach(el => {{
    if (el.disabled) return;
    const n = el.name;
    if (el.tagName === 'SELECT' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {{
      fd[n] = el.value === '' ? null : el.value;
    }}
  }});

  // Champs numériques
  ['avancement','budget_initial','budget_actuel','budget_estime',
   'tension_portee','tension_couts','tension_delais'].forEach(k => {{
    if (fd[k] !== undefined && fd[k] !== null) fd[k] = parseFloat(fd[k]) || 0;
  }});
  ['chef_projet_contact_id','responsable_contact_id','service_id'].forEach(k => {{
    if (fd[k]) fd[k] = parseInt(fd[k]) || null;
    else fd[k] = null;
  }});

  // JSON complexes
  const c6 = {{}};
  ['portee_desc','couts_desc','delais_desc','ressources_desc','qualite_desc','risques_proj_desc'].forEach(k => {{
    c6[k] = fd[k] || ''; delete fd[k];
  }});
  fd.contraintes_6axes = JSON.stringify(c6);

  const tt = {{}};
  ['tension_portee','tension_couts','tension_delais'].forEach(k => {{
    tt[k] = fd[k] || 3; delete fd[k];
  }});
  fd.triangle_tensions = JSON.stringify(tt);
  if (fd.arbitrage !== undefined) {{ /* keep */ }}

  fd.registre_risques = JSON.stringify(_risques);

  try {{
    const res = await fetch('/api/projet/' + PROJET_ID, {{
      method: 'PUT',
      headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN }},
      body: JSON.stringify(fd)
    }});
    const data = await res.json();
    if (data.success) {{
      status.textContent = '✓ Sauvegardé — rechargement…';
      status.style.color = '#6c6';
      cancelEdit();
      // Demander au parent de recharger la fiche depuis l'API
      window.parent.postMessage({{type:'ficheReload', id:PROJET_ID}}, '*');
    }} else {{
      status.textContent = '✗ Erreur : ' + (data.error || 'inconnue');
      status.style.color = '#f66';
    }}
  }} catch(e) {{
    status.textContent = '✗ ' + e.message;
    status.style.color = '#f66';
  }}
}}

function updateViewValues(fd) {{
  document.querySelectorAll('.ef[name]').forEach(el => {{
    const n = el.name;
    const vv = el.closest('td')?.querySelector('.vv');
    if (!vv) return;
    let txt = el.value;
    if (n === 'date_debut' || n === 'date_fin_prevue' || n === 'date_fin_reelle') {{
      txt = txt ? txt.split('-').reverse().join('/') : '';
    }}
    if (n === 'avancement') {{
      updateProgBar(parseInt(txt) || 0);
    }}
    vv.textContent = txt;
  }});
}}

function updateProgBar(v) {{
  const bar = document.getElementById('prog-bar');
  if (!bar) return;
  const color = v >= 80 ? '#27AE60' : (v >= 40 ? '#F39C12' : '#C0392B');
  bar.style.width = v + '%';
  bar.style.background = color;
  bar.textContent = v + '%';
}}

// Triangle sliders
function updateTriSlider(input) {{
  const attr = input.name;
  const v = parseInt(input.value);
  const col = COLORS_TRI[v] || '#F39C12';
  const niv = NIVEAUX_TRI[v] || 'Modéré';
  const lbl = document.getElementById('tri-lbl-' + attr);
  if (lbl) lbl.textContent = v + '/5';
  const cell = document.getElementById('tri-cell-' + attr);
  if (cell) cell.style.background = col;
  const nivEl = document.getElementById('tri-niv-' + attr);
  if (nivEl) {{ const ef = nivEl.querySelector('.ef'); if (ef) ef.textContent = niv; }}
  // Recalc alerte
  let total = 0;
  ['tension_portee','tension_couts','tension_delais'].forEach(a => {{
    const s = document.querySelector('input[name="'+a+'"]');
    total += s ? parseInt(s.value) : 3;
  }});
  const alRow = document.getElementById('tri-alerte');
  if (alRow) {{
    let msg, col2;
    if (total >= 13) {{ msg = 'ALERTE : Triangle très tendu — arbitrage urgent !'; col2 = '#C0392B'; }}
    else if (total >= 10) {{ msg = 'Attention : tensions élevées sur certains axes.'; col2 = '#E67E22'; }}
    else {{ msg = 'Triangle équilibré — axes sous contrôle.'; col2 = '#27AE60'; }}
    alRow.firstElementChild.textContent = msg;
    alRow.firstElementChild.style.background = col2;
  }}
}}

// Registre risques editor
function renderRisquesEditor() {{
  const tbody = document.getElementById('risques-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  _risques.forEach((r, i) => {{
    tbody.insertAdjacentHTML('beforeend', risqueRowHtml(r, i));
  }});
}}

function risqueRowHtml(r, i) {{
  const catOpts = CAT_RISQUES.map(c => `<option${{c===r.categorie?' selected':''}}>${{c}}</option>`).join('');
  const stOpts  = STATUTS_RSK.map(s => `<option${{s===r.statut?' selected':''}}>${{s}}</option>`).join('');
  const crit = (parseInt(r.probabilite||0) * parseInt(r.impact||0));
  return `<tr data-idx="${{i}}">
    <td><input value="${{_esc(r.description||'')}}" oninput="_risques[${{i}}].description=this.value"></td>
    <td><select onchange="_risques[${{i}}].categorie=this.value">${{catOpts}}</select></td>
    <td><input type="number" min="1" max="5" value="${{r.probabilite||1}}" style="width:100%" oninput="_risques[${{i}}].probabilite=parseInt(this.value)||1;_risques[${{i}}].criticite=_risques[${{i}}].probabilite*_risques[${{i}}].impact;this.closest('tr').querySelector('.crit-val').textContent=_risques[${{i}}].criticite"></td>
    <td><input type="number" min="1" max="5" value="${{r.impact||1}}" style="width:100%" oninput="_risques[${{i}}].impact=parseInt(this.value)||1;_risques[${{i}}].criticite=_risques[${{i}}].probabilite*_risques[${{i}}].impact;this.closest('tr').querySelector('.crit-val').textContent=_risques[${{i}}].criticite"></td>
    <td class="crit-val" style="text-align:center;font-weight:bold">${{r.criticite||crit}}</td>
    <td><input value="${{_esc(r.action||'')}}" oninput="_risques[${{i}}].action=this.value"></td>
    <td><select onchange="_risques[${{i}}].statut=this.value">${{stOpts}}</select></td>
    <td><button class="btn-rsk-del" onclick="deleteRisque(${{i}})">✕</button></td>
  </tr>`;
}}

function addRisqueRow() {{
  _risques.push({{description:'',categorie:'Technique',probabilite:1,impact:1,criticite:1,action:'',statut:'Identifié'}});
  renderRisquesEditor();
}}

function deleteRisque(i) {{
  _risques.splice(i, 1);
  renderRisquesEditor();
}}

function _esc(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ── Autocomplete contacts ──────────────────────────────────────────────────
let _allContacts = [];

async function loadContactsForSelects() {{
  try {{
    const res = await fetch('/api/contact', {{
      headers: {{ 'Authorization': 'Bearer ' + TOKEN }}
    }});
    const data = await res.json();
    _allContacts = data.list || [];
    document.querySelectorAll('.ac-input').forEach(ac => initContactAC(ac));
  }} catch(e) {{ console.warn('Contacts load:', e); }}
}}

function _cLabel(c) {{
  const nom = ((c.prenom||'')+' '+(c.nom||'')).trim();
  return nom + (c.fonction ? ' \u2014 '+c.fonction : '');
}}

function _hilight(text, q) {{
  if (!q) return _esc(text);
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return _esc(text);
  return _esc(text.slice(0,i))+'<strong>'+_esc(text.slice(i,i+q.length))+'</strong>'+_esc(text.slice(i+q.length));
}}

function initContactAC(acInput) {{
  const hidden = acInput.nextElementSibling;   // <input type="hidden" name="...">
  const drop   = hidden.nextElementSibling;    // <div class="ac-drop">
  let activeIdx = -1;

  // Pré-remplir si un contact est déjà sélectionné
  if (hidden.value) {{
    const c = _allContacts.find(c => String(c.id) === String(hidden.value));
    if (c) {{ acInput.value = _cLabel(c); acInput.classList.add('ac-ok'); }}
  }}

  acInput.addEventListener('input', () => {{
    hidden.value = '';
    acInput.classList.remove('ac-ok', 'ac-err');
    const q = acInput.value.trim();
    if (!q) {{ _closeDrop(); return; }}
    _showDrop(q);
  }});

  acInput.addEventListener('focus', () => {{
    if (acInput.value.trim() && !hidden.value) _showDrop(acInput.value.trim());
  }});

  acInput.addEventListener('keydown', e => {{
    const items = drop.querySelectorAll('.ac-item');
    if (e.key === 'ArrowDown') {{
      e.preventDefault();
      activeIdx = Math.min(activeIdx+1, items.length-1);
      _setActive(items);
    }} else if (e.key === 'ArrowUp') {{
      e.preventDefault();
      activeIdx = Math.max(activeIdx-1, 0);
      _setActive(items);
    }} else if (e.key === 'Enter') {{
      e.preventDefault();
      if (items[activeIdx]) items[activeIdx].click();
    }} else if (e.key === 'Escape') {{
      _closeDrop(); acInput.blur();
    }}
  }});

  acInput.addEventListener('blur', () => {{
    setTimeout(() => {{
      _closeDrop();
      if (acInput.value.trim() && !hidden.value) acInput.classList.add('ac-err');
    }}, 200);
  }});

  function _showDrop(q) {{
    activeIdx = -1;
    const ql = q.toLowerCase();
    const matches = ql
      ? _allContacts.filter(c => ((c.prenom||'')+' '+(c.nom||'')+' '+(c.fonction||'')+' '+(c.email||'')).toLowerCase().includes(ql))
      : _allContacts;
    drop.innerHTML = '';
    if (!matches.length) {{
      drop.innerHTML = '<div class="ac-empty">Aucun contact trouvé</div>';
    }} else {{
      matches.slice(0, 14).forEach(c => {{
        const nom = _cLabel(c);
        const div = document.createElement('div');
        div.className = 'ac-item';
        div.innerHTML = _hilight(nom, q)
          + (c.email ? '<span class="ac-sub">'+_esc(c.email)+'</span>' : '');
        div.addEventListener('mousedown', ev => ev.preventDefault()); // empêche blur
        div.addEventListener('click', () => {{
          hidden.value = String(c.id);
          acInput.value = nom;
          acInput.classList.add('ac-ok');
          acInput.classList.remove('ac-err');
          _closeDrop();
        }});
        drop.appendChild(div);
      }});
    }}
    drop.classList.add('open');
  }}

  function _closeDrop() {{ drop.classList.remove('open'); activeIdx = -1; }}

  function _setActive(items) {{
    items.forEach((it,i) => it.classList.toggle('ac-active', i===activeIdx));
    if (items[activeIdx]) items[activeIdx].scrollIntoView({{block:'nearest'}});
  }}
}}

// Réception token Word depuis parent
window.addEventListener('message', function(e) {{
  if (e.data === 'closeFicheViewer') window.parent.postMessage('closeFicheViewer','*');
}});
</script>
</body>
</html>'''

    return h


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée web — charge les données depuis PostgreSQL
# ─────────────────────────────────────────────────────────────────────────────
def generer_fiche_html_depuis_id_pg(projet_id: int, db) -> str:
    proj_row = db.fetch_one(
        "SELECT p.*, s.nom as service_nom "
        "FROM projets p LEFT JOIN services s ON s.id=p.service_id "
        "WHERE p.id=%s", [projet_id]
    )
    if not proj_row:
        raise ValueError(f"Projet {projet_id} introuvable")

    proj = dict(proj_row)

    def sg(k, default=''):
        v = proj.get(k)
        return v if v is not None else default

    # Tâches
    taches_rows = db.fetch_all(
        "SELECT titre, statut, date_echeance, estimation_heures "
        "FROM taches WHERE projet_id=%s ORDER BY date_echeance", [projet_id]
    ) or []
    taches = [{'titre': r.get('titre') or '', 'statut': r.get('statut') or '',
               'echeance': _fmt_date(r.get('date_echeance')),
               'heures': f"{int(r.get('estimation_heures') or 0)}h"} for r in taches_rows]

    # Bons de commande
    bcs_rows = db.fetch_all(
        "SELECT numero_bc, objet, statut, montant_ttc FROM bons_commande "
        "WHERE projet_id=%s ORDER BY date_creation DESC LIMIT 8", [projet_id]
    ) or []
    bcs_str = '\n'.join(
        f"• {r.get('numero_bc','')} — {(r.get('objet') or '')[:35]} "
        f"({r.get('statut','')}) — {_fmt_eur(r.get('montant_ttc'))}"
        for r in bcs_rows
    ) if bcs_rows else 'Aucun BC lié'

    def _contact_nom(contact_id):
        if not contact_id: return ''
        try:
            r = db.fetch_one(
                "SELECT COALESCE(prenom,'') || ' ' || COALESCE(nom,'') AS n "
                "FROM contacts WHERE id=%s", [contact_id]
            )
            return (r.get('n') or '').strip() if r else ''
        except: return ''

    chef        = _contact_nom(sg('chef_projet_contact_id') or None)
    responsable = _contact_nom(sg('responsable_contact_id') or None)

    equipe = ''
    try:
        rows = db.fetch_all(
            "SELECT COALESCE(pe.membre_label, TRIM(COALESCE(u.prenom,'') || ' ' || COALESCE(u.nom,''))) AS n "
            "FROM projet_equipe pe LEFT JOIN utilisateurs u ON u.id=pe.utilisateur_id "
            "WHERE pe.projet_id=%s", [projet_id]
        ) or []
        equipe = ', '.join(r.get('n') for r in rows if r.get('n'))
    except: pass

    contacts = []
    try:
        rows = db.fetch_all(
            "SELECT COALESCE(pc.role,'') AS role, "
            "  COALESCE(pc.contact_libre, TRIM(COALESCE(c.prenom,'') || ' ' || COALESCE(c.nom,''))) AS nom, "
            "  COALESCE(c.fonction,'') AS fonction, COALESCE(c.email,'') AS email "
            "FROM projet_contacts pc LEFT JOIN contacts c ON c.id=pc.contact_id "
            "WHERE pc.projet_id=%s", [projet_id]
        ) or []
        contacts = [dict(r) for r in rows]
    except: pass

    prestataires = ''
    try:
        rows = db.fetch_all(
            "SELECT f.nom FROM projet_prestataires pp "
            "JOIN fournisseurs f ON f.id=pp.fournisseur_id "
            "WHERE pp.projet_id=%s", [projet_id]
        ) or []
        prestataires = ', '.join(r.get('nom','') for r in rows if r.get('nom'))
    except: pass

    data = {
        'code':                   sg('code'),
        'nom':                    sg('nom'),
        'statut':                 sg('statut'),
        'phase':                  sg('phase'),
        'priorite':               sg('priorite'),
        'type_projet':            sg('type_projet'),
        'avancement':             sg('avancement', 0),
        'date_debut':             str(sg('date_debut')),
        'date_fin':               str(sg('date_fin_prevue')),
        'date_fin_reelle':        str(sg('date_fin_reelle')),
        'description':            sg('description'),
        'chef_projet':            chef,
        'responsable':            responsable,
        'equipe':                 equipe,
        'prestataires':           prestataires,
        'service':                sg('service_nom'),
        'service_id':             proj.get('service_id'),
        'chef_projet_contact_id': proj.get('chef_projet_contact_id'),
        'responsable_contact_id': proj.get('responsable_contact_id'),
        'budget_previsionnel':    proj.get('budget_initial') or proj.get('budget_estime'),
        'budget_vote':            proj.get('budget_actuel'),
        'budget_consomme':        proj.get('budget_consomme'),
        'budget_initial':         proj.get('budget_initial'),
        'budget_estime':          proj.get('budget_estime'),
        'budget_actuel':          proj.get('budget_actuel'),
        'ligne_budg':             '',
        'bcs':                    bcs_str,
        'objectifs':              sg('objectifs'),
        'enjeux':                 sg('enjeux'),
        'risques':                sg('risques'),
        'gains':                  sg('gains'),
        'contraintes':            sg('contraintes'),
        'solutions':              sg('solutions'),
        'financement':            sg('financement'),
        'note':                   sg('note'),
        'taches':                 taches,
        'contacts':               contacts,
        'registre_risques':       sg('registre_risques'),
        'contraintes_6axes':      sg('contraintes_6axes'),
        'triangle_tensions':      sg('triangle_tensions'),
        'arbitrage':              sg('arbitrage'),
    }

    return generer_fiche_html(data, projet_id)
