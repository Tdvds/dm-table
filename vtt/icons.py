"""App icons drawn in code: a d20 in a gear (launcher), a d20 showing VTT (the table), a d20 with an anvil (Map Forge).
Run `python -m vtt.icons` to write .ico/.png files to assets/ for PyInstaller and Linux desktop entries."""
import math, os, struct, sys
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient

SIZES = (16, 24, 32, 48, 64, 128, 256)
STYLE = {"launcher": ("#9b1c1c", "#e0b84f", "#f3e6c4"), "table": ("#9b1c1c", "#e0b84f", "#f3e6c4"),
         "forge": ("#4a525c", "#ff9a3c", "#ffcc66"), "brewery": ("#1f6f5c", "#e0b84f", "#f3e6c4")}  # die face, edges, label


def shade(col, f):
    c = QColor(col)
    return QColor(*(min(255, int(v * f)) for v in (c.red(), c.green(), c.blue())))


def at(c, r, deg):
    return QPointF(c.x() + r * math.cos(math.radians(deg)), c.y() + r * math.sin(math.radians(deg)))


def d20(p, c, R, face, edge):
    """A d20 seen face-on: hexagon outline, central triangle and the facets around it, lit from the top left."""
    H = [at(c, R, -90 + 60 * k) for k in range(6)]
    T = [at(c, R * 0.5, a) for a in (-90, 30, 150)]
    facets = [((H[0], H[1], T[0]), 1.3), ((H[5], H[0], T[0]), 1.15), ((H[1], H[2], T[1]), 0.85), ((H[1], T[1], T[0]), 1.0),
              ((H[2], H[3], T[1]), 0.68), ((H[3], T[2], T[1]), 0.8), ((H[3], H[4], T[2]), 0.62), ((H[4], H[5], T[2]), 0.9),
              ((H[5], T[0], T[2]), 1.05), ((T[0], T[1], T[2]), 1.12)]
    p.setPen(QPen(QColor(edge), max(0.8, R * 0.04), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    for tri, f in facets:
        p.setBrush(shade(face, f))
        p.drawPolygon(QPolygonF(list(tri)))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(edge), max(1.0, R * 0.08), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolygon(QPolygonF(H))


def gear(p, c, R, teeth=10):
    pts = []
    n = teeth * 4
    for i in range(n):
        r = R if i % 4 in (1, 2) else R * 0.8
        pts.append(at(c, r, i * 360 / n))
    g = QRadialGradient(c - QPointF(R * 0.3, R * 0.3), R * 1.4)
    g.setColorAt(0, QColor("#e9c46a"))
    g.setColorAt(1, QColor("#7a5418"))
    p.setBrush(g)
    p.setPen(QPen(QColor("#3a2a10"), max(0.8, R * 0.04)))
    p.drawPolygon(QPolygonF(pts))
    p.setBrush(QColor("#1c1510"))
    p.drawEllipse(c, R * 0.66, R * 0.66)


def anvil(p, c, w, col):
    pts = [(-0.5, -0.2), (-0.25, -0.26), (0.45, -0.26), (0.45, -0.12), (0.16, -0.06), (0.1, 0.08), (0.26, 0.19), (0.26, 0.27),
           (-0.26, 0.27), (-0.26, 0.19), (-0.1, 0.08), (-0.16, -0.06), (-0.32, -0.1)]
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(c.x() + x * w, c.y() + y * w) for x, y in pts]))
    path.closeSubpath()
    p.setPen(QPen(QColor(0, 0, 0, 160), max(0.6, w * 0.04)))
    p.setBrush(QColor(col))
    p.drawPath(path)


def flask(p, c, w, col):
    """A round potion flask with a cork and glowing brew."""
    p.setPen(QPen(QColor(0, 0, 0, 160), max(0.6, w * 0.04)))
    p.setBrush(QColor("#7a4b25"))
    p.drawRect(QRectF(c.x() - w * 0.09, c.y() - w * 0.5, w * 0.18, w * 0.1))  # cork
    p.setBrush(QColor(col))
    p.drawRect(QRectF(c.x() - w * 0.08, c.y() - w * 0.4, w * 0.16, w * 0.2))  # neck
    p.drawEllipse(QPointF(c.x(), c.y() + w * 0.08), w * 0.3, w * 0.3)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#c04bd6"))
    p.drawChord(QRectF(c.x() - w * 0.26, c.y() - w * 0.18, w * 0.52, w * 0.52), 200 * 16, 140 * 16)  # the brew


def image(kind, size):
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    c = QPointF(size / 2, size / 2)
    face, edge, label = STYLE[kind]
    if kind == "launcher":
        gear(p, c, size * 0.49)
        d20(p, c, size * 0.31, face, edge)
    else:
        R = size * 0.47
        d20(p, c, R, face, edge)
        if kind == "table":
            if size >= 24:  # text is unreadable on the tiniest icon; the red d20 still says "table"
                f = QFont("Palatino Linotype")
                f.setStyleHint(QFont.Serif)  # falls back to any serif on Linux
                f.setBold(True)
                f.setPixelSize(max(6, int(R * 0.27)))
                p.setFont(f)
                p.setPen(QColor(label))
                p.drawText(QRectF(c.x() - R * 0.4, c.y() - R * 0.12, R * 0.8, R * 0.34), Qt.AlignCenter, "VTT")
        elif kind == "brewery":
            flask(p, c + QPointF(0, R * 0.02), R * 0.62, label)
        else:
            anvil(p, c + QPointF(0, R * 0.04), R * 0.62, label)
    p.end()
    return img


def icon(kind):
    ic = QIcon()
    for s in SIZES:
        ic.addPixmap(QPixmap.fromImage(image(kind, s)))
    return ic


def png_bytes(img):
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def write_ico(path, kind):
    """Multi-size Windows .ico with PNG entries (supported since Windows Vista)."""
    blobs = [(s, png_bytes(image(kind, s))) for s in SIZES]
    head = struct.pack("<HHH", 0, 1, len(blobs))
    offset, entries, data = 6 + 16 * len(blobs), b"", b""
    for s, b in blobs:
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(b), offset + len(data))
        data += b
    with open(path, "wb") as f:
        f.write(head + entries + data)


def write_files(folder):
    os.makedirs(folder, exist_ok=True)
    for kind, name in (("launcher", "dmtable"), ("table", "table"), ("forge", "forge"), ("brewery", "brewery")):
        write_ico(os.path.join(folder, f"{name}.ico"), kind)
        image(kind, 256).save(os.path.join(folder, f"{name}.png"))


def windows_taskbar_id():
    """Without this, Windows shows the Python icon in the taskbar when running from source."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DMTable.VTT")
        except (OSError, AttributeError):
            pass


if __name__ == "__main__":
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication(sys.argv)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    write_files(out)
    print("wrote icons to", out)
