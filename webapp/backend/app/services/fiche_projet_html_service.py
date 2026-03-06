"""
fiche_projet_html_service.py
Génère la fiche projet en HTML pour affichage web (navigateur / iframe).
Mêmes couleurs et structure que la version Word :
  #C00000 rouge      → en-têtes sections majeures
  #F2DDDC rose pâle  → zones valeurs
  #D8D8D8 gris clair → libellés
  #BFBFBF gris moyen → sous-sections
  #F2F2F2 gris léger → alternance lignes
"""
import json as _json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

RED   = '#C00000'
PINK  = '#F2DDDC'
GRAY1 = '#D8D8D8'
GRAY2 = '#BFBFBF'
GRAY4 = '#F2F2F2'


def _e(s):
    """HTML escape."""
    if s is None:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _fmt_eur(v):
    try:
        return f"{float(v or 0):,.2f} \u20ac"
    except Exception:
        return '0,00 \u20ac'


def _fmt_pct(v):
    try:
        return f"{int(v or 0)} %"
    except Exception:
        return '0 %'


def _fmt_date(d):
    if not d:
        return ''
    try:
        return datetime.fromisoformat(str(d)[:10]).strftime('%d/%m/%Y')
    except Exception:
        return str(d)[:10]


def _progress_bar(pct):
    try:
        v = int(pct or 0)
    except Exception:
        v = 0
    color = '#27AE60' if v >= 80 else ('#F39C12' if v >= 40 else '#C0392B')
    return (
        f'<div style="background:#e0e0e0;border-radius:4px;height:16px;width:100%;margin:4px 0">'
        f'<div style="width:{v}%;background:{color};height:16px;border-radius:4px;'
        f'display:flex;align-items:center;justify-content:center;color:#fff;font-size:9px;font-weight:bold">'
        f'{v}%</div></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers HTML
# ─────────────────────────────────────────────────────────────────────────────
def _sec(title, colspan=4):
    return f'<tr><td class="sec" colspan="{colspan}">{_e(title)}</td></tr>\n'

def _sub(title, colspan=4, bg=GRAY2):
    return f'<tr><td style="background:{bg};font-weight:bold;padding:5px 8px;font-size:11px" colspan="{colspan}">{_e(title)}</td></tr>\n'

def _sub2(title, colspan=2):
    return f'<td style="background:{GRAY1};font-weight:bold;text-align:center;padding:4px 8px;font-size:10px" colspan="{colspan}">{_e(title)}</td>'

def _hdr(*cols):
    cells = ''.join(f'<th class="hdr">{_e(c)}</th>' for c in cols)
    return f'<tr>{cells}</tr>\n'

def _row2(l1, v1, l2, v2):
    return (f'<tr>'
            f'<td class="lbl">{_e(l1)}</td><td class="val">{_e(v1)}</td>'
            f'<td class="lbl">{_e(l2)}</td><td class="val">{_e(v2)}</td>'
            f'</tr>\n')

def _row1(label, value, colspan=3, cls='val'):
    return f'<tr><td class="lbl">{_e(label)}</td><td class="{cls}" colspan="{colspan}">{_e(value)}</td></tr>\n'

def _ta(text, colspan=4, min_h=60):
    return (f'<tr><td colspan="{colspan}" '
            f'style="background:{PINK};white-space:pre-wrap;padding:6px 8px;min-height:{min_h}px;vertical-align:top">'
            f'{_e(text or "")}</td></tr>\n')


# ─────────────────────────────────────────────────────────────────────────────
# Génération HTML
# ─────────────────────────────────────────────────────────────────────────────
def generer_fiche_html(data: dict) -> str:
    p = data
    today = datetime.now().strftime('%d/%m/%Y')

    css = """
    <style>
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        font-family: Arial, Helvetica, sans-serif;
        font-size: 11px;
        color: #111;
        background: #ececec;
      }
      .toolbar {
        position: sticky;
        top: 0;
        z-index: 100;
        background: #1a1a2e;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
      }
      .toolbar span {
        flex: 1;
        color: #ccc;
        font-size: 12px;
        font-weight: bold;
      }
      .btn-toolbar {
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 11px;
        font-weight: bold;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 5px;
      }
      .btn-close  { background: #dc3545; color: #fff; }
      .btn-print  { background: #0d6efd; color: #fff; }
      .btn-word   { background: #198754; color: #fff; }
      .btn-toolbar:hover { opacity: .87; }
      .page {
        max-width: 980px;
        margin: 20px auto;
        background: #fff;
        padding: 24px 28px;
        box-shadow: 0 2px 12px rgba(0,0,0,.18);
        border-radius: 4px;
      }
      h1.titre {
        background: #C00000;
        color: #fff;
        text-align: center;
        padding: 14px;
        font-size: 17px;
        letter-spacing: .5px;
        border-radius: 3px 3px 0 0;
      }
      p.soustitre {
        background: #9b0000;
        color: #F2DDDC;
        text-align: center;
        padding: 7px;
        font-size: 11px;
        margin-bottom: 20px;
      }
      table.fiche {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        border: 1px solid #bbb;
      }
      table.fiche td, table.fiche th {
        border: 1px solid #bbb;
        padding: 5px 8px;
        font-size: 11px;
        vertical-align: middle;
      }
      .sec {
        background: #C00000;
        color: #fff;
        font-weight: bold;
        font-size: 13px;
        padding: 8px 10px;
        letter-spacing: .3px;
      }
      .hdr { background: #C00000; color: #fff; text-align: center; font-weight: bold; font-size: 10px; }
      .lbl { background: #D8D8D8; font-weight: bold; width: 17%; }
      .val { background: #F2DDDC; }
      .val-w { background: #fff; }
      .val-g { background: #F2F2F2; }
      .ctr { text-align: center; }
      .footer-fiche {
        text-align: center;
        color: #999;
        font-size: 9px;
        margin-top: 24px;
        padding-top: 8px;
        border-top: 1px solid #ddd;
      }
      @media print {
        .toolbar { display: none !important; }
        body { background: #fff; }
        .page { margin: 0; padding: 12px; box-shadow: none; max-width: 100%; }
        table.fiche { page-break-inside: auto; }
        tr { page-break-inside: avoid; }
      }
    </style>
    """

    # ── Toolbar (boutons sticky en haut)
    code = _e(p.get('code', ''))
    toolbar = f"""
    <div class="toolbar no-print">
      <span>Fiche Projet — {code}</span>
      <button class="btn-toolbar btn-print" onclick="window.print()">&#128424; Imprimer / PDF</button>
      <button class="btn-toolbar btn-word" id="btn-word-dl">&#128196; Télécharger Word</button>
      <button class="btn-toolbar btn-close" onclick="window.parent.postMessage('closeFicheViewer','*')">&#10005; Fermer</button>
    </div>
    """

    html = f'<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="UTF-8">\n'
    html += f'<title>Fiche Projet — {code}</title>\n'
    html += css
    html += '</head>\n<body>\n'
    html += toolbar
    html += '<div class="page">\n'

    # ── Bandeau titre
    html += f'<h1 class="titre">FICHE PROJET \u2014 Budget Manager Pro V5</h1>\n'
    html += f'<p class="soustitre">Date\u00a0: {today}\u00a0\u00a0|\u00a0\u00a0Code\u00a0: {_e(p.get("code",""))}\u00a0\u00a0|\u00a0\u00a0Statut\u00a0: {_e(p.get("statut",""))}</p>\n'

    # ── 1. IDENTIFICATION
    html += '<table class="fiche">\n'
    html += _sec('1. IDENTIFICATION')
    html += _sub('Informations générales')
    html += _row2('Code projet', p.get('code',''), 'Intitulé', p.get('nom',''))
    html += _row2('Type', p.get('type_projet',''), 'Priorité', p.get('priorite',''))
    html += _row2('Phase', p.get('phase',''), 'Avancement', _fmt_pct(p.get('avancement')))
    pct = p.get('avancement') or 0
    html += f'<tr><td colspan="4" style="padding:5px 8px;background:#fafafa">{_progress_bar(pct)}</td></tr>\n'
    html += _row2('Date début', _fmt_date(p.get('date_debut')), 'Fin prévue', _fmt_date(p.get('date_fin')))
    html += _row2('Fin réelle', _fmt_date(p.get('date_fin_reelle')), 'Service', p.get('service',''))
    html += _sub('Description détaillée du projet')
    html += _ta(p.get('description',''), min_h=80)
    html += _sub('Acteurs du projet')
    html += _hdr('Rôle', 'Nom Prénom', 'Fonction / Service', 'Email / Tél')
    for role, nom in [('Chef de projet DSI', p.get('chef_projet','')),
                      ('Responsable métier',  p.get('responsable','')),
                      ('Équipe projet',       p.get('equipe','')),
                      ('Prestataires',        p.get('prestataires',''))]:
        html += (f'<tr><td class="lbl">{_e(role)}</td>'
                 f'<td class="val-w">{_e(nom)}</td>'
                 f'<td class="val-w"></td>'
                 f'<td class="val"></td></tr>\n')
    html += '</table>\n'

    # ── 2. OPPORTUNITÉ
    html += '<table class="fiche">\n'
    html += _sec('2. OPPORTUNITÉ')
    html += _sub('Objectifs "métier" opérationnels du projet')
    html += f'<tr>{_sub2("Objectifs identifiés")}{_sub2("Description détaillée")}</tr>\n'
    html += (f'<tr>'
             f'<td colspan="2" style="background:{PINK};white-space:pre-wrap;min-height:70px;padding:6px 8px;vertical-align:top">{_e(p.get("objectifs",""))}</td>'
             f'<td colspan="2" style="background:#fff;min-height:70px"></td>'
             f'</tr>\n')
    html += _sub('Principaux risques identifiés à NE PAS faire le projet')
    html += f'<tr>{_sub2("Risques identifiés")}{_sub2("Description détaillée")}</tr>\n'
    html += (f'<tr>'
             f'<td colspan="2" style="background:{PINK};white-space:pre-wrap;min-height:70px;padding:6px 8px;vertical-align:top">{_e(p.get("risques",""))}</td>'
             f'<td colspan="2" style="background:#fff;min-height:70px"></td>'
             f'</tr>\n')
    html += _sub('Gains qualitatifs et bénéfices attendus')
    html += _ta(p.get('gains',''), min_h=60)
    html += _sub("Enjeux stratégiques de l'établissement")
    html += _ta(p.get('enjeux',''), min_h=50)
    html += '</table>\n'

    # ── 3. BUDGET & FINANCEMENT
    html += '<table class="fiche">\n'
    html += _sec('3. BUDGET & FINANCEMENT')
    html += _sub('Synthèse budgétaire')
    html += _row2('Budget prévisionnel', _fmt_eur(p.get('budget_previsionnel')),
                  'Budget voté',         _fmt_eur(p.get('budget_vote')))
    html += _row2('Budget consommé (BC)', _fmt_eur(p.get('budget_consomme')),
                  'Ligne budgétaire',    p.get('ligne_budg',''))
    html += _row1('Bons de commande liés', p.get('bcs','Aucun BC lié'))
    html += _sub('Coûts et charges par phase')
    html += _hdr('Catégorie', 'Définition projet', 'Mise en œuvre', 'Total €')
    couts = p.get('couts_detail', {}) or {}
    total_def = total_meo = 0.0
    for cat in ['MOE interne','MOA interne','Licences / Logiciels',
                'Materiels / Serveurs','Sous-traitance','Autres']:
        cd = couts.get(cat, {}) or {}
        def_ = cd.get('definition', 0) or 0
        meo  = cd.get('mise_en_oeuvre', 0) or 0
        tot  = cd.get('total', def_ + meo) or 0
        total_def += def_
        total_meo += meo
        html += (f'<tr><td class="val-g">{_e(cat)}</td>'
                 f'<td class="val-w ctr">{f"{def_:,.2f}" if def_ else ""}</td>'
                 f'<td class="val-w ctr">{f"{meo:,.2f}"  if meo  else ""}</td>'
                 f'<td class="val ctr">{f"{tot:,.2f}"    if tot  else ""}</td></tr>\n')
    grand = total_def + total_meo
    html += (f'<tr>'
             f'<td style="background:{GRAY2};font-weight:bold">TOTAL</td>'
             f'<td class="val ctr">{f"{total_def:,.2f}" if total_def else ""}</td>'
             f'<td class="val ctr">{f"{total_meo:,.2f}" if total_meo else ""}</td>'
             f'<td class="val ctr" style="font-weight:bold">{f"{grand:,.2f}" if grand else ""}</td></tr>\n')
    html += _sub('Modalités de financement (internes / externes)')
    html += _ta(p.get('financement','') or '', min_h=50)
    html += '</table>\n'

    # ── 4. PLANNING & TÂCHES
    taches = p.get('taches', []) or []
    html += '<table class="fiche">\n'
    html += _sec('4. PLANNING & TÂCHES')
    html += _hdr('Tâche / Livrable', 'Statut', 'Échéance', 'Charge (h)')
    if taches:
        for i, tk in enumerate(taches):
            bg = GRAY4 if i % 2 else '#fff'
            html += (f'<tr style="background:{bg}">'
                     f'<td style="width:55%">{_e(tk.get("titre",""))}</td>'
                     f'<td class="ctr">{_e(tk.get("statut",""))}</td>'
                     f'<td class="val ctr">{_e(tk.get("echeance",""))}</td>'
                     f'<td class="val ctr">{_e(tk.get("heures",""))}</td></tr>\n')
    else:
        html += '<tr><td colspan="4" style="text-align:center;color:#888;padding:18px">Aucune tâche enregistrée</td></tr>\n'
    html += '</table>\n'

    # ── 5. ÉQUIPE & CONTACTS
    contacts = p.get('contacts', []) or []
    html += '<table class="fiche">\n'
    html += _sec('5. ÉQUIPE & CONTACTS')
    html += _hdr('Rôle', 'Nom Prénom', 'Fonction / Service', 'Email / Tél')
    acteurs = [('Chef de projet DSI', p.get('chef_projet',''), 'DSI', ''),
               ('Responsable métier',  p.get('responsable',''), '', '')]
    for c in contacts:
        acteurs.append((c.get('role',''), c.get('nom',''),
                        c.get('fonction',''), c.get('email','')))
    if not contacts and p.get('equipe'):
        acteurs.append(('Équipe projet', p.get('equipe',''), '', ''))
    for role, nom, fn, email in acteurs:
        html += (f'<tr><td class="lbl">{_e(role)}</td>'
                 f'<td class="val-w">{_e(nom)}</td>'
                 f'<td class="val-w">{_e(fn)}</td>'
                 f'<td class="val">{_e(email)}</td></tr>\n')
    html += '</table>\n'

    # ── 6. SOLUTIONS & CONTRAINTES
    html += '<table class="fiche">\n'
    html += _sec('6. SOLUTIONS & CONTRAINTES')
    html += _sub('Ressources MOE disponibles — Solutions envisagées')
    html += _ta(p.get('solutions',''), min_h=70)
    html += _sub('Contraintes techniques / réglementaires / RGPD')
    html += _ta(p.get('contraintes',''), min_h=70)
    html += '</table>\n'

    # ── 6b. LES 6 CONTRAINTES PROJET
    ctr_data = {}
    ctr_raw = p.get('contraintes_6axes')
    if ctr_raw:
        try:
            ctr_data = _json.loads(ctr_raw) if isinstance(ctr_raw, str) else (ctr_raw or {})
        except Exception:
            pass

    AXES_6 = [
        ('portee_desc',       'Portée',     'Périmètre, livrables, fonctionnalités incluses'),
        ('couts_desc',        'Coûts',      'Budget global, salaires, équipements, licences'),
        ('delais_desc',       'Délais',     'Calendrier, jalons, phases, dates clés'),
        ('ressources_desc',   'Ressources', 'Équipes, compétences, équipements, logiciels'),
        ('qualite_desc',      'Qualité',    "Critères d'acceptation, niveaux de service"),
        ('risques_proj_desc', 'Risques',    'Événements imprévus pouvant impacter le projet'),
    ]
    html += '<table class="fiche">\n'
    html += _sec('6b. LES 6 CONTRAINTES PROJET')
    html += _sub("Les 6 contraintes sont interconnectées — modifier l'une impacte les autres.")
    for i in range(0, len(AXES_6), 2):
        html += '<tr>\n'
        for j in range(2):
            if i + j < len(AXES_6):
                attr, label, hint = AXES_6[i + j]
                val = ctr_data.get(attr, '') or ''
                bg = PINK if val else GRAY4
                txt = _e(val) if val else f'<em style="color:#888">{_e(hint)}</em>'
                html += (f'<td colspan="2" style="background:{bg};padding:8px;'
                         f'vertical-align:top;width:50%;min-height:70px">'
                         f'<strong>{_e(label)}</strong><br><span style="white-space:pre-wrap">{txt}</span></td>\n')
            else:
                html += f'<td colspan="2" style="background:{GRAY4}"></td>\n'
        html += '</tr>\n'
    html += '</table>\n'

    # ── 6c. TRIANGLE D'OR
    tri_data = {}
    tri_raw = p.get('triangle_tensions')
    if tri_raw:
        try:
            tri_data = _json.loads(tri_raw) if isinstance(tri_raw, str) else (tri_raw or {})
        except Exception:
            pass

    NIVEAUX = {1: 'Faible', 2: 'Modéré', 3: 'Modéré', 4: 'Élevé', 5: 'Critique'}
    COULEURS_TRI = {1: '#27AE60', 2: '#27AE60', 3: '#F39C12', 4: '#E67E22', 5: '#C0392B'}

    axes_tri = [
        ('tension_portee', 'Portée',  'Risque de dérive du périmètre (scope creep)'),
        ('tension_couts',  'Coûts',   'Pression sur le budget disponible'),
        ('tension_delais', 'Délais',  'Pression sur le calendrier'),
    ]
    html += '<table class="fiche">\n'
    html += _sec("6c. TRIANGLE D'OR \u2014 PORTÉE / COÛTS / DÉLAIS")
    html += _sub('Niveau de tension sur chaque axe (1 = sous contrôle, 5 = très tendu)')
    html += _hdr('Axe', 'Tension (1-5)', 'Niveau', 'Interprétation')

    total_tri = 0
    for attr, label, desc in axes_tri:
        v = int(tri_data.get(attr, 3))
        total_tri += v
        col = COULEURS_TRI.get(v, '#F39C12')
        niv = NIVEAUX.get(v, 'Modéré')
        bars = '\u2588' * v + '\u2591' * (5 - v)
        html += (f'<tr>'
                 f'<td class="lbl">{_e(label)}</td>'
                 f'<td style="background:{col};color:#fff;font-weight:bold;text-align:center">{v}/5 {bars}</td>'
                 f'<td class="val ctr">{_e(niv)}</td>'
                 f'<td>{_e(desc)}</td></tr>\n')

    if total_tri >= 13:
        alerte = 'ALERTE : Triangle très tendu \u2014 arbitrage urgent nécessaire !'
        fill_tri = '#C0392B'
    elif total_tri >= 10:
        alerte = 'Attention : tensions élevées sur certains axes \u2014 surveiller de près.'
        fill_tri = '#E67E22'
    else:
        alerte = 'Triangle équilibré \u2014 les trois axes sont sous contrôle.'
        fill_tri = '#27AE60'
    html += (f'<tr><td colspan="4" style="background:{fill_tri};color:#fff;'
             f'font-weight:bold;padding:7px 8px">{_e(alerte)}</td></tr>\n')

    arbitrage = p.get('arbitrage', '')
    if arbitrage:
        html += _sub("Stratégie d'arbitrage")
        html += _ta(arbitrage, min_h=50)
    html += '</table>\n'

    # ── 6d. REGISTRE DES RISQUES
    risques_list = []
    rsk_raw = p.get('registre_risques')
    if rsk_raw:
        try:
            risques_list = _json.loads(rsk_raw) if isinstance(rsk_raw, str) else (rsk_raw or [])
        except Exception:
            pass

    html += '<table class="fiche">\n'
    html += _sec('6d. REGISTRE DES RISQUES', colspan=7)
    html += _hdr('Description', 'Catégorie', 'Proba', 'Impact', 'Crit.', 'Action corrective', 'Statut')

    if risques_list:
        risques_sorted = sorted(risques_list,
                                key=lambda x: int(x.get('criticite', 0)), reverse=True)
        for i, rsk in enumerate(risques_sorted):
            crit = int(rsk.get('criticite', 0))
            if crit >= 12:   fc_r = '#C0392B'
            elif crit >= 6:  fc_r = '#E67E22'
            elif crit >= 3:  fc_r = '#F1C40F'
            else:            fc_r = '#27AE60'
            bg = GRAY4 if i % 2 else '#fff'
            html += (f'<tr style="background:{bg}">'
                     f'<td style="width:28%">{_e(rsk.get("description",""))}</td>'
                     f'<td>{_e(rsk.get("categorie",""))}</td>'
                     f'<td class="ctr">{_e(str(rsk.get("probabilite","") or ""))}</td>'
                     f'<td class="ctr">{_e(str(rsk.get("impact","") or ""))}</td>'
                     f'<td class="ctr" style="background:{fc_r};color:#fff;font-weight:bold">{crit}</td>'
                     f'<td>{_e(rsk.get("action",""))}</td>'
                     f'<td class="val ctr">{_e(rsk.get("statut",""))}</td></tr>\n')
        nb_crit  = sum(1 for r in risques_list if int(r.get('criticite', 0)) >= 12)
        nb_eleve = sum(1 for r in risques_list if 6 <= int(r.get('criticite', 0)) < 12)
        fill_s = '#C0392B' if nb_crit > 0 else ('#E67E22' if nb_eleve > 0 else '#27AE60')
        synthese = (f"Total\u00a0: {len(risques_list)} risque(s)\u00a0\u00a0|\u00a0\u00a0"
                    f"Critiques (\u226512)\u00a0: {nb_crit}\u00a0\u00a0|\u00a0\u00a0"
                    f"Élevés (6-11)\u00a0: {nb_eleve}")
        html += (f'<tr><td colspan="7" style="background:{fill_s};color:#fff;'
                 f'font-weight:bold;padding:5px 8px">{_e(synthese)}</td></tr>\n')
    else:
        html += '<tr><td colspan="7" style="text-align:center;color:#888;padding:18px">Aucun risque enregistré dans le registre.</td></tr>\n'
    html += '</table>\n'

    # ── 7. VALIDATION & SIGNATURES
    html += '<table class="fiche">\n'
    html += _sec('7. VALIDATION & SIGNATURES')
    html += _hdr('Valideur', 'Nom / Prénom', 'Date', 'Visa')
    for role in ['Chef de projet', 'Responsable DSI', 'Direction']:
        html += (f'<tr><td class="lbl">{_e(role)}</td>'
                 f'<td class="val" style="min-height:44px;height:44px"></td>'
                 f'<td class="val"></td>'
                 f'<td class="val-w"></td></tr>\n')
    html += '</table>\n'

    html += (f'<p class="footer-fiche">Budget Manager Pro V5 \u2014 '
             f'Fiche projet {_e(p.get("code",""))} \u2014 '
             f'Générée le {today}</p>\n')
    html += '</div>\n</body>\n</html>'
    return html


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée web (charge les données depuis PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────
def generer_fiche_html_depuis_id_pg(projet_id: int, db) -> str:
    """
    Charge le projet depuis PostgreSQL et retourne le HTML de la fiche.
    db : instance DatabaseService
    """
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

    # ── Tâches
    taches_rows = db.fetch_all(
        "SELECT titre, statut, date_echeance, estimation_heures "
        "FROM taches WHERE projet_id=%s ORDER BY date_echeance",
        [projet_id]
    ) or []
    taches = [{
        'titre':    r.get('titre') or '',
        'statut':   r.get('statut') or '',
        'echeance': _fmt_date(r.get('date_echeance')),
        'heures':   f"{int(r.get('estimation_heures') or 0)}h",
    } for r in taches_rows]

    # ── Bons de commande
    bcs_rows = db.fetch_all(
        "SELECT numero_bc, objet, statut, montant_ttc FROM bons_commande "
        "WHERE projet_id=%s ORDER BY date_creation DESC LIMIT 8",
        [projet_id]
    ) or []
    bcs_str = '\n'.join(
        f"• {r.get('numero_bc','')} — {(r.get('objet') or '')[:35]} "
        f"({r.get('statut','')}) — {_fmt_eur(r.get('montant_ttc'))}"
        for r in bcs_rows
    ) if bcs_rows else 'Aucun BC lié'

    # ── Chef de projet & responsable
    def _contact_nom(contact_id):
        if not contact_id:
            return ''
        try:
            r = db.fetch_one(
                "SELECT COALESCE(prenom,'') || ' ' || COALESCE(nom,'') AS n "
                "FROM contacts WHERE id=%s", [contact_id]
            )
            return (r.get('n') or '').strip() if r else ''
        except Exception:
            return ''

    chef        = _contact_nom(sg('chef_projet_contact_id') or None)
    responsable = _contact_nom(sg('responsable_contact_id') or None)

    # ── Équipe (membres)
    equipe = ''
    try:
        rows = db.fetch_all(
            "SELECT COALESCE(pe.membre_label, TRIM(COALESCE(u.prenom,'') || ' ' || COALESCE(u.nom,''))) AS n "
            "FROM projet_equipe pe LEFT JOIN utilisateurs u ON u.id=pe.utilisateur_id "
            "WHERE pe.projet_id=%s", [projet_id]
        ) or []
        equipe = ', '.join(r.get('n') for r in rows if r.get('n'))
    except Exception:
        pass

    # ── Contacts externes
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
    except Exception:
        pass

    # ── Prestataires
    prestataires = ''
    try:
        rows = db.fetch_all(
            "SELECT f.nom FROM projet_prestataires pp "
            "JOIN fournisseurs f ON f.id=pp.fournisseur_id "
            "WHERE pp.projet_id=%s", [projet_id]
        ) or []
        prestataires = ', '.join(r.get('nom', '') for r in rows if r.get('nom'))
    except Exception:
        pass

    data = {
        'code':                sg('code'),
        'nom':                 sg('nom'),
        'statut':              sg('statut'),
        'phase':               sg('phase'),
        'priorite':            sg('priorite'),
        'type_projet':         sg('type_projet'),
        'avancement':          sg('avancement', 0),
        'date_debut':          sg('date_debut'),
        'date_fin':            sg('date_fin_prevue'),
        'date_fin_reelle':     sg('date_fin_reelle'),
        'description':         sg('description'),
        'chef_projet':         chef,
        'responsable':         responsable,
        'equipe':              equipe,
        'prestataires':        prestataires,
        'service':             sg('service_nom'),
        'budget_previsionnel': proj.get('budget_initial') or proj.get('budget_estime'),
        'budget_vote':         proj.get('budget_actuel'),
        'budget_consomme':     proj.get('budget_consomme'),
        'ligne_budg':          '',
        'bcs':                 bcs_str,
        'objectifs':           sg('objectifs'),
        'enjeux':              sg('enjeux'),
        'risques':             sg('risques'),
        'gains':               sg('gains'),
        'contraintes':         sg('contraintes'),
        'solutions':           sg('solutions'),
        'financement':         sg('financement'),
        'taches':              taches,
        'contacts':            contacts,
        'couts_detail':        {},
        'registre_risques':    sg('registre_risques'),
        'contraintes_6axes':   sg('contraintes_6axes'),
        'triangle_tensions':   sg('triangle_tensions'),
        'arbitrage':           sg('arbitrage'),
    }

    return generer_fiche_html(data)
