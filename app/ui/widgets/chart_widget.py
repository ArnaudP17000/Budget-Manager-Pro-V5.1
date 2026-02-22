"""
Widget Graphiques — Dashboard Avancé.

Deux graphiques :
  1. Répartition du budget consommé par projet (camembert)
  2. Charge ETP estimée vs réelle sur l'ensemble des projets (barres)

Utilise PyQtChart (déjà dans requirements.txt).
Fallback matplotlib si PyQtChart indisponible.
"""
import logging
from PyQt5.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QComboBox, QSizePolicy, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt, QTimer, QMargins
from PyQt5.QtGui import QFont, QColor
from .base_widget import BaseWidget

logger = logging.getLogger(__name__)

# ── Import PyQtChart ──────────────────────────────────────────────────────────
try:
    from PyQt5.QtChart import (
        QChart, QChartView, QPieSeries, QPieSlice,
        QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
    )
    from PyQt5.QtGui import QPainter
    CHART_AVAILABLE = True
except ImportError:
    CHART_AVAILABLE = False
    logger.warning("PyQtChart non disponible — installer PyQtChart>=5.15")


# ── Palette cohérente avec themes.py ─────────────────────────────────────────
PALETTE_PROJETS = [
    "#2C5F99", "#4D8EC4", "#1D8A4E", "#3DBA78",
    "#C97A00", "#F0A832", "#C0392B", "#E05548",
    "#7B5EA7", "#A88CC8", "#1A6BB5", "#5D87A1",
]


class ChartWidget(BaseWidget):
    """Widget affichant les graphiques budgétaires et ETP."""

    def __init__(self, parent=None):
        super().__init__(
            widget_id='graphiques',
            title='Graphiques',
            icon='📈',
            parent=parent
        )
        self.setup_content()

        # Rafraîchissement auto 5 min
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(300000)

        self.refresh_data()

    # ── UI ────────────────────────────────────────────────────────────────────

    def setup_content(self):
        """Construit l'interface : onglets Budget / ETP."""
        if not CHART_AVAILABLE:
            msg = QLabel("⚠️ PyQtChart non installé\n\npip install PyQtChart")
            msg.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(msg)
            return

        # Sélecteur de graphique
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Vue :"))
        self.chart_selector = QComboBox()
        self.chart_selector.addItems([
            "Répartition budget par projet",
            "Charge ETP par projet",
        ])
        self.chart_selector.currentIndexChanged.connect(self._switch_chart)
        selector_layout.addWidget(self.chart_selector)
        selector_layout.addStretch()
        self.content_layout.addLayout(selector_layout)

        # Stack des deux vues
        self.stack = QTabWidget()
        self.stack.tabBar().setVisible(False)  # Contrôlé par le combo

        # ── Onglet 1 : Camembert budget ───────────────────────────────────────
        self.pie_chart = QChart()
        self.pie_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.pie_chart.legend().setAlignment(Qt.AlignBottom)
        self.pie_chart.legend().setFont(QFont("Segoe UI", 8))
        self.pie_chart.setMargins(QMargins(4, 4, 4, 4))

        self.pie_view = QChartView(self.pie_chart)
        self.pie_view.setRenderHint(QPainter.Antialiasing)
        self.pie_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        pie_page = QWidget()
        QVBoxLayout(pie_page).addWidget(self.pie_view)
        self.stack.addTab(pie_page, "Budget")

        # ── Onglet 2 : Barres ETP ─────────────────────────────────────────────
        self.bar_chart = QChart()
        self.bar_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.bar_chart.legend().setAlignment(Qt.AlignBottom)
        self.bar_chart.legend().setFont(QFont("Segoe UI", 8))
        self.bar_chart.setMargins(QMargins(4, 4, 4, 4))

        self.bar_view = QChartView(self.bar_chart)
        self.bar_view.setRenderHint(QPainter.Antialiasing)
        self.bar_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        bar_page = QWidget()
        QVBoxLayout(bar_page).addWidget(self.bar_view)
        self.stack.addTab(bar_page, "ETP")

        self.content_layout.addWidget(self.stack)

    def _switch_chart(self, index):
        self.stack.setCurrentIndex(index)

    # ── Données ───────────────────────────────────────────────────────────────

    def refresh_data(self):
        """Charge les données et met à jour les deux graphiques."""
        if not CHART_AVAILABLE:
            return
        try:
            from app.services.database_service import db_service
            from app.services.theme_service import theme_service
            t = theme_service.get_current_theme()

            self._update_pie(db_service, t)
            self._update_bar(db_service, t)
            logger.info("✅ ChartWidget rafraîchi")

        except Exception as e:
            logger.error(f"Erreur ChartWidget: {e}")

    def _apply_chart_theme(self, chart, t):
        """Applique les couleurs du thème à un QChart."""
        bg = QColor(t['surface'])
        chart.setBackgroundBrush(bg)
        chart.setPlotAreaBackgroundVisible(False)
        title_font = QFont("Segoe UI", 10, QFont.Bold)
        chart.setTitleFont(title_font)
        chart.setTitleBrush(QColor(t['text']))

        # Légende
        legend = chart.legend()
        legend.setLabelColor(QColor(t['text']))
        legend.setBackgroundVisible(False)

        # Vue
        for view in [self.pie_view, self.bar_view]:
            view.setBackgroundBrush(QColor(t['background']))

    # ── Camembert : Budget par projet ─────────────────────────────────────────

    def _update_pie(self, db_service, t):
        """Graphique en secteurs : budget consommé par projet."""
        query = """
            SELECT
                nom,
                COALESCE(budget_consomme, 0) as consomme,
                COALESCE(budget_estime, 0)   as estime
            FROM projets
            WHERE statut NOT IN ('TERMINE', 'ANNULE')
              AND COALESCE(budget_estime, 0) > 0
            ORDER BY estime DESC
            LIMIT 8
        """
        rows = db_service.fetch_all(query)

        self.pie_chart.removeAllSeries()
        self._apply_chart_theme(self.pie_chart, t)
        self.pie_chart.setTitle("Répartition budget estimé par projet")

        if not rows:
            self.pie_chart.setTitle("Répartition budget — aucune donnée")
            return

        series = QPieSeries()
        series.setHoleSize(0.35)  # Donut

        for i, row in enumerate(rows):
            nom = row['nom'] if hasattr(row, '__getitem__') else row[0]
            estime = row['estime'] if hasattr(row, '__getitem__') else row[2]
            if estime <= 0:
                continue

            slc = series.append(f"{nom}\n{estime/1000:.0f} k€", estime)
            color = QColor(PALETTE_PROJETS[i % len(PALETTE_PROJETS)])
            slc.setColor(color)
            slc.setBorderColor(QColor(t['border']))
            slc.setLabelVisible(False)  # Labels trop chargés sur donut

        self.pie_chart.addSeries(series)

        # Légende colorée
        for i, slc in enumerate(series.slices()):
            slc.setColor(QColor(PALETTE_PROJETS[i % len(PALETTE_PROJETS)]))

    # ── Barres : Charge ETP par projet ────────────────────────────────────────

    def _update_bar(self, db_service, t):
        """
        Graphique en barres : charge ETP estimée vs réelle.
        ETP = heures / 1607  (jours ouvrés annuels × 7h)
        """
        query = """
            SELECT
                p.nom,
                COALESCE(SUM(t.estimation_heures), 0) as heures_estimees,
                COALESCE(SUM(t.heures_reelles), 0)    as heures_reelles
            FROM projets p
            LEFT JOIN taches t ON t.projet_id = p.id
                AND t.statut NOT IN ('ANNULE')
            WHERE p.statut NOT IN ('TERMINE', 'ANNULE')
            GROUP BY p.id, p.nom
            HAVING heures_estimees > 0 OR heures_reelles > 0
            ORDER BY heures_estimees DESC
            LIMIT 8
        """
        rows = db_service.fetch_all(query)

        self.bar_chart.removeAllSeries()
        # Retirer les axes précédents
        for ax in self.bar_chart.axes():
            self.bar_chart.removeAxis(ax)

        self._apply_chart_theme(self.bar_chart, t)
        self.bar_chart.setTitle("Charge ETP par projet (estimé vs réel)")

        if not rows:
            self.bar_chart.setTitle("Charge ETP — aucune donnée (renseignez estimation_heures dans les tâches)")
            return

        HEURES_ETP = 1607.0  # heures/an = 1 ETP

        set_estime = QBarSet("ETP estimé")
        set_estime.setColor(QColor(t.get('primary', '#2C5F99')))
        set_estime.setBorderColor(QColor(t.get('border', '#D8DDE8')))

        set_reel = QBarSet("ETP réel")
        set_reel.setColor(QColor(t.get('warning', '#C97A00')))
        set_reel.setBorderColor(QColor(t.get('border', '#D8DDE8')))

        categories = []
        max_val = 0.0

        for row in rows:
            nom = row['nom'] if hasattr(row, '__getitem__') else row[0]
            h_est = row['heures_estimees'] if hasattr(row, '__getitem__') else row[1]
            h_reel = row['heures_reelles'] if hasattr(row, '__getitem__') else row[2]

            etp_est  = round(h_est  / HEURES_ETP, 2)
            etp_reel = round(h_reel / HEURES_ETP, 2)

            set_estime.append(etp_est)
            set_reel.append(etp_reel)

            # Nom court (max 12 cars)
            short = nom[:12] + "…" if len(nom) > 12 else nom
            categories.append(short)
            max_val = max(max_val, etp_est, etp_reel)

        series = QBarSeries()
        series.append(set_estime)
        series.append(set_reel)
        self.bar_chart.addSeries(series)

        # Axe X — projets
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor(t['text']))
        axis_x.setGridLineColor(QColor(t['border']))
        self.bar_chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Axe Y — ETP
        axis_y = QValueAxis()
        axis_y.setRange(0, max(max_val * 1.15, 0.5))
        axis_y.setTitleText("ETP")
        axis_y.setTitleFont(QFont("Segoe UI", 8))
        axis_y.setTitleBrush(QColor(t['text_secondary']))
        axis_y.setLabelsColor(QColor(t['text']))
        axis_y.setGridLineColor(QColor(t['border']))
        axis_y.setTickCount(6)
        self.bar_chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
