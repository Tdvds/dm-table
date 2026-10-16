"""Dark medieval look: leather browns, gold trim, parchment text, serif type."""
import os, tempfile
from PySide6.QtGui import QColor, QPalette

GOLD, GOLD_DIM, CRIMSON, PARCHMENT, INK = "#e0b84f", "#8b6b3d", "#7a2020", "#e8d9b5", "#0f0b08"
SERIF = '"Palatino Linotype", "Book Antiqua", Palatino, "URW Palladio L", P052, "TeX Gyre Pagella", Georgia, serif'

QSS = """
* { font-family: @SERIF; font-size: 10.5pt; color: @PARCH; }
QMainWindow, QWidget { background: #15100c; }
QLabel, QCheckBox, QRadioButton, QWidget#row { background: transparent; }
QDockWidget { titlebar-close-icon: none; }
QDockWidget::title { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3d2c1d, stop:1 #221810);
    padding: 6px; border-bottom: 1px solid @GOLDDIM; text-align: center; }
QGroupBox { border: 1px solid #6b5230; border-radius: 6px; margin-top: 14px; padding: 10px 6px 6px; background: #1c1510; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: @GOLD; font-weight: bold; letter-spacing: 1px; }
QPushButton, QToolButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #4a3523, stop:1 #2a1e15);
    border: 1px solid @GOLDDIM; border-radius: 4px; padding: 5px 9px; }
QPushButton:hover, QToolButton:hover { border-color: @GOLD; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5e432c, stop:1 #35261a); }
QPushButton:pressed, QToolButton:checked, QToolButton:pressed { background: @CRIMSON; border-color: @GOLD; }
QPushButton:disabled { color: #6b5a44; border-color: #3a2c1e; }
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTableWidget {
    background: @INK; border: 1px solid #5a4428; border-radius: 3px; padding: 2px; selection-background-color: @CRIMSON; }
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button { width: 16px; border-left: 1px solid #5a4428; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(@UP); width: 8px; height: 6px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QComboBox::down-arrow { image: url(@DOWN); width: 8px; height: 6px; }
QComboBox::drop-down { border-left: 1px solid #5a4428; width: 18px; }
QComboBox QAbstractItemView { background: #1c1510; border: 1px solid @GOLDDIM; selection-background-color: @CRIMSON; }
QTableWidget { gridline-color: #3a2c1e; }
QHeaderView::section { background: #2a1e15; color: @GOLD; border: 0; border-right: 1px solid #5a4428; padding: 4px; }
QTabBar::tab { background: #221810; border: 1px solid #5a4428; padding: 6px 10px; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #3d2c1d; color: @GOLD; border-color: @GOLDDIM; }
QTabWidget::pane { border: 1px solid #5a4428; top: -1px; }
QTabWidget#pages > QTabBar::tab { padding: 8px 22px; font-size: 11.5pt; min-width: 110px; }
QTabWidget#pages > QTabBar { background: #1c1510; }
QSlider::groove:horizontal { height: 6px; background: @INK; border: 1px solid #5a4428; border-radius: 3px; }
QSlider::sub-page:horizontal { background: @CRIMSON; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; background: @GOLD; border: 1px solid #6b5230; border-radius: 7px; }
QToolBar { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2e2116, stop:1 #1c1510); border-bottom: 1px solid @GOLDDIM; spacing: 4px; padding: 4px; }
QMenuBar { background: #1c1510; } QMenuBar::item:selected { background: @CRIMSON; }
QMenu { background: #1c1510; border: 1px solid @GOLDDIM; } QMenu::item { padding: 5px 22px; } QMenu::item:selected { background: @CRIMSON; }
QScrollBar:vertical { background: #15100c; width: 11px; } QScrollBar:horizontal { background: #15100c; height: 11px; }
QScrollBar::handle { background: #5a4428; border-radius: 4px; min-height: 20px; min-width: 20px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QToolTip { background: @PARCH; color: #2a1d10; border: 1px solid @GOLDDIM; padding: 4px; }
QStatusBar { background: #1c1510; color: @GOLD; }
QLabel#title { font-size: 15pt; color: @GOLD; }
QLabel#hint { color: #a8916b; font-style: italic; }
QSplitter::handle { background: #3a2c1e; }
"""


def apply(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, col in ((QPalette.Window, "#15100c"), (QPalette.Base, INK), (QPalette.AlternateBase, "#1c1510"),
                      (QPalette.Text, PARCHMENT), (QPalette.WindowText, PARCHMENT), (QPalette.Button, "#2a1e15"),
                      (QPalette.ButtonText, PARCHMENT), (QPalette.Highlight, CRIMSON), (QPalette.HighlightedText, PARCHMENT),
                      (QPalette.ToolTipBase, PARCHMENT), (QPalette.ToolTipText, "#2a1d10"), (QPalette.PlaceholderText, "#7d6a4f")):
        pal.setColor(role, QColor(col))
    app.setPalette(pal)
    arrows = {}
    for name, pts in (("UP", "0,6 4,0 8,6"), ("DOWN", "0,0 8,0 4,6")):  # stylesheets need image files for arrows
        path = os.path.join(tempfile.gettempdir(), f"dmtable_{name.lower()}.svg")
        with open(path, "w") as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6"><polygon points="{pts}" fill="{GOLD}"/></svg>')
        arrows[name] = path.replace("\\", "/")
    app.setStyleSheet(QSS.replace("@UP", arrows["UP"]).replace("@DOWN", arrows["DOWN"]).replace("@SERIF", SERIF).replace("@PARCH", PARCHMENT).replace("@GOLDDIM", GOLD_DIM)
                      .replace("@GOLD", GOLD).replace("@CRIMSON", CRIMSON).replace("@INK", INK))
