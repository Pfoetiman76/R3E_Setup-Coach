"""Dunkles QSS im Erscheinungsbild der Schwester-Apps (PitBoss R3E, R3E-Resultate).

Akzentfarbe: RaceRoom-Rot #e8212b. Deltas in der Setup-Liste werden
programmatisch gesetzt (positiv/grün etc.), nicht über das Stylesheet.
"""

DARK_QSS = """
QWidget {
    background-color: #1c1c1e;
    color: #e6e6e6;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow, QDialog {
    background-color: #1c1c1e;
}
QLabel {
    background: transparent;
}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #2a2a2e;
    border: 1px solid #3a3a40;
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: #e8212b;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #e8212b;
}
QPushButton {
    background-color: #2a2a2e;
    border: 1px solid #3a3a40;
    border-radius: 4px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #34343a;
    border-color: #e8212b;
}
QPushButton:pressed {
    background-color: #e8212b;
    color: #ffffff;
}
QPushButton:disabled {
    color: #6d6d72;
    border-color: #2a2a2e;
}
QTabWidget::pane {
    border: 1px solid #3a3a40;
    border-radius: 4px;
    top: -1px;
}
QTabBar::tab {
    background: #2a2a2e;
    color: #b8b8bd;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #1c1c1e;
    color: #ffffff;
    border-bottom: 2px solid #e8212b;
}
QGroupBox {
    border: 1px solid #3a3a40;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 6px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #e8212b;
}
QTableWidget {
    background-color: #2a2a2e;
    gridline-color: #3a3a40;
    border: 1px solid #3a3a40;
    border-radius: 4px;
}
QHeaderView::section {
    background-color: #232326;
    color: #b8b8bd;
    border: 0;
    border-bottom: 1px solid #3a3a40;
    padding: 6px;
}
QStatusBar {
    background: #232326;
    color: #b8b8bd;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #232326;
    width: 10px;
    height: 10px;
}
QScrollBar::handle {
    background: #3a3a40;
    border-radius: 5px;
}
"""


def apply_theme(app):
    app.setStyleSheet(DARK_QSS)
    return app
