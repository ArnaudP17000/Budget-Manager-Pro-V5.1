"""
Thèmes Clair/Sombre pour l'application.
"""

THEME_CLAIR = {
    "name": "Clair",
    "background": "#F5F7FA",
    "surface": "#FFFFFF",
    "primary": "#2C5F99",
    "secondary": "#5D87A1",
    "accent": "#E74C3C",
    "text": "#2C3E50",
    "text_secondary": "#7F8C8D",
    "border": "#BDC3C7",
    "success": "#27AE60",
    "warning": "#F39C12",
    "danger": "#E74C3C",
    "info": "#3498DB",
    "hover": "#ECF0F1",
}

THEME_SOMBRE = {
    "name": "Sombre",
    "background": "#1E1E2E",
    "surface": "#2B2B3C",
    "primary": "#5D87A1",
    "secondary": "#7FA3BD",
    "accent": "#E67E73",
    "text": "#E4E6EB",
    "text_secondary": "#A0A4B8",
    "border": "#3A3A4A",
    "success": "#4CAF50",
    "warning": "#FFA726",
    "danger": "#EF5350",
    "info": "#42A5F5",
    "hover": "#363647",
}

def get_stylesheet(theme):
    """Génère le stylesheet CSS pour le thème donné."""
    return f"""
    QWidget {{
        background-color: {theme['background']};
        color: {theme['text']};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
    }}
    
    QMainWindow, QDialog {{
        background-color: {theme['background']};
    }}
    
    QPushButton {{
        background-color: {theme['primary']};
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }}
    
    QPushButton:hover {{
        background-color: {theme['secondary']};
    }}
    
    QPushButton:pressed {{
        background-color: {theme['accent']};
    }}
    
    QPushButton:disabled {{
        background-color: {theme['border']};
        color: {theme['text_secondary']};
    }}
    
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {theme['surface']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        padding: 6px;
        border-radius: 4px;
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 2px solid {theme['primary']};
    }}
    
    QTableWidget, QTableView, QListWidget, QTreeWidget {{
        background-color: {theme['surface']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        gridline-color: {theme['border']};
        alternate-background-color: {theme['hover']};
    }}
    
    QTableWidget::item:selected, QTableView::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {theme['primary']};
        color: white;
    }}
    
    QHeaderView::section {{
        background-color: {theme['surface']};
        color: {theme['text']};
        padding: 8px;
        border: 1px solid {theme['border']};
        font-weight: bold;
    }}
    
    QTabWidget::pane {{
        border: 1px solid {theme['border']};
        background-color: {theme['surface']};
    }}
    
    QTabBar::tab {{
        background-color: {theme['surface']};
        color: {theme['text']};
        padding: 8px 16px;
        border: 1px solid {theme['border']};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {theme['primary']};
        color: white;
    }}
    
    QTabBar::tab:hover {{
        background-color: {theme['hover']};
    }}
    
    QMenuBar {{
        background-color: {theme['surface']};
        color: {theme['text']};
        border-bottom: 1px solid {theme['border']};
    }}
    
    QMenuBar::item:selected {{
        background-color: {theme['primary']};
        color: white;
    }}
    
    QMenu {{
        background-color: {theme['surface']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
    }}
    
    QMenu::item:selected {{
        background-color: {theme['primary']};
        color: white;
    }}
    
    QStatusBar {{
        background-color: {theme['surface']};
        color: {theme['text']};
        border-top: 1px solid {theme['border']};
    }}
    
    QToolBar {{
        background-color: {theme['surface']};
        border: 1px solid {theme['border']};
        spacing: 4px;
        padding: 4px;
    }}
    
    QGroupBox {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: bold;
    }}
    
    QGroupBox::title {{
        color: {theme['text']};
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }}
    
    QLabel {{
        color: {theme['text']};
    }}
    
    QCheckBox, QRadioButton {{
        color: {theme['text']};
        spacing: 8px;
    }}
    
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {theme['border']};
        background-color: {theme['surface']};
        border-radius: 3px;
    }}
    
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {theme['primary']};
        border-color: {theme['primary']};
    }}
    
    QScrollBar:vertical {{
        background-color: {theme['surface']};
        width: 12px;
        border: none;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {theme['border']};
        min-height: 20px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {theme['secondary']};
    }}
    
    QScrollBar:horizontal {{
        background-color: {theme['surface']};
        height: 12px;
        border: none;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {theme['border']};
        min-width: 20px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {theme['secondary']};
    }}
    
    QProgressBar {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        text-align: center;
        background-color: {theme['surface']};
    }}
    
    QProgressBar::chunk {{
        background-color: {theme['primary']};
        border-radius: 3px;
    }}
    
    QToolTip {{
        background-color: {theme['surface']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        padding: 4px;
    }}
    """

THEMES = {
    "Clair": THEME_CLAIR,
    "Sombre": THEME_SOMBRE,
}
