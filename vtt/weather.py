"""Screen-space weather particles, drawn over the player display (and its preview in the admin window)."""
import math, random
from PySide6.QtCore import QLineF, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient

TYPES = ["None", "Rain", "Storm", "Snow", "Fog", "Ash", "Magic", "Sandstorm"]
COUNTS = {"Rain": 450, "Storm": 700, "Snow": 320, "Fog": 16, "Ash": 260, "Magic": 140, "Sandstorm": 420}
WIND = {"Rain": 0.5, "Storm": 0.8, "Snow": 0.12, "Fog": 0.03, "Ash": 0.1, "Magic": 0.03, "Sandstorm": 0.6}
ENVIRONMENTS = {"Clear skies": ("None", 0.5), "Rainy forest": ("Rain", 0.5), "Thunderstorm": ("Storm", 0.9),
                "Snowy peaks": ("Snow", 0.7), "Misty swamp": ("Fog", 0.7), "Volcanic waste": ("Ash", 0.7),
                "Feywild": ("Magic", 0.6), "Desert": ("Sandstorm", 0.8)}
MAGIC = [(180, 90, 255), (80, 200, 255), (255, 210, 90)]


class Weather:
    def __init__(self):
        self.kind, self.intensity, self.wind = "None", 0.6, 0.2
        self.parts, self.flash, self.t = [], 0.0, 0.0

    def set(self, kind):
        self.kind = kind if kind in TYPES else "None"
        self.parts = []

    def spawn(self):
        r, k = random.random, self.kind
        x, y, ph = r(), r(), r() * 6.283
        if k in ("Rain", "Storm"):
            return [x, y, 0, 1.3 + r() * 0.6, 1 + r(), ph]
        if k == "Snow":
            return [x, y, 0, 0.05 + r() * 0.08, 1.5 + r() * 3, ph]
        if k == "Fog":
            return [x, y, 0.01 + r() * 0.02, 0, 0.15 + r() * 0.25, ph]
        if k == "Ash":
            return [x, y, 0, 0.03 + r() * 0.05, 1 + r() * 2.2, ph if r() > 0.12 else -1]  # phase -1 = glowing ember
        if k == "Magic":
            return [x, y, 0, -(0.015 + r() * 0.05), 2 + r() * 4, ph]
        return [x, y, 0.7 + r() * 0.7, (r() - 0.5) * 0.1, 1 + r() * 2, ph]  # sandstorm

    def vx(self, q):
        v = q[2] + self.wind * WIND[self.kind]
        if self.kind in ("Snow", "Ash", "Magic"):
            v += 0.02 * math.sin(self.t * 1.5 + q[5])
        return v

    def step(self, dt):
        if self.kind == "None":
            return
        self.t += dt
        want = int(COUNTS[self.kind] * self.intensity)
        while len(self.parts) < want:
            self.parts.append(self.spawn())
        del self.parts[want:]
        m = 0.4 if self.kind == "Fog" else 0.03  # wrap margin so big fog banks drift fully off-screen
        for q in self.parts:
            q[0] = (q[0] + self.vx(q) * dt + m) % (1 + 2 * m) - m
            q[1] = (q[1] + q[3] * dt + m) % (1 + 2 * m) - m
        if self.kind == "Storm" and random.random() < dt * 0.15 * self.intensity:
            self.flash = 1.0
        self.flash = max(0.0, self.flash - dt * 2.5)

    def paint(self, p, rect):
        k = self.kind
        if k == "None":
            return
        p.save()
        p.setClipRect(rect)
        p.setRenderHint(QPainter.Antialiasing)
        W, H, ox, oy = rect.width(), rect.height(), rect.x(), rect.y()
        s = H / 1080
        P = lambda q: QPointF(ox + q[0] * W, oy + q[1] * H)
        a = self.intensity
        if k in ("Rain", "Storm"):
            p.setPen(QPen(QColor(170, 190, 230, 150), max(1.0, 1.3 * s)))
            p.drawLines([QLineF(P(q), P(q) - QPointF(self.vx(q) * W, q[3] * H) * 0.02) for q in self.parts])
            if self.flash > 0:
                p.fillRect(rect, QColor(255, 255, 255, int(170 * self.flash)))
        elif k == "Snow":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 210))
            for q in self.parts:
                p.drawEllipse(P(q), q[4] * s, q[4] * s)
        elif k == "Fog":
            p.fillRect(rect, QColor(170, 175, 185, int(45 * a)))
            p.setPen(Qt.NoPen)
            for q in self.parts:
                g = QRadialGradient(P(q), q[4] * W)
                g.setColorAt(0, QColor(205, 205, 215, int(80 * a)))
                g.setColorAt(1, QColor(205, 205, 215, 0))
                p.setBrush(g)
                p.drawEllipse(P(q), q[4] * W, q[4] * W * 0.6)
        elif k == "Ash":
            p.fillRect(rect, QColor(60, 40, 30, int(55 * a)))
            p.setPen(Qt.NoPen)
            for q in self.parts:
                ember = q[5] < 0
                p.setBrush(QColor(255, 130, 40, 230) if ember else QColor(120, 115, 110, 190))
                r = q[4] * s * (1.4 if ember else 1)
                p.drawEllipse(P(q), r, r)
        elif k == "Magic":
            p.setCompositionMode(QPainter.CompositionMode_Plus)
            p.setPen(Qt.NoPen)
            for i, q in enumerate(self.parts):
                c = QColor(*MAGIC[i % 3], int(200 * (0.5 + 0.5 * math.sin(self.t * 3 + q[5]))))
                g = QRadialGradient(P(q), q[4] * s * 3)
                g.setColorAt(0, c)
                g.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
                p.setBrush(g)
                p.drawEllipse(P(q), q[4] * s * 3, q[4] * s * 3)
        else:  # sandstorm
            p.fillRect(rect, QColor(194, 160, 100, int(90 * a)))
            p.setPen(QPen(QColor(215, 185, 125, 150), 1.5 * s))
            p.drawLines([QLineF(P(q), P(q) - QPointF(self.vx(q) * W * 0.03, 0)) for q in self.parts])
        p.restore()
