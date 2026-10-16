"""Start screen: choose The Table (the VTT) or Map Forge. Both run in this one process, so a single exe holds everything."""
import sys
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from . import icons, theme

CARD = """
QPushButton#card { text-align: left; padding: 22px; border: 2px solid #8b6b3d; border-radius: 10px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3a2a1c, stop:1 #1c1510); font-size: 12pt; }
QPushButton#card:hover { border-color: #e0b84f; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #4d3824, stop:1 #241a12); }
QPushButton#card:pressed { background: #7a2020; }
"""


class Launcher(QWidget):
    def __init__(self, data_dir=None, table_kwargs=None):
        super().__init__()
        from .app import BASE
        self.data_dir = data_dir or BASE
        self.table_kwargs = table_kwargs or {}
        self.table = self.forge = self.brewery = None
        self.setWindowTitle("Dungeon Master's Table")
        self.setWindowIcon(icons.icon("launcher"))
        self.setFixedSize(1120, 560)
        self.setStyleSheet(CARD)
        v = QVBoxLayout(self)
        v.setContentsMargins(40, 34, 40, 26)
        title = QLabel("⚜  Dungeon Master's Table  ⚜")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26pt; color: #e0b84f; letter-spacing: 2px; background: transparent;")
        sub = QLabel("Choose your path, Dungeon Master")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 12pt; color: #a8916b; font-style: italic; background: transparent;")
        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(26)
        row = QHBoxLayout()
        row.setSpacing(24)
        for kind, name, text, fn in (
                ("table", "The Table", "Run your session: battle maps on the\nplayers' screen, fog of war, lighting,\nweather, initiative, loot and the journal.", self.open_table),
                ("forge", "Map Forge", "Build dungeons, caves and wilds:\nstamp chunks, paint terrain, or let the\nforge generate a map for you.", self.open_forge),
                ("brewery", "Brewery", "Brew your own items, enemies and\nForge objects. Everything you make shows\nup in the Table and Map Forge.", self.open_brewery)):
            b = QPushButton()
            b.setObjectName("card")
            b.setMinimumHeight(270)
            col = QVBoxLayout(b)
            for w, style in ((QLabel(), ""), (QLabel(name), "font-size: 16pt; color: #e0b84f;"),
                             (QLabel(text.replace("\n", " ")), "font-size: 10.5pt; color: #e8d9b5;")):
                w.setAlignment(Qt.AlignCenter)
                w.setWordWrap(True)
                w.setStyleSheet(style + " background: transparent;")
                w.setAttribute(Qt.WA_TransparentForMouseEvents)  # clicks go to the card button
                col.addWidget(w)
            col.itemAt(0).widget().setPixmap(icons.icon(kind).pixmap(QSize(96, 96)))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        v.addLayout(row)
        v.addStretch()
        quit_btn = QPushButton("Leave the tavern")
        quit_btn.clicked.connect(self.close)
        foot = QHBoxLayout()
        foot.addStretch()
        foot.addWidget(quit_btn)
        v.addLayout(foot)

    def paintEvent(self, e):  # parchment-dark backdrop with a gold frame
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#24190f"))
        g.setColorAt(1, QColor("#0f0b08"))
        p.fillRect(self.rect(), g)
        p.setPen(QPen(QColor("#8b6b3d"), 2))
        p.drawRect(self.rect().adjusted(10, 10, -11, -11))
        p.setPen(QPen(QColor("#e0b84f"), 1))
        p.drawRect(self.rect().adjusted(16, 16, -17, -17))

    def open_table(self):
        if self.table is None:
            from .app import App
            self.table = App(**self.table_kwargs)
            self.table.closed.connect(self.table_closed)
            self.table.launcher = self  # lets the table open the Brewery
            self.table.show()
            self.table.show_display()
            self.table.apply_view()
        self.table.raise_()
        self.table.activateWindow()
        self.hide()
        return self.table

    def open_forge(self):
        if self.forge is None:
            from .forge import Forge
            self.forge = Forge(self, self.data_dir)
            self.forge.closed.connect(self.forge_closed)
            self.forge.show()
        self.forge.raise_()
        self.forge.activateWindow()
        self.hide()
        return self.forge

    def open_brewery(self):
        if self.brewery is None:
            from .brewery import Brewery
            self.brewery = Brewery(self)
            self.brewery.closed.connect(self.brewery_closed)
            self.brewery.saved.connect(self.brew_changed)
            self.brewery.show()
        self.brewery.raise_()
        self.brewery.activateWindow()
        self.hide()
        return self.brewery

    def brew_changed(self):
        for w in (self.table, self.forge):  # keep the other open apps in step with the library
            if w is not None:
                w.brew_changed()

    def brewery_closed(self):
        self.brewery = None
        self.back()

    def send_to_table(self, png, cell, props):
        self.open_table().receive_map(png, cell, props)

    def table_closed(self):
        self.table = None
        self.back()

    def forge_closed(self):
        self.forge = None
        self.back()

    def back(self):
        if self.table is None and self.forge is None and self.brewery is None:
            self.show()

    def closeEvent(self, e):
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dungeon Master's Table")
    icons.windows_taskbar_id()
    app.setWindowIcon(icons.icon("launcher"))
    app.setQuitOnLastWindowClosed(False)  # the launcher comes back when an app closes
    theme.apply(app)
    w = Launcher()
    if "--table" in sys.argv:
        w.open_table()
    elif "--forge" in sys.argv:
        w.open_forge()
    elif "--brewery" in sys.argv:
        w.open_brewery()
    else:
        w.show()
    sys.exit(app.exec())
