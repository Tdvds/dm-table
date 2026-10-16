"""Draws Map Forge maps: textured terrain with automatic walls, shadows and edges, plus top-down objects.
Everything is painted in code, so there are no tile images to ship or license."""
import math
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
from .forge_gen import CAVE, DIRT, FLOOR, GRASS, LAVA, LIQUID, N4, N8, PIT, SAND, VOID, WATER, WOOD, MapData

BASE = {FLOOR: "#6e675d", CAVE: "#5e5145", WATER: "#2c5a78", LAVA: "#c2410c", GRASS: "#4d6e31", DIRT: "#7d5f3d",
        WOOD: "#7a5431", PIT: "#0d0a08", SAND: "#c8b07a"}
CUSTOM = {}  # Brewery object id -> spec; apps fill this from the shared library
_IMAGES = {}
BUILT = {FLOOR, WOOD}  # rock next to these is drawn as masonry, otherwise as natural rock
BLEED = {GRASS: 3, CAVE: 3, SAND: 2, DIRT: 2, WATER: 0, LAVA: 0, PIT: 0}  # higher creeps over lower at edges


def rnd(x, y, seed, k=0):
    """Stable pseudo-random 0..1 per cell, so the map looks the same every time it is drawn."""
    n = (x * 374761393 + y * 668265263 + seed * 1442695041 + k * 2654435761) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535


def shade(col, f):
    c = QColor(col)
    return QColor(min(255, max(0, int(c.red() * f))), min(255, max(0, int(c.green() * f))), min(255, max(0, int(c.blue() * f))), c.alpha())


def terrain(p, m, x, y, cs):
    r, t, s = QRectF(x * cs, y * cs, cs, cs), m.t[y][x], m.seed
    R = lambda k: rnd(x, y, s, k)
    p.save()
    p.setClipRect(r)
    p.setPen(Qt.NoPen)
    if t == VOID:
        near = {m.get(x + dx, y + dy) for dx, dy in N8} - {VOID}
        if near & BUILT:  # masonry wall
            p.fillRect(r, QColor("#3d362f"))
            p.setPen(QPen(QColor("#29231e"), max(1.0, cs * 0.05)))
            for row in range(3):
                yy = r.y() + row * cs / 3
                p.drawLine(QLineF(r.x(), yy, r.right(), yy))
                off = (cs / 4) if (y * 3 + row) % 2 else (cs * 0.75)
                p.drawLine(QLineF(r.x() + off, yy, r.x() + off, yy + cs / 3))
        elif near:  # natural rock face
            p.fillRect(r, shade("#3a332c", 0.9 + R(1) * 0.2))
            for k in range(3):
                p.setBrush(QColor(255, 255, 255, 14) if R(k + 5) > 0.5 else QColor(0, 0, 0, 40))
                p.drawEllipse(QPointF(r.x() + R(k + 2) * cs, r.y() + R(k + 9) * cs), cs * 0.25, cs * 0.18)
        else:
            p.fillRect(r, QColor("#15110e"))
        p.restore()
        return
    base = shade(BASE[t], 0.92 + R(0) * 0.16)
    p.fillRect(r, base)
    if t == FLOOR:  # flagstones
        h = cs / 2
        for i in range(2):
            for j in range(2):
                p.fillRect(QRectF(r.x() + i * h, r.y() + j * h, h, h), shade(base, 0.9 + rnd(x * 2 + i, y * 2 + j, s, 1) * 0.2))
        p.setPen(QPen(QColor(0, 0, 0, 80), max(1.0, cs * 0.03)))
        p.drawLine(QLineF(r.x() + h, r.y(), r.x() + h, r.bottom()))
        p.drawLine(QLineF(r.x(), r.y() + h, r.right(), r.y() + h))
        p.drawRect(r)
        if R(3) < 0.15:
            p.setPen(QPen(QColor(0, 0, 0, 90), max(1.0, cs * 0.02)))
            a = QPointF(r.x() + R(4) * cs, r.y() + R(5) * cs)
            p.drawPolyline(QPolygonF([a, a + QPointF(cs * 0.15, cs * 0.1), a + QPointF(cs * 0.22, cs * 0.25)]))
    elif t == WOOD:
        for i in range(4):
            pr = QRectF(r.x(), r.y() + i * cs / 4, cs, cs / 4)
            p.fillRect(pr, shade(base, 0.88 + rnd(x, y * 4 + i, s, 2) * 0.24))
            p.setPen(QPen(QColor(40, 22, 10, 120), max(1.0, cs * 0.025)))
            p.drawLine(pr.bottomLeft(), pr.bottomRight())
            seam = r.x() + ((rnd(x, y * 4 + i, s, 3) * cs) if (x + i) % 2 else cs)
            p.drawLine(QLineF(seam, pr.y(), seam, pr.bottom()))
    elif t in (CAVE, DIRT, SAND):
        for k in range(5 if t == CAVE else 6):
            p.setBrush(QColor(255, 255, 255, 18) if R(k + 10) > 0.5 else QColor(0, 0, 0, 45))
            rad = cs * (0.06 + 0.16 * R(k + 20)) if t == CAVE else cs * 0.05
            p.drawEllipse(QPointF(r.x() + R(k + 30) * cs, r.y() + R(k + 40) * cs), rad, rad * 0.8)
    elif t == GRASS:
        for k in range(9):
            p.setPen(QPen(shade(base, 1.25 if R(k + 50) > 0.5 else 0.7), max(1.0, cs * 0.03)))
            a = QPointF(r.x() + R(k + 60) * cs, r.y() + R(k + 70) * cs)
            p.drawLine(a, a + QPointF(cs * 0.03, -cs * 0.09))
    elif t == WATER:
        p.setPen(QPen(QColor(190, 225, 240, 70), max(1.0, cs * 0.035)))
        p.setBrush(Qt.NoBrush)
        for k in range(2):
            c = QPointF(r.x() + R(k + 80) * cs, r.y() + R(k + 85) * cs)
            p.drawArc(QRectF(c.x() - cs * 0.2, c.y() - cs * 0.08, cs * 0.4, cs * 0.16), 0, 180 * 16)
    elif t == LAVA:
        g = QRadialGradient(QPointF(r.x() + R(90) * cs, r.y() + R(91) * cs), cs * 0.7)
        g.setColorAt(0, QColor("#fde047"))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(r, g)
        p.setBrush(QColor(60, 20, 8, 200))
        for k in range(2):
            p.drawEllipse(QPointF(r.x() + R(k + 92) * cs, r.y() + R(k + 95) * cs), cs * 0.18, cs * 0.12)
    elif t == PIT:
        g = QRadialGradient(r.center(), cs * 0.8)
        g.setColorAt(0, QColor(0, 0, 0))
        g.setColorAt(1, QColor("#2a211b"))
        p.fillRect(r, g)
    rough = t not in BUILT
    for (dx, dy) in N4:
        n = m.get(x + dx, y + dy)
        edge = QLineF(*((r.left(), r.top(), r.right(), r.top()) if dy < 0 else (r.right(), r.top(), r.right(), r.bottom()) if dx > 0
                        else (r.left(), r.bottom(), r.right(), r.bottom()) if dy > 0 else (r.left(), r.top(), r.left(), r.bottom())))
        if n == VOID and rough:  # ragged natural edge: rock bulges into the cell
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#3a332c"))
            for k in range(3):
                u = (k + 0.2 + 0.6 * rnd(x * 4 + dx, y * 4 + dy, s, k + 100)) / 3
                c = edge.pointAt(u)
                rad = cs * (0.12 + 0.14 * rnd(x, y, s, k + dx * 7 + dy * 13 + 110))
                p.drawEllipse(c, rad, rad)
        elif n == VOID:  # crisp wall line
            p.setPen(QPen(QColor(0, 0, 0, 190), max(1.5, cs * 0.06)))
            p.drawLine(edge)
        else:
            if t in LIQUID and n != t:  # shoreline / crust / chasm lip
                col = {WATER: QColor(215, 235, 240, 150), LAVA: QColor(40, 15, 5, 220), PIT: QColor(90, 75, 60, 255)}[t]
                p.setPen(QPen(col, max(1.0, cs * 0.07)))
                p.drawLine(edge)
            if BLEED.get(n, -1) > BLEED.get(t, 9):  # natural ground creeps raggedly over paths and shores
                p.setPen(Qt.NoPen)
                p.setBrush(shade(BASE[n], 0.95))
                for k in range(3):
                    c = edge.pointAt((k + 0.5) / 3)
                    rad = cs * (0.08 + 0.08 * rnd(x, y, s, k + dx * 3 + dy * 5 + 120))
                    p.drawEllipse(c, rad, rad)
    for (dx, dy), vertical in (((0, -1), False), ((-1, 0), True)):  # light from the bottom right: walls cast shadow up/left
        if m.get(x + dx, y + dy) == VOID:
            g = QLinearGradient(r.topLeft(), r.topLeft() + (QPointF(cs * 0.35, 0) if vertical else QPointF(0, cs * 0.35)))
            g.setColorAt(0, QColor(0, 0, 0, 130))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(QRectF(r.x(), r.y(), cs * 0.35 if vertical else cs, cs if vertical else cs * 0.35), g)
    p.restore()


def drop(p, rect, cs):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawEllipse(rect.translated(cs * 0.07, cs * 0.07))


def obj(p, kind, r, vertical=False, opened=False, seed=0):
    """Top-down drawing of an object in cell rect r."""
    cs, c = r.width(), r.center()
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    pen = lambda col, w=0.04: QPen(QColor(col), max(1.0, cs * w))
    if kind.startswith("brew:"):
        custom(p, CUSTOM.get(kind[5:]), r, vertical, opened, seed)
    elif kind == "door":
        p.translate(c)
        if vertical:
            p.rotate(90)
        p.translate(-c)
        th = cs * 0.26
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2d2722"))
        for x in (r.x(), r.right() - cs * 0.12):  # stone jambs
            p.drawRect(QRectF(x, c.y() - th * 0.7, cs * 0.12, th * 1.4))
        plank = QRectF(r.x() + cs * 0.1, c.y() - th / 2, cs * 0.8, th)
        if opened:  # swung open against the jamb
            plank = QRectF(r.x() + cs * 0.1, c.y() - cs * 0.02, th, cs * 0.8)
        p.setBrush(QColor("#7a4a22"))
        p.setPen(pen("#2b1a0c"))
        p.drawRect(plank)
        p.setPen(pen("#2b2b2b", 0.05))
        if opened:
            p.drawLine(QLineF(plank.left(), plank.top() + plank.height() * 0.3, plank.right(), plank.top() + plank.height() * 0.3))
        else:
            for f in (0.25, 0.75):
                p.drawLine(QLineF(plank.left() + plank.width() * f, plank.top(), plank.left() + plank.width() * f, plank.bottom()))
            p.setBrush(QColor("#d4a72c"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(plank.right() - cs * 0.12, c.y()), cs * 0.035, cs * 0.035)
    elif kind == "chest":
        box = QRectF(c.x() - cs * 0.33, c.y() - cs * 0.22, cs * 0.66, cs * 0.46)
        drop(p, box, cs)
        p.setBrush(QColor("#6b3f1d"))
        p.setPen(pen("#d4a72c", 0.05))
        p.drawRect(box)
        if opened:
            p.setBrush(QColor("#3a2210"))
            p.drawRect(box.adjusted(cs * 0.05, cs * 0.05, -cs * 0.05, -cs * 0.05))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#f2c94c"))
            for k in range(6):
                p.drawEllipse(QPointF(box.x() + cs * (0.12 + 0.08 * k), box.center().y() + cs * 0.05 * math.sin(k * 2)), cs * 0.05, cs * 0.05)
        else:
            p.drawLine(QLineF(box.left(), box.top() + box.height() * 0.38, box.right(), box.top() + box.height() * 0.38))
            p.setBrush(QColor("#d4a72c"))
            p.drawRect(QRectF(c.x() - cs * 0.04, box.top() + box.height() * 0.3, cs * 0.08, cs * 0.1))
    elif kind == "pillar":
        b = QRectF(c.x() - cs * 0.36, c.y() - cs * 0.36, cs * 0.72, cs * 0.72)
        drop(p, b, cs)
        g = QRadialGradient(c - QPointF(cs * 0.12, cs * 0.12), cs * 0.45)
        g.setColorAt(0, QColor("#b9b2a6"))
        g.setColorAt(1, QColor("#5e584f"))
        p.setBrush(g)
        p.setPen(pen("#2d2925"))
        p.drawEllipse(b)
    elif kind == "statue":
        base = QRectF(c.x() - cs * 0.35, c.y() - cs * 0.35, cs * 0.7, cs * 0.7)
        drop(p, base, cs)
        p.setBrush(QColor("#6f6a62"))
        p.setPen(pen("#2d2925"))
        p.drawRect(base)
        p.setBrush(QColor("#a7a196"))
        p.drawEllipse(QRectF(c.x() - cs * 0.24, c.y() - cs * 0.08, cs * 0.48, cs * 0.26))
        p.drawEllipse(c - QPointF(0, cs * 0.12), cs * 0.12, cs * 0.12)
    elif kind == "altar":
        b = QRectF(c.x() - cs * 0.4, c.y() - cs * 0.22, cs * 0.8, cs * 0.44)
        drop(p, b, cs)
        p.setBrush(QColor("#8a8178"))
        p.setPen(pen("#3a352f"))
        p.drawRect(b)
        p.fillRect(QRectF(c.x() - cs * 0.1, b.top(), cs * 0.2, b.height()), QColor("#8b1a1a"))
        for dx in (-0.28, 0.28):
            g = QRadialGradient(c + QPointF(cs * dx, 0), cs * 0.12)
            g.setColorAt(0, QColor(255, 220, 120, 255))
            g.setColorAt(1, QColor(255, 180, 60, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(c + QPointF(cs * dx, 0), cs * 0.12, cs * 0.12)
    elif kind == "throne":
        p.setPen(pen("#4a3510"))
        p.setBrush(QColor("#c9a227"))
        p.drawRect(QRectF(c.x() - cs * 0.32, c.y() - cs * 0.38, cs * 0.64, cs * 0.22))
        p.drawRect(QRectF(c.x() - cs * 0.3, c.y() - cs * 0.16, cs * 0.6, cs * 0.5))
        p.setBrush(QColor("#7a2020"))
        p.drawRect(QRectF(c.x() - cs * 0.2, c.y() - cs * 0.1, cs * 0.4, cs * 0.36))
    elif kind == "barrel":
        b = QRectF(c.x() - cs * 0.3, c.y() - cs * 0.3, cs * 0.6, cs * 0.6)
        drop(p, b, cs)
        p.setBrush(QColor("#7a4b25"))
        p.setPen(pen("#2b2b2b", 0.05))
        p.drawEllipse(b)
        p.drawEllipse(b.adjusted(cs * 0.09, cs * 0.09, -cs * 0.09, -cs * 0.09))
    elif kind == "crate":
        b = QRectF(c.x() - cs * 0.31, c.y() - cs * 0.31, cs * 0.62, cs * 0.62)
        drop(p, b, cs)
        p.setBrush(QColor("#8a6234"))
        p.setPen(pen("#3d2610", 0.05))
        p.drawRect(b)
        p.drawLine(b.topLeft(), b.bottomRight())
        p.drawLine(b.topRight(), b.bottomLeft())
    elif kind == "table":
        b = QRectF(c.x() - cs * 0.4, c.y() - cs * 0.27, cs * 0.8, cs * 0.54)
        drop(p, b, cs)
        p.setBrush(QColor("#6e4524"))
        p.setPen(pen("#2e1a0a"))
        p.drawRect(b)
        p.setBrush(QColor("#d8d0c0"))
        p.drawEllipse(c, cs * 0.09, cs * 0.09)
    elif kind == "bed":
        b = QRectF(c.x() - cs * 0.27, c.y() - cs * 0.42, cs * 0.54, cs * 0.84)
        p.setBrush(QColor("#5a3a1e"))
        p.setPen(pen("#2e1a0a"))
        p.drawRect(b)
        p.setBrush(QColor("#7a2020"))
        p.drawRect(b.adjusted(cs * 0.04, cs * 0.25, -cs * 0.04, -cs * 0.04))
        p.setBrush(QColor("#e8e0cc"))
        p.drawRect(QRectF(b.x() + cs * 0.08, b.y() + cs * 0.05, b.width() - cs * 0.16, cs * 0.15))
    elif kind == "bookshelf":
        b = QRectF(r.x() + cs * 0.04, c.y() - cs * 0.2, cs * 0.92, cs * 0.4)
        p.setBrush(QColor("#3e2614"))
        p.setPen(pen("#1e1209"))
        p.drawRect(b)
        cols = ["#7a2020", "#2e5a7a", "#3f6b2f", "#c9a227", "#5b3f7a"]
        for k in range(7):
            p.fillRect(QRectF(b.x() + cs * (0.05 + 0.12 * k), b.y() + cs * 0.06, cs * 0.09, cs * 0.28), QColor(cols[(k + seed) % 5]))
    elif kind in ("stairs_up", "stairs_down"):
        b = QRectF(r.x() + cs * 0.08, r.y() + cs * 0.08, cs * 0.84, cs * 0.84)
        for k in range(6):
            f = k / 5 if kind == "stairs_down" else 1 - k / 5
            p.fillRect(QRectF(b.x(), b.y() + k * b.height() / 6, b.width(), b.height() / 6), shade("#9a9286", 1.1 - 0.75 * f))
        p.setPen(pen("#2d2925", 0.03))
        p.setBrush(Qt.NoBrush)
        p.drawRect(b)
    elif kind == "torch":
        g = QRadialGradient(c, cs * 0.45)
        g.setColorAt(0, QColor(255, 200, 90, 220))
        g.setColorAt(1, QColor(255, 120, 30, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(c, cs * 0.45, cs * 0.45)
        p.setBrush(QColor("#2b2b2b"))
        p.drawEllipse(c, cs * 0.1, cs * 0.1)
        p.setBrush(QColor("#ffd27a"))
        p.drawEllipse(c, cs * 0.05, cs * 0.05)
    elif kind == "trap":
        b = QRectF(c.x() - cs * 0.3, c.y() - cs * 0.3, cs * 0.6, cs * 0.6)
        dash = pen("#ff4040", 0.05)
        dash.setStyle(Qt.DashLine)
        p.setPen(dash)
        p.setBrush(QColor(140, 20, 20, 70))
        p.drawRect(b)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d0d0d0"))
        for i in range(3):
            for j in range(3):
                p.drawEllipse(QPointF(b.x() + cs * (0.12 + 0.18 * i), b.y() + cs * (0.12 + 0.18 * j)), cs * 0.03, cs * 0.03)
    elif kind == "bones":
        p.setPen(pen("#e6dfcf", 0.06))
        p.drawLine(c + QPointF(-cs * 0.22, -cs * 0.12), c + QPointF(cs * 0.2, cs * 0.16))
        p.drawLine(c + QPointF(-cs * 0.2, cs * 0.18), c + QPointF(cs * 0.18, -cs * 0.14))
        p.setBrush(QColor("#e6dfcf"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(c + QPointF(cs * 0.18, cs * 0.2), cs * 0.1, cs * 0.09)
    elif kind == "rubble":
        p.setPen(pen("#2d2925", 0.02))
        for k in range(4):
            a = c + QPointF(cs * (0.25 * math.cos(k * 1.7 + seed)), cs * (0.22 * math.sin(k * 2.3 + seed)))
            p.setBrush(QColor("#7a746a") if k % 2 else QColor("#5f5a52"))
            p.drawPolygon(QPolygonF([a + QPointF(cs * 0.1 * math.cos(t), cs * 0.08 * math.sin(t)) for t in (0, 2, 3.5, 5)]))
    elif kind == "grave":
        b = QRectF(c.x() - cs * 0.2, c.y() - cs * 0.3, cs * 0.4, cs * 0.55)
        drop(p, b, cs)
        path = QPainterPath()
        path.addRoundedRect(b, cs * 0.18, cs * 0.18)
        p.setBrush(QColor("#8c8a84"))
        p.setPen(pen("#3a3834"))
        p.drawPath(path)
        p.drawLine(QLineF(c.x(), b.top() + cs * 0.1, c.x(), b.top() + cs * 0.32))
        p.drawLine(QLineF(c.x() - cs * 0.08, b.top() + cs * 0.17, c.x() + cs * 0.08, b.top() + cs * 0.17))
    elif kind == "well":
        p.setBrush(QColor("#7f7a72"))
        p.setPen(pen("#3a3834", 0.05))
        p.drawEllipse(c, cs * 0.42, cs * 0.42)
        p.setBrush(QColor("#1d3c52"))
        p.drawEllipse(c, cs * 0.26, cs * 0.26)
    elif kind == "campfire":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#6a655c"))
        for k in range(7):
            a = k * math.tau / 7
            p.drawEllipse(c + QPointF(math.cos(a) * cs * 0.3, math.sin(a) * cs * 0.3), cs * 0.08, cs * 0.07)
        g = QRadialGradient(c, cs * 0.26)
        g.setColorAt(0, QColor("#fff3a0"))
        g.setColorAt(0.5, QColor("#ff8a1e"))
        g.setColorAt(1, QColor(200, 40, 0, 0))
        p.setBrush(g)
        p.drawEllipse(c, cs * 0.26, cs * 0.26)
    elif kind == "tree":  # canopy overhangs neighbouring cells
        rad = cs * (0.55 + 0.12 * rnd(int(c.x()), int(c.y()), seed, 1))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawEllipse(c + QPointF(cs * 0.12, cs * 0.12), rad, rad)
        p.setBrush(QColor("#2f4f1f"))
        p.drawEllipse(c, rad, rad)
        for k in range(5):
            a = k * 1.3 + seed
            p.setBrush(QColor("#4f7a32") if k % 2 else QColor("#3d6427"))
            p.drawEllipse(c + QPointF(math.cos(a) * rad * 0.45, math.sin(a) * rad * 0.45), rad * 0.42, rad * 0.42)
    elif kind == "bush":
        p.setPen(Qt.NoPen)
        for k, (dx, dy) in enumerate(((-0.12, 0), (0.12, -0.05), (0, 0.12))):
            p.setBrush(QColor("#3f6b2f") if k % 2 else QColor("#557f38"))
            p.drawEllipse(c + QPointF(cs * dx, cs * dy), cs * 0.2, cs * 0.2)
    elif kind == "rock":
        pts = [c + QPointF(math.cos(a) * cs * (0.3 + 0.08 * math.sin(a * 3 + seed)), math.sin(a) * cs * (0.27 + 0.06 * math.cos(a * 2 + seed)))
               for a in (k * math.tau / 7 for k in range(7))]
        drop(p, QRectF(c.x() - cs * 0.3, c.y() - cs * 0.27, cs * 0.6, cs * 0.54), cs)
        p.setBrush(QColor("#7d7a72"))
        p.setPen(pen("#3a3834", 0.03))
        p.drawPolygon(QPolygonF(pts))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawEllipse(c - QPointF(cs * 0.08, cs * 0.08), cs * 0.12, cs * 0.08)
    elif kind == "mushrooms":
        p.setPen(Qt.NoPen)
        for k, (dx, dy, col) in enumerate(((-0.15, 0.05, "#a855f7"), (0.12, -0.1, "#2dd4bf"), (0.08, 0.16, "#a855f7"))):
            g = QRadialGradient(c + QPointF(cs * dx, cs * dy), cs * 0.18)
            g.setColorAt(0, QColor(col))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(g)
            p.drawEllipse(c + QPointF(cs * dx, cs * dy), cs * 0.18, cs * 0.18)
            p.setBrush(QColor(col))
            p.drawEllipse(c + QPointF(cs * dx, cs * dy), cs * 0.07, cs * 0.07)
    p.restore()


def custom(p, spec, r, vertical, opened, seed):
    """A Brewery object: its own image (or a built-in shape), sized in squares, with a glow in its light colour."""
    cs, c = r.width(), r.center()
    if spec is None:  # deleted from the Brewery: show a placeholder instead of failing
        p.setPen(QPen(QColor("#e0b84f"), max(1.0, cs * 0.04), Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(r.adjusted(cs * 0.15, cs * 0.15, -cs * 0.15, -cs * 0.15))
        p.drawText(r, Qt.AlignCenter, "?")
        return
    L, s = spec.get("light") if spec.get("lit", True) else None, cs * spec.get("size", 1)
    if L:
        g = QRadialGradient(c, s * 0.75)
        col = QColor(L["color"])
        g.setColorAt(0, QColor(col.red(), col.green(), col.blue(), 130))
        g.setColorAt(1, QColor(col.red(), col.green(), col.blue(), 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(c, s * 0.75, s * 0.75)
    path = spec["alt_img"] if opened and spec.get("alt_img") else spec.get("img")
    if path and path not in _IMAGES:
        _IMAGES[path] = QImage(path)
    im = _IMAGES.get(path) if path else None
    box = QRectF(c.x() - s / 2, c.y() - s / 2, s, s)
    if im is not None and not im.isNull():
        k = s / max(im.width(), im.height())
        p.drawImage(QRectF(c.x() - im.width() * k / 2, c.y() - im.height() * k / 2, im.width() * k, im.height() * k), im)
    elif not spec.get("base", "").startswith("brew:"):
        obj(p, spec.get("base") or "statue", box, vertical, opened, seed)


def door_vertical(m, x, y):
    return m.get(x, y - 1) == VOID and m.get(x, y + 1) == VOID


def region(p, m, cs, x0, y0, x1, y1, grid=False, skip=()):
    """Redraws cells x0..x1, y0..y1 (clamped). Objects from one cell further out are redrawn too, clipped,
    so overhanging tree canopies stay correct."""
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(m.w - 1, x1), min(m.h - 1, y1)
    if x0 > x1 or y0 > y1:
        return
    clip = QRectF(x0 * cs, y0 * cs, (x1 - x0 + 1) * cs, (y1 - y0 + 1) * cs)
    p.save()
    p.setClipRect(clip)
    p.setRenderHint(QPainter.Antialiasing)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            terrain(p, m, x, y, cs)
    if grid:
        p.setPen(QPen(QColor(0, 0, 0, 70), 1))
        for x in range(x0, x1 + 2):
            p.drawLine(QLineF(x * cs, clip.top(), x * cs, clip.bottom()))
        for y in range(y0, y1 + 2):
            p.drawLine(QLineF(clip.left(), y * cs, clip.right(), y * cs))
    cells = [(x, y) for y in range(max(0, y0 - 1), min(m.h, y1 + 2)) for x in range(max(0, x0 - 1), min(m.w, x1 + 2))]
    for x, y in sorted(cells, key=lambda c: m.o[c[1]][c[0]] == "tree"):  # trees last, on top
        k = m.o[y][x]
        if k and k not in skip:
            obj(p, k, QRectF(x * cs, y * cs, cs, cs), k == "door" and door_vertical(m, x, y), seed=(x * 7 + y * 13) % 5)
    p.restore()


def render(m, cs, grid=False, skip=()):
    img = QImage(m.w * cs, m.h * cs, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor("#15110e"))
    p = QPainter(img)
    region(p, m, cs, 0, 0, m.w - 1, m.h - 1, grid, skip)
    p.end()
    return img


def object_image(kind, size=140, opened=False):
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    k = max(1.0, (CUSTOM.get(kind[5:]) or {}).get("size", 1)) if kind.startswith("brew:") else 1.0  # big objects shrink to fit
    obj(p, kind, QRectF(size * (1 - 1 / k) / 2, size * (1 - 1 / k) / 2, size / k, size / k), opened=opened)
    p.end()
    return img


def chunk_image(g, cs):
    m = MapData(len(g[0]), len(g), seed=7)
    for y, row in enumerate(g):
        for x, cell in enumerate(row):
            m.t[y][x], m.o[y][x] = cell if cell else (VOID, "")
    img = render(m, cs)
    p = QPainter(img)
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    for y, row in enumerate(g):  # transparent cells stay see-through in previews
        for x, cell in enumerate(row):
            if cell is None:
                p.fillRect(QRectF(x * cs, y * cs, cs, cs), Qt.transparent)
    p.end()
    return img
