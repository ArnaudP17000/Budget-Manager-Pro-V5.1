"""
fiche_bc_view.py — Fiche détail d'un Bon de Commande
Accessible via double-clic dans la liste BC ou bouton 📄 Fiche

Contenu :
  - En-tête : N° BC, statut, entité, dates
  - Bloc Fournisseur : coordonnées complètes
  - Bloc Contrat lié : type, montant max, solde restant, jauge
  - Bloc Ligne budgétaire : voté/engagé/solde avec barre de progression
  - Bloc Application : code, nom
  - Autres BC du même contrat : tableau
  - Journal d'audit de ce BC
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGroupBox, QGridLayout, QWidget, QTabWidget, QScrollArea,
    QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

STATUT_COLORS = {
    'BROUILLON':  ('#95a5a6', '#ffffff'),
    'EN_ATTENTE': ('#f39c12', '#ffffff'),
    'VALIDE':     ('#2ecc71', '#ffffff'),
    'IMPUTE':     ('#2980b9', '#ffffff'),
    'SOLDE':      ('#1abc9c', '#ffffff'),
    'ANNULE':     ('#e74c3c', '#ffffff'),
}


def _card(title, value, color='#2c3e50', value_color=None):
    """Crée une mini-carte info."""
    w = QWidget()
    w.setStyleSheet(f"""
        QWidget {{
            background: {color};
            border-radius: 6px;
            padding: 2px;
        }}
    """)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(10, 8, 10, 8)
    lay.setSpacing(2)
    lbl_t = QLabel(title)
    lbl_t.setStyleSheet("color: #95a5a6; font-size: 10px; font-weight: bold; background: transparent;")
    lbl_v = QLabel(str(value) if value else "—")
    lbl_v.setStyleSheet(
        f"color: {value_color or '#ecf0f1'}; font-size: 13px; font-weight: bold; background: transparent;")
    lbl_v.setWordWrap(True)
    lay.addWidget(lbl_t)
    lay.addWidget(lbl_v)
    return w


def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #2c3e50;")
    return line


class FicheBCDialog(QDialog):
    """Fiche détail complète d'un BC."""

    def __init__(self, bc_id, parent=None):
        super().__init__(parent)
        self.bc_id = bc_id
        self._load_services()
        self.setWindowTitle(f"📄 Fiche BC")
        self.setMinimumWidth(820)
        self.setMinimumHeight(700)
        self.setStyleSheet("background-color: #1a252f; color: #ecf0f1;")
        self._build()
        self._load()

    def _load_services(self):
        try:
            from app.services.bon_commande_service import bon_commande_service
            self.bc_svc = bon_commande_service
        except Exception:
            self.bc_svc = None
        try:
            from app.services.contrat_service import contrat_service
            self.ct_svc = contrat_service
        except Exception:
            self.ct_svc = None
        try:
            from app.services.integrity_service import integrity_service
            self.audit_svc = integrity_service
        except Exception:
            self.audit_svc = None

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── En-tête ──────────────────────────────────────────────────────
        self.header = QWidget()
        self.header.setStyleSheet("background: #1a252f; padding: 12px;")
        hlay = QHBoxLayout(self.header)

        self.lbl_titre = QLabel("📄 Bon de Commande")
        self.lbl_titre.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #ecf0f1;")
        hlay.addWidget(self.lbl_titre)
        hlay.addStretch()

        self.lbl_statut = QLabel("—")
        self.lbl_statut.setStyleSheet(
            "font-size: 13px; font-weight: bold; padding: 6px 14px;"
            "border-radius: 4px; background: #95a5a6; color: white;")
        hlay.addWidget(self.lbl_statut)

        btn_close = QPushButton("✕ Fermer")
        btn_close.setStyleSheet(
            "background: #e74c3c; color: white; font-weight: bold; padding: 6px 14px;")
        btn_close.clicked.connect(self.accept)
        hlay.addWidget(btn_close)
        layout.addWidget(self.header)

        # ── Corps (scrollable) ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #1a252f; border: none;")
        inner = QWidget()
        inner.setStyleSheet("background: #1a252f;")
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(16, 12, 16, 16)
        self.body.setSpacing(12)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def _load(self):
        if not self.bc_svc:
            return
        bc = self.bc_svc.get_bon_commande_by_id(self.bc_id)
        if not bc:
            self.lbl_titre.setText("BC introuvable")
            return

        # Titre + statut
        num = bc.get('numero_bc', '')
        self.lbl_titre.setText(f"📄 {num}")
        self.setWindowTitle(f"📄 Fiche BC — {num}")
        statut = bc.get('statut', '')
        colors = STATUT_COLORS.get(statut, ('#95a5a6', '#ffffff'))
        self.lbl_statut.setText(f"  {statut}  ")
        self.lbl_statut.setStyleSheet(
            f"font-size: 13px; font-weight: bold; padding: 6px 14px;"
            f"border-radius: 4px; background: {colors[0]}; color: {colors[1]};")

        # ── Bloc 1 : Infos générales ──────────────────────────────────────
        grp1 = self._section("📋 Informations générales")
        g1 = QGridLayout()
        g1.setSpacing(8)
        g1.addWidget(_card("Entité",   bc.get('entite_code') or '—'),   0, 0)
        g1.addWidget(_card("N° BC",    bc.get('numero_bc') or '—'),      0, 1)
        g1.addWidget(_card("Objet",    bc.get('objet') or '—'),          0, 2, 1, 2)
        date_c = str(bc.get('date_creation') or bc.get('date_commande') or '')[:10]
        date_l = str(bc.get('date_livraison_prevue') or '')[:10]
        g1.addWidget(_card("Date commande",    date_c),                  1, 0)
        g1.addWidget(_card("Livraison prévue", date_l or '—'),           1, 1)
        g1.addWidget(_card("Nature",    bc.get('nature') or bc.get('type_budget') or '—'), 1, 2)
        ht  = float(bc.get('montant_ht') or 0)
        ttc = float(bc.get('montant_ttc') or 0)
        g1.addWidget(_card("Montant HT",  f"{ht:,.2f} €",  value_color='#f39c12'), 1, 3)
        g1.addWidget(_card("Montant TTC", f"{ttc:,.2f} €", value_color='#e74c3c'), 2, 0)
        desc = (bc.get('description') or bc.get('notes') or '—')[:120]
        g1.addWidget(_card("Description", desc),                         2, 1, 1, 3)
        grp1.setLayout(g1)
        self.body.addWidget(grp1)

        # ── Bloc 2 : Fournisseur ──────────────────────────────────────────
        grp2 = self._section("🏢 Fournisseur")
        g2 = QGridLayout()
        g2.setSpacing(8)
        g2.addWidget(_card("Nom",       bc.get('fournisseur_nom') or '—',
                           value_color='#3498db'), 0, 0, 1, 2)
        # Récupérer coordonnées fournisseur
        fourn = self._get_fournisseur(bc.get('fournisseur_id'))
        if fourn:
            g2.addWidget(_card("Email",     fourn.get('email') or '—'),        0, 2)
            g2.addWidget(_card("Téléphone", fourn.get('telephone') or '—'),    0, 3)
            addr = f"{fourn.get('adresse','')} {fourn.get('code_postal','')} {fourn.get('ville','')}".strip()
            g2.addWidget(_card("Adresse",   addr or '—'),                      1, 0, 1, 2)
            g2.addWidget(_card("SIRET",     fourn.get('siret') or '—'),        1, 2)
            g2.addWidget(_card("Contact",   fourn.get('contact_principal') or '—'), 1, 3)
        grp2.setLayout(g2)
        self.body.addWidget(grp2)

        # ── Bloc 3 : Contrat lié ─────────────────────────────────────────
        contrat_id = bc.get('contrat_id')
        grp3 = self._section("📑 Contrat / Marché lié")
        g3 = QVBoxLayout()

        if contrat_id and self.ct_svc:
            ct = self.ct_svc.get_by_id(contrat_id)
            if ct:
                row1 = QHBoxLayout()
                row1.addWidget(_card("N° Contrat",  ct.get('numero_contrat') or '—', value_color='#9b59b6'))
                row1.addWidget(_card("Type",         ct.get('type_contrat') or '—'))
                row1.addWidget(_card("Fournisseur",  ct.get('fournisseur_nom') or '—'))
                row1.addWidget(_card("Date fin",     str(ct.get('date_fin') or '')[:10]))
                g3.addLayout(row1)

                montant_max  = float(ct.get('montant_max_ht') or ct.get('montant_total_ht') or 0)
                engage_cumul = float(ct.get('montant_engage_cumul') or 0)
                solde        = montant_max - engage_cumul
                pct          = int(engage_cumul / montant_max * 100) if montant_max else 0

                row2 = QHBoxLayout()
                row2.addWidget(_card("Montant max HT", f"{montant_max:,.0f} €"))
                row2.addWidget(_card("Total engagé",   f"{engage_cumul:,.0f} €",
                                     value_color='#e67e22'))
                solde_color = '#e74c3c' if pct >= 90 else ('#f39c12' if pct >= 75 else '#2ecc71')
                row2.addWidget(_card("Solde restant",  f"{solde:,.0f} €",
                                     value_color=solde_color))
                g3.addLayout(row2)

                # Jauge consommation contrat
                jauge_w = QWidget()
                jauge_l = QVBoxLayout(jauge_w)
                jauge_l.setContentsMargins(0, 4, 0, 0)
                lbl_pct = QLabel(f"Consommation contrat : {pct}%")
                lbl_pct.setStyleSheet("color: #bdc3c7; font-size: 11px;")
                jauge_l.addWidget(lbl_pct)
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(min(pct, 100))
                bar.setTextVisible(False)
                bar.setFixedHeight(12)
                bar_color = '#e74c3c' if pct >= 90 else ('#f39c12' if pct >= 75 else '#2ecc71')
                bar.setStyleSheet(f"""
                    QProgressBar {{ background: #2c3e50; border-radius: 4px; }}
                    QProgressBar::chunk {{ background: {bar_color}; border-radius: 4px; }}
                """)
                jauge_l.addWidget(bar)
                g3.addWidget(jauge_w)

                # Reconductions
                nb_max   = int(ct.get('nb_reconductions_max') or ct.get('nombre_reconductions') or 0)
                nb_fait  = int(ct.get('nb_reconductions_faites') or 0)
                tacite   = "Oui" if ct.get('reconduction_tacite') else "Non"
                row3 = QHBoxLayout()
                row3.addWidget(_card("Reconduction tacite", tacite))
                row3.addWidget(_card("Reconductions", f"{nb_fait} / {nb_max} max"))
                row3.addWidget(_card("Statut contrat", ct.get('statut') or '—'))
                row3.addStretch()
                g3.addLayout(row3)
            else:
                g3.addWidget(QLabel("  Contrat introuvable"))
        else:
            lbl_no = QLabel("  ⚠️  Hors marché — aucun contrat rattaché")
            lbl_no.setStyleSheet("color: #f39c12; font-style: italic; padding: 8px;")
            g3.addWidget(lbl_no)

        grp3.setLayout(g3)
        self.body.addWidget(grp3)

        # ── Bloc 4 : Ligne budgétaire ────────────────────────────────────
        grp4 = self._section("📊 Ligne budgétaire")
        g4 = QVBoxLayout()
        lb_id = bc.get('ligne_budgetaire_id')
        lb_libelle = bc.get('ligne_libelle')
        lb_vote    = float(bc.get('ligne_vote') or 0)
        lb_engage  = float(bc.get('ligne_engage') or 0)
        lb_solde   = float(bc.get('ligne_solde') or 0)

        if lb_id:
            row_lb = QHBoxLayout()
            row_lb.addWidget(_card("Ligne", lb_libelle or '—', value_color='#3498db'))
            row_lb.addWidget(_card("Application", bc.get('application_nom') or '—'))
            row_lb.addWidget(_card("Voté",    f"{lb_vote:,.0f} €"))
            row_lb.addWidget(_card("Engagé",  f"{lb_engage:,.0f} €", value_color='#e67e22'))
            solde_lb_color = '#e74c3c' if lb_vote > 0 and lb_engage/lb_vote >= 0.9 else '#2ecc71'
            row_lb.addWidget(_card("Solde",   f"{lb_solde:,.0f} €", value_color=solde_lb_color))
            g4.addLayout(row_lb)

            pct_lb = int(lb_engage / lb_vote * 100) if lb_vote > 0 else 0
            bar_lb = QProgressBar()
            bar_lb.setRange(0, 100)
            bar_lb.setValue(min(pct_lb, 100))
            bar_lb.setFormat(f" {pct_lb}% engagé")
            bar_lb.setFixedHeight(16)
            bar_color_lb = '#e74c3c' if pct_lb >= 90 else ('#f39c12' if pct_lb >= 75 else '#2ecc71')
            bar_lb.setStyleSheet(f"""
                QProgressBar {{ background: #2c3e50; border-radius: 4px; color: white; font-size:10px; }}
                QProgressBar::chunk {{ background: {bar_color_lb}; border-radius: 4px; }}
            """)
            g4.addWidget(bar_lb)
        else:
            lbl = QLabel("  ⚠️  Aucune ligne budgétaire rattachée")
            lbl.setStyleSheet("color: #f39c12; font-style: italic; padding: 8px;")
            g4.addWidget(lbl)

        grp4.setLayout(g4)
        self.body.addWidget(grp4)

        # ── Bloc 5 : Autres BC du même contrat ──────────────────────────
        if contrat_id:
            grp5 = self._section("🔗 Autres BC sur ce contrat")
            g5 = QVBoxLayout()
            autres = self._get_autres_bc(contrat_id, self.bc_id)
            if autres:
                tbl = QTableWidget()
                tbl.setColumnCount(6)
                tbl.setHorizontalHeaderLabels(
                    ["N° BC", "Date", "Objet", "TTC", "Statut", "Imputé"])
                tbl.setRowCount(len(autres))
                hdr = tbl.horizontalHeader()
                hdr.setSectionResizeMode(QHeaderView.Interactive)
                hdr.setStretchLastSection(True)
                tbl.setColumnWidth(0, 130)
                tbl.setColumnWidth(1, 90)
                tbl.setColumnWidth(2, 200)
                tbl.setColumnWidth(3, 90)
                tbl.setColumnWidth(4, 90)
                tbl.setEditTriggers(QTableWidget.NoEditTriggers)
                tbl.setStyleSheet(
                    "QTableWidget { background: #2c3e50; color: #ecf0f1; }"
                    "QHeaderView::section { background: #34495e; color: #ecf0f1; font-weight: bold; }")
                tbl.setMaximumHeight(180)

                for r, b in enumerate(autres):
                    tbl.setItem(r, 0, QTableWidgetItem(b.get('numero_bc') or ''))
                    d = str(b.get('date_creation') or '')[:10]
                    tbl.setItem(r, 1, QTableWidgetItem(d))
                    tbl.setItem(r, 2, QTableWidgetItem(b.get('objet') or ''))
                    tbl.setItem(r, 3, QTableWidgetItem(
                        f"{float(b.get('montant_ttc') or 0):,.0f} €"))
                    st = b.get('statut', '')
                    st_item = QTableWidgetItem(st)
                    st_item.setBackground(QColor(STATUT_COLORS.get(st, ('#95a5a6','#fff'))[0]))
                    st_item.setForeground(QColor('#ffffff'))
                    tbl.setItem(r, 4, st_item)
                    tbl.setItem(r, 5, QTableWidgetItem(
                        "✅" if b.get('impute') else ""))
                g5.addWidget(tbl)

                # Total sur ce contrat
                total_contrat = sum(float(b.get('montant_ttc') or 0) for b in autres)
                total_contrat += ttc
                lbl_total = QLabel(
                    f"  Total BC sur ce contrat (dont celui-ci) : {total_contrat:,.0f} €")
                lbl_total.setStyleSheet("color: #bdc3c7; font-style: italic; padding: 4px;")
                g5.addWidget(lbl_total)
            else:
                lbl = QLabel("  Premier BC sur ce contrat")
                lbl.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 8px;")
                g5.addWidget(lbl)

            grp5.setLayout(g5)
            self.body.addWidget(grp5)

        # ── Bloc 6 : Journal d'audit ─────────────────────────────────────
        grp6 = self._section("📒 Journal d'audit")
        g6 = QVBoxLayout()
        logs = self._get_audit_logs()
        if logs:
            tbl_log = QTableWidget()
            tbl_log.setColumnCount(5)
            tbl_log.setHorizontalHeaderLabels(
                ["Date", "Action", "Détail", "Avant", "Après"])
            tbl_log.setRowCount(len(logs))
            hdr_l = tbl_log.horizontalHeader()
            hdr_l.setSectionResizeMode(QHeaderView.Interactive)
            hdr_l.setStretchLastSection(True)
            tbl_log.setColumnWidth(0, 140)
            tbl_log.setColumnWidth(1, 130)
            tbl_log.setColumnWidth(2, 220)
            tbl_log.setColumnWidth(3, 100)
            tbl_log.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl_log.setStyleSheet(
                "QTableWidget { background: #2c3e50; color: #ecf0f1; }"
                "QHeaderView::section { background: #34495e; color: #ecf0f1; font-weight: bold; }")
            tbl_log.setMaximumHeight(180)

            for r, lg in enumerate(logs):
                date_str = str(lg.get('date_action') or '')[:16].replace('T', ' ')
                tbl_log.setItem(r, 0, QTableWidgetItem(date_str))
                action_item = QTableWidgetItem(lg.get('action') or '')
                action_item.setForeground(QColor('#3498db'))
                tbl_log.setItem(r, 1, action_item)
                tbl_log.setItem(r, 2, QTableWidgetItem(lg.get('detail') or ''))
                tbl_log.setItem(r, 3, QTableWidgetItem(str(lg.get('valeur_avant') or '')))
                tbl_log.setItem(r, 4, QTableWidgetItem(str(lg.get('valeur_apres') or '')))
            g6.addWidget(tbl_log)
        else:
            lbl = QLabel("  Aucune entrée dans le journal pour ce BC")
            lbl.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 8px;")
            g6.addWidget(lbl)

        grp6.setLayout(g6)
        self.body.addWidget(grp6)

        self.body.addStretch()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _section(self, title):
        grp = QGroupBox(title)
        grp.setStyleSheet("""
            QGroupBox {
                color: #ecf0f1;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #2c3e50;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                background: #1e2f3f;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #3498db;
            }
        """)
        return grp

    def _get_fournisseur(self, fourn_id):
        if not fourn_id:
            return None
        try:
            from app.services.fournisseur_service import fournisseur_service
            rows = fournisseur_service.get_all()
            for f in rows:
                if f.get('id') == fourn_id:
                    return f
        except Exception:
            pass
        return None

    def _get_autres_bc(self, contrat_id, current_bc_id):
        if not self.bc_svc:
            return []
        try:
            tous = self.bc_svc.get_all_bons_commande(
                filters={'contrat_id': contrat_id})
            return [b for b in tous if b['id'] != current_bc_id]
        except Exception:
            return []

    def _get_audit_logs(self):
        if not self.audit_svc:
            return []
        try:
            return self.audit_svc.get_logs(objet_type='BC', objet_id=self.bc_id)
        except Exception:
            return []
